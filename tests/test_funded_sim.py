"""A paper model earns trust by being checkable, and by refusing to flatter the strategy.

The output of this module is a number somebody may spend a fee on, so the properties worth
pinning are the ones that decide whether that number means anything.

**A seeded run reproduces.** A figure quoted in a document that cannot be regenerated from
the document is a figure nobody can argue with, and one nobody should act on.

**Cost is charged in units of risk, and it can reverse a winning win rate.** A strategy
that wins 55% of the time at even money is profitable on paper and loses money at Kraken's
spot taker fee against a tight stop. If the model did not reproduce that, it would
recommend the single most popular way of losing a funded account.

**Correlated days breach more often than independent ones.** Modelling a day as independent
coin flips is the largest error in amateur prop modelling: it understates the daily-loss
breach rate by more the more trades there are, and it does so precisely for the
high-frequency strategies that look best on the other metrics.

**Nothing the model generates is unreadable to the rulebook.** An INDETERMINATE path is a
defect in the generator, not an outcome of the strategy, and it must never be quietly
tallied as a failure.
"""
from __future__ import annotations

import random
from datetime import date

import pytest

from lib.funded import (
    DAILY_LOSS,
    TOTAL_DRAWDOWN,
)
from lib.funded_kraken import (
    CANDIDATES,
    BY_NAME,
    SPOT_TAKER_PCT,
    challenge_rules,
    confirm_terms,
    cost_r,
    funded_rules,
    sweep_payout_floor,
    sweep_risk,
)
from lib.funded_sim import StrategyProfile, play_day, resized, simulate


def profile(**kw) -> StrategyProfile:
    kw.setdefault("name", "test")
    kw.setdefault("description", "a profile assembled for one property")
    kw.setdefault("trades_per_day", 4)
    kw.setdefault("win_rate", 0.5)
    kw.setdefault("payoff_ratio", 1.3)
    kw.setdefault("risk_per_trade_pct", 0.8)
    kw.setdefault("cost_r", 0.05)
    return StrategyProfile(**kw)


class TestASeededRunReproduces:
    def run(self, seed):
        # Through the funded phase, so the compared figure is what the trader keeps rather
        # than the fee every path pays whatever happens.
        return simulate(
            challenge_rules(), profile(), funded=funded_rules(), paths=200, seed=seed
        )

    def test_the_same_seed_gives_the_same_answer(self):
        first, second = self.run(7), self.run(7)
        assert first.pass_rate == second.pass_rate
        assert first.net_takes == second.net_takes

    def test_a_different_seed_gives_a_different_answer(self):
        # Otherwise the seed is decorative and the reproducibility above proves nothing.
        assert self.run(7).net_takes != self.run(8).net_takes


class TestCostIsChargedInUnitsOfRiskAndDecidesWhatIsPossible:
    def test_a_round_trip_costs_more_the_tighter_the_stop(self):
        assert cost_r(0.4, SPOT_TAKER_PCT) > cost_r(4.0, SPOT_TAKER_PCT)

    def test_a_position_with_no_defined_risk_is_refused_rather_than_costed_at_zero(self):
        # Defaulting this to zero would report the cheapest possible trading for the most
        # dangerous possible position, which is the wrong answer in the worst direction.
        with pytest.raises(ValueError, match="undefined"):
            cost_r(0.0, SPOT_TAKER_PCT)

    def test_a_winning_win_rate_can_be_a_losing_strategy_after_cost(self):
        # 55% at even money is +0.10R a trade before cost and negative after it at spot
        # taker fees against a 0.4% stop. This is the arithmetic that refuses scalping.
        scalper = profile(win_rate=0.55, payoff_ratio=1.0, cost_r=cost_r(0.4, SPOT_TAKER_PCT))
        assert scalper.edge_r < 0

    def test_a_negative_edge_cannot_be_rescued_by_any_position_size(self):
        # The sweep exists to find an interior optimum. There is not one to find here, and
        # a model that produced one would be recommending a way to lose money slower.
        losing = profile(win_rate=0.55, payoff_ratio=1.0, cost_r=cost_r(0.4, SPOT_TAKER_PCT))
        swept = sweep_risk(losing, (0.1, 0.25, 0.5, 1.0, 2.0), paths=150, seed=3)
        assert all(campaign.pass_rate == 0.0 for _, campaign in swept)
        assert all(campaign.expected_net <= 0 for _, campaign in swept)

    def test_the_description_says_which_side_of_zero_the_edge_is(self):
        # "NEGATIVE after cost" in the output is what stops somebody tuning the win rate
        # of a strategy that arithmetic has already refused.
        losing = profile(win_rate=0.55, payoff_ratio=1.0, cost_r=1.4)
        assert "NEGATIVE after cost" in losing.describe()


