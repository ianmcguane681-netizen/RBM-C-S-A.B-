"""A forecast may be wrong. It may not be wrong in a way nothing in the output shows.

This repository refuses forecasts nearly everywhere and this lane is the exception, on the
precedent `lib.stocks_reaper.Criterion` already sets: a FORECAST is allowed when a named
human declares it. That makes the guards here load-bearing rather than decorative, because
everything else in the repository establishes facts and this thing predicts.

Four ways a mispricing model is wrong, and one group of tests for each.

**The vig was removed wrongly.** Four de-vig methods give four answers and they diverge
most at long odds, which is exactly where a model most often thinks it has found something.
The test that matters is not that each method computes correctly — it is that an edge
smaller than the disagreement between the methods is REFUSED as an artefact rather than
reported as a finding.

**An input was missing.** The founding defect, in the place a model is most tempted to
commit it. An absent injury report is not a fit squad and a timed-out weather call is not a
still evening. Every one of those becomes UNPRICED or a recorded assumption, never a
default.

**The model is wrong.** An edge inside the model's own stated error is FAIR, not "a small
edge". The subtle half is the arithmetic: the error is in probability points and the edge
is in percent of stake, and the first version of this file compared them directly — which
made the same three-point error look negligible at 1.5 and fatal at 15.0.

**Nobody ever checked.** Every other guard can be satisfied by a model that is simply bad.
A PAPER model produces a complete evaluation and cannot size anything, and only a named
person promotes it against a written account of a settled record.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.mispricing import (
    ADDITIVE,
    FAIR,
    KNOWN,
    LIVE,
    METHOD_DEPENDENT,
    METHODS,
    MISPRICED,
    PRICED,
    PROPORTIONAL,
    SHIN,
    STALE,
    UNKNOWN,
    UNPRICED,
    Evidence,
    Feature,
    Forecast,
    GoalsModel,
    MispricingModel,
    devig,
    find_edge,
    league_strengths,
    poisson_scoreline,
)
from lib.mispricing import INDETERMINATE as EDGE_INDETERMINATE

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
STRENGTHS = ("home_attack_strength", "home_defence_strength",
             "away_attack_strength", "away_defence_strength")


def model(**overrides) -> MispricingModel:
    settings = dict(
        name="poisson-v1", declared_by="Ian McGuane",
        reasoning="league scoring rates against the book's de-vigged price",
        requires=STRENGTHS, stated_error_pct=3.0, devig_method=PROPORTIONAL,
        expires_at="2099-01-01T00:00:00Z", max_exposure=50.0,
    )
    settings.update(overrides)
    return MispricingModel(**settings)


def evidence(**values) -> Evidence:
    base = {"home_attack_strength": 1.2, "home_defence_strength": 0.9,
            "away_attack_strength": 1.0, "away_defence_strength": 1.0}
    base.update(values)
    return Evidence("Arsenal v Chelsea", tuple(
        Feature(name, KNOWN, value, source="test") for name, value in base.items()
        if value is not None))


class TestOnlyAPersonMayDeclareAForecastingModel:
    def test_a_model_cannot_be_declared_by_automation(self):
        """The same guard `lib.stocks_reaper.Criterion` applies to a FORECAST criterion,
        and for the same reason: a prediction asserts something no source establishes."""

        with pytest.raises(ValueError, match="cannot declare a mispricing model"):
            model(declared_by="agent:backtester")

    def test_a_model_that_claims_no_error_cannot_be_constructed(self):
        """Without an error band there is no way to tell a real disagreement with the book
        from the model's own noise, and every edge it reported would be rounding."""

        with pytest.raises(ValueError, match="stated_error_pct must be positive"):
            model(stated_error_pct=0.0)

    def test_a_model_that_requires_nothing_cannot_be_constructed(self):
        """It could never be UNPRICED, so it would produce a number on a fixture nothing
        is known about — which is the one output this whole file exists to prevent."""

        with pytest.raises(ValueError, match="cannot be UNPRICED"):
            model(requires=())

    def test_live_without_a_written_record_is_refused(self):
        """LIVE is a claim that somebody checked. Accepting it from somebody who may not
        have is the difference between a guard and a formality."""

        with pytest.raises(ValueError, match="what was seen before it was promoted"):
            model(status=LIVE)

    def test_live_with_a_record_is_accepted_and_may_size(self):
        promoted = model(status=LIVE, promoted_on=(
            "142 settled predictions between 2026-03 and 2026-08; forecast probabilities "
            "within 2.1 points of observed frequency in every decile"))

        assert promoted.may_size is True
        assert model().may_size is False

    def test_a_paper_model_says_what_paper_means(self):
        assert "cannot size anything" in model().describe()


