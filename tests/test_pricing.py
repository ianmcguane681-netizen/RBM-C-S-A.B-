"""A price source can be wrong in four ways, and three of them look like an answer.

The book marked every holding UNPRICED because `status.py` passed `value_at(None)` while
`AlpacaBroker.quote()` sat beside it able to answer. Joining them is a few lines. What
these tests hold is everything that must not happen on the way.

A price too old to trust must not be counted into a total presented as the current value of
the book. A market that is shut must not be reported as a feed falling behind, and — the
asymmetry that matters — a clock nobody could read must not be reported as a shut market,
because that is the direction where an outage arrives dressed as reassurance.

A holding a US broker has never heard of must be told apart from one whose request failed:
the first is the correct, permanent answer for a European ETF and the second is a question
somebody can go and settle. Neither may be filled in from a remembered price, which looks
like data and is a memory.

And nothing here may add euro to dollars. The book records cost in euro, the quotes come
back in dollars, there is no rate in this system, and the one time these were summed the
dashboard printed `-EUR 38.00`. A total that cannot be stated is `None` and says which
units it is made of — including the case that a whole book failed to price, which is not a
book worth nought.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.portfolio import (
    BUY,
    MARKET_CLOSED,
    PRICED,
    STALE,
    UNPRICED,
    Entry,
    Portfolio,
)
from lib.pricing import (
    CLOSED,
    COULD_NOT_LOOK,
    LOOKED,
    OPEN,
    STALE_AFTER_SECONDS,
    UNKNOWN,
    AlpacaPrices,
    Price,
    PriceSourceError,
    value_book,
)


def _stamp(seconds_ago: float = 0.0) -> str:
    when = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    return when.isoformat(timespec="seconds").replace("+00:00", "Z")


def book_of(*assets: tuple[str, float, float], currency: str = "EUR") -> Portfolio:
    book = Portfolio("/tmp/never-written-pricing.json")
    for asset, quantity, price in assets:
        book.add(Entry(asset, "equity", BUY, quantity, price, currency,
                       "2026-07-01T10:00:00Z", "test"))
    return book


class FakeSource:
    """A price source under the test's control, including in how it fails."""

    name = "fake"

    def __init__(self, prices=None, *, market=OPEN, unavailable="", failing=()):
        self.prices = prices or {}
        self.market = market
        self._unavailable = unavailable
        self.failing = set(failing)
        self.asked: list[str] = []

    def unavailable_reason(self) -> str:
        return self._unavailable

    def market_state(self) -> str:
        return self.market

    def price(self, asset: str):
        self.asked.append(asset)
        if asset in self.failing:
            raise PriceSourceError("HTTPError: 429")
        return self.prices.get(asset)


class TestAPriceIsOnlyAPriceWhileItIsCurrent:
    def test_a_live_quote_prices_the_holding_and_carries_where_it_came_from(self):
        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(30), "fake")})

        pricing = value_book(book.positions(), source)
        valuation = pricing.valuations[0]

        assert pricing.look == LOOKED
        assert valuation.status == PRICED
        assert valuation.value == pytest.approx(4182.0)
        assert valuation.source == "fake"
        assert valuation.priced_at

    def test_a_quote_older_than_the_ceiling_is_stale_and_stale_is_not_priced(self):
        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(3600), "fake")})

        valuation = value_book(book.positions(), source).valuations[0]

        assert valuation.status == STALE
        assert valuation.status != PRICED

    def test_a_stale_holding_is_kept_out_of_the_total_it_would_misdate(self):
        """The number a holder reads first must not be part memory.

        `Valuation.value` still returns the stale figure — a reader asking about that one
        holding gets an answer with STALE stamped on it. What must not happen is that
        figure being silently summed into a book total presented as the current value.
        """

        book = book_of(("NET", 40, 96.10), ("MOD", 20, 88.00))
        source = FakeSource({
            "MOD": Price(91.30, "USD", _stamp(3600), "fake"),
            "NET": Price(104.55, "USD", _stamp(30), "fake"),
        })

        exposure = book.exposure(value_book(book.positions(), source).valuations)

        assert exposure.stale_assets == ("MOD",)
        assert exposure.priced_value == pytest.approx(4182.0)
        assert exposure.is_complete is False

    def test_the_ceiling_is_passed_explicitly_and_not_left_at_never_stale(self):
        """`value_at`'s default of -1.0 means "never goes stale". Nothing may inherit it."""

        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(86_400), "fake")})

        pricing = value_book(book.positions(), source)

        assert pricing.stale_after_seconds == STALE_AFTER_SECONDS
        assert pricing.valuations[0].status == STALE


