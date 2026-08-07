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

    PRICED         a price was supplied, with its source and timestamp
    UNPRICED       no price was supplied. NOT a value of zero.
    STALE          a price was supplied and is older than the caller's tolerance
    MARKET_CLOSED  older than the tolerance because the venue is shut, which is a
                   different fact: the last trade genuinely is the last price
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
#: Set by `lib/pricing.py`, which is the only thing here that knows a market has hours.
#: A weekend price is not a feed falling behind, and collapsing the two would mean either
#: a book that reads STALE every Sunday or a ceiling loose enough to hide a dead feed on a
#: Tuesday afternoon.
MARKET_CLOSED = "MARKET_CLOSED"

BUY = "BUY"
SELL = "SELL"

#: Lanes, so exposure can be reported per lane as well as per asset. A portfolio 90% in
#: one lane is concentrated whatever the per-asset limits say.
CRYPTO = "crypto"
EQUITY = "equity"
BETTING = "betting"
#: Operating lanes. Capital goes in and revenue comes out, but there is no mark until
#: something sells, so UNPRICED is their normal resting state rather than a failure.
INVENTORY = "inventory"   # stock bought for resale: Etsy, flipping
VENTURE = "venture"       # hours and cash sunk into something being built

LANES = (CRYPTO, EQUITY, BETTING, INVENTORY, VENTURE)


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
        marker = ""
        if self.status == STALE:
            marker = " (STALE)"
        elif self.status == MARKET_CLOSED:
            marker = " (market shut; last price)"
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
        currency: str = "",
    ) -> Valuation:
        """`currency` is the PRICE's currency, which need not be the book's.

        This holding's cost is recorded in whatever was paid — euro, here — and a US
        quote comes back in dollars. Stamping the book's currency onto a dollar figure is
        how `EUR 39.00` and `USD -77.00` were once added into `-EUR 38.00`: not a
        conversion, two different units summed. So the valuation carries the unit its
        price arrived in, and `Exposure` refuses a total that spans more than one.
        """

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
        if stale_after_seconds >= 0 and (age < 0 or age > stale_after_seconds):
            # An age that could not be established is STALE, not fresh. The first version
            # required `age >= 0` to mark anything stale, so a quote carrying no usable
            # timestamp — which `AlpacaBroker.quote()` can return, since it reads
            # `str(row.get("t") or "")` — was called PRICED and summed into the book total
            # a caller had explicitly asked to be time-limited. Asking for a ceiling and
            # being handed an unmeasurable price is exactly when the stricter word is owed.
            status = STALE
        return Valuation(
            status, self.asset, self.quantity, unit_price, currency or self.currency,
            priced_at, source, age,
        )