class TestRemovingTheBooksMarginIsAChoiceWithConsequences:
    def test_the_method_has_no_default(self):
        """A caller who did not choose is a caller who does not know which of four
        different numbers they are comparing their model against."""

        with pytest.raises(TypeError):
            devig({"HOME": 2.0, "AWAY": 2.0})

    def test_every_method_sums_to_one(self):
        book = {"HOME": 1.45, "DRAW": 4.60, "AWAY": 8.50}

        for method in METHODS:
            fair = devig(book, method=method)
            assert fair.status == PRICED
            assert sum(fair.probabilities.values()) == pytest.approx(1.0, abs=1e-6)

    def test_the_methods_disagree_and_the_spread_is_carried(self):
        """The disagreement is the point. A FairBook that reported one number would let a
        modelling choice be mistaken for a fact about the book."""

        fair = devig({"HOME": 1.45, "DRAW": 4.60, "AWAY": 8.50}, method=PROPORTIONAL)

        assert fair.sensitivity["AWAY"] > 0
        assert "methods disagree by" in fair.describe()

    def test_shin_puts_a_longshot_lower_than_proportional_does(self):
        """The favourite-longshot bias runs this way, and Shin is here for that rather
        than for elegance: without it every method would be biased alike and the spread
        would understate itself."""

        book = {"HOME": 1.25, "DRAW": 6.00, "AWAY": 15.0}

        assert (devig(book, method=SHIN).probabilities["AWAY"]
                < devig(book, method=PROPORTIONAL).probabilities["AWAY"])

    def test_a_book_that_implies_under_one_hundred_is_not_a_mispricing(self):
        """It is an arb, and lib/arbfind.py evaluates those. Reporting it here would put a
        lock and a forecast in the same report."""

        fair = devig({"HOME": 2.10, "AWAY": 2.10}, method=PROPORTIONAL)

        assert fair.status == UNPRICED
        assert "that is an arb" in fair.reason

    def test_a_one_sided_market_is_unpriced_rather_than_partly_priced(self):
        fair = devig({"HOME": 2.10}, method=PROPORTIONAL)

        assert fair.status == UNPRICED
        assert "no other side" in fair.reason

    def test_additive_going_negative_is_reported_rather_than_clipped(self):
        """A clipped zero is a certainty nobody computed. The assumption behind additive
        does not hold on a book like this and the honest answer is to say so."""

        # A heavy favourite, a real overround and a 500/1 outsider: the flat deduction is
        # larger than the outsider's whole implied probability.
        fair = devig({"HOME": 1.30, "DRAW": 3.80, "AWAY": 500.0}, method=ADDITIVE)

        assert fair.status == UNPRICED
        assert "does not hold here" in fair.reason

    def test_the_same_book_still_prices_under_a_method_whose_assumption_holds(self):
        """The refusal is about ADDITIVE on this book, not about the book. Reporting it as
        an unpriceable market would hide a perfectly usable proportional answer."""

        book = {"HOME": 1.30, "DRAW": 3.80, "AWAY": 500.0}

        assert devig(book, method=PROPORTIONAL).status == PRICED


class TestAnAbsentInputIsNeverADefault:
    def test_a_known_feature_with_no_value_cannot_be_constructed(self):
        """The combination by which an absence acquires a status saying otherwise."""

        with pytest.raises(ValueError, match="KNOWN with no value"):
            Feature("wind_speed_kph", KNOWN, None)

    def test_an_unknown_feature_carrying_a_value_cannot_be_constructed(self):
        """A stale or unknown feature must not hand a caller something to use anyway."""

        with pytest.raises(ValueError, match="must not hand a caller something"):
            Feature("wind_speed_kph", UNKNOWN, 12.0)

    def test_a_missing_required_feature_is_unpriced_and_names_it(self):
        thin = Evidence("Arsenal v Chelsea", (
            Feature("home_attack_strength", KNOWN, 1.2),))

        forecast = GoalsModel().forecast(model(), thin)

        assert forecast.status == UNPRICED
        assert set(forecast.missing) == set(STRENGTHS) - {"home_attack_strength"}

    def test_an_unpriced_forecast_says_it_is_not_a_forecast_of_an_even_market(self):
        forecast = GoalsModel().forecast(model(), Evidence("x"))

        assert "nothing was forecast" in forecast.describe()

    def test_a_stale_feature_is_not_usable(self):
        """Read-and-old and never-read call for different actions from a person, and
        neither of them is 'use it anyway'."""

        stale = Feature("wind_speed_kph", STALE, detail="issued nine hours ago")

        assert stale.usable is False
        assert Evidence("x", (stale,)).value("wind_speed_kph") is None


