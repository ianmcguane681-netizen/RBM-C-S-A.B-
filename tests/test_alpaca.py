"""A submit that timed out is not a submit that did not happen.

Every other connector here reads, and a failed read means nothing happened. This one
writes, and that inverts what an unknown answer costs. If a SUBMIT times out the request
may well have reached the broker — reporting "not placed" invites a retry, and the retry
fills twice.

That is the repository's recurring defect at its most expensive: an unknown state read as
the flattering one, costing real money in seconds rather than eventually. So UNKNOWN is its
own status, it says on its face not to resubmit, and every order carries an id derived from
the INTENT rather than the moment, so a retry is refused by the broker as a duplicate
instead of accepted as a second order.
"""
from __future__ import annotations

import json
import urllib.error
from io import BytesIO

import pytest

from connectors.alpaca import (
    BUY,
    CANCELLED,
    FILLED,
    NOT_CONFIGURED,
    PART_FILLED,
    REJECTED,
    SELL,
    SUBMITTED,
    UNKNOWN,
    AlpacaBroker,
    AlpacaCredentials,
    Instruction,
    Quote,
    instruction_id,
)
from lib.http_retry import TransientRetrievalError
from lib.thesis import INDETERMINATE, PERMITTED, REFUSED, Permission


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def responder(payload=None, *, error=None):
    def _open(request, **_kw):
        if error is not None:
            raise error
        return FakeResponse(json.dumps(payload or {}).encode())

    return _open


def broker(payload=None, *, error=None, paper=True):
    return AlpacaBroker(
        AlpacaCredentials("key", "secret", paper=paper), opener=responder(payload, error=error)
    )


def permission(status=PERMITTED):
    return Permission(status, "AAPL", (("board evidence", "MET", "clean"),))


def instruction(status=PERMITTED, symbol="AAPL", side=BUY, qty=10.0):
    return Instruction(symbol, side, qty, permission(status),
                       instruction_id(symbol, side, qty, "2026-08-02T19:00:00Z"))


class TestAnUnknownOutcomeIsNeverUnplaced:
    def test_a_timeout_on_submit_is_unknown_not_a_failure_to_place(self):
        result = broker(error=TransientRetrievalError("timed out")).place(instruction())

        assert result.status == UNKNOWN

    def test_unknown_says_on_its_face_not_to_resubmit(self):
        described = broker(error=TransientRetrievalError("timed out")).place(
            instruction()).describe()

        assert "NOT a report that the order was not placed" in described
        assert "DO NOT RESUBMIT" in described

    def test_unknown_reports_that_a_retry_could_double_fill(self):
        result = broker(error=TransientRetrievalError("x")).place(instruction())

        assert result.may_have_been_placed is True

    def test_a_5xx_is_unknown_because_the_broker_may_have_taken_it(self):
        error = urllib.error.HTTPError("u", 503, "unavailable", {}, None)

        assert broker(error=error).place(instruction()).status == UNKNOWN

    def test_a_4xx_is_a_refusal_because_the_broker_decided(self):
        """A rejection is a fact. It is not an unknown and a retry is safe."""

        error = urllib.error.HTTPError("u", 422, "insufficient buying power", {}, None)
        result = broker(error=error).place(instruction())

        assert result.status == REJECTED
        assert result.may_have_been_placed is False

    def test_an_unrecognised_broker_status_is_unknown_rather_than_guessed(self):
        result = broker({"status": "something_new", "symbol": "AAPL"}).place(instruction())

        assert result.status == UNKNOWN
        assert "unrecognised broker status" in result.reason


class TestTheOrderIdDefeatsTheRetry:
    def test_the_same_intent_produces_the_same_id(self):
        first = instruction_id("AAPL", BUY, 10.0, "2026-08-02T19:00:00Z")
        second = instruction_id("AAPL", BUY, 10.0, "2026-08-02T19:00:00Z")

        assert first == second

    def test_a_different_quantity_is_a_different_order(self):
        assert instruction_id("AAPL", BUY, 10.0, "t") != instruction_id("AAPL", BUY, 11.0, "t")

    def test_a_different_thesis_is_a_different_order(self):
        assert instruction_id("AAPL", BUY, 10.0, "a") != instruction_id("AAPL", BUY, 10.0, "b")

    def test_an_instruction_without_an_id_is_refused(self):
        with pytest.raises(ValueError, match="fills twice"):
            Instruction("AAPL", BUY, 10.0, permission(), "  ")


