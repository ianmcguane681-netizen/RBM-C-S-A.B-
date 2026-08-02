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
    #: Size available AT THIS PRICE, when the source knows it. An aggregator does not and
    #: leaves it UNKNOWN_STAKE; an exchange reads it off the ladder and fills it in. This
    #: is the whole reason an exchange connector is worth more than a wider feed, and
    #: keeping it per-quote means a mixed scan reports honestly rather than at the level of
    #: its weakest source.
    available_stake: float = UNKNOWN_STAKE

    def __post_init__(self) -> None:
        if self.decimal_odds <= 1.0:
            raise ValueError(f"{self.book}/{self.selection}: decimal odds must exceed 1.0")

    @property
    def stake_is_known(self) -> bool:
        return self.available_stake > 0

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
    #: The best combination using a different book per selection, when the cheapest one
    #: doubles up. Empty when the cheapest is already spread, or when no diversified
    #: combination exists at all.
    distinct_book_alternative: tuple[Quote, ...] = ()

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
    def stake_bound(self) -> float:
        """The smallest available stake across the legs, or UNKNOWN_STAKE if any is unread.

        The smallest binds: a position is only as large as its tightest side. One unread
        side makes the whole bound unknown rather than making it the minimum of the ones
        that happened to be readable, which would be the flattering reading.
        """

        if not self.quotes or not all(q.stake_is_known for q in self.quotes):
            return UNKNOWN_STAKE
        return min(q.available_stake for q in self.quotes)

    @property
    def unmet_preconditions(self) -> tuple[str, ...]:
        """What still has to be read at the book before this is a position.

        Computed rather than fixed, so adding an exchange visibly removes one. Settlement
        rules never come off this list from a price feed of any kind: no source in this
        repository returns a book's terms, and the only real position this board examined
        was refused on exactly that.
        """

        unmet: list[str] = []
        sizeless = [q.book for q in self.quotes if not q.stake_is_known]
        if sizeless:
            unmet.append(
                f"available stake at {', '.join(sorted(set(sizeless)))} "
                f"(a feed returns odds, not liquidity)"
            )
        unmet.append("settlement rules at each book (no price source carries the terms)")
        return tuple(unmet)

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
        if self.distinct_book_alternative:
            spread_implied = sum(q.implied_pct for q in self.distinct_book_alternative)
            cost = spread_implied - self.total_implied_pct
            lines.append(
                f"  CONCENTRATED: {len(self.books)} book(s) across "
                f"{len(self.quotes)} legs. One restriction or void there takes out more "
                f"than one leg."
            )
            lines.append(
                f"  A one-book-per-leg alternative implies {spread_implied:.3f}% "
                f"(costs {cost:+.3f}% of margin):"
            )
            for quote in self.distinct_book_alternative:
                lines.append(f"    {quote.selection:<22} {quote.decimal_odds:>7.3f} at "
                             f"{quote.book}")
        bound = self.stake_bound
        if bound != UNKNOWN_STAKE:
            tightest = min(self.quotes, key=lambda q: q.available_stake)
            lines.append(
                f"  size bound {bound:,.2f} at {tightest.book} on {tightest.selection}"
            )
        first, last = self.observation_spread
        if first != last:
            lines.append(f"  quotes span {first} to {last}; they were never simultaneous")
        lines.append("  NOT AN ARB YET. Unread preconditions:")
        for item in self.unmet_preconditions:
            lines.append(f"    - {item}")
        return "\n".join(lines)


def quotes_from_legs(legs: Iterable) -> tuple[Quote, ...]:
    """Adapt a source that already produces `Leg` into discovery quotes.

    An exchange returns the price, the size at that price and the market's rules text, so
    it can build a `Leg` directly. Discovery still runs over `Quote`, and this narrows
    rather than widens: the settlement rule is deliberately DROPPED on the way in.

    That looks like throwing away the best thing the exchange gave us, and it is the point.
    A rule read at one book says nothing about the other book's rule, and the gate exists
    to compare two of them. Carrying one leg's rule into a candidate would let a
    half-verified position read as verified — which is the exact shape of the failure the
    only real position this board examined took.
    """

    return tuple(
        Quote(
            book=leg.book, market=leg.market, selection=leg.selection,
            decimal_odds=leg.decimal_odds, observed_at=leg.observed_at,
            commission_pct=leg.commission_pct, available_stake=leg.max_stake,
        )
        for leg in legs
    )


def best_per_selection(quotes: Sequence[Quote]) -> dict[str, Quote]:
    """Highest net odds per selection. Net, because commission decides which book wins."""

    best: dict[str, Quote] = {}
    for quote in quotes:
        current = best.get(quote.selection)
        if current is None or quote.net_odds > current.net_odds:
            best[quote.selection] = quote
    return best


def best_distinct_books(
    selections: Sequence[str], quotes: Sequence[Quote]
) -> tuple[Quote, ...]:
    """The best combination that uses a DIFFERENT book for every selection.

    Concentration is a real cost and it is not priced into the odds. Two legs at one
    bookmaker means one account restriction, one voided market or one palpable-error claim
    takes out both at once and leaves the rest unhedged — and soft books restrict arbitrage
    accounts as a matter of course, so this is an expected event rather than a tail risk.

    Spreading across books usually costs margin. That trade is the holder's to make, so
    this returns the diversified combination and `find_arb` reports BOTH, with the cost of
    diversifying stated. Silently preferring either one would be deciding it for them.

    Exhaustive over the assignment, which is fine at three-way size and would need a
    matching algorithm beyond about six selections.
    """

    selections = tuple(selections)
    by_selection: dict[str, list[Quote]] = {s: [] for s in selections}
    for quote in quotes:
        if quote.selection in by_selection:
            by_selection[quote.selection].append(quote)
    if any(not options for options in by_selection.values()):
        return ()

    best: tuple[Quote, ...] = ()
    best_implied = float("inf")
    for combination in product(*(by_selection[s] for s in selections)):
        if len({q.book for q in combination}) != len(selections):
            continue
        implied = sum(q.implied_pct for q in combination)
        if implied < best_implied:
            best, best_implied = combination, implied
    return best


def find_arb(
    market: str,
    selections: Sequence[str],
    quotes: Sequence[Quote],
    *,
    allow_single_book: bool = False,
    prefer_distinct_books: bool = True,
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

    # The diversified alternative, computed whenever the cheapest combination doubles up
    # at a book. Reported rather than substituted: paying margin for independence is the
    # holder's call, and it is only a call if both numbers are visible.
    spread: tuple[Quote, ...] = ()
    if prefer_distinct_books and len({q.book for q in chosen}) < len(selections):
        spread = best_distinct_books(selections, relevant)

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

    return ArbCandidate(ARB_CANDIDATE, market, chosen, selections,
                        distinct_book_alternative=spread)


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
