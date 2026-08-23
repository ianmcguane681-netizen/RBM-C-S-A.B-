"""A funded account is a survival problem, so the rulebook must be pessimistic on purpose.

Every property here is one that, got wrong in the flattering direction, produces a paper
model that passes challenges the real account would have failed. That is the failure mode
worth testing for: an over-strict rulebook wastes a fee, an over-generous one recommends
buying a seat that cannot be won.

Three carry the file. **The day's low decides**, because a day that was 6% down at 04:00
and closed flat has already lost the account whatever the close says. **An unreadable day
is not an uneventful one**, because inferring a low from a close is assuming the account
never dipped, on every single day. And **a payout can breach a winning account**, because
withdrawing money lowers the balance while some contracts leave the floor where the peak
put it — which is the term that turns a profitable strategy into a lost account with no
losing day in it.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from lib.funded import (
    BREACHED,
    DAILY_LOSS,
    INDETERMINATE,
    IN_PROGRESS,
    ON_INTRADAY_HIGH,
    PASSED,
    STATIC,
    TIME_EXPIRED,
    TOTAL_DRAWDOWN,
    TRAILING,
    TRAILING_LOCKED,
    AccountWalk,
    ChallengeRules,
    Day,
    evaluate,
    withdrawable,
)

START = date(2026, 9, 1)


def rules(**kw) -> ChallengeRules:
    kw.setdefault("name", "test")
    kw.setdefault("account_size", 10_000.0)
    kw.setdefault("max_total_drawdown_pct", 6.0)
    return ChallengeRules(**kw)


def days(*rows, traded: bool = True) -> list[Day]:
    """Rows of (open, low, close), one per consecutive day.

    The high is taken as the better of open and close, which is right for every test here
    except the ones about trailing ON the high — those build their days by hand, because
    the whole point of that term is that the high is not implied by the other three.
    """

    return [
        Day(START + timedelta(days=i), opened, max(opened, closed), low, closed,
            traded=traded)
        for i, (opened, low, closed) in enumerate(rows)
    ]


class TestTheDaysLowDecidesAndNeverItsClose:
    def test_a_day_that_dipped_through_the_floor_did_not_pass_on_its_close(self):
        # Down through 9,400 at some point in the day, back up past the target by the
        # close. The account was already closed when the profit arrived.
        verdict = evaluate(
            rules(profit_target_pct=8.0),
            days((10_000, 9_350, 10_900)),
        )
        assert verdict.status == BREACHED
        assert verdict.breached_rule == TOTAL_DRAWDOWN

    def test_a_day_that_dipped_through_the_daily_allowance_did_not_pass_on_its_close(self):
        verdict = evaluate(
            rules(profit_target_pct=8.0, max_daily_loss_pct=3.0),
            days((10_000, 9_690, 10_900)),
        )
        assert verdict.status == BREACHED
        assert verdict.breached_rule == DAILY_LOSS

    def test_the_same_close_without_the_dip_passes(self):
        # The only difference from the two cases above is the low, which is the point.
        verdict = evaluate(
            rules(profit_target_pct=8.0, max_daily_loss_pct=3.0),
            days((10_000, 9_980, 10_900)),
        )
        assert verdict.status == PASSED


class TestAnUnreadableDayIsNotAnUneventfulOne:
    def test_a_day_missing_its_low_is_indeterminate(self):
        verdict = evaluate(rules(profit_target_pct=8.0), [
            Day(START, 10_000.0, 10_900.0, None, 10_900.0),
        ])
        assert verdict.status == INDETERMINATE
        assert "low" in verdict.unreadable

    def test_it_is_indeterminate_even_when_the_close_would_have_passed(self):
        # The flattering direction is to take the close and call it a pass. Refusing to is
        # the whole property: a missing low is a missing measurement, not a calm day.
        verdict = evaluate(rules(profit_target_pct=1.0), [
            Day(START, 10_000.0, 10_500.0, None, 10_500.0),
        ])
        assert verdict.status != PASSED

    def test_the_refusal_names_the_day_and_what_is_missing(self):
        verdict = evaluate(rules(profit_target_pct=8.0), [
            Day(START, 10_000.0, 10_010.0, 9_990.0, 10_010.0),
            Day(START + timedelta(days=1), 10_010.0, None, None, None),
        ])
        assert verdict.status == INDETERMINATE
        assert "2026-09-02" in verdict.unreadable
        assert "low" in verdict.unreadable and "close" in verdict.unreadable

    def test_the_days_before_the_unreadable_one_are_still_counted(self):
        verdict = evaluate(rules(profit_target_pct=8.0), [
            Day(START, 10_000.0, 10_010.0, 9_990.0, 10_010.0),
            Day(START + timedelta(days=1), 10_010.0, None, None, None),
        ])
        assert verdict.days_elapsed == 1

    def test_no_days_at_all_is_indeterminate_not_in_progress(self):
        # An account nobody has recorded and an account that has not moved are different
        # facts, and only one of them is evidence of anything.
        verdict = evaluate(rules(profit_target_pct=8.0), [])
        assert verdict.status == INDETERMINATE


class TestWhichFloorAppliesIsATermNotADetail:
    def test_a_static_floor_does_not_rise_with_the_peak(self):
        r = rules(drawdown_basis=STATIC)
        assert r.total_floor(10_000) == pytest.approx(9_400)
        assert r.total_floor(20_000) == pytest.approx(9_400)

    def test_a_trailing_floor_rises_with_the_peak_without_limit(self):
        r = rules(drawdown_basis=TRAILING)
        assert r.total_floor(12_000) == pytest.approx(11_400)

    def test_a_locked_trail_stops_climbing_at_the_starting_balance(self):
        # The difference between TRAILING and TRAILING_LOCKED is the whole downside of a
        # long winning run: one of them ratchets a floor above your entry forever.
        r = rules(drawdown_basis=TRAILING_LOCKED)
        assert r.total_floor(10_200) == pytest.approx(9_600)
        assert r.total_floor(50_000) == pytest.approx(10_000)

    def test_trailing_on_the_intraday_high_is_harsher_than_on_the_close(self):
        # The identical three days, under the identical strategy. Day two spikes to 11,500
        # and gives it all back by the close. Trailing on the close never sees the spike;
        # trailing on the high raises the floor to 10,900 and day three's low is under it.
        series = [
            Day(START, 10_000.0, 10_800.0, 9_990.0, 10_800.0),
            Day(START + timedelta(days=1), 10_800.0, 11_500.0, 10_250.0, 10_300.0),
            Day(START + timedelta(days=2), 10_300.0, 10_400.0, 10_260.0, 10_390.0),
        ]
        on_close = evaluate(rules(drawdown_basis=TRAILING), series)
        on_high = evaluate(
            rules(drawdown_basis=TRAILING, trail_mark=ON_INTRADAY_HIGH), series
        )
        assert on_close.status == IN_PROGRESS
        assert on_high.status == BREACHED
        assert on_high.breached_rule == TOTAL_DRAWDOWN

    def test_the_verdict_names_which_floor_ended_it(self):
        # "BREACHED" alone trains a reader to skim. Which floor decides what to change.
        floor = evaluate(rules(max_daily_loss_pct=50.0), days((10_000, 9_300, 9_300)))
        daily = evaluate(rules(max_daily_loss_pct=3.0), days((10_000, 9_650, 9_650)))
        assert floor.breached_rule == TOTAL_DRAWDOWN
        assert daily.breached_rule == DAILY_LOSS


class TestAPayoutCanBreachAnAccountThatNeverLost:
    def winning_days(self, payout_every: int = 15, gain: float = 60.0, n: int = 20):
        """Days that never lose, withdrawing all profit every `payout_every`th.

        The cycle length is the whole test. Profit per cycle is 900 against a 600 floor
        allowance, so the peak before each payout is far enough above the starting balance
        that a floor left at that peak sits ABOVE the post-payout balance. Shorten the
        cycle below the allowance and the trap does not bite — which is itself worth
        knowing, and is why the payout schedule is a risk parameter rather than an
        administrative one.
        """

        out, equity = [], 10_000.0
        for i in range(n):
            close = equity + gain
            take = (close - 10_000.0) if (i + 1) % payout_every == 0 else 0.0
            out.append(Day(START + timedelta(days=i), equity, close, equity,
                           close - take, withdrawn=take))
            equity = close - take
        return out

    def test_a_frozen_floor_kills_a_winning_account(self):
        # Not one losing day in the series. The payout lands, the floor stays where the
        # peak left it, and the account is under its own floor the moment the money moves.
        verdict = evaluate(
            rules(drawdown_basis=TRAILING, payout_lowers_floor=False),
            self.winning_days(),
        )
        assert verdict.status == BREACHED
        assert verdict.breached_rule == TOTAL_DRAWDOWN

    def test_the_same_account_survives_when_the_floor_follows_the_money_out(self):
        verdict = evaluate(
            rules(drawdown_basis=TRAILING, payout_lowers_floor=True),
            self.winning_days(),
        )
        assert verdict.status == IN_PROGRESS
        assert verdict.withdrawn_gross > 0

    def test_a_short_payout_cycle_does_not_spring_the_trap(self):
        # Same rules, same strategy, payouts every fifth day instead of every fifteenth.
        # The peak never gets far enough above the starting balance for the frozen floor to
        # rise above it. The schedule is the risk, not the withdrawal.
        verdict = evaluate(
            rules(drawdown_basis=TRAILING, payout_lowers_floor=False),
            self.winning_days(payout_every=5),
        )
        assert verdict.status == IN_PROGRESS

    def test_a_static_floor_is_indifferent_to_the_payout_term(self):
        # Worth pinning: the trap is a property of trailing floors specifically, and a
        # reader who takes it as universal will refuse a perfectly safe contract.
        both = [
            evaluate(rules(drawdown_basis=STATIC, payout_lowers_floor=flag),
                     self.winning_days()).status
            for flag in (True, False)
        ]
        assert both == [IN_PROGRESS, IN_PROGRESS]

    def test_the_trader_take_is_the_split_less_the_fee(self):
        verdict = evaluate(
            rules(drawdown_basis=STATIC, profit_split_to_trader=0.8, fee=500.0),
            self.winning_days(),
        )
        assert verdict.trader_take == pytest.approx(
            verdict.withdrawn_gross * 0.8 - 500.0
        )


class TestPassingNeedsTimeServedAsWellAsProfit:
    def test_the_target_alone_does_not_pass_before_the_minimum_trading_days(self):
        verdict = evaluate(
            rules(profit_target_pct=8.0, min_trading_days=5),
            days((10_000, 10_000, 10_900)),
        )
        assert verdict.status == IN_PROGRESS

    def test_a_day_flat_in_cash_is_not_a_trading_day(self):
        # Firms count trading days, not calendar days, and a model that counts the wrong
        # one passes challenges a week before the real account is allowed to.
        series = [
            Day(START + timedelta(days=i), 10_000.0, 10_000.0, 10_000.0, 10_000.0, traded=False)
            for i in range(5)
        ] + days((10_000, 10_000, 10_900))
        series[-1] = Day(START + timedelta(days=5), 10_000.0, 10_900.0, 10_000.0, 10_900.0)
        verdict = evaluate(rules(profit_target_pct=8.0, min_trading_days=5), series)
        assert verdict.status == IN_PROGRESS
        assert verdict.days_traded == 1

    def test_the_deadline_ends_a_phase_that_has_a_target(self):
        verdict = evaluate(
            rules(profit_target_pct=8.0, max_calendar_days=3),
            days((10_000, 9_990, 10_010), (10_010, 10_000, 10_020),
                 (10_020, 10_010, 10_030)),
        )
        assert verdict.status == BREACHED
        assert verdict.breached_rule == TIME_EXPIRED

    def test_a_deadline_does_not_end_a_phase_that_has_no_target(self):
        # A funded account with no target and a calendar limit is a horizon somebody chose
        # to stop watching at. Reporting it as BREACHED would put a loss in the ledger that
        # nobody took.
        verdict = evaluate(
            rules(profit_target_pct=None, max_calendar_days=2),
            days((10_000, 9_990, 10_010), (10_010, 10_000, 10_020)),
        )
        assert verdict.status == IN_PROGRESS


class TestTermsThatCannotBeSatisfiedAreRefusedAtConstruction:
    def test_a_minimum_longer_than_the_deadline_is_refused(self):
        with pytest.raises(ValueError, match="never be passed"):
            rules(profit_target_pct=8.0, min_trading_days=30, max_calendar_days=10)

    @pytest.mark.parametrize("bad", [
        {"max_total_drawdown_pct": 0.0},
        {"max_total_drawdown_pct": 100.0},
        {"account_size": 0.0},
        {"profit_target_pct": -1.0},
        {"max_daily_loss_pct": 0.0},
        {"profit_split_to_trader": 0.0},
        {"day_boundary_utc_hour": 24},
    ])
    def test_a_nonsense_term_is_refused_rather_than_clamped(self, bad):
        with pytest.raises(ValueError):
            rules(**bad)


class TestUnconfirmedTermsSaySo:
    def test_an_unconfirmed_rulebook_announces_it_in_its_own_description(self):
        # A result computed from an assumed rulebook is a result about the assumption, and
        # the only defence against forgetting that is the report saying so every time.
        assert "UNCONFIRMED" in rules(profit_target_pct=8.0).describe()

    def test_a_confirmed_rulebook_does_not(self):
        assert "UNCONFIRMED" not in rules(
            profit_target_pct=8.0, terms_confirmed_by="Ian McGuane"
        ).describe()

    def test_whitespace_is_not_a_confirmation(self):
        assert not rules(terms_confirmed_by="   ").confirmed


class TestTheWalkIsTheOneImplementation:
    def test_a_walk_refuses_to_continue_past_its_verdict(self):
        # The simulator drives this day by day. Letting a settled account take another day
        # would generate paths in which a breached account went on to pass.
        walk = AccountWalk(rules(profit_target_pct=8.0))
        walk.step(Day(START, 10_000.0, 10_000.0, 9_300.0, 9_300.0))
        with pytest.raises(ValueError, match="already finished"):
            walk.step(Day(START + timedelta(days=1), 9_300.0, 11_000.0, 9_300.0, 11_000.0))

    def test_stepping_day_by_day_agrees_with_evaluating_the_series(self):
        series = days((10_000, 9_900, 10_400), (10_400, 10_100, 10_850))
        walk = AccountWalk(rules(profit_target_pct=8.0))
        stepped = None
        for day in series:
            stepped = walk.step(day) or stepped
        assert stepped is not None
        assert stepped.status == evaluate(rules(profit_target_pct=8.0), series).status


class TestWithdrawableIsProfitAndOnlyAboveTheThreshold:
    def test_nothing_is_withdrawable_at_a_loss(self):
        assert withdrawable(rules(), 9_500.0) == 0.0

    def test_nothing_is_withdrawable_below_the_threshold(self):
        assert withdrawable(rules(withdrawal_threshold_pct=2.0), 10_150.0) == 0.0

    def test_the_whole_profit_is_withdrawable_once_the_tap_opens(self):
        assert withdrawable(rules(withdrawal_threshold_pct=1.0), 10_250.0) == 250.0