class TestNothingIsPlacedWithoutPositivePermission:
    def test_a_refused_permission_is_not_sent(self):
        result = broker({"status": "filled"}).place(instruction(REFUSED))

        assert result.status == REJECTED
        assert "not PERMITTED" in result.reason

    def test_indeterminate_is_not_treated_as_a_weaker_yes(self):
        result = broker({"status": "filled"}).place(instruction(INDETERMINATE))

        assert result.status == REJECTED
        assert "not a weaker yes" in result.reason

    def test_an_unconfigured_broker_sends_nothing_and_says_so(self):
        result = AlpacaBroker(None).place(instruction())

        assert result.status == NOT_CONFIGURED
        assert "nothing was sent" in result.reason


class TestPaperAndLiveMustBeDeclared:
    def _dir(self, tmp_path, *markers):
        root = tmp_path / ".alpaca"
        root.mkdir()
        (root / "key_id").write_text("k", encoding="utf-8")
        (root / "secret_key").write_text("s", encoding="utf-8")
        for marker in markers:
            (root / marker).write_text("", encoding="utf-8")
        return root

    def test_neither_marker_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="not a bug you find later"):
            AlpacaCredentials.load(self._dir(tmp_path))

    def test_both_markers_are_refused(self, tmp_path):
        with pytest.raises(ValueError):
            AlpacaCredentials.load(self._dir(tmp_path, "paper", "live"))

    def test_paper_selects_the_paper_endpoint(self, tmp_path):
        found = AlpacaCredentials.load(self._dir(tmp_path, "paper"))

        assert found.paper is True
        assert "paper-api" in found.base

    def test_live_selects_the_live_endpoint(self, tmp_path):
        found = AlpacaCredentials.load(self._dir(tmp_path, "live"))

        assert "paper-api" not in found.base

    def test_an_unconfigured_broker_reports_none_rather_than_live(self, tmp_path):
        """False would read as 'live', which is the wrong way to be wrong."""

        assert AlpacaBroker.from_directory(tmp_path / "nothing").is_paper is None

    def test_an_undeclared_directory_loads_as_unconfigured_rather_than_raising(self, tmp_path):
        assert AlpacaBroker.from_directory(self._dir(tmp_path)).is_configured is False


class TestFillsAreReportedHonestly:
    def test_a_short_fill_marked_filled_is_corrected_to_part_filled(self):
        """Checked rather than trusted: a 'filled' with a short quantity is not complete."""

        result = broker({
            "status": "filled", "symbol": "AAPL", "qty": "10", "filled_qty": "4",
            "filled_avg_price": "200.5", "id": "abc",
        }).place(instruction())

        assert result.status == PART_FILLED

    def test_part_filled_says_the_position_is_smaller_than_the_one_sized(self):
        described = broker({
            "status": "partially_filled", "symbol": "AAPL", "qty": "10",
            "filled_qty": "4", "filled_avg_price": "200.5",
        }).place(instruction()).describe()

        assert "smaller than the one that was sized" in described

    def test_a_complete_fill_is_filled(self):
        result = broker({
            "status": "filled", "symbol": "AAPL", "qty": "10", "filled_qty": "10",
            "filled_avg_price": "200.5",
        }).place(instruction())

        assert result.status == FILLED

    def test_a_404_on_lookup_means_never_accepted_rather_than_unknown(self):
        error = urllib.error.HTTPError("u", 404, "not found", {}, None)

        assert broker(error=error).order_by_client_id("eb-x").status == CANCELLED


class TestQuotesCarryTheirSize:
    def test_a_two_sided_quote_is_returned_with_both_sizes(self):
        found = broker({"quote": {"bp": 200.0, "bs": 300, "ap": 200.1, "as": 500,
                                  "t": "2026-08-02T19:00:00Z"}}).quote("AAPL")

        assert found.bid_size == 300 and found.ask_size == 500

    def test_a_one_sided_quote_is_not_a_price(self):
        """Returning the side that exists lets a caller size against an empty market."""

        assert broker({"quote": {"bp": 200.0, "bs": 300, "ap": 0, "as": 0}}).quote("A") is None

    def test_the_executable_price_is_never_the_mid(self):
        quote = Quote("AAPL", 200.0, 300, 200.10, 500, "t")

        assert quote.executable_price(BUY) == 200.10
        assert quote.executable_price(SELL) == 200.00
        assert quote.mid == pytest.approx(200.05)
