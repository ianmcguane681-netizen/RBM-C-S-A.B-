"""The mispricing lane: a forecast, a price, and every reason the two might not disagree.

`lib/reaper.py` holds the sequence and knows nothing about football. This supplies the five
callables and nothing else, so what is worth reading here is what each stage refuses.

    look     fixtures and standings from football-data, prices from the odds feed,
             conditions from open-meteo, team news from whatever a person typed in
    screen   the cascade: was a forecast produced, was the book de-vigged, is the
             market complete, are the prices current, does the edge survive the doubt
    gates    what no cascade stage can establish from a price — has the event started,
             is the model still in date, what was assumed rather than known
    thesis   minted per fixture from the model a person declared, carrying the caveat
    size     fractional Kelly, floored by the ring-fence, and REFUSED outright while
             the model is PAPER

## Why the ceiling is REFUSED rather than READY, and will be for a while

A model that has never been checked against outcomes is `PAPER`. It runs, it produces a
complete evaluation, and `size` refuses it with the numbers in the refusal — a MEASURED
refusal in the sense `lib.reaper.Unworthy` means, not an INDETERMINATE. That is the whole
point: the lane's output while it is paper is a record of what it would have done, and the
record is what a person eventually reads before promoting the model.

Nothing here can promote it. `MispricingModel(status="LIVE")` refuses construction without
a written account of what was seen, and the model is declared in the config by a named
person exactly as the arb lane's standing authority is.

## This lane is a bet and the arb lane is not

Worth saying once in each file. An arb says two prices cannot both be right and needs no
view about the fixture. This says one price is wrong, which is a forecast, and if the
forecast is wrong the whole stake goes. So the harvest never uses the arb lane's vocabulary
— there is no lock, no guaranteed return, and the word "edge" always appears next to the
band of doubt it had to clear.

## The odds allowance, which is the real constraint on the cadence

This lane and the arb lane buy the same h2h prices from the same key. The free tier is 500
requests a month and the arb lane at eight hours across two sports already spends about six
credits a day. A mispricing lane on the same cadence would double that for prices that
answer a slower question — a fair-value model does not change between breakfast and lunch,
and a fixture list changes once a day. So the cadence is a day, `preflight` prints what
both lanes spend together, and this is stated here because the failure it prevents is the
one this repository fears most: an exhausted key reports no opportunity, which is
indistinguishable from a quiet market for the rest of the month.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from lib.candidates import INDETERMINATE, PASSED, REFUSED, Candidate, Stage
from lib.mispricing import (
    FAIR,
    LIVE,
    MISPRICED,
    METHOD_DEPENDENT,
    PRICED,
    Edge,
    Evidence,
    FairBook,
    Forecast,
    GoalsModel,
    MispricingModel,
    devig,
    find_edge,
)
from lib.reaper import Reaper, Unworthy
from lib.sizing import NOT_MEASURED, SIZED, Constraint, size_position
from lib.thesis import Thesis

#: How old a price may be and still be the price being bet into. Far longer than the arb
#: lane's three minutes, and deliberately: an arb is a relationship between two quotes that
#: must exist at the same instant, and this is one quote against a model that did not change
#: in the last hour. What it still refuses is a price from yesterday.
FRESHNESS_SECONDS = 3600

#: The fraction of full Kelly to stake. Full Kelly is optimal only if the probability is
#: right, and the whole argument of `lib/mispricing.py` is that this one is uncertain — so
#: a quarter, which is the conventional discount for exactly that and still assumes more
#: about the model than it has earned. It is a floor on prudence, not a target.
KELLY_FRACTION = 0.25

#: Below this the bet is not worth the trip to the shop, and more importantly a stake this
#: small is a rounding artefact of the Kelly arithmetic rather than a position.
MINIMUM_STAKE = 2.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class Reading:
    """One precondition a price cannot establish, and whether it stops the lane.

    `blocking` is stated rather than sniffed from the status name, for the reason
    `lib.reaper.gate_findings` gives: whether a gate halts a lane must not depend on how
    somebody spelled a constant.
    """

    status: str
    detail: str
    blocking: bool = True

    def describe(self) -> str:
        return f"{self.status}: {self.detail}"


@dataclass(frozen=True, slots=True)
class Opportunity:
    """One fixture, worked all the way through, carried between the reaper's stages.

    Assembled in `look` rather than recomputed per stage. The screen, the gates and the
    sizer must all be talking about the same forecast and the same de-vig: a stage that
    recomputed would be screening one number and sizing another, which is the failure
    `lib.arb_reaper.chosen_quotes` exists to prevent one lane along.
    """

    #: The fixture, as the odds feed names it. Called `fixture` rather than `market` on
    #: purpose: `lib.reaper._work` names a harvest from a subject's `.market` if it has one
    #: and falls back to `.subject`, so a field called `market` here would name every
    #: harvest after the fixture — three selections at two books would produce six harvests
    #: with one name — AND would then disagree with the thesis minted for `.subject`, which
    #: `lib.thesis.evaluate` refuses as a thesis naming something else.
    fixture: str
    kickoff: str
    book: str
    selection: str
    decimal_odds: float
    observed_at: str
    evidence: Evidence
    forecast: Forecast
    fair: FairBook
    edge: Edge
    #: Every selection the book quoted, so "complete market" is answerable.
    quoted: tuple[str, ...] = ()
    expected: tuple[str, ...] = ()
    #: What the book will actually take, when a source knew. Negative means nobody read it.
    available_stake: float = NOT_MEASURED

    @property
    def subject(self) -> str:
        return f"{self.fixture} / {self.selection} @ {self.book}"


# --- the cascade ---------------------------------------------------------------------

def screen_opportunity(
    opportunity: Opportunity,
    *,
    model: MispricingModel,
    now: datetime | None = None,
    freshness_seconds: int = FRESHNESS_SECONDS,
) -> Candidate:
    """Ordered cheapest and most fatal first, per `lib/candidates.py`.

    The forecast leads, because everything after it is arithmetic on a number that either
    exists or does not — and a market screened on freshness and completeness before anybody
    asked whether the model could price it is a market whose refusal names the wrong thing.
    """

    moment = now or _now()
    stages: list[Stage] = []

    if opportunity.forecast.status != PRICED:
        stages.append(Stage(
            "the model produced a forecast", INDETERMINATE, disqualifying=True,
            detail=(f"{opportunity.forecast.reason} Missing: "
                    f"{', '.join(opportunity.forecast.missing) or 'nothing named'}."),
        ))
    else:
        stages.append(Stage(
            "the model produced a forecast", PASSED, disqualifying=True,
            detail=(f"every required feature was known; "
                    f"{len(opportunity.forecast.assumptions)} assumption(s) recorded"),
        ))

    if opportunity.fair.status != PRICED:
        stages.append(Stage(
            "the book's margin was removed", INDETERMINATE, disqualifying=True,
            detail=opportunity.fair.reason,
        ))
    else:
        stages.append(Stage(
            "the book's margin was removed", PASSED, disqualifying=True,
            detail=(f"{opportunity.fair.method} de-vig on an overround of "
                    f"{opportunity.fair.overround_pct:+.2f}%"),
        ))

    missing = set(opportunity.expected) - set(opportunity.quoted)
    if missing:
        stages.append(Stage(
            "the book quoted the whole market", REFUSED, disqualifying=True,
            detail=(f"{opportunity.book} did not quote {', '.join(sorted(missing))}. A "
                    f"margin cannot be removed from a market with a side missing, so the "
                    f"fair price of the sides that ARE quoted is unknown rather than "
                    f"slightly off."),
        ))
    else:
        stages.append(Stage(
            "the book quoted the whole market", PASSED, disqualifying=True,
            detail=f"{len(opportunity.quoted)} selection(s) quoted at {opportunity.book}",
        ))

    stages.append(_freshness(opportunity, moment, freshness_seconds))
    stages.append(_edge_stage(opportunity, model))
    return Candidate(opportunity.subject, tuple(stages))


def _freshness(opportunity: Opportunity, moment: datetime, window: int) -> Stage:
    observed = _parse(opportunity.observed_at)
    if observed is None:
        return Stage(
            "the price is current", INDETERMINATE, disqualifying=True,
            detail=("the quote carries no readable observation time, so how long ago this "
                    "was the price is unknown — which is not the same as recent."),
        )
    age = (moment - observed).total_seconds()
    if age > window:
        return Stage(
            "the price is current", REFUSED, disqualifying=True,
            detail=(f"the quote is {age / 60:.0f} minutes old against a "
                    f"{window / 60:.0f}-minute window. A model's disagreement with a price "
                    f"that is gone is a disagreement with nobody."),
        )
    return Stage("the price is current", PASSED, disqualifying=True,
                 detail=f"quoted {age / 60:.0f} minute(s) ago")


def _edge_stage(opportunity: Opportunity, model: MispricingModel) -> Stage:
    """Whether the disagreement is bigger than the two ways it could be an artefact.

    A REFUSAL here is the ordinary case and the healthy one. Most prices are close to right,
    and a lane reporting a mispricing on every fixture would be reporting the properties of
    its own model rather than of the market.
    """

    edge = opportunity.edge
    if edge.status == MISPRICED:
        return Stage(
            "the edge survives the doubt", PASSED, disqualifying=True,
            detail=(f"{edge.expected_value_pct:+.2f}% expected against a doubt band of "
                    f"{edge.doubt_band_pct:.2f}% ({edge.method_sensitivity_points:.2f} "
                    f"points of de-vig spread, {edge.stated_error_points:.2f} points of "
                    f"stated model error, at {edge.net_odds:.2f} net odds)"),
        )
    if edge.status == METHOD_DEPENDENT:
        return Stage(
            "the edge survives the doubt", REFUSED, disqualifying=True,
            detail=(f"{edge.expected_value_pct:+.2f}% expected, and the choice of de-vig "
                    f"method alone moves the fair probability by "
                    f"{edge.method_sensitivity_points:.2f} points. Another method would "
                    f"not have found this, so it is an artefact of the arithmetic rather "
                    f"than a disagreement with {opportunity.book}."),
        )
    if edge.status == FAIR:
        return Stage(
            "the edge survives the doubt", REFUSED, disqualifying=True,
            detail=(f"{edge.expected_value_pct:+.2f}% expected, inside the doubt band of "
                    f"{edge.doubt_band_pct:.2f}%. Not a small edge — no edge this model is "
                    f"entitled to claim."),
        )
    return Stage("the edge survives the doubt", INDETERMINATE, disqualifying=True,
                 detail=edge.reason or "the comparison could not be made")


# --- the gates -----------------------------------------------------------------------

def gates_for(
    opportunity: Opportunity,
    *,
    model: MispricingModel,
    now: datetime | None = None,
) -> tuple[Reading, ...]:
    """What a price cannot establish. Short on purpose; every entry is a precondition.

    The assumptions the forecast carried are reported here as NON-blocking. That is a
    deliberate choice and the switch that makes it a real one is `model.requires`: a person
    who thinks team news is a precondition puts `home_key_absences` in that tuple and the
    forecast becomes UNPRICED without it. Making it blocking here as well would take that
    decision away from the person whose name is on the model, and would also stop this lane
    ever producing anything — there is no free structured team-news source, so the
    assumption is present on essentially every fixture.
    """

    moment = now or _now()
    readings: list[Reading] = []

    if model.is_expired(moment):
        readings.append(Reading("MODEL_EXPIRED", (
            f"{model.name} expired at {model.expires_at}. A forecasting method is a claim "
            f"about a period; past it nobody has said it still holds.")))

    kickoff = _parse(opportunity.kickoff)
    if kickoff is None:
        readings.append(Reading("EVENT_START_UNKNOWN", (
            f"{opportunity.fixture!r} carries no readable start time. Not a finding that "
            f"the fixture is upcoming — a price on a market already in play, or settled, "
            f"is not a price you can take.")))
    elif kickoff <= moment:
        readings.append(Reading("EVENT_ALREADY_STARTED", (
            f"kick-off was {kickoff.isoformat(timespec='seconds')}, which is in the past")))

    for assumption in opportunity.forecast.assumptions:
        readings.append(Reading("FORECAST_ASSUMPTION", assumption, blocking=False))

    if opportunity.available_stake == NOT_MEASURED:
        readings.append(Reading("BOOK_LIMIT_UNREAD", (
            "no source read what this book will actually accept at this price. Reported "
            "and not blocking: a single bet that is only partly accepted is a smaller bet, "
            "where a partly-accepted arb leg is an unhedged position. The stake below is "
            "what to ask for, not what will be taken."), blocking=False))

    return tuple(readings)


# --- sizing --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ValueTicket:
    """One bet to place by hand, with the reason it is being placed printed on it.

    Every figure a person needs at the counter, and the ones they need afterwards: what the
    model thought, what the book thought, and the band the edge had to clear. A ticket that
    printed only a stake and a price would be indistinguishable from a hunch a week later,
    when the question is whether the model was right rather than whether the bet won.
    """

    market: str
    book: str
    selection: str
    decimal_odds: float
    stake: float
    currency: str
    model_probability: float
    book_probability: float
    expected_value_pct: float
    doubt_band_pct: float
    kelly_fraction: float
    bound_by: str
    assumptions: tuple[str, ...] = ()
    note: str = ""

    @property
    def to_return(self) -> float:
        return self.stake * self.decimal_odds

    def describe(self) -> str:
        lines = [
            f"PLACE BY HAND — {self.stake:,.2f} {self.currency} on {self.selection} "
            f"at {self.decimal_odds:.2f} with {self.book}",
            f"  {self.market}",
            f"  returns {self.to_return:,.2f} {self.currency} if it wins, and nothing if "
            f"it does not. THIS IS A BET, NOT A LOCK.",
            f"  model {self.model_probability * 100:.2f}% vs book "
            f"{self.book_probability * 100:.2f}% de-vigged  ->  "
            f"{self.expected_value_pct:+.2f}% expected, against a doubt band of "
            f"{self.doubt_band_pct:.2f}%",
            f"  staked at {self.kelly_fraction:.2f} of full Kelly; bound by "
            f"{self.bound_by}",
        ]
        for assumption in self.assumptions:
            lines.append(f"  ASSUMED: {assumption}")
        if self.note:
            lines.append(f"  {self.note}")
        return "\n".join(lines)


def kelly_stake(probability: float, decimal_odds: float, bankroll: float,
                fraction: float = KELLY_FRACTION) -> float:
    """The fractional-Kelly stake, or zero when the bet has no edge at these odds.

    b is the net return per unit staked. Full Kelly maximises long-run growth ONLY if the
    probability is right, and the whole argument of `lib/mispricing.py` is that this one is
    uncertain — so the fraction is a discount for being wrong about p, not a preference.

    Zero rather than negative. A negative Kelly is an instruction to back the other side,
    which is a different bet at a different price that nobody has evaluated.
    """

    b = decimal_odds - 1.0
    if b <= 0 or bankroll <= 0:
        return 0.0
    full = (probability * b - (1.0 - probability)) / b
    return max(0.0, full) * fraction * bankroll


def size_opportunity(
    opportunity: Opportunity,
    *,
    model: MispricingModel,
    bankroll: float,
    kelly_fraction: float = KELLY_FRACTION,
    minimum_stake: float = MINIMUM_STAKE,
):
    """A ticket, or a stated refusal. Never a ticket that should not be placed.

    The PAPER refusal comes first and is deliberately a MEASURED one — `Unworthy`, which
    the reaper reports as REFUSED with this reason, rather than INDETERMINATE. "I worked it
    out and the model is not allowed to bet yet" and "I could not work out a size" are
    different facts, and the first is the entire output of this lane until somebody has
    read enough of it to promote the model.
    """

    edge = opportunity.edge
    if edge.status != MISPRICED or edge.model_probability is None:
        return Unworthy(
            f"the edge did not survive the doubt ({edge.status}): "
            f"{edge.expected_value_pct:+.2f}% expected against a band of "
            f"{edge.doubt_band_pct:.2f}%")

    if model.status != LIVE:
        return Unworthy(
            f"{model.name} is {model.status}. It would have staked on {edge.selection} at "
            f"{edge.decimal_odds:.2f} with {edge.book} — model "
            f"{edge.model_probability * 100:.2f}% against a de-vigged "
            f"{(edge.book_probability or 0) * 100:.2f}%, {edge.expected_value_pct:+.2f}% "
            f"expected. Recorded and not placed: a model with no settled record has not "
            f"been shown to be right about anything, and only a named person moves it to "
            f"{LIVE}.")

    stake = kelly_stake(edge.model_probability, edge.decimal_odds, bankroll,
                        kelly_fraction)
    constraints = [
        Constraint(f"{kelly_fraction:.2f} Kelly", stake,
                   f"on a bankroll of {bankroll:,.2f} at "
                   f"{edge.model_probability * 100:.2f}%"),
        Constraint("the model's stated exposure limit", model.max_exposure,
                   f"declared by {model.declared_by}"),
    ]
    # The book's own limit is NOT a constraint here, and that differs from the arb lane on
    # purpose. An arb leg that is only partly accepted leaves the other leg unhedged, so an
    # unread limit there is a real unmeasured constraint. A single bet only partly accepted
    # is a smaller bet. It is printed on the ticket as a note instead.
    sized = size_position(opportunity.subject, constraints, currency=model.currency)

    if sized.status != SIZED:
        return Unworthy(f"no stake could be set: {sized.describe().splitlines()[0]}")
    if sized.amount < minimum_stake:
        return Unworthy(
            f"the permitted stake is {sized.amount:,.2f} {model.currency}, under the "
            f"{minimum_stake:,.2f} minimum. At this size the Kelly arithmetic is rounding "
            f"rather than a position")

    note = ""
    if opportunity.available_stake == NOT_MEASURED:
        note = ("Nobody read what this book will accept at this price. Ask for the stake "
                "above; a smaller acceptance is a smaller bet, not a broken position.")
    elif opportunity.available_stake < sized.amount:
        note = (f"the source saw only {opportunity.available_stake:,.2f} available at this "
                f"price")

    return ValueTicket(
        market=opportunity.fixture, book=edge.book, selection=edge.selection,
        decimal_odds=edge.decimal_odds, stake=sized.amount, currency=model.currency,
        model_probability=edge.model_probability,
        book_probability=edge.book_probability or 0.0,
        expected_value_pct=edge.expected_value_pct,
        doubt_band_pct=edge.doubt_band_pct,
        kelly_fraction=kelly_fraction, bound_by=sized.bound_by,
        assumptions=edge.assumptions, note=note,
    )


def measure_ticket(ticket: ValueTicket) -> tuple[float, float]:
    """What the breakers check: how much is going on, and the edge being claimed."""

    return (float(ticket.stake), float(ticket.expected_value_pct))


# --- the thesis ----------------------------------------------------------------------

#: Named on every minted thesis. Unlike the arb lane's caveat, this one cannot say the
#: position makes no claim about the fixture — it makes exactly that claim, which is why
#: the caveat has to be blunter.
FORECAST_CAVEAT = (
    "this authorisation was minted from a declared forecasting model: nobody looked at "
    "this particular fixture before authorising it, and unlike an arbitrage the position "
    "DOES rest on a claim about how the fixture will go. If the model is wrong about it "
    "the whole stake is lost"
)


def thesis_from(model: MispricingModel, subject: str) -> Thesis:
    return Thesis(
        subject=subject,
        declared_by=model.declared_by,
        reasoning=model.reasoning,
        considered=(f"the model states its own error at {model.stated_error_pct:.2f} "
                    f"probability points",
                    f"the book's margin is removed by {model.devig_method}",
                    FORECAST_CAVEAT),
        declared_at=model.declared_at or _now().isoformat(timespec="seconds"),
        expires_at=model.expires_at,
        max_exposure=model.max_exposure,
        currency=model.currency,
    )


# --- assembly ------------------------------------------------------------------------

def mispricing_identity(opportunity: Opportunity) -> str:
    """The fixture, the book and the selection. Never the price and never the edge.

    Same argument as `lib.seen.arb_identity`: including the odds would make every tick a
    new sighting and the register would dedupe nothing while appearing to work. Including
    the edge would be worse — the edge moves with the model as well as with the price.
    """

    return (f"{opportunity.fixture.strip()}|{opportunity.book}|"
            f"{opportunity.selection}")


@dataclass
class EvidenceSources:
    """Where each feature comes from, so `look` can be tested without a network.

    Every one is optional and every absence is a feature that reports UNKNOWN rather than a
    call that fails. A lane assembled with none of these still runs and still says, per
    fixture, exactly what it could not see.
    """

    #: -> lib.mispricing.Evidence for one fixture. Supplied whole by the caller, because
    #: how evidence is gathered differs per sport and this file must not know.
    evidence_for: Callable[[str, str, str, str], Evidence] | None = None
    #: -> the quotes for a sport, as `lib.arbfind.Quote`.
    quotes_for: Callable[[str], Sequence[Any]] | None = None
    model: Any = field(default_factory=GoalsModel)


def opportunities_from(
    quotes: Sequence[Any],
    *,
    model: MispricingModel,
    goals_model: Any,
    evidence_for: Callable[[str], Evidence],
    now: datetime | None = None,
) -> list[Opportunity]:
    """Turn a run of quotes into one opportunity per (market, book, selection).

    One per selection rather than one per market, because a book can be long on the draw
    and short on the favourite in the same three-way market, and a market-level record
    would have to pick one — which is the same collapsing this repository refuses
    everywhere else.
    """

    by_market: dict[str, list[Any]] = {}
    for quote in quotes:
        by_market.setdefault(quote.market, []).append(quote)

    out: list[Opportunity] = []
    for market, market_quotes in sorted(by_market.items()):
        expected = tuple(sorted({q.selection for q in market_quotes}))
        evidence = evidence_for(market)
        forecast = goals_model.forecast(model, evidence)

        by_book: dict[str, list[Any]] = {}
        for quote in market_quotes:
            by_book.setdefault(quote.book, []).append(quote)

        for book, book_quotes in sorted(by_book.items()):
            odds = {q.selection: q.decimal_odds for q in book_quotes}
            fair = devig(odds, method=model.devig_method) if len(odds) >= 2 else FairBook(
                "UNPRICED", model.devig_method,
                reason=f"{book} quoted {len(odds)} selection(s); a margin cannot be "
                       f"removed from a market with no other side")
            for quote in sorted(book_quotes, key=lambda q: q.selection):
                edge = find_edge(
                    model=model, forecast=forecast, fair=fair,
                    selection=quote.selection, book=book,
                    decimal_odds=quote.decimal_odds,
                    commission_pct=getattr(quote, "commission_pct", 0.0) or 0.0,
                    subject=market)
                out.append(Opportunity(
                    fixture=market, kickoff=_kickoff_from(market, evidence), book=book,
                    selection=quote.selection, decimal_odds=quote.decimal_odds,
                    observed_at=quote.observed_at, evidence=evidence, forecast=forecast,
                    fair=fair, edge=edge, quoted=tuple(sorted(odds)), expected=expected,
                    available_stake=float(getattr(quote, "available_stake", NOT_MEASURED)),
                ))
    return out


def _kickoff_from(market: str, evidence: Evidence) -> str:
    """The fixture's start time, from the evidence bundle or from the market's own name.

    The odds feed names a market `Home v Away @ <iso>`; an exchange market id carries no
    time at all. Empty rather than a guess, and the gate that consumes it treats empty as
    blocking — which is the answer that stops a bet going on a match already in play.
    """

    if evidence.kickoff:
        return evidence.kickoff
    _, separator, tail = str(market).rpartition(" @ ")
    return tail if separator else ""


def build_mispricing_reaper(
    *,
    model: MispricingModel,
    breakers: Any,
    bankroll: float,
    sports: Sequence[str] = (),
    bookmakers: Sequence[str] = (),
    source: Any = None,
    goals_model: Any = None,
    evidence_for: Callable[[str], Evidence] | None = None,
    register: Any = None,
    now: Callable[[], datetime] = _now,
    freshness_seconds: int = FRESHNESS_SECONDS,
    kelly_fraction: float = KELLY_FRACTION,
    minimum_stake: float = MINIMUM_STAKE,
) -> Reaper:
    """The mispricing lane as a `Reaper`. Nothing here places a bet, and nothing can.

    `evidence_for` is required in practice and optional in the signature, because a lane
    with none still has something honest to do: it produces an empty `Evidence` per fixture,
    every forecast comes back UNPRICED naming the required features, and the harvest says
    which ones. That is a more useful first run than a refusal at assembly time, and it is
    exactly what an operator sees before they have a football-data key.
    """

    engine = goals_model if goals_model is not None else GoalsModel()

    def evidence(market: str) -> Evidence:
        if evidence_for is None:
            return Evidence(market)
        return evidence_for(market)

    def look():
        from connectors.oddsapi import H2H, OddsApiSource

        feed = (source if source is not None
                else OddsApiSource.from_directory(bookmakers=bookmakers))
        if not getattr(feed, "is_configured", False):
            # Raising is correct: COULD_NOT_LOOK. An empty scan reported as "no mispricing"
            # is the confusion the reaper's status set exists to prevent.
            raise RuntimeError(
                "no odds source is configured, so no price was compared against anything. "
                "This is not a finding that every price is fair.")

        asked, answered, quotes = len(sports), 0, []
        for sport in sports:
            try:
                got = feed.quotes(sport, market=H2H)
            except Exception:  # noqa: BLE001 - one silent sport is not a silent scan
                continue
            answered += 1
            quotes.extend(got)

        if not answered:
            raise RuntimeError(
                f"all {asked} sport(s) failed to answer; nothing was compared")

        found = opportunities_from(quotes, model=model, goals_model=engine,
                                   evidence_for=evidence, now=now())
        # Only the ones the model actually disagrees with are carried forward. The rest are
        # not hidden — `NOTHING_FOUND` with the source count is the honest report of a
        # market that was priced correctly, which is the normal state of a market.
        return [o for o in found if o.edge.status == MISPRICED], asked, answered

    return Reaper(
        name="mispricing", lane="mispricing",
        look=look,
        screen=lambda o: screen_opportunity(
            o, model=model, now=now(), freshness_seconds=freshness_seconds),
        gates=lambda o: gates_for(o, model=model, now=now()),
        # Minted for `o.subject`, which is exactly the string `lib.reaper` will name the
        # harvest with. A thesis for the fixture while the harvest names the selection is
        # REFUSED by `lib.thesis.evaluate` as "the thesis on file names something else" —
        # a refusal that looks like a permissions problem and is a naming one.
        thesis_for=lambda o: thesis_from(model, o.subject),
        size=lambda o, _permission: size_opportunity(
            o, model=model, bankroll=bankroll, kelly_fraction=kelly_fraction,
            minimum_stake=minimum_stake),
        breakers=breakers,
        measure=measure_ticket,
        register=register,
        identity=mispricing_identity,
    )
