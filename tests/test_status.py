"""A money status must show authority and uncertainty, never manufacture reassuring zeros.

The operating mode is the most consequential fact on the page: AUTONOMOUS means the lane
places without asking. Missing breaker and outcome files are equally consequential. They
mean limits or exposure cannot be established, not that an armed lane has nothing at risk.
These tests keep all three states visually distinct and keep stale money in view.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from lib.breakers import Breakers, Ringfence
from lib.outcomes import OutcomeLedger
from status import money_panel


def config_file(tmp_path, **overrides):
    config = {
        "arb": {
            "enabled": True,
            "balance": 1_000.0,
            "currency": "EUR",
            "autonomous_execution": True,
        },
        "stocks": {"enabled": False},
        "crypto": {"enabled": False},
    }
    config.update(overrides)
    path = tmp_path / "reapers.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def render(tmp_path, config_path=None):
    return "\n".join(money_panel(
        config_path=config_path or tmp_path / "reapers.json",
        directory=tmp_path,
        ledger_path=tmp_path / "outcomes.json",
    ))


def test_an_autonomous_lane_is_visually_distinct(tmp_path):
    output = render(tmp_path, config_file(tmp_path))

    assert "AUTONOMOUS  [arb]" in output
    assert "PLACES ITS OWN INSTRUCTIONS" in output


def test_missing_money_files_are_not_rendered_as_zero_exposure(tmp_path):
    output = render(tmp_path)

    assert output.count("NOT_CONFIGURED") >= 6
    assert "not a zero balance or zero exposure" in output
    assert "not 0.00 at risk" in output
    assert "0.00 at risk" not in output.replace("not 0.00 at risk", "")


def test_a_ring_fence_reports_its_balance_and_currency(tmp_path):
    output = render(tmp_path, config_file(tmp_path))

    assert "RING-FENCE  1,000.00 EUR" in output


def test_an_unreadable_breaker_is_not_not_configured(tmp_path):
    path = config_file(tmp_path)
    (tmp_path / "breakers-arb.json").write_text("{broken", encoding="utf-8")

    output = render(tmp_path, path)

    assert "BREAKER  UNREADABLE" in output
    assert "unknown loss history must stop the lane" in output


def test_a_tripped_breaker_names_why_when_and_that_it_does_not_self_clear(tmp_path):
    path = config_file(tmp_path)
    controls = Breakers(
        Ringfence("arb", 1_000.0),
        tmp_path / "breakers-arb.json",
        kill_switch=tmp_path / "HALT",
    )
    for _ in range(4):
        controls.record(-1.0, reference="loss")
    controls.save()

    output = render(tmp_path, path)

    assert "BREAKER  TRIPPED  consecutive losses at" in output
    assert "does not self-clear" in output


def test_open_and_stale_money_is_named_as_invisible_to_the_daily_loss_limit(tmp_path):
    path = config_file(tmp_path)
    opened = (datetime.now(timezone.utc) - timedelta(hours=80)).isoformat()
    ledger = OutcomeLedger(tmp_path / "outcomes.json")
    ledger.open_position("arb", "old position", 75.0, source="MANUAL", at=opened)
    ledger.save()

    output = render(tmp_path, path)

    assert "1 position(s) live, 75.00 at risk" in output
    assert "invisible to the daily loss limit" in output
    assert "open over 72h" in output


def test_an_unreadable_outcome_ledger_is_not_an_empty_position_book(tmp_path):
    path = config_file(tmp_path)
    (tmp_path / "outcomes.json").write_text("{broken", encoding="utf-8")

    output = render(tmp_path, path)

    assert "UNREADABLE  the outcome ledger would not parse" in output
    assert "not a report that nothing is open" in output
