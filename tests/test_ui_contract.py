"""A UI contract must expose omissions, not make incomplete functions look operational.

The first front end will be built independently of the money code. These tests hold the
boundary it can trust: versioned JSON, nullable unknown money, explicit execution limits,
and a reserved SRE slot that cannot be mistaken for an authorised scanner.
"""
from __future__ import annotations

import json

import positions
import run
import status
from lib.functions import function_specs
from lib.outcomes import OPEN, Position
from lib.reaping import Reaping


def test_every_function_has_a_stable_identity_and_explicit_execution_boundary():
    rows = [item.to_dict() for item in function_specs()]

    assert [row["id"] for row in rows] == ["arb", "stocks", "crypto", "sre"]
    assert all(row["execution"] for row in rows)
    assert all(row["status"] for row in rows)


def test_sre_is_reserved_until_a_person_records_authorised_scope():
    sre = next(item.to_dict() for item in function_specs() if item.function_id == "sre")

    assert sre["status"] == "RESERVED"
    assert sre["execution"] == "RESEARCH_ONLY"
    assert "authorised target" in sre["remedy"]


def test_the_status_snapshot_carries_schema_and_function_slots(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    payload = status.as_json()

    assert payload["schema_version"] == "1.0"
    assert {item["id"] for item in payload["functions"]} == {
        "arb", "stocks", "crypto", "sre",
    }


def test_a_reap_that_looked_at_nothing_is_machine_readable(monkeypatch, capsys):
    monkeypatch.setattr("lib.reaping.reap", lambda **_kwargs: Reaping())

    code = run.reap("arb", as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "NOTHING_WAS_LOOKED_AT"
    assert payload["harvests"] == []


def test_an_absent_ledger_is_not_configured_instead_of_zero(tmp_path, capsys):
    code = positions.main(["--json", "--ledger", str(tmp_path / "outcomes.json")])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "NOT_CONFIGURED"
    assert payload["unsettled_exposure"] is None
    assert payload["positions"] is None


def test_an_open_position_has_no_manufactured_return_or_profit():
    payload = Position("POS-one", "arb", "A v B", OPEN, 20.0).to_dict()

    assert payload["returned"] is None
    assert payload["profit"] is None
