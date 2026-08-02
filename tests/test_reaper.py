"""A reaper that did not look is not a reaper that found nothing, and it never places.

The recurring defect at the level of a whole lane. A reaper whose source was down and a
reaper that scanned six books and found nothing both produce an empty list, and reporting
them alike is how a system convinces somebody the market is quiet when the pipeline is
broken.

The second property is the boundary: a reaper looks, screens, gates, authorises and sizes
without being asked, and stops. Everything upstream of placing is reversible and placing is
not, so it stays a deliberate act — and for the chain lane it is refused outright, whatever
the configuration says.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.reaper import (
    COULD_NOT_LOOK,
    INDETERMINATE,
    NOTHING_FOUND,
    READY,
    REFUSED,
    Harvest,
    Reaper,
    gate_findings,
)
from lib.thesis import Thesis


class Verdict:
    def __init__(self, verdict="SURFACED", stage="settlement equivalence"):
        self.verdict = verdict
        self.decided_by = type("S", (), {"name": stage})()


class Reading:
    def __init__(self, status):
        self.status = status

    def describe(self):
        return f"reading says {self.status}"


def thesis(limit=500.0):
    return Thesis(
        "Team A v Team B", "Ian McGuane", "worked example",
        ("the price can move", "a book can restrict"),
        "2026-08-02T19:00:00Z",
        (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds"),
        limit,
    )


def reaper(*, subjects=("Team A v Team B",), asked=5, answered=5, verdict="SURFACED",
           readings=(), thesis_value="use-default", sized="an instruction",
           look_raises=None, gates_raise=False, lane="arb", autonomous=False):
    def _look():
        if look_raises:
            raise look_raises
        return list(subjects), asked, answered

    def _gates(_subject):
        if gates_raise:
            raise RuntimeError("source unreachable")
        return list(readings)

    return Reaper(
        name="test", lane=lane, look=_look,
        screen=lambda _s: Verdict(verdict),
        gates=_gates,
        thesis_for=lambda _s: thesis() if thesis_value == "use-default" else thesis_value,
        size=lambda _s, _p: sized,
        autonomous_execution=autonomous,
    )


class TestNotLookingIsNotFindingNothing:
    def test_a_source_failure_is_could_not_look(self):
        harvests = reaper(look_raises=RuntimeError("feed down")).reap()

        assert harvests[0].status == COULD_NOT_LOOK

    def test_could_not_look_says_a_run_of_these_is_a_broken_pipeline(self):
        described = reaper(look_raises=RuntimeError("x")).reap()[0].describe()

        assert "did NOT look" in described
        assert "broken pipeline rather than a" in described

    def test_looking_and_finding_nothing_is_nothing_found(self):
        harvests = reaper(subjects=()).reap()

        assert harvests[0].status == NOTHING_FOUND

    def test_nothing_found_states_the_coverage_it_achieved(self):
        described = reaper(subjects=(), asked=5, answered=2).reap()[0].describe()

        assert "2 of 5 source(s) answered" in described
        assert "may exist at a source that did not answer" in described


class TestTheCascadeAndTheVetoBothStop:
    def test_a_refused_cascade_refuses_and_names_the_stage(self):
        harvest = reaper(verdict="REFUSED").reap()[0]

        assert harvest.status == REFUSED
        assert "settlement equivalence" in harvest.reason

    def test_an_incomplete_cascade_is_indeterminate_not_refused(self):
        assert reaper(verdict="INDETERMINATE").reap()[0].status == INDETERMINATE

    def test_a_blocking_gate_reading_refuses_even_with_a_valid_thesis(self):
        harvest = reaper(readings=(Reading("SETTLEMENT_MISMATCH"),)).reap()[0]

        assert harvest.status == REFUSED

    def test_gates_that_could_not_be_RUN_are_indeterminate_not_clean(self):
        """None, not an empty list. A gate that did not run has not been passed."""

        assert reaper(gates_raise=True).reap()[0].status == INDETERMINATE

    def test_no_thesis_refuses_however_clean_the_gates(self):
        assert reaper(thesis_value=None).reap()[0].status == REFUSED


class TestAnUnassessedGateBlocks:
    @pytest.mark.parametrize("status", [
        "NOT_ASSESSED", "NO_VENUE_FOUND", "UNREADABLE", "SETTLEMENT_MISMATCH",
        "NOT_CONFIGURED", "INDETERMINATE",
    ])
    def test_third_states_become_blocking_findings(self, status):
        """Stricter than a board on purpose: with no seats to weigh an unassessed gate,
        it has to stop things on its own or it stops nothing at all."""

        assert gate_findings([Reading(status)])[0]["severity"] == "SEV-2"

    def test_a_clean_reading_produces_no_finding(self):
        assert gate_findings([Reading("ASSESSED")]) == []

    def test_the_finding_records_that_no_board_was_convened(self):
        assert "no board convened" in gate_findings([Reading("UNREADABLE")])[0]["source"]


class TestReadyStopsBeforeMoney:
    def test_a_clean_run_is_ready_and_carries_the_instruction(self):
        harvest = reaper().reap()[0]

        assert harvest.status == READY
        assert harvest.instruction == "an instruction"

    def test_ready_says_nothing_has_been_placed(self):
        assert "NOTHING HAS BEEN PLACED" in reaper().reap()[0].describe()

    def test_permitted_but_unsizeable_is_indeterminate_not_ready(self):
        harvest = reaper(sized=None).reap()[0]

        assert harvest.status == INDETERMINATE
        assert "a constraint was not measured" in harvest.reason

    def test_autonomous_execution_is_refused_outright_for_the_chain_lane(self):
        with pytest.raises(ValueError, match="irreversible"):
            reaper(lane="crypto", autonomous=True)

    def test_other_lanes_may_opt_in(self):
        assert reaper(lane="stocks", autonomous=True).autonomous_execution is True

    def test_it_defaults_to_off(self):
        assert reaper().autonomous_execution is False


class TestTheMissingAuditChainIsStated:
    def test_a_working_decision_says_no_board_was_convened(self):
        described = reaper().reap()[0].describe()

        assert "No board was convened" in described
        assert "a working decision, not a reviewed one" in described

    def test_nothing_found_does_not_carry_the_board_note(self):
        """There is no decision to qualify, so the note would be noise."""

        assert "No board was convened" not in reaper(subjects=()).reap()[0].describe()