class TestCorrelatedDaysBreachMoreOftenThanIndependentOnes:
    def campaign(self, rho):
        return simulate(
            challenge_rules(),
            profile(trades_per_day=6, win_rate=0.5, payoff_ratio=1.2,
                    intraday_correlation=rho, daily_stop_at=None),
            paths=1200, seed=11,
        )

    def test_the_daily_limit_is_breached_more_when_the_day_is_one_regime(self):
        assert (
            self.campaign(0.9).breaches.get(DAILY_LOSS, 0)
            > self.campaign(0.0).breaches.get(DAILY_LOSS, 0)
        )

    def test_the_lifetime_floor_is_too(self):
        assert (
            self.campaign(0.9).breaches.get(TOTAL_DRAWDOWN, 0)
            > self.campaign(0.0).breaches.get(TOTAL_DRAWDOWN, 0)
        )

    def test_and_the_pass_rate_falls_although_the_edge_is_identical(self):
        # Same win rate, same payoff, same cost, same size. Only the shape of the days
        # differs, and it is worth tens of percentage points of pass rate.
        assert self.campaign(0.9).pass_rate < self.campaign(0.0).pass_rate


class TestTheGeneratorNeverProducesADayTheRulebookCannotRead:
    @pytest.mark.parametrize("candidate", CANDIDATES, ids=lambda c: c.name)
    def test_no_path_comes_back_indeterminate(self, candidate):
        # An INDETERMINATE here is a defect in the generator. Counting it as a failure
        # would let a broken model report a plausible-looking pass rate.
        campaign = simulate(
            challenge_rules(), candidate, funded=funded_rules(), paths=120, seed=5
        )
        assert campaign.indeterminate == 0

    @pytest.mark.parametrize("candidate", CANDIDATES, ids=lambda c: c.name)
    def test_every_path_is_accounted_for(self, candidate):
        campaign = simulate(challenge_rules(), candidate, paths=120, seed=5)
        counted = (
            campaign.passed
            + sum(campaign.breaches.values())
            + campaign.indeterminate
            + campaign.unresolved
        )
        assert counted == campaign.paths

    def test_a_generated_day_brackets_its_own_open_and_close(self):
        # The low and high are running extremes of the intraday path, so they must contain
        # both ends of it. A low above the close would silently under-report drawdown.
        rng = random.Random(4)
        rules = challenge_rules()
        for _ in range(300):
            day = play_day(profile(), rules, date(2026, 9, 1), 10_000.0, rng)
            assert day.equity_low <= min(day.equity_open, day.equity_close)
            assert day.equity_high >= max(day.equity_open, day.equity_close)


class TestAStopYouHaveToBeAwakeForIsNotALimit:
    def test_a_strategy_that_holds_overnight_may_not_also_claim_a_daily_stop(self):
        with pytest.raises(ValueError, match="awake"):
            profile(holds_overnight=True, daily_stop_at=0.6)

    def test_holding_overnight_is_allowed_once_the_stop_is_given_up(self):
        assert profile(holds_overnight=True, daily_stop_at=None).holds_overnight

    def test_a_self_imposed_stop_reduces_daily_breaches(self):
        # The reason the field exists. Discipline inside the firm's allowance is worth more
        # than any of the strategy parameters, and the model should be able to show it.
        common = dict(trades_per_day=8, win_rate=0.5, payoff_ratio=1.2, risk_per_trade_pct=0.7)
        with_stop = simulate(
            challenge_rules(), profile(daily_stop_at=0.5, **common), paths=800, seed=13
        )
        without = simulate(
            challenge_rules(), profile(daily_stop_at=None, **common), paths=800, seed=13
        )
        assert (
            with_stop.breaches.get(DAILY_LOSS, 0) < without.breaches.get(DAILY_LOSS, 0)
        )