class TestAShutMarketIsNotAStalePrice:
    """Two facts that produce the same age and want opposite words.

    A ceiling loose enough to cover a long weekend is loose enough to hide a feed that
    died on Friday morning, so the two are told apart by asking the venue rather than by
    choosing a number that is wrong in both directions.
    """

    def test_a_closed_market_reports_the_last_price_as_the_last_price(self):
        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(86_400), "fake")},
                            market=CLOSED)

        valuation = value_book(book.positions(), source).valuations[0]

        assert valuation.status == MARKET_CLOSED
        assert valuation.value == pytest.approx(4182.0)

    def test_a_closed_market_price_still_counts_toward_the_total(self):
        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(86_400), "fake")},
                            market=CLOSED)

        exposure = book.exposure(value_book(book.positions(), source).valuations)

        assert exposure.stale_assets == ()
        assert exposure.priced_value == pytest.approx(4182.0)

    def test_an_unreadable_clock_keeps_the_stricter_word(self):
        """The asymmetry this whole distinction turns on.

        A failed clock read resolving to CLOSED would relabel every stale price as an
        honest weekend one — an outage reported as reassurance. UNKNOWN keeps STALE.
        """

        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(86_400), "fake")},
                            market=UNKNOWN)

        assert value_book(book.positions(), source).valuations[0].status == STALE


class TestLookingAndFindingAreDifferentFailures:
    def test_a_source_that_cannot_be_asked_is_not_a_book_of_unquotable_assets(self):
        book = book_of(("NET", 40, 96.10), ("MOD", 20, 88.00))
        source = FakeSource(unavailable="no Alpaca credentials: put key_id in ~/.alpaca/")

        pricing = value_book(book.positions(), source)

        assert pricing.look == COULD_NOT_LOOK
        assert source.asked == []
        assert all(v.status == UNPRICED for v in pricing.valuations)
        assert pricing.unquotable == ()
        assert "~/.alpaca/" in pricing.describe()

    def test_a_holding_the_source_does_not_carry_is_named_as_unquotable(self):
        """The expected answer for a European UCITS ETF at a US broker, not a gap."""

        book = book_of(("NET", 40, 96.10), ("VUAA", 12, 92.40))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(30), "fake")})

        pricing = value_book(book.positions(), source)

        assert pricing.look == LOOKED
        assert pricing.unquotable == ("VUAA",)
        assert pricing.unreachable == ()

    def test_a_failed_request_is_unreachable_rather_than_unquotable(self):
        book = book_of(("NET", 40, 96.10), ("S", 100, 17.55))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(30), "fake")},
                            failing={"S"})

        pricing = value_book(book.positions(), source)

        assert pricing.unreachable == ("S",)
        assert pricing.unquotable == ()
        assert "Re-run" in pricing.describe()

    def test_one_asset_failing_leaves_the_others_priced(self):
        book = book_of(("NET", 40, 96.10), ("S", 100, 17.55), ("MOD", 20, 88.00))
        source = FakeSource(
            {"NET": Price(104.55, "USD", _stamp(30), "fake"),
             "MOD": Price(91.30, "USD", _stamp(30), "fake")},
            failing={"S"},
        )

        pricing = value_book(book.positions(), source)

        assert pricing.look == LOOKED
        assert pricing.priced_count == 2

    def test_every_request_failing_is_reported_as_not_having_looked(self):
        book = book_of(("NET", 40, 96.10), ("MOD", 20, 88.00))
        source = FakeSource(failing={"NET", "MOD"})

        assert value_book(book.positions(), source).look == COULD_NOT_LOOK

    def test_a_failed_quote_does_not_reuse_a_price_seen_a_moment_ago(self):
        """A remembered value rendered as current looks like data and is a memory."""

        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(30), "fake")})
        assert value_book(book.positions(), source).valuations[0].status == PRICED

        source.failing = {"NET"}
        second = value_book(book.positions(), source).valuations[0]

        assert second.status == UNPRICED
        assert second.value is None


