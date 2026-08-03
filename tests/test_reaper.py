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


def breakers(tmp_path, **kw):
    from lib.breakers import Breakers, Ringfence
    from lib.outcomes import OutcomeLedger

    return Breakers(Ringfence("arb", 1000.0, **kw), tmp_path / "b.json",
                    kill_switch=tmp_path / "HALT",
                    positions=OutcomeLedger(tmp_path / "outcomes.json"))


def armed(tmp_path, *, size=10.0, edge=2.0, book=None, **kw):
    """The same reaper with limits behind it — the only shape that can reach READY."""

    base = reaper(**kw)
    return Reaper(
        name=base.name, lane=base.lane, look=base.look, screen=base.screen,
        gates=base.gates, thesis_for=base.thesis_for, size=base.size,
        autonomous_execution=base.autonomous_execution,
        breakers=book if book is not None else breakers(tmp_path),
        measure=lambda _i: (size, edge),
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
    def test_a_clean_run_is_ready_and_carries_the_instruction(self, tmp_path):
        harvest = armed(tmp_path).reap()[0]

        assert harvest.status == READY
        assert harvest.instruction == "an instruction"

    def test_ready_says_nothing_has_been_placed(self, tmp_path):
        assert "NOTHING HAS BEEN PLACED" in armed(tmp_path).reap()[0].describe()

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
    def test_a_working_decision_says_no_board_was_convened(self, tmp_path):
        described = armed(tmp_path).reap()[0].describe()

        assert "No board was convened" in described
        assert "a working decision, not a reviewed one" in described

    def test_nothing_found_does_not_carry_the_board_note(self):
        """There is no decision to qualify, so the note would be noise."""

        assert "No board was convened" not in reaper(subjects=()).reap()[0].describe()


class TestTheBreakersAreTheLastGate:
    """A breaker needs a number, so it cannot run before sizing — which makes it last.

    That is also the right place for a different reason: everything before it asks whether
    this particular thing is a good idea, and the breakers ask whether the lane should be
    doing anything at all. A tripped breaker refuses a perfectly good candidate, and that
    is the point.
    """

    def test_a_reaper_with_no_breakers_cannot_reach_ready(self):
        """Remembering to check them separately works until the evening somebody forgets."""

        harvest = reaper().reap()[0]

        assert harvest.status == REFUSED
        assert "no circuit breakers are attached" in harvest.reason

    def test_a_clean_run_with_breakers_reaches_ready(self, tmp_path):
        assert armed(tmp_path).reap()[0].status == READY

    def test_the_kill_switch_refuses_a_perfectly_good_candidate(self, tmp_path):
        book = breakers(tmp_path)
        book.halt("stopping for the night")

        harvest = armed(tmp_path, book=book).reap()[0]

        assert harvest.status == REFUSED
        assert "kill switch" in harvest.reason

    def test_a_size_over_the_cap_is_refused_after_being_sized(self, tmp_path):
        harvest = armed(tmp_path, size=500.0).reap()[0]

        assert harvest.status == REFUSED
        assert "position size" in harvest.reason

    def test_an_implausible_edge_is_refused(self, tmp_path):
        assert "sanity bound" in armed(tmp_path, edge=40.0).reap()[0].reason

    def test_a_tripped_breaker_refuses_before_anything_is_carried_forward(self, tmp_path):
        """The lane stops as a whole. It does not get one more look at a good candidate."""

        book = breakers(tmp_path)
        book.record(-31.0)          # 3% of 1000

        harvest = armed(tmp_path, book=book).reap()[0]

        assert harvest.status == REFUSED
        assert "previously tripped" in harvest.reason

    def test_an_unmeasured_instruction_is_refused_not_waved_through(self, tmp_path):
        """No `measure` means size 0, and an unchecked size is not a permitted one."""

        base = armed(tmp_path)
        unmeasured = Reaper(
            name=base.name, lane=base.lane, look=base.look, screen=base.screen,
            gates=base.gates, thesis_for=base.thesis_for, size=base.size,
            breakers=base.breakers,
        )

        assert unmeasured.reap()[0].status == REFUSED

    def test_the_instruction_is_still_carried_so_the_refusal_is_readable(self, tmp_path):
        """You want to see WHAT was refused, not just that something was."""

        assert armed(tmp_path, size=500.0).reap()[0].instruction == "an instruction"


class TestSurfacingTheSameThingTwice:
    """`lib/seen.py` argues seen-before is not a refusal. That was right, and it assumed
    a person reading a report and deciding each time.

    It stops being right when the lane places by itself. A market re-surfacing every thirty
    minutes and placed on each pass is one opportunity taken eight times before lunch — the
    deployed-capital cap bounds that and does not prevent it. So the register still only
    ever REPORTS, and the reaper decides what that means for the mode it is in.
    """

    def _reaper(self, tmp_path, *, seen=(), autonomous=False, **kw):
        from lib.seen import SeenRegister

        register = SeenRegister.load(tmp_path / "seen.json")
        for identity, when in seen:
            register.record(identity, when)

        base = armed(tmp_path, lane="stocks" if autonomous else "arb")
        return Reaper(
            name=base.name, lane=base.lane, look=base.look, screen=base.screen,
            gates=base.gates, thesis_for=base.thesis_for, size=base.size,
            breakers=base.breakers, measure=base.measure,
            autonomous_execution=autonomous,
            register=register, identity=lambda _s: "the-same-thing", **kw)

    def _now(self, hours_ago=0.0):
        from datetime import datetime, timedelta, timezone

        return (datetime.now(timezone.utc)
                - timedelta(hours=hours_ago)).isoformat(timespec="seconds")

    def test_a_new_candidate_is_ready_and_says_so(self, tmp_path):
        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == READY
        assert "NEW" in harvest.describe()

    def test_a_repeat_under_owner_operating_is_still_ready(self, tmp_path):
        """A standing opportunity that is still there is still real, and you decide."""

        harvest = self._reaper(
            tmp_path, seen=[("the-same-thing", self._now())]).reap()[0]

        assert harvest.status == READY
        assert "SEEN_BEFORE" in harvest.describe()

    def test_a_repeat_under_autonomy_is_refused_as_the_same_opportunity(self, tmp_path):
        harvest = self._reaper(
            tmp_path, seen=[("the-same-thing", self._now())], autonomous=True).reap()[0]

        assert harvest.status == REFUSED
        assert "already surfaced" in harvest.reason
        assert "the same opportunity rather than a new one" in harvest.reason

    def test_the_refusal_says_what_owner_operating_would_have_done(self, tmp_path):
        harvest = self._reaper(
            tmp_path, seen=[("the-same-thing", self._now())], autonomous=True).reap()[0]

        assert "it would be reported and left to you" in harvest.reason

    def test_past_the_cooldown_an_autonomous_lane_may_take_it_again(self, tmp_path):
        harvest = self._reaper(
            tmp_path, seen=[("the-same-thing", self._now(hours_ago=48))],
            autonomous=True, cooldown_seconds=6 * 3600).reap()[0]

        assert harvest.status == READY

    def test_an_unreadable_register_refuses_even_under_owner_operating(self, tmp_path):
        """It HAS been written and its memory is gone, so everything looks new at once."""

        from lib.seen import SeenRegister

        base = armed(tmp_path)
        lane = Reaper(
            name=base.name, lane=base.lane, look=base.look, screen=base.screen,
            gates=base.gates, thesis_for=base.thesis_for, size=base.size,
            breakers=base.breakers, measure=base.measure,
            register=SeenRegister(tmp_path / "seen.json", readable=False,
                                  reason="JSONDecodeError"),
            identity=lambda _s: "x")

        harvest = lane.reap()[0]

        assert harvest.status == REFUSED
        assert "NOT established as new" in harvest.reason

    def test_a_register_that_raises_is_unchecked_rather_than_new(self, tmp_path):
        class Exploding:
            def check(self, _identity):
                raise RuntimeError("disk gone")

        base = armed(tmp_path)
        lane = Reaper(
            name=base.name, lane=base.lane, look=base.look, screen=base.screen,
            gates=base.gates, thesis_for=base.thesis_for, size=base.size,
            breakers=base.breakers, measure=base.measure,
            register=Exploding(), identity=lambda _s: "x")

        harvest = lane.reap()[0]

        assert harvest.status == REFUSED
        assert "has not been looked up at all" in harvest.reason

    def test_no_register_attached_is_ready_and_states_the_omission(self, tmp_path):
        """Never asked for is not the same as asked for and unavailable."""

        harvest = armed(tmp_path).reap()[0]

        assert harvest.status == READY
        assert harvest.seen is None
        assert "was not checked" in harvest.describe()


class TestCheckingWithoutRecordingWouldNeverFire:
    """The lookup working and nothing ever being written is the bug this repo keeps making.

    `Breakers.record()` was called by no production code for weeks while every control
    looked present. A seen register that is consulted and never written to is the same
    shape: the dedup reads NEW forever and the code that implements it all runs.
    """

    def _lane(self, tmp_path, **kw):
        from lib.seen import SeenRegister

        base = armed(tmp_path)
        kw.setdefault("lane", base.lane)
        return Reaper(
            name=base.name, look=base.look, screen=base.screen,
            gates=base.gates, thesis_for=base.thesis_for, size=base.size,
            breakers=base.breakers, measure=base.measure,
            register=SeenRegister.load(tmp_path / "seen.json"),
            identity=lambda _s: "the-same-thing", **kw)

    def test_a_ready_harvest_is_written_to_the_register(self, tmp_path):
        from lib.seen import SEEN_BEFORE, SeenRegister

        self._lane(tmp_path).reap()

        reloaded = SeenRegister.load(tmp_path / "seen.json")
        assert reloaded.check("the-same-thing").status == SEEN_BEFORE

    def test_the_second_run_sees_the_first(self, tmp_path):
        lane = self._lane(tmp_path)
        lane.reap()

        described = self._lane(tmp_path).reap()[0].describe()

        assert "SEEN_BEFORE" in described

    def test_an_autonomous_lane_refuses_its_own_repeat_on_the_next_run(self, tmp_path):
        """End to end: the whole point of the feature, through two actual runs."""

        first = self._lane(tmp_path, lane="stocks", autonomous_execution=True)
        assert first.reap()[0].status == READY

        second = self._lane(tmp_path, lane="stocks", autonomous_execution=True)

        assert second.reap()[0].status == REFUSED

    def test_a_refused_harvest_is_not_recorded(self, tmp_path):
        """The register means "offered to you", not "everything the lane ever looked at"."""

        from lib.seen import NEW, SeenRegister

        base = armed(tmp_path, verdict="REFUSED")
        lane = Reaper(
            name=base.name, lane=base.lane, look=base.look, screen=base.screen,
            gates=base.gates, thesis_for=base.thesis_for, size=base.size,
            breakers=base.breakers, measure=base.measure,
            register=SeenRegister.load(tmp_path / "seen.json"),
            identity=lambda _s: "the-same-thing")

        lane.reap()

        assert SeenRegister.load(tmp_path / "seen.json").check(
            "the-same-thing").status == NEW
