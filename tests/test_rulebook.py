"""A declaration that two books settle alike must be checkable, and must be able to expire.

Before this the arb lane's first and most fatal gate rested on one sentence in a config
file: `"Sky Bet|Smarkets": {"declared_by": "Ian", "reasoning": "..."}`. Nothing underneath
it. No clause, no URL, no date, and — the part that matters — no way for it to stop being
true. A book revises its terms and announces it to nobody, so a declaration written in
August is still passing the cascade in March against wording that changed at the turn of
the season.

The properties below are about that gap, and they divide into three groups.

**What a machine may state, and what it may not.** `lib.arb.EquivalenceDeclaration` argues
at length that comparing two wordings is the judgement automation is not entitled to make,
from a real pair: Betfair's "your return will be half of what it could have been" and
bet365's "stake divided by the number of tying competitors" return the same money on a
two-way dead heat and share no words. So `compare` may say IDENTICAL and DIFFERENT_WORDING,
which are facts about strings, and may never say two different wordings agree or diverge.
Several tests below exist only to pin that line down, because it is the line a future
convenience — a fuzzy matcher, a similarity score — would cross first.

**Unread is not agreed.** A comparison covering three topics of ten is three topics and
seven unexamined ways to lose the whole stake on one leg. UNREAD and STALE are their own
statuses, they block, and they are kept apart from each other because re-reading one page
and reading ten are different errands.

**A declaration can be out of date, and out-of-date must not read as satisfied.** The
subtlest case here: somebody compares two abandonment clauses on the 10th, one clause is
re-read on the 20th and has changed, and the declaration sits in the config passing the
gate. The declaration is not disbelieved — it is not established, and this repository's
standing rule is that an unestablished precondition is not a satisfied one.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.rulebook import (
    COVERED,
    DECLARED_ALIKE,
    DECLARED_DIVERGENT,
    DIFFERENT_WORDING,
    DISQUALIFYING,
    DIVERGENT,
    IDENTICAL,
    INCOMPLETE,
    STALE,
    STALE_AFTER_DAYS,
    TOPICS,
    UNREAD,
    Clause,
    Rulebook,
    RulebookStore,
    TopicDeclaration,
    compare,
)

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
FOOTBALL = "soccer/h2h"


def stamp(days_ago: int = 0) -> str:
    return (NOW - timedelta(days=days_ago)).date().isoformat()


def clause(book: str, topic: str, verbatim: str, *, days_ago: int = 1,
           read_by: str = "Ian McGuane") -> Clause:
    return Clause(book=book, market_type=FOOTBALL, topic=topic, verbatim=verbatim,
                  source_url=f"https://{book.lower().replace(' ', '')}.example/rules",
                  read_by=read_by, read_at=stamp(days_ago))


def fully_read(book: str, *, wording: str = "void", days_ago: int = 1) -> Rulebook:
    """Every disqualifying topic read, so a test about one topic is about one topic."""

    return Rulebook(book, FOOTBALL, tuple(
        clause(book, topic, f"{wording} on {topic}", days_ago=days_ago)
        for topic in DISQUALIFYING))


def declaration(topic: str, *, alike: bool, books=("Smarkets", "William Hill"),
                declared_days_ago: int = 1) -> TopicDeclaration:
    return TopicDeclaration(
        book_a=books[0], book_b=books[1], topic=topic, settle_alike=alike,
        declared_by="Ian McGuane",
        reasoning="read both pages side by side and worked a 2-0 abandonment at 70 minutes",
        declared_at=stamp(declared_days_ago),
        scenarios_checked=("abandoned at 70 minutes, replayed within 48 hours",),
    )


class TestOnlyAPersonMayDecideTwoWordingsMeanTheSameThing:
    """The line this module must never cross, pinned from both sides."""

    def test_wordings_that_differ_are_an_open_question_not_a_divergence(self):
        """The Betfair/bet365 dead-heat case in one assertion.

        Two rules that share no words can return identical money. A comparator that
        reported DIVERGENT here would refuse every real pair of books, and a tool that
        refuses everything is one its user stops reading — which is how the gate that
        actually catches things gets switched off.
        """

        left = Rulebook("Smarkets", FOOTBALL, (clause(
            "Smarkets", "abandonment", "all bets are void"),))
        right = Rulebook("William Hill", FOOTBALL, (clause(
            "William Hill", "abandonment",
            "stakes are returned where a match does not conclude"),))

        row = next(t for t in compare(left, right, now=NOW).topics
                   if t.topic == "abandonment")

        assert row.status == DIFFERENT_WORDING
        assert not row.satisfied
        assert "NOT a finding that they diverge" in row.detail

    def test_the_open_question_names_the_declaration_that_would_close_it(self):
        """"INDETERMINATE" alone trains a reader to skim. This has to be an errand."""

        left = Rulebook("Smarkets", FOOTBALL, (clause("Smarkets", "extra_time", "90 mins"),))
        right = Rulebook("William Hill", FOOTBALL, (clause(
            "William Hill", "extra_time", "regulation time only"),))

        row = next(t for t in compare(left, right, now=NOW).topics
                   if t.topic == "extra_time")

        assert "TopicDeclaration for extra_time" in row.detail

    def test_identical_wording_needs_no_human_judgement_at_all(self):
        """The one case a machine may close by itself, because it is a string comparison
        and is not pretending to be anything else."""

        words = "all bets are void if the match is abandoned"
        left = Rulebook("Smarkets", FOOTBALL, (clause("Smarkets", "abandonment", words),))
        right = Rulebook("William Hill", FOOTBALL, (clause(
            "William Hill", "abandonment", words.upper() + "  "),))

        row = next(t for t in compare(left, right, now=NOW).topics
                   if t.topic == "abandonment")

        assert row.status == IDENTICAL
        assert "no judgement about meaning is being relied on" in row.detail

    def test_a_person_may_close_it_either_way_and_both_are_recorded(self):
        left, right = fully_read("Smarkets"), fully_read("William Hill",
                                                         wording="stands")

        alike = compare(left, right, declarations=(declaration("abandonment", alike=True),),
                        now=NOW)
        apart = compare(left, right, declarations=(declaration("abandonment", alike=False),),
                        now=NOW)

        assert next(t for t in alike.topics
                    if t.topic == "abandonment").status == DECLARED_ALIKE
        assert next(t for t in apart.topics
                    if t.topic == "abandonment").status == DECLARED_DIVERGENT

    def test_a_clause_cannot_be_attributed_to_automation(self):
        """Nothing in this repository retrieves a book's terms, so a machine-attributed
        clause is a clause nobody read — sitting in the store looking exactly like one
        somebody did."""

        with pytest.raises(ValueError, match="cannot be named"):
            clause("Smarkets", "abandonment", "void", read_by="agent:scraper")

    def test_a_topic_declaration_cannot_be_attributed_to_automation(self):
        with pytest.raises(ValueError, match="cannot be named"):
            TopicDeclaration(
                book_a="a", book_b="b", topic="abandonment", settle_alike=True,
                declared_by="model:opus", reasoning="they look the same",
                declared_at=stamp())


class TestAClauseIsARecordOfSomebodyOpeningAPage:
    def test_a_clause_without_a_url_is_refused(self):
        """A rule with no page behind it cannot be re-read when it changes, and a book
        changing its terms is the event this whole record exists to survive."""

        with pytest.raises(ValueError, match="needs the URL"):
            Clause("Smarkets", FOOTBALL, "abandonment", "void", "", "Ian McGuane", stamp())

    def test_a_clause_without_a_readable_date_is_refused(self):
        """An undated reading cannot go stale, which means it never stops being believed."""

        with pytest.raises(ValueError, match="not a readable date"):
            Clause("Smarkets", FOOTBALL, "abandonment", "void", "https://x",
                   "Ian McGuane", "last summer")

    def test_a_clause_with_no_wording_records_only_that_somebody_opened_a_page(self):
        with pytest.raises(ValueError, match="records that somebody opened a page"):
            Clause("Smarkets", FOOTBALL, "abandonment", "   ", "https://x",
                   "Ian McGuane", stamp())

    def test_an_unnamed_topic_is_refused_rather_than_stored(self):
        """A topic nobody has named is a comparison nothing will ever make: it would sit
        in the store, never be compared against anything, and count as work done."""

        with pytest.raises(ValueError, match="unknown settlement topic"):
            clause("Smarkets", "vibes", "we settle on vibes")

    def test_the_most_recent_reading_of_a_topic_is_the_one_that_counts(self):
        """A re-read is a correction: the page changed, or the first reading was partial.
        Both are kept — the earlier one is the evidence that the terms moved — and the
        newer one is what describes the terms in force."""

        book = Rulebook("Smarkets", FOOTBALL, (
            clause("Smarkets", "abandonment", "old wording", days_ago=200),
            clause("Smarkets", "abandonment", "new wording", days_ago=2),
        ))

        assert book.clause("abandonment").verbatim == "new wording"
        assert len(book.clauses) == 2


class TestUnreadIsNotAgreed:
    def test_a_topic_nobody_read_blocks_and_says_which_book_to_read(self):
        left = Rulebook("Smarkets", FOOTBALL, (clause(
            "Smarkets", "abandonment", "void"),))
        right = Rulebook("William Hill", FOOTBALL, ())

        row = next(t for t in compare(left, right, now=NOW).topics
                   if t.topic == "abandonment")

        assert row.status == UNREAD
        assert "William Hill" in row.detail and "Smarkets" not in row.detail

    def test_a_partial_comparison_is_incomplete_rather_than_covered(self):
        """Three topics of ten is three topics and seven unexamined ways to lose the whole
        stake on one leg. The verdict must not improve because somebody ran out of time."""

        one_topic = "abandonment"
        left = Rulebook("Smarkets", FOOTBALL, (clause("Smarkets", one_topic, "void"),))
        right = Rulebook("William Hill", FOOTBALL, (clause(
            "William Hill", one_topic, "void"),))

        comparison = compare(left, right, now=NOW)

        assert comparison.verdict == INCOMPLETE
        assert {t.topic for t in comparison.outstanding} == set(DISQUALIFYING) - {one_topic}

    def test_every_disqualifying_topic_read_and_matching_is_covered(self):
        comparison = compare(fully_read("Smarkets"), fully_read("William Hill"), now=NOW)

        assert comparison.verdict == COVERED
        assert comparison.outstanding == ()
        assert "not a claim that no other divergence exists" in comparison.describe()

    def test_a_topic_that_is_not_a_precondition_does_not_block(self):
        """`lib/candidates.py`'s distinction, kept here: account restriction is worth
        recording and is not a reason the legs settle differently."""

        assert "cash_out_and_restriction" not in DISQUALIFYING
        assert compare(fully_read("Smarkets"), fully_read("William Hill"),
                       now=NOW).verdict == COVERED

    def test_one_declared_divergence_outranks_everything_else_being_covered(self):
        """A definite refusal is decisive whatever else was measured — `PRECEDENCE` in
        lib/candidates.py, applied to settlement."""

        comparison = compare(
            fully_read("Smarkets"), fully_read("William Hill", wording="stands"),
            declarations=tuple(declaration(t, alike=(t != "extra_time"))
                               for t in DISQUALIFYING),
            now=NOW)

        assert comparison.verdict == DIVERGENT
        assert "does not settle this market alike" in comparison.describe()


class TestAReadingGoesOutOfDate:
    def test_an_old_reading_is_stale_rather_than_read(self):
        """A book revises its terms and tells nobody. The age of the reading is the only
        protection available, so it has to be a status rather than a footnote."""

        old = fully_read("Smarkets", days_ago=STALE_AFTER_DAYS + 10)
        row = next(t for t in compare(old, fully_read("William Hill"), now=NOW).topics
                   if t.topic == "abandonment")

        assert row.status == STALE
        assert not row.satisfied

    def test_stale_and_unread_are_different_errands(self):
        """Re-reading one page and reading ten pages are different jobs, and a report that
        merged them would send a person to do the larger one every time."""

        old = fully_read("Smarkets", days_ago=STALE_AFTER_DAYS + 10)
        row = next(t for t in compare(old, fully_read("William Hill"), now=NOW).topics
                   if t.topic == "abandonment")

        assert row.status != UNREAD
        assert "Re-read" in row.detail and "https://" in row.detail

    def test_a_reading_inside_the_window_is_not_stale(self):
        fresh = fully_read("Smarkets", days_ago=STALE_AFTER_DAYS - 10)

        assert compare(fresh, fully_read("William Hill"), now=NOW).verdict == COVERED


class TestADeclarationCanBeOvertakenByTheEvidence:
    def test_a_clause_read_after_the_declaration_supersedes_it(self):
        """The failure this field exists for. Somebody compares two clauses on the 10th;
        one is re-read on the 20th and has changed; the declaration is still in the config
        passing the gate, and it is now about words that are no longer on the page."""

        comparison = compare(
            fully_read("Smarkets", days_ago=1), fully_read("William Hill", days_ago=1),
            now=NOW, pair_declared_at=stamp(30))

        assert comparison.verdict == INCOMPLETE
        assert "SUPERSEDED" in comparison.describe()
        assert "declare it again" in comparison.superseded_declaration

    def test_a_declaration_made_after_the_readings_still_stands(self):
        comparison = compare(
            fully_read("Smarkets", days_ago=30), fully_read("William Hill", days_ago=30),
            now=NOW, pair_declared_at=stamp(1))

        assert comparison.superseded_declaration == ""
        assert comparison.verdict == COVERED


class TestOneQuestionIsOnlyTheSameQuestionWithinOneMarketType:
    def test_comparing_two_market_types_is_refused_rather_than_answered(self):
        """"Does extra time count" means something in knockout football and nothing in
        tennis. Comparing across types would produce tidy IDENTICAL rows about topics that
        are not the same topic."""

        tennis = Rulebook("Smarkets", "tennis/h2h", ())
        with pytest.raises(ValueError, match="only the same question within one market"):
            compare(tennis, Rulebook("William Hill", FOOTBALL, ()), now=NOW)


class TestTheStoreRemembersOrSaysItCannot:
    def test_an_unreadable_store_refuses_to_be_overwritten(self, tmp_path):
        """Saving through an unreadable store would discard every clause somebody has
        already gone and looked up — the most expensive kind of write in this module,
        because the data is somebody's evenings rather than a re-fetchable API result."""

        path = tmp_path / "rulebooks.json"
        path.write_text("{not json", encoding="utf-8")
        store = RulebookStore.load(path)

        assert store.readable is False
        with pytest.raises(RuntimeError, match="already gone and looked up"):
            store.save()

    def test_an_unreadable_store_is_not_an_empty_one(self, tmp_path):
        path = tmp_path / "rulebooks.json"
        path.write_text("{not json", encoding="utf-8")

        described = RulebookStore.load(path).describe()

        assert "UNREADABLE" in described
        assert "not a finding that no rules have been recorded" in described

    def test_an_empty_store_says_it_blocks_the_lane_by_design(self, tmp_path):
        described = RulebookStore.load(tmp_path / "rulebooks.json").describe()

        assert "blocks the arb lane by design" in described

    def test_a_recorded_clause_survives_a_round_trip(self, tmp_path):
        path = tmp_path / "rulebooks.json"
        store = RulebookStore.load(path)
        store.record(clause("Smarkets", "abandonment", "all bets void"))
        store.declare(declaration("abandonment", alike=True))
        store.save(when="2026-08-29T12:00:00Z")

        reloaded = RulebookStore.load(path)

        assert reloaded.books() == ("Smarkets",)
        assert reloaded.rulebook("Smarkets", FOOTBALL).clause(
            "abandonment").verbatim == "all bets void"
        assert reloaded.declarations[0].settle_alike is True

    def test_a_store_written_and_then_lost_is_lost_rather_than_fresh(self, tmp_path):
        """Safe for the lane either way — everything reads UNREAD, which blocks. Wrong
        about a person's time: it sends them to re-read pages they already read."""

        path = tmp_path / "rulebooks.json"
        store = RulebookStore.load(path)
        store.record(clause("Smarkets", "abandonment", "void"))
        store.save(when="2026-08-29T12:00:00Z")
        path.unlink()

        lost = RulebookStore.load(path)

        assert lost.lost is True
        assert "the record was not kept" in lost.describe()

    def test_a_book_with_nothing_recorded_returns_an_empty_rulebook_not_none(self, tmp_path):
        """None would send a caller reaching for a default, and the default for "what does
        this book's abandonment rule say" is the one thing that must not exist."""

        book = RulebookStore.load(tmp_path / "x.json").rulebook("Smarkets", FOOTBALL)

        assert book.clauses == ()
        assert book.unread(disqualifying_only=True) == DISQUALIFYING


