"""Whether this business has been prepared before, and how many times.

A pipeline pointed at a county and run weekly will find the same businesses every week. A
person working from its output will prepare, and eventually contact, the same shop several
times — which is the one failure mode that turns a generous piece of speculative work into
something a recipient describes as spam.

Three decisions, carried over from the parent repository's register unchanged, because the
arguments transfer exactly.

**Identity is the source's stable id, never the name.** `node/1234567`. Two takeaways in
one county share a name more often than anyone expects, and a shop that rebrands is still
the same shop with the same owner who has already had one email.

**Seen before is not a refusal.** A business prepared four months ago with no reply may be
worth a second approach, and that judgement belongs to the person, not to a file. The
register reports the dates and the count and stops there.

**A register that cannot be read reports `UNCHECKED`, never `NEW`.** This is the defect
this whole package is organised around, pointed at the place it would be most expensive:
if an unreadable register answered `NEW`, one missing file would re-prepare an entire
county at once and every one of those businesses would be contacted twice.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from prospector.states import NEW, SEEN_BEFORE, UNCHECKED


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Sighting:
    status: str
    identity: str
    dates: tuple[str, ...] = ()
    reason: str = ""

    def describe(self) -> str:
        if self.status == NEW:
            return f"NEW  {self.identity}"
        if self.status == SEEN_BEFORE:
            return (f"SEEN_BEFORE  {self.identity}  prepared {len(self.dates)}x, "
                    f"last {self.dates[-1]}")
        return (f"UNCHECKED  {self.identity}\n  {self.reason}\n"
                f"  The register could not be read, so whether this business has already "
                f"been approached is unknown. It is not therefore new.")


class Register:
    """A JSON file of identity -> list of dates. Small, boring, and read before every run."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, list[str]] | None:
        """`None` means unreadable. An empty dict means read, and empty — not the same."""

        if not self.path.exists():
            # A register that has never been written is genuinely empty rather than
            # unreadable, and the first run of a new install must not report a whole
            # county as UNCHECKED.
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        return {k: list(v) for k, v in data.items() if isinstance(v, list)}

    def check(self, identity: str) -> Sighting:
        seen = self._load()
        if seen is None:
            return Sighting(UNCHECKED, identity,
                            reason=f"{self.path} exists and could not be parsed")
        dates = tuple(seen.get(identity, ()))
        if dates:
            return Sighting(SEEN_BEFORE, identity, dates=dates)
        return Sighting(NEW, identity)

    def record(self, identity: str, *, at: str | None = None) -> bool:
        """Append a sighting. Returns False when the register could not be written.

        The caller must not treat a False as harmless: an unrecorded preparation is one
        that will be prepared again next week.
        """

        seen = self._load()
        if seen is None:
            return False
        seen.setdefault(identity, []).append(at or _now())
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(seen, indent=1, sort_keys=True), encoding="utf-8")
        except OSError:
            return False
        return True