class TestEveryAdjustmentNotAppliedIsCarriedOutWithTheForecast:
    def test_absent_team_news_is_recorded_as_an_assumption_not_absorbed(self):
        """The largest real effect here and the worst-sourced. A forecast that silently
        assumed a fit squad would be systematically wrong against a book that knows."""

        forecast = GoalsModel().forecast(model(), evidence())

        assumed = " ".join(forecast.assumptions)
        assert "forecast as fully fit" in assumed
        assert "The book is not making that assumption" in assumed

    def test_absent_weather_is_recorded_as_an_assumption(self):
        forecast = GoalsModel().forecast(model(), evidence())

        assert any("no wind reading" in a for a in forecast.assumptions)

    def test_a_known_high_wind_lowers_both_expected_goal_counts(self):
        calm = GoalsModel().forecast(model(), evidence())
        windy = GoalsModel().forecast(model(), Evidence(
            "Arsenal v Chelsea",
            evidence().features + (Feature("wind_speed_kph", KNOWN, 45.0),)))

        # Fewer goals means a higher draw probability at these strengths.
        assert windy.probabilities["DRAW"] > calm.probabilities["DRAW"]
        assert not any("no wind reading" in a for a in windy.assumptions)

    def test_key_absences_are_capped_so_a_long_list_cannot_zero_a_team(self):
        """A fourth and fifth absentee do not keep subtracting linearly, and without the
        cap a long injury list produces a team that cannot score."""

        many = GoalsModel().forecast(model(), Evidence(
            "Arsenal v Chelsea",
            evidence().features + (Feature("home_key_absences", KNOWN, 11.0),)))

        assert many.probabilities["HOME"] > 0.05

    def test_rest_is_applied_on_the_difference_rather_than_the_absolute(self):
        """Both sides on three days' rest is an ordinary midweek round. Only the
        asymmetry shows up, so only the gap is used."""

        engine, declared = GoalsModel(), model()
        both_tired = engine.forecast(declared, Evidence("x", evidence().features + (
            Feature("home_rest_days", KNOWN, 3.0),
            Feature("away_rest_days", KNOWN, 3.0))))
        neither_tired = engine.forecast(declared, Evidence("x", evidence().features + (
            Feature("home_rest_days", KNOWN, 7.0),
            Feature("away_rest_days", KNOWN, 7.0))))

        assert both_tired.probabilities == pytest.approx(neither_tired.probabilities)


class TestTheScorelineArithmetic:
    def test_the_three_outcomes_sum_to_one(self):
        """The truncated Poisson tail is redistributed rather than discarded. Discarded,
        the three sum to slightly under one — and a probability compared against a book
        price is a comparison where "slightly under" is a free edge."""

        assert sum(poisson_scoreline(2.4, 1.9).values()) == pytest.approx(1.0)

    def test_a_stronger_side_is_favoured(self):
        strong = poisson_scoreline(2.2, 0.8)

        assert strong["HOME"] > strong["AWAY"]

    def test_equal_expectations_give_a_symmetric_market(self):
        even = poisson_scoreline(1.4, 1.4)

        assert even["HOME"] == pytest.approx(even["AWAY"])


