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
                         "sanity bound"}

    def test_a_blocked_decision_names_what_stopped_it(self, tmp_path):
        decision = breakers(tmp_path).check(proposed_size=999.0)

        assert "position size" in decision.blocked_by
        assert "Nothing was placed" in decision.describe()
