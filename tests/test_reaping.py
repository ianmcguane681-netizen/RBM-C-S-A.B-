"""A lane nobody configured must never appear beside a lane that looked and found nothing.

The recurring defect, at the level of the command a person actually types. `--reap` runs
every lane; if two of them were never set up, printing tidy "nothing found" lines for them
is a confident report assembled out of an empty config file.

So assembly is a first-class result with five outcomes — CONFIGURED, NOT_CONFIGURED,
UNREADABLE, REFUSED, PARKED — and an unparseable config refuses the whole run rather than
treating every lane as unconfigured.

`PARKED` is the fifth and it draws the same line one level up. Crypto was stood down on
2026-08-29; a lane simply removed from `LANES` would be *absent*, and absent reads as never
written. The tests below therefore assert that a parked lane is still printed, still
carries the reason it was parked, and is never reported as NOT_CONFIGURED — which would
say nobody had set it up, when in fact somebody decided.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.reaping import (
    CONFIGURED,
    LANES,
    NOT_CONFIGURED,
    PARKED,
    PARKED_LANES,
    REFUSED,
    UNREADABLE,
    Assembly,
    Reaping,
    assemble,
    assemble_crypto,
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

    def test_a_parked_lane_is_printed_after_the_running_ones(self, tmp_path):
        """The running lanes first, then what deliberately did not run. Order is the
        message: a reader scanning the top of the report sees what was actually asked."""

        assembled = assemble(config(), **paths(tmp_path))

        assert [a.lane for a in assembled[:len(LANES)]] == list(LANES)
        assert [a.lane for a in assembled[len(LANES):]] == list(PARKED_LANES)

    def test_a_disabled_lane_is_not_configured_rather_than_absent(self, tmp_path):
        stocks = assemble(config(stocks={"enabled": False}), **paths(tmp_path))[1]

        assert stocks.status == NOT_CONFIGURED

    def test_not_configured_says_it_did_not_look(self, tmp_path):
        described = assemble(
            config(stocks={"enabled": False}), **paths(tmp_path))[1].describe()

        assert "did not look" in described
        assert "has not reported that there is nothing to find" in described

    def test_an_empty_config_leaves_every_running_lane_unconfigured(self, tmp_path):
        assembled = assemble({}, **paths(tmp_path))

        running = {a.status for a in assembled if a.lane in LANES}
        assert running == {NOT_CONFIGURED}

    def test_a_parked_lane_is_parked_rather_than_unconfigured(self, tmp_path):
        """The distinction the status exists for, and the one most worth a test.

        NOT_CONFIGURED means nobody set this up and it has an obvious remedy: set it up.
        PARKED means somebody looked at it and decided. Reporting the second as the first
        sends the next reader off to configure a lane that is working exactly as intended.
        """

        crypto = next(a for a in assemble({}, **paths(tmp_path)) if a.lane == "crypto")

        assert crypto.status == PARKED
        assert crypto.status != NOT_CONFIGURED

    def test_a_parked_lane_carries_the_reason_it_was_parked(self, tmp_path):
        """"PARKED" alone trains a reader to skim. The whole value is the sentence after
        it: who decided, when, and what would undo it."""

        crypto = next(a for a in assemble({}, **paths(tmp_path)) if a.lane == "crypto")

        assert "Ian" in crypto.reason and "2026-08-29" in crypto.reason
        assert "move 'crypto' back into LANES" in crypto.reason
        assert "did not fail to look" in crypto.describe()

    def test_a_parked_lane_is_parked_even_when_the_config_still_enables_it(self, tmp_path):
        """An `enabled: true` left in the file must not resurrect a lane by accident.

        The rotation is the registry in code, which is reviewed; the config file is data on
        a box. A stale key in the second one is the likeliest way a stood-down lane starts
        spending money again without anybody deciding it should.
        """

        still_on = config(crypto={"enabled": True, "balance": 100.0, "wallet": "0x" + "a" * 40})

        crypto = next(a for a in assemble(still_on, **paths(tmp_path)) if a.lane == "crypto")

        assert crypto.status == PARKED
        assert crypto.reaper is None

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

    def test_a_bookmaker_list_written_as_one_string_is_refused(self, tmp_path):
        """`"bookmakers": "skybet"` iterates into six one-letter books, and the API is fine
        with that.

        It answers 200 with none of them present, the lane finds no arb, and nothing
        anywhere reports an error. A typo that produces a quiet market rather than a
        failure is the shape of defect this repository refuses at the config boundary.
        """

        broken = config(arb={"enabled": True, "balance": 500.0, "bookmakers": "skybet",
                             "authority": dict(AUTHORITY)})

        arb = assemble(broken, **paths(tmp_path))[0]

        assert arb.status == REFUSED
        assert "JSON list" in arb.reason

    def test_a_configured_bookmaker_list_reaches_the_lane(self, tmp_path):
        """Narrowing the scan is an operator's written choice, so it comes from the file."""

        narrowed = config(arb={"enabled": True, "balance": 500.0,
                               "bookmakers": ["skybet", "paddypower"],
                               "authority": dict(AUTHORITY)})

        arb = assemble(narrowed, **paths(tmp_path))[0]

        assert arb.status == CONFIGURED

    def test_a_zero_balance_ringfence_is_refused(self, tmp_path):
        broken = config(arb={"enabled": True, "balance": 0.0, "authority": dict(AUTHORITY)})

        arb = assemble(broken, **paths(tmp_path))[0]

        assert arb.status == REFUSED
        assert "positive balance" in arb.reason

    def test_crypto_without_a_wallet_is_refused(self, tmp_path):
        """Asserted against the builder rather than through `assemble`, because the lane
        is parked and `assemble` never reaches its builder now.

        Kept rather than deleted: parking is meant to be reversible in one line, and a
        builder whose tests were removed with its rotation entry is a lane that comes back
        untested. The refusal it makes is still the refusal it will make on the day
        somebody moves 'crypto' back into LANES.
        """

        crypto = assemble_crypto({"enabled": True, "balance": 100.0}, **paths(tmp_path))

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


