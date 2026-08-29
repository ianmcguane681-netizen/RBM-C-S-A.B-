"""A lane that bets on a forecast must stop where the forecast stops being checkable.

`tests/test_mispricing.py` holds the model's own guards. This holds the lane's, and there is
one property here that matters more than the rest: **the ceiling is REFUSED while the model
is PAPER, and the refusal carries the numbers.**

That is not a placeholder. A model with no settled record has not been shown to be right
about anything, and every other guard in this system can be satisfied by a model that is
simply bad — the de-vig can be impeccable, the features all present, the error band
honestly stated, and the model still wrong about football. The only thing that establishes
otherwise is a run of settled outcomes, and the only way to accumulate one is for the lane
to publish what it WOULD have done. So `size` refuses with `Unworthy`, which the reaper
reports as REFUSED with the reason — a MEASURED refusal, not INDETERMINATE, because "I
worked it out and the model is not allowed to bet yet" and "I could not work out a size"
are different facts.

The second property is about vocabulary. An arb slip says LOCK and guaranteed return; this
lane may never borrow that language, because if the model is wrong the whole stake goes.
Several assertions below are about words for exactly that reason.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.arbfind import Quote
from lib.candidates import INDETERMINATE, REFUSED, SURFACED
from lib.mispricing import (
    KNOWN,
    LIVE,
    PROPORTIONAL,
    Evidence,
    Feature,
    GoalsModel,
    MispricingModel,
)
from lib.mispricing_reaper import (
    ValueTicket,
    build_mispricing_reaper,
    gates_for,
    kelly_stake,
    measure_ticket,
    mispricing_identity,
    opportunities_from,
    screen_opportunity,
    size_opportunity,
    thesis_from,
)
from lib.reaper import COULD_NOT_LOOK, NOTHING_FOUND, Unworthy
from lib.reaper import REFUSED as HARVEST_REFUSED

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
KICKOFF = "2026-08-29T18:00:00Z"
MARKET = f"Arsenal v Chelsea @ {KICKOFF}"
STRENGTHS = ("home_attack_strength", "home_defence_strength",
             "away_attack_strength", "away_defence_strength")


def stamp(seconds_ago: int = 0) -> str:
    return (NOW - timedelta(seconds=seconds_ago)).isoformat(timespec="seconds")


def model(**overrides) -> MispricingModel:
    settings = dict(
        name="poisson-v1", declared_by="Ian McGuane",
        reasoning="league scoring rates against the book's de-vigged price",
        requires=STRENGTHS, stated_error_pct=1.0, devig_method=PROPORTIONAL,
        expires_at="2099-01-01T00:00:00Z", max_exposure=50.0,
    )
    settings.update(overrides)
    return MispricingModel(**settings)


def live(**overrides) -> MispricingModel:
    return model(status=LIVE, promoted_on=(
        "142 settled predictions between 2026-03 and 2026-08, within 2.1 points of "
        "observed frequency in every decile"), **overrides)


def evidence(market: str = MARKET) -> Evidence:
    """A better home side. The model puts HOME near 60%, DRAW 20%, AWAY 20%."""

    return Evidence(market, (
        Feature("home_attack_strength", KNOWN, 1.25, source="test"),
        Feature("home_defence_strength", KNOWN, 0.85, source="test"),
        Feature("away_attack_strength", KNOWN, 0.95, source="test"),
        Feature("away_defence_strength", KNOWN, 1.05, source="test"),
    ), kickoff=KICKOFF)


def quotes(*, at=None, book: str = "Sky Bet"):
    """A market with a real 3.25% overround where HOME is priced too long.

    Every price here carries margin on purpose. A three-way book summing UNDER 100% is an
    arb, `devig` refuses it by name, and a fixture built out of one would have tested the
    wrong refusal in every case below.
    """

    when = at or stamp()
    return [
        Quote(book, MARKET, "HOME", 2.60, when),
        Quote(book, MARKET, "DRAW", 3.30, when),
        Quote(book, MARKET, "AWAY", 2.90, when),
    ]


def opportunity(*, declared=None, market_quotes=None, evidence_for=None, selection="HOME"):
    declared = declared or model()
    found = opportunities_from(
        market_quotes if market_quotes is not None else quotes(),
        model=declared, goals_model=GoalsModel(),
        evidence_for=evidence_for or (lambda m: evidence(m)), now=NOW)
    return next(o for o in found if o.selection == selection)


class TestThePaperCeiling:
    def test_a_paper_model_refuses_to_size_and_the_refusal_is_measured(self):
        """`Unworthy`, not None. INDETERMINATE would say a constraint could not be
        measured, when in fact everything was measured and the answer is no."""

        sized = size_opportunity(opportunity(), model=model(), bankroll=500.0)

        assert isinstance(sized, Unworthy)
        assert "is PAPER" in sized.reason

    def test_the_paper_refusal_carries_what_it_would_have_done(self):
        """The lane's entire output while it is paper. A refusal saying only "PAPER" would
        accumulate no record, and the record is what a person reads before promoting."""

        reason = size_opportunity(opportunity(), model=model(), bankroll=500.0).reason

        assert "would have staked on HOME" in reason
        assert "%" in reason and "expected" in reason
        assert "only a named person moves it" in reason

    def test_a_live_model_produces_a_ticket(self):
        ticket = size_opportunity(opportunity(), model=live(), bankroll=500.0)

        assert isinstance(ticket, ValueTicket)
        assert ticket.stake > 0

    def test_the_ticket_never_borrows_the_arb_lanes_vocabulary(self):
        """An arb slip says LOCK and guaranteed return. If this model is wrong about the
        fixture the whole stake goes, and the printed instruction has to say so."""

        printed = size_opportunity(opportunity(), model=live(), bankroll=500.0).describe()

        assert "THIS IS A BET, NOT A LOCK" in printed
        assert "guaranteed" not in printed.lower()
        assert "lock" not in printed.lower().replace("not a lock", "")

    def test_the_ticket_records_what_was_assumed_rather_than_known(self):
        printed = size_opportunity(opportunity(), model=live(), bankroll=500.0).describe()

        assert "ASSUMED:" in printed
        assert "The book is not making that assumption" in printed


class TestSizing:
    def test_kelly_is_zero_rather_than_negative_when_there_is_no_edge(self):
        """A negative Kelly is an instruction to back the other side, which is a different
        bet at a different price that nobody has evaluated."""

        assert kelly_stake(0.10, 2.0, 1000.0) == 0.0

    def test_kelly_scales_with_the_declared_fraction(self):
        full = kelly_stake(0.60, 2.0, 1000.0, fraction=1.0)
        quarter = kelly_stake(0.60, 2.0, 1000.0, fraction=0.25)

        assert quarter == pytest.approx(full * 0.25)

    def test_the_models_exposure_limit_binds_when_it_is_tighter_than_kelly(self):
        ticket = size_opportunity(opportunity(), model=live(max_exposure=5.0),
                                  bankroll=100_000.0)

        assert ticket.stake <= 5.0
        assert "exposure limit" in ticket.bound_by

    def test_a_stake_under_the_minimum_is_refused_as_rounding(self):
        sized = size_opportunity(opportunity(), model=live(max_exposure=0.5),
                                 bankroll=10.0)

        assert isinstance(sized, Unworthy)
        assert "rounding rather than a position" in sized.reason

    def test_an_unread_book_limit_is_a_note_rather_than_an_unmeasured_constraint(self):
        """This differs from the arb lane on purpose. An arb leg only partly accepted
        leaves the other leg unhedged; a single bet only partly accepted is a smaller bet.
        Making it an unmeasured constraint here would make the lane INDETERMINATE forever,
        because no odds feed returns a book's limits."""

        ticket = size_opportunity(opportunity(), model=live(), bankroll=500.0)

        assert isinstance(ticket, ValueTicket)
        assert "Nobody read what this book will accept" in ticket.note

    def test_the_breakers_are_given_the_stake_and_the_claimed_edge(self):
        ticket = size_opportunity(opportunity(), model=live(), bankroll=500.0)

        size, edge = measure_ticket(ticket)

        assert size == ticket.stake
        assert edge == ticket.expected_value_pct


