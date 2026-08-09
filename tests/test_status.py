"""A money status must show authority and uncertainty, never manufacture reassuring zeros.

The operating mode is the most consequential fact on the page: AUTONOMOUS means the lane
places without asking. Missing breaker and outcome files are equally consequential. They
mean limits or exposure cannot be established, not that an armed lane has nothing at risk.
These tests keep all three states visually distinct and keep stale money in view.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import status
from lib.breakers import Breakers, Ringfence
from lib.outcomes import OutcomeLedger
from lib.portfolio import Portfolio
from lib.store import LOST, UNREADABLE
from status import money_panel


def config_file(tmp_path, **overrides):
    config = {
        "arb": {
            "enabled": True,
            "balance": 1_000.0,
            "currency": "EUR",
            "autonomous_execution": True,
        },
        "stocks": {"enabled": False},
        "crypto": {"enabled": False},
    }
    config.update(overrides)
    path = tmp_path / "reapers.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def render(tmp_path, config_path=None):
    return "\n".join(money_panel(
        config_path=config_path or tmp_path / "reapers.json",
        directory=tmp_path,
        ledger_path=tmp_path / "outcomes.json",
    ))


def test_an_autonomous_lane_is_visually_distinct(tmp_path):
    output = render(tmp_path, config_file(tmp_path))

    assert "AUTONOMOUS  [arb]" in output
    assert "PLACES ITS OWN INSTRUCTIONS" in output


def test_missing_money_files_are_not_rendered_as_zero_exposure(tmp_path):
    output = render(tmp_path)

    assert output.count("NOT_CONFIGURED") >= 6
    assert "not a zero balance or zero exposure" in output
    assert "not 0.00 at risk" in output
    assert "0.00 at risk" not in output.replace("not 0.00 at risk", "")


def test_a_ring_fence_reports_its_balance_and_currency(tmp_path):
    output = render(tmp_path, config_file(tmp_path))

    assert "RING-FENCE  1,000.00 EUR" in output


def test_an_unreadable_breaker_is_not_not_configured(tmp_path):
    path = config_file(tmp_path)
    (tmp_path / "breakers-arb.json").write_text("{broken", encoding="utf-8")

    output = render(tmp_path, path)

    assert "BREAKER  UNREADABLE" in output
    assert "unknown loss history must stop the lane" in output


def test_a_tripped_breaker_names_why_when_and_that_it_does_not_self_clear(tmp_path):
    path = config_file(tmp_path)
    controls = Breakers(
        Ringfence("arb", 1_000.0),
        tmp_path / "breakers-arb.json",
        kill_switch=tmp_path / "HALT",
    )
    for _ in range(4):
        controls.record(-1.0, reference="loss")
    controls.save()

    output = render(tmp_path, path)

    assert "BREAKER  TRIPPED  consecutive losses at" in output
    assert "does not self-clear" in output


def test_open_and_stale_money_is_named_as_invisible_to_the_daily_loss_limit(tmp_path):
    path = config_file(tmp_path)
    opened = (datetime.now(timezone.utc) - timedelta(hours=80)).isoformat()
    ledger = OutcomeLedger(tmp_path / "outcomes.json")
    ledger.open_position("arb", "old position", 75.0, source="MANUAL", at=opened)
    ledger.save()

    output = render(tmp_path, path)

    assert "1 position(s) live, 75.00 at risk" in output
    assert "invisible to the daily loss limit" in output
    assert "open over 72h" in output


def test_an_unreadable_outcome_ledger_is_not_an_empty_position_book(tmp_path):
    path = config_file(tmp_path)
    (tmp_path / "outcomes.json").write_text("{broken", encoding="utf-8")

    output = render(tmp_path, path)

    assert "UNREADABLE  the outcome ledger would not parse" in output
    assert "not a report that nothing is open" in output


class TestCapitalNeverReportsAZeroItDidNotMeasure:
    """Three different nothings were arriving at the dashboard as one measured zero.

    A portfolio file that never existed, one that vanished, and one that is genuinely
    empty all produce nought positions, and every figure derived from them came out
    `0.0` — which the operator dashboard printed in its largest type as CAPITAL AT COST
    €0.00 beside the word EMPTY_BOOK.

    `capital_panel` never made this mistake. It returns early on LOST and says in as many
    words that an empty book is "not a zero balance: nothing has been entered, so nothing
    is known about what is held". `as_json` did not consult the store state at all, so a
    vanished portfolio reported an empty one — the founding defect of this repository in
    the form it warns about most sharply.
    """

    def _book(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        return tmp_path / "data" / "portfolio.json"

    def test_a_portfolio_nobody_has_started_is_not_a_balance_of_zero(
        self, tmp_path, monkeypatch
    ):
        self._book(tmp_path, monkeypatch)

        capital = status.as_json()["capital"]

        assert capital["value_status"] == "NOT_CONFIGURED"
        assert capital["cost_basis"] is None
        assert capital["priced_value"] is None
        assert capital["is_complete"] is False

    def test_an_empty_book_reports_nothing_known_rather_than_nothing_held(
        self, tmp_path, monkeypatch
    ):
        """The file exists and holds no entries, which is still not a measured zero.

        The panel's wording is that nothing is KNOWN, not that nothing is held, and the
        JSON has no business being more confident than the prose it mirrors.
        """

        book = self._book(tmp_path, monkeypatch)
        book.write_text("[]", encoding="utf-8")

        capital = status.as_json()["capital"]

        assert capital["value_status"] == "EMPTY_BOOK"
        assert capital["cost_basis"] is None

    def test_a_vanished_book_is_never_reported_as_an_empty_one(
        self, tmp_path, monkeypatch
    ):
        """A receipt claiming entries beside a file holding none is LOST, not EMPTY_BOOK.

        This is the case that costs something. There WAS a book; reporting it as empty
        with a zero balance says the holder owns nothing, and says it confidently.
        """

        book = self._book(tmp_path, monkeypatch)
        book.write_text(json.dumps([{
            "asset": "MODN", "lane": "stocks", "side": "BUY", "quantity": 10.0,
            "unit_price": 24.0, "currency": "USD", "when": "2026-08-01T00:00:00Z",
            "reason": "the thesis on file",
        }]), encoding="utf-8")
        Portfolio(book).save()
        book.write_text("[]", encoding="utf-8")          # the entries vanish

        capital = status.as_json()["capital"]

        assert capital["store_state"] == LOST
        assert capital["value_status"] == LOST
        assert capital["cost_basis"] is None
        assert capital["reason"]

    def test_an_unreadable_book_withholds_every_figure_and_says_why(
        self, tmp_path, monkeypatch
    ):
        book = self._book(tmp_path, monkeypatch)
        book.write_text("{ this is not the book", encoding="utf-8")

        capital = status.as_json()["capital"]

        assert capital["value_status"] == UNREADABLE
        assert capital["cost_basis"] is None
        assert capital["reason"]

    def test_a_book_with_real_entries_still_reports_its_real_total(
        self, tmp_path, monkeypatch
    ):
        """The guard must not swallow the case it exists to protect.

        A cost basis computed from entries somebody actually recorded is a measurement,
        and withholding it would be the same defect facing the other way.
        """

        book = self._book(tmp_path, monkeypatch)
        book.write_text(json.dumps([{
            "asset": "MODN", "lane": "stocks", "side": "BUY", "quantity": 10.0,
            "unit_price": 24.0, "currency": "USD", "when": "2026-08-01T00:00:00Z",
            "reason": "the thesis on file",
        }]), encoding="utf-8")

        capital = status.as_json()["capital"]

        assert capital["cost_basis"] == 240.0
        assert capital["value_status"] == "PARTIALLY_UNPRICED"
        assert capital["priced_value"] is None      # no price source is wired
        assert capital["by_lane_cost"] == {"stocks": 240.0}

    def test_what_was_paid_does_not_depend_on_a_price_source(
        self, tmp_path, monkeypatch
    ):
        """CAPITAL AT COST was being taken from the cost of the PRICED subset.

        `Exposure.cost_basis` accumulates only where a valuation came back, so with no
        price source wired for any lane — the state every lane is in — it is 0.0 however
        much is held. The dashboard renders that figure as CAPITAL AT COST, so a fully
        stocked book showed €0.00 for the same reason an empty one did.

        What was paid is knowable without pricing anything, which is precisely why it is
        the figure worth showing while pricing is unwired.
        """

        book = self._book(tmp_path, monkeypatch)
        book.write_text(json.dumps([
            {"asset": "MODN", "lane": "stocks", "side": "BUY", "quantity": 10.0,
             "unit_price": 24.0, "currency": "USD", "when": "2026-08-01T00:00:00Z",
             "reason": "the thesis on file"},
            {"asset": "NET", "lane": "stocks", "side": "BUY", "quantity": 4.0,
             "unit_price": 50.0, "currency": "USD", "when": "2026-08-02T00:00:00Z",
             "reason": "the thesis on file"},
        ]), encoding="utf-8")

        capital = status.as_json()["capital"]

        assert capital["cost_basis"] == 440.0
        # The priced subset keeps its own name, and is nought because nothing is priced.
        assert capital["priced_cost_basis"] == 0.0
        assert capital["unpriced_assets"] == ["MODN", "NET"]


class TestAMonetaryFigureCarriesItsUnit:
    """EUR 39.00 and USD -77.00 were added together and printed as one total.

    Found by putting mock numbers through the dashboard: the arb lane rings its fence in
    EUR and the stocks lane in USD, and the headline tile summed the two realised figures
    because it took the currency from somewhere other than the figure. No price source
    here converts between them, so that total was not a conversion — it was two different
    units added.

    The fix is structural rather than a formatting rule: the figure carries its own
    currency, so a caller cannot render or combine it against a unit fetched separately.
    """

    def test_each_lanes_realised_figure_states_its_own_currency(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        config_file(tmp_path / "data",
                    arb={"enabled": True, "balance": 500.0, "currency": "EUR"},
                    stocks={"enabled": True, "balance": 5000.0, "currency": "USD"})
        (tmp_path / "data" / "outcomes.json").write_text("[]", encoding="utf-8")

        lanes = {l["lane"]: l for l in status.money_state(
            config_path=tmp_path / "data" / "reapers.json",
            directory=tmp_path / "data",
            ledger_path=tmp_path / "data" / "outcomes.json")}

        assert lanes["arb"]["realised"]["currency"] == "EUR"
        assert lanes["stocks"]["realised"]["currency"] == "USD"


class TestSilenceIsSplitIntoItsCauses:
    """Two quiet days is either nothing happening or nothing being sent, and from a phone
    those look identical. The panel exists so the flattering reading is not the only one
    available."""

    def test_never_sent_is_not_reported_as_a_failure(self):
        lines = "\n".join(status.notifications_panel())

        assert "NEVER_SENT" in lines

    def test_a_delivery_is_reported_with_its_age(self):
        import lib.notify

        lib.notify.LOG.write_text(json.dumps([{
            "status": "SENT", "at": _stamp(hours=2), "subject": "STOCKS READY · 4 ALAB",
            "reason": ""}]))

        lines = "\n".join(status.notifications_panel())

        assert "LAST DELIVERED" in lines and "ALAB" in lines

    def test_attempts_that_all_failed_are_not_a_delivery(self):
        """A recorded attempt is not a message somebody read."""

        import lib.notify

        lib.notify.LOG.write_text(json.dumps([{
            "status": "REFUSED", "at": _stamp(hours=1), "subject": "s",
            "reason": "chat not found"}]))

        lines = "\n".join(status.notifications_panel())

        assert "NOTHING DELIVERED" in lines
        assert "REFUSED" in lines

    def test_an_unreadable_log_is_not_an_absence_of_messages(self):
        import lib.notify

        lib.notify.LOG.write_text("{[")

        lines = "\n".join(status.notifications_panel())

        assert "UNREADABLE" in lines
        assert "is unknown" in lines


def _stamp(*, hours: float) -> str:
    when = datetime.now(timezone.utc) - timedelta(hours=hours)
    return when.isoformat(timespec="seconds").replace("+00:00", "Z")
