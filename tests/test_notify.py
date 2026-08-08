"""Silence must mean one thing, and a notification that failed must not look like one that
was never needed.

A system that messages you only when it finds something has a defect in its quietest state.
No message can mean nothing was found, or the supervisor stopped, or the token expired, or
the lane could not reach its source — four facts and one silence, and the flattering
reading is the one a person adopts. Worse, the trust compounds: you stop opening the
dashboard BECAUSE the messages are reliable, and then the messages stop.

So there is a heartbeat whose absence is the alarm, and every send is recorded with its
outcome so `status.py` can tell "nothing happened" from "nothing was sent".

The four delivery states are kept apart for the usual reason: each sends a person somewhere
different. NOT_CONFIGURED is not a failure — somebody who never set up Telegram has not had
a notification fail, and reporting REFUSED would send them hunting a broken token they
never made.

Content is tested too, because a message you cannot act on is a message that arrived and
did nothing. Ian chose full detail on both lanes on 2026-08-08: arb carries selection,
books, odds, stake and guaranteed return because odds move while you go and look; stocks
carries shares, ticker, price and the thesis reason.
"""
from __future__ import annotations

import json
import urllib.error
from dataclasses import dataclass

import pytest

from lib.notify import (
    NOT_CONFIGURED,
    REFUSED,
    SENT,
    UNREACHABLE,
    Telegram,
    TelegramCredentials,
    arb_message,
    blind_lane_message,
    breaker_message,
    heartbeat_message,
    stocks_message,
)


class Answer:
    """Enough of an HTTP response for the sender to read."""

    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def telegram(tmp_path, opener=None, configured=True):
    return Telegram(
        TelegramCredentials("bot-token-123", "chat-456") if configured else None,
        opener=opener or (lambda *a, **kw: Answer({"ok": True})),
        log_path=tmp_path / "notifications.json",
    )


@dataclass
class Leg:
    book: str
    selection: str
    decimal_odds: float
    stake: float
    settlement_rule: str = ""


@dataclass
class Slip:
    market: str = "Everton v Spurs"
    legs: tuple = ()
    total_stake: float = 100.0
    guaranteed_return: float = 103.5
    observed_at: str = "2026-08-08T18:00:00Z"


@dataclass
class Order:
    ticker: str = "ALAB"
    side: str = "buy"
    shares: int = 1
    price: float = 333.99
    cash: float = 333.99
    currency: str = "USD"
    bound_by: str = "risk limit"
    at: str = "2026-08-08T18:00:00Z"


@dataclass
class Thesis:
    reasoning: str = "AI infrastructure: data movement between accelerators."
    expires_at: str = "2027-01-01T00:00:00Z"


class TestTheFourDeliveryStates:
    def test_a_sent_message_is_recorded_as_sent(self, tmp_path):
        assert telegram(tmp_path).send("subject", "body").status == SENT

    def test_no_credentials_is_not_a_failure(self, tmp_path):
        """Somebody who never set Telegram up has not had a notification fail."""

        delivery = telegram(tmp_path, configured=False).send("s", "b")

        assert delivery.status == NOT_CONFIGURED
        assert "nothing was sent and nothing failed" in delivery.describe()

    def test_the_service_saying_no_is_refused_not_unreachable(self, tmp_path):
        """A bad token wants a person. A dead network wants a retry. Different remedies."""

        def refuse(*_a, **_kw):
            raise urllib.error.HTTPError("u", 401, "Unauthorized", None, None)

        assert telegram(tmp_path, opener=refuse).send("s", "b").status == REFUSED

    def test_an_ok_false_payload_is_refused_even_on_a_200(self, tmp_path):
        """Telegram answers 200 with ok:false. A 200 is not a delivery."""

        opener = lambda *a, **kw: Answer({"ok": False, "description": "chat not found"})
        delivery = telegram(tmp_path, opener=opener).send("s", "b")

        assert delivery.status == REFUSED
        assert "chat not found" in delivery.reason

    def test_nothing_answering_is_unreachable(self, tmp_path):
        def dead(*_a, **_kw):
            raise urllib.error.URLError("no route to host")

        assert telegram(tmp_path, opener=dead).send("s", "b").status == UNREACHABLE