class TestTheCascade:
    def test_a_forecast_that_could_not_be_produced_leads_the_refusal(self):
        """The forecast leads because everything after it is arithmetic on a number that
        either exists or does not. A market refused on freshness before anybody asked
        whether the model could price it names the wrong thing."""

        blind = opportunity(evidence_for=lambda m: Evidence(m, kickoff=KICKOFF))

        screened = screen_opportunity(blind, model=model(), now=NOW)

        assert screened.verdict == INDETERMINATE
        assert screened.decided_by.name == "the model produced a forecast"
        assert "home_attack_strength" in screened.decided_by.detail

    def test_a_stale_price_is_refused(self):
        old = opportunity(market_quotes=quotes(at=stamp(7200)))

        screened = screen_opportunity(old, model=model(), now=NOW)

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "the price is current"

    def test_a_price_with_no_readable_time_is_indeterminate_rather_than_fresh(self):
        undated = opportunity(market_quotes=[
            Quote("Sky Bet", MARKET, "HOME", 2.60, ""),
            Quote("Sky Bet", MARKET, "DRAW", 3.30, ""),
            Quote("Sky Bet", MARKET, "AWAY", 2.90, ""),
        ])

        screened = screen_opportunity(undated, model=model(), now=NOW)

        assert screened.verdict == INDETERMINATE
        assert "not the same as recent" in screened.decided_by.detail

    def test_a_book_missing_a_selection_is_refused_rather_than_partly_devigged(self):
        """A margin cannot be removed from a market with a side missing, so the fair price
        of the sides that ARE quoted is unknown rather than slightly off."""

        partial = opportunities_from(
            [Quote("Sky Bet", MARKET, "HOME", 2.60, stamp()),
             Quote("Sky Bet", MARKET, "DRAW", 3.30, stamp()),
             Quote("Paddy Power", MARKET, "AWAY", 2.90, stamp())],
            model=model(), goals_model=GoalsModel(),
            evidence_for=lambda m: evidence(m), now=NOW)
        away = next(o for o in partial if o.book == "Paddy Power")

        screened = screen_opportunity(away, model=model(), now=NOW)

        assert screened.verdict in {REFUSED, INDETERMINATE}

    def test_an_edge_that_survives_the_doubt_surfaces(self):
        screened = screen_opportunity(opportunity(), model=model(), now=NOW)

        assert screened.verdict == SURFACED

    def test_a_refused_edge_names_the_band_it_failed_to_clear(self):
        """`stated_error_pct` at 40 points is absurd and is the point: the same fixture and
        the same price, refused because the model admits it does not know."""

        screened = screen_opportunity(
            opportunity(declared=model(stated_error_pct=40.0)),
            model=model(stated_error_pct=40.0), now=NOW)

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "the edge survives the doubt"
        assert "doubt band" in screened.decided_by.detail


