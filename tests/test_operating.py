"""Autonomy is asserted, never assumed — and taking the wheel must not cost the research.

Two properties carry this file.

The first is the repository's recurring defect pointed at the most consequential switch it
has. An absent key, a typo, a `"true"` string, an unreadable ledger — every one of them must
resolve to OWNER_OPERATING_MANUALLY. There is exactly one way to reach AUTONOMOUS and it is
`autonomous_execution: true` with no file overriding it.

The second is why the middle mode exists at all. A stopped system tells you nothing, so
"I am taking the wheel" must not also mean "I am blind". Under manual the lane still looks,
screens, sizes and reports; only the placing stops. A switch that costs you the research is
a switch people avoid using, which makes it worse than no switch.
"""
from __future__ import annotations

import pytest

from lib.operating import (
    AUTONOMOUS,
    FROM_CONFIG,
    FROM_DEFAULT,
    FROM_EXPOSURE,
    FROM_FILE,
    FROM_REFUSAL,
    HALTED,
    OWNER_OPERATING_MANUALLY,
    describe_modes,
    modes_for,
    operating_mode,
    resume,
    take_the_wheel,
)


def mode(tmp_path, lane="arb", **kw):
    return operating_mode(lane, directory=tmp_path, **kw)


class TestAutonomyIsAssertedNeverAssumed:
    def test_the_only_route_to_autonomous_is_an_explicit_true(self, tmp_path):
        assert mode(tmp_path, config_autonomous=True).mode == AUTONOMOUS

    def test_an_absent_setting_is_manual_not_autonomous(self, tmp_path):
        found = mode(tmp_path)

        assert found.mode == OWNER_OPERATING_MANUALLY
        assert found.source == FROM_DEFAULT
        assert "Absent is not permission" in found.reason

    def test_false_is_manual(self, tmp_path):
        assert mode(tmp_path, config_autonomous=False).mode == OWNER_OPERATING_MANUALLY

    @pytest.mark.parametrize("value", ["true", "TRUE", "yes", 1, [], {}, "1"])
    def test_anything_that_is_not_an_explicit_true_is_a_no(self, tmp_path, value):
        """A JSON typo must not resolve to placing freely."""

        found = mode(tmp_path, config_autonomous=value)

        assert found.mode == OWNER_OPERATING_MANUALLY

    def test_a_truthy_non_true_says_why_it_was_not_enough(self, tmp_path):
        found = mode(tmp_path, config_autonomous="true")

        assert found.source == FROM_CONFIG
        assert "not an explicit yes is a no" in found.reason


class TestTheFileBeatsTheConfig:
    def test_a_global_manual_file_overrides_an_autonomous_config(self, tmp_path):
        take_the_wheel(tmp_path, "watching it for an hour")

        found = mode(tmp_path, config_autonomous=True)

        assert found.mode == OWNER_OPERATING_MANUALLY
        assert found.source == FROM_FILE

    def test_a_per_lane_file_stops_only_that_lane(self, tmp_path):
        take_the_wheel(tmp_path, "odds look wrong", lane="arb")

        assert mode(tmp_path, "arb", config_autonomous=True).mode == (
            OWNER_OPERATING_MANUALLY)
        assert mode(tmp_path, "stocks", config_autonomous=True).mode == AUTONOMOUS

    def test_it_says_a_setting_cannot_override_a_switch(self, tmp_path):
        take_the_wheel(tmp_path, "taking over")

        assert "would not be a switch" in mode(tmp_path, config_autonomous=True).reason

    def test_anything_can_take_the_wheel_without_authority(self, tmp_path):
        """Becoming more cautious needs no permission. Becoming less does."""

        path = take_the_wheel(tmp_path, "automated tripwire fired")

        assert path.exists()

    def test_the_reason_is_written_into_the_file(self, tmp_path):
        take_the_wheel(tmp_path, "spreads looked wrong at the open")

        assert "spreads looked wrong" in (tmp_path / "MANUAL").read_text(encoding="utf-8")


class TestHaltStillStopsEverything:
    def test_halt_outranks_an_autonomous_config(self, tmp_path):
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")

        assert mode(tmp_path, config_autonomous=True).mode == HALTED

    def test_halt_outranks_manual_too(self, tmp_path):
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")
        take_the_wheel(tmp_path, "manual")

        assert mode(tmp_path).mode == HALTED

    def test_a_per_lane_halt_stops_one_lane(self, tmp_path):
        (tmp_path / "HALT-crypto").write_text("stop", encoding="utf-8")

        assert mode(tmp_path, "crypto").mode == HALTED
        assert mode(tmp_path, "arb").mode != HALTED

    def test_halted_is_the_only_mode_that_stops_the_research(self, tmp_path):
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")

        assert mode(tmp_path).may_reap is False

    def test_manual_keeps_looking(self, tmp_path):
        """A switch that costs you the research is one people avoid using."""

        take_the_wheel(tmp_path, "taking the wheel")

        found = mode(tmp_path)
        assert found.may_reap is True
        assert found.may_place is False

    def test_manual_says_the_lane_still_works(self, tmp_path):
        take_the_wheel(tmp_path, "taking the wheel")

        assert "still looks, screens, gates" in mode(tmp_path).describe()


