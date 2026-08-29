"""A source that did not answer must never look like a source that answered plainly.

Four sources feed one forecast — league tables, prices, weather, team news — and each can
be silent for a different reason on the same fixture. The failure this file guards against
is small, specific and would be invisible: a timed-out weather call becoming a still, dry
evening, an unmatched club name becoming an average team, a missing injury report becoming
a fit squad. Each of those is a number the model would use without hesitation, and none of
them was ever measured.

The other property here is about matching, and it is a deliberate piece of friction. The
odds feed says `Manchester United`; football-data says `Manchester United FC`. Reconciling
that automatically past a small stated normalisation is where this kind of system quietly
goes wrong — a fuzzy matcher that is right 95% of the time models the wrong team's goals
one fixture in twenty with nothing downstream able to tell. So an unmatched name is UNKNOWN
naming both spellings, which is an alias somebody adds once. That is more annoying than a
fuzzy match, in the direction that produces a question rather than a wrong number.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from connectors.football_data import (
    MINIMUM_MATCHES_FOR_STRENGTH,
    NOT_CONFIGURED,
    READ,
    UNREACHABLE,
    FootballData,
    Standings,
    TeamRow,
    rest_days,
    strengths_from,
)
from connectors.teamnews import Report, TeamNews
from connectors.weather import (
    NOT_FOUND,
    OUT_OF_HORIZON,
    Place,
    VenueBook,
    WeatherReading,
    _hour_from,
    conditions_for,
    forecast_at,
)
from lib.mispricing import KNOWN, STALE, UNKNOWN
from lib.mispricing_evidence import (
    StandingsCache,
    gather,
    normalise_team,
    split_market,
    strength_features,
)

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
KICKOFF = "2026-08-29T18:00:00Z"
MARKET = f"Arsenal v Chelsea @ {KICKOFF}"


def table(**played) -> Standings:
    rows = tuple(
        TeamRow(team=team, played=games, goals_for=games * 2, goals_against=games)
        for team, games in (played or {"Arsenal FC": 20, "Chelsea FC": 20}).items())
    return Standings(READ, "PL", rows, "2026-08-01", "2026-08-29T00:00:00Z")


class TestAnUnmatchedTeamIsAQuestionNotAnAverage:
    def test_a_club_suffix_is_stripped_because_it_is_a_stated_difference(self):
        assert normalise_team("Manchester United FC") == "manchester united"
        assert normalise_team("Arsenal") == normalise_team("Arsenal FC")

    def test_normalisation_stops_where_guessing_would_start(self):
        """Everything it does is predictable from its name. `Spurs` and `Tottenham
        Hotspur` are the same club and this deliberately does not know that — that is an
        alias somebody records, not a rule somebody guesses."""

        assert normalise_team("Spurs") != normalise_team("Tottenham Hotspur")

    def test_an_unmatched_team_produces_unknown_strengths_naming_both_spellings(self):
        features, report = strength_features(
            "Spurs", "Chelsea", {"Tottenham Hotspur": {"attack": 1.1, "defence": 0.9},
                                 "Chelsea": {"attack": 1.0, "defence": 1.0}})

        assert all(f.status == UNKNOWN for f in features)
        assert report.answered is False
        assert "Spurs" in features[0].detail and "Tottenham Hotspur" in features[0].detail
        assert "alias" in features[0].detail

    def test_an_alias_closes_it(self):
        features, report = strength_features(
            "Spurs", "Chelsea",
            {"Tottenham Hotspur": {"attack": 1.1, "defence": 0.9},
             "Chelsea": {"attack": 1.0, "defence": 1.0}},
            aliases={"Spurs": "Tottenham Hotspur"})

        assert all(f.status == KNOWN for f in features)
        assert report.answered is True

    def test_no_table_at_all_is_unknown_with_the_reason(self):
        features, report = strength_features(
            "Arsenal", "Chelsea", {}, refusal="no key at ~/.footballdata/key")

        assert all(f.status == UNKNOWN for f in features)
        assert "no key" in features[0].detail
        assert report.answered is False

    def test_a_market_name_that_cannot_be_parsed_looks_nothing_up(self):
        """Inventing a home side from the first half of a string is how a fixture gets
        modelled against the wrong team."""

        assert split_market("1.234567") == ("", "", "")
        gathered = gather("1.234567")

        assert gathered.evidence.features == ()
        assert "neither side could be identified" in gathered.sources[0].detail


class TestALeagueTableCanBeTooEarlyToMeanAnything:
    def test_a_table_with_too_few_matches_refuses_rather_than_computing(self):
        """Four matches of noise, used as though it were a rate, is a confident number
        with nothing behind it."""

        early = table(**{"Arsenal FC": 4, "Chelsea FC": 4})

        strengths, _rate, refusal = strengths_from(early)

        assert strengths == {}
        assert str(MINIMUM_MATCHES_FOR_STRENGTH) in refusal

    def test_the_minimum_applies_per_team_rather_than_to_the_total(self):
        """A table where one side has played fourteen and another four is not a table with
        an average of nine — the four-game team's rate is still noise."""

        lopsided = table(**{"Arsenal FC": 30, "Chelsea FC": 4})

        assert lopsided.has_enough_evidence is False

    def test_a_table_that_was_never_retrieved_is_not_a_table_with_no_teams(self):
        strengths, _rate, refusal = strengths_from(
            Standings(NOT_CONFIGURED, "PL", reason="no key"))

        assert strengths == {}
        assert "was not retrieved" in refusal

    def test_a_full_table_produces_strengths(self):
        strengths, rate, refusal = strengths_from(table())

        assert refusal == ""
        assert set(strengths) == {"Arsenal FC", "Chelsea FC"}
        assert rate > 0

    def test_an_unconfigured_client_says_so_rather_than_returning_an_empty_league(self):
        standings = FootballData(None).standings("PL")

        assert standings.status == NOT_CONFIGURED
        assert "not a finding that the competition has no table" in standings.describe()

    def test_a_client_that_cannot_reach_the_api_is_unreachable_not_empty(self):
        def dead(_request, **_kw):
            raise OSError("connection reset")

        from connectors.football_data import Credentials

        standings = FootballData(Credentials("k"), opener=dead).standings("PL")

        assert standings.status == UNREACHABLE
        assert "unknown, not absent" in standings.describe()

    def test_only_the_total_table_is_read(self):
        """Taking the first table would silently take HOME on competitions that order them
        differently, and a home-only attack strength multiplied by this model's own home
        advantage counts the same effect twice."""

        payload = {"season": {"startDate": "2026-08-01"}, "standings": [
            {"type": "HOME", "table": [
                {"team": {"name": "Arsenal FC"}, "playedGames": 10,
                 "goalsFor": 30, "goalsAgainst": 2}]},
            {"type": "TOTAL", "table": [
                {"team": {"name": "Arsenal FC"}, "playedGames": 20,
                 "goalsFor": 40, "goalsAgainst": 20}]},
        ]}

        class Response:
            def read(self):
                return json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        from connectors.football_data import Credentials

        standings = FootballData(Credentials("k"),
                                 opener=lambda *_a, **_kw: Response()).standings("PL")

        assert standings.team("Arsenal FC").played == 20

    def test_rest_days_are_none_rather_than_a_plausible_week(self):
        """A team whose last fixture nobody could establish is not a well-rested team."""

        assert rest_days(KICKOFF, "") is None
        assert rest_days(KICKOFF, "2026-08-26T18:00:00Z") == pytest.approx(3.0)


