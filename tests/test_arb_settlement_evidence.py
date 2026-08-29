"""The arb lane's first gate must be able to look underneath the sentence it rests on.

`tests/test_arb_reaper.py` holds the property that the lane stops at settlement equivalence
until a person declares it. This file holds the next one: that the declaration is checked
against what that person actually read.

Until now the two states were "a declaration exists" and "one does not", and the first of
those covered three quite different situations that a holder would act on differently:

    nothing recorded at all      the sentence is all there is
    recorded and it agrees       the clauses were read, they match, the lock is backed
    recorded and it DISAGREES    the clauses were read and one of them says otherwise

The third is the one worth the whole file. A declaration contradicted by the clauses
somebody read is not a satisfied precondition — it is a judgement that needs making again,
and passing it would be this repository's founding defect in the one gate that has actually
cost money: an unread rule and a rule read and found to differ, reported alike.

The compatibility property is here too, and it is deliberate rather than an oversight. A
lane with no rulebook store attached behaves exactly as it did before rulebooks existed. A
change that started refusing every previously-working configuration on the day the evidence
layer arrived would be a change people work around by switching it off, and then nothing is
checked at all.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lib.arb import EquivalenceDeclaration
from lib.arbfind import Quote, find_arb
from lib.arb_reaper import gates_for, rulebook_evidence, screen_candidate
from lib.candidates import INDETERMINATE, PASSED, REFUSED, SURFACED
from lib.rulebook import (
    COVERED,
    DISQUALIFYING,
    INCOMPLETE,
    Clause,
    RulebookStore,
    TopicDeclaration,
)

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
KICKOFF = "2026-08-29T14:00:00Z"
MARKET = f"Arsenal v Chelsea @ {KICKOFF}"
BOTH = ("Arsenal", "Chelsea")
FOOTBALL = "soccer/h2h"


def stamp(seconds_ago: int = 0) -> str:
    return (NOW - timedelta(seconds=seconds_ago)).isoformat(timespec="seconds")


def day(days_ago: int = 1) -> str:
    return (NOW - timedelta(days=days_ago)).date().isoformat()


def candidate(*, market_type: str = FOOTBALL):
    """A two-book, two-way arb at Smarkets and William Hill."""

    when = stamp()
    return find_arb(MARKET, BOTH, [
        Quote("Smarkets", MARKET, "Arsenal", 2.30, when, market_type=market_type),
        Quote("William Hill", MARKET, "Chelsea", 2.10, when, market_type=market_type),
    ])


def pair_declaration(declared_days_ago: int = 1) -> EquivalenceDeclaration:
    return EquivalenceDeclaration(
        "Ian McGuane",
        "read both books' football win/draw/win settlement pages on the same evening",
        ("abandonment", "postponement"),
        day(declared_days_ago),
    )


def declarations() -> dict:
    return {"Smarkets|William Hill": pair_declaration()}


def store(tmp_path, *, wording=("void", "void"), days_ago: int = 1,
          topic_declarations=(), skip: tuple[str, ...] = ()) -> RulebookStore:
    """A store where both books are read on every disqualifying topic."""

    kept = RulebookStore.load(tmp_path / "rulebooks.json")
    for book, words in zip(("Smarkets", "William Hill"), wording):
        for topic in DISQUALIFYING:
            if topic in skip:
                continue
            kept.record(Clause(
                book=book, market_type=FOOTBALL, topic=topic,
                verbatim=f"{words} on {topic}",
                source_url=f"https://{book.split()[0].lower()}.example/rules",
                read_by="Ian McGuane", read_at=day(days_ago)))
    for declaration in topic_declarations:
        kept.declare(declaration)
    return kept


def topic_declaration(topic: str, *, alike: bool) -> TopicDeclaration:
    return TopicDeclaration(
        book_a="Smarkets", book_b="William Hill", topic=topic, settle_alike=alike,
        declared_by="Ian McGuane",
        reasoning="worked a 2-0 abandonment at 70 minutes through both books' wording",
        declared_at=day(1),
        scenarios_checked=("abandoned at 70 minutes and replayed within 48 hours",),
    )


def settlement(found, **kwargs):
    screened = screen_candidate(found, now=NOW, **kwargs)
    return next(s for s in screened.stages if s.name == "settlement equivalence")


class TestADeclarationWithNothingUnderItStillPassesAndSaysSo:
    """Backwards compatibility, stated as a property rather than left implicit."""

    def test_a_lane_with_no_store_behaves_as_it_did_before_rulebooks_existed(self):
        stage = settlement(candidate(), declarations=declarations())

        assert stage.verdict == PASSED

    def test_and_the_stage_says_there_is_nothing_underneath_it(self):
        """The honesty this buys. The gate passes on one sentence, and the report now
        states that it is one sentence, so nobody reads a backed lock into it."""

        stage = settlement(candidate(), declarations=declarations())

        assert "no rulebook store is attached" in stage.detail
        assert "no clause, no URL and no reading date behind it" in stage.detail

    def test_no_declaration_at_all_is_still_indeterminate(self):
        stage = settlement(candidate(), rulebooks=None)

        assert stage.verdict == INDETERMINATE
        assert "no declaration covers" in stage.detail


class TestTheRecordCanContradictTheDeclaration:
    def test_a_declared_divergence_refuses_rather_than_leaving_it_open(self, tmp_path):
        """The case the file exists for. Somebody read both pages and wrote down that they
        differ; a pair declaration in the config says otherwise. The clauses win, because
        the clauses are the evidence and the config line is the claim."""

        kept = store(tmp_path, wording=("void", "stands"), topic_declarations=(
            topic_declaration("abandonment", alike=False),))

        stage = settlement(candidate(), declarations=declarations(), rulebooks=kept)

        assert stage.verdict == REFUSED
        assert "THE RECORDED RULES SAY OTHERWISE" in stage.detail
        assert "a judgement to make again" in stage.detail

    def test_a_refused_settlement_stage_refuses_the_whole_candidate(self, tmp_path):
        """The stage is disqualifying, so this asserts the cascade honours it rather than
        surfacing a candidate whose legs are known to settle differently."""

        kept = store(tmp_path, wording=("void", "stands"), topic_declarations=(
            topic_declaration("abandonment", alike=False),))

        screened = screen_candidate(candidate(), declarations=declarations(),
                                    rulebooks=kept, now=NOW)

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "settlement equivalence"

    def test_an_unread_topic_leaves_the_declaration_unestablished(self, tmp_path):
        """Not disbelieved. Unestablished — and this repository's standing rule is that an
        unestablished precondition is not a satisfied one."""

        kept = store(tmp_path, skip=("extra_time",))

        stage = settlement(candidate(), declarations=declarations(), rulebooks=kept)

        assert stage.verdict == INDETERMINATE
        assert "extra_time" in stage.detail
        assert "not being disbelieved" in stage.detail

    def test_a_fully_read_matching_pair_passes_and_says_what_it_rests_on(self, tmp_path):
        stage = settlement(candidate(), declarations=declarations(),
                           rulebooks=store(tmp_path))

        assert stage.verdict == PASSED
        assert "Backed by the rulebook" in stage.detail
        assert FOOTBALL in stage.detail

    def test_a_backed_candidate_surfaces(self, tmp_path):
        screened = screen_candidate(candidate(), declarations=declarations(),
                                    rulebooks=store(tmp_path), now=NOW)

        assert screened.verdict == SURFACED


class TestTheGatesAskAgainRatherThanTrustingTheCascade:
    """Two checks of one precondition, on purpose.

    The cascade decides whether to surface and the gates decide whether the thesis may
    authorise. A precondition enforced in one and not the other is a hole exactly the width
    of whichever check somebody remembered to run, and `lib.reaper` runs both.
    """

    def test_a_divergence_reaches_the_gates_as_a_blocking_reading(self, tmp_path):
        kept = store(tmp_path, wording=("void", "stands"), topic_declarations=(
            topic_declaration("abandonment", alike=False),))

        readings = gates_for(candidate(), declarations=declarations(), rulebooks=kept,
                             now=NOW)

        assert any(r.status == "SETTLEMENT_RULES_DIVERGE" for r in readings)

    def test_an_incomplete_record_reaches_the_gates_as_a_blocking_reading(self, tmp_path):
        readings = gates_for(candidate(), declarations=declarations(),
                             rulebooks=store(tmp_path, skip=("extra_time",)), now=NOW)

        assert any(r.status == "SETTLEMENT_RULES_NOT_ESTABLISHED" for r in readings)

    def test_a_backed_pair_adds_no_reading_at_all(self, tmp_path):
        readings = gates_for(candidate(), declarations=declarations(),
                             rulebooks=store(tmp_path), now=NOW)

        assert [r.status for r in readings] == []


class TestWhichRulesApplyIsItselfAPrecondition:
    def test_a_quote_with_no_market_type_leaves_settlement_unestablished(self, tmp_path):
        """The most easily missed failure here. With no market type the store is queried
        for rules that cannot match and answers UNREAD, which reads as "go and read the
        pages" when the real problem is that the lane does not know which pages."""

        verdict, detail = rulebook_evidence(
            ("Smarkets", "William Hill"), "", rulebooks=store(tmp_path), now=NOW)

        assert verdict == INCOMPLETE
        assert "the market type is not established" in detail

    def test_legs_claiming_different_market_types_report_none(self):
        """Not the first leg's type, and not a guess. A combination whose legs disagree
        about what kind of market this is cannot have its rules looked up at all."""

        when = stamp()
        mixed = find_arb(MARKET, BOTH, [
            Quote("Smarkets", MARKET, "Arsenal", 2.30, when, market_type=FOOTBALL),
            Quote("William Hill", MARKET, "Chelsea", 2.10, when,
                  market_type="tennis/h2h"),
        ])

        assert mixed.market_type == ""

    def test_the_feed_names_the_sport_rather_than_the_competition(self):
        """One set of football rules covers the leagues a book takes bets on. Keying per
        competition would multiply the reading job by the number of leagues scanned and
        guarantee almost nothing was ever read."""

        from connectors.oddsapi import market_type_for

        assert market_type_for("soccer_epl", "h2h") == "soccer/h2h"
        assert market_type_for("soccer_efl_cup", "h2h") == "soccer/h2h"
        assert market_type_for("", "h2h") == ""