class TestAnEdgeMustClearTheDoubtInItsOwnUnits:
    def _fair(self, method=PROPORTIONAL):
        return devig({"HOME": 1.45, "DRAW": 4.60, "AWAY": 8.50}, method=method)

    def _edge(self, probability, odds=8.50, **kw):
        return find_edge(
            model=model(**kw), forecast=Forecast(PRICED, "x", {"AWAY": probability}),
            fair=self._fair(), selection="AWAY", book="Sky Bet", decimal_odds=odds)

    def test_the_doubt_band_is_converted_into_percent_of_stake(self):
        """The bug this property exists for. Three points of model error is 4.5% of stake
        at 1.5 and 24% at 8.0, and comparing points against percent directly made the same
        model look strict on favourites and reckless on longshots."""

        long_shot = self._edge(0.20, odds=8.50)
        short = self._edge(0.80, odds=1.50)

        assert long_shot.doubt_band_pct == pytest.approx(3.0 * long_shot.net_odds)
        assert short.doubt_band_pct == pytest.approx(3.0 * short.net_odds)
        assert long_shot.doubt_band_pct > short.doubt_band_pct

    def test_an_edge_inside_the_model_error_is_fair_not_a_small_edge(self):
        edge = self._edge(0.125)

        assert edge.status == FAIR
        assert edge.expected_value_pct > 0
        assert "no edge that this model is entitled to claim" in edge.describe()

    def test_an_edge_clearing_the_band_is_mispriced_and_says_it_is_a_bet(self):
        edge = self._edge(0.20)

        assert edge.status == MISPRICED
        assert edge.survives_doubt is True
        assert "not a lock" in edge.describe()

    def test_an_edge_smaller_than_the_devig_spread_is_an_artefact(self):
        """A model with a tiny stated error still cannot claim an edge that another de-vig
        method would not have found. The refusal names the arithmetic rather than the
        model, because that is where a person would go to check it."""

        edge = find_edge(
            model=model(stated_error_pct=0.001),
            # Just past break-even at 8.5 (0.1176), and inside the 4.6% of stake that the
            # de-vig spread alone is worth at these odds.
            forecast=Forecast(PRICED, "x", {"AWAY": 0.120}),
            fair=self._fair(), selection="AWAY", book="Sky Bet", decimal_odds=8.50)

        assert edge.status == METHOD_DEPENDENT
        assert "artefact of how the margin was removed" in edge.describe()

    def test_the_model_agreeing_with_the_book_is_fair(self):
        assert self._edge(0.05).status == FAIR

    def test_an_unpriced_forecast_is_indeterminate_rather_than_fair(self):
        """"I could not price it" and "I priced it and the book is right" are different
        facts, and merging them reports a fair market that nobody assessed."""

        edge = find_edge(
            model=model(), forecast=Forecast(UNPRICED, "x", reason="no strengths"),
            fair=self._fair(), selection="AWAY", book="b", decimal_odds=8.5)

        assert edge.status == EDGE_INDETERMINATE
        assert "not a finding that the price is fair" in edge.describe()

    def test_an_expired_model_is_indeterminate(self):
        """A forecasting method is a claim about a period. Past it nobody has said it
        still holds, and the direction that stops is the direction to be wrong in."""

        expired = model(expires_at=(NOW - timedelta(days=1)).isoformat())
        edge = find_edge(
            model=expired, forecast=Forecast(PRICED, "x", {"AWAY": 0.5}),
            fair=self._fair(), selection="AWAY", book="b", decimal_odds=8.5)

        assert edge.status == EDGE_INDETERMINATE
        assert "expired" in edge.reason

    def test_a_selection_only_one_side_prices_is_indeterminate(self):
        edge = find_edge(
            model=model(), forecast=Forecast(PRICED, "x", {"HOME": 0.5}),
            fair=self._fair(), selection="AWAY", book="b", decimal_odds=8.5)

        assert edge.status == EDGE_INDETERMINATE
        assert "not both talking about" in edge.reason

    def test_commission_is_taken_before_the_edge_is_judged(self):
        """The most common way a paper edge evaporates, and it applies to a single bet on
        an exchange exactly as it does to an arb leg."""

        gross = find_edge(model=model(), forecast=Forecast(PRICED, "x", {"AWAY": 0.20}),
                          fair=self._fair(), selection="AWAY", book="b",
                          decimal_odds=8.5)
        net = find_edge(model=model(), forecast=Forecast(PRICED, "x", {"AWAY": 0.20}),
                        fair=self._fair(), selection="AWAY", book="b",
                        decimal_odds=8.5, commission_pct=5.0)

        assert net.expected_value_pct < gross.expected_value_pct


class TestLeagueStrengths:
    def test_a_team_with_no_games_is_omitted_rather_than_called_average(self):
        """A promoted side in August has no rate, and calling it 1.0 is the modelling
        equivalent of `or 0.0`."""

        strengths, _ = league_strengths([
            {"team": "A", "played": 10, "goals_for": 15, "goals_against": 10},
            {"team": "B", "played": 10, "goals_for": 10, "goals_against": 15},
            {"team": "New", "played": 0, "goals_for": 0, "goals_against": 0},
        ])

        assert set(strengths) == {"A", "B"}

    def test_strengths_are_relative_to_the_league_so_average_is_one(self):
        strengths, rate = league_strengths([
            {"team": "A", "played": 10, "goals_for": 12, "goals_against": 12},
            {"team": "B", "played": 10, "goals_for": 12, "goals_against": 12},
        ])

        assert rate == pytest.approx(1.2)
        assert strengths["A"]["attack"] == pytest.approx(1.0)

    def test_an_empty_table_produces_no_strengths_and_no_rate(self):
        assert league_strengths([]) == ({}, 0.0)
