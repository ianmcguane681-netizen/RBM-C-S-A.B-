"""The arithmetic is trivial. Everything that loses money is in "the same outcome".

Two books offering what looks like the same bet can settle differently: one voids on
abandonment and the other pays, one settles at 90 minutes and the other includes extra
time, one applies dead-heat reduction and the other does not. Both legs priced correctly,
and the lock is a coin flip.

So the tests here are mostly not about margins. They are about the four ways a
correct-looking arb is not one: the rules differ, the size is not there, the commission
eats it, or one leg can void and leave the other exposed.
"""
from __future__ import annotations

import pytest

from lib.arb import (
    INDETERMINATE,
    EquivalenceDeclaration,
    LOCK,
    NO_LOCK,
    SETTLEMENT_MISMATCH,
    UNFILLABLE,
    ArbFinding,
    Leg,
    evaluate,
)

RULE = "Settled on 90 minutes plus stoppage. Void if abandoned before full time."
OTHER_RULE = "Settled on the official result including extra time."


def leg(book, selection, odds, *, rule=RULE, max_stake=10_000.0, commission=0.0):
    return Leg(
        book=book, market="Match Odds: A v B", selection=selection, decimal_odds=odds,
        settlement_rule=rule, max_stake=max_stake, observed_at="2026-08-02T09:00:00Z",
        commission_pct=commission,
    )


class TestSettlementIsTheWholeGame:
    def test_differing_rules_are_refused_however_good_the_price(self):
        """A 20% margin under mismatched rules is not a 20% margin."""

        finding = evaluate([
            leg("BookA", "A", 3.0),
            leg("BookB", "B", 3.0, rule=OTHER_RULE),
        ])

        assert finding.status == SETTLEMENT_MISMATCH

    def test_the_refusal_explains_why_a_priced_pair_is_still_a_bet(self):
        described = evaluate([
            leg("BookA", "A", 3.0),
            leg("BookB", "B", 3.0, rule=OTHER_RULE),
        ]).describe()

        assert "settle under different rules" in described
        assert "a bet, not a lock" in described

    def test_whitespace_and_case_are_not_a_real_difference(self):
        finding = evaluate([
            leg("BookA", "A", 2.10),
            leg("BookB", "B", 2.10, rule="  SETTLED ON 90 minutes plus stoppage.   Void if abandoned before full time. "),
        ])

        assert finding.status == LOCK

    def test_a_leg_without_a_stated_rule_cannot_be_built(self):
        """Refused at construction, so no code path can compare an undeclared rule."""

        with pytest.raises(ValueError):
            Leg("BookA", "M", "A", 2.0, "   ", 100.0, "t")

    def test_different_markets_are_refused(self):
        one = leg("BookA", "A", 3.0)
        other = Leg("BookB", "Match Odds: C v D", "B", 3.0, RULE, 10_000.0, "t")

        assert evaluate([one, other]).status == SETTLEMENT_MISMATCH

    def test_the_quoted_rules_survive_into_the_description(self):
        """Quoted from each operator and never normalised: normalising is where two
        different rules silently become one."""

        described = evaluate([leg("BookA", "A", 2.10), leg("BookB", "B", 2.10)]).describe()

        assert "NOT normalised" in described
        assert "Void if abandoned" in described


# Verbatim from the operators' own dead-heat pages. Not one word in common, and on 100
# staked at 2.0 in a two-way dead heat both return exactly 100.
BETFAIR_DEAD_HEAT = (
    "A Dead Heat is calculated by dividing the stake proportionally between the number of "
    "winners in the event. So, in a two-way Dead Heat your return will be half of what it "
    "could have been."
)
BET365_DEAD_HEAT = (
    "Your original stake is divided by the number of selections tied for that exact "
    "position. The reduced stake is multiplied by the original odds. The portion of the "
    "stake allocated to the extra tied competitors is treated as lost."
)


