"""The arb lane, worked from a feed to a slip a person can execute, or a stated refusal.

`lib/reaper.py` holds the sequence and knows nothing about odds. This supplies the five
callables for the arb lane and nothing else, so the interesting content is in what each
stage refuses.

    look     every configured sport, once, through the aggregator
    screen   the cascade in lib/candidates.py, ordered most-fatal-first
    gates    the preconditions no cascade stage can establish from a price feed
    thesis   minted per market from a standing grant a person signed once
    size     lib/betslip.build_slip, on the diversified combination where one exists

## Why this lane's ceiling is INDETERMINATE until a person does something

An odds feed returns odds. It does not return each book's settlement rules, and the only
real position this board has ever examined had a positive margin net of commission and was
refused because one leg voided on abandonment while the other stood. No amount of
engineering reads that off an API.

So `settlement equivalence` is the first cascade stage, it is disqualifying, and it is
INDETERMINATE — not PASSED — until an `EquivalenceDeclaration` exists naming the books.
That declaration is a one-time human act per pair of books and market type, not a per-bet
one: somebody reads bet365's and Sky Bet's rules for football win/draw/win once, records
who decided and why, and the lane runs from then on. `lib/arb.EquivalenceDeclaration`
refuses an automation author, so this cannot be self-served.

Until that exists the lane still runs, still finds candidates, and reports each one as
INDETERMINATE naming the exact declaration missing. That is the useful output: it tells you
which two books are worth an evening with their rules pages.

## The standing thesis, and what it costs

`lib/thesis.Thesis` requires a named human and a subject. Nobody writes a thesis per
football match at nine in the morning, so `StandingAuthority` carries the human's reasoning,
limit and expiry once and mints a `Thesis` per market from it.

The honesty cost is real and is recorded rather than absorbed: every minted thesis carries,
in `considered`, the fact that nobody looked at *this* market before authorising it. An arb
is the one position where that is defensible — the claim is not that this fixture will go a
particular way, it is that two books disagree by more than the cost of taking both sides —
and the reasoning field is where that has to be said out loud.

## Three books rather than two, where the prices allow it

`find_arb` already computes a one-book-per-leg alternative and states what diversifying
costs in margin. This lane takes it when it exists. Two legs at one bookmaker means one
restriction or one voided market takes out both and leaves the rest unhedged, and soft books
restrict arbitrage accounts as routine business rather than as a tail risk. The margin given
up is the premium on that, and the slip records which combination was used.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from lib.arbfind import ARB_CANDIDATE, UNKNOWN_STAKE, ArbCandidate, Quote, scan_markets
from lib.betslip import MINIMUM_RETURN_PCT, READY_TO_PLACE, SlipLeg, build_slip
from lib.candidates import INDETERMINATE, PASSED, REFUSED, Candidate, Stage
from lib.reaper import Reaper, Unworthy
from lib.thesis import Thesis

#: How far apart two quotes may have been observed and still be treated as a single
#: combination. Above this they were prices at different moments rather than a position.
FRESHNESS_SECONDS = 180

#: Matches any pair of books. Deliberately awkward to reach for: a declaration that two
#: unnamed books settle alike is not a judgement anybody made.
ANY_BOOKS = "*"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def starts_at_from_market(market: str) -> datetime | None:
    """The aggregator names a market `Home v Away @ <iso>`. Exchange ids carry no time.

    Returning None is the whole point of the function: an exchange market called `1.234567`
    has no start time in its name, and the gate that consumes this treats "not known" as
    blocking rather than as fine.
    """

    _, separator, tail = str(market).rpartition(" @ ")
    return _parse(tail) if separator else None


@dataclass(frozen=True, slots=True)
class Reading:
    """One precondition a price feed cannot establish, and whether it stops the lane.

    `blocking` is stated rather than inferred from the status name, because whether a gate
    halts a lane should not depend on how somebody spelled a constant.
    """

    status: str
    detail: str
    blocking: bool = True

    def describe(self) -> str:
        return f"{self.status}: {self.detail}"


@dataclass(frozen=True, slots=True)
class StandingAuthority:
    """One person authorising a class of positions once, rather than each one.

    Not a loophole around `Thesis` requiring a human author — the human is still named on
    every minted thesis and still carries the limit and the expiry. What it drops is the
    pretence that they read each fixture, and that omission is written into the thesis
    rather than left for a reader to work out.
    """

    declared_by: str
    reasoning: str
    considered: tuple[str, ...]
    expires_at: str
    max_exposure: float
    declared_at: str = ""
    currency: str = "EUR"

    #: Named on every minted thesis. An arb thesis makes no claim about the fixture, which
    #: is exactly why a standing grant is defensible here and would not be for a stock.
    STANDING_CAVEAT = (
        "this authorisation was minted from a standing grant: nobody looked at this "
        "particular market before authorising it, and the grant rests on the position "
        "making no claim about the event's outcome"
    )

    def __post_init__(self) -> None:
        """Checked here, not only when a thesis is minted.

        `Thesis` applies the same guard, but it applies it per market inside `reap()` —
        so an automation-authored grant assembled cleanly at start-up and raised in the
        middle of a run, out of a callable nothing catches. A grant that cannot authorise
        anything should fail where it is declared.
        """

        from lib.thesis import AUTOMATION_PREFIXES

        author = self.declared_by.strip().lower()
        if not author:
            raise ValueError("a standing authority needs a named author")
        if any(author.startswith(prefix) for prefix in AUTOMATION_PREFIXES):
            raise ValueError(
                f"{self.declared_by!r} cannot hold a standing authority. Minting theses "
                f"from it does not launder the authorship: whoever is named on the grant "
                f"is named on every position taken under it"
            )

    def thesis_for(self, market: str) -> Thesis:
        return Thesis(
            subject=market,
            declared_by=self.declared_by,
            reasoning=self.reasoning,
            considered=tuple(self.considered) + (self.STANDING_CAVEAT,),
            declared_at=self.declared_at or _now().isoformat(timespec="seconds"),
            expires_at=self.expires_at,
            max_exposure=self.max_exposure,
            currency=self.currency,
        )


def books_key(books: Sequence[str]) -> str:
    return "|".join(sorted(set(books)))


def declaration_for(books: Sequence[str], declarations: Mapping[str, Any] | None):
    """The declaration covering exactly these books, or the explicit any-books one."""

    if not declarations:
        return None
    return declarations.get(books_key(books)) or declarations.get(ANY_BOOKS)


# --- the evidence under a declaration ------------------------------------------------

def rulebook_evidence(
    books: Sequence[str],
    market_type: str,
    *,
    rulebooks: Any = None,
    declaration: Any = None,
    now: datetime | None = None,
):
    """What is actually recorded about how these books settle, pair by pair.

    Returns `(verdict, detail)` where verdict is one of `lib.rulebook`'s COVERED,
    DIVERGENT or INCOMPLETE, or the string `NO_STORE` when no rulebook store was supplied
    at all. That fourth value is the one worth having: it separates "the readings say these
    books agree" from "nobody attached a record, so the declaration is a sentence with
    nothing under it", and those are not the same standard of evidence for a lock.

    Every PAIR is compared, not just the first two. A three-leg position across three books
    has three pairs, and two of them agreeing establishes nothing about the third — which
    is the leg that will void on its own while the other two stand.
    """

    from lib.rulebook import COVERED, DIVERGENT, INCOMPLETE, RulebookStore

    if rulebooks is None:
        return "NO_STORE", (
            "no rulebook store is attached, so nothing underneath this declaration has "
            "been recorded. The declaration is a person's sentence with no clause, no URL "
            "and no reading date behind it — see lib/rulebook.py.")

    if not getattr(rulebooks, "readable", True):
        return INCOMPLETE, (
            f"the rulebook store could not be read ({getattr(rulebooks, 'reason', '')}). "
            f"What these books' rules say is UNKNOWN, which is not the same as their "
            f"saying the same thing.")

    if isinstance(rulebooks, RulebookStore) and rulebooks.lost:
        return INCOMPLETE, (
            f"the rulebook store is LOST: {rulebooks.status.describe()} The readings were "
            f"taken and the record is gone, so nothing backs this declaration now.")

    if not market_type:
        # The most easily missed of the failures here. Every clause is filed under a market
        # type, so with none established the store is queried for rules that cannot match
        # and answers UNREAD — a refusal that looks like "go and read the pages" when the
        # real problem is that the lane does not know which pages.
        return INCOMPLETE, (
            f"the market type is not established for {', '.join(books)}, so which "
            f"rulebook applies was never looked up. A feed that does not name its sport "
            f"leaves settlement unknown rather than ordinary.")

    if len(books) < 2:
        return INCOMPLETE, "a settlement comparison needs two books"

    declared_at = str(getattr(declaration, "declared_at", "") or "")
    verdicts: list[str] = []
    details: list[str] = []
    for index, first in enumerate(books):
        for second in books[index + 1:]:
            comparison = rulebooks.compare(first, second, market_type, now=now,
                                           pair_declared_at=declared_at)
            verdicts.append(comparison.verdict)
            if comparison.verdict != COVERED:
                outstanding = ", ".join(t.topic for t in comparison.outstanding)
                details.append(
                    f"{first} vs {second}: {comparison.verdict}"
                    + (f" on {outstanding}" if outstanding else "")
                    + (f". {comparison.superseded_declaration}"
                       if comparison.superseded_declaration else ""))

    if DIVERGENT in verdicts:
        return DIVERGENT, "; ".join(details)
    if INCOMPLETE in verdicts:
        return INCOMPLETE, "; ".join(details)
    return COVERED, (
        f"every disqualifying topic is identical wording or declared alike across all "
        f"{len(verdicts)} pair(s) of {', '.join(books)} for {market_type}")


# --- the cascade -------------------------------------------------------------------

def chosen_quotes(
    candidate: ArbCandidate, *, prefer_distinct_books: bool = True
) -> tuple[Quote, ...]:
    """The combination that will actually be placed — screened AND sized from this.

    Screening one combination and placing another is how a settlement declaration covering
    two books ends up backing a position at three. `find_arb` reports the cheapest
    combination as the headline and a one-book-per-leg alternative beside it, and this lane
    prefers the alternative, so the alternative is what every stage must be asked about:
    its books, its margin, its observation spread.
    """

    if prefer_distinct_books and candidate.distinct_book_alternative:
        return candidate.distinct_book_alternative
    return candidate.quotes


def screen_candidate(
    candidate: ArbCandidate,
    *,
    declarations: Mapping[str, Any] | None = None,
    rulebooks: Any = None,
    now: datetime | None = None,
    freshness_seconds: int = FRESHNESS_SECONDS,
    prefer_distinct_books: bool = True,
) -> Candidate:
    """Ordered cheapest and most fatal first, per `lib/candidates.py`.

    Settlement leads even though it is not the cheapest check, because a position that
    cannot settle should be refused before anybody prices it.
    """

    moment = now or _now()
    stages: list[Stage] = []
    placed = chosen_quotes(candidate, prefer_distinct_books=prefer_distinct_books)
    books = tuple(sorted({q.book for q in placed}))
    implied = sum(q.implied_pct for q in placed)

    declaration = declaration_for(books, declarations)
    stages.append(_settlement(books, candidate.market_type, declaration, rulebooks, moment))

    if len(books) < 2:
        stages.append(Stage(
            "two counterparties", REFUSED, disqualifying=True,
            detail=(f"every leg is at {books[0] if books else 'one book'}. One book pricing "
                    f"both sides is one counterparty, and it may void the whole market."),
        ))
    else:
        stages.append(Stage(
            "two counterparties", PASSED, disqualifying=True,
            detail=f"{len(books)} book(s): {', '.join(books)}.",
        ))

    missing = set(candidate.selections_expected) - {q.selection for q in placed}
    if missing or candidate.status != ARB_CANDIDATE:
        stages.append(Stage(
            "complete book", REFUSED, disqualifying=True,
            detail=(f"{len(placed)} of {len(candidate.selections_expected)} "
                    f"selection(s) quoted; missing {', '.join(sorted(missing)) or 'none'}. "
                    f"Backing only what is quoted is a bet on the rest not happening."
                    if missing else f"status is {candidate.status}, not {ARB_CANDIDATE}."),
        ))
    else:
        stages.append(Stage(
            "complete book", PASSED, disqualifying=True,
            detail=f"all {len(candidate.selections_expected)} selection(s) quoted.",
        ))

    if implied >= 100.0:
        stages.append(Stage(
            "margin after commission", REFUSED, disqualifying=True,
            detail=(f"implies {implied:.3f}%. That is the books' margin and it is the "
                    f"normal state of a market."),
        ))
    else:
        stages.append(Stage(
            "margin after commission", PASSED, disqualifying=True,
            detail=(f"implies {implied:.3f}%, margin {100.0 - implied:+.3f}% before "
                    f"stakes are floored."),
        ))

    stages.append(_freshness(placed, moment, freshness_seconds))
    return Candidate(candidate.market, tuple(stages))


def _settlement(
    books: Sequence[str], market_type: str, declaration: Any, rulebooks: Any,
    moment: datetime,
) -> Stage:
    """The first stage, and the only one that can be wrong in a way that costs everything.

    Two things have to be true and they are separate. A named person must have declared
    that these books settle alike — that judgement stays human and no amount of recorded
    clause text replaces it. And the reading it was made from must still stand: the clauses
    read, not stale, and not re-read since the declaration was signed.

    The four outcomes are kept apart because a person acts differently on each:

        no declaration      INDETERMINATE. Go and read two rules pages, once, ever.
        declared, divergent REFUSED. The evidence contradicts the declaration; the
                            declaration is the thing that is wrong and it must be revisited
        declared, unread    INDETERMINATE naming the exact topics still to read
        declared, covered   PASSED, and the report says what it rests on

    A declaration with no rulebook store attached still PASSES, as it did before this
    module existed — a system that started refusing every previously-working configuration
    on the day the evidence layer arrived would simply be turned off. What changes is that
    the stage now says out loud that nothing is underneath it.
    """

    from lib.rulebook import COVERED, DIVERGENT

    if declaration is None:
        return Stage(
            "settlement equivalence", INDETERMINATE, disqualifying=True,
            detail=(f"no declaration covers {books_key(books)}. A price feed does not carry "
                    f"a book's terms, and the only real position this board examined had a "
                    f"positive margin and voided on one leg only. Read both books' rules "
                    f"once and record an EquivalenceDeclaration under this key."),
        )

    verdict, detail = rulebook_evidence(
        books, market_type, rulebooks=rulebooks, declaration=declaration, now=moment)
    signed = (f"{declaration.declared_by} declared {', '.join(books)} settle alike: "
              f"{declaration.reasoning}")

    if verdict == DIVERGENT:
        return Stage(
            "settlement equivalence", REFUSED, disqualifying=True,
            detail=(f"{signed} — AND THE RECORDED RULES SAY OTHERWISE: {detail}. A "
                    f"declaration contradicted by the clauses somebody read is not a "
                    f"precondition that has been met; it is a judgement to make again."),
        )
    if verdict == COVERED:
        return Stage(
            "settlement equivalence", PASSED, disqualifying=True,
            detail=f"{signed} Backed by the rulebook: {detail}.",
        )
    if verdict == "NO_STORE":
        return Stage(
            "settlement equivalence", PASSED, disqualifying=True,
            detail=f"{signed} {detail}",
        )
    return Stage(
        "settlement equivalence", INDETERMINATE, disqualifying=True,
        detail=(f"{signed} — and the record does not yet support it: {detail}. The "
                f"declaration is not being disbelieved; it is not established, and an "
                f"unestablished precondition is not a satisfied one."),
    )


def _freshness(placed: Sequence[Quote], moment: datetime, window: int) -> Stage:
    stamps = sorted(q.observed_at for q in placed if q.observed_at)
    first, last = (stamps[0], stamps[-1]) if stamps else ("", "")
    earliest, latest = _parse(first), _parse(last)
    if len(stamps) != len(placed):
        earliest = None
    if earliest is None or latest is None:
        return Stage(
            "price freshness", INDETERMINATE, disqualifying=True,
            detail=("at least one quote carries no readable observation time, so how long "
                    "ago these were the prices is unknown."),
        )

    spread = (latest - earliest).total_seconds()
    age = (moment - latest).total_seconds()
    if spread > window:
        return Stage(
            "price freshness", REFUSED, disqualifying=True,
            detail=(f"the legs were observed {spread:.0f}s apart, over a {window}s window. "
                    f"They were prices at different moments rather than a combination."),
        )
    if age > window:
        return Stage(
            "price freshness", REFUSED, disqualifying=True,
            detail=(f"the newest quote is {age:.0f}s old, over a {window}s window. A margin "
                    f"computed on gone prices is arithmetic, not an opportunity."),
        )
    return Stage(
        "price freshness", PASSED, disqualifying=True,
        detail=f"legs {spread:.0f}s apart, newest {age:.0f}s old, within {window}s.",
    )


# --- the gates ---------------------------------------------------------------------

def gates_for(
    candidate: ArbCandidate,
    *,
    declarations: Mapping[str, Any] | None = None,
    rulebooks: Any = None,
    starts_at: Callable[[str], datetime | None] = starts_at_from_market,
    register: Any = None,
    now: datetime | None = None,
    prefer_distinct_books: bool = True,
) -> tuple[Reading, ...]:
    """What no cascade stage can establish from prices alone.

    Deliberately short. Every reading here is a precondition; observations that are merely
    worth knowing (book concentration, unread maximum stakes) already appear on the slip and
    would only dilute the findings if repeated as ones that block.

    The seen register is NOT here. It used to be, and it was the only lane that checked it —
    `lib.reaper` now does it for every lane, and two mechanisms for one job is how they
    drift apart.
    """

    moment = now or _now()
    readings: list[Reading] = []
    books = tuple(sorted({q.book for q in chosen_quotes(
        candidate, prefer_distinct_books=prefer_distinct_books)}))

    declaration = declaration_for(books, declarations)
    if declaration is None:
        readings.append(Reading(
            "SETTLEMENT_RULES_NOT_DECLARED",
            f"no EquivalenceDeclaration covers {books_key(books)}",
        ))
    else:
        # Asked again here, and deliberately not shared with the cascade's answer. The
        # cascade decides whether to SURFACE and the gates decide whether the thesis may
        # authorise, and a precondition that stopped one and not the other would be a hole
        # exactly the width of whichever check somebody remembered to run.
        from lib.rulebook import COVERED, DIVERGENT

        verdict, detail = rulebook_evidence(
            books, candidate.market_type, rulebooks=rulebooks,
            declaration=declaration, now=moment)
        if verdict == DIVERGENT:
            readings.append(Reading("SETTLEMENT_RULES_DIVERGE", detail))
        elif verdict not in {COVERED, "NO_STORE"}:
            readings.append(Reading("SETTLEMENT_RULES_NOT_ESTABLISHED", detail))

    commencement = starts_at(candidate.market)
    if commencement is None:
        readings.append(Reading(
            "EVENT_START_UNKNOWN",
            (f"{candidate.market!r} carries no readable start time. Not a finding that the "
             f"event is upcoming — a price on a market that has already turned in play, or "
             f"settled, is not a price you can take."),
        ))
    elif commencement <= moment:
        readings.append(Reading(
            "EVENT_ALREADY_STARTED",
            f"started {commencement.isoformat(timespec='seconds')}, which is in the past",
        ))

    return tuple(readings)


# --- sizing ------------------------------------------------------------------------

def _slip_legs(quotes: Sequence[Quote]) -> tuple[SlipLeg, ...]:
    return tuple(
        SlipLeg(
            book=q.book, selection=q.selection, decimal_odds=q.decimal_odds, stake=0.0,
            # A feed returns odds, not liquidity. Zero here means nobody read it, and the
            # slip prints that on the leg rather than assuming the book will take the stake.
            max_stake_seen=(0.0 if q.available_stake == UNKNOWN_STAKE
                            else float(q.available_stake)),
            settlement_rule="",
        )
        for q in quotes
    )


def size_candidate(
    candidate: ArbCandidate,
    *,
    bankroll_limit: float,
    minimum_return_pct: float = MINIMUM_RETURN_PCT,
    prefer_distinct_books: bool = True,
):
    """A slip, or a stated refusal — never a slip that should not be placed.

    Takes the one-book-per-leg combination when `find_arb` found one, which usually costs
    margin and is the trade the holder asked for: one restriction at one bookmaker should
    not be able to take out two legs.
    """

    placed = chosen_quotes(candidate, prefer_distinct_books=prefer_distinct_books)
    note = ""
    if placed is not candidate.quotes:
        cost = sum(q.implied_pct for q in placed) - candidate.total_implied_pct
        note = (f"one book per leg, costing {cost:+.3f}% of margin against the cheapest "
                f"combination")

    slip = build_slip(candidate.market, _slip_legs(placed),
                      bankroll_limit=bankroll_limit,
                      minimum_return_pct=minimum_return_pct)
    if slip.status != READY_TO_PLACE:
        return Unworthy(f"the slip refused it: {slip.reason}")
    return replace(slip, reason=note) if note else slip


def measure_slip(slip) -> tuple[float, float]:
    """What the breakers check: how much is going on, and the edge being claimed."""

    return (float(slip.total_stake), float(slip.return_pct))


# --- assembly ----------------------------------------------------------------------

def arb_identity_for(candidate: ArbCandidate, *, prefer_distinct_books: bool = True) -> str:
    """The market and the (book, selection) pairs that will be backed. Never the price.

    Same combination the cascade screened and the slip will size, for the same reason: an
    identity built from the cheapest quotes while the diversified ones are placed would
    dedupe a position nobody takes. And the odds are excluded deliberately — including them
    makes every tick a new sighting, and the register dedupes nothing while appearing to.
    """

    from lib.seen import arb_identity

    placed = chosen_quotes(candidate, prefer_distinct_books=prefer_distinct_books)
    return arb_identity(candidate.market, [(q.book, q.selection) for q in placed])


def build_arb_reaper(
    *,
    authority: StandingAuthority,
    breakers: Any,
    sports: Sequence[str] = (),
    #: Provider keys to ask for instead of a whole region. Empty asks for the region, and
    #: the connector's docstring argues why that is the default rather than a book list.
    bookmakers: Sequence[str] = (),
    declarations: Mapping[str, Any] | None = None,
    #: The clauses somebody actually read, as a `lib.rulebook.RulebookStore`. Optional: a
    #: lane with none behaves exactly as it did before rulebooks existed and says so on
    #: every settlement stage, rather than a missing store quietly tightening the lane.
    rulebooks: Any = None,
    source: Any = None,
    register: Any = None,
    starts_at: Callable[[str], datetime | None] = starts_at_from_market,
    now: Callable[[], datetime] = _now,
    freshness_seconds: int = FRESHNESS_SECONDS,
    minimum_return_pct: float = MINIMUM_RETURN_PCT,
    prefer_distinct_books: bool = True,
    bankroll_limit: float | None = None,
) -> Reaper:
    """The arb lane as a `Reaper`. Nothing here places a bet, and nothing here can.

    `bankroll_limit` defaults to the standing grant's exposure limit. The breakers apply
    their own per-position cap afterwards on the sized total, so the tighter of the two
    binds without either needing to know about the other.
    """

    limit = authority.max_exposure if bankroll_limit is None else bankroll_limit

    def look():
        from connectors.oddsapi import H2H, OddsApiSource

        feed = (source if source is not None
                else OddsApiSource.from_directory(bookmakers=bookmakers))
        if not getattr(feed, "is_configured", False):
            # Raising is correct: this is COULD_NOT_LOOK, and reporting it as an empty
            # scan is the exact confusion the reaper's status set exists to prevent.
            raise RuntimeError(
                "no odds source is configured, so nothing was scanned. This is not a "
                "finding that no arb exists."
            )

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
                f"all {asked} sport(s) failed to answer; nothing was scanned"
            )

        markets: dict[str, set] = {}
        for quote in quotes:
            markets.setdefault(quote.market, set()).add(quote.selection)
        result = scan_markets({m: tuple(sorted(s)) for m, s in markets.items()}, quotes)
        return list(result.arbs), asked, answered

    return Reaper(
        name="arb", lane="arb",
        look=look,
        screen=lambda c: screen_candidate(
            c, declarations=declarations, rulebooks=rulebooks, now=now(),
            freshness_seconds=freshness_seconds,
            prefer_distinct_books=prefer_distinct_books),
        gates=lambda c: gates_for(
            c, declarations=declarations, rulebooks=rulebooks, starts_at=starts_at,
            register=register, now=now(),
            prefer_distinct_books=prefer_distinct_books),
        thesis_for=lambda c: authority.thesis_for(c.market),
        size=lambda c, _permission: size_candidate(
            c, bankroll_limit=limit, minimum_return_pct=minimum_return_pct,
            prefer_distinct_books=prefer_distinct_books),
        breakers=breakers,
        measure=measure_slip,
        register=register,
        identity=lambda c: arb_identity_for(
            c, prefer_distinct_books=prefer_distinct_books),
    )
