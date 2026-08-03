"""Three of six circuit-breaker controls were dead, and this is what revives them.

`Breakers.record()` was called by no production code, so the daily loss limit, the
consecutive-loss run and the previously-tripped check all read zero forever. The end of this
file proves the gap is closed the only way that counts: four losses recorded as outcomes
actually trip the lane.

The rest of the file is about the sentinel. An unsettled position is not a zero-profit one,
and a void is not either — `Breakers.consecutive_losses()` breaks its run on any outcome
that is not negative, so passing zero for either would end a losing streak without a win
having happened. Both errors point the same way, which is the direction that keeps you
trading.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.breakers import ARMED, TRIPPED, Breakers, Ringfence
from lib.outcomes import (
    BROKER,
    OPEN,
    SETTLED,
    STALE_HOURS,
    UNKNOWN,
    VOID,
    OutcomeLedger,
    apply_to_breakers,
    describe_ledger,
    position_id,
)

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def stamp(hours_ago: float = 0.0) -> str:
    return (NOW - timedelta(hours=hours_ago)).isoformat(timespec="seconds")


def ledger(tmp_path):
    return OutcomeLedger(tmp_path / "outcomes.json")


def breakers(tmp_path, balance=1000.0, **kw):
    return Breakers(Ringfence("arb", balance, **kw), tmp_path / "b.json",
                    kill_switch=tmp_path / "HALT")


def placed(book, lane="arb", subject="Arsenal v Chelsea", staked=100.0, **kw):
    return book.open_position(lane, subject, staked, at=kw.pop("at", stamp()), **kw)


class TestAnUnsettledPositionIsNotAZero:
    def test_an_open_position_has_no_profit_at_all(self, tmp_path):
        """`None`, not 0.0. A caller that gets zero does not know there was a question."""

        assert placed(ledger(tmp_path)).profit is None

    def test_an_unknown_position_has_no_profit_either(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book)

        book.mark_unknown(position.position_id, "bet365 restricted the account")

        assert book.get(position.position_id).profit is None

    def test_a_settled_position_has_one(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book, staked=100.0)

        settled = book.settle(position.position_id, 108.22)

        assert settled.profit == pytest.approx(8.22)

    def test_a_total_loss_returns_zero_and_is_the_full_stake(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book, staked=100.0)

        assert book.settle(position.position_id, 0.0).profit == pytest.approx(-100.0)

    def test_an_open_position_is_never_handed_to_a_breaker(self, tmp_path):
        book, controls = ledger(tmp_path), breakers(tmp_path)
        placed(book, staked=500.0)

        applied = apply_to_breakers(book, controls)

        assert applied.applied == ()
        assert len(applied.skipped_unsettled) == 1
        assert controls.profit_today() == 0.0

    def test_the_report_says_the_breakers_have_less_than_the_full_picture(self, tmp_path):
        book, controls = ledger(tmp_path), breakers(tmp_path)
        placed(book)

        assert "less than the full picture" in apply_to_breakers(book, controls).describe()


class TestVoidIsNotAWin:
    def test_a_void_is_never_applied(self, tmp_path):
        book, controls = ledger(tmp_path), breakers(tmp_path)
        position = placed(book)
        book.void(position.position_id, note="abandoned; both books voided")

        applied = apply_to_breakers(book, controls)

        assert applied.applied == ()
        assert applied.skipped_void == (position.position_id,)

    def test_a_void_does_not_end_a_losing_run(self, tmp_path):
        """The specific bug: consecutive_losses() breaks on anything not negative."""

        book, controls = ledger(tmp_path), breakers(tmp_path)
        for _ in range(2):
            book.settle(placed(book, at=stamp(hours_ago=len(book.positions))).position_id,
                        0.0)
        book.void(placed(book, at=stamp(hours_ago=9)).position_id)

        apply_to_breakers(book, controls)

        assert controls.consecutive_losses() == 2

    def test_a_void_returns_the_stake(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book, staked=250.0)

        assert book.void(position.position_id).returned == pytest.approx(250.0)

    def test_it_says_why_it_was_not_applied(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book)

        described = book.void(position.position_id).describe()

        assert "end a losing run without a win having happened" in described


class TestUnknownIsAStatusNotAGap:
    def test_it_needs_a_stated_reason(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book)

        with pytest.raises(ValueError, match="indistinguishable from neglect"):
            book.mark_unknown(position.position_id, "   ")

    def test_it_still_counts_as_exposure(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book, staked=400.0)
        book.mark_unknown(position.position_id, "5xx from the broker, order id unresolved")

        assert book.unsettled_exposure() == pytest.approx(400.0)

    def test_it_says_it_is_neither_a_loss_nor_a_nothing(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book)

        described = book.mark_unknown(position.position_id, "account restricted").describe()

        assert "not a loss and it is not a nothing" in described


class TestExposureTheBreakersCannotSee:
    def test_live_positions_are_summed(self, tmp_path):
        book = ledger(tmp_path)
        placed(book, staked=100.0, at=stamp(1))
        placed(book, staked=250.0, at=stamp(2))

        assert book.unsettled_exposure() == pytest.approx(350.0)

    def test_settled_positions_drop_out(self, tmp_path):
        book = ledger(tmp_path)
        first = placed(book, staked=100.0, at=stamp(1))
        placed(book, staked=250.0, at=stamp(2))
        book.settle(first.position_id, 110.0)

        assert book.unsettled_exposure() == pytest.approx(250.0)

    def test_it_can_be_read_per_lane(self, tmp_path):
        book = ledger(tmp_path)
        placed(book, lane="arb", staked=100.0, at=stamp(1))
        placed(book, lane="stocks", subject="MODN", staked=900.0, at=stamp(2))

        assert book.unsettled_exposure("arb") == pytest.approx(100.0)

    def test_a_stale_open_position_is_surfaced(self, tmp_path):
        book = ledger(tmp_path)
        placed(book, at=stamp(hours_ago=STALE_HOURS + 1))

        assert len(book.stale_open(now=NOW)) == 1

    def test_a_recent_one_is_not(self, tmp_path):
        book = ledger(tmp_path)
        placed(book, at=stamp(hours_ago=1))

        assert book.stale_open(now=NOW) == ()

    def test_an_unreadable_opening_time_counts_as_stale(self, tmp_path):
        """Unknown age is not young age."""

        book = ledger(tmp_path)
        placed(book, at="whenever")

        assert len(book.stale_open(now=NOW)) == 1


class TestApplyingIsIdempotent:
    def _four_losses(self, tmp_path):
        """Small enough that the 3% daily limit does not trip first — 4 x 5 is under 30."""

        book, controls = ledger(tmp_path), breakers(tmp_path)
        for index in range(4):
            position = placed(book, staked=5.0, at=stamp(hours_ago=index + 1))
            book.settle(position.position_id, 0.0, source=BROKER)
        return book, controls

    def test_applying_twice_does_not_double_count(self, tmp_path):
        book, controls = self._four_losses(tmp_path)

        apply_to_breakers(book, controls)
        second = apply_to_breakers(book, controls)

        assert second.applied == ()
        assert len(second.already_applied) == 4
        assert controls.profit_today() == pytest.approx(-20.0)

    def test_the_flag_is_persisted(self, tmp_path):
        book, controls = self._four_losses(tmp_path)

        apply_to_breakers(book, controls)

        assert all(p.applied_to_breakers
                   for p in OutcomeLedger(tmp_path / "outcomes.json").positions)

    def test_four_recorded_losses_actually_trip_the_lane(self, tmp_path):
        """The proof the gap is closed. Before this module the count was always zero."""

        book, controls = self._four_losses(tmp_path)

        applied = apply_to_breakers(book, controls)

        assert controls.state.status == TRIPPED
        assert applied.tripped_by == "consecutive losses"

    def test_a_tripped_lane_then_blocks_the_next_check(self, tmp_path):
        book, controls = self._four_losses(tmp_path)
        apply_to_breakers(book, controls)

        fresh = breakers(tmp_path)

        assert fresh.check(proposed_size=1.0).verdict == "BLOCKED"

    def test_the_daily_loss_limit_trips_too(self, tmp_path):
        book, controls = ledger(tmp_path), breakers(tmp_path)   # 3% of 1000 = 30
        position = placed(book, staked=50.0)
        book.settle(position.position_id, 19.0)

        apply_to_breakers(book, controls)

        assert controls.state.tripped_by == "daily loss limit"

    def test_the_application_says_a_breaker_tripped_and_will_not_self_clear(self, tmp_path):
        book, controls = self._four_losses(tmp_path)

        assert "does not reset itself" in apply_to_breakers(book, controls).describe()

    def test_nothing_settled_is_a_clean_no_op(self, tmp_path):
        assert apply_to_breakers(ledger(tmp_path), breakers(tmp_path)).applied == ()


class TestUnreadableRefusesRatherThanEmptying:
    def test_an_unreadable_ledger_refuses_to_be_written(self, tmp_path):
        (tmp_path / "outcomes.json").write_text("{not json", encoding="utf-8")
        book = OutcomeLedger(tmp_path / "outcomes.json")

        assert not book.readable
        with pytest.raises(RuntimeError, match="still holding money"):
            book.open_position("arb", "x", 10.0)

    def test_an_unreadable_ledger_is_not_applied_as_an_empty_day(self, tmp_path):
        (tmp_path / "outcomes.json").write_text("nonsense", encoding="utf-8")

        applied = apply_to_breakers(OutcomeLedger(tmp_path / "outcomes.json"),
                                    breakers(tmp_path))

        assert "told the breakers the day went fine" in applied.describe().replace(
            "tell the breakers", "told the breakers")

    def test_unreadable_breakers_are_not_written_to(self, tmp_path):
        (tmp_path / "b.json").write_text("{not json", encoding="utf-8")
        book = ledger(tmp_path)
        book.settle(placed(book).position_id, 0.0)

        applied = apply_to_breakers(book, breakers(tmp_path))

        assert applied.applied == ()
        assert "not a satisfied daily loss limit" in applied.refusal

    def test_a_vanished_ledger_reports_LOST_rather_than_first_run(self, tmp_path):
        book = ledger(tmp_path)
        placed(book)
        book.save()

        (tmp_path / "outcomes.json").unlink()

        assert OutcomeLedger(tmp_path / "outcomes.json").status.state == "LOST"

    def test_the_report_of_an_unreadable_ledger_is_not_a_report_of_nothing_open(self,
                                                                               tmp_path):
        (tmp_path / "outcomes.json").write_text("[[[", encoding="utf-8")

        described = describe_ledger(OutcomeLedger(tmp_path / "outcomes.json"))

        assert "not a report that nothing is open" in described


class TestAmendingAndDuplicates:
    def test_the_id_is_deterministic(self):
        assert position_id("arb", "x", "t") == position_id("arb", "x", "t")

    def test_recording_the_same_placement_twice_collides(self, tmp_path):
        book = ledger(tmp_path)
        placed(book, at=stamp(1))

        with pytest.raises(ValueError, match="recorded twice rather than two bets"):
            placed(book, at=stamp(1))

    def test_a_settled_position_cannot_be_amended(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book)
        book.settle(position.position_id, 50.0)

        with pytest.raises(ValueError, match="the copy that stops you"):
            book.settle(position.position_id, 900.0)

    def test_a_position_with_no_stake_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="not a position"):
            ledger(tmp_path).open_position("arb", "x", 0.0)

    def test_a_negative_return_is_refused(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book)

        with pytest.raises(ValueError, match="a total loss returns 0"):
            book.settle(position.position_id, -5.0)

    def test_an_unknown_id_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="no position"):
            ledger(tmp_path).settle("POS-nope", 1.0)


class TestTheRoundTrip:
    def test_positions_survive_a_save_and_reload(self, tmp_path):
        book = ledger(tmp_path)
        position = placed(book, staked=100.0)
        book.settle(position.position_id, 112.0, source=BROKER, note="filled")
        book.save()

        reloaded = OutcomeLedger(tmp_path / "outcomes.json").get(position.position_id)

        assert reloaded.status == SETTLED
        assert reloaded.profit == pytest.approx(12.0)
        assert reloaded.source == BROKER

    def test_the_receipt_carries_a_count_and_never_a_subject(self, tmp_path):
        book = ledger(tmp_path)
        placed(book, subject="Arsenal v Chelsea")
        book.save()

        raw = (tmp_path / "outcomes.receipt.json").read_text(encoding="utf-8")

        assert '"rows_at_last_write": 1' in raw
        assert "Arsenal" not in raw

    def test_the_money_view_names_what_the_limit_cannot_see(self, tmp_path):
        book = ledger(tmp_path)
        placed(book, staked=420.0)

        assert "invisible to the daily loss limit" in describe_ledger(book, now=NOW)

    def test_an_empty_ledger_says_so_plainly(self, tmp_path):
        assert "No position is open" in describe_ledger(ledger(tmp_path))

    def test_settled_but_unapplied_outcomes_are_flagged(self, tmp_path):
        book = ledger(tmp_path)
        book.settle(placed(book).position_id, 1.0)

        assert "or they never will" in describe_ledger(book, now=NOW)
