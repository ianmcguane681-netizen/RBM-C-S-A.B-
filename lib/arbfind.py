"""Find candidate arbs across many books — and refuse to call them arbs.

`lib/arb.py` verifies a position someone hands it: two legs, both with a stated maximum
stake and a settlement rule quoted verbatim, and it returns `LOCK` or it refuses. Nothing
in this repository *discovers* a position, which is why the arbitrage lane has never had
anything to point at.

This discovers. It is deliberately a different type from `Leg`, and the difference is the
whole design.

**An aggregated quote is not a price you can bet.** An odds feed returns a number. A `Leg`
requires three things and refuses construction without them:

    decimal_odds      the feed gives this
    max_stake         odds are not liquidity, and the feed does not know it
    settlement_rule   the feed does not carry the book's terms

So a discovery produces an `ArbCandidate`, never a `Leg`. The two missing fields are named
as missing rather than defaulted, because defaulting `max_stake` to something plausible
would let a position be sized against a number nobody read, and defaulting
`settlement_rule` to empty would slip past the gate that caught the only real position this
board has examined — a two-leg position with a *positive* margin whose legs voided
differently on abandonment.

**A market needs every outcome.** Two of a football market's three selections is not a
cheap arb, it is a bet on the draw not happening. `INCOMPLETE_BOOK` is its own status and
never renders as a small margin.

**Commission is per book and applies to winnings.** An exchange charging 5% of net winnings
turns a 2% edge into nothing, and applying it after the fact is the most common way a paper
arb evaporates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterable, Sequence

ARB_CANDIDATE = "ARB_CANDIDATE"
NO_ARB = "NO_ARB"
INCOMPLETE_BOOK = "INCOMPLETE_BOOK"
SINGLE_BOOK = "SINGLE_BOOK"
INSUFFICIENT_QUOTES = "INSUFFICIENT_QUOTES"

#: What the feed could not tell us. Named rather than defaulted, because both fields are
#: preconditions and a plausible default for either is worse than an absence.
UNKNOWN_STAKE = -1.0
UNKNOWN_RULE = ""


@dataclass(frozen=True, slots=True)
class Quote:
    """One book's price for one selection, as an odds feed returns it.

    No maximum stake and no settlement rule, because a feed carries neither. This is a
    `REFERENCE_RATE` in the vocabulary of the price-evidence design: real, useful for
    finding things, and not a price you can size against.
    """

    book: str
    market: str
    selection: str
    decimal_odds: float
    observed_at: str
    commission_pct: float = 0.0

    def __post_init__(self) -> None:
        if self.decimal_odds <= 1.0:
            raise ValueError(f"{self.book}/{self.selection}: decimal odds must exceed 1.0")

    @property
    def net_odds(self) -> float:
        """After the book's commission on winnings, which is where paper arbs die."""

        return 1.0 + (self.decimal_odds - 1.0) * (1.0 - self.commission_pct / 100.0)

    @property
    def implied_pct(self) -> float:
        return 100.0 / self.net_odds


@dataclass(frozen=True, slots=True)
class ArbCandidate:
    """A combination of quotes whose implied probabilities sum under 100%.

    Called a candidate and not an arb, on purpose. Two preconditions are unmet by
    construction — nobody has read the available stake or the settlement rules — and both
    have to be satisfied at the book before this becomes a position.
    """

    status: str
    market: str
    quotes: tuple[Quote, ...] = ()
    selections_expected: tuple[str, ...] = ()
    reason: str = ""

    @property
    def total_implied_pct(self) -> float:
        return sum(q.implied_pct for q in self.quotes)

    @property
    def margin_pct(self) -> float:
        """How far under 100% the combined implied probabilities sit.

        Not a rate of return: the return is lower once stakes are rounded to what the
        books actually accept, and it is zero if the legs do not settle alike.
        """

        return 100.0 - self.total_implied_pct

    @property
    def books(self) -> tuple[str, ...]:
        return tuple(sorted({q.book for q in self.quotes}))

    @property
    def observation_spread(self) -> tuple[str, str]:
        stamps = sorted(q.observed_at for q in self.quotes if q.observed_at)
        return (stamps[0], stamps[-1]) if stamps else ("", "")

    @property
    def unmet_preconditions(self) -> tuple[str, ...]:
        """Always both, until a person reads them at the book. Stated, never assumed."""

        return (
            "available stake at each book (a feed returns odds, not liquidity)",
            "settlement rules at each book (a feed does not carry the terms)",
        )

    def describe(self) -> str:
        if self.status == INCOMPLETE_BOOK:
            missing = set(self.selections_expected) - {q.selection for q in self.quotes}
            return (
                f"INCOMPLETE_BOOK  {self.market}\n"
                f"  {len(self.quotes)} of {len(self.selections_expected)} selection(s) "
                f"quoted; missing {', '.join(sorted(missing))}.\n"
                f"  Backing only the selections that are quoted is not an arb, it is a bet "
                f"on the missing outcome not happening."
            )
        if self.status in {NO_ARB, INSUFFICIENT_QUOTES, SINGLE_BOOK}:
            head = f"{self.status}  {self.market}"
            if self.quotes:
                head += f"\n  best combination implies {self.total_implied_pct:.3f}%"
            return f"{head}\n  {self.reason}" if self.reason else head

        lines = [
            f"ARB_CANDIDATE  {self.market}",
            f"  implied {self.total_implied_pct:.3f}%, margin {self.margin_pct:+.3f}%",
        ]
        for quote in self.quotes:
            commission = f" less {quote.commission_pct:.1f}% comm" if quote.commission_pct else ""
            lines.append(
                f"    {quote.selection:<22} {quote.decimal_odds:>7.3f} at "
                f"{quote.book}{commission}   {quote.observed_at}"
            )
        first, last = self.observation_spread
        if first != last:
            lines.append(f"  quotes span {first} to {last}; they were never simultaneous")
        lines.append("  NOT AN ARB YET. Unread preconditions:")
        for item in self.unmet_preconditions:
            lines.append(f"    - {item}")
        return "\n".join(lines)


