"""What each book's settlement rules actually say — quoted, dated, and attributed.

`lib/arb.py` refuses a pair of legs whose settlement rules are not declared identical, and
`lib/arb_reaper.py` reports every candidate as INDETERMINATE until an
`EquivalenceDeclaration` names the two books. That is correct and it leaves the interesting
half undone, because a declaration is a single sentence — "Ian says William Hill and
Smarkets settle alike" — with nothing underneath it. It cannot be checked, it cannot go
stale, and it cannot say *which* scenario was compared.

This is the underneath. A `Clause` is one book's wording on one settlement question, as a
person read it off the book's own rules page: the words, the URL, who read them and when.
A `Rulebook` is a book's clauses for one market type. `compare` puts two rulebooks side by
side, topic by topic, and reports what is the same, what differs, and — the part that
matters most — what nobody has read yet.

## Three things this deliberately does not do

**It does not decide that two different wordings settle alike.** That is the judgement
`EquivalenceDeclaration` exists to keep with a named human, argued there from a real pair:
Betfair's "your return will be half of what it could have been" and bet365's "stake divided
by the number of tying competitors, paid at full odds on that reduced stake" return the same
money on a two-way dead heat and share no words. A comparator that called those DIVERGENT
would refuse every real pair and teach its reader to ignore it; one that called them AGREED
would be automation making exactly the call it is not entitled to make. So the machine
reports `IDENTICAL` (a fact about two strings) or `DIFFERENT_WORDING` (also a fact about two
strings, and *not* a finding of divergence), and a `TopicDeclaration` from a person is what
turns the second into DECLARED_ALIKE or DECLARED_DIVERGENT.

**It does not fetch anything.** No rules page is retrieved, parsed or scraped here. A
bookmaker's terms are prose with defined terms, cross-references and per-competition
exceptions, and a scraper producing 90% of that is producing a rule that is wrong in a way
nobody can see. Reading the page is a person's job and the record of having read it is what
this module holds.

**It does not treat unread as agreed.** `UNREAD` is a status of its own and it blocks. A
comparison covering three of ten topics is not a comparison; it is three topics and seven
unexamined ways to lose the whole stake on one leg.

## Staleness, and why it has a number

A book revises its terms when it likes and announces it to nobody. There is no change feed,
so the only available protection is the age of the reading. `STALE_AFTER_DAYS` is 180: short
enough that a rule change between seasons is caught before the next season is bet into, long
enough that re-reading is a twice-a-year job rather than a chore that gets skipped, which is
the failure mode of every shorter number.

A stale clause is `STALE`, never absent and never fine. That is the same third state the
rest of this repository keeps: read-and-old and never-read call for different actions from a
person, and a system that merged them would send them to re-read ten pages when one had
changed.

## The declaration-was-made-first case

The subtlest failure this module exists to catch. A person reads two books' abandonment
clauses on the 10th and declares them equivalent. On the 20th somebody re-reads one book and
records new wording. The declaration is still sitting in the config, still passing the
cascade, and it was made about words that are no longer on the page.

So a declaration carries `declared_at`, and a clause read after it invalidates it —
INDETERMINATE, naming the book and the topic, asking for the judgement to be made again
against what the page says now. Failing toward stopping: an out-of-date declaration is not
a satisfied precondition.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from lib.store import JSON_BACKEND, LOST, Receipt, StoreStatus, inspect
from lib.thesis import AUTOMATION_PREFIXES

#: How old a reading may be before it stops counting as knowledge of the current terms.
STALE_AFTER_DAYS = 180

# Per-topic comparison outcomes. The first two are facts about strings and a machine may
# state them; the next two are judgements and only a person may. The last two are absences.
IDENTICAL = "IDENTICAL"
DIFFERENT_WORDING = "DIFFERENT_WORDING"
DECLARED_ALIKE = "DECLARED_ALIKE"
DECLARED_DIVERGENT = "DECLARED_DIVERGENT"
UNREAD = "UNREAD"
STALE = "STALE"

#: Per-topic outcomes that satisfy the topic. Deliberately short, and DIFFERENT_WORDING is
#: deliberately not in it: two wordings that differ are an open question, not an answer.
SETTLED_ALIKE = frozenset({IDENTICAL, DECLARED_ALIKE})

# Whole-comparison verdicts.
COVERED = "COVERED"
DIVERGENT = "DIVERGENT"
INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True, slots=True)
class Topic:
    """One settlement question two books can answer differently.

    `disqualifying` marks the questions where a divergence alone turns the position into a
    bet. The others are worth reading and worth recording and do not, on their own, stop a
    lane — the distinction `lib/candidates.py` draws between a precondition and a
    preference, kept here so a reader can see which is which.
    """

    key: str
    question: str
    why: str
    disqualifying: bool = True


#: The questions worth reading two books' pages for, ordered by how often each has actually
#: cost somebody the stake. Abandonment is first because it is the one this board met: a
#: two-leg position with a positive margin net of commission, refused because the exchange
#: leg voided on abandonment while the bookmaker leg stood if the fixture was replayed
#: within 48 hours.
#:
#: The list is short on purpose. Every entry here is a page a person has to read for every
#: book they use, so an entry that has never decided anything is a tax on the one job this
#: module needs somebody to actually do.
TOPICS: tuple[Topic, ...] = (
    Topic(
        "abandonment",
        "What happens to a bet if the match is abandoned before it finishes?",
        "The divergence this board actually met. An exchange voids; a bookmaker may let "
        "the bet stand if the fixture is replayed inside a stated window. One leg voided "
        "and one standing is an unhedged single bet for the whole stake on the other side.",
    ),
    Topic(
        "postponement",
        "How long may a postponed fixture be replayed within and still settle the bet?",
        "The same failure as abandonment with a different trigger, and the windows are the "
        "part that diverges: 48 hours, the same weekend, the end of the season, and void "
        "immediately are all real answers offered by books that are otherwise similar.",
    ),
    Topic(
        "venue_change",
        "Does the bet stand if the fixture moves to another ground or a neutral venue?",
        "Home advantage is priced in, so a book that voids on a venue change and a book "
        "that stands are pricing two different events. Rare, and it concentrates exactly "
        "where prices are already unusual, which is where an arb is found.",
    ),
    Topic(
        "extra_time",
        "Does the market settle on 90 minutes plus stoppage, or does extra time count?",
        "The commonest silent divergence in knockout football, and unlike the others it "
        "does not need anything unusual to happen — it decides the outcome of an ordinary "
        "match that happens to be level at full time.",
    ),
    Topic(
        "result_source",
        "Whose declaration of the result settles the market, and when?",
        "Two books settling from different bodies can pay opposite ways on a result that "
        "is later amended — an awarded match, a walkover, a disqualification. Whether "
        "later amendments are honoured is part of the same answer.",
    ),
    Topic(
        "palpable_error",
        "Under what terms may the book void a bet it says was priced in error?",
        "The clause aimed squarely at the position an arb takes: the outlying price is the "
        "one being backed, and it is the one most likely to be called an error. A book "
        "that can void the profitable leg after the fact leaves the hedge running alone.",
    ),
    Topic(
        "maximum_payout",
        "What is the most this book will pay out on one bet, one market or one day?",
        "A cap does not void anything and it silently truncates the winning leg, so the "
        "position pays less than the arithmetic says while the losing leg pays in full. It "
        "binds at stake sizes worth having, which is the only size that matters.",
    ),
    Topic(
        "dead_heat",
        "How is a tie between two selections settled?",
        "The worked example in `lib.arb.EquivalenceDeclaration`: Betfair and bet365 use "
        "wording with no words in common and return the same money. Recorded because it is "
        "the case that proves a wording comparison must not be the last word.",
    ),
    Topic(
        "non_runner",
        "What deduction applies when a participant is withdrawn?",
        "Rule 4 on the winnings against a reduction factor on the odds — the same algebra "
        "at equal rates, and the rates come from different places. "
        "`lib.arb.non_runner_divergence` computes the gap rather than assuming it away.",
        disqualifying=False,
    ),
    Topic(
        "cash_out_and_restriction",
        "May the book limit, restrict or close the account, and on what notice?",
        "Not a settlement rule, and recorded because the position depends on both legs "
        "being placeable at size. A soft book restricting an arbitrage account is routine "
        "business rather than a tail risk, and it decides which pair is worth using.",
        disqualifying=False,
    ),
)

TOPICS_BY_KEY: Mapping[str, Topic] = {topic.key: topic for topic in TOPICS}

#: The subset a divergence on which is enough, alone, to make the position a bet.
DISQUALIFYING = tuple(topic.key for topic in TOPICS if topic.disqualifying)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    """`None` on an unreadable stamp, so an unknown date never reads as a recent one."""

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _refuse_automation(who: str, what: str) -> str:
    """One guard, used by both things in this file a person has to sign.

    Reading a rules page and quoting it is as much a human act as declaring two wordings
    equivalent. Nothing in this repository retrieves a book's terms, so a clause attributed
    to an agent is a clause nobody read — and it would be indistinguishable from one
    somebody did, which is the whole reason the attribution exists.
    """

    name = who.strip()
    if not name:
        raise ValueError(f"{what} needs a named person: an unattributed reading is a "
                         f"recollection, and there is no page to check it against")
    if any(name.lower().startswith(prefix) for prefix in AUTOMATION_PREFIXES):
        raise ValueError(
            f"{who!r} cannot be named for {what}. No source in this repository returns a "
            f"book's terms, so this can only be the record of a person opening the page — "
            f"and a machine-attributed clause would sit in the store looking exactly like "
            f"one somebody actually read"
        )
    return name


@dataclass(frozen=True, slots=True)
class Clause:
    """One book's wording on one settlement question, as somebody read it off the page.

    `verbatim` is quoted and never normalised, for the reason `lib.arb.Leg` gives about
    `settlement_rule`: normalising is precisely where two different rules become one. The
    URL is mandatory because a rule with no page behind it cannot be re-read when it
    changes, which is the only way anybody finds out that it did.
    """

    book: str
    market_type: str
    topic: str
    verbatim: str
    source_url: str
    read_by: str
    read_at: str

    def __post_init__(self) -> None:
        if self.topic not in TOPICS_BY_KEY:
            raise ValueError(
                f"unknown settlement topic {self.topic!r}. Known topics are "
                f"{', '.join(TOPICS_BY_KEY)}. A topic nobody has named is a comparison "
                f"nothing will ever make."
            )
        if not self.verbatim.strip():
            raise ValueError(
                f"{self.book}/{self.topic}: a clause with no wording records that somebody "
                f"opened a page, not what it said"
            )
        if not self.source_url.strip():
            raise ValueError(
                f"{self.book}/{self.topic}: a clause needs the URL it was read from. "
                f"Without it nobody can re-read it when the book changes it, and a book "
                f"changing its terms is the event this whole record exists to survive"
            )
        if _parse(self.read_at) is None:
            raise ValueError(
                f"{self.book}/{self.topic}: read_at {self.read_at!r} is not a readable "
                f"date. An undated reading cannot go stale, which means it never stops "
                f"being believed"
            )
        object.__setattr__(self, "read_by", _refuse_automation(
            self.read_by, f"the reading of {self.book}'s {self.topic} clause"))

    @property
    def normalised(self) -> str:
        """Whitespace-collapsed and lowercased, for equality only.

        Used to answer "are these literally the same words", never to answer "do these mean
        the same thing". The second question is a person's.
        """

        return " ".join(self.verbatim.lower().split())

    def age_days(self, now: datetime | None = None) -> float | None:
        moment = now or _now()
        read = _parse(self.read_at)
        return None if read is None else (moment - read).total_seconds() / 86400.0

    def is_stale(self, now: datetime | None = None,
                 stale_after_days: int = STALE_AFTER_DAYS) -> bool:
        age = self.age_days(now)
        # An unreadable date is treated as stale rather than as fresh. Construction refuses
        # one, so this is only reachable through a hand-edited store — and the direction
        # that halts is the direction to be wrong in.
        return True if age is None else age > stale_after_days

    def describe(self, now: datetime | None = None) -> str:
        age = self.age_days(now)
        aged = "age unknown" if age is None else f"{age:.0f} days old"
        mark = "  STALE" if self.is_stale(now) else ""
        return (f"{self.book} / {self.topic}{mark}\n"
                f"  \"{self.verbatim.strip()}\"\n"
                f"  read by {self.read_by} on {self.read_at} ({aged}) from "
                f"{self.source_url}")


@dataclass(frozen=True, slots=True)
class TopicDeclaration:
    """A named human saying what two books' differing wordings actually do on one topic.

    Narrower than `lib.arb.EquivalenceDeclaration` on purpose. That one covers a pair of
    books entirely and is what the cascade consults; this covers one topic, so a person can
    record "these two agree on abandonment and I have not compared extra time" instead of
    having to declare everything at once or nothing at all. Partial honest coverage is what
    people actually produce on an evening with two rules pages open.

    `settle_alike=False` is not a nuisance value. Recording that two books DIVERGE on a
    topic is worth as much as recording that they agree: it stops the pair being examined
    again every season, and it is the finding that keeps a lane from placing.
    """

    book_a: str
    book_b: str
    topic: str
    settle_alike: bool
    declared_by: str
    reasoning: str
    declared_at: str
    #: The concrete cases walked through. Not decoration: "they both void" is a claim about
    #: the words, and "on a 2-0 abandonment at 70 minutes both return the stake" is a claim
    #: about money, which is the one being relied on.
    scenarios_checked: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.topic not in TOPICS_BY_KEY:
            raise ValueError(f"unknown settlement topic {self.topic!r}")
        if not self.reasoning.strip():
            raise ValueError(
                "a declaration without reasoning is indistinguishable from a guess")
        if _parse(self.declared_at) is None:
            raise ValueError(
                f"declared_at {self.declared_at!r} is not a readable date. A declaration "
                f"with no date cannot be found to predate the wording it is about"
            )
        object.__setattr__(self, "declared_by", _refuse_automation(
            self.declared_by, f"a settlement declaration on {self.topic}"))

    @property
    def pair(self) -> tuple[str, str]:
        return tuple(sorted((self.book_a, self.book_b)))  # type: ignore[return-value]

    def covers(self, book_a: str, book_b: str, topic: str) -> bool:
        return self.topic == topic and self.pair == tuple(sorted((book_a, book_b)))


@dataclass(frozen=True, slots=True)
class Rulebook:
    """One book's clauses for one market type, and what it has not been read on."""

    book: str
    market_type: str
    clauses: tuple[Clause, ...] = ()

    def clause(self, topic: str) -> Clause | None:
        """The most recent reading of this topic, or None. Never a default.

        Most recent rather than first, because a re-read is a correction: the page changed
        or the earlier reading was partial, and either way the newer one is the one that
        describes the terms in force.
        """

        matching = [c for c in self.clauses if c.topic == topic]
        if not matching:
            return None
        return max(matching, key=lambda c: _parse(c.read_at) or datetime.min.replace(
            tzinfo=timezone.utc))

    def unread(self, *, disqualifying_only: bool = False) -> tuple[str, ...]:
        topics = DISQUALIFYING if disqualifying_only else tuple(TOPICS_BY_KEY)
        return tuple(topic for topic in topics if self.clause(topic) is None)

    def stale(self, now: datetime | None = None,
              stale_after_days: int = STALE_AFTER_DAYS) -> tuple[str, ...]:
        return tuple(
            topic for topic in TOPICS_BY_KEY
            if (c := self.clause(topic)) is not None
            and c.is_stale(now, stale_after_days)
        )

    def last_read_at(self) -> str:
        """When anything in this book was last read. Empty when nothing has been."""

        stamps = sorted(c.read_at for c in self.clauses)
        return stamps[-1] if stamps else ""

    def describe(self, now: datetime | None = None) -> str:
        read = len(TOPICS_BY_KEY) - len(self.unread())
        lines = [f"{self.book}  [{self.market_type}]  {read} of {len(TOPICS_BY_KEY)} "
                 f"topic(s) read"]
        for topic in TOPICS:
            clause = self.clause(topic.key)
            gate = " (precondition)" if topic.disqualifying else ""
            if clause is None:
                lines.append(f"  UNREAD  {topic.key}{gate}")
                lines.append(f"          {topic.question}")
            elif clause.is_stale(now):
                age = clause.age_days(now)
                lines.append(f"  STALE   {topic.key}{gate}  read {clause.read_at}"
                             f"{'' if age is None else f' ({age:.0f} days ago)'}")
                lines.append(f"          re-read {clause.source_url}")
            else:
                lines.append(f"  read    {topic.key}{gate}  {clause.read_at}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class TopicComparison:
    """What is established about one topic across two books, and what a person must do."""

    topic: str
    status: str
    detail: str
    disqualifying: bool = True

    @property
    def satisfied(self) -> bool:
        return self.status in SETTLED_ALIKE

    def describe(self) -> str:
        mark = {
            IDENTICAL: "  ok  ", DECLARED_ALIKE: "  ok  ", DECLARED_DIVERGENT: " STOP ",
            DIFFERENT_WORDING: "  ??  ", UNREAD: "  ??  ", STALE: "  ??  ",
        }[self.status]
        gate = " (precondition)" if self.disqualifying else ""
        return f"[{mark}] {self.topic}{gate}  {self.status}\n         {self.detail}"


@dataclass(frozen=True, slots=True)
class Comparison:
    """Two books' rules, topic by topic, and what still has to be read or decided."""

    book_a: str
    book_b: str
    market_type: str
    topics: tuple[TopicComparison, ...] = ()
    #: A declaration for the pair that predates a clause reading, when one does. Held
    #: separately because it is a fact about the RECORD rather than about the books.
    superseded_declaration: str = ""

    @property
    def verdict(self) -> str:
        """DIVERGENT beats INCOMPLETE beats COVERED, and unread never becomes covered.

        The precedence is `lib/candidates.py`'s: a definite refusal is decisive whatever
        else could not be measured, and an unmeasured precondition blocks rather than
        averaging away. The COVERED case is the only one that permits, and it requires
        every disqualifying topic to be settled — not most of them, and not the ones
        somebody happened to have time for.
        """

        gates = [t for t in self.topics if t.disqualifying]
        if any(t.status == DECLARED_DIVERGENT for t in gates):
            return DIVERGENT
        if self.superseded_declaration:
            return INCOMPLETE
        if all(t.satisfied for t in gates) and gates:
            return COVERED
        return INCOMPLETE

    @property
    def outstanding(self) -> tuple[TopicComparison, ...]:
        """The disqualifying topics that still block, in the order they were compared."""

        return tuple(t for t in self.topics
                     if t.disqualifying and not t.satisfied)

    def describe(self) -> str:
        lines = [f"{self.verdict}  {self.book_a} vs {self.book_b}  [{self.market_type}]"]
        if self.superseded_declaration:
            lines.append(f"  {self.superseded_declaration}")
        lines += [t.describe() for t in self.topics]

        if self.verdict == COVERED:
            lines.append("")
            lines.append(
                "  Every disqualifying topic is either identical wording or declared "
                "alike by a person. That is what this record can establish; it is not a "
                "claim that no other divergence exists, only that none is known.")
            return "\n".join(lines)

        lines.append("")
        lines.append("  WHAT A PERSON HAS TO DO NEXT:")
        for topic in self.outstanding:
            lines.append(f"    - {topic.topic}: {topic.detail}")
        if self.verdict == DIVERGENT:
            lines.append(
                "  A declared divergence on a precondition is a refusal, not a gap. This "
                "pair of books does not settle this market alike and no amount of margin "
                "compensates for the legs being different bets.")
        return "\n".join(lines)


def compare(
    book_a: Rulebook,
    book_b: Rulebook,
    *,
    declarations: Sequence[TopicDeclaration] = (),
    now: datetime | None = None,
    stale_after_days: int = STALE_AFTER_DAYS,
    pair_declared_at: str = "",
) -> Comparison:
    """Two books, topic by topic. Never concludes that different wordings settle alike.

    `pair_declared_at` is when the `lib.arb.EquivalenceDeclaration` covering this pair was
    made, if there is one. A clause read AFTER that date supersedes it: the person declared
    equivalence against wording that has since been re-read, so their judgement is about
    words that may no longer be on the page. Reported rather than silently kept, because a
    stale declaration passing the cascade is a precondition that looks satisfied and is not.
    """

    moment = now or _now()
    if book_a.market_type != book_b.market_type:
        # Comparing a football win/draw/win rulebook against a tennis one would produce
        # tidy IDENTICAL rows about topics that mean different things in each.
        raise ValueError(
            f"cannot compare {book_a.book}'s {book_a.market_type!r} rules against "
            f"{book_b.book}'s {book_b.market_type!r}: a settlement question is only the "
            f"same question within one market type"
        )

    declared_at = _parse(pair_declared_at) if pair_declared_at else None
    superseded = ""
    if declared_at is not None:
        newer = [
            f"{shelf.book}/{clause.topic} re-read {clause.read_at}"
            for shelf in (book_a, book_b) for clause in shelf.clauses
            if (read := _parse(clause.read_at)) is not None and read > declared_at
        ]
        if newer:
            superseded = (
                f"THE PAIR DECLARATION IS SUPERSEDED. It was made on {pair_declared_at} "
                f"and these clauses have been read since: {', '.join(sorted(newer))}. The "
                f"judgement was made about wording nobody has compared to what is on the "
                f"page now — declare it again rather than relying on it."
            )

    rows: list[TopicComparison] = []
    for topic in TOPICS:
        clause_a = book_a.clause(topic.key)
        clause_b = book_b.clause(topic.key)

        missing = [shelf.book for shelf, clause in
                   ((book_a, clause_a), (book_b, clause_b)) if clause is None]
        if missing:
            rows.append(TopicComparison(topic.key, UNREAD, disqualifying=topic.disqualifying,
                                        detail=(
                f"nobody has read {' and '.join(missing)} on this. {topic.question} "
                f"{topic.why}")))
            continue

        assert clause_a is not None and clause_b is not None
        aged = [f"{c.book} (read {c.read_at})" for c in (clause_a, clause_b)
                if c.is_stale(moment, stale_after_days)]
        if aged:
            rows.append(TopicComparison(topic.key, STALE, disqualifying=topic.disqualifying,
                                        detail=(
                f"read more than {stale_after_days} days ago at {' and '.join(aged)}. A "
                f"book revises its terms without telling anybody, so an old reading is not "
                f"knowledge of the current terms. Re-read {clause_a.source_url} and "
                f"{clause_b.source_url}.")))
            continue

        declaration = next(
            (d for d in declarations if d.covers(book_a.book, book_b.book, topic.key)),
            None)
        if declaration is not None and not declaration.settle_alike:
            rows.append(TopicComparison(
                topic.key, DECLARED_DIVERGENT, disqualifying=topic.disqualifying, detail=(
                    f"{declaration.declared_by} compared these on {declaration.declared_at} "
                    f"and recorded that they DIFFER: {declaration.reasoning}")))
            continue

        if clause_a.normalised == clause_b.normalised:
            rows.append(TopicComparison(
                topic.key, IDENTICAL, disqualifying=topic.disqualifying, detail=(
                    "both books use the same wording, so no judgement about meaning is "
                    "being relied on here.")))
            continue

        if declaration is not None:
            scenarios = ("; ".join(declaration.scenarios_checked)
                         if declaration.scenarios_checked
                         else "no scenario was recorded, so this rests on the reasoning "
                              "alone")
            rows.append(TopicComparison(
                topic.key, DECLARED_ALIKE, disqualifying=topic.disqualifying, detail=(
                    f"the wordings differ and {declaration.declared_by} declared on "
                    f"{declaration.declared_at} that they settle alike: "
                    f"{declaration.reasoning}. Scenarios checked: {scenarios}")))
            continue

        rows.append(TopicComparison(
            topic.key, DIFFERENT_WORDING, disqualifying=topic.disqualifying, detail=(
                f"the two clauses are worded differently and nobody has said whether they "
                f"settle alike. This is NOT a finding that they diverge — Betfair and "
                f"bet365's dead-heat rules share no words and return the same money. It is "
                f"a question only a person can close, by reading both and recording a "
                f"TopicDeclaration for {topic.key}.")))

    return Comparison(book_a.book, book_b.book, book_a.market_type, tuple(rows),
                      superseded_declaration=superseded)


class RulebookStore:
    """Clauses and topic declarations on disk, with a lost store reported rather than empty.

    Same discipline as `lib.seen.SeenRegister` and for a sharper reason. An empty store
    reports every topic UNREAD, which BLOCKS — so unlike the seen register, a store that
    silently comes back empty fails safe on the lane. What it does not fail safe on is a
    person's time: it would send them to re-read ten rules pages they have already read,
    which is the way this record stops being kept. `LOST` says the readings existed and the
    file is gone, which is a different errand from `FRESH`.
    """

    def __init__(self, path: str | Path, *, readable: bool = True, reason: str = "") -> None:
        self.path = Path(path)
        self.receipt_path = self.path.with_suffix(".receipt.json")
        self.readable = readable
        self.reason = reason
        self.clauses: list[Clause] = []
        self.declarations: list[TopicDeclaration] = []
        self.status: StoreStatus = inspect(
            self.path.name, receipt_path=self.receipt_path,
            rows_found=None if not readable else 0, reason=reason,
        )

    @classmethod
    def load(cls, path: str | Path) -> "RulebookStore":
        store = cls(path)
        if not store.path.is_file():
            return store
        try:
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            store.clauses = [Clause(**row) for row in payload.get("clauses", ())]
            store.declarations = [
                TopicDeclaration(**{**row,
                                    "scenarios_checked": tuple(
                                        row.get("scenarios_checked", ()))})
                for row in payload.get("declarations", ())
            ]
        except (OSError, ValueError, TypeError) as error:
            return cls(path, readable=False,
                       reason=f"{type(error).__name__}: {error}"[:160])
        store.status = inspect(store.path.name, receipt_path=store.receipt_path,
                               rows_found=len(store.clauses) + len(store.declarations))
        return store

    @property
    def lost(self) -> bool:
        return self.status.state == LOST

    def books(self, market_type: str = "") -> tuple[str, ...]:
        return tuple(sorted({c.book for c in self.clauses
                             if not market_type or c.market_type == market_type}))

    def rulebook(self, book: str, market_type: str) -> Rulebook:
        """A book's clauses. An empty one is a real answer: nothing has been read.

        Never None, because a caller handed None reaches for a default and the default for
        "what does this book's abandonment rule say" is the one thing that must not exist.
        """

        return Rulebook(book, market_type, tuple(
            c for c in self.clauses
            if c.book == book and c.market_type == market_type))

    def compare(self, book_a: str, book_b: str, market_type: str, **kwargs) -> Comparison:
        return compare(self.rulebook(book_a, market_type),
                       self.rulebook(book_b, market_type),
                       declarations=tuple(self.declarations), **kwargs)

    def record(self, clause: Clause) -> None:
        """Append a reading. Never replaces one — see `Rulebook.clause`.

        Keeping the earlier reading is the point: a book that changed its abandonment rule
        between two readings is exactly what the record is for, and overwriting would erase
        the evidence that it did.
        """

        self._refuse_unreadable()
        self.clauses.append(clause)

    def declare(self, declaration: TopicDeclaration) -> None:
        self._refuse_unreadable()
        self.declarations.append(declaration)

    def _refuse_unreadable(self) -> None:
        if not self.readable:
            raise RuntimeError(
                f"refusing to write a rulebook store that could not be read "
                f"({self.reason}): saving would discard every clause somebody has already "
                f"gone and looked up"
            )

    def save(self, when: str = "") -> None:
        self._refuse_unreadable()
        payload = {
            "clauses": [asdict(c) for c in sorted(
                self.clauses, key=lambda c: (c.book, c.market_type, c.topic, c.read_at))],
            "declarations": [
                {**asdict(d), "scenarios_checked": list(d.scenarios_checked)}
                for d in sorted(self.declarations,
                                key=lambda d: (d.pair, d.topic, d.declared_at))
            ],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        stamp = when or _now().isoformat(timespec="seconds").replace("+00:00", "Z")
        previous = Receipt.load(self.receipt_path) or Receipt(self.path.name, JSON_BACKEND)
        rows = len(self.clauses) + len(self.declarations)
        previous.written(stamp, rows).save(self.receipt_path)

    def describe(self, market_type: str = "") -> str:
        if not self.readable:
            return (f"UNREADABLE  {self.path}: {self.reason}\n"
                    f"  No clause has been read from this store. That is not a finding "
                    f"that no rules have been recorded.")
        if self.lost:
            return (f"LOST  {self.status.describe()}\n"
                    f"  Readings were recorded here and the file is gone. Every book will "
                    f"report UNREAD, which is safe for the lane and wrong about your time: "
                    f"the pages were read, the record was not kept.")
        books = self.books(market_type)
        if not books:
            return (f"No rules have been recorded"
                    f"{f' for {market_type}' if market_type else ''} yet. Every pair of "
                    f"books will report UNREAD on every topic, which is the correct "
                    f"reading of an empty record and blocks the arb lane by design.")
        lines = [f"{len(self.clauses)} clause(s) across {len(books)} book(s): "
                 f"{', '.join(books)}"]
        if self.declarations:
            lines.append(f"{len(self.declarations)} topic declaration(s) recorded.")
        return "\n".join(lines)
