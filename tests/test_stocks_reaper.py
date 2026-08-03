"""This lane disqualifies. Anything that survives it is not thereby a recommendation.

The property under test is the direction of the claim. A filing can establish that a
company's own numbers disagree with each other; no filing establishes that a share will go
up. So the person names the subject and declares the thesis, the lane tries to knock it out,
and a criterion that asserts something about the future refuses construction without a named
human behind it.

The second property is that volatility is measured rather than omitted. `lib/sizing` makes
an unmeasured ceiling INDETERMINATE precisely because dropping one always raises the
permitted size, and a stocks lane that quietly sized on risk limit alone would size at full
limit exactly when nothing is known about how far the price moves.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from connectors.alpaca import Quote
from lib.candidates import INDETERMINATE, REFUSED, SURFACED
from lib.reaper import COULD_NOT_LOOK, INDETERMINATE as HARVEST_INDETERMINATE
from lib.reaper import READY, REFUSED as HARVEST_REFUSED, Unworthy
from lib.stocks_reaper import (
    FORECAST,
    MIN_CLOSES,
    OBSERVATIONAL,
    Criterion,
    StockOrder,
    Subject,
    build_stocks_reaper,
    gates_for,
    measure_order,
    realised_move_pct,
    restatement_limit,
    screen_subject,
    size_subject,
)
from lib.thesis import Thesis

TICKER = "MODN"


class Series:
    """Enough of `connectors.edgar.ConceptSeries` for the stages to read."""

    def __init__(self, status="REPORTED", revised=0, units=("USD",), alternates=(),
                 taxonomy="us-gaap"):
        self.status = status
        self.units_seen = units
        self.alternates_with_data = alternates
        self.taxonomy = taxonomy
        self._revised = revised

    def revised_durations(self):
        return {f"2024-01-01..2024-12-{i + 1:02d}": () for i in range(self._revised)}


def closes(count=30, step=1.004, start=100.0):
    """Closes that move, so realised volatility is a measurement rather than a zero."""

    prices, price = [], start
    for i in range(count):
        price *= step if i % 2 else (2.0 - step)
        prices.append(round(price, 4))
    return tuple(prices)


def quote(bid=99.98, ask=100.02, ask_size=1000.0):
    return Quote(TICKER, bid, 1000.0, ask, ask_size, "2026-08-02T15:00:00Z")


def subject(*, filings=None, **kw):
    return Subject(
        TICKER,
        {"revenue": Series(), "net income": Series()} if filings is None else filings,
        quote=kw.pop("quote", quote()),
        closes=kw.pop("closes", closes()),
        **kw,
    )


def thesis(limit=5_000.0, subject_name=TICKER):
    return Thesis(
        subject_name, "Ian McGuane", "the filings are internally consistent and I want it",
        ("the price can fall", "the filings can be restated later"),
        "2026-08-02T09:00:00Z",
        (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds"),
        limit, currency="USD",
    )


class Register:
    def __init__(self, held=None, readable=True):
        self.held = held or {}
        self.readable = readable
        self.reason = "" if readable else "JSONDecodeError: line 1"

    def current(self, name):
        return self.held.get(name)


class TestAForecastNeedsAHuman:
    def _forecast(self, **kw):
        return Criterion("restaters underperform", FORECAST,
                         "filers who restate go on to trade lower",
                         lambda _f: (SURFACED, ""), **kw)

    def test_a_forecast_criterion_refuses_construction_without_a_declarer(self):
        with pytest.raises(ValueError, match="named human"):
            self._forecast()

    def test_automation_cannot_declare_one(self):
        with pytest.raises(ValueError, match="named human"):
            self._forecast(declared_by="agent:stocks-reaper")

    def test_a_named_human_may_declare_one(self):
        assert self._forecast(declared_by="Ian McGuane").kind == FORECAST

    def test_an_observation_needs_nobody(self):
        assert restatement_limit().kind == OBSERVATIONAL

    def test_a_criterion_that_will_not_say_which_it_is_is_refused(self):
        with pytest.raises(ValueError, match="which it is"):
            Criterion("vibes", "MAYBE", "it feels right", lambda _f: (SURFACED, ""))

    def test_the_cascade_records_which_kind_was_applied(self):
        stage = next(s for s in screen_subject(
            subject(), criterion=restatement_limit()).stages
            if s.name == "criterion is declared")

        assert OBSERVATIONAL in stage.detail

    def test_a_declared_forecast_names_its_human_in_the_record(self):
        rule = Criterion("restaters underperform", FORECAST, "they trade lower",
                         lambda _f: (SURFACED, ""), declared_by="Ian McGuane")

        stage = next(s for s in screen_subject(subject(), criterion=rule).stages
                     if s.name == "criterion is declared")

        assert "declared by Ian McGuane" in stage.detail


class TestTheRestatementCriterionDisqualifies:
    def test_a_filer_that_disagrees_with_itself_is_refused(self):
        screened = screen_subject(
            subject(filings={"revenue": Series(revised=3), "net income": Series()}),
            criterion=restatement_limit())

        assert screened.verdict == REFUSED
        assert "revenue (3)" in screened.decided_by.detail

    def test_a_consistent_filer_surfaces(self):
        assert screen_subject(subject(), criterion=restatement_limit()).verdict == SURFACED

    def test_the_ceiling_can_be_raised(self):
        screened = screen_subject(
            subject(filings={"revenue": Series(revised=2)}),
            criterion=restatement_limit(max_revised_spans=2))

        assert screened.verdict == SURFACED

    def test_no_filings_at_all_is_indeterminate_not_a_clean_bill(self):
        verdict, detail = restatement_limit().test({})

        assert verdict == INDETERMINATE
        assert "nothing was checked" in detail

    def test_an_unreported_concept_is_not_counted_as_zero_restatements(self):
        """NOT_REPORTED is a statement about the tagging, not a clean series."""

        verdict, detail = restatement_limit().test({"revenue": Series(status="NOT_REPORTED")})

        assert verdict != INDETERMINATE
        assert "0 restated" in detail


class TestUnreadableIsNotClean:
    def test_a_series_that_could_not_be_retrieved_is_indeterminate(self):
        screened = screen_subject(
            subject(filings={"revenue": Series(status="INDETERMINATE")}),
            criterion=restatement_limit())

        assert screened.verdict == INDETERMINATE
        assert screened.decided_by.name == "filings retrievable"

    def test_mixed_units_make_figures_incomparable_rather_than_wrong(self):
        screened = screen_subject(
            subject(filings={"revenue": Series(units=("USD", "EUR"))}),
            criterion=restatement_limit())

        assert screened.verdict == INDETERMINATE
        assert screened.decided_by.name == "figures are comparable"

    def test_a_history_split_across_tags_is_not_the_whole_history(self):
        screened = screen_subject(
            subject(filings={"revenue": Series(alternates=("Revenues",))}),
            criterion=restatement_limit())

        assert "not the whole history" in screened.decided_by.detail


class TestThePriceMustBeTwoSided:
    def test_no_quote_is_indeterminate(self):
        screened = screen_subject(subject(quote=None), criterion=restatement_limit())

        assert screened.verdict == INDETERMINATE
        assert "one-sided market is not a price" in screened.decided_by.detail

    def test_a_wide_spread_is_refused(self):
        screened = screen_subject(subject(quote=quote(bid=95.0, ask=105.0)),
                                  criterion=restatement_limit())

        assert screened.verdict == REFUSED
        assert "The mid is fiction" in screened.decided_by.detail

    def test_a_tight_spread_passes(self):
        assert screen_subject(subject(), criterion=restatement_limit()).verdict == SURFACED


class TestVolatilityIsMeasuredNotOmitted:
    def test_too_few_closes_is_unknown_rather_than_still(self):
        assert realised_move_pct(closes(count=MIN_CLOSES - 1)) is None

    def test_no_history_at_all_is_unknown(self):
        assert realised_move_pct(None) is None

    def test_a_flat_series_is_a_measurement_failure_not_a_still_market(self):
        assert realised_move_pct((100.0,) * 30) is None

    def test_a_non_positive_price_yields_unknown(self):
        assert realised_move_pct((100.0, 0.0) + closes(count=20)) is None

    def test_a_moving_series_measures(self):
        assert realised_move_pct(closes()) > 0

    def test_unknown_movement_stops_the_cascade(self):
        screened = screen_subject(subject(closes=None), criterion=restatement_limit())

        assert screened.verdict == INDETERMINATE
        assert screened.decided_by.name == "realised movement is known"

    def test_it_also_stops_sizing_rather_than_sizing_without_it(self):
        """Belt and braces on purpose: the flattering direction is the unmeasured one."""

        assert size_subject(subject(closes=None), free_balance=100_000.0,
                            max_exposure=5_000.0) is None


class TestSizingBuysWholeSharesAtTheAsk:
    def _order(self, **kw):
        return size_subject(subject(**kw.pop("subject_kw", {})),
                            free_balance=kw.pop("free_balance", 100_000.0),
                            max_exposure=kw.pop("max_exposure", 5_000.0), **kw)

    def test_it_prices_at_the_ask_not_the_mid(self):
        order = self._order()

        assert order.price == pytest.approx(100.02)

    def test_it_buys_a_whole_number_of_shares(self):
        order = self._order()

        assert isinstance(order.shares, int)
        assert order.cash == pytest.approx(round(order.shares * order.price, 2))

    def test_the_binding_constraint_is_named(self):
        order = self._order(max_exposure=1_000.0)

        assert order.bound_by == "thesis exposure limit"
        assert "thesis exposure limit" in order.describe()

    def test_it_never_sizes_past_the_binding_ceiling(self):
        order = self._order(max_exposure=1_000.0)

        assert order.cash <= 1_000.0

    def test_the_ask_size_binds_when_it_is_the_smallest(self):
        order = self._order(subject_kw={"quote": quote(ask_size=3.0)})

        assert order.bound_by == "venue maximum"
        assert order.shares == 3

    def test_a_position_too_small_for_one_share_is_a_measured_refusal(self):
        result = self._order(max_exposure=10.0)

        assert isinstance(result, Unworthy)
        assert "does not buy one share" in result.reason

    def test_no_quote_means_no_size_rather_than_a_guessed_one(self):
        assert size_subject(subject(quote=None), free_balance=100_000.0,
                            max_exposure=5_000.0) is None

    def test_the_breakers_are_handed_cash_and_no_invented_edge(self):
        """A stock purchase claims no edge. Populating the field would invent one."""

        order = self._order()

        assert measure_order(order) == (order.cash, 0.0)


class TestTheGatesAreShort:
    def test_an_unreadable_portfolio_blocks(self):
        lost = type("P", (), {"readable": False})()

        readings = gates_for(subject(), portfolio=lost)

        assert readings[0].status == "PORTFOLIO_UNREADABLE"
        assert readings[0].blocking

    def test_an_unreported_concept_is_recorded_and_does_not_block(self):
        readings = gates_for(subject(filings={"revenue": Series(status="NOT_REPORTED")}))

        assert readings[0].status == "CONCEPT_NOT_REPORTED"
        assert not readings[0].blocking

    def test_a_clean_subject_produces_nothing(self):
        assert gates_for(subject()) == ()


class TestTheLaneEndToEnd:
    class Edgar:
        def __init__(self, raises=False, revised=0):
            self.raises = raises
            self.revised = revised

        def cik_for_ticker(self, ticker):
            if self.raises:
                raise RuntimeError("EDGAR unreachable")
            return "0000067347"

        def first_reported(self, _cik, _tags):
            return Series(revised=self.revised)

    class Desk:
        def __init__(self, priced=True, history=True):
            self.priced = priced
            self.history = history

        def quote(self, _symbol):
            return quote() if self.priced else None

        def daily_closes(self, _symbol, days=30):
            return closes() if self.history else None

    def _breakers(self, tmp_path, balance=200_000.0):
        from lib.breakers import Breakers, Ringfence

        from lib.outcomes import OutcomeLedger

        return Breakers(Ringfence("stocks", balance), tmp_path / "b.json",
                        kill_switch=tmp_path / "HALT",
                        positions=OutcomeLedger(tmp_path / "outcomes.json"))

    def _reaper(self, tmp_path, *, register=None, edgar=None, desk=None, **kw):
        return build_stocks_reaper(
            watchlist=(TICKER,),
            theses=register if register is not None else Register({TICKER: thesis()}),
            breakers=self._breakers(tmp_path, balance=kw.pop("balance", 200_000.0)),
            free_balance=kw.pop("free_balance", 100_000.0),
            client=edgar if edgar is not None else self.Edgar(),
            broker=desk if desk is not None else self.Desk(),
            concepts={"revenue": ["Revenues"]}, **kw)

    def test_a_clean_filer_with_a_thesis_reaches_ready(self, tmp_path):
        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == READY
        assert isinstance(harvest.instruction, StockOrder)

    def test_ready_still_says_nothing_has_been_placed(self, tmp_path):
        assert "NOTHING HAS BEEN PLACED" in self._reaper(tmp_path).reap()[0].describe()

    def test_no_thesis_is_refused_rather_than_skipped(self, tmp_path):
        """"Nobody authorised this" is a result worth printing."""

        harvest = self._reaper(tmp_path, register=Register({})).reap()[0]

        assert harvest.status == HARVEST_REFUSED

    def test_an_unreadable_thesis_register_could_not_look(self, tmp_path):
        """Not "nothing is authorised" — that is a different and much worse answer."""

        harvest = self._reaper(tmp_path, register=Register(readable=False)).reap()[0]

        assert harvest.status == COULD_NOT_LOOK
        assert "unknown rather than nothing" in harvest.reason

    def test_edgar_being_unreachable_is_could_not_look(self, tmp_path):
        harvest = self._reaper(tmp_path, edgar=self.Edgar(raises=True)).reap()[0]

        assert harvest.status == COULD_NOT_LOOK

    def test_a_restating_filer_is_refused_and_the_reason_names_the_spans(self, tmp_path):
        harvest = self._reaper(tmp_path, edgar=self.Edgar(revised=4)).reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "filed at more than one value" in harvest.reason

    def test_no_price_stops_at_indeterminate(self, tmp_path):
        harvest = self._reaper(tmp_path, desk=self.Desk(priced=False)).reap()[0]

        assert harvest.status == HARVEST_INDETERMINATE

    def test_no_history_stops_at_indeterminate(self, tmp_path):
        harvest = self._reaper(tmp_path, desk=self.Desk(history=False)).reap()[0]

        assert harvest.status == HARVEST_INDETERMINATE

    def test_the_kill_switch_stops_a_clean_filer(self, tmp_path):
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")

        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "kill switch" in harvest.reason

    def test_a_cash_amount_over_the_ringfence_cap_is_refused_after_sizing(self, tmp_path):
        harvest = self._reaper(tmp_path, balance=1_000.0).reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "position size" in harvest.reason
        assert harvest.instruction is not None

    def test_the_chain_lane_rule_does_not_apply_here(self, tmp_path):
        """Stocks may opt into autonomous placement; crypto may not."""

        from dataclasses import replace

        assert replace(self._reaper(tmp_path),
                       autonomous_execution=True).autonomous_execution is True