class TestWeatherIsNeverAStillDryEvening:
    def test_a_failed_call_produces_unknown_features_not_zeroes(self):
        def dead(_request, **_kw):
            raise OSError("timed out")

        reading = forecast_at(Place("Emirates", 51.55, -0.11), KICKOFF, opener=dead,
                              now=NOW)

        assert reading.status == UNREACHABLE
        features = reading.features(NOW)
        assert all(f.status == UNKNOWN and f.value is None for f in features)
        assert "not a still, dry evening" in reading.describe()

    def test_a_fixture_beyond_the_forecast_horizon_is_not_a_failure(self):
        far = (NOW + timedelta(days=40)).isoformat()

        reading = forecast_at(Place("Emirates", 51.55, -0.11), far,
                              opener=lambda *_a, **_kw: None, now=NOW)

        assert reading.status == OUT_OF_HORIZON
        assert "The service is working" in reading.reason

    def test_the_nearest_hour_must_actually_be_near(self):
        """Taking the closest available hour whatever its distance is how a Saturday
        evening fixture gets Sunday morning weather."""

        payload = {"hourly": {"time": ["2026-08-30T09:00"], "temperature_2m": [14.0],
                              "wind_speed_10m": [8.0], "precipitation": [0.0]}}

        reading = _hour_from(payload, Place("Emirates", 51.55, -0.11),
                             datetime.fromisoformat("2026-08-29T18:00:00+00:00"), NOW)

        assert reading.status == OUT_OF_HORIZON
        assert "different part of the evening" in reading.reason

    def test_a_reading_within_tolerance_becomes_known_features(self):
        payload = {"generationtime_stamp": "2026-08-29T11:00:00Z",
                   "hourly": {"time": ["2026-08-29T18:00"], "temperature_2m": [14.0],
                              "wind_speed_10m": [8.0], "precipitation": [0.0]}}

        reading = _hour_from(payload, Place("Emirates", 51.55, -0.11),
                             datetime.fromisoformat("2026-08-29T18:00:00+00:00"), NOW)
        features = reading.features(NOW)

        assert reading.status == READ
        assert {f.name for f in features if f.status == KNOWN} == {
            "temperature_c", "wind_speed_kph", "precipitation_mm"}

    def test_an_old_forecast_run_is_stale_rather_than_current(self):
        """Open-Meteo refreshes hourly, so anything past a few hours is a superseded run —
        still a forecast, and not the current one."""

        reading = WeatherReading(
            READ, "Emirates", valid_at=KICKOFF,
            issued_at=(NOW - timedelta(hours=12)).isoformat(),
            temperature_c=14.0, wind_speed_kph=8.0, precipitation_mm=0.0)

        assert reading.is_stale(NOW) is True
        assert all(f.status == STALE for f in reading.features(NOW))

    def test_a_reading_with_no_issue_time_is_treated_as_stale(self):
        """A forecast whose age cannot be established has not been established to be
        current, and the direction that withholds an adjustment is the one to be wrong in."""

        assert WeatherReading(READ, "x", issued_at="not a date").is_stale(NOW) is True

    def test_a_recorded_venue_is_used_before_the_geocoder(self, tmp_path):
        """A geocoder asked for 'Anfield' will answer, and it will also answer for a street
        of that name in another country."""

        path = tmp_path / "venues.json"
        path.write_text(json.dumps([{"name": "Anfield", "latitude": 53.4308,
                                     "longitude": -2.9608, "source": "the club's page"}]),
                        encoding="utf-8")

        asked = []

        def opener(request, **_kw):
            asked.append(request.full_url)
            raise OSError("no network in this test")

        conditions_for("Anfield", KICKOFF, venues=VenueBook.load(path), opener=opener,
                       now=NOW)

        assert all("geocoding" not in url for url in asked)

    def test_an_unfindable_place_is_not_found_rather_than_unreachable(self, tmp_path):
        """Two failures that send a person to opposite ends of the problem: one is a name
        to correct, one is a request to make again."""

        class Empty:
            def read(self):
                return b'{"results": []}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        reading, place = conditions_for("Nowhere Stadium", KICKOFF,
                                        venues=VenueBook.load(tmp_path / "none.json"),
                                        opener=lambda *_a, **_kw: Empty(), now=NOW)

        assert reading.status == NOT_FOUND
        assert place is None


