"""The stocks lane: a company's own filings, a stated criterion, a price, a sized order.

Same sequence as the arb lane, over completely different evidence, and the interesting
difference is what the lane is FOR.

## This lane disqualifies. It does not select

`look` returns the watchlist a person supplied, not a discovery. That is deliberate and it
is the honest division of labour this repository has settled on: a board can veto but never
authorise, and the same asymmetry applies to a lane. Screening thousands of listed companies
down to the ones worth buying is a forecast dressed as a filter, and no amount of tagging
discipline makes "this one will go up" fall out of a 10-K.

What the filings CAN do is take a company off the list. A filer whose reported figures
disagree with each other across filings, whose history is split across tags, or who reports
in mixed units is a company whose own numbers cannot be compared — and that is an
observation, cited to the accession number that produced it.

So the person names the subject and declares the thesis. The lane tries to disqualify it.
Anything that survives is not thereby a recommendation, and the harvest says so.

## Observational or forecast, declared rather than assumed

`Criterion` carries its `kind`, and the distinction is not decoration:

    OBSERVATIONAL   "this filer restated three reporting spans"   a fact, from filings
    FORECAST        "filers who restate tend to underperform"     a prediction about them

The first is computed. The second is a claim about the future that no filing contains, so a
FORECAST criterion refuses construction without a named human declaring it — the same guard
`Thesis` and `EquivalenceDeclaration` already use, for the same reason. The machine may
observe. It may not predict on its own authority and then act on the prediction.

The default criterion is a restatement ceiling used as a DISQUALIFIER, which needs no
declarer because it makes no claim about what the price will do.

## Volatility is measured, not omitted

`lib/sizing.volatility_bound` turns unknown volatility into NOT_MEASURED and makes the whole
size INDETERMINATE, because dropping a ceiling you could not measure always raises the
permitted size. This lane therefore reads daily closes and computes realised movement rather
than leaving the constraint out — a lane that quietly sized on risk limit alone would be
sizing at full limit precisely when nothing is known about how far the price moves.

When the bars cannot be read the size is INDETERMINATE and the lane stops. That is the
intended behaviour and not a gap to route around.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from guards.human_acts import AUTOMATION_PREFIXES as _AUTOMATION_PREFIXES
from lib.candidates import INDETERMINATE, PASSED, REFUSED, Candidate, Stage
from lib.reaper import Reaper, Unworthy
from lib.sizing import (
    SIZED,
    Constraint,
    risk_limit,
    size_position,
    venue_maximum,
    volatility_bound,
)

OBSERVATIONAL = "OBSERVATIONAL"
FORECAST = "FORECAST"

#: Prefixes that cannot declare a forecast criterion. Identical to `lib.thesis`, because it
#: is the identical judgement: a claim about the future needs somebody accountable for it.
AUTOMATION_PREFIXES = _AUTOMATION_PREFIXES

#: Above this the two sides are far enough apart that the mid is fiction and the executable
#: price is materially worse than the screen price.
MAX_SPREAD_PCT = 1.0

#: How old a quote may be, during market hours, and still be sized against. Fifteen
#: minutes is generous for a liquid name and deliberately not "a session" — outside market
#: hours the age is not what disqualifies the price, the closed venue is, and those are
#: reported as different facts.
MAX_QUOTE_AGE_SECONDS = 900.0

#: A one-day move of this size should cost no more than the tolerated fraction of balance.
TOLERATED_MOVE_PCT = 2.0

#: Fewer closes than this and realised movement is a rumour rather than a measurement.
MIN_CLOSES = 10


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def realised_move_pct(closes: Sequence[float] | None) -> float | None:
    """Standard deviation of daily percentage moves, or None when it cannot be computed.

    None on every failure path — too few closes, a non-positive price, no history at all —
    because the caller turns None into NOT_MEASURED and a zero into "this stock does not
    move", and those must not be the same value.
    """

    if not closes or len(closes) < MIN_CLOSES:
        return None
    moves = []
    for previous, current in zip(closes, closes[1:]):
        if previous <= 0:
            return None
        moves.append((current - previous) / previous * 100.0)
    if len(moves) < 2:
        return None
    deviation = statistics.stdev(moves)
    return deviation if deviation > 0 else None


# --- the criterion -----------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Criterion:
    """What makes a filer eligible, and whether that is a thing observed or predicted."""

    name: str
    kind: str
    statement: str
    #: filings -> (verdict, detail). Verdict is one of PASSED / REFUSED / INDETERMINATE.
    test: Callable[[Mapping[str, Any]], tuple[str, str]]
    #: Required for a FORECAST. A prediction is not something a machine may make on its
    #: own authority and then trade on.
    declared_by: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {OBSERVATIONAL, FORECAST}:
            raise ValueError(
                f"kind must be {OBSERVATIONAL} or {FORECAST}, not {self.kind!r}. A "
                f"criterion that will not say which it is is the one worth distrusting"
            )
        if self.kind != FORECAST:
            return
        author = self.declared_by.strip().lower()
        if not author or any(author.startswith(p) for p in AUTOMATION_PREFIXES):
            raise ValueError(
                "a FORECAST criterion needs a named human: it asserts something no filing "
                "contains, and a machine originating its own predictions and then trading "
                "on them is the arrangement this repository exists to refuse"
            )


def restatement_limit(max_revised_spans: int = 0) -> Criterion:
    """A filer whose own numbers disagree across filings, used as a disqualifier.

    Note the direction. "This filer restated three spans" is an observation. "Restaters
    underperform, so short them" is a forecast, and building that as the default would
    smuggle a prediction in as a filter. Used this way the criterion only ever removes a
    company from consideration, which is a claim the filings support on their own.
    """

    def test(filings: Mapping[str, Any]) -> tuple[str, str]:
        if not filings:
            return INDETERMINATE, "no filing series were retrieved, so nothing was checked"

        revised: dict[str, int] = {}
        for label, series in filings.items():
            if getattr(series, "status", "") != "REPORTED":
                continue
            count = len(series.revised_durations())
            if count:
                revised[label] = count

        total = sum(revised.values())
        if total > max_revised_spans:
            detail = ", ".join(f"{label} ({count})" for label, count in sorted(revised.items()))
            return REFUSED, (
                f"{total} reporting span(s) were filed at more than one value: {detail}. "
                f"A restated figure and the original are two different facts, and a filer "
                f"disagreeing with itself is one whose figures cannot be compared."
            )
        return PASSED, (
            f"{total} restated reporting span(s) across {len(filings)} series, within a "
            f"ceiling of {max_revised_spans}."
        )

    return Criterion(
        name=f"no more than {max_revised_spans} restated reporting span(s)",
        kind=OBSERVATIONAL,
        statement=("a filer whose reported figures disagree with each other across filings "
                   "is one whose numbers cannot be compared"),
        test=test,
    )


# --- the cascade -------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Subject:
    """One watchlist entry with everything read about it, so stages need no I/O."""

    ticker: str
    filings: Mapping[str, Any]
    quote: Any = None
    closes: tuple[float, ...] | None = None
    reason: str = ""
    #: Whether the venue was open when this was read, asked of the venue. `None` means the
    #: clock could not be reached, which is NOT "closed" and NOT "open" — see `_freshness`.
    market_open: bool | None = None
    #: When the venue next opens, so a refusal on a Saturday can say when to try again.
    next_open: str = ""

    @property
    def subject(self) -> str:
        return self.ticker


@dataclass(frozen=True, slots=True)
class Reading:
    status: str
    detail: str
    blocking: bool = True

    def describe(self) -> str:
        return f"{self.status}: {self.detail}"


def screen_subject(
    subject: Subject, *, criterion: Criterion, max_spread_pct: float = MAX_SPREAD_PCT,
    max_quote_age_seconds: float = MAX_QUOTE_AGE_SECONDS,
) -> Candidate:
    """Cheapest and most fatal first: unreadable filings before an unreadable price."""

    stages: list[Stage] = []

    if not subject.filings:
        stages.append(Stage(
            "filings retrievable", INDETERMINATE, disqualifying=True,
            detail=(f"no filing series were retrieved for {subject.ticker}"
                    + (f": {subject.reason}" if subject.reason else "")
                    + ". This says nothing about what the company reports."),
        ))
    else:
        unreadable = [label for label, s in subject.filings.items()
                      if getattr(s, "status", "") == "INDETERMINATE"]
        if unreadable:
            stages.append(Stage(
                "filings retrievable", INDETERMINATE, disqualifying=True,
                detail=(f"{', '.join(sorted(unreadable))} could not be retrieved. Not a "
                        f"finding that the company does not report them."),
            ))
        else:
            stages.append(Stage(
                "filings retrievable", PASSED, disqualifying=True,
                detail=f"{len(subject.filings)} series read from the filer's own filings.",
            ))

    stages.append(Stage(
        "criterion is declared", PASSED, disqualifying=True,
        detail=(f"{criterion.kind}: {criterion.statement}"
                + (f" (declared by {criterion.declared_by})" if criterion.declared_by
                   else "; no human declarer is required for an observation")),
    ))

    verdict, detail = criterion.test(subject.filings)
    stages.append(Stage(criterion.name, verdict, detail=detail, disqualifying=True))

    stages.append(_comparability(subject))
    # Before the spread, because a stale quote's spread is not a fact about the market. On
    # the Saturday this was written, IEX's last quote of Friday was 10% wide on three
    # liquid names — market makers pull their books at the bell — and the spread gate
    # refused all three. It was right, and it was right by accident: had Friday's closing
    # quote been tight, a live order would have been sized against a price twenty hours
    # dead, and every line of the output would have read normally.
    currency_of_price = _freshness(subject, max_quote_age_seconds)
    if currency_of_price is not None:
        stages.append(currency_of_price)
    # The spread is only evaluated on a price that is current, because a spread taken from
    # a book nobody is maintaining is not a measurement of anything. On the Saturday this
    # was written, Friday's closing quotes were ~10% wide and the spread stage REFUSED all
    # three — and REFUSED outranks INDETERMINATE, so the output led with "the spread is
    # 9.72%" and buried the fact that the market was shut. A reader goes looking for
    # liquidity that was never missing. The cause is the answer, so the consequence is not
    # computed.
    if currency_of_price is None or currency_of_price.verdict == PASSED:
        stages.append(_price(subject, max_spread_pct))
    stages.append(_volatility(subject))
    return Candidate(subject.ticker, tuple(stages))


def _comparability(subject: Subject) -> Stage:
    """Mixed units and split tag histories, which make figures incomparable rather than bad."""

    mixed = [label for label, s in subject.filings.items()
             if len(getattr(s, "units_seen", ()) or ()) > 1]
    split = [label for label, s in subject.filings.items()
             if getattr(s, "alternates_with_data", ())]
    if mixed:
        return Stage(
            "figures are comparable", INDETERMINATE, disqualifying=True,
            detail=(f"{', '.join(sorted(mixed))} reported in more than one unit. Values in "
                    f"different units are not comparable and were not combined."),
        )
    if split:
        return Stage(
            "figures are comparable", INDETERMINATE, disqualifying=True,
            detail=(f"{', '.join(sorted(split))} also reported under another tag, so this "
                    f"series alone is not the whole history."),
        )
    return Stage(
        "figures are comparable", PASSED, disqualifying=True,
        detail="one unit per series and no history split across tags.",
    )


def quote_age_seconds(quote: Any, *, now: datetime | None = None) -> float | None:
    """How old the quote is, or None when that cannot be established.

    None on every failure path — no quote, no timestamp, an unparseable one — because the
    caller turns None into "cannot tell" and a zero into "brand new", and sizing a live
    order against a price whose age is unknown is the thing this exists to prevent.
    """

    stamp = str(getattr(quote, "observed_at", "") or "").strip()
    if not stamp:
        return None
    try:
        observed = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if observed.tzinfo is None:
        # A bare timestamp is assumed UTC rather than local. Assuming local would make the
        # measured age depend on the reader's clock, so the same quote would be fresh in
        # Dublin and stale in Sydney.
        observed = observed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (current - observed).total_seconds()


def _freshness(subject: Subject, max_age_seconds: float) -> Stage | None:
    """Is this price current — and if not, say WHICH not.

    Three different facts, deliberately not merged, because a reader responds to each
    differently:

        the market is shut      the last price genuinely IS the last price. Nothing is
                                broken; come back when it opens.
        the quote is STALE      the market is open and this price is old. Something is
                                wrong with the feed, and that is worth looking at now.
        the age is unknown      no timestamp, or the venue clock could not be reached.
                                Not fresh, not stale — unestablished.

    All three disqualify, because you cannot buy at a price you are not being offered. The
    naming is what differs, and it is the whole point: "STALE" printed on a Sunday would
    send somebody hunting a feed fault that does not exist.
    """

    if subject.quote is None:
        # No stage at all, rather than one reporting "not applicable". With no quote there
        # is no question of how old it is, and `decided_by` takes the first stage that did
        # not pass — so any stage emitted here, blocking or not, would take the refusal off
        # the price stage and hand the reader "there is no quote to age" instead of "no
        # quote with size on both sides was returned".
        return None

    age = quote_age_seconds(subject.quote)

    if subject.market_open is False:
        when = f" The venue next opens at {subject.next_open}." if subject.next_open else ""
        return Stage(
            "the quote is current", INDETERMINATE, disqualifying=True,
            detail=(f"the market is shut, so this price is the last one of the previous "
                    f"session rather than a stale reading"
                    + (f" ({age / 3600:.1f} hours old)" if age is not None else "")
                    + f". Market makers withdraw at the close, so its spread describes an "
                      f"empty book and not the market.{when}"),
        )

    if subject.market_open is None:
        return Stage(
            "the quote is current", INDETERMINATE, disqualifying=True,
            detail=("the venue clock could not be reached, so whether the market is open "
                    "is unknown. An unknown session is not an open one: a price cannot be "
                    "called current when nothing establishes that trading is happening."),
        )

    if age is None:
        return Stage(
            "the quote is current", INDETERMINATE, disqualifying=True,
            detail=("the quote carries no readable timestamp, so its age cannot be "
                    "established. An unmeasured age is not a young one."),
        )

    if age > max_age_seconds:
        return Stage(
            "the quote is current", INDETERMINATE, disqualifying=True,
            detail=(f"STALE: the market is open and this quote is {age / 60:.1f} minutes "
                    f"old, over a {max_age_seconds / 60:.0f} minute ceiling. The market is "
                    f"trading and this price is not keeping up with it."),
        )

    return Stage(
        "the quote is current", PASSED, disqualifying=True,
        detail=(f"the market is open and the quote is {age:.0f}s old, inside the "
                f"{max_age_seconds / 60:.0f} minute ceiling."),
    )


def _price(subject: Subject, max_spread_pct: float) -> Stage:
    if subject.quote is None:
        return Stage(
            "a two-sided price", INDETERMINATE, disqualifying=True,
            detail=("no quote with size on both sides was returned. A one-sided market is "
                    "not a price, and the last trade is not one either."),
        )
    spread = float(subject.quote.spread_pct)
    if spread > max_spread_pct:
        return Stage(
            "a two-sided price", REFUSED, disqualifying=True,
            detail=(f"the spread is {spread:.2f}%, over a {max_spread_pct:.2f}% ceiling. "
                    f"The mid is fiction at that width and you pay the ask."),
        )
    return Stage(
        "a two-sided price", PASSED, disqualifying=True,
        detail=(f"bid {subject.quote.bid:,.4f} / ask {subject.quote.ask:,.4f}, spread "
                f"{spread:.2f}%, observed {subject.quote.observed_at}."),
    )


def _volatility(subject: Subject) -> Stage:
    measured = realised_move_pct(subject.closes)
    if measured is None:
        return Stage(
            "realised movement is known", INDETERMINATE, disqualifying=True,
            detail=(f"fewer than {MIN_CLOSES} usable daily closes, so how far this price "
                    f"moves is unknown. Sizing without that ceiling would size at full "
                    f"risk limit exactly when nothing is known about the movement."),
        )
    return Stage(
        "realised movement is known", PASSED, disqualifying=True,
        detail=(f"{measured:.2f}% standard deviation of daily moves over "
                f"{len(subject.closes or ())} closes."),
    )


# --- the gates ---------------------------------------------------------------------

def gates_for(subject: Subject, *, portfolio: Any = None) -> tuple[Reading, ...]:
    """Preconditions no cascade stage establishes. Short, and every one blocks."""

    readings: list[Reading] = []
    if portfolio is not None and not getattr(portfolio, "readable", True):
        readings.append(Reading(
            "PORTFOLIO_UNREADABLE",
            ("what is already held could not be read, so whether this adds to an existing "
             "position or opens a new one is unknown rather than new"),
        ))
    for label, series in subject.filings.items():
        if getattr(series, "status", "") == "NOT_REPORTED":
            readings.append(Reading(
                "CONCEPT_NOT_REPORTED",
                (f"{label} is not reported under the {getattr(series, 'taxonomy', '?')} "
                 f"taxonomy. A statement about the tagging and the namespace asked, not a "
                 f"value of zero."),
                blocking=False,
            ))
    return tuple(readings)


# --- sizing ------------------------------------------------------------------------

def size_subject(
    subject: Subject,
    *,
    free_balance: float,
    max_exposure: float,
    pct_of_balance: float = 5.0,
    tolerated_move_pct: float = TOLERATED_MOVE_PCT,
    currency: str = "USD",
):
    """A whole number of shares, or a stated refusal. Never a fractional guess.

    Sized in cash through `lib.sizing`, which names the binding constraint, then converted
    at the ASK — the price you pay, not the mid everybody quotes and nobody trades at.
    """

    if subject.quote is None:
        return None

    price = float(subject.quote.executable_price("buy"))
    if price <= 0:
        return None

    constraints: list[Constraint] = [
        risk_limit(free_balance, pct_of_balance),
        Constraint("thesis exposure limit", max_exposure, "stated on the thesis"),
        volatility_bound(free_balance, realised_move_pct(subject.closes),
                         tolerated_move_pct),
        venue_maximum(float(subject.quote.ask_size) * price, "the ask at Alpaca"),
    ]

    size = size_position(subject.ticker, constraints, currency=currency)
    if size.status != SIZED:
        # INDETERMINATE keeps its meaning: a constraint was not measured. Returning None
        # is what the reaper turns into INDETERMINATE, and REFUSED here means every
        # ceiling was zero, which is a measured no.
        return None if size.status == "INDETERMINATE" else Unworthy(
            f"every permitted size was zero or less, bound by {size.bound_by}")

    shares = int(size.amount // price)
    if shares < 1:
        return Unworthy(
            f"{size.amount:,.2f} {currency} bound by {size.bound_by} does not buy one "
            f"share at {price:,.4f}. Fractional shares are available and deliberately not "
            f"used: a position too small to round to one share is too small to be worth "
            f"the position.")

    return StockOrder(
        ticker=subject.ticker, side="buy", shares=shares, price=price,
        cash=round(shares * price, 2), currency=currency, bound_by=size.bound_by,
        sizing=size, at=_now(),
    )


@dataclass(frozen=True, slots=True)
class StockOrder:
    """A sized, unplaced order. The instruction a person or the adapter acts on."""

    ticker: str
    side: str
    shares: int
    price: float
    cash: float
    currency: str
    bound_by: str
    sizing: Any
    at: str

    def describe(self) -> str:
        lines = [
            f"ORDER  {self.side.upper()} {self.shares} {self.ticker} at up to "
            f"{self.price:,.4f} {self.currency}",
            f"  {self.cash:,.2f} {self.currency}, bound by {self.bound_by}",
            f"  priced at the ask, not the mid. Read {self.at}.",
            "",
            self.sizing.describe(),
        ]
        return "\n".join(lines)


def measure_order(order: StockOrder) -> tuple[float, float]:
    """The breakers check cash at risk. The claimed edge is zero, and that is not a slip.

    An arb slip claims a guaranteed return and the sanity bound catches a misplaced decimal
    in it. A stock purchase claims no edge at all — the thesis is the reason, and it is a
    person's, unquantified on purpose. Handing the breakers a made-up percentage here so
    the field looks populated would be inventing the exact number this lane declines to.
    """

    return (float(order.cash), 0.0)


# --- assembly ----------------------------------------------------------------------

def build_stocks_reaper(
    *,
    watchlist: Sequence[str],
    theses: Any,
    breakers: Any,
    free_balance: float,
    criterion: Criterion | None = None,
    broker: Any = None,
    client: Any = None,
    concepts: Mapping[str, Sequence[str]] | None = None,
    portfolio: Any = None,
    register: Any = None,
    pct_of_balance: float = 5.0,
    tolerated_move_pct: float = TOLERATED_MOVE_PCT,
    max_spread_pct: float = MAX_SPREAD_PCT,
    max_quote_age_seconds: float = MAX_QUOTE_AGE_SECONDS,
    currency: str = "USD",
    history_days: int = 30,
) -> Reaper:
    """The stocks lane as a `Reaper`. It sizes an order and stops.

    `theses` is a `lib.thesis.ThesisRegister` or anything with `.current(subject)`. A
    watchlist entry with no live thesis is REFUSED rather than skipped, because "nobody
    authorised this" is a result worth printing.
    """

    from check_stock import CONCEPTS

    tags = dict(concepts or CONCEPTS)
    rule = criterion or restatement_limit()

    def look():
        from connectors.edgar import EdgarClient

        if not getattr(theses, "readable", True):
            # Lane-wide, and COULD_NOT_LOOK rather than "nothing is authorised". A register
            # that would not parse answering "no thesis" is indistinguishable from one that
            # parsed and was empty, and the second is a reason to stop while the first is a
            # broken file.
            raise RuntimeError(
                f"the thesis register could not be read "
                f"({getattr(theses, 'reason', 'no reason recorded')}), so what is "
                f"authorised is unknown rather than nothing"
            )

        edgar = client if client is not None else EdgarClient()
        desk = broker
        if desk is None:
            from connectors.alpaca import AlpacaBroker

            desk = AlpacaBroker.from_directory()

        # Once per run, not per ticker: the session is a property of the venue and asking
        # five times invites five answers. `None` when it could not be asked, which the
        # freshness stage reports as unestablished rather than guessing either way.
        # getattr, because a price source that cannot answer "is the venue open" is a real
        # case — a second connector, a stub, a feed that only quotes — and it must resolve
        # to "unknown session" rather than an AttributeError that reads as COULD_NOT_LOOK
        # for the whole lane.
        ask_clock = getattr(desk, "clock", None) if desk is not None else None
        clock = ask_clock() if callable(ask_clock) else None
        market_open = clock.is_open if clock is not None else None
        next_open = clock.next_open if clock is not None else ""

        asked, answered, subjects = len(watchlist), 0, []
        for ticker in watchlist:
            try:
                cik = edgar.cik_for_ticker(ticker)
                filings = {label: edgar.first_reported(cik, list(candidates))
                           for label, candidates in tags.items()}
            except Exception as error:  # noqa: BLE001 - one silent filer is not a silent scan
                subjects.append(Subject(ticker, {}, reason=f"{type(error).__name__}: {error}"[:120]))
                continue
            answered += 1
            subjects.append(Subject(
                ticker, filings,
                quote=desk.quote(ticker) if desk is not None else None,
                closes=desk.daily_closes(ticker, days=history_days) if desk is not None
                else None,
                market_open=market_open, next_open=next_open,
            ))

        if not answered:
            raise RuntimeError(
                f"EDGAR answered for none of {asked} watchlist entries; nothing was read"
            )
        return subjects, asked, answered

    return Reaper(
        name="stocks", lane="stocks",
        look=look,
        screen=lambda s: screen_subject(s, criterion=rule, max_spread_pct=max_spread_pct,
                                        max_quote_age_seconds=max_quote_age_seconds),
        gates=lambda s: gates_for(s, portfolio=portfolio),
        thesis_for=lambda s: theses.current(s.ticker),
        size=lambda s, permission: size_subject(
            s, free_balance=free_balance,
            max_exposure=_limit_from(theses, s.ticker, free_balance),
            pct_of_balance=pct_of_balance, tolerated_move_pct=tolerated_move_pct,
            currency=currency),
        breakers=breakers,
        measure=measure_order,
        register=register,
        # The ticker, not the price or the size. Buying MODN today and again tomorrow at a
        # different price is the same watchlist entry acted on twice.
        identity=lambda s: f"stocks:{s.ticker}",
    )


def _limit_from(theses: Any, ticker: str, fallback: float) -> float:
    thesis = theses.current(ticker)
    return float(thesis.max_exposure) if thesis is not None else fallback
