"""What has been scanned, when, and what came of it — so a cadence can be decided later.

Nobody knows yet how often a county is worth re-scanning. The honest response to that is
not to guess a number and put it in a cron line; it is to record what happens and let the
answer come out of the record. A county that yields four prospects in March and nothing in
April has told you something a schedule invented in advance never would.

So every completed run appends one row: the area, when, how long, and the three counts that
matter — prepared, refused, indeterminate. The dashboard reads it back as "last scanned
twelve days ago, four prepared", next to the button.

Two rules, both the same rule as everywhere else.

**A run that failed is recorded as a failure, not omitted.** A history containing only
successful runs makes a flaky source look reliable and makes "we scanned Mayo and found
nothing" indistinguishable from "the scan of Mayo died".

**An unreadable history reports `UNKNOWN`, never "never scanned".** The second would send
somebody over the same county on the day the file went missing, which is exactly the
duplicate-approach failure the seen register exists to prevent, arriving by another door.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RECORDED = "RECORDED"
NEVER_SCANNED = "NEVER_SCANNED"
UNKNOWN = "UNKNOWN"

LEDGER = Path("data/runs.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Run:
    """One scan, as it turned out."""

    area: str
    started: str
    finished: str
    prepared: int = 0
    refused: int = 0
    indeterminate: int = 0
    #: The run's own verdict on itself: LOOKED, AREA_UNKNOWN, SOURCE_UNREADABLE, FAILED.
    outcome: str = ""
    digest: str = ""
    operator: str = ""

    @property
    def days_ago(self) -> int | None:
        try:
            when = datetime.fromisoformat(self.finished or self.started)
        except (TypeError, ValueError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - when).days

    def describe(self) -> str:
        ago = self.days_ago
        when = f"{ago} day(s) ago" if ago is not None else self.finished or "unknown date"
        return (f"{self.area}: {when} — {self.prepared} prepared, {self.refused} refused, "
                f"{self.indeterminate} indeterminate ({self.outcome or 'no outcome recorded'})")


@dataclass(frozen=True, slots=True)
class Sighting:
    """What is known about one area's scanning history."""

    status: str
    area: str
    last: Run | None = None
    count: int = 0
    reason: str = ""

    def describe(self) -> str:
        if self.status == RECORDED and self.last:
            return f"RECORDED  {self.last.describe()}  ({self.count} run(s) in total)"
        if self.status == NEVER_SCANNED:
            return f"NEVER_SCANNED  {self.area} has not been scanned from this machine"
        return (f"UNKNOWN  {self.reason}\n  The history could not be read, so whether "
                f"{self.area} has been scanned is unknown. It is not therefore fresh.")


class History:
    """An append-only list of runs. Small, boring, and the input to any future cadence."""

    def __init__(self, path: Path | str = LEDGER) -> None:
        self.path = Path(path)

    def _load(self) -> list[dict] | None:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, list) else None

    def record(self, run: Run) -> bool:
        rows = self._load()
        if rows is None:
            return False
        rows.append(asdict(run))
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        except OSError:
            return False
        return True

    def runs(self, limit: int = 50) -> list[Run]:
        rows = self._load()
        if not rows:
            return []
        out = []
        for row in rows[-limit:][::-1]:
            try:
                out.append(Run(**row))
            except TypeError:
                continue
        return out

    def about(self, area: str) -> Sighting:
        rows = self._load()
        if rows is None:
            return Sighting(UNKNOWN, area, reason=f"{self.path} will not parse")
        matching = [row for row in rows if str(row.get("area", "")).casefold()
                    == area.casefold()]
        if not matching:
            return Sighting(NEVER_SCANNED, area)
        try:
            last = Run(**matching[-1])
        except TypeError:
            return Sighting(UNKNOWN, area, reason="the last row for this area will not load")
        return Sighting(RECORDED, area, last, len(matching))