class TestTheShippedExampleCanActuallyPlace:
    """A config whose grant exceeds its own per-position cap refuses every position.

    That is exactly what the example shipped with — a standing grant of 50 against a cap of
    25 — written in different sessions and never checked against each other. Every arb would
    have sized to 50 and been refused by its own breakers, and the first live session would
    have been spent working out why.
    """

    def _config(self):
        import json
        from pathlib import Path

        return json.loads(Path("examples/reapers.example.json").read_text("utf-8"))

    def test_the_arb_grant_fits_inside_its_own_per_position_cap(self):
        from lib.breakers import Ringfence

        arb = self._config()["arb"]
        ring = Ringfence("arb", float(arb["balance"]),
                         per_position_pct=float(arb.get("per_position_pct", 5.0)))

        assert float(arb["authority"]["max_exposure"]) <= ring.per_position_limit

    def test_every_lane_s_ringfence_constructs(self):
        """A per-position cap above the deployed cap raises, so this catches that too."""

        from lib.breakers import Ringfence

        config = self._config()
        for lane in ("arb", "stocks", "crypto"):
            settings = config[lane]
            Ringfence(lane, float(settings["balance"]),
                      per_position_pct=float(settings.get("per_position_pct", 5.0)),
                      daily_loss_pct=float(settings.get("daily_loss_pct", 3.0)),
                      max_deployed_pct=float(settings.get("max_deployed_pct", 40.0)))

    def test_a_lane_can_reach_ready_within_its_own_limits(self, tmp_path):
        """The end-to-end version: size it, hand it to the breakers, see it permitted."""

        from lib.breakers import Ringfence

        arb = self._config()["arb"]
        ring = Ringfence("arb", float(arb["balance"]))
        grant = float(arb["authority"]["max_exposure"])

        assert grant <= ring.per_position_limit <= ring.deployed_limit