class TestTheGates:
    def test_a_fixture_already_under_way_is_blocked(self):
        started = f"Arsenal v Chelsea @ {(NOW - timedelta(hours=1)).isoformat()}"
        found = opportunity(
            market_quotes=[Quote("Sky Bet", started, s, o, stamp())
                           for s, o in (("HOME", 2.6), ("DRAW", 3.3), ("AWAY", 2.9))],
            evidence_for=lambda m: Evidence(m, evidence().features))

        readings = gates_for(found, model=model(), now=NOW)

        assert any(r.status == "EVENT_ALREADY_STARTED" and r.blocking for r in readings)

    def test_a_fixture_with_no_readable_start_is_blocked(self):
        nameless = opportunity(
            market_quotes=[Quote("Sky Bet", "1.234567", s, o, stamp())
                           for s, o in (("HOME", 2.6), ("DRAW", 3.3), ("AWAY", 2.9))],
            evidence_for=lambda m: Evidence(m, evidence().features))

        readings = gates_for(nameless, model=model(), now=NOW)

        assert any(r.status == "EVENT_START_UNKNOWN" and r.blocking for r in readings)

    def test_an_expired_model_blocks(self):
        stale = model(expires_at=(NOW - timedelta(days=1)).isoformat())

        readings = gates_for(opportunity(declared=stale), model=stale, now=NOW)

        assert any(r.status == "MODEL_EXPIRED" and r.blocking for r in readings)

    def test_forecast_assumptions_are_reported_without_blocking(self):
        """Declared rather than sniffed, and non-blocking on purpose. The switch that makes
        it a real decision is `model.requires`: put `home_key_absences` in it and the
        forecast is UNPRICED without team news. Blocking here as well would take that away
        from the person whose name is on the model, and stop the lane ever producing
        anything — there is no free structured team-news source."""

        readings = gates_for(opportunity(), model=model(), now=NOW)

        assumptions = [r for r in readings if r.status == "FORECAST_ASSUMPTION"]
        assert assumptions
        assert all(not r.blocking for r in assumptions)

    def test_a_model_requiring_team_news_is_unpriced_without_it(self):
        """The other side of the same property: the person decides, and the machine
        honours the decision."""

        strict = model(requires=STRENGTHS + ("home_key_absences",))

        found = opportunity(declared=strict)

        assert found.forecast.status != "PRICED"
        assert "home_key_absences" in found.forecast.missing