class TestAFailedSendIsAnEventNotANonEvent:
    def test_every_attempt_is_recorded_including_the_failures(self, tmp_path):
        """An operator who has heard nothing for two days must be able to tell
        "nothing happened" from "nothing was sent"."""

        def dead(*_a, **_kw):
            raise urllib.error.URLError("down")

        telegram(tmp_path, opener=dead).send("first", "b")
        telegram(tmp_path).send("second", "b")

        rows = json.loads((tmp_path / "notifications.json").read_text())
        assert [r["status"] for r in rows] == [UNREACHABLE, SENT]

    def test_a_send_never_raises_so_a_lane_survives_a_messaging_outage(self, tmp_path):
        """The lane's job is the money. Taking a run down because Telegram is down turns
        an outage into a missed opportunity, which is the opposite of the point."""

        def explode(*_a, **_kw):
            raise OSError("socket exploded")

        assert telegram(tmp_path, opener=explode).send("s", "b").status == UNREACHABLE

    def test_an_unwritable_log_does_not_lose_the_message(self, tmp_path):
        """Recording is best effort. Losing the record must not lose the notification."""

        blocked = Telegram(TelegramCredentials("t", "c"),
                           opener=lambda *a, **kw: Answer({"ok": True}),
                           log_path=tmp_path / "no" / "such" / "dir" / "x.json")
        blocked.log_path = tmp_path  # a directory, so the write fails

        assert blocked.send("s", "b").status == SENT

    def test_the_bot_token_never_appears_in_a_recorded_reason(self, tmp_path):
        """Error strings quote the request URL back, and the token lives in that path."""

        def refuse(*_a, **_kw):
            raise urllib.error.HTTPError(
                "https://api.telegram.org/botSECRET-TOKEN/sendMessage", 401, "no", None, None)

        telegram(tmp_path, opener=refuse).send("s", "b")
        written = (tmp_path / "notifications.json").read_text()

        assert "SECRET-TOKEN" not in written


class TestSilenceMustMeanOneThing:
    def test_the_heartbeat_reports_lanes_that_found_nothing(self, tmp_path):
        """A digest listing only findings is indistinguishable from one that never sent."""

        @dataclass
        class Lane:
            lane: str
            status: str
            reason: str = ""

        _, body = heartbeat_message([Lane("arb", "NOTHING_FOUND"), Lane("stocks", "REFUSED")])

        assert "arb" in body and "NOTHING_FOUND" in body

    def test_the_heartbeat_says_its_own_absence_is_the_alarm(self):
        _, body = heartbeat_message([])

        assert "heartbeat" in body
        assert "before assuming a quiet market" in body

    def test_a_blind_lane_says_nothing_was_established(self):
        """COULD_NOT_LOOK is the state a quiet market is most often mistaken for."""

        _, body = blind_lane_message("arb", 3, "all sources failed")

        assert "NOT a report that there was nothing to find" in body


class TestTheMessageCanBeActedOnWithoutOpeningAnything:
    def _arb(self):
        return arb_message(Slip(legs=(
            Leg("William Hill", "Everton", 2.10, 50.0),
            Leg("Betfair", "Draw or Spurs", 2.05, 50.0),
        )))

    def test_arb_carries_selection_books_odds_and_stake(self):
        """Odds move while you go and look, so the message must be sufficient alone."""

        _, body = self._arb()

        for expected in ("William Hill", "Everton", "2.100", "50.00", "Betfair"):
            assert expected in body, expected

    def test_arb_states_the_profit_and_the_return_separately(self):
        subject, body = self._arb()

        assert "GUARANTEED RETURN" in body
        assert "+3.50" in body
        assert "+3.50" in subject

    def test_arb_warns_that_the_aggregator_stake_is_not_the_books_stake(self):
        """Available stake is read AT THE BOOK, never from a feed. Placing on the feed's
        number is how a slip that priced correctly gets half-filled."""

        _, body = self._arb()

        assert "Re-check both books" in body

    def test_stocks_carries_shares_ticker_price_and_why(self):
        subject, body = stocks_message(Order(), thesis=Thesis())

        assert "1 × ALAB" in body
        assert "333.99" in body
        assert "AI infrastructure" in body
        assert "ALAB" in subject

    def test_stocks_names_the_binding_constraint(self):
        """Which limit sized it is the difference between "small" and "correctly small"."""

        _, body = stocks_message(Order(bound_by="volatility bound"), thesis=Thesis())

        assert "volatility bound" in body

    def test_stocks_says_so_when_no_reasoning_is_attached(self):
        """An instruction with no stated reason must not look complete."""

        _, body = stocks_message(Order(), thesis=None)

        assert "no thesis reasoning was attached" in body

    def test_stocks_says_the_price_is_the_ask(self):
        _, body = stocks_message(Order(), thesis=Thesis())

        assert "not the mid" in body


class TestABreakerNeedsAPerson:
    def test_it_says_the_breaker_will_not_clear_itself(self):
        @dataclass
        class State:
            reason: str = "4 consecutive losses"

        _, body = breaker_message("stocks", State())

        assert "does not reset on a timer" in body
        assert "4 consecutive losses" in body


class TestTruncation:
    def test_a_long_message_keeps_its_tail(self, tmp_path):
        """Telegram truncates around 4096 characters and the tail is where the binding
        constraint and the timestamp live, so the middle goes instead."""

        captured = {}

        def capture(request, *_a, **_kw):
            captured["data"] = request.data.decode("utf-8")
            return Answer({"ok": True})

        telegram(tmp_path, opener=capture).send("subject", "A" * 5000 + "TAILMARKER")

        assert "TAILMARKER" in captured["data"]
        assert "trimmed" in captured["data"]
