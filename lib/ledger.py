"""What the facts were last time, so a change can be noticed rather than assumed.

A review is a snapshot. It says what was true at a block height or in a filing, and says
nothing about tomorrow. The gap between "reviewed once" and "still true" is where a holder
actually lives, and closing it needs no forecast at all -- only a memory of the last
observation and the honesty to distinguish four things that look alike:

    FIRST_SEEN   no baseline; this is a record, not a finding
    UNCHANGED    read successfully, same as before
    CHANGED      read successfully, different from before
    ABSENT       read successfully, and the fact is no longer reported
    UNREADABLE   NOT read at all this time

`UNREADABLE` and `ABSENT` are the pair that matters, and conflating them is the defect this
repository keeps meeting. A rate-limited node and a contract whose owner was renounced both
leave the field empty. One is a fact about the world; the other is a fact about the network,
and reporting the second as the first would announce a change nobody made.

So an unreadable observation **never overwrites the baseline**. If it did, the next run
would find no history, report FIRST_SEEN, and quietly forget that anything was ever known --
a monitor that loses its memory every time a request times out is worse than no monitor,
because it looks like one.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from lib.store import JSON_BACKEND, Receipt, StoreStatus, inspect

def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


FIRST_SEEN = "FIRST_SEEN"
UNCHANGED = "UNCHANGED"
CHANGED = "CHANGED"
ABSENT = "ABSENT"
UNREADABLE = "UNREADABLE"

# Changes that mean a prior review can no longer be relied upon. Distinguished from the
# rest because a monitor that shouts equally about everything trains its reader to ignore
# it, and the whole point is to be believed on the day it matters.
MATERIAL_FACTS = frozenset({
    "implementation", "admin", "owner", "masterMinter", "paused", "proxy_status",
})


@dataclass(frozen=True, slots=True)
class Observation:
    """One fact about one subject at one time, or the fact that it could not be read."""

    subject: str
    fact: str
    value: str
    observed_at: str
    source: str = ""
    readable: bool = True

    @property
    def key(self) -> tuple[str, str]:
        return (self.subject, self.fact)


@dataclass(frozen=True, slots=True)
class Change:
    status: str
    subject: str
    fact: str
    before: str = ""
    after: str = ""
    observed_at: str = ""
    reason: str = ""

    @property
    def is_material(self) -> bool:
        return self.status == CHANGED and self.fact in MATERIAL_FACTS

    def describe(self) -> str:
        head = "!! MATERIAL" if self.is_material else f"   {self.status}"
        if self.status == CHANGED:
            return f"{head}  {self.subject}  {self.fact}\n        was: {self.before}\n        now: {self.after}"
        if self.status == ABSENT:
            return (
                f"{head}  {self.subject}  {self.fact}\n"
                f"        was: {self.before}\n"
                f"        now: no longer reported. The read succeeded and the fact is gone,"
                f" which is different from not having been read."
            )
        if self.status == UNREADABLE:
            return (
                f"{head}  {self.subject}  {self.fact}: could not be read ({self.reason}). "
                f"The previous value stands and is NOT contradicted."
            )
        if self.status == FIRST_SEEN:
            return f"{head}  {self.subject}  {self.fact} = {self.after}"
        return f"{head}  {self.subject}  {self.fact}"


class Ledger:
    """Latest known value per (subject, fact), persisted as plain JSON.

    Plain JSON on purpose: the file outlives any container, can be committed, diffed and
    read by a person, and needs no service to be running to be useful.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.receipt_path = self.path.with_suffix(".receipt.json")
        self._entries: dict[tuple[str, str], Observation] = {}
        rows: int | None = 0
        reason = ""
        if self.path.is_file():
            try:
                for row in json.loads(self.path.read_text(encoding="utf-8")):
                    observation = Observation(**row)
                    self._entries[observation.key] = observation
                rows = len(self._entries)
            except (OSError, ValueError, TypeError) as error:
                # A ledger that will not parse has NOT been read, and reporting its facts
                # as absent would announce changes nobody made.
                rows, reason = None, f"{type(error).__name__}: {error}"[:120]
        # A ledger whose file is gone reports zero entries and would call every fact
        # FIRST_SEEN, which is indistinguishable from a first run. The receipt is what
        # tells them apart, and it outlives the data because it names no subjects.
        self.status: StoreStatus = inspect(
            self.path.name, receipt_path=self.receipt_path, rows_found=rows, reason=reason
        )

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, subject: str, fact: str) -> Observation | None:
        return self._entries.get((subject, fact))

    def compare(self, observations: Sequence[Observation]) -> list[Change]:
        """What moved since last time. Does not write; `record` does that."""

        changes: list[Change] = []
        for current in observations:
            previous = self._entries.get(current.key)
            if not current.readable:
                changes.append(Change(
                    UNREADABLE, current.subject, current.fact,
                    before=previous.value if previous else "",
                    observed_at=current.observed_at, reason=current.value,
                ))
            elif previous is None:
                changes.append(Change(
                    FIRST_SEEN, current.subject, current.fact,
                    after=current.value, observed_at=current.observed_at,
                ))
            elif not previous.readable:
                # The baseline itself was never a real reading, so this is the first
                # actual observation rather than a change from one.
                changes.append(Change(
                    FIRST_SEEN, current.subject, current.fact,
                    after=current.value, observed_at=current.observed_at,
                ))
            elif current.value == previous.value:
                changes.append(Change(
                    UNCHANGED, current.subject, current.fact,
                    before=previous.value, after=current.value,
                    observed_at=current.observed_at,
                ))
            elif not current.value:
                changes.append(Change(
                    ABSENT, current.subject, current.fact,
                    before=previous.value, observed_at=current.observed_at,
                ))
            else:
                changes.append(Change(
                    CHANGED, current.subject, current.fact,
                    before=previous.value, after=current.value,
                    observed_at=current.observed_at,
                ))
        return changes

    def record(self, observations: Iterable[Observation]) -> None:
        """Update the baseline, and NEVER let an unreadable observation overwrite one.

        A monitor that forgets what it knew whenever a request times out is worse than no
        monitor: the next run finds no history, reports FIRST_SEEN, and looks like it is
        working.
        """

        for observation in observations:
            if not observation.readable and observation.key in self._entries:
                continue
            self._entries[observation.key] = observation

    def save(self, when: str = "") -> None:
        rows = [asdict(o) for o in sorted(self._entries.values(), key=lambda o: o.key)]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        # The receipt is committable and the data is not: it carries a count and dates,
        # never a subject, so a public repository can hold proof the store existed without
        # publishing what is being watched.
        previous = Receipt.load(self.receipt_path) or Receipt(self.path.name, JSON_BACKEND)
        previous.written(when or _now(), len(rows)).save(self.receipt_path)


def summarise(changes: Sequence[Change]) -> str:
    """The material ones first, then everything else, then what could not be read."""

    material = [c for c in changes if c.is_material]
    other = [c for c in changes if c.status == CHANGED and not c.is_material]
    absent = [c for c in changes if c.status == ABSENT]
    unreadable = [c for c in changes if c.status == UNREADABLE]
    first = [c for c in changes if c.status == FIRST_SEEN]

    lines: list[str] = []
    if material:
        lines.append("MATERIAL CHANGES -- a prior review of this subject may no longer hold:")
        lines += [c.describe() for c in material]
        lines.append("")
    if other or absent:
        lines.append("Other changes:")
        lines += [c.describe() for c in other + absent]
        lines.append("")
    if unreadable:
        lines.append("Could not be read this run. Previous values stand:")
        lines += [c.describe() for c in unreadable]
        lines.append("")
    if first:
        lines.append(f"{len(first)} fact(s) recorded for the first time; no comparison possible yet.")
    compared = len(changes) - len(first)
    if not any((material, other, absent, unreadable)) and compared:
        readable = compared
        lines.append(
            f"No change across {readable} fact(s) read. This says nothing about facts not "
            f"in the ledger."
        )
    return "\n".join(lines)
