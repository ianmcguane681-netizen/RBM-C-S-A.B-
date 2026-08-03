"""Scheduled reapers must preserve both cadence and the meaning of a run.

Odds, chain state and filings age at different rates, so combining them under one timer
either wastes scarce source capacity or leaves fast evidence stale. More importantly, exit
2 means NOTHING WAS LOOKED AT. A scheduler that calls it success turns a blind pipeline
into a quiet market, which is the most expensive possible interpretation of no output.
"""
from __future__ import annotations

from lib.reaping import Reaping
from run import LANES, reap


def test_each_reaper_lane_has_the_cadence_of_its_evidence():
    lanes = {lane.name: lane for lane in LANES}

    assert lanes["reap-arb"].cadence_seconds == 30 * 60
    assert lanes["reap-crypto"].cadence_seconds == 6 * 3600
    assert lanes["reap-stocks"].cadence_seconds == 24 * 3600


def test_scheduled_reapers_keep_nothing_looked_at_as_unconfigured():
    for lane in (item for item in LANES if item.name.startswith("reap-")):
        assert lane.produces_decisions is True
        assert lane.findings_exit_codes == (1,)
        assert lane.unconfigured_exit_codes == (2,)


def test_a_named_reap_runs_only_that_lane(monkeypatch):
    received = []

    def fake_reap(**kwargs):
        received.append(kwargs)
        return Reaping(refusal="nothing configured")

    monkeypatch.setattr("lib.reaping.reap", fake_reap)

    assert reap("arb") == 2
    assert received[0]["lanes"] == ("arb",)


def test_a_scheduled_reap_places_and_a_dry_one_does_not(monkeypatch):
    """The cadence lanes run unattended, so whether they place is part of the contract."""

    received = []

    def fake_reap(**kwargs):
        received.append(kwargs)
        return Reaping(refusal="nothing configured")

    monkeypatch.setattr("lib.reaping.reap", fake_reap)

    reap("arb")
    reap("arb", dry=True)

    assert received[0]["place"] is True
    assert received[1]["place"] is False


def test_an_unknown_lane_refuses_and_names_the_valid_choices(capsys):
    """Derived from lib.reaping.LANES, so a fourth lane cannot leave this stale."""

    from lib.reaping import LANES as REAPER_LANES

    assert reap("property") == 2

    output = capsys.readouterr().out
    assert all(lane in output for lane in REAPER_LANES)
    assert "Unknown reaper lane 'property'" in output

