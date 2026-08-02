"""Where prices come from, and what it means when they do not.

Every odds source needs credentials this repository does not have, so no live provider is
implemented here. What IS implemented is the shape they must take and, more importantly,
the answer an unconfigured source gives.

That answer is `NOT_CONFIGURED`, and it is the whole reason this file exists ahead of any
provider. A scanner that finds no arb because it could not reach a book, and reports "no
arb", has told the operator something false in the direction that costs nothing today and
everything the day they rely on it. This system has met that defect in a court archive, an
empty proxy slot, an absent liquidity venue and an unfiled accounting tag; an odds feed is
where it would be cheapest to make and least visible.

Two provider shapes, and they differ in a way that matters more than the API:

    EXCHANGE    prices are other people's money, sizes are visible, commission on winnings
    BOOKMAKER   prices are the operator's, limits are undisclosed and applied per account

An exchange's stated size is a fact. A bookmaker's is a policy, and the same headline price
is offered at different sizes to different accounts. `max_stake` from a bookmaker is
therefore an upper bound on a hope, and `stake_is_observed` records which kind it is.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from lib.arb import Leg

CONFIGURED = "CONFIGURED"
NOT_CONFIGURED = "NOT_CONFIGURED"
UNREACHABLE = "UNREACHABLE"

EXCHANGE = "EXCHANGE"
BOOKMAKER = "BOOKMAKER"


@dataclass(frozen=True, slots=True)
class MarketQuote:
    """What one source offered on one market, or why it offered nothing."""

    status: str
    source: str
    kind: str
    market: str = ""
    legs: tuple[Leg, ...] = ()
    observed_at: str = ""
    stake_is_observed: bool = False
    reason: str = ""

    def describe(self) -> str:
        if self.status == NOT_CONFIGURED:
            return (
                f"{self.source} is NOT CONFIGURED: {self.reason or 'no credentials supplied'}. "
                f"No prices were retrieved from it. This is not a finding that "
                f"{self.source} offers no price, and any scan excluding it has not covered it."
            )
        if self.status == UNREACHABLE:
            return (
                f"{self.source} could not be reached: {self.reason}. Its prices are "
                f"unknown, not absent."
            )
        stake_note = (
            "sizes are observed from the book"
            if self.stake_is_observed
            else "sizes are an UPPER BOUND, not an offer: a bookmaker applies undisclosed "
                 "per-account limits and may accept far less"
        )
        return (
            f"{self.source} ({self.kind}) on {self.market} at {self.observed_at}: "
            f"{len(self.legs)} selection(s). {stake_note}."
        )


class OddsSource(Protocol):
    """What any provider must supply.

    `quote` returns a `MarketQuote` and never raises for an absent configuration, because
    a caller scanning ten sources must be able to tell which ones actually answered.
    """

    name: str
    kind: str

    def quote(self, market: str) -> MarketQuote: ...


@dataclass(frozen=True, slots=True)
class UnconfiguredSource:
    """A named provider with no credentials, which says so every time it is asked.

    Registering these deliberately, rather than leaving the source list short, is what
    makes a scan's coverage legible: the operator sees "Betfair NOT CONFIGURED" instead of
    a scan that quietly never considered Betfair at all.
    """

    name: str
    kind: str = BOOKMAKER
    reason: str = "no credentials supplied"

    def quote(self, market: str) -> MarketQuote:
        return MarketQuote(
            NOT_CONFIGURED, self.name, self.kind, market=market, reason=self.reason
        )


# Named because naming them is the point: an operator can see at a glance that a scan
# covered two of five books, and which three it did not. Every entry stays here once a
# real provider is implemented, so coverage is always reported against the full list.
KNOWN_SOURCES: tuple[UnconfiguredSource, ...] = (
    UnconfiguredSource("Betfair Exchange", EXCHANGE,
                       "needs an app key; live prices cost a one-off activation fee"),
    UnconfiguredSource("Smarkets", EXCHANGE,
                       "needs an account username and password in ~/.smarkets"),
    UnconfiguredSource("Matchbook", EXCHANGE, "needs API credentials"),
    UnconfiguredSource("Paddy Power", BOOKMAKER, "no public odds API; needs a licensed feed"),
    UnconfiguredSource("Bet365", BOOKMAKER, "no public odds API; needs a licensed feed"),
)


@dataclass(frozen=True, slots=True)
class ScanCoverage:
    """How much of the intended universe a scan actually saw.

    Reported alongside every result. A scan that reached one book of five and found no arb
    has established almost nothing, and the ratio is what says so.
    """

    market: str
    quotes: tuple[MarketQuote, ...]

    @property
    def answered(self) -> tuple[MarketQuote, ...]:
        return tuple(q for q in self.quotes if q.status == CONFIGURED)

    @property
    def silent(self) -> tuple[MarketQuote, ...]:
        return tuple(q for q in self.quotes if q.status != CONFIGURED)

    @property
    def is_complete(self) -> bool:
        return bool(self.quotes) and not self.silent

    def describe(self) -> str:
        lines = [
            f"Coverage for {self.market}: {len(self.answered)} of {len(self.quotes)} "
            f"source(s) answered."
        ]
        for quote in self.silent:
            lines.append(f"  NOT COVERED  {quote.source}: {quote.reason}")
        if self.silent:
            lines.append(
                "  A price better than anything above may exist at a source that did not "
                "answer. Absence of an arb here is absence of evidence, not evidence of "
                "absence."
            )
        return "\n".join(lines)


def scan(market: str, sources: Sequence[OddsSource] = KNOWN_SOURCES) -> ScanCoverage:
    """Ask every source, keep every answer including the refusals."""

    return ScanCoverage(market, tuple(source.quote(market) for source in sources))
