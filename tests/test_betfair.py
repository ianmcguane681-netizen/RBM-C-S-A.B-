"""A dead session, a delayed key and a missing rule must not look like a quiet market.

Every test here is about a failure that renders as an absence of opportunity. That is the
dangerous direction for an arb scanner: "no arb found" from a connector that saw nothing is
indistinguishable from "no arb exists", and the operator has no way to tell.

Built without credentials, against a fake transport. The endpoint shapes come from
Betfair's published documentation and have not been exercised live from here, which is
recorded in the module rather than assumed away.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from connectors.betfair import (
    BetfairCredentials,
    BetfairSession,
    BetfairSource,
    SessionExpired,
)
from connectors.odds import CONFIGURED, NOT_CONFIGURED, UNREACHABLE
from lib.arb import Leg

RULES = "Settled on the official result. Void if the match is abandoned."


def creds(tmp_path: Path, *, delayed=False, cert=False, password="pw") -> BetfairCredentials:
    (tmp_path / "app_key").write_text("APPKEY123")
    (tmp_path / "username").write_text("someone@example.com")
    (tmp_path / "password").write_text(password)
    (tmp_path / ("delayed" if delayed else "live")).write_text("")
    if cert:
        (tmp_path / "client.crt").write_text("cert")
        (tmp_path / "client.key").write_text("key")
    return BetfairCredentials.load(tmp_path)


def transport(*, token="SSOID-1", catalogue=None, book=None, fault=None, login_status="SUCCESS"):
    calls = []

    def _post(url, headers, body):
        calls.append((url, headers, body))
        if "certlogin" in url:
            return {"loginStatus": login_status, "sessionToken": token}
        if "identitysso" in url:
            return {"status": login_status, "token": token}
        if fault and "listMarketCatalogue" in url:
            return {"faultcode": "Client", "faultstring": fault}
        if "listMarketCatalogue" in url:
            return catalogue if catalogue is not None else []
        if "listMarketBook" in url:
            return book if book is not None else []
        return {}

    _post.calls = calls
    return _post


CATALOGUE = [{
    "marketName": "Match Odds",
    "description": {"rules": RULES},
    "runners": [{"selectionId": 1, "runnerName": "Team A"},
                {"selectionId": 2, "runnerName": "Team B"}],
}]
BOOK = [{
    "lastMatchTime": "2026-08-02T11:00:00Z",
    "runners": [
        {"selectionId": 1, "ex": {"availableToBack": [
            {"price": 2.10, "size": 500.0}, {"price": 2.08, "size": 9000.0}]}},
        {"selectionId": 2, "ex": {"availableToBack": [{"price": 2.05, "size": 300.0}]}},
    ],
}]


def source(tmp_path, **kw):
    delayed = kw.pop("delayed", False)
    return BetfairSource(
        session=BetfairSession(creds(tmp_path, delayed=delayed), transport=transport(**kw))
    )


class TestNoCredentialsIsAStateNotAnError:
    def test_a_missing_directory_yields_not_configured(self, tmp_path):
        assert BetfairCredentials.load(tmp_path / "absent") is None

    def test_the_source_still_answers_when_unconfigured(self, tmp_path):
        quote = BetfairSource.from_directory(tmp_path / "absent").quote("1.234")

        assert quote.status == NOT_CONFIGURED
        assert quote.legs == ()

    def test_the_key_kind_must_be_declared_not_guessed(self, tmp_path):
        """Betfair's delayed keys carry a naming convention. Resting a correctness property
        on a convention is how a scanner arbs five-minute-old prices and believes itself."""

        (tmp_path / "app_key").write_text("APPKEY123")
        (tmp_path / "username").write_text("someone@example.com")

        with pytest.raises(ValueError, match="declared rather than guessed"):
            BetfairCredentials.load(tmp_path)

    def test_declaring_both_kinds_is_also_refused(self, tmp_path):
        creds(tmp_path)
        (tmp_path / "delayed").write_text("")

        with pytest.raises(ValueError):
            BetfairCredentials.load(tmp_path)


class TestADeadSessionIsNotAQuietMarket:
    def test_an_expired_token_raises_rather_than_returning_no_prices(self, tmp_path):
        session = BetfairSession(creds(tmp_path), transport=transport(fault="INVALID_SESSION_INFORMATION"))

        with pytest.raises(SessionExpired):
            session.call("https://x/listMarketCatalogue/", {})

    def test_the_source_reports_unreachable_rather_than_an_empty_market(self, tmp_path):
        quote = source(tmp_path, fault="INVALID_SESSION_INFORMATION").quote("1.234")

        assert quote.status == UNREACHABLE
        assert quote.legs == ()
        assert "unknown, not absent" in quote.describe()

    def test_re_authentication_is_attempted_exactly_once(self, tmp_path):
        """A login loop against a refused credential hammers the identity service and
        eventually locks the account."""

        post = transport(fault="INVALID_SESSION_INFORMATION")
        session = BetfairSession(creds(tmp_path), transport=post)

        with pytest.raises(SessionExpired):
            session.call("https://x/listMarketCatalogue/", {})

        logins = [c for c in post.calls if "identitysso" in c[0]]
        assert len(logins) == 2

    def test_a_refused_login_is_not_a_silent_empty_session(self, tmp_path):
        session = BetfairSession(creds(tmp_path), transport=transport(login_status="FAIL"))

        with pytest.raises(SessionExpired):
            session.login()

    def test_a_login_returning_no_token_is_refused(self, tmp_path):
        session = BetfairSession(creds(tmp_path), transport=transport(token=""))

        with pytest.raises(SessionExpired):
            session.login()


class TestRulesAreRequiredNotOptional:
    def test_a_market_without_rules_yields_no_legs(self, tmp_path):
        """AG-02 compares settlement wording verbatim. A leg built without it would let a
        settlement mismatch through unseen, which is how an arb becomes a coin flip."""

        bare = [{"marketName": "Match Odds", "description": {}, "runners": []}]
        quote = source(tmp_path, catalogue=bare, book=BOOK).quote("1.234")

        assert quote.status == UNREACHABLE
        assert "RULES_UNAVAILABLE" in quote.reason
        assert quote.legs == ()

    def test_the_rules_text_reaches_every_leg(self, tmp_path):
        quote = source(tmp_path, catalogue=CATALOGUE, book=BOOK).quote("1.234")

        assert quote.legs
        assert all(leg.settlement_rule == RULES for leg in quote.legs)


class TestPricesAndSizes:
    def test_only_the_size_at_the_best_price_is_taken(self, tmp_path):
        """availableToBack is a ladder. Summing it reports depth nobody can take at the
        quoted price."""

        quote = source(tmp_path, catalogue=CATALOGUE, book=BOOK).quote("1.234")
        team_a = next(leg for leg in quote.legs if leg.selection == "Team A")

        assert team_a.decimal_odds == 2.10
        assert team_a.max_stake == 500.0

    def test_exchange_sizes_are_marked_observed(self, tmp_path):
        quote = source(tmp_path, catalogue=CATALOGUE, book=BOOK).quote("1.234")

        assert quote.stake_is_observed is True
        assert "observed from the book" in quote.describe()

    def test_commission_travels_onto_every_leg(self, tmp_path):
        quote = source(tmp_path, catalogue=CATALOGUE, book=BOOK).quote("1.234")

        assert all(leg.commission_pct > 0 for leg in quote.legs)
        assert quote.legs[0].net_odds < quote.legs[0].decimal_odds

    def test_a_runner_with_no_offers_is_skipped_not_zero_priced(self, tmp_path):
        book = [{"runners": [{"selectionId": 1, "ex": {"availableToBack": []}}]}]
        quote = source(tmp_path, catalogue=CATALOGUE, book=book).quote("1.234")

        assert quote.legs == ()

    def test_selection_names_come_from_the_catalogue(self, tmp_path):
        quote = source(tmp_path, catalogue=CATALOGUE, book=BOOK).quote("1.234")

        assert {leg.selection for leg in quote.legs} == {"Team A", "Team B"}


class TestADelayedKeyIsLabelled:
    def test_a_delayed_quote_says_so_on_its_face(self, tmp_path):
        quote = source(tmp_path, delayed=True, catalogue=CATALOGUE, book=BOOK).quote("1.234")

        assert "DELAYED KEY" in quote.reason
        assert "no arb computed from them is real" in quote.reason

    def test_a_live_quote_carries_no_such_warning(self, tmp_path):
        quote = source(tmp_path, catalogue=CATALOGUE, book=BOOK).quote("1.234")

        assert "DELAYED" not in quote.reason


class TestTheOperatorNeverHandlesAToken:
    def test_the_token_is_minted_on_first_use(self, tmp_path):
        session = BetfairSession(creds(tmp_path), transport=transport())

        assert session.is_open is False
        session.headers()
        assert session.is_open is True

    def test_the_token_is_sent_as_x_authentication(self, tmp_path):
        session = BetfairSession(creds(tmp_path), transport=transport(token="SSOID-9"))

        headers = session.headers()

        assert headers["X-Authentication"] == "SSOID-9"
        assert headers["X-Application"] == "APPKEY123"

    def test_a_certificate_login_is_preferred_when_available(self, tmp_path):
        post = transport()
        session = BetfairSession(creds(tmp_path, cert=True), transport=post)

        session.login()

        assert any("certlogin" in call[0] for call in post.calls)


class TestMarketEnumerationIsBoundedAndStated:
    """A scan that has to be handed market IDs is not a scan.

    Two defaults are named rather than hidden, because both fail in the same tone as a
    correct answer. The wrong sport reports no arbs exactly like the right sport finding
    none, and an unbounded window returns thousands of markets months out whose prices are
    neither liquid nor comparable to a bookmaker's.
    """

    def _calls(self):
        seen = []

        def call(url, payload):
            seen.append((url, payload))
            return [{
                "marketId": "1.234567", "marketName": "Match Odds",
                "marketStartTime": "2026-08-09T14:00:00Z", "totalMatched": 48210.0,
                "event": {"name": "Arsenal v Chelsea"},
            }]

        return seen, call

    def _source(self, call):
        from connectors.betfair import BetfairCredentials, BetfairSession, BetfairSource

        session = BetfairSession(BetfairCredentials(
            app_key="k", username="u", password="p", delayed=True,
        ))
        session.call = call  # type: ignore[method-assign]
        return BetfairSource(session=session)

    def test_the_listing_carries_matched_volume_not_only_a_name(self):
        """A market with a price and no volume is a price nobody has taken."""

        seen, call = self._calls()

        listings = self._source(call).list_markets()

        assert listings[0].total_matched == 48210.0
        assert listings[0].market_id == "1.234567"

    def test_the_window_is_bounded_and_appears_in_the_filter(self):
        seen, call = self._calls()

        self._source(call).list_markets(within_hours=6)

        market_filter = seen[0][1]["filter"]["marketStartTime"]
        assert market_filter["from"] and market_filter["to"]
        assert market_filter["from"] < market_filter["to"]

    def test_only_markets_with_an_unambiguous_outcome_set_are_requested(self):
        """Totals and handicaps need a line as well as a side; find_arb needs the set."""

        seen, call = self._calls()

        self._source(call).list_markets()

        assert seen[0][1]["filter"]["marketTypeCodes"] == ["MATCH_ODDS"]

    def test_busiest_first_so_requests_are_spent_where_depth_is(self):
        seen, call = self._calls()

        self._source(call).list_markets()

        assert seen[0][1]["sort"] == "MAXIMUM_TRADED"

    def test_an_unconfigured_source_lists_nothing_rather_than_raising(self):
        from connectors.betfair import BetfairSource

        assert BetfairSource.from_directory("/tmp/definitely-not-here").list_markets() == ()
