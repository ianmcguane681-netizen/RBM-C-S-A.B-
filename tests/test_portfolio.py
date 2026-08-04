"""An unpriced holding is not a holding worth nothing, and a size hides which rule bound it.

Two properties, both aimed at the number a holder looks at first.

A stored value goes stale silently and a zero shows the portfolio shrinking the moment a
feed dies — a loss that never happened. Worse than the display error: a risk limit computed
against that balance sizes the next position against a number wrong in the reassuring
direction. So `value` returns `None` rather than `0.0`, and callers must handle it.

And a size that does not name its binding constraint hides the difference between "my own
rules are holding me back" and "the market cannot absorb me", which call for opposite
responses.
"""
from __future__ import annotations

import pytest

from lib.portfolio import (
    BUY,
    EQUITY,
    PRICED,
    SELL,
    STALE,
    UNPRICED,
    Entry,
    Portfolio,
    Valuation,
)
from lib.sizing import (
    INDETERMINATE,
    NOT_MEASURED,
    REFUSED,
    SIZED,
    Constraint,
    exit_depth,
    risk_limit,
    size_position,
    venue_maximum,
    volatility_bound,
)


def buy(asset="MOD", qty=100.0, price=90.0, when="2026-05-01T12:00:00Z"):
    return Entry(asset, EQUITY, BUY, qty, price, "USD", when, reason="thesis")


class TestUnpricedIsNotZero:
    def test_an_unpriced_holding_has_no_value_rather_than_a_zero_one(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy())

        valuation = book.positions()[0].value_at(None)

        assert valuation.status == UNPRICED
        assert valuation.value is None

    def test_the_wording_refuses_to_claim_a_zero(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy())

        described = book.positions()[0].value_at(None).describe()

        assert "NOT a value of zero" in described

    def test_unpriced_holdings_are_excluded_from_the_total_and_named(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy("MOD"))
        book.add(buy("NET", 10, 200.0))

        exposure = book.exposure([
            book.positions()[0].value_at(100.0, source="test"),
            book.positions()[1].value_at(None),
        ])

        assert exposure.unpriced_assets == ("NET",)
        assert exposure.is_complete is False

    def test_the_total_warns_against_being_sized_against(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy("MOD"))
        book.add(buy("NET", 10, 200.0))

        text = book.exposure([
            book.positions()[0].value_at(100.0),
            book.positions()[1].value_at(None),
        ]).describe()

        assert "Do not size a position against this number" in text

    def test_a_stale_price_is_priced_but_marked(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy())

        valuation = book.positions()[0].value_at(
            100.0, priced_at="2020-01-01T00:00:00Z", stale_after_seconds=60
        )

        assert valuation.status == STALE
        assert valuation.value == pytest.approx(10_000.0)


class TestCostBasisIsDerived:
    def test_two_buys_average(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy(qty=100, price=90.0))
        book.add(buy(qty=100, price=110.0))

        assert book.positions()[0].average_cost == pytest.approx(100.0)

    def test_a_sell_leaves_the_average_untouched(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy(qty=100, price=90.0))
        book.add(Entry("MOD", EQUITY, SELL, 50, 200.0, "USD", "2026-06-01T12:00:00Z"))

        position = book.positions()[0]

        assert position.quantity == pytest.approx(50.0)
        assert position.average_cost == pytest.approx(90.0)

    def test_a_fully_sold_position_disappears(self):
        book = Portfolio("/tmp/never-written.json")
        book.add(buy(qty=100, price=90.0))
        book.add(Entry("MOD", EQUITY, SELL, 100, 200.0, "USD", "2026-06-01T12:00:00Z"))

        assert book.positions() == ()

    def test_direction_is_carried_by_side_not_by_a_negative_quantity(self):
        with pytest.raises(ValueError, match="direction is carried by side"):
            Entry("MOD", EQUITY, BUY, -1, 90.0, "USD", "2026-05-01T12:00:00Z")


