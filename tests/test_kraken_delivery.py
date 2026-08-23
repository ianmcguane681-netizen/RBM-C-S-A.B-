"""The delivery path: what reaches a person, and what can reach the venue.

Two halves, and the properties that carry them are the ones that cost money to get wrong.

**A partial delivery is not a delivery.** Two channels are not a redundancy unless somebody
is told when one of them stops, so a fan-out that reported success whenever ANY channel
worked would let Discord fail silently for a month — and the person would find out on the
day Telegram also went down, which is the day it mattered.

**A dry run must never read as a fill.** `KrakenBroker.place` defaults to asking Kraken to
validate without placing, and returning FILLED for that would be the single worst bug the
adapter could contain.

**An entry with no exit is refused at construction.** A position with no stop is not a
smaller risk than one with a bad stop; it is an unbounded one.

**The forming candle is not a candle.** Deciding on the bar currently forming produces a
signal that appears at nine, vanishes at two and returns at six — three answers about one
day, none of which the backtest ever saw.
"""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from connectors.kraken import Bar
from connectors.kraken_exec import (
    NOT_CONFIGURED as KRAKEN_NOT_CONFIGURED,
)
from connectors.kraken_exec import (
    REJECTED,
    UNKNOWN,
    VALIDATED,
    Instruction,
    KrakenBroker,
    KrakenCredentials,
    _next_nonce,
    userref_for,
)
from lib.kraken_lane import scan, describe_scan
from lib.notify import (
    ALL_SENT,
    NONE_SENT,
    NOT_CONFIGURED,
    PARTIAL,
    REFUSED,
    SENT,
    Channels,
    Delivery,
    Discord,
    DiscordCredentials,
    signal_message,
    _redact,
    _now,
)
from lib.sizing import INDETERMINATE, SIZED
from lib.thesis import PERMITTED, Permission


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def responder(payload=b"", status=200):
    def opener(request, **kw):
        return FakeResponse(payload)
    return opener


def failing(error):
    def opener(request, **kw):
        raise error
    return opener


class FakeChannel:
    def __init__(self, name, status):
        self.name = name
        self._status = status
        self.sent = []

    @property
    def is_configured(self):
        return self._status != NOT_CONFIGURED

    def send(self, subject, body):
        self.sent.append((subject, body))
        return Delivery(self._status, _now(), subject, "fake")


# --------------------------------------------------------------------------------------
# Channels
# --------------------------------------------------------------------------------------


class TestAPartialDeliveryIsNotADelivery:
    def test_one_channel_failing_beside_one_working_is_partial(self):
        result = Channels([FakeChannel("A", SENT), FakeChannel("B", REFUSED)]).send("s", "b")
        assert result.status == PARTIAL
        assert result.reached_somebody

    def test_partial_names_which_channel_failed(self):
        result = Channels([FakeChannel("A", SENT), FakeChannel("B", REFUSED)]).send("s", "b")
        assert [name for name, _ in result.failures] == ["B"]

    def test_every_channel_working_is_all_sent(self):
        result = Channels([FakeChannel("A", SENT), FakeChannel("B", SENT)]).send("s", "b")
        assert result.status == ALL_SENT and not result.failures

    def test_every_channel_failing_is_none_sent(self):
        result = Channels([FakeChannel("A", REFUSED), FakeChannel("B", REFUSED)]).send("s", "b")
        assert result.status == NONE_SENT
        assert not result.reached_somebody

    def test_one_channel_failing_does_not_prevent_the_others_attempt(self):
        # Otherwise the first failure silences every channel after it, and the redundancy
        # is worth nothing precisely when it is needed.
        second = FakeChannel("B", SENT)
        Channels([FakeChannel("A", REFUSED), second]).send("s", "b")
        assert second.sent

    def test_an_unconfigured_channel_is_not_a_failure(self):
        # Having only Telegram set up is a choice, not an outage. Counting it as one trains
        # a reader to ignore the warning.
        result = Channels([FakeChannel("A", SENT), FakeChannel("B", NOT_CONFIGURED)]).send("s", "b")
        assert result.status == ALL_SENT

    def test_no_channel_at_all_is_not_configured_rather_than_a_failure(self):
        result = Channels([FakeChannel("B", NOT_CONFIGURED)]).send("s", "b")
        assert result.status == NOT_CONFIGURED
        assert "nothing was sent and nothing failed" in result.describe()


