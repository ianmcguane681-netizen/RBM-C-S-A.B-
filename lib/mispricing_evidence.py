"""Gather one fixture's evidence from three sources, and report each one that was silent.

`lib/mispricing.py` holds what a feature IS and refuses to compute without the ones a model
requires. `lib/mispricing_reaper.py` holds the lane. This is the wiring in between: given a
market name and the lane's configuration, produce an `Evidence` bundle.

The only interesting decision here is what happens when a source does not answer, and it is
the same decision the whole repository makes. A silent source produces features that are
`UNKNOWN` **with the reason attached**, never features that are absent and never features
that are plausible. Four sources can each be silent for different reasons on the same
fixture, and a bundle that merged them into "some evidence was gathered" would leave a
person unable to tell a missing key from a dead endpoint from a competition nobody
configured.

## The name-matching problem, stated rather than papered over

The odds feed names a fixture `Manchester United v Liverpool @ 2026-08-29T14:00:00Z`.
football-data calls the same club `Manchester United FC`. These are two vocabularies for one
set of teams and nothing reconciles them automatically here.

Doing it automatically is where a system like this quietly goes wrong: a fuzzy matcher that
is right 95% of the time is a model built on the wrong team's goals one fixture in twenty,
with no signal that it happened. So matching is exact after a small, stated normalisation —
case, punctuation, and a short list of club-name suffixes — and anything that does not match
is `UNKNOWN` naming both spellings, which is an alias a person adds to the config once.

That is deliberately more annoying than a fuzzy match. It is annoying in the direction that
produces a question rather than a wrong number.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from lib.mispricing import KNOWN, UNKNOWN, Evidence, Feature

#: Suffixes stripped before comparing club names. Short, and each one is a real difference
#: between how an odds feed and a results API write the same club. Anything beyond this list
#: is an alias somebody records, not a rule somebody guesses.
CLUB_SUFFIXES = (" fc", " afc", " cf", " sc", " ac", " bk", " if", " fk")

TEAM_NEWS = Path("data/team-news.json")
VENUES = Path("data/venues.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalise_team(name: str) -> str:
    """Lowercase, punctuation-free, and without a trailing club suffix.

    Stated and small on purpose. Every transformation here is one a person could predict
    from the name of the function, which is what makes an unmatched team a question about
    an alias rather than a mystery about a matcher.
    """

    cleaned = "".join(
        character.lower() if character.isalnum() or character.isspace() else " "
        for character in str(name)
    )
    cleaned = " ".join(cleaned.split())
    for suffix in CLUB_SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
            break
    return cleaned


def split_market(market: str) -> tuple[str, str, str]:
    """`Home v Away @ <iso>` into its three parts. Empty strings on anything else.

    Empty rather than a best guess. A market whose name this cannot parse is a market whose
    teams are unknown, and inventing one from the first half of a string is how a fixture
    gets modelled against the wrong side.
    """

    head, separator, tail = str(market).rpartition(" @ ")
    if not separator:
        head, tail = str(market), ""
    home, versus, away = head.partition(" v ")
    if not versus:
        return "", "", tail.strip()
    return home.strip(), away.strip(), tail.strip()


@dataclass(frozen=True, slots=True)
class SourceReport:
    """Whether one source answered for this fixture, kept beside the features it produced.

    Carried separately from the features because "the weather call failed" and "the weather
    call succeeded and had no wind value for that hour" produce the same UNKNOWN feature and
    are different problems. The lane prints these; the model never sees them.
    """

    source: str
    answered: bool
    detail: str = ""

    def describe(self) -> str:
        return f"{self.source}: {'answered' if self.answered else 'silent'} — {self.detail}"


def strength_features(
    home: str,
    away: str,
    strengths: Mapping[str, Mapping[str, float]],
    *,
    aliases: Mapping[str, str] | None = None,
    source: str = "football-data",
    refusal: str = "",
) -> tuple[tuple[Feature, ...], SourceReport]:
    """The four strength features, or four UNKNOWNs that say which team went unmatched."""

    names = ("home_attack_strength", "home_defence_strength",
             "away_attack_strength", "away_defence_strength")

    if refusal:
        return (tuple(Feature(n, UNKNOWN, source=source, detail=refusal) for n in names),
                SourceReport(source, False, refusal))

    lookup = {normalise_team(team): values for team, values in strengths.items()}
    resolved = dict(aliases or {})
    found = {}
    unmatched = []
    for side, team in (("home", home), ("away", away)):
        key = normalise_team(resolved.get(team, team))
        if key in lookup:
            found[side] = lookup[key]
        else:
            unmatched.append(team)

    if unmatched:
        detail = (
            f"{' and '.join(unmatched)} did not match any team in the league table. The "
            f"table has {', '.join(sorted(strengths)[:4])}"
            + ("..." if len(strengths) > 4 else "")
            + ". Matching is exact after normalisation on purpose — a fuzzy match that is "
              "right most of the time models the wrong team's goals with no signal that it "
              "did. Add an alias to the lane's `team_aliases` if these are the same club."
        )
        return (tuple(Feature(n, UNKNOWN, source=source, detail=detail) for n in names),
                SourceReport(source, False, detail))

    return (
        (Feature("home_attack_strength", KNOWN, found["home"]["attack"], source=source),
         Feature("home_defence_strength", KNOWN, found["home"]["defence"], source=source),
         Feature("away_attack_strength", KNOWN, found["away"]["attack"], source=source),
         Feature("away_defence_strength", KNOWN, found["away"]["defence"], source=source)),
        SourceReport(source, True, "both teams matched in the table"),
    )


def weather_features(
    venue: str,
    kickoff: str,
    *,
    venues: Any = None,
    opener: Any = None,
    now: datetime | None = None,
) -> tuple[tuple[Feature, ...], SourceReport]:
    """Conditions at the ground, or three UNKNOWNs saying why there are none."""

    from connectors.weather import READ, conditions_for
    from lib.http_retry import retrying_urlopen

    names = ("temperature_c", "wind_speed_kph", "precipitation_mm")
    if not venue:
        detail = ("no venue is known for this fixture, so no coordinates could be "
                  "resolved. Not a still evening — an unasked question")
        return (tuple(Feature(n, UNKNOWN, source="open-meteo", detail=detail)
                      for n in names),
                SourceReport("open-meteo", False, detail))

    reading, _place = conditions_for(
        venue, kickoff, venues=venues,
        opener=opener or retrying_urlopen, now=now)
    return (reading.features(now),
            SourceReport("open-meteo", reading.status == READ,
                         reading.reason or f"{reading.status} for {venue}"))


def team_news_features(
    home: str,
    away: str,
    *,
    news: Any = None,
    now: datetime | None = None,
) -> tuple[tuple[Feature, ...], SourceReport]:
    """Key absences per side, which is UNKNOWN on almost every fixture and says so."""

    from connectors.teamnews import TeamNews

    if news is None:
        news = TeamNews.load(TEAM_NEWS)

    features = (news.feature(home, "home_key_absences", now=now),
                news.feature(away, "away_key_absences", now=now))
    answered = all(f.status == KNOWN for f in features)
    return features, SourceReport(
        "team news (recorded by hand)", answered,
        "both sides recorded and current" if answered else
        "no free structured source exists for this; the book has one and this does not")


@dataclass(frozen=True, slots=True)
class GatheredEvidence:
    """An evidence bundle and the per-source account of how complete it is."""

    evidence: Evidence
    sources: tuple[SourceReport, ...] = ()

    def describe(self) -> str:
        return "\n".join([self.evidence.describe(), "  sources:"]
                         + [f"    {s.describe()}" for s in self.sources])


def gather(
    market: str,
    *,
    strengths: Mapping[str, Mapping[str, float]] | None = None,
    strengths_refusal: str = "",
    venue: str = "",
    aliases: Mapping[str, str] | None = None,
    venues: Any = None,
    news: Any = None,
    opener: Any = None,
    now: datetime | None = None,
    with_weather: bool = True,
) -> GatheredEvidence:
    """Everything known about one fixture, with each source's silence recorded.

    Pure in the sense that matters for testing: every source is injectable and the default
    for each is "not supplied", which produces UNKNOWN features rather than a network call.
    A test that had to stub HTTP to assert a refusal would be a test people stop writing.
    """

    home, away, kickoff = split_market(market)
    if not home or not away:
        detail = (f"{market!r} is not in the form 'Home v Away @ <iso>', so neither side "
                  f"could be identified. Nothing about this fixture was looked up")
        return GatheredEvidence(
            Evidence(market, kickoff=kickoff),
            (SourceReport("market name", False, detail),))

    features: list[Feature] = []
    reports: list[SourceReport] = []

    strength, report = strength_features(
        home, away, strengths or {}, aliases=aliases,
        refusal=strengths_refusal or ("" if strengths else
                                      "no league table was supplied to this lane"))
    features.extend(strength)
    reports.append(report)

    if with_weather:
        weather, report = weather_features(venue, kickoff, venues=venues, opener=opener,
                                           now=now)
        features.extend(weather)
        reports.append(report)

    absences, report = team_news_features(home, away, news=news, now=now)
    features.extend(absences)
    reports.append(report)

    return GatheredEvidence(
        Evidence(market, tuple(features), kickoff=kickoff), tuple(reports))


class StandingsCache:
    """Standings fetched once per run rather than once per fixture.

    A twenty-fixture matchday would otherwise ask football-data for the same table twenty
    times — well inside the free tier's ten-a-minute, and still twenty chances for one call
    to fail and produce a fixture whose evidence disagrees with its neighbours'. One table
    per competition per run means every fixture in a league is modelled against the same
    numbers, which is a property worth more than the requests saved.
    """

    def __init__(self, client: Any = None, competitions: Sequence[str] = ()) -> None:
        self.client = client
        self.competitions = tuple(competitions)
        self._strengths: dict[str, Mapping[str, Mapping[str, float]]] = {}
        self._refusals: dict[str, str] = {}
        self._loaded = False

    def load(self) -> None:
        from connectors.football_data import strengths_from

        if self._loaded or self.client is None:
            self._loaded = True
            return
        for competition in self.competitions:
            strengths, _rate, refusal = strengths_from(self.client.standings(competition))
            if refusal:
                self._refusals[competition] = refusal
            else:
                self._strengths[competition] = strengths
        self._loaded = True

    def for_team(self, home: str, away: str) -> tuple[dict, str]:
        """The first competition holding BOTH sides, or a refusal naming what was tried.

        Both, not either. A table containing the home side and not the away side would give
        one real strength and one unmatched — and the UNKNOWN that produces is correct but
        buried, where a refusal at this level says plainly that these two are not in the
        same competition anybody configured.
        """

        self.load()
        if self.client is None:
            return {}, ("no league-data client is configured, so no team strength was "
                        "retrieved. This is not a finding that the teams are average")
        wanted = {normalise_team(home), normalise_team(away)}
        for competition, strengths in self._strengths.items():
            if wanted <= {normalise_team(team) for team in strengths}:
                return dict(strengths), ""
        tried = ", ".join(self.competitions) or "no competition"
        refusals = "; ".join(f"{k}: {v}" for k, v in self._refusals.items())
        return {}, (
            f"neither {home} nor {away} was found together in any configured league table "
            f"({tried})." + (f" Refusals: {refusals}" if refusals else ""))


def assemble_evidence(
    market: str,
    *,
    settings: Mapping[str, Any],
    directory: Path,
    cache: StandingsCache | None = None,
    now: datetime | None = None,
) -> Evidence:
    """The lane's own reader: config in, one fixture's evidence out.

    Every source is optional and every absence is a stated UNKNOWN, so this never raises and
    never returns None. A lane with nothing configured still produces a bundle, and the
    model then reports UNPRICED naming exactly which features would have changed the answer
    — which is the most useful thing the lane can say before anybody has a key.
    """

    from connectors.teamnews import TeamNews
    from connectors.weather import VenueBook

    home, away, _ = split_market(market)
    if cache is None:
        cache = _cache_for(settings)

    strengths, refusal = cache.for_team(home, away) if home and away else ({}, "")
    venues = VenueBook.load(directory / VENUES.name)
    news = TeamNews.load(directory / TEAM_NEWS.name)

    return gather(
        market,
        strengths=strengths, strengths_refusal=refusal,
        venue=str((settings.get("venues") or {}).get(market, "")),
        aliases=settings.get("team_aliases") or {},
        venues=venues, news=news, now=now,
        with_weather=bool(settings.get("use_weather", True)),
    ).evidence


def _cache_for(settings: Mapping[str, Any]) -> StandingsCache:
    """One standings cache per configuration, built from a key that may not be there."""

    from connectors.football_data import FootballData

    competitions = tuple(settings.get("competitions") or ())
    if not competitions:
        return StandingsCache(None, ())
    client = FootballData.from_directory()
    return StandingsCache(client if client.is_configured else None, competitions)
