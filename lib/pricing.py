"""What the book is worth now, from a source that is allowed to be unreachable.

`status.py` valued every holding with `value_at(None)` — the argument meaning "no price
available" — so the whole book marked UNPRICED however much was knowable, while
`AlpacaBroker.quote()` sat beside it able to answer. Both ends existed and nothing joined
them. This is the join. `docs/pricing-design.md` carries the design; what follows is only
the part that would look arbitrary in the code without it.

**The bid, never the mid or the ask.** A holding is worth what you could get for it. The
mid is the number everyone quotes and nobody trades at, and the ask states a price nobody
is offering you — on ten holdings that is the spread overstated ten times, in the figure a
holder looks at first. `Quote.executable_price` answers a different question, about what
an order would cost, and is right to use the other side.

**A price has a shelf life and it is stated, never defaulted.**
`Portfolio.value_at(stale_after_seconds=-1.0)` means "never goes stale", which is this
repository's founding defect wearing a timestamp. Every call here passes an explicit
ceiling, and `priced_at` comes from the feed's own timestamp rather than the moment of the
HTTP call — the difference `connectors/oddsapi` already argues at length, and the reason a
cached response cannot present itself as fresh.

**A shut market is not a stale price.** Fifteen minutes is a sensible ceiling on a Tuesday
afternoon and nonsense at the weekend, when the last trade genuinely is the last price. The
two are told apart rather than reconciled with a looser number, because a ceiling generous
enough to cover a long weekend is also generous enough to hide a feed that died on Friday
morning. So the market state is asked for, and:

    market OPEN     + older than the ceiling  ->  STALE
    market CLOSED   + older than the ceiling  ->  MARKET_CLOSED
    market UNKNOWN  + older than the ceiling  ->  STALE

The last line is the whole reason the clock returns three states. An unread clock resolving
to "closed" would relabel every stale price as an honest weekend one, turning an outage
into reassurance. Unknown keeps the stricter word.

**Looking and finding are different failures**, at both levels. A source that cannot be
reached at all is `COULD_NOT_LOOK` and says so once, for the book. A source that answered
and holds no price for a particular asset leaves that holding UNPRICED and *unquotable* —
which is the expected, correct outcome for a European UCITS ETF on a US broker, not a gap
to fill with a scraped number. A holding whose own request failed is UNPRICED and
*unreachable*, and is not the same fact as one that came back empty.

**Nothing here remembers a previous price.** A remembered value rendered as current looks
like data and is a memory; it is the vanished ledger reporting FIRST_SEEN, applied to
money. A failed look produces UNPRICED and the holding leaves the total.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, Sequence

from lib.portfolio import MARKET_CLOSED, STALE, UNPRICED, Position, Valuation

#: Fifteen minutes: long enough that refreshing a page does not mark a live book stale,
#: short enough that a price from before lunch is never rendered as the current one.
STALE_AFTER_SECONDS = 900.0

#: What the venue is doing. UNKNOWN is not a synonym for CLOSED — see the module docstring.
OPEN = "OPEN"
CLOSED = "CLOSED"
UNKNOWN = "UNKNOWN"

LOOKED = "LOOKED"
COULD_NOT_LOOK = "COULD_NOT_LOOK"


class PriceSourceError(Exception):
    """The source could not be asked. Distinct from it answering "no price for that"."""


@dataclass(frozen=True, slots=True)
class Price:
    """One price, carrying the three things that make it usable: unit, age and origin."""

    unit_price: float
    currency: str
    priced_at: str
    source: str


class PriceSource(Protocol):
    """What `value_book` needs, so `status.py` holds no connector knowledge.

    A second source — for the European ETFs, or for the chain lane — is then an argument
    rather than a rewrite, which is the lane-registry lesson applied one layer up.
    """

    name: str

    def unavailable_reason(self) -> str:
        """`""` when the source can be asked, otherwise what a person can do about it."""

    def market_state(self) -> str:
        """OPEN, CLOSED or UNKNOWN."""

    def price(self, asset: str) -> Price | None:
        """The price, or `None` when this source holds none for that asset.

        Raise `PriceSourceError` when the request itself failed. The two are different
        answers and the caller reports them differently.
        """


@dataclass(frozen=True, slots=True)
class Pricing:
    """One look at the book: what priced, what did not, and whether anyone was asked."""

    look: str
    valuations: tuple[Valuation, ...]
    source: str = ""
    market: str = UNKNOWN
    reason: str = ""
    #: Answered, holds no price for these. The normal state of a non-US listing here.
    unquotable: tuple[str, ...] = ()
    #: The request failed for these. Not the same fact, and not the same fix.
    unreachable: tuple[str, ...] = ()
    stale_after_seconds: float = STALE_AFTER_SECONDS

    @property
    def priced_count(self) -> int:
        return sum(1 for v in self.valuations if v.status != UNPRICED)

    def describe(self) -> str:
        if self.look == COULD_NOT_LOOK:
            # Two ways to reach COULD_NOT_LOOK and they want different sentences. The
            # single wording said "nothing was asked" directly beneath the reason "every
            # request to the price source failed", and never named which holdings failed.
            if self.unreachable:
                return (
                    f"PRICES  COULD_NOT_LOOK via {self.source or 'no source'}: {self.reason}. "
                    f"Every request failed — {', '.join(self.unreachable)} — so every holding "
                    f"below is UNPRICED for want of an answer, not for want of a listing."
                )
            return (
                f"PRICES  COULD_NOT_LOOK via {self.source or 'no source'}: {self.reason} "
                f"Every holding below is UNPRICED because nothing was asked, which is not "
                f"a book of unquotable assets."
            )
        lines = [
            f"PRICES  {self.priced_count} of {len(self.valuations)} holding(s) priced from "
            f"{self.source}, market {self.market}, stale after "
            f"{self.stale_after_seconds:,.0f}s."
        ]
        if self.unquotable:
            lines.append(
                f"  {self.source} holds no price for {', '.join(self.unquotable)}. It "
                f"answered; these are not listed with it. Pricing them is a second source, "
                f"not a retry."
            )
        if self.unreachable:
            lines.append(
                f"  The request failed for {', '.join(self.unreachable)} — unknown, not "
                f"unquotable. Re-run to find out which."
            )
        if self.market == UNKNOWN:
            lines.append(
                "  The market clock could not be read, so an old price is reported STALE "
                "rather than assumed to be a shut venue."
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "look": self.look,
            "source": self.source,
            "market": self.market,
            "reason": self.reason or None,
            "unquotable": list(self.unquotable),
            "unreachable": list(self.unreachable),
            "stale_after_seconds": self.stale_after_seconds,
            "priced": self.priced_count,
            "holdings": len(self.valuations),
        }


def value_book(
    positions: Sequence[Position],
    source: PriceSource,
    *,
    stale_after_seconds: float = STALE_AFTER_SECONDS,
) -> Pricing:
    """Value every position, and report how the answer was arrived at.

    One asset failing never fails the others: the loop values what it can and names the
    rest. `look` is `COULD_NOT_LOOK` only when nothing was asked — an unavailable source,
    or every single request failing — because a partial answer reported as no answer would
    hide a book that mostly priced, and no answer reported as a partial one would show an
    outage as a book of unquotable holdings.
    """

    unavailable = source.unavailable_reason()
    if unavailable:
        return Pricing(
            COULD_NOT_LOOK,
            tuple(p.value_at(None) for p in positions),
            source=getattr(source, "name", ""),
            reason=unavailable,
            stale_after_seconds=stale_after_seconds,
        )

    market = source.market_state()
    valuations: list[Valuation] = []
    unquotable: list[str] = []
    unreachable: list[str] = []

    for position in positions:
        try:
            price = source.price(position.asset)
        except PriceSourceError:
            # Unknown, not unpriced-because-unlisted. The holding leaves the total either
            # way; which of the two it was decides whether anybody should do anything.
            unreachable.append(position.asset)
            valuations.append(position.value_at(None))
            continue

        if price is None:
            unquotable.append(position.asset)
            valuations.append(position.value_at(None))
            continue

        valuation = position.value_at(
            price.unit_price,
            source=price.source,
            priced_at=price.priced_at,
            stale_after_seconds=stale_after_seconds,
            currency=price.currency,
        )
        if valuation.status == STALE and market == CLOSED and valuation.age_seconds >= 0:
            # `age_seconds < 0` means the age could not be established at all, and the
            # previous fix made that STALE precisely so it would leave the total. Relabelling
            # it MARKET_CLOSED here put it straight back in, because a shut market's last
            # price legitimately counts — so every evening and weekend a quote with no usable
            # timestamp reported PRICED and complete. A shut venue explains an OLD price. It
            # explains nothing about a price whose age is unknown.
            valuation = replace(valuation, status=MARKET_CLOSED)
        valuations.append(valuation)

    looked = COULD_NOT_LOOK if positions and len(unreachable) == len(positions) else LOOKED
    return Pricing(
        looked,
        tuple(valuations),
        source=getattr(source, "name", ""),
        market=market,
        reason=(
            "every request to the price source failed"
            if looked == COULD_NOT_LOOK else ""
        ),
        unquotable=tuple(unquotable),
        unreachable=tuple(unreachable),
        stale_after_seconds=stale_after_seconds,
    )


class AlpacaPrices:
    """`AlpacaBroker` as a `PriceSource`: the bid, in dollars, with the feed's timestamp.

    **The currency is stated, not inferred from the book.** Alpaca quotes US-listed
    securities in USD while this book records cost in EUR, and the whole reason
    `Valuation` carries its own currency is that these two must never be added.

    The broker's `quote()` returns `None` both when it is unconfigured and when the symbol
    has no two-sided price, so this checks configuration first and can then read a `None`
    as the second thing — the distinction the caller needs and the connector does not draw.
    """

    name = "alpaca"

    def __init__(self, broker) -> None:
        self._broker = broker

    def unavailable_reason(self) -> str:
        if not getattr(self._broker, "is_configured", False):
            return (
                "no Alpaca credentials: put key_id and secret_key in ~/.alpaca/ (mode "
                "600) with exactly one of paper or live, then re-run."
            )
        return ""

    def market_state(self) -> str:
        open_now = self._broker.is_market_open()
        if open_now is None:
            return UNKNOWN
        return OPEN if open_now else CLOSED

    def price(self, asset: str) -> Price | None:
        import http.client

        from lib.http_retry import TransientRetrievalError

        try:
            quote = self._broker.quote(asset)
        # `http.client.HTTPException` — IncompleteRead, BadStatusLine — is not an OSError,
        # so one malformed response from the venue escaped this handler entirely and came
        # out of `/api/v1/overview` as a 500. A bad response is the ordinary unreachable
        # case and belongs in the same bucket as a reset connection.
        except (TransientRetrievalError, OSError, ValueError, http.client.HTTPException) as error:
            raise PriceSourceError(f"{type(error).__name__}: {error}"[:120]) from error
        if quote is None:
            return None
        return Price(
            quote.bid,
            # Alpaca's equity feed is US-listed and quotes in dollars. Stated here rather
            # than assumed downstream, where it would be assumed to be the book's euro.
            "USD",
            quote.observed_at,
            self.name,
        )


def _impatient_opener(request):
    """One attempt, then the truth. The retrying opener is wrong for this caller.

    `retrying_urlopen` sleeps 5, 20 and 60 seconds on a 429 because it was written for a
    research connector where a rate limit is worth waiting out — a run that takes an extra
    minute still produces the right answer, and the alternative was a study whose result
    depended on how busy the API was that afternoon.

    Valuing the book is the opposite caller. It runs on a page load, once per holding, so
    the same policy turns one rate-limited dashboard refresh into fourteen minutes of
    sleeping across ten symbols, and the operator watches a blank panel while it happens.
    The design note for this job says it in one line: do not retry into the limit. A
    holding that hits a 429 goes UNPRICED and is NAMED as unreachable — the reader learns
    it now instead of being made to wait for the same answer.

    The lanes keep the retrying opener. A reaper sizing a position in the background is
    the first caller, not this one.
    """

    import urllib.request

    # A timeout is not optional here: the default is no timeout at all, and a hung socket
    # on one holding would stop the panel more completely than the retries just removed.
    return urllib.request.urlopen(request, timeout=10)


def alpaca_prices(directory: str = "~/.alpaca") -> AlpacaPrices:
    """The default source, resolved at call time.

    Deliberately not a module-level default argument: binding one at import is how a full
    `pytest` run once wrote a journal into the live `data/`.
    """

    from connectors.alpaca import AlpacaBroker

    return AlpacaPrices(AlpacaBroker.from_directory(directory, opener=_impatient_opener))