class TestDiscordAnswersDifferentlyFromTelegram:
    def test_an_empty_204_body_is_a_success(self, tmp_path):
        # Discord acknowledges with 204 and no body. A client written against Telegram's
        # {"ok": true} would read every success as a malformed reply.
        channel = Discord(DiscordCredentials("https://discord.com/api/webhooks/1/tok"),
                          opener=responder(b""), log_path=tmp_path / "n.json")
        assert channel.send("s", "b").status == SENT

    def test_an_http_error_is_refused_not_unreachable(self, tmp_path):
        channel = Discord(
            DiscordCredentials("https://discord.com/api/webhooks/1/tok"),
            opener=failing(urllib.error.HTTPError("u", 401, "no", {}, None)),
            log_path=tmp_path / "n.json",
        )
        assert channel.send("s", "b").status == REFUSED

    def test_the_webhook_never_appears_in_a_failure_reason(self, tmp_path):
        # The webhook URL IS the credential — anyone holding it can post to the channel.
        url = "https://discord.com/api/webhooks/1234567/SUPERSECRETTOKEN"
        channel = Discord(
            DiscordCredentials(url),
            opener=failing(urllib.error.HTTPError(url, 404, "gone", {}, None)),
            log_path=tmp_path / "n.json",
        )
        assert "SUPERSECRETTOKEN" not in channel.send("s", "b").reason

    def test_redaction_keeps_the_diagnosis_while_dropping_the_secret(self):
        redacted = _redact("HTTP 404 https://discord.com/api/webhooks/1/SECRET failed")
        assert "SECRET" not in redacted
        assert "HTTP 404" in redacted and "discord.com" in redacted

    def test_an_unconfigured_channel_sends_nothing_and_fails_nothing(self, tmp_path):
        channel = Discord(None, log_path=tmp_path / "n.json")
        assert channel.send("s", "b").status == NOT_CONFIGURED

    def test_a_webhook_that_is_not_a_url_is_not_credentials(self, tmp_path):
        (tmp_path / "webhook").write_text("paste your webhook here", encoding="utf-8")
        assert DiscordCredentials.load(tmp_path) is None

    def test_every_attempt_is_recorded_including_the_failures(self, tmp_path):
        log = tmp_path / "n.json"
        Discord(DiscordCredentials("https://discord.com/api/webhooks/1/t"),
                opener=responder(b""), log_path=log).send("s", "b")
        assert json.loads(log.read_text(encoding="utf-8"))[0]["status"] == SENT


class TestTheMessageCannotBeMistakenForAFill:
    def test_a_signal_message_says_nothing_was_placed(self):
        class FakeSignal:
            side, pair, strategy = "buy", "XBTUSD", "donchian-20"
            price, stop, target, volume, notional, risk_cash = 100.0, 95.0, 110.0, 1.0, 100.0, 5.0
            reward_to_risk = 2.0
            size = type("S", (), {"bound_by": "risk limit"})()

        subject, body = signal_message(FakeSignal())
        assert "NOTHING HAS BEEN PLACED" in body
        assert subject.startswith("SIGNAL")


# --------------------------------------------------------------------------------------
# The scan
# --------------------------------------------------------------------------------------


def rising(n=80, start_ts=1_700_000_000):
    return tuple(
        Bar(start_ts + i * 86400, 100 + i, 101 + i, 99 + i, 100 + i, 10.0)
        for i in range(n)
    )


class Peeker:
    """Records the last bar it was shown, so the forming-bar rule can be tested."""

    name, philosophy = "peeker", "a fixture"
    warmup, stop_atr, target_atr = 20, 2.0, 3.0

    def __init__(self):
        self.last_seen = None

    def signal_at(self, window):
        self.last_seen = window[-1].ts
        return 1


class TestTheFormingCandleIsNotACandle:
    def test_the_decision_is_made_on_the_last_CLOSED_bar(self):
        bars = rising()
        peeker = Peeker()
        scan({"T": bars}, peeker, balance=10_000, risk_pct=1.0,
             per_position_limit=500.0, depth_reader=None)
        assert peeker.last_seen == bars[-2].ts, "the forming bar must not decide"

    def test_the_signal_records_which_bar_decided_it(self):
        bars = rising()
        signals = scan({"T": bars}, Peeker(), balance=10_000, risk_pct=1.0,
                       per_position_limit=500.0, depth_reader=None)
        assert signals[0].decided_on == bars[-2].ts

    def test_the_entry_price_is_the_live_one_not_the_decision_bars(self):
        # Decide on the closed bar, execute at what the market is now — the shape the
        # backtest modelled.
        bars = rising()
        signals = scan({"T": bars}, Peeker(), balance=10_000, risk_pct=1.0,
                       per_position_limit=500.0, depth_reader=None)
        assert signals[0].price == bars[-1].close


