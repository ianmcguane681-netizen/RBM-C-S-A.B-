"""A half-matched arb is worse than one that never went on.

An exchange partially matches as a matter of course — ask for £250 and get £80, because
that is all anyone was offering. For an ordinary bet that is a smaller bet. For an arbitrage
it is a £250 position hedged for £80 and an unhedged £170 on a selection nobody chose to
back: a directional position taken by accident, on an instrument with no sell button.

So `LEG_EXPOSED` is a first-class state, `NOTHING_PLACED` is the outcome to prefer over it,
and legs go on thinnest first — failing on the first leg costs nothing, failing on a later
one leaves money out.
"""
from __future__ import annotations

import pytest

from connectors.betfair_exec import (
    ALL_LEGS_MATCHED,
    LEG_EXPOSED,
    MATCHED,
    NOTHING_PLACED,
    NOT_CONFIGURED,
    PART_MATCHED,
    REJECTED,
    UNKNOWN,
    BetInstruction,
    BetfairExecutor,
    bet_ref,
)
from lib.http_retry import TransientRetrievalError
from lib.thesis import INDETERMINATE, PERMITTED, REFUSED, Permission


class FakeSession:
    """Replies in order; a callable reply is raised or invoked."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def call(self, url, payload):
        self.calls.append((url, payload))
        reply = self.replies.pop(0) if self.replies else {}
        if isinstance(reply, Exception):
            raise reply
        return reply


def report(matched=250.0, requested=250.0, order_status="EXECUTION_COMPLETE",
           status="SUCCESS", error=None):
    row = {"status": "FAILURE" if error else "SUCCESS", "orderStatus": order_status,
           "sizeMatched": matched, "averagePriceMatched": 2.16, "betId": "b1",
           "customerOrderRef": "eb-x"}
    if error:
        row["errorCode"] = error
    return {"status": status, "instructionReports": [row]}


def permission(status=PERMITTED):
    return Permission(status, "market", (("board evidence", "MET", "clean"),))


def instruction(size=250.0, selection=1, available=250.0, status=PERMITTED, price=2.16):
    return BetInstruction("1.234567", selection, "BACK", size, price, permission(status),
                          bet_ref("1.234567", selection, "BACK", size, price, "t"),
                          available_when_seen=available)


class TestAPartialMatchIsNotASmallerArb:
    def test_a_short_match_marked_complete_is_corrected_to_part_matched(self):
        executor = BetfairExecutor(FakeSession(report(matched=80.0, requested=250.0)))

        result = executor.place_bet(instruction(size=250.0))

        assert result.status == PART_MATCHED
        assert result.unmatched_size == pytest.approx(170.0)

    def test_one_matched_leg_and_one_failed_leg_is_leg_exposed(self):
        executor = BetfairExecutor(FakeSession(
            report(matched=250.0), report(matched=0.0, order_status="EXPIRED"),
        ))

        execution = executor.place_arb([instruction(selection=1), instruction(selection=2)])

        assert execution.status == LEG_EXPOSED

    def test_the_exposure_is_reported_as_a_number_and_shouted_about(self):
        executor = BetfairExecutor(FakeSession(
            report(matched=250.0), report(matched=80.0, requested=250.0),
        ))

        execution = executor.place_arb([instruction(selection=1), instruction(selection=2)])
        text = execution.describe()

        assert execution.exposure == pytest.approx(170.0)
        assert "not a smaller arb" in text
        assert "needs a person NOW" in text

    def test_nothing_matched_is_the_cheap_failure_and_says_so(self):
        executor = BetfairExecutor(FakeSession(report(matched=0.0, order_status="EXPIRED")))

        execution = executor.place_arb([instruction(selection=1), instruction(selection=2)])

        assert execution.status == NOTHING_PLACED
        assert "cheap failure" in execution.describe()

    def test_all_legs_matched_refuses_to_imply_profit(self):
        executor = BetfairExecutor(FakeSession(report(), report()))

        execution = executor.place_arb([instruction(selection=1), instruction(selection=2)])

        assert execution.status == ALL_LEGS_MATCHED
        assert "not thereby a profitable one" in execution.describe()


class TestSequencingPutsTheThinnestLegFirst:
    def test_the_leg_with_least_available_stake_goes_first(self):
        """Failing on the first leg costs nothing; failing on a later one leaves money out."""

        session = FakeSession(report(), report())
        executor = BetfairExecutor(session)

        executor.place_arb([
            instruction(selection=1, available=5000.0),
            instruction(selection=2, available=250.0),
        ])

        first_payload = session.calls[0][1]
        assert first_payload["instructions"][0]["selectionId"] == 2

    def test_a_failed_first_leg_stops_the_rest_from_going_on(self):
        session = FakeSession(report(matched=0.0, order_status="EXPIRED"), report())
        executor = BetfairExecutor(session)

        executor.place_arb([instruction(selection=1), instruction(selection=2)])

        assert len(session.calls) == 1

    def test_a_single_leg_is_not_an_arb_and_places_nothing(self):
        session = FakeSession(report())

        execution = BetfairExecutor(session).place_arb([instruction()])

        assert execution.status == NOTHING_PLACED
        assert session.calls == []


class TestAnUnknownPlacementIsNeverUnplaced:
    def test_a_timeout_is_unknown(self):
        executor = BetfairExecutor(FakeSession(TransientRetrievalError("timed out")))

        assert executor.place_bet(instruction()).status == UNKNOWN

    def test_unknown_says_a_bet_is_irreversible_and_not_to_re_place(self):
        described = BetfairExecutor(
            FakeSession(TransientRetrievalError("x"))).place_bet(instruction()).describe()

        assert "irreversible once matched" in described
        assert "DO NOT RE-PLACE" in described

    def test_a_success_with_no_instruction_report_is_unknown_not_a_silent_success(self):
        executor = BetfairExecutor(FakeSession({"status": "SUCCESS"}))

        assert executor.place_bet(instruction()).status == UNKNOWN

    def test_an_explicit_failure_is_rejected_and_carries_the_error_code(self):
        executor = BetfairExecutor(FakeSession(report(error="INSUFFICIENT_FUNDS")))

        result = executor.place_bet(instruction())

        assert result.status == REJECTED
        assert "INSUFFICIENT_FUNDS" in result.reason

    def test_a_complete_order_matching_nothing_is_rejected_not_matched(self):
        """FILL_OR_KILL killed it at the asked price. No money is at risk."""

        executor = BetfairExecutor(FakeSession(report(matched=0.0)))

        assert executor.place_bet(instruction()).status == REJECTED


class TestNothingGoesOnWithoutPositivePermission:
    def test_a_refused_permission_places_nothing(self):
        session = FakeSession(report())

        result = BetfairExecutor(session).place_bet(instruction(status=REFUSED))

        assert result.status == REJECTED
        assert session.calls == []

    def test_indeterminate_is_not_a_weaker_yes(self):
        result = BetfairExecutor(FakeSession(report())).place_bet(
            instruction(status=INDETERMINATE))

        assert "not a weaker yes" in result.reason

    def test_an_unconfigured_executor_sends_nothing(self):
        result = BetfairExecutor(None).place_bet(instruction())

        assert result.status == NOT_CONFIGURED
        assert "nothing was sent" in result.reason


class TestTheReferenceDefeatsTheRetry:
    def test_the_same_intent_produces_the_same_reference(self):
        assert bet_ref("1.2", 3, "BACK", 250.0, 2.16, "t") == \
               bet_ref("1.2", 3, "BACK", 250.0, 2.16, "t")

    def test_a_different_price_is_a_different_bet(self):
        assert bet_ref("1.2", 3, "BACK", 250.0, 2.16, "t") != \
               bet_ref("1.2", 3, "BACK", 250.0, 2.18, "t")

    def test_the_reference_fits_betfairs_thirty_two_character_limit(self):
        assert len(bet_ref("1.234567", 12345, "BACK", 250.0, 2.16, "t")) <= 32

    def test_the_reference_contains_only_characters_betfair_accepts(self):
        import re

        assert re.fullmatch(r"[A-Za-z0-9.-]+", bet_ref("1.2", 3, "BACK", 250.0, 2.16, "t"))

    def test_an_instruction_without_a_reference_is_refused(self):
        with pytest.raises(ValueError, match="a retry and a second bet"):
            BetInstruction("1.2", 3, "BACK", 250.0, 2.16, permission(), "  ")


class TestTheOrderIsFillOrKill:
    def test_the_exchange_is_asked_to_refuse_rather_than_half_fill(self):
        """A partial match is the failure this module is named after."""

        session = FakeSession(report())

        BetfairExecutor(session).place_bet(instruction())

        limit = session.calls[0][1]["instructions"][0]["limitOrder"]
        assert limit["timeInForce"] == "FILL_OR_KILL"
