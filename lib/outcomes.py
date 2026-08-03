"""What actually happened, fed back to the breakers that are supposed to stop you.

Until this existed, `Breakers.record()` was called by no production code. Three of the six
controls therefore read zero forever: the daily loss limit, the consecutive-loss run, and
the previously-tripped check that depends on either having fired. The kill switch, the
position cap and the sanity bound worked. The three that catch **a strategy going wrong over
time** — the failure this whole module set exists for — could not engage.

That is the recurring defect of this repository at the level of the safety system itself:
protection that looks present and is not.

## An unsettled position is not a zero-profit position

The sentinel this type exists to prevent. A bet placed this afternoon and settling on Sunday
has no profit yet, and recording `0.0` for it would do two wrong things at once: contribute
nothing to the daily loss, and — because `Breakers.consecutive_losses()` breaks its run on
any outcome that is not negative — **end a losing streak without a win having happened**.
Both errors point the same way, which is the direction that keeps you trading.

So `Position.profit` returns `None` unless the status is `SETTLED`, and nothing but a
`SETTLED` position is ever handed to a breaker.

## VOID is not zero either, for the same reason

A voided bet returns the stake. The arithmetic profit is zero, and it is neither a win nor a
loss — so it must not reach `consecutive_losses()`, which would read it as the streak
ending. A void is the absence of a result, not a result of nothing. It is recorded, it is
reported, and it is deliberately never applied.

## UNKNOWN is a status, not a gap

A position placed at a bookmaker that then restricted the account, or an order whose broker
returned a 5xx, has a real outcome that we could not read. Left as `OPEN` it looks like
something still running; recorded as settled-at-zero it corrupts the breakers. `UNKNOWN` is
neither, and `stale_open()` exists so an `OPEN` position that is really an `UNKNOWN` gets
noticed rather than quietly aging.

## Applying is idempotent, and fails toward stopping

`Breakers.record()` appends, so re-applying the same outcome would double-count it. The
`applied_to_breakers` flag prevents that, and the write order is deliberate:

    breakers.record(profit) → breakers.save() → set the flag → ledger.save()

A crash between the flag and the ledger save double-counts a loss on the next run, which
trips a breaker *earlier*. The reverse order would silently drop the loss. Neither is
pleasant and only one of them is survivable, so the ordering is chosen rather than
incidental.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from lib.store import Receipt, inspect

OPEN = "OPEN"
SETTLED = "SETTLED"
VOID = "VOID"
UNKNOWN = "UNKNOWN"

#: Statuses that still tie up money. A position is exposure until it is not.
LIVE = frozenset({OPEN, UNKNOWN})

#: How we came to know the outcome. Recorded because "I typed it in" and "the broker said
#: so" are different levels of confidence and the record should not flatten them.
MANUAL = "MANUAL"
BROKER = "BROKER"
CHAIN = "CHAIN"

LEDGER = Path("data/outcomes.json")
RECEIPT = Path("data/outcomes.receipt.json")

#: Past this, an OPEN position is more likely an UNKNOWN nobody chased.
STALE_HOURS = 72


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def position_id(lane: str, subject: str, opened_at: str) -> str:
    """Deterministic, so the same placement recorded twice collides instead of duplicating."""

    digest = hashlib.sha256(f"{lane}|{subject}|{opened_at}".encode("utf-8")).hexdigest()
    return f"POS-{digest[:10]}"


@dataclass(frozen=True, slots=True)
class Position:
    """One thing placed, and what became of it — or the fact that we do not know."""

    position_id: str
    lane: str
    subject: str
    status: str
    staked: float
    returned: float = 0.0
    opened_at: str = ""
    settled_at: str = ""
    source: str = ""
    note: str = ""
    #: True once this outcome has been handed to the breakers. Prevents double-counting,
    #: because Breakers.record() appends rather than upserting.
    applied_to_breakers: bool = False

    @property
    def profit(self) -> float | None:
        """`None` unless SETTLED. Never a zero standing in for an unknown.

        The whole type exists for this line. A caller that wants a number and gets `None`
        has to decide what to do about it; a caller that gets `0.0` does not know there was
        anything to decide.
        """

        return (self.returned - self.staked) if self.status == SETTLED else None

    @property
    def is_live(self) -> bool:
        return self.status in LIVE

    def age_hours(self, now: datetime | None = None) -> float | None:
        opened = _parse(self.opened_at)
        if opened is None:
            return None
        return ((now or datetime.now(timezone.utc)) - opened).total_seconds() / 3600.0

    def describe(self) -> str:
        head = f"{self.position_id}  [{self.lane}]  {self.subject}"
        if self.status == SETTLED:
            return (f"{head}\n  SETTLED  staked {self.staked:,.2f}, returned "
                    f"{self.returned:,.2f}, profit {self.profit:+,.2f}  "
                    f"({self.source or 'source not recorded'})")
        if self.status == VOID:
            return (f"{head}\n  VOID  stake {self.staked:,.2f} returned. Neither a win nor "
                    f"a loss, and deliberately NOT applied to the breakers: passing zero "
                    f"would end a losing run without a win having happened."
                    + (f"\n  {self.note}" if self.note else ""))
        if self.status == UNKNOWN:
            return (f"{head}\n  UNKNOWN  {self.staked:,.2f} was placed and what happened "
                    f"could not be established. This is not a loss and it is not a "
                    f"nothing; until it is resolved the breakers are working with less "
                    f"than the full picture."
                    + (f"\n  {self.note}" if self.note else ""))
        return (f"{head}\n  OPEN  {self.staked:,.2f} at risk since {self.opened_at}. No "
                f"profit exists yet, so none is reported and none is applied.")


@dataclass(frozen=True, slots=True)
class Application:
    """What one pass of `apply_to_breakers` did, and what it deliberately left alone."""

    lane: str
    applied: tuple[str, ...] = ()
    skipped_unsettled: tuple[str, ...] = ()
    skipped_void: tuple[str, ...] = ()
    already_applied: tuple[str, ...] = ()
    tripped_by: str = ""
    refusal: str = ""

    def describe(self) -> str:
        if self.refusal:
            return f"NOT APPLIED  [{self.lane}]\n  {self.refusal}"
        lines = [f"APPLIED  [{self.lane}]  {len(self.applied)} settled outcome(s)"]
        if self.skipped_unsettled:
            lines.append(
                f"  {len(self.skipped_unsettled)} still open or unknown, and NOT counted "
                f"as zero. The breakers are working with less than the full picture until "
                f"these settle.")
        if self.skipped_void:
            lines.append(
                f"  {len(self.skipped_void)} void, deliberately not applied: a returned "
                f"stake is neither a win nor a loss, and zero would end a losing run.")
        if self.tripped_by:
            lines.append(
                f"  BREAKER TRIPPED: {self.tripped_by}. It does not reset itself — "
                f"clearing it is a human act and is recorded with a reason.")
        return "\n".join(lines)


class OutcomeLedger:
    """Positions on file. Append-and-amend; nothing is ever deleted."""

    def __init__(self, path: str | Path = LEDGER,
                 *, receipt_path: str | Path | None = None) -> None:
        self.path = Path(path)
        self.receipt_path = (Path(receipt_path) if receipt_path is not None
                             else self.path.with_suffix(".receipt.json"))
        self.positions: list[Position] = []
        self.readable = True
        self.reason = ""

        if self.path.is_file():
            try:
                rows = json.loads(self.path.read_text(encoding="utf-8"))
                self.positions = [Position(**row) for row in rows]
            except (OSError, ValueError, TypeError) as error:
                self.readable = False
                self.reason = f"{type(error).__name__}: {error}"[:160]

    @property
    def status(self):
        """FRESH / INTACT / LOST / UNREADABLE, against the committed receipt.

        A ledger that held nine positions and now holds none is a different alarm from one
        that never existed, and only the receipt can tell them apart — which matters more
        here than anywhere else, because an emptied ledger silently un-trips a breaker.
        """

        return inspect(
            "outcomes", receipt_path=self.receipt_path,
            rows_found=len(self.positions) if self.readable else None,
            reason=self.reason,
        )

    # -- reading ----------------------------------------------------------------------

    def get(self, identifier: str) -> Position | None:
        return next((p for p in self.positions if p.position_id == identifier), None)

    def live(self, lane: str = "") -> tuple[Position, ...]:
        return tuple(p for p in self.positions
                     if p.is_live and (not lane or p.lane == lane))

    def unsettled_exposure(self, lane: str = "") -> float:
        """Money out that no breaker can see.

        The daily loss limit is computed from settled outcomes, so it is blind to
        everything still running. Reporting this beside it is what stops the limit reading
        as a complete picture of what is at risk.
        """

        return sum(p.staked for p in self.live(lane))

    def stale_open(self, hours: float = STALE_HOURS,
                   now: datetime | None = None) -> tuple[Position, ...]:
        """OPEN positions old enough that they are probably UNKNOWN nobody chased."""

        moment = now or datetime.now(timezone.utc)
        out = []
        for position in self.positions:
            if position.status != OPEN:
                continue
            age = position.age_hours(moment)
            if age is None or age >= hours:
                out.append(position)
        return tuple(out)

    def pending_application(self, lane: str = "") -> tuple[Position, ...]:
        return tuple(p for p in self.positions
                     if p.status == SETTLED and not p.applied_to_breakers
                     and (not lane or p.lane == lane))

    # -- writing ----------------------------------------------------------------------

    def _require_readable(self) -> None:
        if not self.readable:
            raise RuntimeError(
                f"refusing to write an outcome ledger that could not be read "
                f"({self.reason}). Overwriting it would erase positions that are still "
                f"holding money and un-trip any breaker they had tripped."
            )

    def _replace(self, position: Position, **changes: Any) -> Position:
        updated = replace(position, **changes)
        self.positions = [updated if p.position_id == position.position_id else p
                          for p in self.positions]
        return updated

    def open_position(self, lane: str, subject: str, staked: float,
                      *, source: str = MANUAL, at: str = "", note: str = "") -> Position:
        self._require_readable()
        if staked <= 0:
            raise ValueError("a position with no stake is not a position")
        opened = at or _now()
        identifier = position_id(lane, subject, opened)
        if self.get(identifier) is not None:
            raise ValueError(
                f"{identifier} already exists. The id is derived from lane, subject and "
                f"time, so this is the same placement recorded twice rather than two bets."
            )
        position = Position(identifier, lane, subject, OPEN, float(staked),
                            opened_at=opened, source=source, note=note)
        self.positions.append(position)
        return position

    def settle(self, identifier: str, returned: float,
               *, source: str = MANUAL, note: str = "", at: str = "") -> Position:
        self._require_readable()
        position = self._must_be_live(identifier)
        if returned < 0:
            raise ValueError("a return cannot be negative; a total loss returns 0")
        return self._replace(position, status=SETTLED, returned=float(returned),
                             settled_at=at or _now(), source=source, note=note)

    def void(self, identifier: str, *, note: str = "", at: str = "") -> Position:
        """The stake came back. Recorded, reported, and never applied to a breaker."""

        self._require_readable()
        position = self._must_be_live(identifier)
        return self._replace(position, status=VOID, returned=position.staked,
                             settled_at=at or _now(), note=note)

    def mark_unknown(self, identifier: str, reason: str, *, at: str = "") -> Position:
        self._require_readable()
        if not reason.strip():
            raise ValueError(
                "an UNKNOWN without a stated reason is indistinguishable from neglect"
            )
        position = self._must_be_live(identifier)
        return self._replace(position, status=UNKNOWN, settled_at=at or _now(),
                             note=reason)

    def amend_stake(self, identifier: str, staked: float, *, note: str = "") -> Position:
        """Correct a live position to what actually went on. Downward only.

        A part fill is the case: 3 shares of a requested 49 went on, and leaving the
        position at the requested size would overstate `unsettled_exposure` for the rest of
        its life. Increases are refused because a fill cannot exceed its request, so an
        upward amendment is a bug somewhere else rather than a correction.
        """

        self._require_readable()
        position = self._must_be_live(identifier)
        if staked <= 0:
            raise ValueError(
                "a position amended to nothing is not a position. If nothing went on, "
                "void it — that says the same thing and says it in the status"
            )
        if staked > position.staked:
            raise ValueError(
                f"refusing to raise {identifier} from {position.staked:,.2f} to "
                f"{staked:,.2f}: a fill cannot exceed its request, so this is a defect "
                f"upstream rather than a correction"
            )
        return self._replace(position, staked=float(staked),
                             note=(f"{position.note}; {note}" if position.note and note
                                   else note or position.note))

    def _must_be_live(self, identifier: str) -> Position:
        position = self.get(identifier)
        if position is None:
            raise ValueError(f"no position {identifier}")
        if not position.is_live:
            raise ValueError(
                f"{identifier} is already {position.status}. Amending a settled outcome "
                f"after it reached the breakers would leave the two disagreeing, and the "
                f"breakers are the copy that stops you."
            )
        return position

    def save(self) -> None:
        self._require_readable()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(p) for p in self.positions], indent=2) + "\n",
            encoding="utf-8")
        receipt = Receipt.load(self.receipt_path) or Receipt("outcomes")
        receipt.written(_now(), len(self.positions)).save(self.receipt_path)


def apply_to_breakers(ledger: OutcomeLedger, breakers: Any,
                      *, lane: str = "", save: bool = True) -> Application:
    """Hand every unapplied SETTLED outcome to the breakers, once.

    Order is deliberate: record, save the breakers, set the flag, save the ledger. A crash
    between the flag and the ledger save double-counts a loss next run and trips a breaker
    earlier; the reverse order would silently drop it. Fail toward stopping.
    """

    target = lane or getattr(getattr(breakers, "ringfence", None), "lane", "")

    if not ledger.readable:
        return Application(target, refusal=(
            f"the outcome ledger could not be read ({ledger.reason}), so what has settled "
            f"is unknown rather than nothing. Applying an empty set would tell the "
            f"breakers the day went fine."))
    if not getattr(breakers, "readable", True):
        return Application(target, refusal=(
            f"the breaker state could not be read ({getattr(breakers, 'reason', '')}). An "
            f"unknown daily loss is not a satisfied daily loss limit."))

    unsettled = tuple(p.position_id for p in ledger.live(target))
    voided = tuple(p.position_id for p in ledger.positions
                   if p.status == VOID and (not target or p.lane == target))
    already = tuple(p.position_id for p in ledger.positions
                    if p.status == SETTLED and p.applied_to_breakers
                    and (not target or p.lane == target))

    applied: list[str] = []
    state = getattr(breakers, "state", None)
    for position in ledger.pending_application(target):
        state = breakers.record(position.profit, reference=position.position_id)
        applied.append(position.position_id)

    if applied and save:
        breakers.save()
    for identifier in applied:
        position = ledger.get(identifier)
        assert position is not None
        ledger._replace(position, applied_to_breakers=True)
    if applied and save:
        ledger.save()

    return Application(
        target, tuple(applied), unsettled, voided, already,
        tripped_by=getattr(state, "tripped_by", "") or "",
    )


def describe_ledger(ledger: OutcomeLedger, *, now: datetime | None = None) -> str:
    """The money view: what is out, what is stuck, and what the breakers cannot see."""

    if not ledger.readable:
        return (f"UNREADABLE  the outcome ledger would not parse ({ledger.reason}). This "
                f"is not a report that nothing is open.")

    status = ledger.status
    lines = []
    if status.state == "LOST":
        lines.append(status.describe())
        lines.append("")

    live = ledger.live()
    if not live:
        lines.append("No position is open. Every placement recorded here has settled.")
    else:
        lines.append(f"{len(live)} position(s) live, {ledger.unsettled_exposure():,.2f} "
                     f"at risk and invisible to the daily loss limit:")
        lines += [f"  {p.describe()}" for p in live]

    stale = ledger.stale_open(now=now)
    if stale:
        lines.append("")
        lines.append(
            f"  {len(stale)} of these have been open over {STALE_HOURS}h. An OPEN position "
            f"that old is usually an UNKNOWN nobody chased, and it is holding the breakers "
            f"short of the full picture.")

    pending = ledger.pending_application()
    if pending:
        lines.append("")
        lines.append(f"  {len(pending)} settled outcome(s) have not reached the breakers "
                     f"yet. Run the application step or they never will.")
    return "\n".join(lines)