class TestTeamNewsSaysItDoesNotKnow:
    def test_no_report_is_unknown_and_says_the_book_knows(self, tmp_path):
        news = TeamNews.load(tmp_path / "news.json")

        feature = news.feature("Arsenal", "home_key_absences", now=NOW)

        assert feature.status == UNKNOWN
        assert "The book knows it" in feature.detail

    def test_an_old_report_is_stale_rather_than_usable(self, tmp_path):
        """A squad changes in three days. An injury list from Monday is not the team news
        for Saturday, and the two must not render alike."""

        news = TeamNews(tmp_path / "news.json")
        news.record(Report("Arsenal", 2, ("a", "b"), "a press conference", "Ian McGuane",
                           (NOW - timedelta(days=9)).date().isoformat()))

        feature = news.feature("Arsenal", "home_key_absences", now=NOW)

        assert feature.status == STALE
        assert feature.value is None

    def test_a_current_report_becomes_a_number(self, tmp_path):
        news = TeamNews(tmp_path / "news.json")
        news.record(Report("Arsenal", 2, ("a", "b"), "a press conference", "Ian McGuane",
                           (NOW - timedelta(days=1)).date().isoformat()))

        feature = news.feature("Arsenal", "home_key_absences", now=NOW)

        assert feature.status == KNOWN and feature.value == 2.0

    def test_a_report_needs_a_source_and_a_person(self, tmp_path):
        with pytest.raises(ValueError, match="needs its source"):
            Report("Arsenal", 1, (), "", "Ian McGuane", "2026-08-29")
        with pytest.raises(ValueError, match="needs the person"):
            Report("Arsenal", 1, (), "a press conference", "", "2026-08-29")

    def test_a_partial_name_list_is_refused(self):
        """A partial list reads as the whole one, and a count nobody can argue with is the
        wrong kind of unarguable."""

        with pytest.raises(ValueError, match="Either name all of them or none"):
            Report("Arsenal", 3, ("one name",), "a press conference", "Ian McGuane",
                   "2026-08-29")

    def test_an_unreadable_file_is_not_a_fit_squad(self, tmp_path):
        path = tmp_path / "news.json"
        path.write_text("{not json", encoding="utf-8")

        news = TeamNews.load(path)

        assert news.readable is False
        assert news.feature("Arsenal", "home_key_absences").status == UNKNOWN
        assert "Not a finding that everybody is fit" in news.describe()

    def test_the_most_recent_report_supersedes_an_earlier_one(self, tmp_path):
        """A player passed fit on Friday is fit."""

        news = TeamNews(tmp_path / "news.json")
        news.record(Report("Arsenal", 3, (), "Wednesday", "Ian McGuane", "2026-08-26"))
        news.record(Report("Arsenal", 1, (), "Friday", "Ian McGuane", "2026-08-28"))

        assert news.latest("Arsenal").key_absences == 1