class TestAnUnmeasuredConstraintRefusesRatherThanRaisesTheSize:
    def test_an_unread_order_book_makes_the_size_indeterminate(self):
        # The flattering direction is to size from the three constraints that DID measure,
        # which is always the larger number.
        signals = scan({"T": rising()}, Peeker(), balance=10_000, risk_pct=1.0,
                       per_position_limit=500.0, depth_reader=None)
        assert signals[0].size.status == INDETERMINATE
        assert not signals[0].actionable

    def test_a_read_order_book_produces_a_size(self):
        class Depth:
            usable, exitable_value = True, 1_000_000.0

        signals = scan({"T": rising()}, Peeker(), balance=10_000, risk_pct=1.0,
                       per_position_limit=500.0, depth_reader=lambda p: Depth())
        assert signals[0].size.status == SIZED
        assert signals[0].actionable and signals[0].volume > 0

    def test_an_unsizeable_signal_is_reported_and_not_dropped(self):
        signals = scan({"T": rising()}, Peeker(), balance=10_000, risk_pct=1.0,
                       per_position_limit=500.0, depth_reader=None)
        assert "NOT actionable" in describe_scan(signals, scanned=1)

    def test_a_market_that_could_not_be_read_is_named_in_the_scan(self):
        # A scan reporting only its hits cannot be told from one that reached two markets
        # of ten.
        described = describe_scan([], scanned=8, blind=("SOLUSD", "ADAUSD"))
        assert "COULD NOT BE READ" in described
        assert "SOLUSD" in described and "ADAUSD" in described
        assert "not quiet" in described


# --------------------------------------------------------------------------------------
# The venue adapter
# --------------------------------------------------------------------------------------


def permitted():
    return Permission(PERMITTED, "XBTUSD")


class TestAnEntryWithNoExitIsRefused:
    def test_an_instruction_without_a_stop_will_not_construct(self):
        with pytest.raises(ValueError, match="stop price is required"):
            Instruction("XBTUSD", "buy", 1.0, 0.0, permitted(), 1)

    def test_a_buys_stop_above_its_entry_is_refused(self):
        # As written that order stops out on arrival. Better caught here than at the venue.
        with pytest.raises(ValueError, match="stops out on arrival"):
            Instruction("XBTUSD", "buy", 1.0, 110.0, permitted(), 1, limit_price=100.0)

    def test_a_sells_stop_below_its_entry_is_refused(self):
        with pytest.raises(ValueError, match="stops out on arrival"):
            Instruction("XBTUSD", "sell", 1.0, 90.0, permitted(), 1, limit_price=100.0)

    def test_a_correctly_placed_stop_constructs(self):
        assert Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1, limit_price=100.0)


class TestADryRunMustNeverReadAsAFill:
    def broker(self, payload, tmp_path):
        (tmp_path / "key").write_text("k", encoding="utf-8")
        (tmp_path / "secret").write_text("c2VjcmV0", encoding="utf-8")
        return KrakenBroker(KrakenCredentials.load(tmp_path),
                            opener=responder(json.dumps(payload).encode()))

    def test_validate_is_the_default(self, tmp_path):
        broker = self.broker(
            {"error": [], "result": {"descr": {"order": "buy 1 XBTUSD @ limit 100"}}},
            tmp_path,
        )
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1))
        assert result.status == VALIDATED
        assert "DID NOT PLACE" in result.describe()

    def test_a_validated_order_is_not_treated_as_possibly_placed(self, tmp_path):
        broker = self.broker({"error": [], "result": {"descr": {"order": "x"}}}, tmp_path)
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1))
        assert not result.may_have_been_placed

    def test_placing_for_real_requires_saying_so(self, tmp_path):
        broker = self.broker({"error": [], "result": {"txid": ["TX-1"]}}, tmp_path)
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1),
                              validate=False)
        assert result.status != VALIDATED and result.txid == "TX-1"


