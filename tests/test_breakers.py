"""The failure mode is not one bad decision. It is four hundred of them before anybody looks.

Rate of error matters more than probability of error once nobody is watching, so every
control here is aimed at the rate rather than at the call.

Three properties carry the file. A breaker that cannot be EVALUATED trips, because an
unknown limit is not a limit and the cost of continuing wrongly is unbounded while the cost
of stopping wrongly is a delay. A tripped breaker does not reset itself, because a strategy
that lost four in a row and resumed at midnight has learned nothing. And the kill switch is
a file, because the mechanism that has to work when everything else has not should be the
simplest one available.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.breakers import (
    ARMED,
    BLOCKED,
    PERMITTED,
    TRIPPED,
    Breakers,
    Outcome,
    Ringfence,
)


def fence(**kw):
    return Ringfence("arb", kw.pop("balance", 1000.0), **kw)


def breakers(tmp_path, ring=None, **kw):
    from lib.outcomes import OutcomeLedger

    kw.setdefault("positions", OutcomeLedger(tmp_path / "outcomes.json"))
    return Breakers(ring or fence(), tmp_path / "breakers.json",
                    kill_switch=tmp_path / "HALT", **kw)


def ok(tmp_path, **kw):
    """A check that would pass but for whatever the test is exercising."""

    return breakers(tmp_path, **kw).check(proposed_size=10.0, claimed_edge_pct=2.0)


class TestTheKillSwitchIsAFile:
    def test_its_presence_blocks_everything(self, tmp_path):
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")

        assert ok(tmp_path).verdict == BLOCKED

    def test_no_other_condition_is_consulted_once_it_exists(self, tmp_path):
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")

        decision = ok(tmp_path)

        assert decision.blocked_by == ("kill switch",)
        assert "no other condition is consulted" in decision.checks[0].detail

    def test_anything_can_create_it(self, tmp_path):
        book = breakers(tmp_path)

        book.halt("phone, no terminal")

        assert (tmp_path / "HALT").exists()
        assert book.check(proposed_size=10.0).verdict == BLOCKED

    def test_absent_it_does_not_block(self, tmp_path):
        assert ok(tmp_path).verdict == PERMITTED


class TestUnknownIsNotWithinLimits:
    def test_unreadable_state_blocks_rather_than_passing(self, tmp_path):
        """Fail closed: an unknown daily loss is not a satisfied daily loss limit."""

        (tmp_path / "breakers.json").write_text("{not json", encoding="utf-8")

        decision = breakers(tmp_path).check(proposed_size=10.0)

        assert decision.verdict == BLOCKED
        assert "an unknown limit is not a limit" in decision.checks[1].detail

    def test_unreadable_state_refuses_to_be_overwritten(self, tmp_path):
        (tmp_path / "breakers.json").write_text("nonsense", encoding="utf-8")

        with pytest.raises(RuntimeError):
            breakers(tmp_path).record(-5.0)

    def test_an_unproposed_size_blocks_rather_than_passing(self, tmp_path):
        decision = breakers(tmp_path).check(proposed_size=0.0)

        assert decision.verdict == BLOCKED
        assert "An unchecked size is not a permitted one" in "".join(
            c.detail for c in decision.checks)


class TestTheLimitsBite:
    def test_a_position_over_the_cap_is_blocked(self, tmp_path):
        # 5% of 1000 = 50
        assert breakers(tmp_path).check(proposed_size=50.01).verdict == BLOCKED

    def test_a_position_at_the_cap_passes(self, tmp_path):
        assert breakers(tmp_path).check(proposed_size=50.0).verdict == PERMITTED

    def test_the_daily_loss_limit_blocks_and_trips(self, tmp_path):
        book = breakers(tmp_path)          # 3% of 1000 = 30

        book.record(-31.0)

        assert book.state.status == TRIPPED
        assert book.state.tripped_by == "daily loss limit"

    def test_a_losing_run_trips(self, tmp_path):
        book = breakers(tmp_path)
        for _ in range(4):
            book.record(-1.0)

        assert book.state.status == TRIPPED
        assert book.state.tripped_by == "consecutive losses"

    def test_a_win_ends_the_run(self, tmp_path):
        book = breakers(tmp_path)
        book.record(-1.0)
        book.record(-1.0)
        book.record(1.0)

        assert book.consecutive_losses() == 0

    def test_an_implausible_edge_is_a_data_error_not_an_opportunity(self, tmp_path):
        decision = breakers(tmp_path).check(proposed_size=10.0, claimed_edge_pct=40.0)

        assert decision.verdict == BLOCKED
        assert "misplaced decimal" in "".join(c.detail for c in decision.checks)


class TestATrippedBreakerDoesNotResetItself:
    def test_a_tripped_breaker_blocks_on_the_next_check(self, tmp_path):
        book = breakers(tmp_path)
        book.record(-31.0)
        book.save()

        assert breakers(tmp_path).check(proposed_size=1.0).verdict == BLOCKED

    def test_the_block_says_it_does_not_reset_itself(self, tmp_path):
        book = breakers(tmp_path)
        book.record(-31.0)
        book.save()

        decision = breakers(tmp_path).check(proposed_size=1.0)

        assert "does not reset itself" in "".join(c.detail for c in decision.checks)

    def test_a_person_can_re_arm_it_with_a_reason(self, tmp_path):
        book = breakers(tmp_path)
        book.record(-31.0)

        book.reset("Ian McGuane", "reviewed the four losses, cause understood")

        assert book.state.status == ARMED

    def test_automation_cannot_re_arm_it(self, tmp_path):
        """It tripped because something was wrong; deciding it is now right is exactly
        the judgement automation must not make about its own halt."""

        book = breakers(tmp_path)
        book.record(-31.0)

        with pytest.raises(ValueError, match="about its own halt"):
            book.reset("agent:arb-reaper", "looks fine now")

    def test_a_reset_needs_a_stated_reason(self, tmp_path):
        book = breakers(tmp_path)
        book.record(-31.0)

        with pytest.raises(ValueError, match="stated reason"):
            book.reset("Ian McGuane", "   ")


class TestTheRingfenceRefusesNonsense:
    def test_a_zero_balance_is_refused(self):
        with pytest.raises(ValueError, match="positive balance"):
            Ringfence("arb", 0.0)

    def test_a_percentage_over_a_hundred_is_refused(self):
        with pytest.raises(ValueError):
            Ringfence("arb", 1000.0, per_position_pct=101.0)

    def test_limits_are_derived_from_the_ringfence(self):
        ring = Ringfence("arb", 2000.0, per_position_pct=5.0, daily_loss_pct=3.0)

        assert ring.per_position_limit == pytest.approx(100.0)
        assert ring.daily_loss_limit == pytest.approx(60.0)


class TestTheDecisionExplainsItself:
    def test_a_permitted_decision_lists_every_check(self, tmp_path):
        decision = ok(tmp_path)

        names = {c.name for c in decision.checks}
        assert names == {"kill switch", "breaker state", "previously tripped",
                         "daily loss limit", "consecutive losses", "position size",
                         "deployed capital", "concurrent positions", "sanity bound"}

    def test_a_blocked_decision_names_what_stopped_it(self, tmp_path):
        decision = breakers(tmp_path).check(proposed_size=999.0)

        assert "position size" in decision.blocked_by
        assert "Nothing was placed" in decision.describe()


class TestThePerPositionCapNeverBoundedTheTotal:
    """Twenty positions at 5% is the whole ring-fence, and nothing used to notice.

    The per-position cap is per position. For a lane whose positions settle days later —
    a Saturday's football, a stock held over a weekend — a dozen live at once is the
    ordinary state of a busy week. The daily loss limit cannot see them either, because it
    is computed from SETTLED outcomes and none of these have settled.
    """

    def _with(self, tmp_path, *, live=0, staked=10.0, **ring):
        from lib.outcomes import OutcomeLedger

        book = OutcomeLedger(tmp_path / "outcomes.json")
        for index in range(live):
            book.open_position("arb", f"match {index}", staked,
                               at=f"2026-08-03T{index:02d}:00:00Z")
        return breakers(tmp_path, ring=fence(**ring), positions=book)

    def test_the_total_already_out_blocks_a_position_the_per_position_cap_allows(self,
                                                                                tmp_path):
        # 5% of 1000 = 50 per position, 40% = 400 deployed. Eight at 50 is 400.
        book = self._with(tmp_path, live=8, staked=50.0)

        decision = book.check(proposed_size=10.0, claimed_edge_pct=2.0)

        assert decision.verdict == BLOCKED
        assert "deployed capital" in decision.blocked_by

    def test_it_says_settling_is_what_frees_it(self, tmp_path):
        book = self._with(tmp_path, live=8, staked=50.0)

        decision = book.check(proposed_size=10.0)

        assert "Settling what is open is what frees this" in "".join(
            c.detail for c in decision.checks)

    def test_a_lane_with_room_still_places(self, tmp_path):
        book = self._with(tmp_path, live=2, staked=50.0)

        assert book.check(proposed_size=10.0, claimed_edge_pct=2.0).verdict == PERMITTED

    def test_the_proposed_size_counts_toward_the_total(self, tmp_path):
        """390 out and a 20 proposal is 410, over 400 — even though 20 is a legal size."""

        book = self._with(tmp_path, live=6, staked=65.0)

        assert book.check(proposed_size=20.0).verdict == BLOCKED

    def test_a_count_of_small_positions_blocks_on_its_own(self, tmp_path):
        """They never breach the cash cap and still leave a lane with no attention left."""

        book = self._with(tmp_path, live=8, staked=1.0)

        decision = book.check(proposed_size=1.0, claimed_edge_pct=2.0)

        assert "concurrent positions" in decision.blocked_by

    def test_settled_positions_do_not_count_against_either(self, tmp_path):
        from lib.outcomes import OutcomeLedger

        book = OutcomeLedger(tmp_path / "outcomes.json")
        for index in range(8):
            position = book.open_position("arb", f"match {index}", 50.0,
                                          at=f"2026-08-03T{index:02d}:00:00Z")
            book.settle(position.position_id, 55.0)

        controls = breakers(tmp_path, positions=book)

        assert controls.check(proposed_size=10.0, claimed_edge_pct=2.0).verdict == PERMITTED

    def test_another_lane_s_positions_do_not_count(self, tmp_path):
        from lib.outcomes import OutcomeLedger

        book = OutcomeLedger(tmp_path / "outcomes.json")
        for index in range(8):
            book.open_position("stocks", f"TICK{index}", 50.0,
                               at=f"2026-08-03T{index:02d}:00:00Z")

        controls = breakers(tmp_path, positions=book)

        assert controls.check(proposed_size=10.0, claimed_edge_pct=2.0).verdict == PERMITTED


class TestAnUnknownTotalIsNotATotalWithinLimits:
    def test_no_ledger_attached_blocks_rather_than_passing(self, tmp_path):
        from lib.breakers import Breakers

        controls = Breakers(fence(), tmp_path / "b.json", kill_switch=tmp_path / "HALT")

        decision = controls.check(proposed_size=10.0, claimed_edge_pct=2.0)

        assert decision.verdict == BLOCKED
        assert "deployed capital" in decision.blocked_by

    def test_it_explains_why_the_per_position_cap_is_not_enough(self, tmp_path):
        from lib.breakers import Breakers

        controls = Breakers(fence(), tmp_path / "b.json", kill_switch=tmp_path / "HALT")

        assert "twenty positions at 5% is the whole ring-fence" in "".join(
            c.detail for c in controls.check(proposed_size=10.0).checks)

    def test_an_unreadable_ledger_blocks_too(self, tmp_path):
        from lib.outcomes import OutcomeLedger

        (tmp_path / "outcomes.json").write_text("{not json", encoding="utf-8")
        controls = breakers(tmp_path,
                            positions=OutcomeLedger(tmp_path / "outcomes.json"))

        assert controls.check(proposed_size=10.0).verdict == BLOCKED


class TestARingfenceThatCouldNeverPlaceIsRefused:
    def test_a_position_cap_above_the_deployed_cap_is_refused(self):
        """It would breach the total on its first position, so the lane could never act."""

        with pytest.raises(ValueError, match="could never place anything"):
            Ringfence("arb", 1000.0, per_position_pct=50.0, max_deployed_pct=40.0)

    def test_a_zero_concurrency_limit_is_refused(self):
        with pytest.raises(ValueError, match="at least 1"):
            Ringfence("arb", 1000.0, max_concurrent_positions=0)

    def test_the_deployed_limit_is_derived_from_the_ringfence(self):
        assert Ringfence("arb", 2000.0, max_deployed_pct=40.0).deployed_limit == (
            pytest.approx(800.0))