class TestTheBookRefusesToAddTwoCurrencies:
    """`EUR 39.00` and `USD -77.00` were once summed and printed as `-EUR 38.00`.

    That was not a formatting slip. It was two units added because the figure did not
    carry its own, and the fix is structural: a valuation states the unit its price
    arrived in, and a total that spans more than one cannot be stated at all.
    """

    def test_a_price_carries_its_own_currency_not_the_books(self):
        book = book_of(("NET", 40, 96.10), currency="EUR")
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(30), "fake")})

        valuation = value_book(book.positions(), source).valuations[0]

        assert valuation.currency == "USD"

    def test_a_book_priced_in_two_currencies_produces_no_single_total(self):
        book = book_of(("NET", 40, 96.10), ("VUAA", 12, 92.40))
        source = FakeSource({
            "NET": Price(104.55, "USD", _stamp(30), "fake"),
            "VUAA": Price(101.20, "EUR", _stamp(30), "fake"),
        })

        exposure = book.exposure(value_book(book.positions(), source).valuations)

        assert exposure.priced_value is None
        assert exposure.spans_currencies is True
        assert exposure.is_complete is False
        assert set(exposure.by_currency) == {"USD", "EUR"}

    def test_the_refusal_names_the_units_rather_than_saying_indeterminate(self):
        book = book_of(("NET", 40, 96.10), ("VUAA", 12, 92.40))
        source = FakeSource({
            "NET": Price(104.55, "USD", _stamp(30), "fake"),
            "VUAA": Price(101.20, "EUR", _stamp(30), "fake"),
        })

        text = book.exposure(value_book(book.positions(), source).valuations).describe()

        assert "EUR" in text and "USD" in text
        assert "no exchange rate" in text

    def test_a_value_and_a_cost_in_different_units_are_not_put_on_one_line(self):
        book = book_of(("NET", 40, 96.10))
        source = FakeSource({"NET": Price(104.55, "USD", _stamp(30), "fake")})

        text = book.exposure(value_book(book.positions(), source).valuations).describe()

        assert "is not a gain" in text


class TestAnUnpricedBookIsNotABookWorthNothing:
    """The same error `Realised` made by reporting COMPLETE over an empty book.

    Nothing priced and nothing held both produce an empty set of priced values, and only
    one of them is worth zero. Found by running the panel with an unavailable source: it
    printed `Priced holdings: 0.00 EUR` for a fully stocked book.
    """

    def test_a_book_where_nothing_priced_states_no_total_rather_than_zero(self):
        book = book_of(("NET", 40, 96.10), ("VUAA", 12, 92.40))
        source = FakeSource(unavailable="no credentials")

        exposure = book.exposure(value_book(book.positions(), source).valuations)

        assert exposure.nothing_priced is True
        assert exposure.priced_value is None
        assert "NOT a book worth 0.00" in exposure.describe()

    def test_a_book_with_no_holdings_still_totals_to_zero(self):
        """Because that one genuinely is nought, and the two must stay distinguishable."""

        book = book_of()

        exposure = book.exposure([])

        assert exposure.nothing_priced is False
        assert exposure.priced_value == 0.0