class TestKrakenSaysNoWithHttp200:
    def broker(self, payload, tmp_path):
        (tmp_path / "key").write_text("k", encoding="utf-8")
        (tmp_path / "secret").write_text("c2VjcmV0", encoding="utf-8")
        return KrakenBroker(KrakenCredentials.load(tmp_path),
                            opener=responder(json.dumps(payload).encode()))

    def test_an_error_array_beside_a_result_is_a_rejection(self, tmp_path):
        # The exact shape a client checking only the status code reads as success — and
        # here that means recording a fill that never happened.
        broker = self.broker({"error": ["EOrder:Insufficient funds"], "result": {}},
                             tmp_path)
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1),
                              validate=False)
        assert result.status == REJECTED
        assert "Insufficient funds" in result.reason

    def test_no_error_and_no_txid_is_unknown_rather_than_success(self, tmp_path):
        broker = self.broker({"error": [], "result": {}}, tmp_path)
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1),
                              validate=False)
        assert result.status == UNKNOWN

    def test_a_timeout_is_unknown_and_may_have_been_placed(self, tmp_path):
        (tmp_path / "key").write_text("k", encoding="utf-8")
        (tmp_path / "secret").write_text("c2VjcmV0", encoding="utf-8")
        broker = KrakenBroker(KrakenCredentials.load(tmp_path),
                              opener=failing(TimeoutError("gave up")))
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1),
                              validate=False)
        assert result.status == UNKNOWN
        assert result.may_have_been_placed
        assert "DO NOT RESUBMIT" in result.describe()

    def test_a_4xx_is_a_rejection_rather_than_an_unknown(self, tmp_path):
        (tmp_path / "key").write_text("k", encoding="utf-8")
        (tmp_path / "secret").write_text("c2VjcmV0", encoding="utf-8")
        broker = KrakenBroker(
            KrakenCredentials.load(tmp_path),
            opener=failing(urllib.error.HTTPError("u", 400, "bad", {}, None)),
        )
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1),
                              validate=False)
        assert result.status == REJECTED
        assert not result.may_have_been_placed


class TestThePermissionIsRereadAtTheVenue:
    def test_an_unpermitted_instruction_is_rejected_before_anything_is_sent(self, tmp_path):
        (tmp_path / "key").write_text("k", encoding="utf-8")
        (tmp_path / "secret").write_text("c2VjcmV0", encoding="utf-8")
        sent = []

        def watching(request, **kw):
            sent.append(request)
            return FakeResponse(b'{"error": [], "result": {"txid": ["T"]}}')

        broker = KrakenBroker(KrakenCredentials.load(tmp_path), opener=watching)
        result = broker.place(
            Instruction("XBTUSD", "buy", 1.0, 95.0,
                        Permission("INDETERMINATE", "XBTUSD"), 1),
            validate=False,
        )
        assert result.status == REJECTED
        assert not sent, "nothing may reach the venue on an unpermitted instruction"

    def test_no_credentials_sends_nothing_and_says_which_directory(self):
        broker = KrakenBroker(None)
        result = broker.place(Instruction("XBTUSD", "buy", 1.0, 95.0, permitted(), 1))
        assert result.status == KRAKEN_NOT_CONFIGURED
        assert "~/.kraken" in result.reason


class TestTheNonceOnlyEverGoesUp:
    def test_a_clock_that_steps_backwards_does_not_reuse_a_nonce(self, tmp_path):
        # An NTP correction or a resumed VM produces a nonce Kraken has already seen, and
        # the rejection looks exactly like a rejected order.
        first = _next_nonce(tmp_path, now_ms=lambda: 1_000_000)
        second = _next_nonce(tmp_path, now_ms=lambda: 900_000)
        assert second > first

    def test_it_follows_the_clock_when_the_clock_is_sane(self, tmp_path):
        _next_nonce(tmp_path, now_ms=lambda: 1_000_000)
        assert _next_nonce(tmp_path, now_ms=lambda: 2_000_000) == 2_000_000

    def test_a_corrupt_marker_does_not_stop_a_nonce_being_issued(self, tmp_path):
        (tmp_path / "nonce").write_text("not a number", encoding="utf-8")
        assert _next_nonce(tmp_path, now_ms=lambda: 5_000) == 5_000


class TestTheReferenceIsDerivedFromTheIntent:
    def test_the_same_intent_gives_the_same_reference(self):
        # So an UNKNOWN can be resolved by asking Kraken about it, which is the only safe
        # move when the venue does not reject a duplicate.
        assert (userref_for("XBTUSD", "buy", 0.5, "t")
                == userref_for("XBTUSD", "buy", 0.5, "t"))

    def test_a_different_intent_gives_a_different_reference(self):
        assert (userref_for("XBTUSD", "buy", 0.5, "t")
                != userref_for("XBTUSD", "sell", 0.5, "t"))

    def test_it_fits_krakens_signed_32_bit_field(self):
        assert 0 <= userref_for("XBTUSD", "buy", 0.5, "t") <= 0x7FFFFFFF


class TestTheLaneIsRegisteredWhereItCanBeGated:
    def test_kraken_has_a_placer_so_it_is_not_refused_as_an_unknown_lane(self):
        from lib.placing import PLACERS

        assert "kraken" in PLACERS

    def test_and_a_broker_factory_beside_it(self):
        from lib.placing import BROKER_FACTORIES

        assert "kraken" in BROKER_FACTORIES