class TestTheTopicsThemselves:
    def test_every_topic_says_why_it_is_worth_reading_a_page_for(self):
        """Each entry is a page somebody has to read for every book they use, so one that
        has never decided anything is a tax on the job this module needs done."""

        for topic in TOPICS:
            assert topic.question.endswith("?")
            assert len(topic.why) > 80

    def test_abandonment_is_first_because_it_is_the_one_that_happened(self):
        assert TOPICS[0].key == "abandonment"
        assert TOPICS[0].disqualifying is True


class TestTheCommandAPersonActuallyTypes:
    """`rulebook.py` is where the evening's reading goes. Its exit codes have to mean
    what every other command here means, or a scheduler learns the wrong lesson from it."""

    def test_the_shipped_example_records_without_being_edited_first(self, tmp_path):
        """An example that has to be hand-repaired before it parses is an example people
        stop trusting, and this one carries `_note` keys explaining itself."""

        import rulebook as cli

        code = cli.main(["--store", str(tmp_path / "r.json"),
                         "--record", "examples/arb/rulebook.example.json"])

        assert code == 0
        assert RulebookStore.load(tmp_path / "r.json").books() == (
            "Smarkets", "William Hill")

    def test_a_bad_clause_writes_nothing_at_all(self, tmp_path):
        """All or nothing. Half a file applied leaves the operator unsure which half, and
        the cheapest way to find out is re-reading pages they have already read."""

        import rulebook as cli

        path = tmp_path / "in.json"
        path.write_text('{"clauses": [{"book": "A", "market_type": "soccer/h2h", '
                        '"topic": "abandonment", "verbatim": "void", "source_url": "", '
                        '"read_by": "Ian McGuane", "read_at": "2026-08-29"}]}',
                        encoding="utf-8")

        code = cli.main(["--store", str(tmp_path / "r.json"), "--record", str(path)])

        assert code == 2
        assert not (tmp_path / "r.json").exists()

    def test_an_empty_store_exits_two_rather_than_zero(self, tmp_path, capsys):
        """Exit 2 is this repository's "nothing was examined", and a store with fewer than
        two books has examined nothing. A scheduler reading 0 would call it a clean run."""

        import rulebook as cli

        assert cli.main(["--store", str(tmp_path / "r.json")]) == 2
        assert "INDETERMINATE on every candidate" in capsys.readouterr().out

    def test_a_declared_divergence_exits_one_rather_than_two(self, tmp_path):
        """1 means there is a finding for a person; 2 means nothing was looked at. A pair
        of books established NOT to settle alike is a finding, and a real one."""

        import rulebook as cli

        store = RulebookStore.load(tmp_path / "r.json")
        for book, wording in (("Smarkets", "void"), ("William Hill", "stands")):
            for topic in DISQUALIFYING:
                store.record(clause(book, topic, f"{wording} on {topic}"))
        store.declare(declaration("abandonment", alike=False))
        store.save(when="2026-08-29T12:00:00Z")

        code = cli.main(["--store", str(tmp_path / "r.json"),
                         "--compare", "Smarkets", "William Hill"])

        assert code == 1
