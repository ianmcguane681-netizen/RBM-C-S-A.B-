"""One balance must not be euros to the limits that guard it and dollars to the arithmetic
that spends it.

The stocks lane is funded by a single figure. `Ringfence` turns it into the per-position
cap, the daily loss limit and the deployed ceiling; `stock_order` divides it by the ask to
get a whole number of shares. Both read `settings["currency"]` — and until 2026-08-08 they
read it with different defaults, EUR in `breakers_for` and USD in `assemble_stocks`, about
a hundred lines apart in one file. With the key unset the same number was denominated two
ways at once, and setting it to EUR, the natural thing for a euro book, made it worse: the
refusal message printed "EUR" beside a price quoted in dollars.

It undersized rather than oversized at the rates that prevailed, so it was losing nothing
and would have kept not losing anything right up until the rate moved or the book was
funded the other way round. That is what makes it worth a test file: nothing in the output
disagreed with anything else, because both halves were confidently wrong in their own
units.

The properties below are therefore about agreement rather than about any one value. What
the currency IS matters far less than that one answer reaches every part of the lane, and
that a lane which cannot honour that is stopped rather than sized by a rate nobody has.
"""
from __future__ import annotations

import pytest

from connectors import alpaca
from lib.reaping import CONFIGURED, LANE_CURRENCY, REFUSED, assemble_stocks, breakers_for

AUTHORITY = {
    "declared_by": "Ian McGuane",
    "reasoning": "two books disagree by more than the cost of taking both sides",
    "considered": ["a book restricts the account"],
    "expires_at": "2099-01-01T00:00:00Z",
    "max_exposure": 50.0,
}


def stocks(**overrides):
    settings = {"enabled": True, "balance": 2_000.0, "watchlist": ["MODN"]}
    settings.update(overrides)
    return settings


def paths(tmp_path):
    return {"directory": tmp_path, "kill_switch": tmp_path / "HALT",
            "theses_path": tmp_path / "theses.json"}


class TestTheLimitsAndTheArithmeticAgree:
    def test_the_share_arithmetic_is_told_the_ring_fences_own_currency(
            self, tmp_path, monkeypatch):
        """The property the defect broke, asserted where it broke it.

        Not "both say USD" — that would pass again the day someone changes one default and
        not the other to something they happen to agree on. This compares the value handed
        to the sizer against the value on the ring-fence object itself.
        """

        import lib.stocks_reaper as stocks_reaper

        captured: dict = {}
        real = stocks_reaper.build_stocks_reaper

        def spy(**kwargs):
            captured.update(kwargs)
            return real(**kwargs)

        monkeypatch.setattr(stocks_reaper, "build_stocks_reaper", spy)
        assembled = assemble_stocks(stocks(), **paths(tmp_path))

        assert assembled.status == CONFIGURED
        assert captured["currency"] == captured["breakers"].ringfence.currency

    def test_an_unset_currency_denominates_the_lane_where_its_venue_quotes(self, tmp_path):
        breakers = breakers_for("stocks", stocks(), directory=tmp_path,
                                kill_switch=tmp_path / "HALT")

        assert breakers.ringfence.currency == alpaca.QUOTES_IN

    def test_the_panel_and_the_lane_denominate_one_balance_alike(self, tmp_path):
        """`status.py` builds its breakers through the same function, and a currency
        default passed in by each caller would have left the two free to disagree again —
        the panel reporting a euro ring-fence for a lane sizing in dollars."""

        from status import _controls_for

        panel, reason = _controls_for("stocks", stocks(), directory=tmp_path)
        lane = breakers_for("stocks", stocks(), directory=tmp_path,
                            kill_switch=tmp_path / "HALT")

        assert reason == ""
        assert panel.ringfence.currency == lane.ringfence.currency

    def test_the_venue_currency_is_stated_once_rather_than_copied(self):
        """A second literal "USD" in the lane table is the same defect one move along."""

        assert LANE_CURRENCY["stocks"] is alpaca.QUOTES_IN


class TestACurrencyTheVenueDoesNotQuoteStopsTheLane:
    def test_a_euro_ring_fence_refuses_rather_than_sizing_against_a_dollar_ask(
            self, tmp_path):
        assembled = assemble_stocks(stocks(currency="EUR"), **paths(tmp_path))

        assert assembled.status == REFUSED

    def test_the_refusal_names_the_key_and_the_value_to_set(self, tmp_path):
        """"INDETERMINATE" alone trains a reader to skim. This one has to be actionable."""

        reason = assemble_stocks(stocks(currency="EUR"), **paths(tmp_path)).reason

        assert "EUR" in reason and alpaca.QUOTES_IN in reason
        assert "currency" in reason

    def test_it_refuses_rather_than_converting(self, tmp_path):
        """There is no FX rate in this repository and a rate is itself a price that goes
        stale, so a converted size would be a guess wearing a number. The lane stops."""

        reason = assemble_stocks(stocks(currency="EUR"), **paths(tmp_path)).reason

        assert "converts" in reason
        assert "wrong number of shares" in reason

    def test_the_lane_carries_no_reaper_when_it_refuses(self, tmp_path):
        """A REFUSED assembly that still handed back a working reaper would let the run
        size orders against the very mismatch that refused it."""

        assert assemble_stocks(stocks(currency="EUR"), **paths(tmp_path)).reaper is None


class TestTheOtherLanesKeepTheirOwn:
    def test_the_arb_lane_is_still_denominated_in_euro(self, tmp_path):
        """Its books are Irish and British and its stakes are euro. Unifying every lane on
        the stocks venue's currency would have been the same defect with one label."""

        breakers = breakers_for("arb", {"balance": 500.0}, directory=tmp_path,
                                kill_switch=tmp_path / "HALT")

        assert breakers.ringfence.currency == "EUR"

    def test_an_explicit_currency_still_wins_for_a_lane_that_can_hold_one(self, tmp_path):
        breakers = breakers_for("arb", {"balance": 500.0, "currency": "GBP"},
                                directory=tmp_path, kill_switch=tmp_path / "HALT")

        assert breakers.ringfence.currency == "GBP"

    def test_a_lane_outside_the_table_still_gets_a_ring_fence(self, tmp_path):
        """A lane nobody has denominated must not fail to construct — it is REFUSED later,
        by name, for having no placer, which is the message worth reading."""

        breakers = breakers_for("flipper", {"balance": 300.0}, directory=tmp_path,
                                kill_switch=tmp_path / "HALT")

        assert breakers.ringfence.currency == "EUR"