class TestTheChainLaneIsRefusedOutright:
    def test_asking_for_autonomous_crypto_does_not_grant_it(self, tmp_path):
        found = mode(tmp_path, "crypto", config_autonomous=True)

        assert found.mode == OWNER_OPERATING_MANUALLY
        assert found.source == FROM_REFUSAL

    def test_it_is_stated_rather_than_silently_downgraded(self, tmp_path):
        """A setting that quietly did nothing is a misunderstanding nobody finds."""

        found = mode(tmp_path, "crypto", config_autonomous=True)

        assert "refused whatever it says" in found.reason
        assert "no key path either" in found.reason

    def test_the_stocks_lane_may_have_it(self, tmp_path):
        assert mode(tmp_path, "stocks", config_autonomous=True).mode == AUTONOMOUS


class TestUnresolvedExposureDropsToManual:
    def test_an_unknown_position_stops_the_lane_placing(self, tmp_path):
        found = mode(tmp_path, config_autonomous=True, unresolved_unknowns=1)

        assert found.mode == OWNER_OPERATING_MANUALLY
        assert found.source == FROM_EXPOSURE

    def test_it_says_why_the_breakers_cannot_catch_this(self, tmp_path):
        found = mode(tmp_path, config_autonomous=True, unresolved_unknowns=2)

        assert "never reaches the breakers by design" in found.reason
        assert "Settle or void them and this clears" in found.reason

    def test_resolving_them_restores_autonomy(self, tmp_path):
        assert mode(tmp_path, config_autonomous=True,
                    unresolved_unknowns=0).mode == AUTONOMOUS


class TestComingBackIsAHumanAct:
    def test_a_person_can_resume_with_a_reason(self, tmp_path):
        take_the_wheel(tmp_path, "watching")

        assert resume(tmp_path, "Ian McGuane", "watched a full session, behaviour understood")
        assert mode(tmp_path, config_autonomous=True).mode == AUTONOMOUS

    def test_automation_cannot_resume(self, tmp_path):
        take_the_wheel(tmp_path, "watching")

        with pytest.raises(ValueError, match="its own supervision"):
            resume(tmp_path, "agent:arb-reaper", "looks fine now")

    def test_a_resume_needs_a_stated_reason(self, tmp_path):
        take_the_wheel(tmp_path, "watching")

        with pytest.raises(ValueError, match="impatient"):
            resume(tmp_path, "Ian McGuane", "  ")

    def test_an_unnamed_resume_is_refused(self, tmp_path):
        take_the_wheel(tmp_path, "watching")

        with pytest.raises(ValueError, match="named person"):
            resume(tmp_path, "", "fine now")

    def test_resuming_when_nothing_is_switched_reports_it_rather_than_pretending(self,
                                                                                tmp_path):
        assert resume(tmp_path, "Ian McGuane", "nothing to do") is False

    def test_a_failed_resume_leaves_the_switch_in_place(self, tmp_path):
        take_the_wheel(tmp_path, "watching")

        with pytest.raises(ValueError):
            resume(tmp_path, "agent:x", "fine")

        assert mode(tmp_path, config_autonomous=True).mode == OWNER_OPERATING_MANUALLY


class TestAcrossEveryLane:
    def _config(self, **kw):
        base = {"arb": {"autonomous_execution": True},
                "stocks": {"autonomous_execution": True},
                "crypto": {"autonomous_execution": True}}
        base.update(kw)
        return base

    def test_every_lane_is_always_reported(self, tmp_path):
        modes = modes_for(("arb", "stocks", "crypto"), self._config(), directory=tmp_path)

        assert [m.lane for m in modes] == ["arb", "stocks", "crypto"]

    def test_crypto_never_places_however_it_is_configured(self, tmp_path):
        modes = modes_for(("arb", "stocks", "crypto"), self._config(), directory=tmp_path)

        assert {m.lane for m in modes if m.may_place} == {"arb", "stocks"}

    def test_an_unreadable_ledger_drops_every_lane_to_manual(self, tmp_path):
        """Unreadable is not empty, and this is the direction that stops."""

        lost = type("L", (), {"readable": False, "positions": []})()

        modes = modes_for(("arb", "stocks"), self._config(), directory=tmp_path,
                          ledger=lost)

        assert all(m.mode == OWNER_OPERATING_MANUALLY for m in modes)
        assert all(m.source == FROM_EXPOSURE for m in modes)

    def test_an_unknown_in_one_lane_does_not_stop_another(self, tmp_path):
        from lib.outcomes import OutcomeLedger

        book = OutcomeLedger(tmp_path / "outcomes.json")
        position = book.open_position("arb", "x", 10.0, at="2026-08-03T01:00:00Z")
        book.mark_unknown(position.position_id, "account restricted")

        modes = {m.lane: m for m in modes_for(("arb", "stocks"), self._config(),
                                              directory=tmp_path, ledger=book)}

        assert modes["arb"].may_place is False
        assert modes["stocks"].may_place is True

    def test_the_summary_names_which_lanes_place_without_asking(self, tmp_path):
        described = describe_modes(
            modes_for(("arb", "stocks", "crypto"), self._config(), directory=tmp_path))

        assert "2 lane(s) will place without asking: arb, stocks" in described

    def test_the_summary_is_explicit_when_nothing_places(self, tmp_path):
        described = describe_modes(
            modes_for(("arb",), {"arb": {}}, directory=tmp_path))

        assert "Every instruction waits for you" in described
