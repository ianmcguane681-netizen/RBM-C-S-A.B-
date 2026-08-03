"""A lane nobody configured must never appear beside a lane that looked and found nothing.

The recurring defect, at the level of the command a person actually types. `--reap` runs
three lanes; if two of them were never set up, printing three tidy "nothing found" lines is
a confident report assembled out of an empty config file.

So assembly is a first-class result with four outcomes — CONFIGURED, NOT_CONFIGURED,
UNREADABLE, REFUSED — and an unparseable config refuses the whole run rather than treating
every lane as unconfigured.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.reaping import (
    CONFIGURED,
    NOT_CONFIGURED,
    REFUSED,
    UNREADABLE,
    Assembly,
    Reaping,
    assemble,
    load_config,
    reap,
)

AUTHORITY = {
    "declared_by": "Ian McGuane",
    "reasoning": "two books disagree by more than the cost of taking both sides",
    "considered": ["a book restricts the account"],
    "expires_at": "2099-01-01T00:00:00Z",
    "max_exposure": 50.0,
}


def config(**overrides):
    base = {
        "arb": {"enabled": True, "balance": 500.0, "sports": ["soccer_epl"],
                "authority": dict(AUTHORITY)},
        "stocks": {"enabled": True, "balance": 5000.0, "watchlist": ["MODN"]},
        "crypto": {"enabled": False},
    }
    base.update(overrides)
    return base


def paths(tmp_path):
    return {"directory": tmp_path, "kill_switch": tmp_path / "HALT",
            "theses_path": tmp_path / "theses.json"}


class TestFourOutcomesNotTwo:
    def test_every_lane_is_always_reported(self, tmp_path):
        assembled = assemble(config(), **paths(tmp_path))

        assert [a.lane for a in assembled] == ["arb", "stocks", "crypto"]

    def test_a_disabled_lane_is_not_configured_rather_than_absent(self, tmp_path):
        crypto = assemble(config(), **paths(tmp_path))[2]

        assert crypto.status == NOT_CONFIGURED

    def test_not_configured_says_it_did_not_look(self, tmp_path):
        described = assemble(config(), **paths(tmp_path))[2].describe()

        assert "did not look" in described
        assert "has not reported that there is nothing to find" in described

    def test_an_empty_config_leaves_every_lane_unconfigured(self, tmp_path):
        assert {a.status for a in assemble({}, **paths(tmp_path))} == {NOT_CONFIGURED}

    def test_a_configured_lane_carries_a_reaper(self, tmp_path):
        arb = assemble(config(), **paths(tmp_path))[0]

        assert arb.status == CONFIGURED
        assert arb.reaper.lane == "arb"


class TestUnreadableIsNotUnconfigured:
    def test_unreadable_breaker_state_is_unreadable_not_configured(self, tmp_path):
        (tmp_path / "breakers-arb.json").write_text("{not json", encoding="utf-8")

        arb = assemble(config(), **paths(tmp_path))[0]

        assert arb.status == UNREADABLE
        assert "not a satisfied daily loss limit" in arb.reason

    def test_an_unreadable_thesis_register_stops_the_stocks_lane(self, tmp_path):
        (tmp_path / "theses.json").write_text("nonsense", encoding="utf-8")

        stocks = assemble(config(), **paths(tmp_path))[1]

        assert stocks.status == UNREADABLE
        assert "unknown rather than nothing" in stocks.reason

    def test_the_wording_distinguishes_it_from_nothing_being_asked(self, tmp_path):
        (tmp_path / "theses.json").write_text("nonsense", encoding="utf-8")

        described = assemble(config(), **paths(tmp_path))[1].describe()

        assert "not the same as nothing being asked" in described


class TestConfigurationIsRefusedRatherThanPatched:
    def test_arb_without_a_standing_authority_is_refused(self, tmp_path):
        broken = config(arb={"enabled": True, "balance": 500.0})

        arb = assemble(broken, **paths(tmp_path))[0]

        assert arb.status == REFUSED
        assert "mints its own authorisation" in arb.reason

    def test_an_automation_authored_grant_is_refused(self, tmp_path):
        grant = dict(AUTHORITY, declared_by="agent:arb-reaper")
        broken = config(arb={"enabled": True, "balance": 500.0, "authority": grant})

        assert assemble(broken, **paths(tmp_path))[0].status == REFUSED

    def test_a_zero_balance_ringfence_is_refused(self, tmp_path):
        broken = config(arb={"enabled": True, "balance": 0.0, "authority": dict(AUTHORITY)})

        arb = assemble(broken, **paths(tmp_path))[0]

        assert arb.status == REFUSED
        assert "positive balance" in arb.reason

    def test_crypto_without_a_wallet_is_refused(self, tmp_path):
        broken = config(crypto={"enabled": True, "balance": 100.0})

        crypto = assemble(broken, **paths(tmp_path))[2]

        assert crypto.status == REFUSED
        assert "nobody to build a transaction for" in crypto.reason


class TestTheConfigFileItself:
    def test_an_absent_file_is_not_a_broken_one(self, tmp_path):
        payload, error = load_config(tmp_path / "nothing.json")

        assert (payload, error) == ({}, "")

    def test_a_broken_file_reports_why(self, tmp_path):
        path = tmp_path / "reapers.json"
        path.write_text("{not json", encoding="utf-8")

        _payload, error = load_config(path)

        assert "JSONDecodeError" in error

    def test_a_json_array_is_not_a_config(self, tmp_path):
        path = tmp_path / "reapers.json"
        path.write_text("[]", encoding="utf-8")

        assert load_config(path)[1].endswith("does not contain a JSON object")

    def test_a_broken_file_refuses_the_whole_run(self, tmp_path):
        path = tmp_path / "reapers.json"
        path.write_text("{not json", encoding="utf-8")

        reaping = reap(config_path=path, **paths(tmp_path))

        assert reaping.refusal
        assert "confident answer assembled out of a parse error" in reaping.refusal
        assert reaping.harvests == ()

    def test_the_committed_example_parses_and_assembles(self, tmp_path):
        payload = json.loads(Path("examples/reapers.example.json").read_text("utf-8"))

        assembled = assemble(payload, **paths(tmp_path))

        assert [a.lane for a in assembled] == ["arb", "stocks", "crypto"]
        assert assembled[0].status == CONFIGURED

    def test_the_example_config_is_not_the_live_one(self):
        """data/reapers.json is gitignored: it names watchlists and a wallet."""

        assert "data/reapers.json" in Path(".gitignore").read_text("utf-8")


class TestTheReport:
    def test_nothing_configured_says_nothing_was_looked_at(self):
        described = Reaping(tuple(Assembly(l, NOT_CONFIGURED)
                                  for l in ("arb", "stocks", "crypto"))).describe()

        assert "NOTHING was looked at" in described
        assert "not a report that there was nothing to find" in described

    def test_a_ready_harvest_still_says_nothing_was_placed(self):
        harvest = type("H", (), {"status": "READY", "describe": lambda _s: "READY [arb]"})()

        described = Reaping((Assembly("arb", CONFIGURED),), (harvest,)).describe()

        assert "NOTHING HAS BEEN PLACED, SIGNED OR SENT" in described

    def test_no_ready_harvest_says_the_reasons_are_above(self):
        harvest = type("H", (), {"status": "REFUSED", "describe": lambda _s: "REFUSED"})()

        described = Reaping((Assembly("arb", CONFIGURED),), (harvest,)).describe()

        assert "Nothing reached READY" in described

    def test_every_lane_failing_to_look_is_not_a_quiet_morning(self):
        """The distinction the whole repository is about, at the level of a whole run."""

        blind = type("H", (), {"status": "COULD_NOT_LOOK",
                               "describe": lambda _s: "COULD_NOT_LOOK"})()

        reaping = Reaping((Assembly("arb", CONFIGURED),), (blind,))

        assert reaping.looked is False
        assert "it is a pipeline that did not run" in reaping.describe()

    def test_one_lane_looking_is_enough_to_be_a_run(self):
        blind = type("H", (), {"status": "COULD_NOT_LOOK", "describe": lambda _s: "x"})()
        found = type("H", (), {"status": "NOTHING_FOUND", "describe": lambda _s: "y"})()

        assert Reaping((Assembly("arb", CONFIGURED),), (blind, found)).looked is True

    def test_a_refusal_replaces_the_whole_report(self):
        assert Reaping(refusal="broken").describe().startswith("REFUSING TO REAP")


class TestTheCommand:
    def _write(self, tmp_path, payload):
        path = tmp_path / "reapers.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_an_unconfigured_run_reaps_nothing_and_says_so(self, tmp_path):
        reaping = reap(config_path=self._write(tmp_path, {}), **paths(tmp_path))

        assert reaping.ready == ()
        assert reaping.harvests == ()

    def test_a_configured_lane_that_cannot_look_still_produces_a_harvest(self, tmp_path):
        """No odds key here, so the arb lane reports COULD_NOT_LOOK rather than silence."""

        from lib.reaper import COULD_NOT_LOOK

        path = self._write(tmp_path, {"arb": {"enabled": True, "balance": 500.0,
                                              "sports": ["soccer_epl"],
                                              "authority": dict(AUTHORITY)}})

        reaping = reap(config_path=path, **paths(tmp_path))

        assert reaping.ready == ("arb",)
        assert [h.status for h in reaping.harvests] == [COULD_NOT_LOOK]

    def test_settled_outcomes_reach_the_breakers_before_the_lane_looks(self, tmp_path):
        """A breaker not told about yesterday's four losses permits a fifth position.

        Asserted against the reaper's OWN breakers object rather than a freshly loaded
        one, because that is the failure mode: applying to a second instance writes the
        trip to disk and leaves the reaper checking the armed copy it loaded at assembly
        time — tripping and permitting in the same run.
        """

        from lib.breakers import TRIPPED
        from lib.outcomes import OutcomeLedger

        book = OutcomeLedger(tmp_path / "outcomes.json")
        for index in range(4):
            position = book.open_position("arb", f"match {index}", 5.0,
                                          at=f"2026-08-03T0{index}:00:00Z")
            book.settle(position.position_id, 0.0)
        book.save()

        reaping = reap(config_path=self._write(tmp_path, config()),
                       ledger_path=tmp_path / "outcomes.json", **paths(tmp_path))

        arb = next(a for a in reaping.assemblies if a.lane == "arb")
        assert arb.reaper.breakers.state.status == TRIPPED

    def test_the_applications_are_carried_and_printed(self, tmp_path):
        reaping = reap(config_path=self._write(tmp_path, config()),
                       ledger_path=tmp_path / "outcomes.json", **paths(tmp_path))

        assert len(reaping.applications) == 2      # arb and stocks; crypto is disabled
        assert "OUTCOMES APPLIED BEFORE REAPING" in reaping.describe()

    def test_a_lane_holding_outcomes_with_no_breakers_is_reported(self, tmp_path):
        """Otherwise its losses reach nothing while the report reads tidy."""

        from lib.outcomes import OutcomeLedger

        book = OutcomeLedger(tmp_path / "outcomes.json")
        position = book.open_position("crypto", "0xdead", 100.0, at="2026-08-03T01:00:00Z")
        book.settle(position.position_id, 0.0)
        book.save()

        reaping = reap(config_path=self._write(tmp_path, config()),
                       ledger_path=tmp_path / "outcomes.json", **paths(tmp_path))

        assert "its results reach nothing" in reaping.describe()

    def test_an_unreadable_ledger_does_not_silently_apply_an_empty_day(self, tmp_path):
        (tmp_path / "outcomes.json").write_text("{not json", encoding="utf-8")

        reaping = reap(config_path=self._write(tmp_path, config()),
                       ledger_path=tmp_path / "outcomes.json", **paths(tmp_path))

        assert all(a.refusal for a in reaping.applications)
        assert "the day went fine" in reaping.describe()

    def test_the_kill_switch_does_not_hide_the_lanes(self, tmp_path):
        """A halted lane still reports. Silence would look like nothing to do."""

        (tmp_path / "HALT").write_text("stop", encoding="utf-8")
        path = self._write(tmp_path, config())

        reaping = reap(config_path=path, **paths(tmp_path))

        assert "arb" in reaping.ready
