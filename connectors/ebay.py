"""Where sold comparables come from, and the one question this connector cannot answer.

`docs/flipper-design.md` opens with it: **can your eBay account read SOLD listings at all?**
The Browse API gives active listings freely; historical completed sales sit behind approval,
and the whole function rests on them. If sold data is not reachable the honest answer is
that the function does not work as designed — not that asking prices are substituted, which
is the failure that document exists to prevent.

So this connector has two sources and they are not alternatives to each other.

**`RecordedComparables`** reads completed sales a person entered by hand, from
`data/comparables.json`. It works today, it needs no key, and it is what the design means by
"eBay comparables against a source you input by hand". Typing five sold prices off a
completed-listings page takes a couple of minutes and produces evidence of exactly the same
quality as an API would — the sales are real either way.

**`EbaySoldSource`** is the API path, and it reports `NOT_CONFIGURED` without credentials
rather than raising, so a lane can say which sources answered. It is deliberately a thin
shape rather than a finished client: the endpoint, the scopes and the response format all
depend on which programme the account is approved for, and writing a client against a
guessed contract would produce something that looks finished and returns nothing.

**Neither will hand back an asking price as a sale.** `Browse` results are `ASKING` at the
type level, `lib.flipper.distribution` filters them out of every calculation, and there is
no flag to change that.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence

from lib.flipper import ASKING, SOLD, Comparable, ItemKey

CONFIGURED = "CONFIGURED"
NOT_CONFIGURED = "NOT_CONFIGURED"
UNREACHABLE = "UNREACHABLE"
READ = "READ"

#: Completed sales somebody typed in. Gitignored with the rest of `data/*.json`: it records
#: which items are being traded, which is a watchlist by another name.
COMPARABLES = Path("data/comparables.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class SoldLookup:
    """What one source returned for one item key, or why it returned nothing.

    A status rather than an exception for the usual reason: a lane asking two sources has
    to be able to report which one was silent, and a lookup that raised would make "no
    comparables" and "nobody asked" the same event.
    """

    status: str
    key: str
    comparables: tuple[Comparable, ...] = ()
    source: str = ""
    retrieved_at: str = ""
    reason: str = ""

    @property
    def sold(self) -> tuple[Comparable, ...]:
        return tuple(c for c in self.comparables if c.kind == SOLD)

    def describe(self) -> str:
        if self.status == NOT_CONFIGURED:
            return (f"{self.source}: NOT_CONFIGURED — {self.reason}. No comparable was "
                    f"retrieved from it, which is not a finding that none exist.")
        if self.status == UNREACHABLE:
            return (f"{self.source}: UNREACHABLE — {self.reason}. What this item sold for "
                    f"is unknown, not absent.")
        return (f"{self.source}: {len(self.sold)} completed sale(s) for {self.key}, read "
                f"{self.retrieved_at}")


class ComparableSource(Protocol):
    """What any source of comparables must supply.

    `sold_for` returns a `SoldLookup` and never raises for an absent configuration, so a
    caller asking several sources can tell which ones actually answered.
    """

    name: str

    def sold_for(self, key: ItemKey) -> SoldLookup: ...


@dataclass
class RecordedComparables:
    """Completed sales a person typed in from a completed-listings page.

    The source that works today, and the reason the flipper is not entirely blocked on the
    API question. A sale somebody read off eBay's completed listings and typed in is exactly
    as real as the same sale arriving over HTTP — what an API buys is volume and freshness,
    not evidence of a different quality.

    Every row carries who entered it and when, the same discipline `lib/rulebook.py` applies
    to a settlement clause and for the same reason: nothing here can retrieve it, so an
    entry attributed to a machine would be an entry nobody made.
    """

    path: Path = COMPARABLES
    readable: bool = True
    reason: str = ""
    rows: list[dict] = None  # type: ignore[assignment]
    name: str = "recorded by hand"

    def __post_init__(self) -> None:
        if self.rows is None:
            self.rows = []

    @classmethod
    def load(cls, path: str | Path = COMPARABLES) -> "RecordedComparables":
        store = cls(Path(path))
        if not store.path.is_file():
            return store
        try:
            store.rows = list(json.loads(store.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError) as error:
            return cls(Path(path), readable=False,
                       reason=f"{type(error).__name__}: {error}"[:140])
        return store

    def sold_for(self, key: ItemKey) -> SoldLookup:
        if not self.readable:
            return SoldLookup(UNREACHABLE, key.key, source=self.name, reason=self.reason)

        found: list[Comparable] = []
        for row in self.rows:
            try:
                row_key = ItemKey(
                    title=str(row["title"]), grade=str(row["grade"]),
                    grader=str(row["grader"]),
                    qualifiers=tuple(str(q) for q in row.get("qualifiers", ())))
                if not row_key.matches(key):
                    continue
                found.append(Comparable(
                    key=row_key, price=float(row["price"]),
                    currency=str(row.get("currency", "EUR")),
                    # No default. A row that does not say whether somebody paid it is a row
                    # this cannot use, and guessing SOLD is the one guess that matters.
                    kind=str(row["kind"]), observed_at=str(row["sold_at"]),
                    source=f"{self.name}: {row.get('entered_by', 'unattributed')}",
                    url=str(row.get("url", ""))))
            except (KeyError, TypeError, ValueError):
                # One malformed row is not a failed lookup. Skipped, and the count in the
                # result is what a caller compares against the floor — so a store full of
                # bad rows reports too few comparables rather than a crash or a silence.
                continue
        return SoldLookup(READ, key.key, tuple(found), self.name, _now())

    def describe(self) -> str:
        if not self.readable:
            return (f"UNREADABLE  {self.path}: {self.reason}\n"
                    f"  No comparable was read. Not a finding that none are recorded.")
        sold = sum(1 for row in self.rows if str(row.get("kind")) == SOLD)
        return (f"{len(self.rows)} recorded row(s), {sold} of them completed sales. "
                f"Asking prices are kept for display and never sized against.")


@dataclass
class EbaySoldSource:
    """The API path, unconfigured until the account question is answered.

    Deliberately a shape rather than a finished client. Which endpoint serves completed
    sales, which scopes it needs and what the response looks like all depend on which
    programme the account is approved for — and a client written against a guessed contract
    is worse than none, because it looks finished and returns nothing.

    What is real here is the refusal. With no credentials this answers NOT_CONFIGURED, so a
    lane reports "the API was not asked" rather than "this item has no comparables", which
    are the two readings `docs/flipper-design.md` spends its first page separating.
    """

    credentials: Any = None
    name: str = "eBay completed sales"

    @classmethod
    def from_directory(cls, directory: str | Path = "~/.ebay") -> "EbaySoldSource":
        path = Path(directory).expanduser() / "oauth_token"
        try:
            token = path.read_text(encoding="utf-8").strip()
        except OSError:
            return cls(None)
        return cls(token or None)

    @property
    def is_configured(self) -> bool:
        return bool(self.credentials)

    def sold_for(self, key: ItemKey) -> SoldLookup:
        if not self.is_configured:
            return SoldLookup(NOT_CONFIGURED, key.key, source=self.name, reason=(
                "no token at ~/.ebay/oauth_token. Sold data is the most restricted part of "
                "eBay's API surface and approval is per-account — docs/flipper-design.md "
                "question 1. Until that is answered, record comparables by hand"))
        return SoldLookup(NOT_CONFIGURED, key.key, source=self.name, reason=(
            "a token is present and no completed-sales client is written. Which endpoint "
            "serves this, and in what shape, depends on which programme the account is "
            "approved for — writing one against a guessed contract would look finished and "
            "return nothing. Answer question 1 in docs/flipper-design.md first"))


def gather(
    key: ItemKey, sources: Sequence[Any]
) -> tuple[tuple[Comparable, ...], tuple[SoldLookup, ...]]:
    """Ask every source, and hand back both the comparables and who answered.

    The lookups travel with the comparables rather than being logged and dropped. A
    distribution built from three sales where one of two sources was silent is a different
    fact from one built from three where both answered, and only the first has an obvious
    next step.
    """

    lookups = tuple(source.sold_for(key) for source in sources)
    comparables: list[Comparable] = []
    for lookup in lookups:
        comparables.extend(lookup.comparables)
    return tuple(comparables), lookups


def describe_sources(lookups: Sequence[SoldLookup]) -> str:
    answered = [look.source for look in lookups if look.status == READ]
    silent = [f"{look.source} ({look.status})" for look in lookups
              if look.status != READ]
    line = f"{len(answered)} of {len(lookups)} comparable source(s) answered"
    if silent:
        line += (f"; silent: {', '.join(silent)}. Anything they would have returned was "
                 f"not looked for")
    return line


def template() -> list[dict]:
    """The shape of `data/comparables.json`, for somebody typing the first ones in."""

    return [{
        "_note": ("One completed sale. `kind` has no default: SOLD means somebody paid "
                  "this, ASKING means somebody wanted it. Only SOLD is ever sized "
                  "against, and a row that does not say which is skipped."),
        "title": "Charizard Base Set Holo",
        "qualifiers": ["Base Set", "1999", "Unlimited"],
        "grade": "9",
        "grader": "PSA",
        "price": 340.0,
        "currency": "EUR",
        "kind": SOLD,
        "sold_at": "2026-08-20",
        "entered_by": "Your Name",
        "url": "https://www.ebay.ie/itm/...",
    }, {
        "title": "Charizard Base Set Holo",
        "qualifiers": ["Base Set", "1999", "Unlimited"],
        "grade": "9",
        "grader": "PSA",
        "price": 495.0,
        "currency": "EUR",
        "kind": ASKING,
        "sold_at": "2026-08-25",
        "entered_by": "Your Name",
        "url": "https://www.ebay.ie/itm/...",
    }]
