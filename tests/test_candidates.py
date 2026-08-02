"""The case against a score, written as tests rather than as an argument.

A weighted Opportunity Score was proposed: seven dimensions summed to a number out of a
hundred, surfaced above a threshold. The dimensions are right. The sum is the defect, and
the proof is a position this board actually failed — good on six of seven, fatal on the
seventh, and comfortably past any sane threshold.

Two properties are asserted here and neither is achievable with a scalar. A precondition
refuses regardless of how well everything else did. And an unmeasured stage blocks the
surface rather than averaging away — because under a score, unknown either counts as zero
(and real opportunities are missed) or drops out of the mean, which RAISES the score for
having looked at less.
"""
from __future__ import annotations

import pytest

from lib.candidates import (
    INDETERMINATE,
    PASSED,
    REFUSED,
    SURFACED,
    Stage,
    coverage_stage,
    cost_stage,
    freshness_stage,
    screen,
    seen_stage,
    settlement_stage,
    size_stage,
)
from lib.seen import SeenRegister, SeenVerdict, UNCHECKED, arb_identity


def good(name="fine"):
    return Stage(name, PASSED, detail="fine")


class TestAPreconditionIsNotADeduction:
    def test_one_fatal_stage_refuses_past_six_good_ones(self):
        """The worked example: liquidity, freshness, profit, commission, size, coverage all
        fine, and the legs settle differently on abandonment. A weighted sum surfaces it."""

        from lib.arb import SETTLEMENT_MISMATCH

        candidate = screen("Team A v Team B", [
            settlement_stage(SETTLEMENT_MISMATCH, "one voids, one stands if replayed"),
            good("liquidity"), good("freshness"), good("profit"),
            good("commission"), good("size"), good("coverage"),
        ])

        assert candidate.verdict == REFUSED
        assert candidate.decided_by.name == "settlement equivalence"

    def test_the_refusal_names_the_stage_rather_than_a_number(self):
        from lib.arb import SETTLEMENT_MISMATCH

        text = screen("x", [settlement_stage(SETTLEMENT_MISMATCH, "differ"), good()]).describe()

        assert "settlement equivalence" in text
        assert "no margin makes them one" in text

    def test_every_stage_is_reported_even_after_a_refusal(self):
        """A position refused on settlement AND stale AND illiquid is worth knowing about:
        the second pair says do not go looking for a fix."""

        from lib.arb import SETTLEMENT_MISMATCH

        candidate = screen("x", [
            settlement_stage(SETTLEMENT_MISMATCH, "differ"),
            freshness_stage(600, 60),
            size_stage(10, 1000),
        ])

        assert len(candidate.stages) == 3
        assert sum(s.verdict == REFUSED for s in candidate.stages) == 3


class TestUnmeasuredBlocksRatherThanAverages:
    def test_an_unmeasured_stage_does_not_surface(self):
        candidate = screen("x", [good(), good(), size_stage(0, 100), good()])

        assert candidate.verdict == INDETERMINATE

    def test_indeterminate_is_reported_apart_from_refused(self):
        """'The rules say no' and 'I could not read the rules' need different responses."""

        candidate = screen("x", [size_stage(0, 100)])

        assert candidate.verdict != REFUSED
        assert "has not been established" in candidate.describe()

    def test_a_known_refusal_outranks_an_unknown(self):
        candidate = screen("x", [size_stage(0, 100), cost_stage(1.0, 5.0)])

        assert candidate.verdict == REFUSED

    def test_zero_coverage_is_indeterminate_not_a_pass(self):
        """Nought of five books cannot establish these were the best prices."""

        assert coverage_stage(0, 5).verdict == INDETERMINATE

    def test_partial_coverage_passes_but_says_what_it_missed(self):
        stage = coverage_stage(2, 5)

        assert stage.verdict == PASSED
        assert "may exist at one that did not" in stage.detail

    def test_an_unmeasured_cost_is_not_a_zero_cost(self):
        assert cost_stage(1.0, -1).verdict == INDETERMINATE

    def test_an_unmeasured_price_age_is_not_a_fresh_price(self):
        assert freshness_stage(-1, 60).verdict == INDETERMINATE


class TestSurfacingClaimsNothingMore:
    def test_a_clean_cascade_surfaces(self):
        candidate = screen("x", [good(), good(), good()])

        assert candidate.verdict == SURFACED
        assert candidate.decided_by is None

    def test_surfacing_refuses_to_imply_a_ranking(self):
        text = screen("x", [good()]).describe()

        assert "there is no score" in text
        assert "not a ranking" in text


class TestTheSeenStageDoesNotOverreach:
    def test_seen_before_still_passes_because_a_standing_edge_is_still_real(self, tmp_path):
        register = SeenRegister(tmp_path / "seen.json")
        register.record("id", "2026-08-02T12:00:00Z")

        assert seen_stage(register.check("id")).verdict == PASSED

    def test_acting_twice_on_one_thing_is_refused(self, tmp_path):
        register = SeenRegister(tmp_path / "seen.json")
        register.record_action("id", "2026-08-02T12:00:00Z")

        stage = seen_stage(register.check("id"))

        assert stage.verdict == REFUSED
        assert "double a position already taken" in stage.detail

    def test_an_unreadable_register_blocks_rather_than_reporting_new(self):
        """The expensive direction: everything looks novel the day the file goes missing."""

        verdict = SeenVerdict(UNCHECKED, "id", reason="corrupt")

        assert seen_stage(verdict).verdict == INDETERMINATE
