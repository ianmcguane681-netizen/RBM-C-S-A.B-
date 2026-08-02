"""Whether this opportunity has already been put in front of you, and whether you acted.

The gap this closes is real: a scan that runs on a schedule will surface the same standing
opportunity every time it runs, and a reader who acts each time has acted several times on
one thing. Nothing else in this repository dedupes.

Three decisions make it honest rather than merely convenient.

**Identity excludes the price.** Two quotes on the same market and the same selections at
2.16 and 2.14 are one opportunity seen twice, not two opportunities. Identity is the market
and the set of (book, selection) pairs; the odds are deliberately excluded, because
including them would make every tick a new sighting and the register would dedupe nothing
while appearing to work.

**Seen before is not a refusal.** A standing opportunity that is still there is still real.
`SEEN_BEFORE` says "you have been told about this, on these dates, this many times" and
leaves the judgement where it belongs. Auto-rejecting repeats would hide a persistent
genuine edge, which is the expensive direction of this particular error.

**A register that cannot be read reports `UNCHECKED`, never `NEW`.** This is the recurring
defect in the place it would cost most. If an unreadable register answered `NEW`, every
candidate would look novel on the day the file went missing, and a scheduled scan would
re-surface everything at once — the flattering reading, arriving in bulk, at the moment
there is least reason to trust it.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

NEW = "NEW"
SEEN_BEFORE = "SEEN_BEFORE"
ACTED_ON = "ACTED_ON"
UNCHECKED = "UNCHECKED"


def arb_identity(market: str, legs: Sequence[tuple[str, str]]) -> str:
    """Market plus the (book, selection) pairs, sorted. Prices excluded on purpose.

    Sorted because the same two legs read in either order are one opportunity, and a
    register that disagreed with itself about that would dedupe nothing.
    """

    pairs = sorted(f"{book}/{selection}" for book, selection in legs)
    return f"{market.strip()}|{'|'.join(pairs)}"


@dataclass(frozen=True, slots=True)
class Sighting:
    identity: str
    first_seen: str
    last_seen: str
    times_seen: int = 1
    acted_at: str = ""


@dataclass(frozen=True, slots=True)
class SeenVerdict:
    status: str
    identity: str
    sighting: Sighting | None = None
    reason: str = ""

    def describe(self) -> str:
        if self.status == UNCHECKED:
            return (
                f"UNCHECKED  the register could not be read ({self.reason}). This candidate "
                f"is NOT established as new; it has not been looked up at all."
            )
        if self.status == NEW:
            return "NEW  not in the register"
        seen = self.sighting
        assert seen is not None
        if self.status == ACTED_ON:
            return (
                f"ACTED_ON  you acted on this on {seen.acted_at}. Seen {seen.times_seen} "
                f"time(s) since {seen.first_seen}. Still being reported because it is still "
                f"there, not because it is new."
            )
        return (
            f"SEEN_BEFORE  first {seen.first_seen}, last {seen.last_seen}, "
            f"{seen.times_seen} sighting(s). Still real, and not news."
        )


class SeenRegister:
    """Sightings by identity, as plain JSON that outlives any container."""

    def __init__(self, path: str | Path, *, readable: bool = True, reason: str = "") -> None:
        self.path = Path(path)
        self.readable = readable
        self.reason = reason
        self._sightings: dict[str, Sighting] = {}

    @classmethod
    def load(cls, path: str | Path) -> "SeenRegister":
        """A register that fails to parse is UNREADABLE, not empty.

        An empty register answers NEW to everything, which is exactly the answer a corrupt
        file must not be allowed to give.
        """

        register = cls(path)
        if not register.path.is_file():
            return register
        try:
            rows = json.loads(register.path.read_text(encoding="utf-8"))
            for row in rows:
                sighting = Sighting(**row)
                register._sightings[sighting.identity] = sighting
        except (OSError, ValueError, TypeError) as error:
            return cls(path, readable=False, reason=f"{type(error).__name__}: {error}"[:120])
        return register

    def __len__(self) -> int:
        return len(self._sightings)

    def check(self, identity: str) -> SeenVerdict:
        """Look up without writing. `record` is the separate, deliberate step."""

        if not self.readable:
            return SeenVerdict(UNCHECKED, identity, reason=self.reason)
        sighting = self._sightings.get(identity)
        if sighting is None:
            return SeenVerdict(NEW, identity)
        if sighting.acted_at:
            return SeenVerdict(ACTED_ON, identity, sighting)
        return SeenVerdict(SEEN_BEFORE, identity, sighting)

    def record(self, identity: str, when: str) -> Sighting:
        """Note that this was surfaced. Refuses to write through an unreadable register."""

        if not self.readable:
            raise RuntimeError(
                "refusing to write a register that could not be read: doing so would "
                "discard every prior sighting and make everything look new"
            )
        previous = self._sightings.get(identity)
        sighting = Sighting(
            identity=identity,
            first_seen=previous.first_seen if previous else when,
            last_seen=when,
            times_seen=(previous.times_seen + 1) if previous else 1,
            acted_at=previous.acted_at if previous else "",
        )
        self._sightings[identity] = sighting
        return sighting

    def record_action(self, identity: str, when: str) -> None:
        """Acting on something is different from being shown it, and outranks it."""

        previous = self._sightings.get(identity)
        self._sightings[identity] = Sighting(
            identity=identity,
            first_seen=previous.first_seen if previous else when,
            last_seen=previous.last_seen if previous else when,
            times_seen=previous.times_seen if previous else 1,
            acted_at=when,
        )

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError("refusing to overwrite an unreadable register")
        rows = [asdict(s) for s in sorted(self._sightings.values(), key=lambda s: s.identity)]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
