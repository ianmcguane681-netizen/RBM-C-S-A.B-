"""A lane that did not run is not a lane that found nothing, and the queue is the throttle.

Two properties carry this file.

The first is the recurring defect aimed at a scheduler. A crashed runner, a cadence not yet
elapsed, a lane held back and a clean run with no findings are four different facts, and a
dashboard reporting "0 alerts" for all four is worse than no dashboard.

The second is the part normally left out. Every lane produces work for a person, and a
person's capacity does not rise because more lanes were added. An orchestrator that fires
regardless converts a backlog into a bigger backlog and calls it throughput — so past the
limit, lanes that would add more are HELD. The system stops exactly when it would otherwise
look busiest.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.orchestrator import (
    COMPLETED,
    FAILED,
    FINDINGS,
    HELD,
    NOT_DUE,
    OPEN,
    UNCONFIGURED,
    Lane,
    Orchestrator,
)

NOW = datetime(2026, 8, 2, 12, 0, 0, tzinfo=timezone.utc)


def lane(name="watcher", cadence=3600, decisions=True, consumes=(), findings=(4,),
         unconfigured=()):
    return Lane(name, ("true",), cadence, decisions, tuple(consumes), tuple(findings),
                tuple(unconfigured))


def orchestrator(tmp_path, *lanes, limit=12):
    return Orchestrator(lanes or (lane(),), tmp_path / "state.json", queue_limit=limit)


class TestNotRunIsNotAResult:
    def test_a_lane_never_run_is_due(self, tmp_path):
        assert orchestrator(tmp_path).plan(now=NOW)[0].status == COMPLETED

    def test_a_lane_inside_its_cadence_is_not_due_and_says_when(self, tmp_path):
        book = orchestrator(tmp_path)
        book.record_run(book.lanes[0], 0, now=NOW)

        verdict = book.plan(now=NOW + timedelta(minutes=30))[0]

        assert verdict.status == NOT_DUE
        assert "next due" in verdict.reason

    def test_a_lane_past_its_cadence_runs_again(self, tmp_path):
        book = orchestrator(tmp_path)
        book.record_run(book.lanes[0], 0, now=NOW)

        assert book.plan(now=NOW + timedelta(hours=2))[0].status == COMPLETED

    def test_an_unreadable_state_file_refuses_to_run_anything(self, tmp_path):
        """Re-running everything would raise every decision already answered."""

        path = tmp_path / "state.json"
        path.write_text("{not json", encoding="utf-8")

        book = Orchestrator((lane(),), path)

        assert book.readable is False
        assert book.plan(now=NOW)[0].status == FAILED

    def test_an_unreadable_state_file_refuses_to_be_overwritten(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text("nonsense", encoding="utf-8")

        with pytest.raises(RuntimeError, match="raised again"):
            Orchestrator((lane(),), path).save()


class TestExitCodesAreThreeDifferentThings:
    def test_a_clean_exit_is_completed(self, tmp_path):
        book = orchestrator(tmp_path)

        assert book.record_run(book.lanes[0], 0).status == COMPLETED

    def test_a_declared_findings_code_is_not_a_failure(self, tmp_path):
        book = orchestrator(tmp_path)

        assert book.record_run(book.lanes[0], 4).status == FINDINGS

    def test_a_declared_unconfigured_code_is_not_a_failure_either(self, tmp_path):
        """preflight and scan_arb exit 2 meaning 'no source configured'. Found by running
        it: that was landing as FAILED, and the response to it is a credential rather than
        a debugging session."""

        book = orchestrator(tmp_path, lane(unconfigured=(2,)))

        assert book.record_run(book.lanes[0], 2).status == UNCONFIGURED

    def test_an_undeclared_nonzero_exit_is_a_failure(self, tmp_path):
        book = orchestrator(tmp_path)

        assert book.record_run(book.lanes[0], 99).status == FAILED


class TestTheQueueIsTheThrottle:
    def _fill(self, book, count):
        for index in range(count):
            book.raise_decision("watcher", f"subject-{index}", "?", now=NOW)

    def test_a_lane_producing_decisions_is_held_when_the_queue_is_full(self, tmp_path):
        book = orchestrator(tmp_path, lane(decisions=True), limit=3)
        self._fill(book, 3)

        assert book.plan(now=NOW)[0].status == HELD

    def test_the_hold_explains_that_more_output_is_not_more_throughput(self, tmp_path):
        book = orchestrator(tmp_path, lane(decisions=True), limit=1)
        self._fill(book, 1)

        assert "bigger backlog, not" in book.plan(now=NOW)[0].reason

    def test_a_lane_producing_no_decisions_still_runs_when_the_queue_is_full(self, tmp_path):
        """A report that asks nothing is exactly what somebody needs when the queue is deep."""

        book = orchestrator(tmp_path, lane("reporter", decisions=False), limit=1)
        book.raise_decision("other", "s", "?", now=NOW)

        assert book.plan(now=NOW)[0].status == COMPLETED

    def test_resolving_a_decision_releases_the_hold(self, tmp_path):
        book = orchestrator(tmp_path, lane(decisions=True), limit=1)
        raised = book.raise_decision("watcher", "s", "?", now=NOW)

        assert book.plan(now=NOW)[0].status == HELD
        book.resolve(raised.decision_id, "done", now=NOW)
        assert book.plan(now=NOW)[0].status == COMPLETED


class TestTheQueueDeduplicates:
    def test_the_same_subject_is_not_raised_twice(self, tmp_path):
        """A lane on a cadence re-observes the same standing item every cycle."""

        book = orchestrator(tmp_path)
        book.raise_decision("watcher", "monitor exited 4", "?", now=NOW)

        again = book.raise_decision("watcher", "monitor exited 4", "?", now=NOW)

        assert again is None
        assert len(book.open_decisions) == 1

    def test_a_resolved_subject_can_be_raised_again(self, tmp_path):
        """Seeing it after answering it means the condition genuinely recurred."""

        book = orchestrator(tmp_path)
        first = book.raise_decision("watcher", "s", "?", now=NOW)
        book.resolve(first.decision_id, "handled", now=NOW)

        assert book.raise_decision("watcher", "s", "?", now=NOW) is not None

    def test_a_different_subject_queues_separately(self, tmp_path):
        book = orchestrator(tmp_path)
        book.raise_decision("watcher", "a", "?", now=NOW)
        book.raise_decision("watcher", "b", "?", now=NOW)

        assert len(book.open_decisions) == 2


class TestChainingWaitsForItsInput:
    def test_a_lane_whose_dependency_never_ran_is_not_due(self, tmp_path):
        book = orchestrator(tmp_path, lane("builder", consumes=("researcher",)))

        verdict = book.plan(now=NOW)[0]

        assert verdict.status == NOT_DUE
        assert "never run" in verdict.reason

    def test_the_reason_says_it_would_run_over_no_input(self, tmp_path):
        book = orchestrator(tmp_path, lane("builder", consumes=("researcher",)))

        assert "clean result over no input" in book.plan(now=NOW)[0].reason

    def test_a_lane_runs_once_its_dependency_has(self, tmp_path):
        upstream, downstream = lane("researcher"), lane("builder", consumes=("researcher",))
        book = orchestrator(tmp_path, upstream, downstream)
        book.record_run(upstream, 0, now=NOW)

        assert book.plan(now=NOW)[1].status == COMPLETED


class TestTheQueueReportDoesNotOverclaim:
    def test_an_empty_queue_says_what_it_does_not_cover(self, tmp_path):
        text = orchestrator(tmp_path).describe_queue()

        assert "says nothing about lanes that did not" in text

    def test_a_full_queue_says_lanes_are_being_held(self, tmp_path):
        book = orchestrator(tmp_path, limit=1)
        book.raise_decision("watcher", "s", "q", now=NOW)

        assert "QUEUE FULL" in book.describe_queue()

    def test_decisions_survive_a_round_trip_and_runs_are_trimmed(self, tmp_path):
        book = orchestrator(tmp_path)
        book.raise_decision("watcher", "s", "q", now=NOW)
        for _ in range(600):
            book.record_run(book.lanes[0], 0, now=NOW)
        book.save()

        reloaded = Orchestrator((lane(),), tmp_path / "state.json")

        assert len(reloaded.open_decisions) == 1
        assert len(reloaded.runs) == 500
