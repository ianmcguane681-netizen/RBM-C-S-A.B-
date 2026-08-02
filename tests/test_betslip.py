"""A slip you can execute from while a price is moving, with the abort plan already written.

Bookmakers have no betting API. bet365 and Sky Bet will not take an order from a program, so
a bookmaker-to-bookmaker arbitrage is executed by a person with two tabs open and the
deliverable is a slip rather than an adapter.

The property that earns its place is the one slips normally omit: the abort plan is written
BEFORE the first bet goes on. Once leg one is placed and leg two has vanished, the person
holding an unhedged position is under time pressure, disappointed, and exactly the wrong
person to be inventing a plan.
"""
from __future__ import annotations

import pytest

from lib.betslip import DO_NOT_PLACE, READY_TO_PLACE, BetSlip, SlipLeg, build_slip

RULE = "Settled on the official result."


def leg(book, selection, odds, maximum=0.0, rule=RULE):
    return SlipLeg(book, selection, odds, 0.0, maximum, rule)


def two_way(a=2.20, b=2.20, **kw):
    return build_slip("Team A v Team B",
                      [leg("bet365", "Team A", a), leg("Sky Bet", "Team B", b)], **kw)


class TestStakesAreATypedNumber:
    def test_every_outcome_returns_the_same_within_a_penny(self):
        slip = two_way(2.40, 2.10, bankroll_limit=1000.0)

        returns = [l.returns for l in slip.legs]

        assert max(returns) - min(returns) < 0.02

    def test_stakes_are_floored_so_a_book_cannot_refuse_them(self):
        slip = two_way(2.37, 2.13, bankroll_limit=1000.0)

        for slip_leg in slip.legs:
            assert slip_leg.stake == pytest.approx(round(slip_leg.stake, 2))

    def test_the_return_is_computed_from_floored_stakes_not_from_the_ratio(self):
        """Every earlier version of this arithmetic here over-reported by a fraction."""

        slip = two_way(2.40, 2.10, bankroll_limit=1000.0)

        staked = sum(l.stake for l in slip.legs)
        assert slip.guaranteed_return == pytest.approx(
            min(l.returns for l in slip.legs) - staked)

    def test_a_read_maximum_binds_the_whole_position(self):
        slip = build_slip("m", [
            leg("bet365", "A", 2.20, maximum=50.0), leg("Sky Bet", "B", 2.20),
        ], bankroll_limit=10_000.0)

        assert slip.legs[0].stake <= 50.0

    def test_an_unread_maximum_does_not_bind_and_the_leg_says_so(self):
        slip = two_way(2.40, 2.10, bankroll_limit=1000.0)

        assert "max stake NOT READ" in slip.describe()


class TestTheAbortPlanIsWrittenInAdvance:
    def test_the_exposure_is_the_whole_first_stake_not_the_margin(self):
        slip = two_way(2.40, 2.10, bankroll_limit=1000.0)

        assert slip.worst_case_if_a_leg_fails == pytest.approx(-slip.legs[0].stake)

    def test_the_slip_states_the_break_even_price_on_the_remaining_leg(self):
        slip = two_way(2.40, 2.10, bankroll_limit=1000.0)

        assert slip.break_even_odds_for(1) > 1.0
        assert "Break-even on the remaining leg" in slip.describe()

    def test_the_slip_gives_explicit_permission_to_take_the_loss(self):
        text = two_way(2.40, 2.10, bankroll_limit=1000.0).describe()

        assert "TAKE THE SMALL LOSS" in text
        assert "do not increase the stake to make it back" in text

    def test_it_says_why_the_advice_is_written_beforehand(self):
        text = two_way(2.40, 2.10, bankroll_limit=1000.0).describe()

        assert "not the advice you will want in the moment" in text


class TestOrderingIsNotArbitrary:
    def test_the_shortest_price_is_placed_first(self):
        """It is the one everyone else who saw this is also taking.

        Odds chosen to actually arb: 1.40/4.20/6.00 implies 111.9% and was correctly
        refused, which was the test premise being wrong rather than the code.
        """

        slip = build_slip("m", [
            leg("Sky Bet", "Draw", 4.00), leg("bet365", "A", 2.90), leg("Paddy", "B", 4.20),
        ], bankroll_limit=1000.0)

        assert slip.status == READY_TO_PLACE
        assert slip.legs[0].decimal_odds == 2.90


class TestConcentrationIsFlagged:
    def test_two_legs_at_one_book_are_named(self):
        """One restriction there takes out both legs, leaving the third unhedged."""

        slip = build_slip("m", [
            leg("bet365", "A", 2.40), leg("Sky Bet", "Draw", 4.20),
            leg("bet365", "B", 3.60),
        ], bankroll_limit=1000.0)

        assert slip.concentrated_books == ("bet365",)
        assert "takes out 2 legs at once" in slip.describe()

    def test_legs_spread_across_books_are_not_flagged(self):
        assert two_way(2.40, 2.10, bankroll_limit=1000.0).concentrated_books == ()


class TestItRefusesWhatIsNotWorthPlacing:
    def test_an_ordinary_market_is_do_not_place(self):
        slip = two_way(1.90, 1.90, bankroll_limit=1000.0)

        assert slip.status == DO_NOT_PLACE
        assert "normal state of a market" in slip.reason

    def test_a_margin_too_thin_to_be_worth_two_manual_bets_is_refused(self):
        slip = two_way(2.005, 2.005, bankroll_limit=1000.0, minimum_return_pct=1.0)

        assert slip.status == DO_NOT_PLACE
        assert "more risk than this pays for" in slip.reason

    def test_one_leg_is_not_an_arbitrage(self):
        slip = build_slip("m", [leg("bet365", "A", 2.20)], bankroll_limit=1000.0)

        assert slip.status == DO_NOT_PLACE

    def test_a_genuine_edge_is_ready_to_place(self):
        assert two_way(2.40, 2.10, bankroll_limit=1000.0).status == READY_TO_PLACE


class TestSettlementIsTheCheckItCannotDo:
    def test_a_missing_rule_is_flagged_as_the_check_that_catches_a_bet(self):
        slip = build_slip("m", [
            leg("bet365", "A", 2.40, rule=""), leg("Sky Bet", "B", 2.10),
        ], bankroll_limit=1000.0)

        text = slip.describe()

        assert "SETTLEMENT RULES WERE NOT READ" in text
        assert "looks like an arb and is a bet" in text

    def test_rules_present_on_every_leg_drops_the_warning(self):
        text = two_way(2.40, 2.10, bankroll_limit=1000.0).describe()

        assert "SETTLEMENT RULES WERE NOT READ" not in text

    def test_the_eye_check_always_names_non_runners_and_abandonment(self):
        text = two_way(2.40, 2.10, bankroll_limit=1000.0).describe()

        assert "non-runner and an abandonment" in text