class TestGatheringReportsEverySourceSeparately:
    def test_every_silent_source_is_named_separately(self, tmp_path):
        """Four sources can each be silent for a different reason on the same fixture, and
        a bundle that merged them leaves a person unable to tell a missing key from a dead
        endpoint from a competition nobody configured."""

        gathered = gather(MARKET, news=TeamNews.load(tmp_path / "n.json"),
                          with_weather=False, now=NOW)

        assert [r.answered for r in gathered.sources] == [False, False]
        assert len({r.source for r in gathered.sources}) == 2

    def test_a_gathered_bundle_carries_the_kickoff_from_the_market_name(self):
        assert gather(MARKET, with_weather=False).evidence.kickoff == KICKOFF

    def test_no_venue_is_an_unasked_question_rather_than_a_calm_evening(self):
        gathered = gather(MARKET, venue="", with_weather=True, now=NOW)

        weather = [f for f in gathered.evidence.features
                   if f.name == "wind_speed_kph"][0]
        assert weather.status == UNKNOWN
        assert "an unasked question" in weather.detail


class TestTheStandingsCache:
    def test_a_lane_with_no_client_says_the_teams_are_not_average(self):
        strengths, refusal = StandingsCache(None, ()).for_team("Arsenal", "Chelsea")

        assert strengths == {}
        assert "not a finding that the teams are average" in refusal

    def test_both_sides_must_be_in_the_same_table(self):
        """A table with the home side and not the away side gives one real strength and
        one unmatched — correct, and buried. This says plainly that these two are not in
        the same competition anybody configured."""

        class OneTeam:
            def standings(self, _competition):
                return table(**{"Arsenal FC": 20})

        cache = StandingsCache(OneTeam(), ("PL",))

        strengths, refusal = cache.for_team("Arsenal", "Chelsea")

        assert strengths == {}
        assert "PL" in refusal

    def test_a_table_holding_both_sides_answers(self):
        class Both:
            def standings(self, _competition):
                return table()

        strengths, refusal = StandingsCache(Both(), ("PL",)).for_team("Arsenal", "Chelsea")

        assert refusal == ""
        assert set(strengths) == {"Arsenal FC", "Chelsea FC"}

    def test_the_table_is_fetched_once_for_every_fixture_in_it(self):
        """One table per competition per run means every fixture in a league is modelled
        against the same numbers — a property worth more than the requests saved."""

        calls = []

        class Counting:
            def standings(self, competition):
                calls.append(competition)
                return table()

        cache = StandingsCache(Counting(), ("PL",))
        cache.for_team("Arsenal", "Chelsea")
        cache.for_team("Arsenal", "Chelsea")

        assert calls == ["PL"]