class TestSizingNamesItsBindingConstraint:
    def test_the_smallest_constraint_binds_and_is_named(self):
        size = size_position("MOD", [
            risk_limit(100_000, 11.0),
            exit_depth(4_200, 1.8),
            venue_maximum(50_000, "Alpaca"),
        ])

        assert size.status == SIZED
        assert size.amount == pytest.approx(4_200.0)
        assert size.bound_by == "exit depth"

    def test_the_output_says_what_the_other_rule_would_have_allowed(self):
        text = size_position("MOD", [
            risk_limit(100_000, 11.0), exit_depth(4_200, 1.8),
        ]).describe()

        assert "bound by: exit depth" in text
        assert "risk limit would have allowed 11,000.00" in text

    def test_the_amount_is_floored_to_the_penny(self):
        """100.00000000000001 against a 100.00 limit reported a book that could not fill."""

        size = size_position("X", [Constraint("a", 100.00000000000001)])

        assert size.amount == pytest.approx(100.00)

    def test_a_zero_ceiling_refuses_rather_than_sizing_at_zero(self):
        size = size_position("X", [Constraint("depth", 0.0, "nothing exitable")])

        assert size.status == REFUSED


class TestAnUnmeasuredConstraintBlocks:
    def test_unknown_volatility_makes_the_size_indeterminate(self):
        """Skipping it would size at full risk limit precisely when nothing is known."""

        size = size_position("MOD", [
            risk_limit(100_000, 10.0),
            volatility_bound(100_000, None, 2.0),
        ])

        assert size.status == INDETERMINATE
        assert size.amount == 0.0

    def test_indeterminate_explains_why_skipping_would_flatter(self):
        text = size_position("MOD", [
            risk_limit(100_000, 10.0), volatility_bound(100_000, None, 2.0),
        ]).describe()

        assert "always the larger number" in text

    def test_a_volatility_of_zero_is_a_measurement_failure_not_a_still_market(self):
        assert volatility_bound(100_000, 0.0, 2.0).limit == NOT_MEASURED

    def test_measured_volatility_produces_a_real_ceiling(self):
        constraint = volatility_bound(100_000, 4.0, 2.0)

        assert constraint.limit == pytest.approx(50_000.0)

    def test_no_constraints_at_all_is_indeterminate_not_unlimited(self):
        assert size_position("X", []).status == INDETERMINATE


class TestObligationsAreChosenInAdvance:
    """The row that would be got wrong by default is the last one.

    A monitor that reduced a position because a node timed out would be a catastrophe
    assembled out of an unhandled sentinel, and this repository has produced that class of
    bug in six less consequential places.
    """

    def _changes(self, *specs):
        from lib.ledger import Change

        return [Change(status, "ethereum:0xA0b8", fact, before="a", after="b", reason="x")
                for status, fact in specs]

    def test_an_unreadable_fact_carries_no_obligation(self):
        from lib.ledger import UNREADABLE
        from lib.sizing import NONE, obligations_for

        found = obligations_for(self._changes((UNREADABLE, "implementation")))

        assert found[0].action == NONE
        assert "not an event" in found[0].why

    def test_an_implementation_swap_compels_exit_or_re_review(self):
        from lib.ledger import CHANGED
        from lib.sizing import EXIT_OR_REVIEW, obligations_for

        found = obligations_for(self._changes((CHANGED, "implementation")))

        assert found[0].action == EXIT_OR_REVIEW
        assert found[0].deadline_days == 7

    def test_a_pause_freezes_because_you_may_not_be_able_to_exit(self):
        from lib.ledger import CHANGED
        from lib.sizing import FREEZE, obligations_for

        found = obligations_for(self._changes((CHANGED, "paused")))

        assert found[0].action == FREEZE
        assert "unable to exit" in found[0].why

    def test_an_uncovered_fact_is_recorded_rather_than_read_as_nothing_required(self):
        from lib.ledger import CHANGED
        from lib.sizing import NONE, obligations_for

        found = obligations_for(self._changes((CHANGED, "totalSupply")))

        assert found[0].action == NONE
        assert "no policy row covers this fact" in found[0].why

    def test_an_absent_fact_says_it_is_no_longer_reported_at_all(self):
        from lib.ledger import ABSENT
        from lib.sizing import obligations_for

        found = obligations_for(self._changes((ABSENT, "owner")))

        assert "no longer reported at all" in found[0].why

    def test_the_summary_leads_with_the_most_compelling(self):
        from lib.ledger import CHANGED
        from lib.sizing import obligations_for, summarise_obligations

        text = summarise_obligations(obligations_for(
            self._changes((CHANGED, "owner"), (CHANGED, "implementation"))
        ))

        assert text.index("EXIT_OR_RE_REVIEW") < text.index("NO_ADDITIONS")

    def test_no_obligations_says_what_it_did_not_cover(self):
        from lib.ledger import UNCHANGED
        from lib.sizing import obligations_for, summarise_obligations

        text = summarise_obligations(obligations_for(self._changes((UNCHANGED, "owner"))))

        assert "says nothing about anything not being watched" in text


