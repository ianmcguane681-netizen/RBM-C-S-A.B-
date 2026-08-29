"""What an item is, what similar ones actually sold for, and what the round trip costs.

Built to `docs/flipper-design.md`, which was decided on 2026-08-09 and settles the scope,
the floor, both tier thresholds, the capacity and the horizon. What is implemented here is
everything that does not depend on the one question still open — whether the eBay account
can read SOLD listings at all. That question decides where comparables come from; it does
not change what a comparable IS, what the fee arithmetic does, or what happens when there
are too few. Those are most of the work and they are here.

## The whole discipline, in one distinction

**A completed sale is evidence. An asking price is somebody's hope.** A flipper built on
asking prices computes margins against numbers nobody paid, and it produces confident,
wrong, profitable-looking suggestions all day. So the vocabulary this repository already
uses is enforced in the type: a `Comparable` carries `SOLD` or `ASKING`, `distribution`
refuses to build from asking prices at all, and there is no code path by which an asking
price reaches a stake.

## A distribution, never a number

Sold comparables say *others sold at that price*, not that you will. So a suggestion
carries what similar items actually fetched, how many, over what window, and the spread.
`n=3 over 90 days` and `n=47 over 14 days` are different facts and must not both render as
"sells for 120". Below the floor — five sales within ninety days, matching grade AND grader
— the verdict is `INDETERMINATE`. Not a low estimate, not a wide range: unestablished.

**The grade is part of the identity, not a modifier on it.** The same card raw and at PSA 10
can differ by fifty times, so a comparable that does not match on grade and grader is not a
comparable, it is a different item with the same name. Grade inflation between graders is a
live argument in trading cards, which is exactly why both halves are in the key.

## Fees before margin, always

Platform commission, the fixed fee, payment processing, postage by weight band, and an
assumed returns rate — every one before a margin is stated. The fee arithmetic is what
inverted the original tiering: a 40 EUR item needs a 32% markup merely to break even and a
200 EUR item needs 21%, because postage and the fixed fee do not scale down. That is where
the 75 EUR floor comes from, and it settles the loose-retro-games question on arithmetic
rather than taste.

## The exit is never contracted

Stocks and arb settle on their own; a flip never does. An item can sit unsold indefinitely,
so there is a write-down horizon — fifty days, then off the list — because an item nobody
bid on for fifty days is not worth what was paid for it, and carrying it at cost overstates
the book.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

# What a price IS. The distinction the whole module is built to keep.
SOLD = "SOLD"
ASKING = "ASKING"

# What was established about an item's resale value.
PRICED = "PRICED"
INDETERMINATE = "INDETERMINATE"

# What the lane thinks should be done about it, and how loudly.
URGENT = "URGENT"
ROUTINE = "ROUTINE"
NOT_WORTH_IT = "NOT_WORTH_IT"
BELOW_FLOOR = "BELOW_FLOOR"
AT_CAPACITY = "AT_CAPACITY"

#: Decided 2026-08-09. Below this no realistic markup makes an item worth sourcing,
#: listing, packing and posting — see the arithmetic in docs/flipper-design.md, which is
#: also where the loose-retro-games question was settled.
MINIMUM_BUY = 75.0

#: Net of every fee, not as a markup. A markup that has not had fees taken out of it is the
#: number that made the original 40 EUR tier look viable when it lost money.
URGENT_NET_PCT = 50.0
ROUTINE_NET_PCT = 30.0

#: How far apart the tiers must stay. The failure to design against is tier inflation: if
#: ROUTINE items arrive often they are read as noise, and the day an URGENT arrives it is
#: skimmed with them. Asserted in the tests so the two can never be tuned together into one.
MINIMUM_TIER_GAP_PCT = 15.0

#: How many items fit in a house and can be packed and posted in a week. A risk control for
#: stocks; a physical fact here, and usually tighter than the ring-fence.
CAPACITY = 20

#: Unsold for this long and it comes off the list. Not a valuation judgement dressed up: an
#: item nobody bid on for fifty days is not worth what was paid for it.
WRITE_DOWN_DAYS = 50

#: The comparable floor: this many completed sales, within this window, matching grade AND
#: grader. Ninety days is deliberately tight — cards bubbled through 2020-22 and corrected,
#: so a sale from 2021 is a different market rather than an old data point.
COMPARABLE_FLOOR = 5
COMPARABLE_WINDOW_DAYS = 90

#: Graders whose numbers this lane will treat as an identity. Not a quality ranking: it is
#: the set whose grades are printed on a slab with a cert number, which is what makes the
#: key machine-readable. CGC is here because it grades a large share of TCG and omitting it
#: would discard comparables that exist.
GRADERS = frozenset({"PSA", "BGS", "SGC", "CGC", "WATA", "VGA"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# --- what the item is ------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ItemKey:
    """The exact identity two fungible items share. Grade and grader are part of it.

    Not a title match with a grade filter applied afterwards. The same card raw and at
    PSA 10 can differ by fifty times, and grade inflation between graders is a live argument
    in trading cards — a CGC 9.5 and a PSA 10 are not the same item. So both are in the key,
    and a comparable that does not match on them is not a comparable at all.

    `cert` is optional and is never part of matching: a cert number identifies one physical
    slab, and two slabs of the same card at the same grade are exactly what a comparable
    set is made of.
    """

    title: str
    grade: str
    grader: str
    #: Card: set and year and parallel. Game: platform, region, seal or box type. Kept as
    #: one ordered tuple because what makes an identity exact differs by category and a
    #: field-per-category schema would make adding one a migration.
    qualifiers: tuple[str, ...] = ()
    cert: str = ""

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("an item with no title has no identity to match on")
        if not str(self.grade).strip():
            raise ValueError(
                f"{self.title}: no grade. The grade is part of the identity, not a "
                f"modifier on it — an ungraded item and a PSA 10 are different items with "
                f"the same name, and scope is graded items only")
        grader = str(self.grader).strip().upper()
        if grader not in GRADERS:
            raise ValueError(
                f"{self.title}: {self.grader!r} is not a grader this lane recognises "
                f"({', '.join(sorted(GRADERS))}). An unrecognised grader's number cannot "
                f"be matched against anything, so the item is not machine-identifiable")
        object.__setattr__(self, "grader", grader)

    @property
    def key(self) -> str:
        """The matching string. Cert deliberately excluded — see the class docstring."""

        parts = [self.title.strip().lower(), *(q.strip().lower() for q in self.qualifiers),
                 self.grader, str(self.grade).strip()]
        return "|".join(part for part in parts if part)

    def matches(self, other: "ItemKey") -> bool:
        return self.key == other.key

    def describe(self) -> str:
        qualifiers = ", ".join(self.qualifiers)
        return (f"{self.title}"
                + (f" ({qualifiers})" if qualifiers else "")
                + f" — {self.grader} {self.grade}"
                + (f", cert {self.cert}" if self.cert else ""))


# --- what similar items fetched ----------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Comparable:
    """One observed price, and whether anybody actually paid it.

    `kind` is mandatory and has no default. A default of SOLD would let an asking price
    become evidence by omission, which is the single failure this module exists to prevent,
    and a default of ASKING would silently discard real evidence. Whoever retrieved it knows
    which it is and says so.
    """

    key: ItemKey
    price: float
    currency: str
    kind: str
    observed_at: str
    source: str = ""
    url: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {SOLD, ASKING}:
            raise ValueError(
                f"a comparable is {SOLD} or {ASKING}, not {self.kind!r}. A completed sale "
                f"is a transaction that happened; an active listing is somebody's hope, "
                f"and a margin computed against one is fiction")
        if self.price <= 0:
            raise ValueError("a comparable with no price is not a comparable")

    def age_days(self, now: datetime | None = None) -> float | None:
        observed = _parse(self.observed_at)
        return None if observed is None else (
            (now or _now()) - observed).total_seconds() / 86400.0


@dataclass(frozen=True, slots=True)
class Distribution:
    """What comparable items actually fetched — a shape, never a point.

    `n=3 over 90 days` and `n=47 over 14 days` are different facts and this type exists so
    they cannot both render as "sells for 120". Every consumer gets the count, the window
    and the spread whether it wants them or not.
    """

    status: str
    key: str
    prices: tuple[float, ...] = ()
    currency: str = "EUR"
    window_days: int = COMPARABLE_WINDOW_DAYS
    #: Asking prices seen for the same key. Carried for display and REFUSED for sizing —
    #: `REFERENCE_RATE` in the vocabulary of the price-evidence design.
    asking_seen: int = 0
    reason: str = ""

    @property
    def count(self) -> int:
        return len(self.prices)

    @property
    def median(self) -> float | None:
        return statistics.median(self.prices) if self.prices else None

    @property
    def low(self) -> float | None:
        return min(self.prices) if self.prices else None

    @property
    def high(self) -> float | None:
        return max(self.prices) if self.prices else None

    @property
    def spread_pct(self) -> float | None:
        """How wide the observed sales are, as a percentage of the median.

        The number that stops a distribution being read as a price. Two sales at 100 and
        104 and two at 40 and 200 have the same median and are not the same evidence.
        """

        middle = self.median
        if middle is None or middle <= 0 or self.count < 2:
            return None
        return (self.high - self.low) / middle * 100.0

    @property
    def conservative(self) -> float | None:
        """What to size against: the lower quartile, not the median.

        The median is what a typical seller got. Sizing against it assumes this sale will be
        typical, which is a forecast — and the direction to be wrong in is the one that
        refuses a marginal item rather than the one that buys it. With fewer than four
        sales the lowest observed price is used, because a quartile of three numbers is an
        arithmetic exercise rather than a measurement.
        """

        if not self.prices:
            return None
        if self.count < 4:
            return min(self.prices)
        ordered = sorted(self.prices)
        return statistics.quantiles(ordered, n=4)[0]

    def describe(self) -> str:
        if self.status != PRICED:
            return (f"INDETERMINATE  {self.key}\n  {self.reason}\n"
                    f"  This is not a low estimate and it is not a wide range. What this "
                    f"item resells for has not been established.")
        return (
            f"{self.count} sale(s) in {self.window_days} days: "
            f"{self.low:,.2f}–{self.high:,.2f} {self.currency}, median "
            f"{self.median:,.2f}, spread {self.spread_pct or 0:.0f}% of median. "
            f"Sizing against {self.conservative:,.2f}."
            + (f"\n  {self.asking_seen} asking price(s) were also seen and are NOT used: "
               f"nobody paid them." if self.asking_seen else "")
        )


def distribution(
    key: ItemKey,
    comparables: Sequence[Comparable],
    *,
    now: datetime | None = None,
    floor: int = COMPARABLE_FLOOR,
    window_days: int = COMPARABLE_WINDOW_DAYS,
    currency: str = "EUR",
) -> Distribution:
    """Completed sales for exactly this key, inside the window, or INDETERMINATE.

    Four filters and each drops something for a different stated reason: a different item,
    somebody's hope, a different market, and a different currency. What survives is
    evidence; what is left is named in the refusal so a person can see what was discarded
    rather than wondering why the count is low.
    """

    moment = now or _now()
    matching = [c for c in comparables if c.key.matches(key)]
    asking = [c for c in matching if c.kind == ASKING]
    sold = [c for c in matching if c.kind == SOLD]

    # Currency is filtered rather than converted. There is no FX rate in this repository
    # and a rate is itself a price that goes stale, so a converted comparable would be a
    # guess wearing a number — the same argument lib/reaping makes about the stocks lane.
    wrong_currency = [c for c in sold if c.currency != currency]
    sold = [c for c in sold if c.currency == currency]

    recent, stale = [], []
    for comparable in sold:
        age = comparable.age_days(moment)
        (recent if age is not None and age <= window_days else stale).append(comparable)

    if len(recent) < floor:
        discarded = []
        if asking:
            discarded.append(f"{len(asking)} asking price(s), which nobody paid")
        if stale:
            discarded.append(
                f"{len(stale)} sale(s) older than {window_days} days — cards bubbled "
                f"through 2020-22 and corrected, so an older sale is a different market "
                f"rather than an old data point")
        if wrong_currency:
            discarded.append(
                f"{len(wrong_currency)} sale(s) in another currency, not converted "
                f"because there is no rate here that is not itself a stale price")
        return Distribution(
            INDETERMINATE, key.key, currency=currency, window_days=window_days,
            asking_seen=len(asking),
            reason=(f"{len(recent)} completed sale(s) matching grade AND grader within "
                    f"{window_days} days, against a floor of {floor}."
                    + (f" Discarded: {'; '.join(discarded)}." if discarded else "")))

    return Distribution(PRICED, key.key, tuple(c.price for c in recent), currency,
                        window_days, len(asking))


# --- what the round trip costs ------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FeeSchedule:
    """What a sale actually costs, from the account rather than from a help page.

    Every figure is the operator's and lives in config, because they change and because
    reading them off a published card rather than the account is how a margin becomes
    fiction. `connectors/chain_costs.py` is the precedent: the round trip is costed before
    the opportunity is called one.

    The returns rate is here and is the one people leave out. A 3% returns rate on an item
    is not a 3% haircut — a returned item costs the postage both ways and usually cannot be
    relisted at the same price, so it is charged as a proportion of the whole round trip.
    """

    #: Percentage of the total the platform takes, INCLUDING the postage the buyer paid,
    #: which is how eBay charges and is the half people forget.
    commission_pct: float
    #: The per-order fixed fee. Small, and it is half the reason a 40 EUR item cannot work.
    fixed_fee: float
    #: Payment processing, where the platform charges it separately.
    processing_pct: float = 0.0
    #: What it costs to send the item, by weight band. The other half of the 40 EUR problem.
    postage: float = 0.0
    #: What the buyer pays towards postage. Counted as revenue AND as commissionable, since
    #: the platform takes its cut of it.
    postage_charged: float = 0.0
    #: Proportion of sales that come back. Applied to the whole round trip, not to the fee.
    returns_rate_pct: float = 0.0
    currency: str = "EUR"

    def __post_init__(self) -> None:
        for name in ("commission_pct", "fixed_fee", "processing_pct", "postage",
                     "postage_charged", "returns_rate_pct"):
            if float(getattr(self, name)) < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.commission_pct <= 0:
            raise ValueError(
                "a commission of nought is not a fee schedule anybody read off an "
                "account. Every threshold in this lane moves with the real rate, so an "
                "unset one must refuse rather than flatter every margin")


@dataclass(frozen=True, slots=True)
class RoundTrip:
    """Buy, sell, fees, and what is actually left. Every line stated.

    A single net figure with the fees folded in is the shape that lets somebody sanity-check
    a wrong number and fail to. The lines are here so a margin can be argued with.
    """

    buy: float
    sell: float
    currency: str
    commission: float
    fixed_fee: float
    processing: float
    postage: float
    postage_income: float
    returns_cost: float

    @property
    def fees(self) -> float:
        return (self.commission + self.fixed_fee + self.processing + self.postage
                + self.returns_cost)

    @property
    def net_profit(self) -> float:
        return self.sell + self.postage_income - self.buy - self.fees

    @property
    def net_margin_pct(self) -> float:
        """Net profit as a percentage of what was laid out. Zero on a zero outlay.

        Against the BUY rather than against the sale price, because the buy is the money at
        risk and the thing being decided is whether to commit it.
        """

        return 0.0 if self.buy <= 0 else self.net_profit / self.buy * 100.0

    def describe(self) -> str:
        return "\n".join([
            f"  buy                {self.buy:>10,.2f} {self.currency}",
            f"  sells for          {self.sell:>10,.2f}  (the conservative comparable)",
            f"  postage charged    {self.postage_income:>10,.2f}",
            f"  commission        -{self.commission:>10,.2f}",
            f"  fixed fee         -{self.fixed_fee:>10,.2f}",
            f"  processing        -{self.processing:>10,.2f}",
            f"  postage           -{self.postage:>10,.2f}",
            f"  returns allowance -{self.returns_cost:>10,.2f}",
            f"  NET                {self.net_profit:>10,.2f}  "
            f"({self.net_margin_pct:+.1f}% on the buy)",
        ])


def round_trip(buy: float, sell: float, fees: FeeSchedule) -> RoundTrip:
    """The arithmetic, in the order it actually happens. Fees before margin, always."""

    revenue = sell + fees.postage_charged
    commission = revenue * fees.commission_pct / 100.0
    processing = revenue * fees.processing_pct / 100.0
    # Charged on the whole round trip rather than on the fee: a returned item costs the
    # postage both ways and usually cannot be relisted at the same price.
    exposure = buy + commission + fees.fixed_fee + processing + fees.postage
    returns_cost = exposure * fees.returns_rate_pct / 100.0
    return RoundTrip(buy, sell, fees.currency, commission, fees.fixed_fee, processing,
                     fees.postage, fees.postage_charged, returns_cost)


def break_even_sell(buy: float, fees: FeeSchedule) -> float:
    """What an item must fetch to get the money back. The number that sets the floor.

    Solved rather than searched: revenue r must satisfy
    `r - r*(c+p)/100 - fixed - postage - returns = buy`, with returns proportional to the
    outlay. A 40 EUR item needing a 32% markup merely to break even is what inverted the
    original tiering, and this is the function that says so.
    """

    rate = (fees.commission_pct + fees.processing_pct) / 100.0
    returns = fees.returns_rate_pct / 100.0
    # exposure = buy + commission + fixed + processing + postage; returns_cost = exposure*r
    # net = revenue - buy - commission - fixed - processing - postage - returns_cost = 0
    numerator = (buy + fees.fixed_fee + fees.postage) * (1.0 + returns)
    denominator = 1.0 - rate * (1.0 + returns)
    if denominator <= 0:
        # Fees at or above 100% of revenue. Not a number to return; a schedule to question.
        return float("inf")
    return numerator / denominator - fees.postage_charged


# --- what to do about it -------------------------------------------------------------------

def tier(net_margin_pct: float, *, urgent_pct: float = URGENT_NET_PCT,
         routine_pct: float = ROUTINE_NET_PCT) -> str:
    """URGENT, ROUTINE or NOT_WORTH_IT, from the margin NET of every fee.

    A property of the opportunity rather than a notification setting, so the same item
    carries the same urgency wherever it is read. The thresholds are set to keep URGENT
    rare by construction: if routine finds arrive often they are read as noise, and the day
    an urgent one arrives it is skimmed with them.
    """

    if net_margin_pct >= urgent_pct:
        return URGENT
    if net_margin_pct >= routine_pct:
        return ROUTINE
    return NOT_WORTH_IT


@dataclass(frozen=True, slots=True)
class Holding:
    """One item bought and not yet sold, and whether it still counts at cost."""

    key: str
    bought_at: str
    cost: float
    currency: str = "EUR"
    sold_at: str = ""

    @property
    def is_open(self) -> bool:
        return not self.sold_at

    def days_held(self, now: datetime | None = None) -> float | None:
        bought = _parse(self.bought_at)
        return None if bought is None else (
            (now or _now()) - bought).total_seconds() / 86400.0

    def written_down(self, now: datetime | None = None,
                     horizon: int = WRITE_DOWN_DAYS) -> bool:
        """Past the horizon and unsold. Not a valuation judgement dressed up as one.

        An item nobody bid on for fifty days is not worth what was paid for it, and
        carrying it at cost overstates the book — which matters here more than it looks,
        because `docs/levelling-design.md` promotes on the PESSIMISTIC book and a lane with
        slow stock would otherwise sit at level one permanently.
        """

        if not self.is_open:
            return False
        held = self.days_held(now)
        # Unreadable purchase date counts as written down. The direction that understates
        # the book is the one to be wrong in.
        return True if held is None else held > horizon


@dataclass(frozen=True, slots=True)
class Capacity:
    """How many items are on the shelf against how many fit there.

    A risk control for stocks; a physical fact here. It is usually tighter than the
    ring-fence — twenty items at the 75 floor is 1,500 and at 200 each is 4,000 — and a
    lane that ignored it would suggest a twenty-first item while twenty sat unlisted in a
    hallway.
    """

    held: int
    limit: int = CAPACITY
    written_down: int = 0

    @property
    def full(self) -> bool:
        return self.held >= self.limit

    @property
    def free(self) -> int:
        return max(0, self.limit - self.held)

    def describe(self) -> str:
        note = (f", {self.written_down} of them past the {WRITE_DOWN_DAYS}-day horizon and "
                f"no longer counted at cost" if self.written_down else "")
        if self.full:
            return (f"AT_CAPACITY: {self.held} of {self.limit} items held{note}. This is "
                    f"not a finding that there is nothing to buy — it is a shelf that is "
                    f"full, and the next thing to do is sell something.")
        return f"{self.held} of {self.limit} items held{note}; room for {self.free}."


def capacity_from(holdings: Sequence[Holding], *, limit: int = CAPACITY,
                  horizon: int = WRITE_DOWN_DAYS,
                  now: datetime | None = None) -> Capacity:
    """Open items still counted, with the written-down ones excluded and counted separately.

    A written-down item is still physically in the hallway, so it is NOT freed from the
    shelf — the write-down is about what the book says it is worth, not about where it is.
    Reporting it both ways is the honest reading and it is why the count and the note are
    separate fields.
    """

    open_items = [h for h in holdings if h.is_open]
    stale = [h for h in open_items if h.written_down(now, horizon)]
    return Capacity(len(open_items), limit, len(stale))


def book_value(holdings: Sequence[Holding], *, horizon: int = WRITE_DOWN_DAYS,
               now: datetime | None = None) -> tuple[float, float]:
    """`(carried_at_cost, written_off)` across the open items.

    Two numbers rather than one net figure, because "the book is 900" and "the book is
    1,400 of which 500 is stock nobody has bid on since June" are different facts about the
    same hallway.
    """

    carried = sum(h.cost for h in holdings
                  if h.is_open and not h.written_down(now, horizon))
    written = sum(h.cost for h in holdings
                  if h.is_open and h.written_down(now, horizon))
    return carried, written