@dataclass(frozen=True, slots=True)
class Exposure:
    """Totals, with what could not be priced kept visible beside them.

    Three things are kept out of `priced_value` rather than summed into it, and each is a
    different reason for the same refusal.

    **UNPRICED** is the original one: a holding with no price is absent from the total and
    named beside it, never counted as nothing.

    **STALE** joined it when a price source was first wired. A stale price is still a
    price and `Valuation.value` still returns it — but a total built partly on prices the
    caller has already declared too old, presenting itself as the current value of the
    book, is the founding defect one level up. The stale holdings are named and the total
    covers what is actually current.

    **More than one currency** produces no total at all. The book records cost in euro and
    a US quote arrives in dollars; there is no rate in this repository, and a rate is
    itself a price that goes stale. Adding them once produced `EUR 39.00 + USD -77.00 =
    -EUR 38.00`. `priced_value` is `None` in that case, `by_currency` holds each subtotal
    under its own unit, and nothing here will guess the missing rate.
    """

    currency: str
    #: `None` means no single total can be stated — not zero, and not "nothing priced".
    priced_value: float | None = 0.0
    cost_basis: float = 0.0
    unpriced_assets: tuple[str, ...] = ()
    by_lane: dict[str, float] = field(default_factory=dict)
    stale_assets: tuple[str, ...] = ()
    by_currency: dict[str, float] = field(default_factory=dict)

    @property
    def spans_currencies(self) -> bool:
        return len(self.by_currency) > 1

    @property
    def is_complete(self) -> bool:
        """Every holding priced, currently, in one unit. Anything less says so."""

        return not self.unpriced_assets and not self.stale_assets and not self.spans_currencies

    @property
    def nothing_priced(self) -> bool:
        """Holdings are held and not one of them has a price behind it."""

        return not self.by_currency and bool(self.unpriced_assets or self.stale_assets)

    def describe(self) -> str:
        lines: list[str] = []
        if self.nothing_priced:
            held = len(self.unpriced_assets) + len(self.stale_assets)
            lines.append(
                f"Nothing could be priced: {held} holding(s) are held and no current price "
                f"stands behind any of them. This is NOT a book worth 0.00 — what it is "
                f"worth is unknown, and what it cost is the figure above."
            )
        elif self.spans_currencies:
            lines.append(
                "No single priced total: the holdings that priced are quoted in "
                f"{', '.join(sorted(self.by_currency))}, and there is no exchange rate "
                "anywhere in this system to add them with."
            )
            for unit, value in sorted(self.by_currency.items()):
                lines.append(f"  {value:>14,.2f} {unit} priced")
            lines.append(
                f"  Cost is recorded in {self.currency}: {self.cost_basis:,.2f} for the "
                f"priced holdings, and is not comparable with a total in another unit."
            )
        else:
            priced_currency = next(iter(self.by_currency), self.currency)
            lines.append(
                f"Priced holdings: {self.priced_value or 0.0:,.2f} {priced_currency}."
            )
            if priced_currency == self.currency:
                lines.append(f"  Cost of those holdings: {self.cost_basis:,.2f} "
                             f"{self.currency}.")
            else:
                # On their own lines, because a value and a cost in different units side
                # by side invite exactly the subtraction that has no answer here.
                lines.append(
                    f"  Cost of those holdings: {self.cost_basis:,.2f} {self.currency}. "
                    f"Different unit from the value above; there is no rate here and the "
                    f"difference between them is not a gain."
                )
            for lane, value in sorted(self.by_lane.items()):
                share = (value / self.priced_value * 100.0) if self.priced_value else 0.0
                lines.append(f"  {lane:<8} {value:>14,.2f}  {share:5.1f}% of priced")

        if self.stale_assets:
            lines.append(
                f"  {len(self.stale_assets)} holding(s) priced STALE and are NOT in the "
                f"total above: {', '.join(self.stale_assets)}. A price too old to trust is "
                f"not a current value."
            )
        if self.unpriced_assets:
            lines.append(
                f"  {len(self.unpriced_assets)} holding(s) are UNPRICED and are NOT in the "
                f"total above: {', '.join(self.unpriced_assets)}."
            )
        if self.unpriced_assets or self.stale_assets:
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
        """Totals over what could be priced CURRENTLY, with the rest named rather than
        counted.

        A STALE valuation is excluded from the total and named separately. It carries a
        real number — the caller can still see it per holding — but a book total assembled
        from prices already declared too old, rendered as what the holdings are worth now,
        is exactly the defect this module was written against, arriving through the one
        door left open for it.
        """

        by_lane: dict[str, float] = {}
        by_currency: dict[str, float] = {}
        lanes = {p.asset: p.lane for p in self.positions()}
        basis = {p.asset: p.cost_basis for p in self.positions()}

        cost_total = 0.0
        unpriced: list[str] = []
        stale: list[str] = []
        for valuation in valuations:
            value = valuation.value
            if value is None:
                unpriced.append(valuation.asset)
                continue
            if valuation.status == STALE:
                stale.append(valuation.asset)
                continue
            unit = valuation.currency or currency
            by_currency[unit] = by_currency.get(unit, 0.0) + value
            cost_total += basis.get(valuation.asset, 0.0)
            lane = lanes.get(valuation.asset, "unknown")
            by_lane[lane] = by_lane.get(lane, 0.0) + value

        priced_total: float | None = sum(by_currency.values()) if by_currency else 0.0
        if len(by_currency) > 1:
            # Not a total anybody can state. None rather than the sum, which would be a
            # number made of two units.
            priced_total = None
        elif not by_currency and valuations:
            # Holdings exist and not one of them priced. `0.0` here is the same mistake
            # `Realised` made by reporting COMPLETE over an empty book: a total of nought
            # reads as "we looked at everything and it came to nothing", when nothing was
            # valued at all. Only a book with no holdings totals to zero.
            priced_total = None

        return Exposure(
            currency, priced_total, cost_total, tuple(unpriced), by_lane,
            tuple(stale), by_currency,
        )

    def save(self, when: str = "") -> None:
        from lib.store import JSON_BACKEND, Receipt

        rows = [asdict(e) for e in self._entries]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        previous = Receipt.load(self.receipt_path) or Receipt(self.path.name, JSON_BACKEND)
        previous.written(when or _now(), len(rows)).save(self.receipt_path)
