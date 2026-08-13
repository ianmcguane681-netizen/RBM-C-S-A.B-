"""Cadences describe an intention until something invokes them.

Every lane carries a `cadence_seconds` and `run.py --go` runs whatever is due — but `--go`
is one shot, and **nothing invoked it**. The Procfile declared a web process and no worker;
there was no cron entry, no timer and no workflow anywhere in the repository. Placing an
API key would not have changed that: the lanes would have been ready and nobody would have
asked them to run.

The failure this must not have is silence. A supervisor that dies leaves a system that
looks entirely normal — the dashboard renders, the ledger is intact, every lane reports the
state it was last left in — while nothing at all happens. That is this repository's founding
defect at the level of the process table, so the loop leaves a heartbeat and `status` calls
it STALE when it stops moving.
"""
from __future__ import annotations

import json

import run
import status


class TestTheLanesAreActuallyInvoked:
    def test_a_worker_process_exists_to_run_them(self):
        """The Procfile declared a web process and no worker, which is the whole bug.

        With only `web:`, the operator API serves a dashboard describing cadences that
        nothing is keeping.
        """

        procfile = (run.Path(__file__).parent.parent / "Procfile").read_text()

        assert "run.py --serve" in procfile

    def test_the_supervisor_runs_the_due_lanes_each_tick(self, tmp_path, monkeypatch):
        ticks = []
        monkeypatch.setattr(run, "main", lambda go: ticks.append(go) or 0)

        run.serve(interval=0, limit=3, heartbeat=tmp_path / "heartbeat.json")

        assert ticks == [True, True, True]

    def test_one_failed_tick_does_not_end_the_schedule(self, tmp_path, monkeypatch):
        """Ending the loop would turn one broken tick into a permanently stopped system,
        and the stopping would be invisible."""

        calls = []

        def flaky(go):
            calls.append(go)
            if len(calls) == 2:
                raise RuntimeError("a lane blew up")
            return 0

        monkeypatch.setattr(run, "main", flaky)

        run.serve(interval=0, limit=4, heartbeat=tmp_path / "heartbeat.json")

        assert len(calls) == 4


class TestAStoppedSupervisorIsVisible:
    def _beat(self, tmp_path, monkeypatch, **overrides):
        path = tmp_path / "data" / "heartbeat.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        beat = {"pid": 1, "started_at": "2026-08-05T09:00:00Z",
                "last_tick_at": "2026-08-05T09:00:00Z", "ticks": 5, "tick_seconds": 60}
        beat.update(overrides)
        path.write_text(json.dumps(beat), encoding="utf-8")
        monkeypatch.setattr(run, "HEARTBEAT", path)
        return path

    def test_a_system_nobody_has_supervised_says_so(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run, "HEARTBEAT", tmp_path / "absent.json")

        state = status._scheduler_state()

        assert state["status"] == "NEVER_STARTED"
        assert "intention" in state["reason"]

    def test_a_heartbeat_that_stopped_moving_is_stale_rather_than_quiet(
        self, tmp_path, monkeypatch
    ):
        """The case that costs: cadences on the page describing something that is not
        happening, with nothing else on the page looking any different."""

        self._beat(tmp_path, monkeypatch)      # last tick is hours old

        state = status._scheduler_state()

        assert state["status"] == "STALE"
        assert "no lane is being run" in state["reason"]

    def test_a_live_heartbeat_reports_running(self, tmp_path, monkeypatch):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        self._beat(tmp_path, monkeypatch, last_tick_at=now)

        state = status._scheduler_state()

        assert state["status"] == "RUNNING"
        assert state["reason"] is None

    def test_an_unreadable_stamp_is_never_treated_as_recent(self, tmp_path, monkeypatch):
        """`None` age means STALE. An unparseable timestamp must not read as young."""

        self._beat(tmp_path, monkeypatch, last_tick_at="not a timestamp")

        assert status._scheduler_state()["status"] == "STALE"

    def test_an_unreadable_heartbeat_is_not_a_stopped_one(self, tmp_path, monkeypatch):
        path = tmp_path / "data" / "heartbeat.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json", encoding="utf-8")
        monkeypatch.setattr(run, "HEARTBEAT", path)

        state = status._scheduler_state()

        assert state["status"] == "UNREADABLE"
        assert state["reason"]

    def test_the_heartbeat_records_enough_to_tell_a_restart_from_a_long_run(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(run, "main", lambda go: 0)
        path = tmp_path / "heartbeat.json"

        run.serve(interval=0, limit=2, heartbeat=path)
        beat = json.loads(path.read_text(encoding="utf-8"))

        assert beat["ticks"] == 2
        assert beat["started_at"] and beat["last_tick_at"]
        assert beat["pid"]

    def test_a_supervisor_does_not_die_of_its_own_bookkeeping(self, tmp_path, monkeypatch):
        """A heartbeat it cannot write must not stop the thing the heartbeat describes."""

        blocked = tmp_path / "not-a-dir"
        blocked.write_text("x", encoding="utf-8")
        monkeypatch.setattr(run, "main", lambda go: 0)

        assert run.serve(interval=0, limit=2, heartbeat=blocked / "beat.json") == 0


class TestAFailingDigestDoesNotFloodTheLog:
    """A digest that did not go is deliberately not recorded as told, so the next tick
    tries again — correct, and at a sixty-second tick it meant a fresh attempt every
    minute. Each one appends to a bounded log, so a revoked token filled the whole record
    with failures in an afternoon. The retry is right; its cadence was the tick's."""

    def test_the_digest_is_not_attempted_on_every_tick(self, tmp_path, monkeypatch):
        attempts = []
        monkeypatch.setattr(run, "main", lambda go: 0)
        monkeypatch.setattr(run, "_digest_once", lambda announcer: attempts.append(1))

        run.serve(interval=0, limit=5, heartbeat=tmp_path / "heartbeat.json")

        assert attempts == [1]

    def test_the_first_tick_always_tries(self, tmp_path, monkeypatch):
        """A supervisor restarted at 09:00 must not wait out a retry window first, or a
        machine that keeps restarting sends nothing ever — which is the failure the whole
        heartbeat argument is built on."""

        attempts = []
        monkeypatch.setattr(run, "main", lambda go: 0)
        monkeypatch.setattr(run, "_digest_once", lambda announcer: attempts.append(1))

        run.serve(interval=0, limit=1, heartbeat=tmp_path / "heartbeat.json")

        assert attempts == [1]

    def test_a_tick_past_the_retry_window_tries_again(self, tmp_path, monkeypatch):
        """The window throttles the retry; it must not cancel it."""

        attempts = []
        monkeypatch.setattr(run, "main", lambda go: 0)
        monkeypatch.setattr(run, "_digest_once", lambda announcer: attempts.append(1))
        monkeypatch.setattr(run, "DIGEST_RETRY_SECONDS", 0)

        run.serve(interval=0, limit=3, heartbeat=tmp_path / "heartbeat.json")

        assert attempts == [1, 1, 1]
