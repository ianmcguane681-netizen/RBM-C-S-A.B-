"""Emit Postgres DDL for the review store, derived from the live SQLite schema.

    python tools/pg_schema.py > migrations/0001_review_store.sql

Derived rather than hand-written, for a reason this repository paid for recently: RBM-004
and RBM-005 shipped with `"RBM-003"` welded into their schemas because the packages were
copied by hand, and the fix was to generate them from the profile. A migration transcribed
by hand from seventeen tables would carry the same class of error, and a column quietly
dropped in transcription is invisible until something needs it.

Two things this adds that SQLite could only approximate:

**Immutability by grant, not by trigger.** The store enforces its audit chain with
`BEFORE UPDATE ... RAISE(ABORT)`. A trigger can be dropped by whoever can write. `REVOKE
UPDATE, DELETE` cannot be undone by the role it was revoked from, so the guarantee holds
against the application itself rather than only against its own bugs.

**Deny-by-default row security.** A local SQLite file is reachable by whoever holds the
container. A hosted database is reachable by whoever holds a key, and this repository is
public. Every table ships with RLS enabled and no permissive policy, so a leaked anon key
reads nothing until a policy is written deliberately.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

STORE = Path("data/review_board.sqlite3")

#: Tables whose rows are facts about what happened. Nothing may ever rewrite one.
#: Taken from the triggers the SQLite store already carries, plus the decision tables.
APPEND_ONLY = (
    "review_packages", "evidence_references", "conflict_declarations", "review_reports",
    "findings", "decision_candidates", "decision_ratifications", "publications",
    "audit_log", "report_evidence_links", "finding_evidence_links", "remediation_plans",
    "board_decisions",
)

TYPES = (
    (re.compile(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", re.I), "BIGSERIAL PRIMARY KEY"),
    (re.compile(r"\bINTEGER\b", re.I), "BIGINT"),
    (re.compile(r"\bTEXT\b", re.I), "TEXT"),
    (re.compile(r"\bREAL\b", re.I), "DOUBLE PRECISION"),
    (re.compile(r"\bBLOB\b", re.I), "BYTEA"),
    (re.compile(r"\bAUTOINCREMENT\b", re.I), ""),
)


def to_postgres(sql: str) -> str:
    for pattern, replacement in TYPES:
        sql = pattern.sub(replacement, sql)
    # SQLite tolerates a bare `"table"` quoting style Postgres also accepts, so identifiers
    # pass through. What does not is IF NOT EXISTS placement, which is identical, and
    # SQLite's implicit rowid, which the runtime never relies on.
    return sql.strip().rstrip(";")


def main() -> int:
    if not STORE.is_file():
        print(f"-- no store at {STORE}; nothing to derive from", file=sys.stderr)
        return 2

    connection = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    rows = connection.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL "
        "ORDER BY name"
    ).fetchall()

    out: list[str] = [
        "-- Review store, derived from the live SQLite schema by tools/pg_schema.py.",
        "-- Do not edit by hand: regenerate. Hand-transcription is how RBM-004 shipped",
        "-- with another profile's identity welded into its schemas.",
        "",
        "BEGIN;",
        "",
        "CREATE SCHEMA IF NOT EXISTS board;",
        "SET search_path TO board, public;",
        "",
    ]

    names: list[str] = []
    for name, sql in rows:
        if name.startswith("sqlite_"):
            continue
        names.append(name)
        out.append(to_postgres(sql) + ";")
        out.append("")

    out += [
        "-- Row security: deny by default, on every table, before any data lands.",
        "-- A permissive default plus a public repository is how a published decision",
        "-- becomes editable by anyone holding an anon key.",
        "",
    ]
    for name in names:
        out.append(f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY;')
        out.append(f'ALTER TABLE "{name}" FORCE ROW LEVEL SECURITY;')
    out.append("")

    out += [
        "-- Immutability by grant rather than by trigger. A trigger can be dropped by",
        "-- whoever can write; a revoked privilege cannot be restored by the role it was",
        "-- revoked from, so the guarantee holds against the application itself.",
        "",
    ]
    for name in APPEND_ONLY:
        if name in names:
            out.append(f'REVOKE UPDATE, DELETE ON "{name}" FROM PUBLIC, anon, authenticated;')
    out.append("")

    missing = [n for n in APPEND_ONLY if n not in names]
    if missing:
        # Named rather than skipped. A guard that silently covers nothing is the defect
        # this repository keeps meeting, and it would read here as "the table is protected".
        out.append("-- NOT PRESENT in the source store, so NOT protected here. This is a")
        out.append("-- statement about the schema that was read, not a claim of safety:")
        for name in missing:
            out.append(f"--   {name}")
        out.append("")

    out += [
        "COMMIT;",
        "",
        f"-- {len(names)} table(s) derived; "
        f"{sum(1 for n in APPEND_ONLY if n in names)} marked append-only.",
    ]
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