class TestTheJsonLayerDoesNotReintroduceTheZero:
    """The presentation layer is where a carefully-built distinction goes to die.

    An empty book has no unpriced assets, so `is_complete` reads true and the total
    emitted 0.0 -- which a front end renders as a known balance of zero. The text panel
    already said "an empty book, not a zero balance". The JSON layer had quietly
    reintroduced the very defect the module argues against, and it was found by running
    it rather than by reading it.
    """

    def _payload(self, monkeypatch, tmp_path):
        import status

        monkeypatch.setattr(status, "BOOK", tmp_path / "portfolio.json")
        return status.as_json()

    def test_a_book_nobody_has_started_emits_null_rather_than_zero(
        self, monkeypatch, tmp_path
    ):
        """This fixture points at a file that does not exist, so it is NOT_CONFIGURED.

        The status was `EMPTY_BOOK` while absent and empty were one case. They are now
        told apart, because a book nobody has started and a book somebody started and
        emptied are different facts — and `cost_basis` is null for both, where it used to
        be the 0.0 this whole class exists to argue against.
        """

        payload = self._payload(monkeypatch, tmp_path)

        assert payload["capital"]["priced_value"] is None
        assert payload["capital"]["cost_basis"] is None
        assert payload["capital"]["value_status"] == "NOT_CONFIGURED"

    def test_a_book_that_exists_and_holds_nothing_is_an_empty_book(
        self, monkeypatch, tmp_path
    ):
        book = tmp_path / "portfolio.json"
        book.write_text("[]", encoding="utf-8")

        import status

        monkeypatch.setattr(status, "BOOK", book)
        payload = status.as_json()

        assert payload["capital"]["value_status"] == "EMPTY_BOOK"
        assert payload["capital"]["cost_basis"] is None

    def test_an_empty_book_is_not_reported_as_complete(self, monkeypatch, tmp_path):
        assert self._payload(monkeypatch, tmp_path)["capital"]["is_complete"] is False

    def test_an_unpriced_holding_emits_null_with_a_status(self, monkeypatch, tmp_path):
        import status
        from lib.portfolio import Portfolio

        path = tmp_path / "portfolio.json"
        book = Portfolio(path)
        book.add(buy("MOD"))
        book.save()
        monkeypatch.setattr(status, "BOOK", path)

        held = status.as_json()["capital"]["positions"][0]

        assert held["value"] is None
        assert held["value_status"] == "UNPRICED"

    def test_the_payload_names_the_fields_it_refuses_to_emit(self, monkeypatch, tmp_path):
        """So a front end cannot quietly invent a risk score in the top bar."""

        refused = self._payload(monkeypatch, tmp_path)["refused_fields"]

        assert set(refused) == {
            "risk_score", "daily_pnl", "best_performer", "expected_profit",
        }
        assert "heterogeneous" in refused["risk_score"]

    def test_an_unconfigured_lane_reports_its_status_not_an_empty_result(
            self, monkeypatch, tmp_path):
        engines = {e["lane"]: e for e in self._payload(monkeypatch, tmp_path)["engines"]}

        assert engines["arb"]["status"] in {"DEGRADED", "BLOCKED"}
        assert engines["arb"]["missing"]
