"""A scan that could not reach a book has not established that the book has no price.

This is the cheapest place in the whole system to make the recurring mistake and the
hardest place to notice it. A scanner reaching two books of five, finding no arb, and
printing "no arb found" is wrong in a way that looks exactly like being right, every time,
until the day someone acts on it.

So the unconfigured source is written before any real provider, and it answers loudly.
"""
from __future__ import annotations

import pytest

from connectors.odds import (
    BOOKMAKER,
    CONFIGURED,
    EXCHANGE,
    KNOWN_SOURCES,
    NOT_CONFIGURED,
    UNREACHABLE,
    MarketQuote,
    ScanCoverage,
    UnconfiguredSource,
    scan,
)

MARKET = "Match Odds: A v B"


class TestSilenceIsNotAnAbsenceOfPrice:
    def test_an_unconfigured_source_says_so_rather_than_returning_nothing(self):
        quote = UnconfiguredSource("Betfair Exchange", EXCHANGE).quote(MARKET)

        assert quote.status == NOT_CONFIGURED
        assert quote.legs == ()

    def test_the_wording_refuses_to_claim_the_book_has_no_price(self):
        described = UnconfiguredSource("Bet365").quote(MARKET).describe()

        assert "not a finding that Bet365 offers no price" in described
        assert "has not covered it" in described

    def test_unreachable_is_unknown_rather_than_absent(self):
        described = MarketQuote(
            UNREACHABLE, "Smarkets", EXCHANGE, market=MARKET, reason="timeout"
        ).describe()

        assert "unknown, not absent" in described

    def test_asking_never_raises_so_a_scan_can_report_who_answered(self):
        """A provider that raised would end the scan and hide the sources after it."""

        assert scan(MARKET).quotes


class TestCoverageIsReportedNotAssumed:
    def test_a_scan_over_only_unconfigured_sources_is_not_complete(self):
        assert scan(MARKET).is_complete is False

    def test_every_silent_source_is_named(self):
        described = scan(MARKET).describe()

        for source in KNOWN_SOURCES:
            assert source.name in described

    def test_the_absence_of_an_arb_is_labelled_as_absence_of_evidence(self):
        described = scan(MARKET).describe()

        assert "absence of evidence, not evidence of absence" in described

    def test_a_fully_answered_scan_reports_complete(self):
        class Answering:
            name, kind = "Test", EXCHANGE

            def quote(self, market):
                return MarketQuote(CONFIGURED, self.name, self.kind, market=market,
                                   stake_is_observed=True)

        assert scan(MARKET, [Answering()]).is_complete is True

    def test_coverage_counts_answers_not_attempts(self):
        coverage = ScanCoverage(MARKET, (
            MarketQuote(CONFIGURED, "A", EXCHANGE, stake_is_observed=True),
            MarketQuote(NOT_CONFIGURED, "B", BOOKMAKER, reason="no key"),
        ))

        assert len(coverage.answered) == 1
        assert len(coverage.silent) == 1
        assert "1 of 2 source(s) answered" in coverage.describe()


class TestAnExchangeSizeAndABookmakerSizeAreDifferentClaims:
    def test_a_bookmaker_size_is_labelled_an_upper_bound(self):
        """The same headline price is offered at different sizes to different accounts.
        A bookmaker's limit is a policy, not an offer."""

        described = MarketQuote(
            CONFIGURED, "Paddy Power", BOOKMAKER, market=MARKET, stake_is_observed=False
        ).describe()

        assert "UPPER BOUND" in described
        assert "may accept far less" in described

    def test_an_exchange_size_is_labelled_observed(self):
        described = MarketQuote(
            CONFIGURED, "Betfair Exchange", EXCHANGE, market=MARKET, stake_is_observed=True
        ).describe()

        assert "observed from the book" in described


class TestTheRegistryNamesWhatIsMissing:
    def test_known_sources_are_declared_even_though_none_is_implemented(self):
        """Leaving the list short would make a scan look complete over one book."""

        assert len(KNOWN_SOURCES) >= 5

    def test_each_declares_why_it_cannot_be_used(self):
        assert all(source.reason.strip() for source in KNOWN_SOURCES)

    def test_exchanges_and_bookmakers_are_distinguished(self):
        kinds = {source.kind for source in KNOWN_SOURCES}

        assert kinds == {EXCHANGE, BOOKMAKER}
