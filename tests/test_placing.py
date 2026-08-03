"""The only step that cannot be undone, and the two orderings that make it survivable.

**The position is recorded before the order is sent.** That looks backwards and is the only
safe way round. Placing first leaves a window where the process can die between sending and
recording, and on the far side of that window is a real position nothing in this system
knows about — invisible to the breakers, invisible to exposure, found when a statement
arrives. Recording first can leave a phantom for an order the broker rejected, which is
visible and fixed in one command. Over-reporting exposure is the direction to fail in.

**UNKNOWN is not a failure to place.** A 5xx or a timeout means the order may exist.
Resubmitting is how you fill twice. The position is recorded as UNKNOWN, and `lib.operating`
then drops the lane to owner-operating on its own, because a lane that does not know its own
exposure has no business opening more.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from connectors.alpaca import (
    FILLED,
    PART_FILLED,
    REJECTED,
    UNKNOWN,
    OrderResult,
)
from lib.operating import AUTONOMOUS, OWNER_OPERATING_MANUALLY, Mode, operating_mode
from lib.outcomes import OutcomeLedger
from lib.placing import (
    NOT_PLACED,
    PLACED,
    REFUSED,
    UNRESOLVED,
    describe_placements,
    place_harvest,
)
from lib.stocks_reaper import StockOrder
from lib.thesis import PERMITTED, Permission

TICKER = "MODN"


def order(shares=49, price=100.02):
    return StockOrder(ticker=TICKER, side="buy", shares=shares, price=price,
                      cash=round(shares * price, 2), currency="USD",
                      bound_by="risk limit", sizing=None, at="2026-08-03T12:00:00Z")


class Harvest:
    def __init__(self, status="READY", lane="stocks", instruction=None,
                 permission=None):
        self.status = status
        self.lane = lane
        self.subject = TICKER
        self.instruction = order() if instruction is None else instruction
        self.permission = permission or Permission(PERMITTED, TICKER, ())


class Broker:
    """Records what it was asked to do, and answers however the test needs."""

    def __init__(self, result=None):
        self.result = result
        self.calls: list = []

    def place(self, instruction):
        self.calls.append(instruction)
        if self.result is not None:
            return self.result
        return OrderResult(FILLED, TICKER, instruction.client_order_id,
                           broker_order_id="brk-1",
                           filled_quantity=instruction.quantity,
                           requested_quantity=instruction.quantity,
                           filled_avg_price=100.02)


def autonomous():
    return Mode("stocks", AUTONOMOUS, "CONFIG", "the config states it.")


def manual():
    return Mode("stocks", OWNER_OPERATING_MANUALLY, "FILE", "data/MANUAL exists.")


def ledger(tmp_path):
    return OutcomeLedger(tmp_path / "outcomes.json")


def place(tmp_path, *, harvest=None, mode=None, broker=None, book=None):
    return place_harvest(
        harvest or Harvest(), mode=mode or autonomous(),
        ledger=book if book is not None else ledger(tmp_path),
        broker=broker if broker is not None else Broker(),
        thesis_declared_at="2026-08-02T09:00:00Z")


class TestTheModeDecidesWhetherAnythingIsSent:
    def test_autonomous_places(self, tmp_path):
        broker = Broker()

        result = place(tmp_path, broker=broker)

        assert result.status == PLACED
        assert len(broker.calls) == 1

    def test_owner_operating_sends_nothing(self, tmp_path):
        broker = Broker()

        result = place(tmp_path, mode=manual(), broker=broker)

        assert result.status == NOT_PLACED
        assert broker.calls == []

    def test_and_it_says_the_instruction_is_waiting_for_you(self, tmp_path):
        result = place(tmp_path, mode=manual())

        assert "you place it" in result.reason

    def test_a_halted_lane_sends_nothing(self, tmp_path):
        halted = Mode("stocks", "HALTED", "FILE", "data/HALT exists.")

        assert place(tmp_path, mode=halted).status == NOT_PLACED

    def test_the_real_mode_function_agrees(self, tmp_path):
        """No hand-built Mode: the switch a person actually flips must stop this."""

        from lib.operating import take_the_wheel

        take_the_wheel(tmp_path, "taking over")
        mode = operating_mode("stocks", directory=tmp_path, config_autonomous=True)

        assert place(tmp_path, mode=mode).status == NOT_PLACED


class TestOnlyAReadyHarvestIsPlaceable:
    @pytest.mark.parametrize("status", ["REFUSED", "INDETERMINATE", "NOTHING_FOUND",
                                        "COULD_NOT_LOOK"])
    def test_nothing_else_is_sent(self, tmp_path, status):
        broker = Broker()

        result = place(tmp_path, harvest=Harvest(status=status), broker=broker)

        assert result.status == NOT_PLACED
        assert broker.calls == []

    def test_the_refusal_names_what_ready_means(self, tmp_path):
        result = place(tmp_path, harvest=Harvest(status="INDETERMINATE"))

        assert "screened, un-vetoed, authorised and sized" in result.reason


class TestTwoLanesHaveNoAdapterOnPurpose:
    def test_arb_is_not_placed_and_says_the_slip_is_the_deliverable(self, tmp_path):
        result = place(tmp_path, harvest=Harvest(lane="arb"))

        assert result.status == NOT_PLACED
        assert "The slip IS the deliverable" in result.reason

    def test_crypto_is_not_placed_and_says_it_cannot_sign(self, tmp_path):
        result = place(tmp_path, harvest=Harvest(lane="crypto"))

        assert result.status == NOT_PLACED
        assert "no key path" in result.reason

    def test_neither_reaches_the_broker(self, tmp_path):
        broker = Broker()

        for lane in ("arb", "crypto"):
            place(tmp_path, harvest=Harvest(lane=lane), broker=broker)

        assert broker.calls == []


class TestTheRecordComesFirst:
    def test_a_position_exists_before_the_broker_is_called(self, tmp_path):
        """The broker asserts it mid-call, which is the only way to prove the ordering."""

        book = ledger(tmp_path)
        seen: list[int] = []

        class Watching(Broker):
            def place(self, instruction):
                seen.append(len(OutcomeLedger(tmp_path / "outcomes.json").positions))
                return super().place(instruction)

        place(tmp_path, book=book, broker=Watching())

        assert seen == [1]

    def test_a_filled_order_leaves_the_position_open(self, tmp_path):
        """A filled BUY is money at risk. It settles when the holding is closed."""

        book = ledger(tmp_path)

        result = place(tmp_path, book=book)

        assert book.get(result.position_id).status == "OPEN"

    def test_the_recorded_stake_is_the_cash_that_went_in(self, tmp_path):
        book = ledger(tmp_path)

        result = place(tmp_path, book=book)

        assert book.get(result.position_id).staked == pytest.approx(4900.98)

    def test_a_rejected_order_leaves_a_void_rather_than_a_phantom(self, tmp_path):
        book = ledger(tmp_path)
        broker = Broker(OrderResult(REJECTED, TICKER, "eb-x", reason="insufficient buying power"))

        result = place(tmp_path, book=book, broker=broker)

        assert result.status == NOT_PLACED
        assert book.get(result.position_id).status == "VOID"
        assert book.unsettled_exposure() == 0.0

    def test_the_void_says_nothing_is_at_risk(self, tmp_path):
        book = ledger(tmp_path)
        broker = Broker(OrderResult(REJECTED, TICKER, "eb-x", reason="no buying power"))

        result = place(tmp_path, book=book, broker=broker)

        assert "nothing is at risk" in book.get(result.position_id).note

    def test_an_unrecordable_order_is_refused_before_anything_is_sent(self, tmp_path):
        """An order nobody can record is one no breaker will ever see."""

        (tmp_path / "outcomes.json").write_text("{not json", encoding="utf-8")
        broker = Broker()

        result = place(tmp_path, broker=broker)

        assert result.status == REFUSED
        assert broker.calls == []
        assert "no breaker will ever see" in result.reason


class TestUnknownIsNotAFailureToPlace:
    def _unresolved(self, tmp_path, book=None):
        broker = Broker(OrderResult(UNKNOWN, TICKER, "eb-x", requested_quantity=49,
                                    reason="HTTP 503: upstream timeout"))
        return place(tmp_path, book=book or ledger(tmp_path), broker=broker), broker

    def test_it_reports_unresolved_rather_than_not_placed(self, tmp_path):
        result, _ = self._unresolved(tmp_path)

        assert result.status == UNRESOLVED

    def test_the_position_is_recorded_as_unknown_not_removed(self, tmp_path):
        book = ledger(tmp_path)

        result, _ = self._unresolved(tmp_path, book)

        assert book.get(result.position_id).status == "UNKNOWN"

    def test_it_still_counts_as_exposure(self, tmp_path):
        book = ledger(tmp_path)

        self._unresolved(tmp_path, book)

        assert book.unsettled_exposure("stocks") == pytest.approx(4900.98)

    def test_it_says_not_to_resubmit(self, tmp_path):
        result, _ = self._unresolved(tmp_path)

        assert "DO NOT RESUBMIT" in result.describe()

    def test_it_drops_the_lane_to_owner_operating_without_any_extra_wiring(self, tmp_path):
        """The stop is automatic: lib.operating reads the ledger and does it."""

        book = ledger(tmp_path)
        self._unresolved(tmp_path, book)
        book.save()

        from lib.operating import modes_for

        mode = modes_for(("stocks",), {"stocks": {"autonomous_execution": True}},
                         directory=tmp_path,
                         ledger=OutcomeLedger(tmp_path / "outcomes.json"))[0]

        assert mode.mode == OWNER_OPERATING_MANUALLY
        assert mode.may_place is False

    def test_settling_it_hands_autonomy_back(self, tmp_path):
        from lib.operating import modes_for

        book = ledger(tmp_path)
        result, _ = self._unresolved(tmp_path, book)
        book.settle(result.position_id, 4900.98, note="it did reach the broker and filled")
        book.save()

        mode = modes_for(("stocks",), {"stocks": {"autonomous_execution": True}},
                         directory=tmp_path,
                         ledger=OutcomeLedger(tmp_path / "outcomes.json"))[0]

        assert mode.mode == AUTONOMOUS


class TestAPartFillIsSmallerThanWhatWasSized:
    def _part(self, tmp_path, book):
        broker = Broker(OrderResult(PART_FILLED, TICKER, "eb-x", filled_quantity=3,
                                    requested_quantity=49, filled_avg_price=100.02))
        return place(tmp_path, book=book, broker=broker)

    def test_it_is_placed(self, tmp_path):
        assert self._part(tmp_path, ledger(tmp_path)).status == PLACED

    def test_the_position_is_corrected_to_what_actually_went_on(self, tmp_path):
        """Otherwise exposure is overstated for the rest of the position's life."""

        book = ledger(tmp_path)

        result = self._part(tmp_path, book)

        assert book.get(result.position_id).staked == pytest.approx(300.06)

    def test_the_correction_is_noted(self, tmp_path):
        book = ledger(tmp_path)

        result = self._part(tmp_path, book)

        assert "part filled: 3 of 49" in book.get(result.position_id).note

    def test_the_report_says_it_is_smaller_than_the_sized_position(self, tmp_path):
        assert "smaller than the one that was sized" in self._part(
            tmp_path, ledger(tmp_path)).describe()

    def test_a_stake_cannot_be_amended_upwards(self, tmp_path):
        """A fill cannot exceed its request, so that is a defect rather than a correction."""

        book = ledger(tmp_path)
        position = book.open_position("stocks", TICKER, 100.0, at="2026-08-03T01:00:00Z")

        with pytest.raises(ValueError, match="defect upstream"):
            book.amend_stake(position.position_id, 200.0)

    def test_amending_to_nothing_is_refused_in_favour_of_voiding(self, tmp_path):
        book = ledger(tmp_path)
        position = book.open_position("stocks", TICKER, 100.0, at="2026-08-03T01:00:00Z")

        with pytest.raises(ValueError, match="void it"):
            book.amend_stake(position.position_id, 0.0)


