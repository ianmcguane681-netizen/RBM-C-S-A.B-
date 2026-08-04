"""Adding a fourth money lane must be one decision, not a hunt through five files.

Three lanes exist and more are planned — flipper, an app studio, a media lane, a commerce
lane. The risk that creates is not that a new lane is hard to write; it is that a new lane
half-arrives. It assembles and places, and is missing from the money panel because that
file kept its own copy of the lane list. Or it is rejected by the API because a
`Literal` three names long says it does not exist. Or it never runs at all, because the
scheduler's entries were typed out by hand — and a lane that is never scheduled fails
*silently*, which is indistinguishable from a lane that keeps finding nothing.

So these tests do not check that three lanes work. They add a lane that does not exist and
assert it reaches the parts of the system nobody would remember to update, without those
parts being edited. The registry in `lib.reaping.LANES` is the single decision; everything
downstream is derived from it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import run
import status
from lib.reaping import LANES, REFUSED, assemble


@pytest.fixture
def a_fourth_lane(monkeypatch):
    """`flipper` — a real planned lane, deliberately with no builder written yet."""

    extended = LANES + ("flipper",)
    monkeypatch.setattr("lib.reaping.LANES", extended)
    return extended


def test_no_module_keeps_its_own_copy_of_the_lane_list():
    """`status.MONEY_LANES` restated the three names and would have silently omitted a
    fourth from the one screen whose job is to show every lane that can spend money."""

    assert status.MONEY_LANES is LANES


def test_a_new_lane_is_scheduled_without_touching_the_scheduler(a_fourth_lane):
    """A lane nobody scheduled never runs, and never running looks like finding nothing.

    That is the failure mode worth a test: it is invisible. There is no error, no refusal
    and no empty result — the lane is simply absent from the orchestrator's list forever.
    """

    scheduled = {lane.name for lane in run._reaper_lanes()}

    assert "reap-flipper" in scheduled
    assert scheduled == {f"reap-{lane}" for lane in a_fourth_lane}


def test_a_lane_with_no_stated_cadence_gets_the_default_rather_than_none(a_fourth_lane):
    lane = next(l for l in run._reaper_lanes() if l.name == "reap-flipper")

    assert lane.cadence_seconds == run.DEFAULT_REAP_CADENCE
    assert lane.unconfigured_exit_codes == (2,)   # nothing looked at stays distinguishable


def test_a_declared_lane_with_no_builder_is_reported_rather_than_raised(
    a_fourth_lane, tmp_path
):
    """`builders[lane]` on an unknown key is a KeyError out of the middle of the pass.

    Every other lane's assembly is lost with it, so a half-added fourth lane takes the
    report for the three that were working. A named refusal keeps the other three visible
    and says what is missing.
    """

    config = {lane: {"enabled": True, "balance": 500.0} for lane in a_fourth_lane}

    assembled = assemble(config, directory=tmp_path, kill_switch=tmp_path / "HALT",
                         theses_path=tmp_path / "theses.json")

    assert [item.lane for item in assembled] == list(a_fourth_lane)
    flipper = next(item for item in assembled if item.lane == "flipper")
    assert flipper.status == REFUSED
    assert "assemble_flipper" in flipper.reason


def test_the_api_accepts_a_new_lane_without_editing_the_request_model(a_fourth_lane):
    """The allowed set is read from the registry at validation time, not from a Literal.

    A `Literal` three names long turns adding a lane into a 422 from a file nobody would
    think to look in: the lane assembles, schedules and places, and only the API says it
    does not exist.
    """

    from backend.app import ReaperCommand

    assert ReaperCommand(lane="flipper").lane == "flipper"
    with pytest.raises(ValueError, match="unknown lane"):
        ReaperCommand(lane="roulette")


def test_the_dashboard_names_a_lane_it_has_no_label_for(a_fourth_lane):
    """Presentation degrades to the lane's own id rather than to `undefined`.

    The front end must not be a second place that decides which lanes exist. A label it
    has not been taught is a cosmetic gap; printing "undefined Division" beside a live
    ring-fence is not.
    """

    script = (Path(__file__).parent.parent / "backend/static/app.js").read_text()

    assert "laneName" in script and "laneIcon" in script
    # No direct map lookup survives, since that is what produced `undefined`.
    assert "laneNames[" not in script
    assert "laneIcons[" not in script


def test_the_three_lanes_that_exist_still_assemble_unchanged(tmp_path):
    """The guard must not be bought by breaking the case it protects."""

    config = {lane: {} for lane in LANES}

    assembled = assemble(config, directory=tmp_path, kill_switch=tmp_path / "HALT",
                         theses_path=tmp_path / "theses.json")

    assert [item.lane for item in assembled] == list(LANES)
    assert all(item.status != REFUSED for item in assembled)
