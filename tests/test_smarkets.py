"""Cheap access does not change what an empty answer is allowed to mean.

Smarkets needs no application key and no fee, which makes it the sensible first exchange
and changes nothing about the failure that matters: a market that could not be read must
never render as a market with no opportunity in it.

One limit is specific to this API and shapes the code. Login is capped at 5 requests per
300 seconds, so a connector that re-authenticated on every failure would exhaust the
allowance in under half a minute and lock itself out for five -- during which every market
it examined would look unavailable rather than unqueried.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from connectors.odds import CONFIGURED, NOT_CONFIGURED, UNREACHABLE
from connectors.smarkets import (
    SmarketsCredentials,
    SmarketsSession,
    SmarketsSessionError,
    SmarketsSource,
)
from lib.http_retry import TransientRetrievalError

RULES = "Settled on the official result at the end of regulation time."


def creds(tmp_path: Path) -> SmarketsCredentials:
    (tmp_path / "username").write_text("someone@example.com")
    (tmp_path / "password").write_text("pw")
    return SmarketsCredentials.load(tmp_path)


MARKET = {"markets": [{"name": "Match Odds", "description": RULES,
                       "last_executed_at": "2026-08-02T12:00:00Z"}]}
CONTRACTS = {"contracts": [{"id": 111, "name": "Team A"}, {"id": 222, "name": "Team B"}]}
QUOTES = {
    "111": {"bids": [{"price": 4630, "quantity": 5_000_000},
                     {"price": 4600, "quantity": 90_000_000}]},
    "222": {"bids": [{"price": 4760, "quantity": 2_500_000}]},
}


def transport(*, token="TOK-1", market=None, contracts=None, quotes=None, fail=None):
    calls = []

    def _request(url, headers, body, method):
        calls.append((url, method))
        if url.endswith("/sessions/"):
            return {"token": token} if token else {}
        if fail:
            raise TransientRetrievalError(fail)
        if url.endswith("/contracts/"):
            return contracts if contracts is not None else CONTRACTS
        if url.endswith("/quotes/"):
            return quotes if quotes is not None else QUOTES
        return market if market is not None else MARKET

    _request.calls = calls
    return _request


def source(tmp_path, **kw):
    return SmarketsSource(session=SmarketsSession(creds(tmp_path), transport=transport(**kw)))


class TestNoKeyStillMeansNoGuessing:
    def test_missing_credentials_are_a_state_not_an_error(self, tmp_path):
        quote = SmarketsSource.from_directory(tmp_path / "absent").quote("1")

        assert quote.status == NOT_CONFIGURED
        assert "not a finding that Smarkets offers no price" in quote.describe()

    def test_a_login_returning_no_token_is_refused(self, tmp_path):
        session = SmarketsSession(creds(tmp_path), transport=transport(token=""))

        with pytest.raises(SmarketsSessionError):
            session.login()

    def test_an_unreachable_api_is_not_an_empty_market(self, tmp_path):
        quote = source(tmp_path, fail="Smarkets 503").quote("1")

        assert quote.status == UNREACHABLE
        assert quote.legs == ()
        assert "unknown, not absent" in quote.describe()


class TestTheLoginCapIsRespected:
    def test_re_authentication_happens_at_most_once(self, tmp_path):
        """5 logins per 300 seconds. A retry loop exhausts that in under half a minute and
        then every market reads as unavailable for five."""

        request = transport(fail="Smarkets 401 unauthorized")
        session = SmarketsSession(creds(tmp_path), transport=request)

        with pytest.raises(TransientRetrievalError):
            session.get("/markets/1/")

        logins = [c for c in request.calls if c[0].endswith("/sessions/")]
        assert len(logins) == 2

    def test_a_non_auth_failure_does_not_re_authenticate(self, tmp_path):
        """Burning a login on a 503 spends an allowance that a rate limit will need."""

        request = transport(fail="Smarkets 503 unavailable")
        session = SmarketsSession(creds(tmp_path), transport=request)

        with pytest.raises(TransientRetrievalError):
            session.get("/markets/1/")

        assert len([c for c in request.calls if c[0].endswith("/sessions/")]) == 1

    def test_the_token_is_minted_lazily_and_reused(self, tmp_path):
        request = transport()
        session = SmarketsSession(creds(tmp_path), transport=request)

        assert session.is_open is False
        session.get("/markets/1/")
        session.get("/markets/2/")

        assert len([c for c in request.calls if c[0].endswith("/sessions/")]) == 1

    def test_the_token_is_sent_in_the_documented_header_form(self, tmp_path):
        session = SmarketsSession(creds(tmp_path), transport=transport(token="TOK-9"))

        assert session.headers()["Authentication"] == "Session-Token TOK-9"


class TestRulesAndPrices:
    def test_a_market_without_a_description_yields_no_legs(self, tmp_path):
        bare = {"markets": [{"name": "Match Odds"}]}
        quote = source(tmp_path, market=bare).quote("1")

        assert quote.status == UNREACHABLE
        assert "RULES_UNAVAILABLE" in quote.reason

    def test_percentage_prices_are_converted_to_decimal_odds(self, tmp_path):
        """Smarkets quotes probability in hundredths of a percent. 4630 is 46.30%, which is
        decimal 2.16 -- reading it as odds directly would be wrong by a factor of two
        thousand and still look like a number."""

        quote = source(tmp_path).quote("1")
        team_a = next(leg for leg in quote.legs if leg.selection == "Team A")

        assert team_a.decimal_odds == pytest.approx(2.1598, abs=0.001)

    def test_only_the_top_of_book_is_taken(self, tmp_path):
        quote = source(tmp_path).quote("1")
        team_a = next(leg for leg in quote.legs if leg.selection == "Team A")

        assert team_a.max_stake == pytest.approx(500.0)

    def test_the_rules_reach_every_leg(self, tmp_path):
        quote = source(tmp_path).quote("1")

        assert quote.legs
        assert all(leg.settlement_rule == RULES for leg in quote.legs)

    def test_exchange_sizes_are_marked_observed(self, tmp_path):
        assert source(tmp_path).quote("1").stake_is_observed is True

    def test_commission_travels_onto_every_leg(self, tmp_path):
        quote = source(tmp_path).quote("1")

        assert all(leg.net_odds < leg.decimal_odds for leg in quote.legs)


class TestAnEmptyBookIsNotProvenIlliquid:
    def test_no_priced_contracts_says_access_may_be_restricted(self, tmp_path):
        quote = source(tmp_path, quotes={}).quote("1")

        assert quote.status == CONFIGURED
        assert "RESTRICTED_OR_EMPTY" in quote.reason
        assert "not a finding that the market has no liquidity" in quote.reason

    def test_a_contract_with_no_bids_is_skipped_not_zero_priced(self, tmp_path):
        quote = source(tmp_path, quotes={"111": {"bids": []}}).quote("1")

        assert quote.legs == ()