class TestTheOrderIdIsStableAcrossRetries:
    """Derived from the intent, never the moment. A retry after an UNKNOWN must collide."""

    def _id(self, shares=49):
        from connectors.alpaca import instruction_id

        return instruction_id(TICKER, "buy", float(shares), "2026-08-02T09:00:00Z")

    def test_the_placement_uses_it_rather_than_inventing_one(self, tmp_path):
        assert place(tmp_path).client_order_id == self._id()

    def test_the_same_intent_produces_the_same_id(self):
        assert self._id() == self._id()

    def test_a_different_size_produces_a_different_one(self):
        assert self._id() != self._id(shares=7)

    def test_a_retry_after_an_unresolved_order_carries_the_same_id(self, tmp_path):
        """Which is why resubmitting collides at the broker instead of filling twice."""

        broker = Broker(OrderResult(UNKNOWN, TICKER, "eb-x", reason="timeout"))

        result = place(tmp_path, broker=broker)

        assert result.client_order_id == self._id()
        assert result.client_order_id in result.describe()


class TestThePermissionTravelsWithTheOrder:
    def test_it_is_attached_so_the_adapter_can_re_check_it(self, tmp_path):
        """The last thing before money moves is where a redundant check earns its place."""

        broker = Broker()

        place(tmp_path, broker=broker)

        assert broker.calls[0].permission.status == PERMITTED

    def test_an_indeterminate_permission_is_carried_through_rather_than_upgraded(self,
                                                                                tmp_path):
        broker = Broker()
        harvest = Harvest(permission=Permission("INDETERMINATE", TICKER, ()))

        place(tmp_path, harvest=harvest, broker=broker)

        assert broker.calls[0].permission.status == "INDETERMINATE"

    def test_the_real_adapter_then_refuses_it(self, tmp_path):
        """Proved against connectors/alpaca rather than the fake, since that is the guard."""

        from connectors.alpaca import AlpacaBroker

        broker = Broker()
        place(tmp_path, harvest=Harvest(permission=Permission("INDETERMINATE", TICKER, ())),
              broker=broker)

        result = AlpacaBroker(credentials=None).place(broker.calls[0])

        assert result.status == REJECTED
        assert "not a weaker yes" in result.reason


class TestTheSummary:
    def test_it_says_money_has_moved(self, tmp_path):
        assert "MONEY HAS MOVED" in describe_placements([place(tmp_path)])

    def test_it_flags_unresolved_orders_above_everything_else(self, tmp_path):
        broker = Broker(OrderResult(UNKNOWN, TICKER, "eb-x", reason="timeout"))

        described = describe_placements([place(tmp_path, broker=broker)])

        assert "Query them at the broker before anything else" in described

    def test_nothing_placed_says_everything_waits_for_you(self, tmp_path):
        described = describe_placements([place(tmp_path, mode=manual())])

        assert "Every instruction is waiting for you" in described

    def test_an_empty_list_produces_nothing(self):
        assert describe_placements([]) == ""
