"""What actually ran, kept after the process that ran it has gone.

Everything a reap produces is currently printed and then lost. `data/orchestrator.json`
keeps a last-run time and an exit code; the harvests, the reasons and the placements exist
for the length of one stdout. So the question a person actually asks — *what did the arb
lane find on Tuesday, and what did we do about it* — has no answer, and neither does the
one the plan turns on: **prove one function produces something real before starting a
fourth**. You cannot prove it from a record that does not exist.

## This is a record, not a source of truth

`data/outcomes.json` remains the ledger. It is what the breakers read, what
`unsettled_exposure` sums, and the thing `positions.py` writes under a receipt. Nothing
here competes with it, and a reader wanting to know what is at risk should not come to this
file — a second answer to a money question is worse than no second answer, because
eventually the two disagree and nothing says which is right.

What lives here is history: runs, what each lane reported, and what was submitted. Append
only. Rows are never updated and never deleted, so a run that went badly is still on file
in the shape it went badly in.

## SQLite, with the Postgres migration as the deployment target

`migrations/0002` and `0003` define the same shape in Postgres for a deployed service, and
`data/review_board.sqlite3` is the existing precedent for a local store. SQLite is chosen
here because it needs no server, survives the process, and can be verified by running it
rather than by asserting it would work.

The column names deliberately match the migration, so moving a local journal into Postgres
is a copy rather than a translation.

## Failure to journal must never fail the run

A reap that placed an order and then could not write its diary has still placed the order.
Losing the note is bad; losing the order because of the note is worse. Every write here is
best effort, records its own failure in `last_error`, and returns rather than raising —
which is the one place in this repository where swallowing an exception is correct, and it
is correct because the alternative fails in the expensive direction.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

JOURNAL = Path("data/journal.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reaper_runs (
    run_id TEXT PRIMARY KEY,
    lane TEXT,
    dry_run INTEGER NOT NULL,
    status TEXT NOT NULL,
    looked INTEGER,
    requested_by TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    refusal TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS harvests (
    harvest_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES reaper_runs(run_id),
    lane TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    instruction TEXT,
    observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES reaper_runs(run_id),
    lane TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    position_id TEXT,
    client_order_id TEXT,
    requested_quantity REAL,
    filled_quantity REAL,
    reason TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS runs_started_at ON reaper_runs(started_at);
CREATE INDEX IF NOT EXISTS harvests_run ON harvests(run_id);
CREATE INDEX IF NOT EXISTS executions_run ON executions(run_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


#: Which runs belong to which lane, for `activity_since`. Three sources unioned, because a
#: run reaches a lane by two different routes: the scheduler invokes `--reap <lane>` and the
#: row names it, while an all-lane `--reap` names none and is only connected to a lane by
#: what it produced. Reaching runs through `harvests` alone — which this used to do — made a
#: run that harvested nothing invisible, so a REFUSED lane reported as never having run.
#: `UNION` rather than `UNION ALL`: the two routes overlap on every ordinary run.
_LANE_RUNS = (
    "WITH lane_runs AS ("
    " SELECT r.lane AS lane, r.run_id AS run_id FROM reaper_runs r"
    "  WHERE r.dry_run = 0 AND r.started_at >= ? AND r.lane IS NOT NULL"
    " UNION"
    " SELECT h.lane, h.run_id FROM harvests h"
    "  JOIN reaper_runs r ON h.run_id = r.run_id"
    "  WHERE r.dry_run = 0 AND r.started_at >= ?"
    " UNION"
    " SELECT e.lane, e.run_id FROM executions e"
    "  JOIN reaper_runs r ON e.run_id = r.run_id"
    "  WHERE r.dry_run = 0 AND r.started_at >= ?"
    ") "
)


class Journal:
    """An append-only record of runs. Readable, and never in the way of a run."""

    def __init__(self, path: str | Path = JOURNAL) -> None:
        self.path = Path(path)
        self.readable = True
        self.reason = ""
        self.last_error = ""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(SCHEMA)
        except (OSError, sqlite3.Error) as error:
            # UNREADABLE, and stated. A journal that cannot open is not an empty journal,
            # and `describe` says which of the two a reader is looking at.
            self.readable = False
            self.reason = f"{type(error).__name__}: {error}"[:160]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def record(self, reaping: Any, *, lane: str = "", dry_run: bool = False,
               requested_by: str = "") -> str:
        """One run, its harvests and its placements, in a single transaction.

        Returns the run id, or `""` when nothing was written. **Never raises.** A reap that
        placed an order and then could not write its diary has still placed the order, and
        taking the run down over the note would fail in the expensive direction.

        The status is `Reaping.to_dict()`'s, so the four kinds of nothing stay apart here
        exactly as they do everywhere else: a run that could not look is not a run that
        found nothing, three weeks later and read from a table.
        """

        if not self.readable:
            return ""

        payload = reaping.to_dict()
        run_id = str(uuid.uuid4())
        at = _now()
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO reaper_runs (run_id, lane, dry_run, status, looked, "
                    "requested_by, started_at, completed_at, refusal) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (run_id, lane or None, int(dry_run), payload["status"],
                     int(bool(getattr(reaping, "looked", False))), requested_by, at, at,
                     payload.get("reason") or ""),
                )
                connection.executemany(
                    "INSERT INTO harvests (harvest_id, run_id, lane, subject, status, "
                    "reason, instruction, observed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [(str(uuid.uuid4()), run_id, row["lane"], row.get("subject") or "",
                      row["status"], row.get("reason") or "",
                      json.dumps(row.get("instruction")) if row.get("instruction") else None,
                      row.get("at") or at)
                     for row in payload.get("harvests", [])],
                )
                connection.executemany(
                    "INSERT INTO executions (execution_id, run_id, lane, subject, status, "
                    "position_id, client_order_id, requested_quantity, filled_quantity, "
                    "reason, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(str(uuid.uuid4()), run_id, row["lane"], row.get("subject") or "",
                      row["status"], row.get("position_id"), row.get("client_order_id"),
                      row.get("requested_quantity"), row.get("filled_quantity"),
                      row.get("reason") or "", at)
                     for row in payload.get("placements", [])],
                )
        except (OSError, sqlite3.Error, KeyError, TypeError) as error:
            self.last_error = f"{type(error).__name__}: {error}"[:160]
            return ""
        return run_id

    def recent_runs(self, limit: int = 20) -> tuple[dict, ...]:
        """Newest first. An unreadable journal returns nothing and says so via `readable`."""

        if not self.readable:
            return ()
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT run_id, lane, dry_run, status, looked, started_at, refusal "
                    "FROM reaper_runs ORDER BY started_at DESC, rowid DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        except (OSError, sqlite3.Error):
            return ()
        return tuple(
            {"run_id": r[0], "lane": r[1], "dry_run": bool(r[2]), "status": r[3],
             "looked": None if r[4] is None else bool(r[4]), "at": r[5],
             "reason": r[6] or None}
            for r in rows
        )

    def activity_since(self, since: str) -> dict[str, Any]:
        """What each lane actually FOUND in a window, per lane, for the daily digest.

        `recent_runs` answers "what happened lately" for a reader with a screen. This
        answers the narrower question a digest needs: for each lane, how many times it ran,
        what its harvests were, and what became of anything placed — because a digest
        saying `reap-arb COMPLETED` reports that a process exited, and the whole argument
        for a daily message is that it distinguishes a lane which looked and found nothing
        from one which never looked at all.

        **Unreadable is a status, not an empty result.** A journal that will not open
        returns `UNREADABLE` with no lanes, and the caller must render that as "what these
        lanes found is unknown". Returning empty counts would put "found nothing" in a
        message on the day the record went missing, which is the founding defect delivered
        to a phone.

        **A run is counted from `reaper_runs`, never from the harvests it produced.** This
        query used to reach the runs table only through a JOIN from `harvests`, so a run
        that harvested nothing did not exist: a config that would not parse makes every
        lane REFUSED before it is assembled, produces no harvests, and the digest then
        reported the lane as `NOT_RUN` — nobody asked it — while the REFUSED row sat in the
        table being discarded by the join. "Ran and was refused" and "was never asked" send
        a person to different places, so the run count and the last refusal come from the
        runs table and only the counts come from the harvests.

        A run belongs to a lane if `reaper_runs.lane` names it OR it produced a harvest or
        a placement for it. Both halves are needed and the first alone is not enough: an
        all-lane `--reap` is recorded with no lane, so counting only the named ones would
        report a lane whose findings are sitting in the table as NOT_RUN — the same defect
        pointing the other way. What survives both is a run that named no lane and produced
        nothing for any, which is returned as `unattributed_runs` rather than folded into a
        lane or quietly dropped. Everything on a cadence names its lane.

        Dry runs are excluded. `--dry` is somebody at a keyboard looking, and counting it
        would report a person's curiosity as the system running on its cadence.
        """

        if not self.readable:
            return {"status": "UNREADABLE", "reason": self.reason, "lanes": {},
                    "unattributed_runs": None}
        try:
            with self._connect() as connection:
                totals = connection.execute(
                    _LANE_RUNS + "SELECT lr.lane, COUNT(DISTINCT lr.run_id), "
                    "MAX(r.started_at) FROM lane_runs lr "
                    "JOIN reaper_runs r ON lr.run_id = r.run_id GROUP BY lr.lane",
                    (since, since, since),
                ).fetchall()
                # Newest first, so the first row seen per lane is the current state. A lane
                # refused at 02:00 and fixed by 09:00 should not report the refusal.
                outcomes = connection.execute(
                    _LANE_RUNS + "SELECT lr.lane, r.status, r.refusal FROM lane_runs lr "
                    "JOIN reaper_runs r ON lr.run_id = r.run_id "
                    "ORDER BY r.started_at DESC, r.rowid DESC",
                    (since, since, since),
                ).fetchall()
                # A run that named no lane and produced nothing for any. It cannot be
                # attributed and must not be invented into one.
                unattributed = connection.execute(
                    "SELECT COUNT(*) FROM reaper_runs r "
                    "WHERE r.dry_run = 0 AND r.started_at >= ? AND r.lane IS NULL "
                    "AND NOT EXISTS (SELECT 1 FROM harvests h WHERE h.run_id = r.run_id) "
                    "AND NOT EXISTS (SELECT 1 FROM executions e WHERE e.run_id = r.run_id)",
                    (since,),
                ).fetchone()[0]
                found = connection.execute(
                    "SELECT h.lane, h.status, COUNT(*) "
                    "FROM harvests h JOIN reaper_runs r ON h.run_id = r.run_id "
                    "WHERE r.dry_run = 0 AND r.started_at >= ? GROUP BY h.lane, h.status",
                    (since,),
                ).fetchall()
                placed = connection.execute(
                    "SELECT e.lane, e.status, COUNT(*) "
                    "FROM executions e JOIN reaper_runs r ON e.run_id = r.run_id "
                    "WHERE r.dry_run = 0 AND r.started_at >= ? GROUP BY e.lane, e.status",
                    (since,),
                ).fetchall()
        except (OSError, sqlite3.Error) as error:
            return {"status": "UNREADABLE", "reason": f"{type(error).__name__}: {error}",
                    "lanes": {}, "unattributed_runs": None}

        def blank() -> dict[str, Any]:
            return {"runs": 0, "last_at": None, "harvests": {}, "placements": {},
                    "last_status": "", "last_refusal": ""}

        lanes: dict[str, dict[str, Any]] = {}
        for lane, runs, last_at in totals:
            lanes[lane] = {**blank(), "runs": runs, "last_at": last_at}
        for lane, status, refusal in outcomes:
            entry = lanes.setdefault(lane, blank())
            if not entry["last_status"]:
                entry["last_status"] = status
                entry["last_refusal"] = refusal or ""
        # A harvest or an execution whose lane never appeared in `reaper_runs.lane` still
        # gets an entry. It means an all-lane run produced it, and losing the finding
        # because the run was not attributed would be the same defect one table along.
        for lane, status, count in found:
            lanes.setdefault(lane, blank())["harvests"][status] = count
        for lane, status, count in placed:
            lanes.setdefault(lane, blank())["placements"][status] = count
        return {"status": "READ", "reason": "", "lanes": lanes,
                "unattributed_runs": unattributed}

    def placements_for(self, run_id: str) -> tuple[dict, ...]:
        if not self.readable:
            return ()
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT lane, subject, status, position_id, client_order_id, "
                    "filled_quantity, reason FROM executions WHERE run_id = ? "
                    "ORDER BY rowid", (run_id,),
                ).fetchall()
        except (OSError, sqlite3.Error):
            return ()
        return tuple(
            {"lane": r[0], "subject": r[1], "status": r[2], "position_id": r[3],
             "client_order_id": r[4], "filled_quantity": r[5], "reason": r[6] or None}
            for r in rows
        )

    def counts(self) -> dict[str, int | None]:
        """Row counts, or nulls. Nought runs recorded and an unreadable journal differ."""

        if not self.readable:
            return {"runs": None, "harvests": None, "executions": None}
        try:
            with self._connect() as connection:
                return {
                    name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                    for name in ("reaper_runs", "harvests", "executions")
                }
        except (OSError, sqlite3.Error):
            return {"runs": None, "harvests": None, "executions": None}

    def describe(self) -> str:
        if not self.readable:
            return (f"JOURNAL  UNREADABLE  {self.reason}\n"
                    f"  No run history is being kept. This is not a system that has never "
                    f"run; it is one whose record of running cannot be opened.")
        counts = self.counts()
        runs = counts.get("reaper_runs")
        if not runs:
            return ("JOURNAL  EMPTY  no run has been recorded yet. This is not the same as "
                    "a run that found nothing.")
        return (f"JOURNAL  {runs} run(s) on file, {counts.get('harvests')} harvest(s), "
                f"{counts.get('executions')} execution(s) — {self.path}")
