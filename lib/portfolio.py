"""What is held, what it cost, and what it is worth — with the last one never stored.

RBF-001 component 1. Bookkeeping only: it holds no view on price, produces no verdict, and
cannot originate a reason to buy or sell anything.

Three rules, and the third is the one that matters.

**Append-only.** A position is a running total of entries and exits, each recorded with its
date, quantity, unit price and the reason given at the time. Editing a position in place
would lose the history that makes a cost basis checkable, and the cost basis is the only
number here that cannot be recomputed from anywhere else.

**Cost basis is stated, not inferred.** Average cost is computed from the recorded entries.
A basis typed in by hand and a basis derived from fills are different facts, and which one
is in use is recorded so a tax figure is never quietly built on a guess.

**Current value is DERIVED, never stored, and an unpriced holding is `UNPRICED` — not
zero.** This is the recurring defect aimed at the number a holder looks at first. A stored
value goes stale silently. A zero shows a portfolio shrinking the moment a feed dies, which
would read as a loss that never happened, and — worse — a risk limit computed against it
would size the next position against a balance that is wrong in the reassuring direction.

    PRICED     a price was supplied, with its source and timestamp
    UNPRICED   no price was supplied. NOT a value of zero.
    STALE      a price was supplied and is older than the caller's tolerance
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

PRICED = "PRICED"
UNPRICED = "UNPRICED"
STALE = "STALE"

BUY = "BUY"
SELL = "SELL"

#: Lanes, so exposure can be reported per lane as well as per asset. A portfolio 90% in
#: one lane is concentrated whatever the per-asset limits say.
CRYPTO = "crypto"
EQUITY = "equity"
BETTING = "betting"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Entry:
    """One buy or sell. Immutable, and carries the reason given at the time."""

    asset: str
    lane: str
    side: str
    quantity: float
    unit_price: float
    currency: str
    when: str
    #: Why, in the holder's words, recorded when it happened rather than reconstructed
    #: afterwards. A position with no stated reason is a position nobody has to defend.
    reason: str = ""
    reference: str = ""

    def __post_init__(self) -> None:
        if self.side not in {BUY, SELL}:
            raise ValueError(f"side must be {BUY} or {SELL}, not {self.side!r}")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive; direction is carried by side")
        if self.unit_price < 0:
            raise ValueError("unit price cannot be negative")

    @property
    def signed_quantity(self) -> float:
        return self.quantity if self.side == BUY else -self.quantity

    @property
    def consideration(self) -> float:
        return self.quantity * self.unit_price


@dataclass(frozen=True, slots=True)
class Valuation:
    """What a holding is worth, or the honest statement that it is not known."""

    status: str
    asset: str
    quantity: float = 0.0
    unit_price: float = 0.0
    currency: str = ""
    priced_at: str = ""
    source: str = ""
    age_seconds: float = -1.0

    @property
    def value(self) -> float | None:
        """`None` when unpriced. Deliberately not 0.0.

        Callers must handle the None. A float would let an unpriced holding flow into a
        sum and silently reduce a balance that a risk limit is computed against.
        """

        return self.quantity * self.unit_price if self.status != UNPRICED else None

    def describe(self) -> str:
        if self.status == UNPRICED:
            return (
                f"{self.asset}: {self.quantity:,.6g} held, UNPRICED. No price was supplied. "
                f"This is NOT a value of zero and this holding is absent from any total "
                f"below rather than counted as nothing."
            )
        marker = " (STALE)" if self.status == STALE else ""
        return (
            f"{self.asset}: {self.quantity:,.6g} @ {self.unit_price:,.4f} "
            f"{self.currency} = {self.value:,.2f}{marker}  [{self.source} {self.priced_at}]"
        )


@dataclass(frozen=True, slots=True)
class Position:
    asset: str
    lane: str
    quantity: float
    cost_basis: float
    currency: str
    entries: int
    first_entry: str = ""
    last_entry: str = ""

    @property
    def average_cost(self) -> float:
        return self.cost_basis / self.quantity if self.quantity else 0.0

    def value_at(
        self,
        unit_price: float | None,
        *,
        source: str = "",
        priced_at: str = "",
        stale_after_seconds: float = -1.0,
    ) -> Valuation:
        if unit_price is None:
            return Valuation(UNPRICED, self.asset, self.quantity, currency=self.currency)

        age = -1.0
        if priced_at:
            try:
                stamp = datetime.fromisoformat(priced_at.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - stamp).total_seconds()
            except ValueError:
                age = -1.0
        status = PRICED
        if stale_after_seconds >= 0 and age >= 0 and age > stale_after_seconds:
            status = STALE
        return Valuation(
            status, self.asset, self.quantity, unit_price, self.currency,
            priced_at, source, age,
        )


@dataclass(frozen=True, slots=True)
class Exposure:
    """Totals, with what could not be priced kept visible beside them."""

    currency: str
    priced_value: float = 0.0
    cost_basis: float = 0.0
    unpriced_assets: tuple[str, ...] = ()
    by_lane: dict[str, float] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return not self.unpriced_assets

    def describe(self) -> str:
        lines = [
            f"Priced holdings: {self.priced_value:,.2f} {self.currency} "
            f"against {self.cost_basis:,.2f} cost."
        ]
        for lane, value in sorted(self.by_lane.items()):
            share = (value / self.priced_value * 100.0) if self.priced_value else 0.0
            lines.append(f"  {lane:<8} {value:>14,.2f}  {share:5.1f}% of priced")
        if self.unpriced_assets:
            lines.append(
                f"  {len(self.unpriced_assets)} holding(s) are UNPRICED and are NOT in the "
                f"total above: {', '.join(self.unpriced_assets)}."
            )
            lines.append(
                "  Every percentage here is a share of what could be priced, not of what "
                "is held. Do not size a position against this number."
            )
        return "\n".join(lines)


class Portfolio:
    """An append-only book of entries. Positions are derived; nothing is edited."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.receipt_path = self.path.with_suffix(".receipt.json")
        self._entries: list[Entry] = []
        rows: int | None = 0
        reason = ""
        if self.path.is_file():
            try:
                self._entries = [
                    Entry(**row)
                    for row in json.loads(self.path.read_text(encoding="utf-8"))
                ]
                rows = len(self._entries)
            except (OSError, ValueError, TypeError) as error:
                rows, reason = None, f"{type(error).__name__}: {error}"[:120]

        from lib.store import inspect

        self.status = inspect(
            self.path.name, receipt_path=self.receipt_path, rows_found=rows, reason=reason
        )

    def __len__(self) -> int:
        return len(self._entries)

    def add(self, entry: Entry) -> None:
        """Append. There is no edit and no delete, deliberately."""

        if self.status.state == "UNREADABLE":
            raise RuntimeError(
                "refusing to append to a book that could not be read: the existing entries "
                "would be discarded and the cost basis silently rebuilt from nothing"
            )
        self._entries.append(entry)

    def entries_for(self, asset: str) -> tuple[Entry, ...]:
        return tuple(e for e in self._entries if e.asset == asset)

    def positions(self) -> tuple[Position, ...]:
        """Derived from the entries every time. Never cached, never stored.

        Cost basis is average-cost: a sell reduces quantity and basis proportionally,
        leaving the average untouched. FIFO would give a different tax figure and is a
        choice a holder makes with their accountant, not one this file makes for them.
        """

        books: dict[str, dict] = {}
        for entry in self._entries:
            book = books.setdefault(entry.asset, {
                "lane": entry.lane, "currency": entry.currency, "quantity": 0.0,
                "basis": 0.0, "count": 0, "first": entry.when, "last": entry.when,
            })
            if entry.side == BUY:
                book["quantity"] += entry.quantity
                book["basis"] += entry.consideration
            else:
                sold = min(entry.quantity, book["quantity"])
                if book["quantity"]:
                    book["basis"] -= book["basis"] * (sold / book["quantity"])
                book["quantity"] -= sold
            book["count"] += 1
            book["last"] = max(book["last"], entry.when)
            book["first"] = min(book["first"], entry.when)

        return tuple(
            Position(
                asset, book["lane"], round(book["quantity"], 12), round(book["basis"], 12),
                book["currency"], book["count"], book["first"], book["last"],
            )
            for asset, book in sorted(books.items())
            if round(book["quantity"], 12) > 0
        )

    def exposure(self, valuations: Sequence[Valuation], *, currency: str = "EUR") -> Exposure:
        """Totals over what could be priced, with the rest named rather than counted."""

        by_lane: dict[str, float] = {}
        lanes = {p.asset: p.lane for p in self.positions()}
        basis = {p.asset: p.cost_basis for p in self.positions()}

        priced_total = 0.0
        cost_total = 0.0
        unpriced: list[str] = []
        for valuation in valuations:
            value = valuation.value
            if value is None:
                unpriced.append(valuation.asset)
                continue
            priced_total += value
            cost_total += basis.get(valuation.asset, 0.0)
            lane = lanes.get(valuation.asset, "unknown")
            by_lane[lane] = by_lane.get(lane, 0.0) + value

        return Exposure(currency, priced_total, cost_total, tuple(unpriced), by_lane)

    def save(self, when: str = "") -> None:
        from lib.store import JSON_BACKEND, Receipt

        rows = [asdict(e) for e in self._entries]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        previous = Receipt.load(self.receipt_path) or Receipt(self.path.name, JSON_BACKEND)
        previous.written(when or _now(), len(rows)).save(self.receipt_path)
