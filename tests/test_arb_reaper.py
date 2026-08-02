"""The arb lane's ceiling is INDETERMINATE until a person reads two books' rules.

That is the property this file exists to hold. Everything else here — freshness, two
counterparties, a complete book, a positive margin — a feed can establish, and settlement
equivalence is the one it cannot and the one that has actually cost money. So the lane runs
fully, finds candidates, and stops at exactly the stage where a human judgement is required,
naming which declaration is missing rather than reporting nothing found.

The second property is that the diversified combination is taken where one exists, and what
it cost in margin is stated rather than absorbed. Two legs at one bookmaker is one
restriction away from an unhedged single bet, and soft books restrict arbitrage accounts as
routine business.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.arb import EquivalenceDeclaration
from lib.arbfind import Quote, find_arb
from lib.arb_reaper import (
    ANY_BOOKS,
    Reading,
    StandingAuthority,
    books_key,
    build_arb_reaper,
    declaration_for,
    gates_for,
    measure_slip,
    screen_candidate,
    size_candidate,
    starts_at_from_market,
)
from lib.candidates import INDETERMINATE, REFUSED, SURFACED
from lib.reaper import COULD_NOT_LOOK, NOTHING_FOUND, READY, Unworthy
from lib.reaper import REFUSED as HARVEST_REFUSED

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
KICKOFF = "2026-08-09T14:00:00Z"
MARKET = f"Arsenal v Chelsea @ {KICKOFF}"
THREE = ("Arsenal", "Draw", "Chelsea")


def stamp(seconds_ago: int = 0) -> str:
    return (NOW - timedelta(seconds=seconds_ago)).isoformat(timespec="seconds")


def declaration(by="Ian McGuane"):
    return EquivalenceDeclaration(
        by, "read both books' abandonment and non-runner rules for football win/draw/win",
        ("abandonment", "non-runner"),
    )


def authority(limit=500.0, **kw):
    return StandingAuthority(
        declared_by=kw.pop("declared_by", "Ian McGuane"),
        reasoning=("two books disagree by more than the cost of taking both sides; this "
                   "makes no claim about the fixture"),
        considered=("a book restricts the account", "a leg is voided", "a price moves"),
        expires_at=(NOW + timedelta(days=30)).isoformat(timespec="seconds"),
        max_exposure=limit, **kw,
    )


def quotes(*, concentrated=True, at=None):
    """A genuine three-way arb. bet365 is cheapest on two legs; three books can cover it."""

    when = at or stamp()
    priced = [
        Quote("bet365", MARKET, "Arsenal", 2.45, when),
        Quote("Sky Bet", MARKET, "Arsenal", 2.40, when),
        Quote("bet365", MARKET, "Chelsea", 3.70, when),
        Quote("Paddy Power", MARKET, "Chelsea", 3.60, when),
        Quote("Sky Bet", MARKET, "Draw", 4.20, when),
        Quote("Paddy Power", MARKET, "Draw", 4.10, when),
    ]
    if concentrated:
        return priced
    return [q for q in priced if (q.book, q.selection) in {
        ("bet365", "Arsenal"), ("Sky Bet", "Draw"), ("Paddy Power", "Chelsea")}]


def candidate(**kw):
    return find_arb(MARKET, THREE, quotes(**kw))


class TestSettlementIsThePreconditionNotADimension:
    def test_without_a_declaration_the_cascade_is_indeterminate_not_refused(self):
        """"I could not read the rules" and "the rules say no" call for different things."""

        assert screen_candidate(candidate(), now=NOW).verdict == INDETERMINATE

    def test_it_is_the_deciding_stage_and_names_the_missing_key(self):
        screened = screen_candidate(candidate(), now=NOW)

        assert screened.decided_by.name == "settlement equivalence"
        assert "Paddy Power|Sky Bet|bet365" in screened.decided_by.detail

    def test_the_key_names_the_books_that_will_be_PLACED_not_the_cheapest_ones(self):
        """The cheapest combination here is two books; the lane places three.

        Screening one and placing the other would check a declaration covering bet365 and
        Sky Bet, then put a third of the money on Paddy Power's terms unread.
        """

        cheapest = {q.book for q in candidate().quotes}
        screened = screen_candidate(candidate(), now=NOW)

        assert cheapest == {"Sky Bet", "bet365"}
        assert "Paddy Power" in screened.decided_by.detail

    def test_with_diversification_off_the_key_is_the_cheapest_pair(self):
        screened = screen_candidate(candidate(), now=NOW, prefer_distinct_books=False)

        assert "Sky Bet|bet365" in screened.decided_by.detail
        assert "Paddy Power" not in screened.decided_by.detail

    def test_a_declaration_lets_the_cascade_surface(self):
        from lib.arb_reaper import chosen_quotes

        placed = chosen_quotes(candidate())
        declarations = {books_key([q.book for q in placed]): declaration()}

        assert screen_candidate(candidate(), declarations=declarations,
                                now=NOW).verdict == SURFACED

    def test_it_is_first_so_a_position_that_cannot_settle_is_never_priced(self):
        stages = screen_candidate(candidate(), now=NOW).stages

        assert stages[0].name == "settlement equivalence"
        assert stages[0].disqualifying

    def test_automation_cannot_declare_it(self):
        with pytest.raises(ValueError, match="named human"):
            EquivalenceDeclaration("agent:arb-reaper", "they look the same to me")


class TestTheDeclarationLookupIsExact:
    def test_a_declaration_for_other_books_does_not_cover_these(self):
        assert declaration_for(["bet365", "Sky Bet"],
                               {"Betfair|Smarkets": declaration()}) is None

    def test_order_does_not_matter(self):
        found = declaration_for(["Sky Bet", "bet365"], {"Sky Bet|bet365": declaration()})

        assert found is not None

    def test_an_any_books_declaration_is_possible_and_explicit(self):
        assert declaration_for(["anything"], {ANY_BOOKS: declaration()}) is not None

    def test_no_declarations_at_all_is_not_a_match(self):
        assert declaration_for(["bet365"], None) is None


class TestTheRestOfTheCascade:
    def _declared(self, cand):
        return screen_candidate(cand, declarations={ANY_BOOKS: declaration()}, now=NOW)

    def test_stale_prices_are_refused_rather_than_priced(self):
        screened = self._declared(candidate(at=stamp(seconds_ago=600)))

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "price freshness"
        assert "arithmetic, not an opportunity" in screened.decided_by.detail

    def test_legs_observed_far_apart_are_refused_even_when_the_newest_is_fresh(self):
        spread = [
            Quote("bet365", MARKET, "Arsenal", 2.45, stamp(seconds_ago=20)),
            Quote("Sky Bet", MARKET, "Draw", 4.20, stamp(seconds_ago=600)),
            Quote("Paddy Power", MARKET, "Chelsea", 3.70, stamp(seconds_ago=40)),
        ]

        screened = self._declared(find_arb(MARKET, THREE, spread))

        assert screened.verdict == REFUSED
        assert "different moments rather than a combination" in screened.decided_by.detail

    def test_an_unreadable_timestamp_is_indeterminate_not_stale(self):
        undated = [
            Quote("bet365", MARKET, "Arsenal", 2.45, ""),
            Quote("Sky Bet", MARKET, "Draw", 4.20, ""),
            Quote("Paddy Power", MARKET, "Chelsea", 3.70, ""),
        ]

        assert self._declared(find_arb(MARKET, THREE, undated)).verdict == INDETERMINATE

    def test_one_book_pricing_every_leg_is_one_counterparty(self):
        alone = [
            Quote("bet365", MARKET, "Arsenal", 2.45, stamp()),
            Quote("bet365", MARKET, "Draw", 4.20, stamp()),
            Quote("bet365", MARKET, "Chelsea", 3.70, stamp()),
        ]

        screened = self._declared(
            find_arb(MARKET, THREE, alone, allow_single_book=True))

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "two counterparties"

    def test_an_ordinary_market_is_refused_on_margin(self):
        ordinary = [
            Quote("bet365", MARKET, "Arsenal", 2.00, stamp()),
            Quote("Sky Bet", MARKET, "Draw", 3.00, stamp()),
            Quote("Paddy Power", MARKET, "Chelsea", 3.00, stamp()),
        ]

        screened = self._declared(find_arb(MARKET, THREE, ordinary))

        assert screened.decided_by.name in {"complete book", "margin after commission"}
        assert screened.verdict == REFUSED


class TestTheGatesAreOnlyPreconditions:
    def test_a_missing_declaration_blocks(self):
        readings = gates_for(candidate(), now=NOW)

        assert readings[0].status == "SETTLEMENT_RULES_NOT_DECLARED"
        assert readings[0].blocking

    def test_a_market_with_no_readable_start_time_blocks(self):
        """An exchange market called 1.234567 carries no kickoff, and unknown is not fine."""

        anonymous = find_arb("1.234567", THREE, [
            Quote("bet365", "1.234567", "Arsenal", 2.45, stamp()),
            Quote("Sky Bet", "1.234567", "Draw", 4.20, stamp()),
            Quote("Paddy Power", "1.234567", "Chelsea", 3.70, stamp()),
        ])

        statuses = {r.status for r in gates_for(
            anonymous, declarations={ANY_BOOKS: declaration()}, now=NOW)}

        assert "EVENT_START_UNKNOWN" in statuses

    def test_a_started_event_blocks(self):
        after = NOW + timedelta(hours=3)

        statuses = {r.status for r in gates_for(
            candidate(), declarations={ANY_BOOKS: declaration()}, now=after)}

        assert "EVENT_ALREADY_STARTED" in statuses

    def test_an_unreadable_seen_register_blocks(self):
        lost = type("R", (), {"readable": False})()

        statuses = {r.status for r in gates_for(
            candidate(), declarations={ANY_BOOKS: declaration()}, register=lost, now=NOW)}

        assert "SEEN_REGISTER_UNREADABLE" in statuses

    def test_a_clean_candidate_produces_no_gate_readings(self):
        assert gates_for(candidate(), declarations={ANY_BOOKS: declaration()},
                         now=NOW) == ()

    def test_blocking_is_stated_rather_than_spelled_into_the_status(self):
        """So whether a gate halts a lane never depends on how a constant was named."""

        from lib.reaper import gate_findings

        assert gate_findings([Reading("LOOKS_FINE", "but it is not", blocking=True)])
        assert gate_findings([Reading("NOT_A_PROBLEM", "really", blocking=False)]) == []


class TestSizingTakesTheSpreadCombination:
    def test_one_book_per_leg_is_used_when_one_exists(self):
        slip = size_candidate(candidate(), bankroll_limit=500.0)

        assert len({leg.book for leg in slip.legs}) == 3

    def test_what_diversifying_cost_is_stated_on_the_slip(self):
        slip = size_candidate(candidate(), bankroll_limit=500.0)

        assert "costing +0.751% of margin" in slip.reason
        assert "costing +0.751% of margin" in slip.describe()

    def test_it_can_be_switched_off_and_then_doubles_up(self):
        slip = size_candidate(candidate(), bankroll_limit=500.0,
                              prefer_distinct_books=False)

        assert slip.concentrated_books == ("bet365",)

    def test_a_slip_under_the_return_floor_is_a_measured_refusal_not_a_gap(self):
        """Unworthy, not None. "Not worth it" is not "I could not work it out"."""

        result = size_candidate(candidate(), bankroll_limit=500.0,
                                minimum_return_pct=99.0)

        assert isinstance(result, Unworthy)
        assert "the slip refused it" in result.reason

    def test_the_bankroll_binds_the_total(self):
        slip = size_candidate(candidate(), bankroll_limit=100.0)

        assert slip.total_stake <= 100.0

    def test_an_unread_maximum_does_not_bind_and_says_so(self):
        slip = size_candidate(candidate(), bankroll_limit=500.0)

        assert all(not leg.stake_is_confirmed for leg in slip.legs)

    def test_the_breakers_are_handed_the_stake_and_the_return(self):
        slip = size_candidate(candidate(), bankroll_limit=500.0)

        size, edge = measure_slip(slip)

        assert size == pytest.approx(slip.total_stake)
        assert edge == pytest.approx(slip.return_pct)


class TestTheStandingGrantRecordsWhatItSkipped:
    def test_it_mints_a_thesis_whose_subject_is_the_market(self):
        assert authority().thesis_for(MARKET).subject == MARKET

    def test_every_minted_thesis_says_nobody_looked_at_this_market(self):
        minted = authority().thesis_for(MARKET)

        assert any("standing grant" in item for item in minted.considered)

    def test_the_human_stays_named_on_it(self):
        assert authority().thesis_for(MARKET).declared_by == "Ian McGuane"

    def test_automation_cannot_hold_a_standing_grant_either(self):
        """And it fails where the grant is DECLARED, not per market inside reap()."""

        with pytest.raises(ValueError, match="cannot hold a standing authority"):
            authority(declared_by="agent:arb-reaper")

    def test_an_unnamed_grant_is_refused(self):
        with pytest.raises(ValueError, match="named author"):
            authority(declared_by="   ")


class TestTheLaneEndToEnd:
    class Feed:
        is_configured = True

        def __init__(self, priced=None, raises=False):
            self.priced = quotes() if priced is None else priced
            self.raises = raises

        def quotes(self, _sport, market=""):
            if self.raises:
                raise RuntimeError("feed down")
            return self.priced

    def _breakers(self, tmp_path, balance=20_000.0):
        from lib.breakers import Breakers, Ringfence

        return Breakers(Ringfence("arb", balance), tmp_path / "b.json",
                        kill_switch=tmp_path / "HALT")

    def _reaper(self, tmp_path, *, declarations=None, feed=None, **kw):
        return build_arb_reaper(
            authority=authority(), breakers=self._breakers(tmp_path),
            sports=("soccer_epl",), declarations=declarations,
            source=feed if feed is not None else self.Feed(),
            now=lambda: NOW, **kw)

    def test_it_reaches_ready_with_a_declaration_on_file(self, tmp_path):
        harvest = self._reaper(tmp_path,
                               declarations={ANY_BOOKS: declaration()}).reap()[0]

        assert harvest.status == READY
        assert harvest.instruction.total_stake > 0

    def test_ready_still_says_nothing_has_been_placed(self, tmp_path):
        described = self._reaper(
            tmp_path, declarations={ANY_BOOKS: declaration()}).reap()[0].describe()

        assert "NOTHING HAS BEEN PLACED" in described
        assert "No board was convened" in described

    def test_without_a_declaration_it_stops_at_indeterminate(self, tmp_path):
        from lib.reaper import INDETERMINATE as HARVEST_INDETERMINATE

        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == HARVEST_INDETERMINATE
        assert harvest.instruction is None

    def test_the_indeterminate_harvest_names_the_declaration_to_go_and_get(self, tmp_path):
        """Otherwise the lane's most useful output is "a stage was not measured"."""

        harvest = self._reaper(tmp_path).reap()[0]

        assert "settlement equivalence" in harvest.reason
        assert "Paddy Power|Sky Bet|bet365" in harvest.reason

    def test_an_unconfigured_source_could_not_look(self, tmp_path):
        blank = type("F", (), {"is_configured": False})()

        harvest = self._reaper(tmp_path, feed=blank).reap()[0]

        assert harvest.status == COULD_NOT_LOOK
        assert "not a finding that no arb exists" in harvest.reason

    def test_every_sport_failing_is_could_not_look_not_nothing_found(self, tmp_path):
        harvest = self._reaper(tmp_path, feed=self.Feed(raises=True)).reap()[0]

        assert harvest.status == COULD_NOT_LOOK

    def test_a_quiet_market_is_nothing_found_with_its_coverage(self, tmp_path):
        ordinary = [
            Quote("bet365", MARKET, "Arsenal", 2.00, stamp()),
            Quote("Sky Bet", MARKET, "Draw", 3.00, stamp()),
            Quote("Paddy Power", MARKET, "Chelsea", 3.00, stamp()),
        ]

        harvest = self._reaper(tmp_path, feed=self.Feed(ordinary)).reap()[0]

        assert harvest.status == NOTHING_FOUND
        assert "1 of 1 source(s) answered" in harvest.describe()

    def test_the_kill_switch_stops_a_declared_clean_candidate(self, tmp_path):
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")

        harvest = self._reaper(tmp_path,
                               declarations={ANY_BOOKS: declaration()}).reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "kill switch" in harvest.reason

    def test_a_stake_over_the_ringfence_cap_is_refused_after_sizing(self, tmp_path):
        """5% of a 100 balance is 5, and the slip sizes to the standing grant's 500."""

        reaper = build_arb_reaper(
            authority=authority(), breakers=self._breakers(tmp_path, balance=100.0),
            sports=("soccer_epl",), declarations={ANY_BOOKS: declaration()},
            source=self.Feed(), now=lambda: NOW)

        harvest = reaper.reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "position size" in harvest.reason
        assert harvest.instruction is not None


class TestStartTimeParsing:
    def test_the_aggregator_naming_convention_is_read(self):
        assert starts_at_from_market(MARKET).hour == 14

    def test_an_exchange_id_yields_none_rather_than_a_guess(self):
        assert starts_at_from_market("1.234567") is None

    def test_an_unparseable_tail_yields_none(self):
        assert starts_at_from_market("Arsenal v Chelsea @ soon") is None