def best_per_selection(quotes: Sequence[Quote]) -> dict[str, Quote]:
    """Highest net odds per selection. Net, because commission decides which book wins."""

    best: dict[str, Quote] = {}
    for quote in quotes:
        current = best.get(quote.selection)
        if current is None or quote.net_odds > current.net_odds:
            best[quote.selection] = quote
    return best


def find_arb(
    market: str,
    selections: Sequence[str],
    quotes: Sequence[Quote],
    *,
    allow_single_book: bool = False,
) -> ArbCandidate:
    """The best combination for one market, and whether it sums under 100%.

    `selections` is the full set of outcomes and must be supplied by the caller rather than
    inferred from the quotes. Inferring it would make a market look complete precisely when
    a book failed to return one of its selections, which is when it is least complete.
    """

    selections = tuple(selections)
    relevant = [q for q in quotes if q.market == market and q.selection in selections]

    if len(selections) < 2:
        return ArbCandidate(
            INSUFFICIENT_QUOTES, market, (), selections,
            reason="a market with fewer than two outcomes cannot be arbed",
        )

    best = best_per_selection(relevant)
    if len(best) < len(selections):
        return ArbCandidate(
            INCOMPLETE_BOOK, market, tuple(best.values()), selections,
            reason="not every outcome was quoted",
        )

    chosen = tuple(best[selection] for selection in selections)
    total = sum(q.implied_pct for q in chosen)

    if total >= 100.0:
        return ArbCandidate(
            NO_ARB, market, chosen, selections,
            reason=(
                f"the best available combination still implies {total:.3f}%. That is the "
                f"books' margin and it is the normal state of a market."
            ),
        )

    if not allow_single_book and len({q.book for q in chosen}) == 1:
        # One book pricing both sides under 100% is either an error it will void or a
        # promotion with terms. Either way it is not two counterparties.
        return ArbCandidate(
            SINGLE_BOOK, market, chosen, selections,
            reason=(
                f"every leg is at {chosen[0].book}. A single book pricing its own market "
                f"under 100% is an error it may void or a promotion with terms, not two "
                f"independent counterparties."
            ),
        )

    return ArbCandidate(ARB_CANDIDATE, market, chosen, selections)


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Every market examined, with the ones that yielded nothing kept visible."""

    candidates: tuple[ArbCandidate, ...] = ()
    books_seen: tuple[str, ...] = ()
    markets_examined: int = 0

    @property
    def arbs(self) -> tuple[ArbCandidate, ...]:
        return tuple(c for c in self.candidates if c.status == ARB_CANDIDATE)

    @property
    def incomplete(self) -> tuple[ArbCandidate, ...]:
        return tuple(c for c in self.candidates if c.status == INCOMPLETE_BOOK)

    def describe(self) -> str:
        lines = [
            f"{self.markets_examined} market(s) examined across "
            f"{len(self.books_seen)} book(s): {', '.join(self.books_seen)}",
            f"{len(self.arbs)} candidate(s) implied under 100%.",
        ]
        if self.incomplete:
            lines.append(
                f"{len(self.incomplete)} market(s) had a selection nobody quoted and were "
                f"NOT evaluated. An unquoted outcome is not a free one."
            )
        lines.append("")
        lines += [c.describe() for c in self.arbs]
        if not self.arbs:
            lines.append(
                "No combination implied under 100%. That is a statement about the books "
                "that answered, and says nothing about a book that did not."
            )
        return "\n".join(lines)


def scan_markets(
    markets: dict[str, Sequence[str]],
    quotes: Sequence[Quote],
    *,
    allow_single_book: bool = False,
) -> ScanResult:
    """Run every market. Markets yielding nothing are kept, not filtered away."""

    candidates = tuple(
        find_arb(market, selections, quotes, allow_single_book=allow_single_book)
        for market, selections in sorted(markets.items())
    )
    return ScanResult(
        candidates, tuple(sorted({q.book for q in quotes})), len(markets)
    )