class TestEveryPairIsComparedNotJustTheFirstTwo:
    def test_a_three_book_position_compares_all_three_pairs(self, tmp_path):
        """Two pairs agreeing establishes nothing about the third — and the third is the
        leg that voids on its own while the other two stand."""

        kept = store(tmp_path)
        for topic in DISQUALIFYING:
            kept.record(Clause(
                book="Paddy Power", market_type=FOOTBALL, topic=topic,
                verbatim=f"something else entirely on {topic}",
                source_url="https://paddypower.example/rules",
                read_by="Ian McGuane", read_at=day(1)))

        verdict, detail = rulebook_evidence(
            ("Paddy Power", "Smarkets", "William Hill"), FOOTBALL, rulebooks=kept,
            declaration=pair_declaration(), now=NOW)

        assert verdict == INCOMPLETE
        assert "Paddy Power vs Smarkets" in detail
        assert "Paddy Power vs William Hill" in detail

    def test_all_pairs_covered_is_covered(self, tmp_path):
        verdict, _ = rulebook_evidence(
            ("Smarkets", "William Hill"), FOOTBALL, rulebooks=store(tmp_path),
            declaration=pair_declaration(), now=NOW)

        assert verdict == COVERED


class TestAnUnreadableStoreCannotBuyTheNoStoreTreatment:
    def test_a_corrupt_store_is_incomplete_rather_than_absent(self, tmp_path):
        """`None` means "no evidence layer was asked for" and passes on the declaration
        alone. A file that fails to parse must not be able to reach that treatment by
        being broken — that is the direction this repository refuses to fail in."""

        path = tmp_path / "rulebooks.json"
        path.write_text("{not json", encoding="utf-8")

        stage = settlement(candidate(), declarations=declarations(),
                           rulebooks=RulebookStore.load(path))

        assert stage.verdict == INDETERMINATE
        assert "could not be read" in stage.detail

    def test_a_lost_store_is_incomplete_and_says_the_readings_existed(self, tmp_path):
        path = tmp_path / "rulebooks.json"
        kept = store(tmp_path)
        kept.save(when="2026-08-29T12:00:00Z")
        path.unlink()

        stage = settlement(candidate(), declarations=declarations(),
                           rulebooks=RulebookStore.load(path))

        assert stage.verdict == INDETERMINATE
        assert "LOST" in stage.detail


