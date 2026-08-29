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
from lib.reaping import LANES, PARKED, PARKED_LANES, REFUSED, assemble


@pytest.fixture
def a_fourth_lane(monkeypatch):
    """`media` — a real planned lane, deliberately with no builder written yet.

    This was `flipper` until 2026-08-29, when the flipper was built and stopped being a
    worked example of a half-added lane. The replacement is the next name in
    `lib/reaper.py`'s list of planned lanes, and it will need replacing again the day
    somebody builds that one — which is the guard doing its job rather than a smell.
    """

    extended = LANES + ("media",)
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

    assert "reap-media" in scheduled
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

    assert [item.lane for item in assembled][:len(a_fourth_lane)] == list(a_fourth_lane)
    media = next(item for item in assembled if item.lane == "media")
    assert media.status == REFUSED
    assert "assemble_media" in media.reason


def test_the_api_accepts_a_new_lane_without_editing_the_request_model(a_fourth_lane):
    """The allowed set is read from the registry at validation time, not from a Literal.

    A `Literal` three names long turns adding a lane into a 422 from a file nobody would
    think to look in: the lane assembles, schedules and places, and only the API says it
    does not exist.
    """

    from backend.app import ReaperCommand

    assert ReaperCommand(lane="media").lane == "media"
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


def test_the_lanes_that_exist_still_assemble_unchanged(tmp_path):
    """The guard must not be bought by breaking the case it protects."""

    config = {lane: {} for lane in LANES}

    assembled = assemble(config, directory=tmp_path, kill_switch=tmp_path / "HALT",
                         theses_path=tmp_path / "theses.json")

    assert [item.lane for item in assembled][:len(LANES)] == list(LANES)
    assert all(item.status != REFUSED for item in assembled)


def test_a_parked_lane_reaches_the_report_without_reaching_the_scheduler(tmp_path):
    """The two halves of parking, asserted together because either alone is a bug.

    A parked lane that still gets scheduled goes on spending an API quota nobody meant to
    spend. A parked lane that vanishes from the assembly report is indistinguishable from
    a lane that was never written, which is the whole failure this repository is organised
    around — and it is worse here than elsewhere, because the thing that went missing is
    a decision somebody made rather than a value somebody failed to read.
    """

    scheduled = {lane.name for lane in run._reaper_lanes()}
    assembled = assemble({}, directory=tmp_path, kill_switch=tmp_path / "HALT",
                         theses_path=tmp_path / "theses.json")

    for lane in PARKED_LANES:
        assert f"reap-{lane}" not in scheduled
        assert next(a for a in assembled if a.lane == lane).status == PARKED


def test_the_api_refuses_a_parked_lane_by_name_rather_than_as_unknown(tmp_path):
    """A 422 saying "unknown lane: crypto" is a lie about a lane that exists and works."""

    from backend.app import ReaperCommand

    with pytest.raises(ValueError, match="PARKED"):
        ReaperCommand(lane="crypto")


class TestANewLaneCannotBorrowAnotherLanesExecutionPath:
    """`place_harvest` used to END with `return _place_stock(...)`.

    Every refusal above it named a lane — arb and crypto have no adapter, the mode is not
    AUTONOMOUS, the ledger is unreadable — and anything that survived them was handed to
    the stock placer. Not because it was stocks; because it was not one of the two lanes
    that had been thought about.

    A flipper instruction with a broker attached would therefore have been submitted as an
    equity order. And since this module records the position BEFORE it sends, the first
    evidence would have been a phantom position on file beside a broker error. That is the
    exact direction the rest of the repository refuses to fail in, sitting in the one
    module that cannot undo what it does.
    """

    def _ready(self, lane: str):
        from lib.reaper import Harvest

        return Harvest(lane=lane, status="READY", subject="a thing",
                       instruction=object(), permission=None)

    def _autonomous(self):
        from lib.operating import AUTONOMOUS, Mode

        return Mode("media", AUTONOMOUS, "config", "autonomous_execution is true")

    class _Ledger:
        readable = True
        reason = ""

    def test_a_lane_with_no_execution_path_is_refused_by_name(self):
        from lib.placing import REFUSED, place_harvest

        placement = place_harvest(
            self._ready("media"), mode=self._autonomous(), ledger=self._Ledger(),
            broker=object(),
        )

        assert placement.status == REFUSED
        assert "no execution path is written for 'media'" in placement.reason
        # And it says which of the two registries the answer belongs in.
        assert "PLACERS" in placement.reason and "NO_ADAPTER" in placement.reason

    def test_the_refusal_lands_before_anything_is_recorded(self):
        """Cheap refusals come first, and this one has to be among them.

        An unknown lane refused AFTER the position is written leaves the phantom the
        ordering exists to avoid, for an order that was never sendable in the first place.
        """

        from lib.placing import place_harvest

        wrote: list = []

        class Recording(self.__class__._Ledger):
            def open_position(self, *a, **kw):
                wrote.append(a)
                raise AssertionError("recorded a position for a lane that cannot place")

        placement = place_harvest(
            self._ready("media"), mode=self._autonomous(), ledger=Recording(),
            broker=object(),
        )

        assert wrote == []
        assert placement.position_id == ""

    def test_a_lane_that_deliberately_cannot_place_still_says_why(self):
        """NO_ADAPTER outranks the unknown-lane refusal: arb is not an oversight."""

        from lib.placing import NOT_PLACED, place_harvest

        placement = place_harvest(
            self._ready("arb"), mode=self._autonomous(), ledger=self._Ledger(),
            broker=object(),
        )

        assert placement.status == NOT_PLACED
        assert "no betting API" in placement.reason

    def test_the_lane_that_does_place_still_places(self):
        from lib.placing import PLACERS

        assert set(PLACERS) == {"stocks"}

    def test_a_lane_with_no_broker_factory_gets_none_rather_than_an_import_error(self):
        from lib.placing import broker_for

        assert broker_for("media") is None

    def test_the_flipper_now_declares_why_it_cannot_place_rather_than_being_unknown(self):
        """It was the worked example of an unbuilt lane until it was built. Now it is in
        NO_ADAPTER, and the refusal has to say WHY rather than "no execution path" — eBay
        taking no automated purchase is a fact about eBay, not unfinished work here."""

        from lib.placing import NOT_PLACED, place_harvest

        from lib.operating import AUTONOMOUS, Mode

        placement = place_harvest(
            self._ready("flipper"),
            mode=Mode("flipper", AUTONOMOUS, "config", "autonomous_execution is true"),
            ledger=self._Ledger(), broker=object())

        assert placement.status == NOT_PLACED
        assert "no automated purchase" in placement.reason
