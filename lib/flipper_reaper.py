"""The flipper lane: an item, what similar ones sold for, and what the round trip leaves.

`lib/reaper.py` holds the sequence. This supplies the five callables, in the shape
`docs/flipper-design.md` specified on 2026-08-09, so the interesting content is what each
stage refuses.

    look     candidate items from the configured sources, with comparables for each
    screen   the cascade below, cheapest and most fatal first
    gates    physical capacity, the authorisation ceiling, the item floor
    thesis   a bounded standing authority under a figure, per-item above it
    size     the buy price, against a comparable-backed exit DISTRIBUTION

The cascade, from the design document:

    the item is what it says          an exact key: title, qualifiers, grade AND grader
    there are enough sold comparables n >= 5 within 90 days, or INDETERMINATE
    the exit is a distribution        spread and count stated, never a single number
    the round trip is affordable      fees, postage, returns, before any margin
    there is capacity                 physical, not just financial

## Why the authorisation is a hybrid and not a standing grant

The arb lane has a `StandingAuthority` and it is defensible for one stated reason: an arb
makes **no claim about the fixture**. A flip makes exactly such a claim — that this item is
underpriced and will resell — so a standing authority for flipping would authorise a
judgement in advance, which is what the arb one is careful not to do.

Per-item theses are honest and do not scale, and volume is the whole point of the function.
So this is option 3 from the design: a bounded standing authority **under a figure**, and a
per-item thesis above it. The figure is the number at which somebody wants to look at an
item themselves before money moves, and it is theirs to set.

## AT_CAPACITY is not NOTHING_FOUND

Twenty items is how many fit in a house and can be packed and posted in a week, not a risk
control. A full shelf is a different fact from a quiet market and leads somewhere else
entirely — the next thing to do is sell something, not look harder — so it is refused by
name at the gates rather than allowed to look like a lane that found nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from lib.candidates import INDETERMINATE, PASSED, REFUSED, Candidate, Stage
from lib.flipper import (
    CAPACITY,
    COMPARABLE_FLOOR,
    COMPARABLE_WINDOW_DAYS,
    MINIMUM_BUY,
    NOT_WORTH_IT,
    PRICED,
    ROUTINE_NET_PCT,
    URGENT,
    URGENT_NET_PCT,
    Capacity,
    Distribution,
    FeeSchedule,
    ItemKey,
    RoundTrip,
    distribution,
    round_trip,
    tier,
)
from lib.reaper import Reaper, Unworthy
from lib.thesis import Thesis

#: How wide the observed sales may be, as a percentage of the median, before the
#: distribution stops describing one item. Two sales at 100 and 104 and two at 40 and 200
#: have the same median and are not the same evidence — past this the spread usually means
#: the key is catching two different things (a reprint, a different parallel, a damaged
#: slab) rather than one item with a volatile price.
MAXIMUM_SPREAD_PCT = 120.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Reading:
    """One precondition the prices cannot establish, and whether it stops the lane."""

    status: str
    detail: str
    blocking: bool = True

    def describe(self) -> str:
        return f"{self.status}: {self.detail}"


@dataclass(frozen=True, slots=True)
class Listing:
    """An item somebody is selling, as a source described it."""

    key: ItemKey
    price: float
    currency: str
    source: str
    url: str = ""
    observed_at: str = ""

    @property
    def subject(self) -> str:
        return f"{self.key.describe()} at {self.price:,.2f} {self.currency}"


@dataclass(frozen=True, slots=True)
class Opportunity:
    """One listing worked through, carried between the reaper's stages.

    Assembled in `look` rather than recomputed per stage, for the reason every lane here
    repeats: a stage that recomputed would screen one number and size another.
    """

    listing: Listing
    comparables: Distribution
    trip: RoundTrip | None
    capacity: Capacity
    lookups: tuple[Any, ...] = ()

    @property
    def subject(self) -> str:
        return self.listing.subject

    @property
    def market(self) -> str:
        """Named so `lib.reaper._work` titles the harvest with the item rather than the
        object's repr. The item IS the subject here, unlike the mispricing lane where the
        fixture and the position are different things."""

        return self.listing.subject

    @property
    def net_margin_pct(self) -> float:
        return self.trip.net_margin_pct if self.trip is not None else 0.0

    @property
    def tier(self) -> str:
        return tier(self.net_margin_pct) if self.trip is not None else NOT_WORTH_IT


# --- the cascade -------------------------------------------------------------------------

def screen_opportunity(
    opportunity: Opportunity,
    *,
    minimum_buy: float = MINIMUM_BUY,
    routine_pct: float = ROUTINE_NET_PCT,
    maximum_spread_pct: float = MAXIMUM_SPREAD_PCT,
) -> Candidate:
    """The five stages from the design, in order, with the first refusal decisive."""

    listing = opportunity.listing
    stages: list[Stage] = []

    stages.append(Stage(
        "the item is what it says", PASSED, disqualifying=True,
        detail=(f"an exact key: {listing.key.describe()}. Grade and grader are part of it, "
                f"so a comparable that does not match on both is a different item with the "
                f"same name.")))

    if listing.price < minimum_buy:
        stages.append(Stage(
            "the item clears the floor", REFUSED, disqualifying=True,
            detail=(f"{listing.price:,.2f} {listing.currency} is under the "
                    f"{minimum_buy:,.2f} floor. Postage and the fixed fee do not scale "
                    f"down: below this no realistic markup covers sourcing, listing, "
                    f"packing and posting. This is arithmetic, not taste.")))
    else:
        stages.append(Stage("the item clears the floor", PASSED, disqualifying=True,
                            detail=f"{listing.price:,.2f} {listing.currency}"))

    if opportunity.comparables.status != PRICED:
        stages.append(Stage(
            "there are enough sold comparables", INDETERMINATE, disqualifying=True,
            detail=(f"{opportunity.comparables.reason} This is NOT a low estimate and NOT "
                    f"a wide range — what this item resells for has not been established.")))
    else:
        stages.append(Stage(
            "there are enough sold comparables", PASSED, disqualifying=True,
            detail=opportunity.comparables.describe().replace("\n", " ")))

    spread = opportunity.comparables.spread_pct
    if opportunity.comparables.status == PRICED and spread is not None and (
            spread > maximum_spread_pct):
        stages.append(Stage(
            "the exit is a distribution", REFUSED, disqualifying=True,
            detail=(f"the observed sales span {spread:.0f}% of their median, over the "
                    f"{maximum_spread_pct:.0f}% limit. A spread that wide usually means "
                    f"the key is catching two different things — a reprint, another "
                    f"parallel, a damaged slab — rather than one item with a volatile "
                    f"price. Narrow the key rather than averaging across it.")))
    elif opportunity.comparables.status == PRICED:
        stages.append(Stage(
            "the exit is a distribution", PASSED, disqualifying=True,
            detail=(f"n={opportunity.comparables.count} over "
                    f"{opportunity.comparables.window_days} days, spread "
                    f"{spread or 0:.0f}% of median. Sized against the conservative end, "
                    f"not the median: the median is what a typical seller got, and "
                    f"assuming this sale is typical is a forecast.")))
    else:
        stages.append(Stage(
            "the exit is a distribution", INDETERMINATE, disqualifying=True,
            detail="no distribution exists, so its shape was not examined"))

    if opportunity.trip is None:
        stages.append(Stage(
            "the round trip is affordable", INDETERMINATE, disqualifying=True,
            detail=("the round trip was not costed, because there is no exit price to "
                    "cost it against")))
    elif opportunity.net_margin_pct < routine_pct:
        stages.append(Stage(
            "the round trip is affordable", REFUSED, disqualifying=True,
            detail=(f"{opportunity.net_margin_pct:+.1f}% net on the buy, under the "
                    f"{routine_pct:.0f}% routine threshold. Stated NET: a markup that has "
                    f"not had fees taken out of it is the number that made the original "
                    f"40 EUR tier look viable when it lost money.")))
    else:
        stages.append(Stage(
            "the round trip is affordable", PASSED, disqualifying=True,
            detail=(f"{opportunity.net_margin_pct:+.1f}% net on the buy after commission, "
                    f"the fixed fee, processing, postage and a returns allowance — "
                    f"{opportunity.tier}")))

    if opportunity.capacity.full:
        stages.append(Stage(
            "there is capacity", REFUSED, disqualifying=True,
            detail=opportunity.capacity.describe()))
    else:
        stages.append(Stage("there is capacity", PASSED, disqualifying=True,
                            detail=opportunity.capacity.describe()))

    return Candidate(opportunity.subject, tuple(stages))


# --- the gates ---------------------------------------------------------------------------

def gates_for(
    opportunity: Opportunity,
    *,
    per_item_thesis_above: float,
    theses: Any = None,
) -> tuple[Reading, ...]:
    """What the prices cannot establish. Capacity, the authorisation ceiling, the sources.

    Capacity appears here as well as in the cascade, and that is not duplication: the
    cascade decides whether to surface and the gates decide whether the thesis may
    authorise. A shelf that stopped one and not the other would be a hole exactly the width
    of whichever check somebody remembered to run.
    """

    readings: list[Reading] = []

    if opportunity.capacity.full:
        readings.append(Reading("AT_CAPACITY", opportunity.capacity.describe()))

    price = opportunity.listing.price
    if price > per_item_thesis_above:
        subject = opportunity.subject
        written = theses.get(subject) if isinstance(theses, dict) else None
        if written is None:
            readings.append(Reading("PER_ITEM_THESIS_REQUIRED", (
                f"{price:,.2f} {opportunity.listing.currency} is above the "
                f"{per_item_thesis_above:,.2f} ceiling of the standing authority. A flip "
                f"makes a claim about the item — unlike an arb, which makes none about the "
                f"fixture — so above the figure somebody set, they look at it themselves "
                f"before money moves. Write a thesis for: {subject}")))

    silent = [look for look in opportunity.lookups
              if getattr(look, "status", "") != "READ"]
    if silent:
        # Non-blocking: too few comparables already blocks in the cascade, and this says
        # WHY the count is low, which is a different and more useful thing to read.
        readings.append(Reading("COMPARABLE_SOURCE_SILENT", "; ".join(
            getattr(look, "describe", lambda: str(look))() for look in silent),
            blocking=False))

    return tuple(readings)


# --- sizing --------------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BuySuggestion:
    """An item to go and buy by hand, with the evidence and the uncertainty on it.

    Never a point estimate of what it will fetch. `docs/flipper-design.md`: `n=3 over 90
    days` and `n=47 over 14 days` are different facts and must not both render as "sells
    for 120", so the count, the window and the spread are printed on every suggestion
    whether the reader wants them or not.
    """

    subject: str
    url: str
    buy: float
    currency: str
    tier: str
    trip: RoundTrip
    comparables: Distribution
    source: str = ""

    @property
    def stake(self) -> float:
        return self.buy

    def describe(self) -> str:
        lines = [
            f"{self.tier} — BUY BY HAND: {self.subject}",
            f"  {self.url}" if self.url else f"  from {self.source}",
            "",
            "  What comparable items ACTUALLY SOLD FOR:",
            f"    {self.comparables.describe()}",
            "",
            "  The round trip:",
            self.trip.describe(),
            "",
            "  THE EXIT IS NOT CONTRACTED. Sold comparables say others sold at that "
            "price, not that you will. Nothing has been bought.",
        ]
        if self.tier == URGENT:
            lines.append(
                f"  URGENT means {URGENT_NET_PCT:.0f}%+ net and is meant to be rare. If "
                f"these start arriving often, the thresholds are wrong rather than the "
                f"market being generous.")
        return "\n".join(lines)


def size_opportunity(
    opportunity: Opportunity,
    *,
    ring_fence_limit: float,
    minimum_buy: float = MINIMUM_BUY,
    routine_pct: float = ROUTINE_NET_PCT,
):
    """A suggestion, or a stated refusal. Never a suggestion sized off an asking price.

    There is no path here by which an asking price becomes a number: the exit comes from
    `opportunity.comparables`, which `lib.flipper.distribution` builds from completed sales
    only, and a distribution that could not be built is INDETERMINATE rather than thin.
    """

    listing = opportunity.listing

    if opportunity.comparables.status != PRICED or opportunity.trip is None:
        # None rather than Unworthy: this is a constraint that could not be MEASURED, which
        # the reaper reports as INDETERMINATE. "Too few sales to know" is not "I worked it
        # out and it is not worth it".
        return None

    if opportunity.capacity.full:
        return Unworthy(opportunity.capacity.describe())

    if listing.price < minimum_buy:
        return Unworthy(
            f"{listing.price:,.2f} {listing.currency} is under the {minimum_buy:,.2f} "
            f"floor; postage and the fixed fee do not scale down")

    if listing.price > ring_fence_limit:
        return Unworthy(
            f"{listing.price:,.2f} {listing.currency} is over the per-item ring-fence of "
            f"{ring_fence_limit:,.2f}. The item is not the problem; the size is")

    if opportunity.net_margin_pct < routine_pct:
        return Unworthy(
            f"{opportunity.net_margin_pct:+.1f}% net on the buy, under the "
            f"{routine_pct:.0f}% threshold — after commission, the fixed fee, processing, "
            f"postage and a returns allowance")

    return BuySuggestion(
        subject=listing.subject, url=listing.url, buy=listing.price,
        currency=listing.currency, tier=opportunity.tier, trip=opportunity.trip,
        comparables=opportunity.comparables, source=listing.source)


def measure_suggestion(suggestion: BuySuggestion) -> tuple[float, float]:
    """What the breakers check: how much is going out, and the margin being claimed."""

    return (float(suggestion.buy), float(suggestion.trip.net_margin_pct))


# --- the thesis ------------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BoundedAuthority:
    """A standing grant with a ceiling, and a per-item thesis above it.

    Option 3 from `docs/flipper-design.md`, and the bound is the whole point. An arb's
    standing authority is defensible because the position makes no claim about the fixture;
    a flip DOES claim the item is underpriced and will resell, so an unbounded standing
    grant would authorise that judgement in advance for every item forever.
    """

    declared_by: str
    reasoning: str
    considered: tuple[str, ...]
    expires_at: str
    #: The most a single item may cost under the standing grant. Above this a person writes
    #: a thesis for the item — the figure is theirs, and it is the number at which they want
    #: to look at something themselves before money moves.
    per_item_ceiling: float
    max_exposure: float
    declared_at: str = ""
    currency: str = "EUR"

    STANDING_CAVEAT = (
        "this authorisation was minted from a standing grant bounded at a per-item "
        "figure: nobody looked at this particular item before authorising it, and — "
        "unlike an arbitrage — the position DOES rest on a claim that the item is "
        "underpriced and will resell. Above the ceiling a person writes their own thesis"
    )

    def __post_init__(self) -> None:
        from lib.thesis import AUTOMATION_PREFIXES

        author = self.declared_by.strip().lower()
        if not author:
            raise ValueError("a standing authority needs a named author")
        if any(author.startswith(prefix) for prefix in AUTOMATION_PREFIXES):
            raise ValueError(
                f"{self.declared_by!r} cannot hold a standing authority. Minting theses "
                f"from it does not launder the authorship: whoever is named on the grant "
                f"is named on every item bought under it")
        if self.per_item_ceiling <= 0:
            raise ValueError(
                "a per-item ceiling of nought or less means every item needs its own "
                "thesis, which is honest and is not what a standing grant is for. Set the "
                "figure at which you want to look at something yourself")

    def thesis_for(self, subject: str) -> Thesis:
        return Thesis(
            subject=subject, declared_by=self.declared_by, reasoning=self.reasoning,
            considered=tuple(self.considered) + (self.STANDING_CAVEAT,),
            declared_at=self.declared_at or _now().isoformat(timespec="seconds"),
            expires_at=self.expires_at, max_exposure=self.max_exposure,
            currency=self.currency)


# --- assembly ---------------------------------------------------------------------------------

def flipper_identity(opportunity: Opportunity) -> str:
    """The item key and the source. Never the asking price.

    Same argument as `lib.seen.arb_identity`: including the price makes every relist a new
    sighting and the register dedupes nothing while appearing to work. The source is in it
    because the same card listed on two sites is two things to go and buy.
    """

    return f"{opportunity.listing.key.key}|{opportunity.listing.source}"


def opportunities_from(
    listings: Sequence[Listing],
    *,
    sources: Sequence[Any],
    fees: FeeSchedule,
    capacity: Capacity,
    now: datetime | None = None,
    floor: int = COMPARABLE_FLOOR,
    window_days: int = COMPARABLE_WINDOW_DAYS,
) -> list[Opportunity]:
    """Every listing, with its comparables gathered and its round trip costed."""

    from connectors.ebay import gather

    moment = now or _now()
    out: list[Opportunity] = []
    for listing in listings:
        comparables, lookups = gather(listing.key, sources)
        spread = distribution(listing.key, comparables, now=moment, floor=floor,
                              window_days=window_days, currency=listing.currency)
        exit_price = spread.conservative
        trip = (round_trip(listing.price, exit_price, fees)
                if spread.status == PRICED and exit_price is not None else None)
        out.append(Opportunity(listing, spread, trip, capacity, lookups))
    return out


def build_flipper_reaper(
    *,
    authority: BoundedAuthority,
    breakers: Any,
    fees: FeeSchedule,
    ring_fence_limit: float,
    sources: Sequence[Any] = (),
    listings: Callable[[], tuple[Sequence[Listing], int, int]] | None = None,
    holdings: Callable[[], Sequence[Any]] | None = None,
    theses: Any = None,
    register: Any = None,
    capacity_limit: int = CAPACITY,
    minimum_buy: float = MINIMUM_BUY,
    routine_pct: float = ROUTINE_NET_PCT,
    now: Callable[[], datetime] = _now,
) -> Reaper:
    """The flipper lane as a `Reaper`. Nothing here buys anything, and nothing can.

    eBay takes no automated purchase worth relying on, and Facebook Marketplace and DoneDeal
    have no public API at all — which is not a missing adapter, exactly as bookmakers having
    no betting API is not one for arb. `lib.placing.NO_ADAPTER` says so by name.
    """

    def look():
        from lib.flipper import capacity_from

        if listings is None:
            # Raising is correct: COULD_NOT_LOOK. A lane with no source that reported
            # "no deals today" would be the exact confusion the status set exists to
            # prevent, and it is the likeliest state of this lane for a while.
            raise RuntimeError(
                "no listing source is configured, so nothing was examined. This is not a "
                "finding that there is nothing worth buying.")

        found, asked, answered = listings()
        shelf = capacity_from(holdings() if holdings is not None else (),
                              limit=capacity_limit, now=now())
        worked = opportunities_from(found, sources=sources, fees=fees, capacity=shelf,
                                    now=now())
        # Everything is carried forward, including the ones with too few comparables. The
        # cascade reports each refusal by name, which is the useful output of a lane whose
        # commonest honest answer is "not enough sales to know".
        return worked, asked, answered

    return Reaper(
        name="flipper", lane="flipper",
        look=look,
        screen=lambda o: screen_opportunity(o, minimum_buy=minimum_buy,
                                            routine_pct=routine_pct),
        gates=lambda o: gates_for(
            o, per_item_thesis_above=authority.per_item_ceiling, theses=theses),
        thesis_for=lambda o: authority.thesis_for(o.subject),
        size=lambda o, _permission: size_opportunity(
            o, ring_fence_limit=ring_fence_limit, minimum_buy=minimum_buy,
            routine_pct=routine_pct),
        breakers=breakers,
        measure=measure_suggestion,
        register=register,
        identity=flipper_identity,
    )