class TestADeclarationOlderThanTheReadingItRestsOn:
    def test_a_pair_declaration_predating_a_re_read_stops_the_lane(self, tmp_path):
        """The declaration was signed against wording that has since been read again. It
        may still be right; nobody has checked, and the gate must not assume."""

        kept = store(tmp_path, days_ago=1)
        old = {"Smarkets|William Hill": pair_declaration(declared_days_ago=30)}

        stage = settlement(candidate(), declarations=old, rulebooks=kept)

        assert stage.verdict == INDETERMINATE
        assert "SUPERSEDED" in stage.detail

    def test_a_declaration_made_after_the_readings_passes(self, tmp_path):
        kept = store(tmp_path, days_ago=30)
        recent = {"Smarkets|William Hill": pair_declaration(declared_days_ago=1)}

        stage = settlement(candidate(), declarations=recent, rulebooks=kept)

        assert stage.verdict == PASSED

    def test_an_undated_declaration_cannot_be_found_to_be_superseded(self, tmp_path):
        """Stated rather than hidden. `declared_at` is optional so that every existing
        config keeps working, and the cost of leaving it out is exactly this: the one
        check that catches a rules change happening after the judgement cannot run."""

        undated = {"Smarkets|William Hill": EquivalenceDeclaration(
            "Ian McGuane", "read both books' pages", ("abandonment",))}

        stage = settlement(candidate(), declarations=undated, rulebooks=store(tmp_path))

        assert stage.verdict == PASSED
        assert "SUPERSEDED" not in stage.detail