class TestDifferentWordsCanMeanTheSameSettlement:
    """The flaw live evidence exposed.

    Comparing rule text for equality is right in principle -- no string comparison is
    entitled to decide two wordings mean the same thing -- and in practice refused nearly
    every real pair, which is useless and teaches its user to ignore the tool.

    So the judgement stays human and becomes a record instead of an assumption.
    """

    def mismatched(self):
        return [
            leg("Betfair", "A", 2.10, rule=BETFAIR_DEAD_HEAT),
            leg("bet365", "B", 2.10, rule=BET365_DEAD_HEAT),
        ]

    def test_differing_wording_still_refuses_by_default(self):
        assert evaluate(self.mismatched()).status == SETTLEMENT_MISMATCH

    def test_a_named_human_may_declare_them_equivalent(self):
        declaration = EquivalenceDeclaration(
            declared_by="Ian McGuane",
            reasoning="Both halve the effective stake in a two-way dead heat; 100 at 2.0 "
                      "returns 100 under either wording.",
            scenarios_checked=("two-way dead heat at 2.0",),
        )

        assert evaluate(self.mismatched(), equivalence=declaration).status == LOCK

    def test_an_agent_may_not_declare_equivalence(self):
        """Deciding two wordings settle alike is exactly the judgement automation is not
        entitled to make."""

        for actor in ("agent:mia", "ai:reviewer", "model:gpt", "automation:bot"):
            with pytest.raises(ValueError):
                EquivalenceDeclaration(actor, "they look the same")

    def test_a_declaration_without_reasoning_is_refused(self):
        with pytest.raises(ValueError):
            EquivalenceDeclaration("Ian McGuane", "   ")

    def test_the_declaration_is_reported_on_the_finding(self):
        declaration = EquivalenceDeclaration(
            "Ian McGuane", "equivalent on a two-way dead heat",
            scenarios_checked=("two-way dead heat", "abandonment"),
        )

        described = evaluate(self.mismatched(), equivalence=declaration).describe()

        assert "THE RULES DIFFER IN WORDING" in described
        assert "Ian McGuane declared them equivalent" in described
        assert "two-way dead heat; abandonment" in described

    def test_the_lock_is_stated_to_rest_on_that_judgement(self):
        """A waived mismatch must be distinguishable in the record from one that never
        existed."""

        declaration = EquivalenceDeclaration("Ian McGuane", "checked dead heat only")

        described = evaluate(self.mismatched(), equivalence=declaration).describe()

        assert "This lock rests on that judgement" in described
        assert "not checked above, it is a bet" in described

    def test_identical_wording_needs_no_declaration(self):
        finding = evaluate([leg("BookA", "A", 2.10), leg("BookB", "B", 2.10)])

        assert finding.status == LOCK
        assert "THE RULES DIFFER" not in finding.describe()


class TestALockIsOnlyALockWhileBothLegsStand:
    def test_the_void_exposure_is_reported_beside_the_profit(self):
        finding = evaluate([leg("BookA", "A", 2.10), leg("BookB", "B", 2.10)], target_stake=1000)

        assert finding.status == LOCK
        assert finding.worst_case_if_a_leg_voids < 0

    def test_the_exposure_is_the_whole_stake_on_the_larger_leg(self):
        """A void returns its own stake and settles nothing, so the loss is everything
        staked on the side that lost."""

        finding = evaluate([leg("BookA", "A", 2.10), leg("BookB", "B", 2.10)], target_stake=1000)

        assert finding.worst_case_if_a_leg_voids == pytest.approx(-max(finding.stakes))

    def test_the_description_states_the_guarantee_is_conditional(self):
        described = evaluate(
            [leg("BookA", "A", 2.10), leg("BookB", "B", 2.10)], target_stake=1000
        ).describe()

        assert "IF ONE LEG VOIDS" in described
        assert "only while both legs stand" in described


class TestSizeIsPartOfThePrice:
    def test_a_lock_that_cannot_be_filled_is_not_profit(self):
        finding = evaluate(
            [leg("BookA", "A", 2.10, max_stake=20.0), leg("BookB", "B", 2.10)],
            target_stake=1000,
        )

        assert finding.status == UNFILLABLE

    def test_unfillable_says_it_is_not_a_finding_of_profit(self):
        described = evaluate(
            [leg("BookA", "A", 2.10, max_stake=20.0), leg("BookB", "B", 2.10)],
            target_stake=1000,
        ).describe()

        assert "not a finding of profit" in described

    def test_without_a_target_the_stake_fits_the_smallest_book(self):
        finding = evaluate([leg("BookA", "A", 2.10, max_stake=100.0), leg("BookB", "B", 2.10)])

        assert finding.status == LOCK
        assert all(s <= l.max_stake + 1e-9 for l, s in zip(finding.legs, finding.stakes))

    def test_a_leg_with_no_available_stake_cannot_be_built(self):
        with pytest.raises(ValueError):
            Leg("BookA", "M", "A", 2.0, RULE, 0.0, "t")