class TestOneOpportunityPerSelectionPerBook:
    def test_a_three_way_market_at_one_book_produces_three_opportunities(self):
        """One per market would have to pick a selection, and a book can be long on the
        draw and short on the favourite in the same market."""

        found = opportunities_from(quotes(), model=model(), goals_model=GoalsModel(),
                                   evidence_for=lambda m: evidence(m), now=NOW)

        assert {o.selection for o in found} == {"HOME", "DRAW", "AWAY"}

    def test_each_book_is_devigged_against_its_own_prices(self):
        """A fair probability taken from one book and compared against another's price is
        a comparison between two books, which is the arb lane's question, not this one."""

        both = quotes(book="Sky Bet") + [
            Quote("Paddy Power", MARKET, "HOME", 2.45, stamp()),
            Quote("Paddy Power", MARKET, "DRAW", 3.40, stamp()),
            Quote("Paddy Power", MARKET, "AWAY", 3.00, stamp()),
        ]

        found = opportunities_from(both, model=model(), goals_model=GoalsModel(),
                                   evidence_for=lambda m: evidence(m), now=NOW)
        sky = next(o for o in found if o.book == "Sky Bet" and o.selection == "HOME")
        paddy = next(o for o in found if o.book == "Paddy Power" and o.selection == "HOME")

        assert sky.fair.probabilities != paddy.fair.probabilities

    def test_identity_excludes_the_price_and_the_edge(self):
        """Including the odds makes every tick a new sighting and the register dedupes
        nothing while appearing to work. Including the edge is worse — it moves with the
        model as well as with the price."""

        cheap = opportunity(market_quotes=quotes())
        dearer = opportunity(market_quotes=[
            Quote("Sky Bet", MARKET, "HOME", 3.10, stamp()),
            Quote("Sky Bet", MARKET, "DRAW", 3.30, stamp()),
            Quote("Sky Bet", MARKET, "AWAY", 2.90, stamp()),
        ])

        assert mispricing_identity(cheap) == mispricing_identity(dearer)
        assert "2.6" not in mispricing_identity(cheap)


class TestTheThesisSaysThisIsABet:
    def test_the_minted_thesis_records_that_it_rests_on_a_claim(self):
        """The arb lane's caveat can say the position makes no claim about the fixture.
        This one makes exactly that claim, so the caveat has to be blunter."""

        thesis = thesis_from(model(), MARKET)

        considered = " ".join(thesis.considered)
        assert "DOES rest on a claim about how the fixture will go" in considered
        assert "the whole stake is lost" in considered

    def test_the_thesis_carries_the_model_authors_name(self):
        assert thesis_from(model(), MARKET).declared_by == "Ian McGuane"


class TestTheLaneEndToEnd:
    class _Breakers:
        class _Verdict:
            verdict = "PERMITTED"
            blocked_by = ()

        def check(self, **_kw):
            return self._Verdict()

    class _Feed:
        is_configured = True

        def __init__(self, rows):
            self.rows = rows

        def quotes(self, _sport, market=""):
            return self.rows

    def _reaper(self, feed, declared=None):
        return build_mispricing_reaper(
            model=declared or model(), breakers=self._Breakers(), bankroll=500.0,
            sports=("soccer_epl",), source=feed,
            evidence_for=lambda m: evidence(m), now=lambda: NOW)

    def test_an_unconfigured_feed_could_not_look_rather_than_found_nothing(self):
        class Unconfigured:
            is_configured = False

        harvests = build_mispricing_reaper(
            model=model(), breakers=self._Breakers(), bankroll=500.0,
            sports=("soccer_epl",), source=Unconfigured(), now=lambda: NOW).reap()

        assert harvests[0].status == COULD_NOT_LOOK
        assert "not a finding that every price is fair" in harvests[0].reason

    def test_a_correctly_priced_market_is_nothing_found_with_its_coverage(self):
        """The normal state of a market. A lane reporting a mispricing on every fixture
        would be reporting the properties of its own model rather than of the market."""

        # Priced tight around what the model thinks: HOME 60%, DRAW 20%, AWAY 20%.
        even = [Quote("Sky Bet", MARKET, "HOME", 1.60, stamp()),
                Quote("Sky Bet", MARKET, "DRAW", 4.20, stamp()),
                Quote("Sky Bet", MARKET, "AWAY", 4.60, stamp())]

        harvests = self._reaper(self._Feed(even)).reap()

        assert harvests[0].status == NOTHING_FOUND
        assert harvests[0].sources_answered == 1

    def test_a_paper_model_reaches_refused_with_the_numbers(self):
        harvests = self._reaper(self._Feed(quotes())).reap()

        refused = [h for h in harvests if h.status == HARVEST_REFUSED]
        assert refused
        assert any("is PAPER" in h.reason for h in refused)

    def test_a_live_model_reaches_ready_with_a_ticket(self):
        harvests = self._reaper(self._Feed(quotes()), declared=live()).reap()

        ready = [h for h in harvests if h.status == "READY"]
        assert ready
        assert isinstance(ready[0].instruction, ValueTicket)
