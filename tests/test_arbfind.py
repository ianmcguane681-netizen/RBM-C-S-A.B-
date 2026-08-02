"""Discovery finds candidates. It must not find arbs, and it must not find them cheaply.

`lib/arb.py` verifies a position handed to it. This finds one, and the gap between those two
verbs is where the money is lost. Three properties keep the gap visible.

An aggregated quote is not a price you can bet: a feed returns odds, and a `Leg` refuses
construction without an available stake and a settlement rule. Defaulting either would let
a position be sized against a number nobody read, or slip past the gate that caught the only
real position this board has examined — positive margin, and the legs voided differently on
abandonment.

Two of three selections is not a cheap arb, it is a bet on the draw not happening.

And commission is per book and applies to winnings, which decides *which book wins* a
selection, not merely what the margin is afterwards.
"""
from __future__ import annotations

import pytest

from lib.arbfind import (
    ARB_CANDIDATE,
    INCOMPLETE_BOOK,
    INSUFFICIENT_QUOTES,
    NO_ARB,
    SINGLE_BOOK,
    Quote,
    best_per_selection,
    find_arb,
    scan_markets,
)

MARKET = "Team A v Team B @ 2026-08-09T14:00:00Z"
BOTH = ("Team A", "Team B")


def quote(book, selection, odds, commission=0.0, at="2026-08-02T16:00:00Z"):
    return Quote(book, MARKET, selection, odds, at, commission)


class TestACandidateIsNotAnArb:
    def test_an_under_100_combination_is_a_candidate_not_a_lock(self):
        found = find_arb(MARKET, BOTH, [
            quote("BookA", "Team A", 2.20), quote("BookB", "Team B", 2.20),
        ])

        assert found.status == ARB_CANDIDATE
        assert found.margin_pct == pytest.approx(9.0909, abs=1e-3)

    def test_both_preconditions_are_always_named_as_unread(self):
        found = find_arb(MARKET, BOTH, [
            quote("BookA", "Team A", 2.20), quote("BookB", "Team B", 2.20),
        ])

        assert len(found.unmet_preconditions) == 2
        assert "NOT AN ARB YET" in found.describe()

    def test_the_description_names_stake_and_settlement_as_the_gaps(self):
        text = find_arb(MARKET, BOTH, [
            quote("BookA", "Team A", 2.20), quote("BookB", "Team B", 2.20),
        ]).describe()

        assert "not liquidity" in text
        assert "no price source carries the terms" in text


class TestAKnownStakeRemovesOnePrecondition:
    """Adding an exchange has to be visibly worth more than adding a wider feed."""

    def _sized(self, a_stake, b_stake):
        return find_arb(MARKET, BOTH, [
            Quote("Betfair", MARKET, "Team A", 2.20, "2026-08-02T16:00:00Z",
                  available_stake=a_stake),
            Quote("Smarkets", MARKET, "Team B", 2.20, "2026-08-02T16:00:00Z",
                  available_stake=b_stake),
        ])

    def test_both_stakes_known_leaves_only_settlement_unread(self):
        found = self._sized(5_000.0, 250.0)

        assert len(found.unmet_preconditions) == 1
        assert "settlement" in found.unmet_preconditions[0]

    def test_the_smallest_stake_binds_and_is_named(self):
        found = self._sized(5_000.0, 250.0)

        assert found.stake_bound == pytest.approx(250.0)
        assert "size bound 250.00 at Smarkets" in found.describe()

    def test_one_unread_side_makes_the_whole_bound_unknown(self):
        """Not the minimum of the sides that happened to be readable."""

        from lib.arbfind import UNKNOWN_STAKE

        found = self._sized(5_000.0, UNKNOWN_STAKE)

        assert found.stake_bound == UNKNOWN_STAKE

    def test_the_sizeless_book_is_named_rather_than_the_gap_being_generic(self):
        from lib.arbfind import UNKNOWN_STAKE

        found = self._sized(5_000.0, UNKNOWN_STAKE)

        assert "available stake at Smarkets" in found.unmet_preconditions[0]
        assert "Betfair" not in found.unmet_preconditions[0]

    def test_a_discovery_never_produces_a_leg(self):
        """A Leg would imply a stake and a rule that nobody read."""

        found = find_arb(MARKET, BOTH, [
            quote("BookA", "Team A", 2.20), quote("BookB", "Team B", 2.20),
        ])

        from lib.arb import Leg

        assert not any(isinstance(q, Leg) for q in found.quotes)