class TestCommissionIsNotOptional:
    def test_an_exchange_commission_can_erase_the_edge(self):
        """A 1% paper margin on an exchange charging 5% of winnings was never an edge."""

        without = evaluate([leg("BookA", "A", 2.02), leg("BookB", "B", 2.02)])
        with_commission = evaluate([
            leg("BookA", "A", 2.02), leg("BookB", "B", 2.02, commission=5.0),
        ])

        assert without.status == LOCK
        assert with_commission.status == NO_LOCK

    def test_net_odds_reduce_only_the_winnings(self):
        priced = leg("Exchange", "A", 3.0, commission=5.0)

        assert priced.net_odds == pytest.approx(1.0 + 2.0 * 0.95)


class TestNoLockIsStatedPlainly:
    def test_an_overround_pair_is_no_lock(self):
        finding = evaluate([leg("BookA", "A", 1.90), leg("BookB", "B", 1.90)])

        assert finding.status == NO_LOCK

    def test_no_lock_does_not_present_an_average_as_a_guarantee(self):
        described = evaluate([leg("BookA", "A", 1.90), leg("BookB", "B", 1.90)]).describe()

        assert "on average" in described
        assert "not a guarantee either way" in described

    def test_indeterminate_is_not_a_finding_that_no_arb_exists(self):
        described = ArbFinding(INDETERMINATE, (), reason="odds feed unavailable").describe()

        assert "not a finding that no arb exists" in described

    def test_one_leg_is_not_an_arb(self):
        assert evaluate([leg("BookA", "A", 2.10)]).status == INDETERMINATE

    def test_two_legs_on_the_same_selection_are_refused(self):
        """Backing the same outcome twice is a bigger bet, not a hedge."""

        finding = evaluate([leg("BookA", "A", 2.10), leg("BookB", "A", 2.10)])

        assert finding.status == INDETERMINATE


class TestTheMathsItself:
    def test_stakes_equalise_the_return_across_outcomes(self):
        """Equal to within a penny of stake, not exactly: stakes are floored to whole
        pennies because that is what can be placed. `guaranteed_return` takes the minimum
        across outcomes, so the rounding can only ever be reported against the holder."""

        finding = evaluate([leg("BookA", "A", 2.50), leg("BookB", "B", 1.80)], target_stake=1000)

        returns = [s * l.net_odds for l, s in zip(finding.legs, finding.stakes)]

        assert returns[0] == pytest.approx(returns[1], abs=0.05)

    def test_the_guarantee_is_the_worst_outcome_not_the_average(self):
        finding = evaluate([leg("BookA", "A", 2.50), leg("BookB", "B", 1.80)], target_stake=1000)

        returns = [s * l.net_odds for l, s in zip(finding.legs, finding.stakes)]

        assert finding.guaranteed_return == pytest.approx(min(returns) - finding.total_stake)

    def test_the_return_exceeds_the_margin_and_the_two_are_not_the_same_number(self):
        """Margin is how far under 100% the book sits; return is profit over turnover, and
        it is always the larger. Reporting one as the other understates what a lock pays
        and, worse, invites the reverse mistake somewhere else."""

        finding = evaluate([leg("BookA", "A", 2.10), leg("BookB", "B", 2.10)], target_stake=1000)

        assert finding.guaranteed_return > 0
        assert finding.return_pct > finding.margin_pct
        assert finding.return_pct == pytest.approx(
            finding.margin_pct / (100 - finding.margin_pct) * 100, rel=1e-6
        )

    def test_no_forecast_or_expected_value_is_offered(self):
        """Expected value needs a model of what will happen. This has only what is priced."""

        for forbidden in ("expected_value", "probability", "edge_forecast", "ev", "win_rate"):
            assert forbidden not in ArbFinding.__dataclass_fields__
            assert not hasattr(ArbFinding, forbidden)