class TestSizeIsAQuestionAskedOfAStrategyNotARivalToIt:
    def test_resizing_changes_the_size_and_nothing_else(self):
        base = BY_NAME["momentum-swing"]
        smaller = resized(base, 0.4)
        assert smaller.risk_per_trade_pct == 0.4
        assert smaller.edge_r == base.edge_r
        assert smaller.win_rate == base.win_rate
        assert smaller.trades_per_day == base.trades_per_day

    def test_the_best_size_is_neither_the_smallest_nor_the_largest_tried(self):
        # Too small and the clock beats you, too large and the floor does. If the optimum
        # sat at an end of the range, the model would not be capturing the trade-off the
        # whole exercise is about.
        swept = sweep_risk(
            BY_NAME["momentum-swing"], (0.1, 0.5, 0.75, 1.0, 3.0), paths=600, seed=17
        )
        nets = [campaign.expected_net for _, campaign in swept]
        assert nets.index(max(nets)) not in (0, len(nets) - 1)

    def test_too_small_fails_the_clock_and_too_large_fails_the_floor(self):
        swept = dict(sweep_risk(BY_NAME["momentum-swing"], (0.1, 3.0), paths=600, seed=17))
        from lib.funded import TIME_EXPIRED

        assert swept[0.1].breaches.get(TIME_EXPIRED, 0) > swept[3.0].breaches.get(TIME_EXPIRED, 0)
        assert swept[3.0].breaches.get(TOTAL_DRAWDOWN, 0) > swept[0.1].breaches.get(TOTAL_DRAWDOWN, 0)


class TestThePayoutTermIsWorthMoneyAndTheModelPricesIt:
    def test_a_floor_that_does_not_follow_the_money_out_costs_the_trader(self):
        swept = dict(sweep_payout_floor(BY_NAME["cross-venue-arb"], paths=400, seed=19))
        assert swept[True].expected_net > swept[False].expected_net

    def test_and_it_shortens_the_life_of_the_funded_account(self):
        # The mechanism, not just the outcome: the accounts die sooner, which is what
        # distinguishes this from simply earning less per day.
        swept = dict(sweep_payout_floor(BY_NAME["cross-venue-arb"], paths=400, seed=19))
        import statistics

        assert (
            statistics.median(swept[False].funded_days)
            < statistics.median(swept[True].funded_days)
        )


class TestConfirmingTheTermsIsAReadingAndAReadingIsSomebodys:
    @pytest.mark.parametrize(
        "who", ["agent: claude", "ai: gpt", "model: opus", "automation: cron",
                "bot: helper", "system: init"],
    )
    def test_an_automation_cannot_confirm_the_terms(self, who):
        with pytest.raises(ValueError, match="automation"):
            confirm_terms(challenge_rules(), who)

    def test_an_empty_name_is_refused_rather_than_treated_as_confirmed(self):
        with pytest.raises(ValueError, match="name of the person"):
            confirm_terms(challenge_rules(), "   ")

    def test_a_person_may(self):
        confirmed = confirm_terms(challenge_rules(), "Ian McGuane")
        assert confirmed.confirmed
        assert "UNCONFIRMED" not in confirmed.describe()

    def test_confirming_changes_nothing_but_the_signature(self):
        # A confirmation is an attestation about the numbers, so it had better not alter
        # them on its way through.
        before = challenge_rules()
        after = confirm_terms(before, "Ian McGuane")
        assert after.account_size == before.account_size
        assert after.max_total_drawdown_pct == before.max_total_drawdown_pct
        assert after.profit_target_pct == before.profit_target_pct


class TestTheCampaignReportsWhatTheTraderActuallyKeeps:
    def test_the_net_is_the_split_less_every_fee_including_the_dead_accounts(self):
        # The mean is over accounts STARTED, not accounts funded. Averaging only the
        # survivors is how a challenge is made to look like a good trade.
        campaign = simulate(
            challenge_rules(fee=500.0), BY_NAME["cross-venue-arb"],
            funded=funded_rules(), paths=300, seed=23,
        )
        assert len(campaign.net_takes) == campaign.paths
        failures = [t for t in campaign.net_takes if t == -500.0]
        assert failures, "some accounts must have died having returned only the fee"

    def test_an_account_that_never_reaches_funding_returns_exactly_the_fee(self):
        campaign = simulate(
            challenge_rules(fee=500.0),
            profile(win_rate=0.55, payoff_ratio=1.0, cost_r=cost_r(0.4, SPOT_TAKER_PCT)),
            funded=funded_rules(), paths=100, seed=29,
        )
        assert campaign.expected_net == pytest.approx(-500.0)

    def test_beating_the_fee_is_rarer_than_passing(self):
        # An account can pass and then breach the funded phase before its first payout.
        # Reporting the pass rate as though it were the money outcome overstates the case.
        campaign = simulate(
            challenge_rules(), BY_NAME["momentum-swing"],
            funded=funded_rules(payout_lowers_floor=False), paths=500, seed=31,
        )
        assert campaign.profitable_rate <= campaign.pass_rate