class TestAnIncompleteBookIsNotAThinMargin:
    def test_a_missing_selection_refuses_rather_than_summing_what_is_there(self):
        """Two of three implies well under 100% and is a bet on the draw not happening."""

        three = ("Team A", "Draw", "Team B")

        found = find_arb(MARKET, three, [
            quote("BookA", "Team A", 2.20), quote("BookB", "Team B", 2.20),
        ])

        assert found.status == INCOMPLETE_BOOK

    def test_the_wording_says_what_backing_the_quoted_ones_would_be(self):
        found = find_arb(MARKET, ("Team A", "Draw", "Team B"), [
            quote("BookA", "Team A", 2.20), quote("BookB", "Team B", 2.20),
        ])

        assert "bet on the missing outcome not happening" in found.describe()

    def test_the_outcome_set_comes_from_the_caller_not_from_the_quotes(self):
        """Inferring it would make a market look complete exactly when a book failed."""

        found = find_arb(MARKET, ("Team A", "Draw", "Team B"), [
            quote("BookA", "Team A", 2.20), quote("BookB", "Team B", 2.20),
        ])

        assert found.selections_expected == ("Team A", "Draw", "Team B")

    def test_a_one_outcome_market_cannot_be_arbed(self):
        assert find_arb(MARKET, ("Only",), []).status == INSUFFICIENT_QUOTES


class TestCommissionDecidesWhichBookWins:
    def test_the_best_price_is_chosen_net_of_commission_not_gross(self):
        """3.00 on an exchange at 5% is worse than 2.95 at a bookmaker."""

        best = best_per_selection([
            quote("Exchange", "Team A", 3.00, commission=5.0),
            quote("Bookmaker", "Team A", 2.95),
        ])

        assert best["Team A"].book == "Bookmaker"

    def test_a_margin_that_survives_gross_can_die_net(self):
        gross = find_arb(MARKET, BOTH, [
            quote("A", "Team A", 2.05), quote("B", "Team B", 2.05),
        ])
        net = find_arb(MARKET, BOTH, [
            quote("A", "Team A", 2.05, commission=5.0),
            quote("B", "Team B", 2.05, commission=5.0),
        ])

        assert gross.status == ARB_CANDIDATE
        assert net.status == NO_ARB


class TestOrdinaryMarketsAreReportedAsOrdinary:
    def test_a_normal_book_is_no_arb_and_says_that_is_normal(self):
        found = find_arb(MARKET, BOTH, [
            quote("A", "Team A", 1.90), quote("B", "Team B", 1.90),
        ])

        assert found.status == NO_ARB
        assert "normal state of a market" in found.reason

    def test_one_book_pricing_both_sides_is_not_two_counterparties(self):
        found = find_arb(MARKET, BOTH, [
            quote("A", "Team A", 2.20), quote("A", "Team B", 2.20),
        ])

        assert found.status == SINGLE_BOOK
        assert "may void" in found.reason

    def test_a_single_book_can_be_allowed_deliberately(self):
        found = find_arb(MARKET, BOTH, [
            quote("A", "Team A", 2.20), quote("A", "Team B", 2.20),
        ], allow_single_book=True)

        assert found.status == ARB_CANDIDATE


class TestTheScanKeepsWhatItFoundNothingIn:
    def test_markets_yielding_nothing_are_retained_not_filtered(self):
        result = scan_markets({MARKET: BOTH}, [
            quote("A", "Team A", 1.90), quote("B", "Team B", 1.90),
        ])

        assert result.markets_examined == 1
        assert result.arbs == ()
        assert len(result.candidates) == 1

    def test_an_empty_result_says_it_covered_only_the_books_that_answered(self):
        text = scan_markets({MARKET: BOTH}, [
            quote("A", "Team A", 1.90), quote("B", "Team B", 1.90),
        ]).describe()

        assert "says nothing about a book that did not" in text

    def test_incomplete_markets_are_counted_separately_from_no_arb(self):
        result = scan_markets({MARKET: ("Team A", "Draw", "Team B")}, [
            quote("A", "Team A", 2.20), quote("B", "Team B", 2.20),
        ])

        assert len(result.incomplete) == 1
        assert "not a free one" in result.describe()

    def test_the_quote_spread_is_reported_when_legs_were_not_simultaneous(self):
        found = find_arb(MARKET, BOTH, [
            quote("A", "Team A", 2.20, at="2026-08-02T16:00:00Z"),
            quote("B", "Team B", 2.20, at="2026-08-02T16:04:00Z"),
        ])

        assert "never simultaneous" in found.describe()
