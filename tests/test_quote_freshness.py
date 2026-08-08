"""A price you are not being offered must not be sized against, and WHY must be nameable.

Found live, on a Saturday. The lane fetched quotes for three liquid names and every one
came back about 10% wide, so the spread gate refused all three. The gate was right — and it
was right by accident. The raw payload said the quotes were timestamped 20:00:00Z on the
Friday, exactly the New York closing bell, and nothing anywhere in the lane looked at that
timestamp. Market makers withdraw at the close, so a wide book is what a shut market looks
like. Had Friday's closing quote happened to be tight, a live order would have been sized
against a price twenty hours dead and every line of the output would have read normally.

So the age is now measured, and the refusal names which of three different things is true:

    the market is shut      the last price genuinely IS the last price. Nothing is broken.
    the quote is STALE      the market is open and the price is not keeping up. Something
                            is wrong with the feed, and it is worth looking at NOW.
    the age is unknown      no timestamp, or the venue clock could not be reached.

All three refuse. The distinction is not about what happens, it is about what a person
does next — and "STALE" printed on a Sunday sends somebody hunting a fault that does not
exist, which is the same defect as reporting a missing thing as an absent one.

The session is asked of the venue rather than computed here. A holiday calendar in this
repository would be wrong silently on exactly the days it mattered.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from connectors.alpaca import MarketClock, Quote
from lib.stocks_reaper import (
    INDETERMINATE,
    PASSED,
    Subject,
    quote_age_seconds,
    screen_subject,
    restatement_limit,
)

from test_stocks_reaper import Series, closes


def at(seconds_ago: float) -> str:
    moment = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    return moment.isoformat(timespec="microseconds").replace("+00:00", "Z")


def quote(*, age_seconds: float = 5.0, bid: float = 99.99, ask: float = 100.01) -> Quote:
    return Quote("ALAB", bid, 100.0, ask, 100.0, at(age_seconds))


def subject(**kw) -> Subject:
    return Subject(
        "ALAB",
        kw.pop("filings", {"revenue": Series(), "net income": Series()}),
        quote=kw.pop("quote", quote()),
        closes=kw.pop("closes", closes()),
        **kw,
    )


def freshness(subject_):
    candidate = screen_subject(subject_, criterion=restatement_limit())
    return next(s for s in candidate.stages if s.name == "the quote is current")


class TestTheAgeOfAPriceIsMeasuredNotAssumed:
    def test_a_fresh_quote_in_an_open_market_passes(self):
        stage = freshness(subject(market_open=True, quote=quote(age_seconds=5)))

        assert stage.verdict == PASSED

    def test_a_quote_older_than_the_ceiling_in_an_open_market_is_stale(self):
        """The case that would have placed an order against a dead price."""

        stage = freshness(subject(market_open=True, quote=quote(age_seconds=3600)))

        assert stage.verdict == INDETERMINATE
        assert "STALE" in stage.detail

    def test_stale_says_the_market_is_open_so_the_feed_is_the_suspect(self):
        stage = freshness(subject(market_open=True, quote=quote(age_seconds=3600)))

        assert "the market is open" in stage.detail
        assert "not keeping up" in stage.detail

    def test_an_unparseable_timestamp_is_unknown_age_not_zero_age(self):
        stage = freshness(subject(
            market_open=True, quote=Quote("ALAB", 99.99, 100.0, 100.01, 100.0, "not a date")))

        assert stage.verdict == INDETERMINATE
        assert "cannot be established" in stage.detail
        assert "unmeasured age is not a young one" in stage.detail

    def test_a_missing_timestamp_is_unknown_age(self):
        stage = freshness(subject(
            market_open=True, quote=Quote("ALAB", 99.99, 100.0, 100.01, 100.0, "")))

        assert stage.verdict == INDETERMINATE


class TestAShutMarketIsNotAStaleFeed:
    def test_a_closed_market_refuses_without_calling_the_price_stale(self):
        """The Saturday case. Calling this STALE sends a reader after a feed fault."""

        stage = freshness(subject(market_open=False, quote=quote(age_seconds=73_800)))

        assert stage.verdict == INDETERMINATE
        assert "the market is shut" in stage.detail
        assert "STALE" not in stage.detail

    def test_it_explains_why_a_shut_market_quotes_a_wide_spread(self):
        """Otherwise the 10% spread reads as a broken feed rather than an empty book."""

        stage = freshness(subject(market_open=False, quote=quote(age_seconds=73_800)))

        assert "withdraw at the close" in stage.detail
        assert "empty book" in stage.detail

    def test_it_names_when_to_come_back(self):
        """A refusal names what a person can go and do about it."""

        stage = freshness(subject(
            market_open=False, next_open="2026-08-10T13:30:00Z", quote=quote(age_seconds=73_800)))

        assert "2026-08-10T13:30:00Z" in stage.detail

    def test_a_closed_market_still_refuses_even_with_a_fresh_quote(self):
        """You cannot buy at a price nobody is offering, however recently it was printed."""

        stage = freshness(subject(market_open=False, quote=quote(age_seconds=2)))

        assert stage.verdict == INDETERMINATE


class TestAnUnknownSessionIsNotAnOpenOne:
    def test_an_unreachable_clock_refuses_rather_than_assuming_open(self):
        """`market_open=None` is the third state and must not resolve to either answer."""

        stage = freshness(subject(market_open=None, quote=quote(age_seconds=5)))

        assert stage.verdict == INDETERMINATE
        assert "could not be reached" in stage.detail

    def test_it_does_not_report_the_market_as_shut_either(self):
        stage = freshness(subject(market_open=None, quote=quote(age_seconds=5)))

        assert "the market is shut" not in stage.detail

    def test_the_clock_returns_none_rather_than_false_when_unconfigured(self):
        """A broker with no keys must not report the market closed — it did not ask."""

        from connectors.alpaca import AlpacaBroker

        assert AlpacaBroker(None).clock() is None


class TestFreshnessIsCheckedBeforeTheSpread:
    def test_a_shut_market_is_the_reason_given_not_the_spread_it_causes(self):
        """The exact defect this was written for, and ordering alone did not fix it.

        Putting freshness first was not enough: the spread stage returns REFUSED, which
        outranks INDETERMINATE, so a Saturday still reported "the spread is 9.72%" and
        buried the shut market. A reader then goes hunting liquidity that was never
        missing. So a spread is only computed on a price that is current — one taken from
        a book nobody is maintaining is not a measurement of anything.
        """

        candidate = screen_subject(
            subject(market_open=False, next_open="2026-08-10T13:30:00Z",
                    quote=quote(age_seconds=73_800, bid=315.86, ask=348.14)),
            criterion=restatement_limit())

        assert "the market is shut" in candidate.decided_by.detail
        assert "spread" not in candidate.decided_by.detail.split("its spread")[0]
        assert not [s for s in candidate.stages if s.name == "a two-sided price"]

    def test_a_stale_quote_also_suppresses_the_spread_it_cannot_measure(self):
        candidate = screen_subject(
            subject(market_open=True, quote=quote(age_seconds=3600, bid=90.0, ask=110.0)),
            criterion=restatement_limit())

        assert "STALE" in candidate.decided_by.detail
        assert not [s for s in candidate.stages if s.name == "a two-sided price"]

    def test_a_current_quote_still_has_its_spread_judged(self):
        """The suppression must not become a way for a wide spread to pass unexamined."""

        candidate = screen_subject(
            subject(market_open=True, quote=quote(age_seconds=5, bid=90.0, ask=110.0)),
            criterion=restatement_limit())

        assert "The mid is fiction" in candidate.decided_by.detail

    def test_an_absent_quote_raises_no_freshness_stage_at_all(self):
        """With no quote there is no question of its age, and `decided_by` takes the first
        stage that did not pass — so any stage here, blocking or not, would take the
        refusal off the price stage and hand a reader "there is no quote to age" instead
        of "no quote with size on both sides was returned"."""

        candidate = screen_subject(subject(market_open=True, quote=None),
                                   criterion=restatement_limit())

        assert not [s for s in candidate.stages if s.name == "the quote is current"]
        assert "one-sided market is not a price" in candidate.decided_by.detail


class TestTheAgeHelper:
    def test_it_returns_none_rather_than_zero_when_it_cannot_tell(self):
        assert quote_age_seconds(None) is None
        assert quote_age_seconds(Quote("A", 1.0, 1.0, 1.0, 1.0, "")) is None
        assert quote_age_seconds(Quote("A", 1.0, 1.0, 1.0, 1.0, "rubbish")) is None

    def test_it_reads_alpacas_nanosecond_timestamps(self):
        """The live payload carries nine fractional digits, which not every parser takes."""

        now = datetime(2026, 8, 8, 16, 30, tzinfo=timezone.utc)
        age = quote_age_seconds(
            Quote("ALAB", 1.0, 1.0, 1.0, 1.0, "2026-08-07T20:00:00.018463502Z"), now=now)

        assert age == pytest.approx(20.5 * 3600, abs=60)

    def test_a_naive_timestamp_is_read_as_utc_not_local(self):
        """Otherwise the same quote is fresh in Dublin and stale in Sydney."""

        now = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
        age = quote_age_seconds(Quote("A", 1.0, 1.0, 1.0, 1.0, "2026-08-08T11:00:00"), now=now)

        assert age == pytest.approx(3600, abs=1)


class TestTheClockIsAskedOfTheVenue:
    def test_it_reports_what_the_venue_said(self):
        clock = MarketClock(is_open=True, next_open="2026-08-10T13:30:00Z")

        assert clock.is_open is True
        assert clock.next_open == "2026-08-10T13:30:00Z"

    def test_a_clock_without_is_open_is_no_answer(self):
        """A payload missing the field must not be read as closed."""

        from connectors.alpaca import AlpacaBroker, AlpacaCredentials

        broker = AlpacaBroker(AlpacaCredentials("k", "s", paper=True))
        broker._call = lambda *a, **kw: {"timestamp": "2026-08-08T16:30:00Z"}

        assert broker.clock() is None