class TestTheAlpacaAdapterValuesAtTheBid:
    class FakeQuote:
        def __init__(self, bid, ask, observed_at):
            self.bid, self.ask, self.observed_at = bid, ask, observed_at

    class FakeBroker:
        def __init__(self, quote=None, *, configured=True, open_now=True, raises=None):
            self.is_configured = configured
            self._quote, self._open, self._raises = quote, open_now, raises

        def is_market_open(self):
            return self._open

        def quote(self, symbol):
            if self._raises:
                raise self._raises
            return self._quote

    def test_a_wide_spread_is_valued_at_the_bid_not_the_ask(self):
        """What you could get for it, not what somebody is asking for one."""

        quote = self.FakeQuote(90.0, 110.0, _stamp(30))
        price = AlpacaPrices(self.FakeBroker(quote)).price("NET")

        assert price.unit_price == 90.0

    def test_the_quotes_own_timestamp_is_carried_not_the_time_of_the_call(self):
        stamped = _stamp(600)
        price = AlpacaPrices(self.FakeBroker(self.FakeQuote(90.0, 91.0, stamped))).price("N")

        assert price.priced_at == stamped

    def test_the_currency_is_stated_as_dollars_rather_than_inherited(self):
        price = AlpacaPrices(self.FakeBroker(self.FakeQuote(90.0, 91.0, _stamp()))).price("N")

        assert price.currency == "USD"

    def test_an_unconfigured_broker_names_the_files_a_person_must_write(self):
        reason = AlpacaPrices(self.FakeBroker(configured=False)).unavailable_reason()

        assert "~/.alpaca/" in reason
        assert "key_id" in reason

    def test_a_transport_failure_raises_rather_than_reading_as_no_such_asset(self):
        source = AlpacaPrices(self.FakeBroker(raises=OSError("connection reset")))

        with pytest.raises(PriceSourceError):
            source.price("NET")

    def test_an_absent_quote_is_no_price_for_that_asset(self):
        assert AlpacaPrices(self.FakeBroker(None)).price("VUAA") is None

    def test_a_clock_that_cannot_be_read_is_unknown_not_closed(self):
        assert AlpacaPrices(self.FakeBroker(open_now=None)).market_state() == UNKNOWN

    def test_the_two_real_clock_answers_survive_the_translation(self):
        assert AlpacaPrices(self.FakeBroker(open_now=True)).market_state() == OPEN
        assert AlpacaPrices(self.FakeBroker(open_now=False)).market_state() == CLOSED


class TestValuingABookDoesNotSleepIntoARateLimit:
    """`retrying_urlopen` waits out a 429, and for its own callers that is right.

    It sleeps 5, 20 then 60 seconds, which suits a research run whose answer is worth a
    minute. Valuing the book runs on a page load and once per holding, so the same policy
    turns one rate-limited refresh into a quarter of an hour of sleeping over ten symbols
    while the panel shows nothing. The design note for this work says do not retry into
    the limit; this holds the source to it.
    """

    def _broker(self, opener):
        from connectors.alpaca import AlpacaBroker, AlpacaCredentials

        return AlpacaBroker(AlpacaCredentials("key", "secret", paper=True), opener=opener)

    def test_a_rate_limited_quote_fails_the_holding_once_rather_than_three_times(self):
        import urllib.error

        calls = []

        def opener(request, **kw):
            calls.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many", {}, None)

        source = AlpacaPrices(self._broker(opener))

        with pytest.raises(PriceSourceError):
            source.price("NET")
        assert len(calls) == 1

    def test_the_default_source_is_not_built_on_the_retrying_opener(self):
        """The property, stated where a future refactor would otherwise undo it."""

        from lib.http_retry import retrying_urlopen
        from lib.pricing import alpaca_prices

        source = alpaca_prices("/tmp/no-such-alpaca-directory")

        assert source._broker._opener is not retrying_urlopen
