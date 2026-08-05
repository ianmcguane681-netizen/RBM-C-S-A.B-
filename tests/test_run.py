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

    assert lanes["reap-crypto"].cadence_seconds == 6 * 3600
    assert lanes["reap-stocks"].cadence_seconds == 24 * 3600


def test_the_arb_cadence_is_set_by_the_allowance_rather_than_by_the_odds():
    """Odds justify every five minutes. A 500-a-month tier does not, and it binds.

    This lane was every 30 minutes with `arb-scan` on the same cadence — two lanes buying
    the same prices from the same key, ~288 credits a day against 16.4. The allowance went
    in under two days, and what follows is a lane reporting no arb because the key is
    spent, which is indistinguishable from a quiet market for the rest of the month.

    The assertion is the budget rather than a literal cadence, so a future change that
    shortens the interval has to argue with the arithmetic instead of just passing.
    """

    from connectors.oddsapi import FREE_TIER_MONTHLY, credits_per_day

    lanes = {lane.name: lane for lane in LANES}
    # What this repository actually ships in examples/reapers.example.json.
    daily = credits_per_day(sports=2, cadence_seconds=lanes["reap-arb"].cadence_seconds)
    daily += credits_per_day(sports=1, cadence_seconds=lanes["arb-scan"].cadence_seconds)

    assert daily <= FREE_TIER_MONTHLY / 30.4, (
        f"the shipped cadences spend {daily:.1f} credits/day against a budget of "
        f"{FREE_TIER_MONTHLY / 30.4:.1f}")


def test_the_two_odds_lanes_do_not_share_a_cadence():
    """They asked on the same timer, for the same prices, from the same key.

    `arb-scan` is the discovery view a person reads; `reap-arb` is the one that reaches a
    sized instruction. Running both half-hourly answered the same question twice and
    charged twice for it.
    """

    lanes = {lane.name: lane for lane in LANES}

    assert lanes["arb-scan"].cadence_seconds != lanes["reap-arb"].cadence_seconds


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

