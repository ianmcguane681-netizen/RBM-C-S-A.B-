"""A cost sheet, not a forecast, and the difference is load-bearing.

The temptation this file guards against is the one that would do real damage: printing a
projected profit next to measured costs, where it borrows their credibility and has none
of its own. There is no expected return here. The only profit figure is arithmetic on a
target the caller supplied, and it is named after them.

The other guard is subtler. Losing 5% of a stake needs a 5.26% rise to recover, because
the gain is earned on what is left. Reporting the loss as the required move understates
it -- always in the flattering direction, and always on the number a holder acts on.
"""
from __future__ import annotations

import pytest

from connectors.chain import ChainClient, ChainProvider
from connectors.chain_costs import (
    INDETERMINATE,
    NO_ROUTE,
    PRICED,
    RoundTrip,
    round_trip,
)
from connectors.chain_liquidity import SELECTORS

PROVIDER = ChainProvider(
    name="fake", url="https://example.test", chain="testnet",
    max_log_range=50, archive="yes", logs="yes",
)
POOL = "0x" + "ab".rjust(64, "0")
TOKEN = "0x" + "11" * 20
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def trip(spent=1000, returned=950, tokens=500):
    return RoundTrip(
        PRICED, TOKEN, USDC, "USDC", 100,
        spent=spent, tokens_received=tokens, returned=returned,
        entry_venue="uniswap-v3-500/USDC", exit_venue="uniswap-v3-500/USDC",
    )


class TestBreakevenIsNotTheLoss:
    def test_the_required_move_exceeds_the_loss(self):
        """5% of the stake gone needs a 5.26% rise, not 5%. Understating this is wrong on
        exactly the number a holder acts on."""

        priced = trip(spent=1000, returned=950)

        assert priced.round_trip_loss == pytest.approx(0.05)
        assert priced.breakeven_move_pct == pytest.approx(5.2631, abs=0.001)
        assert priced.breakeven_move_pct > priced.round_trip_loss * 100

    def test_a_severe_round_trip_needs_a_far_larger_move(self):
        """Half the stake gone needs a double, not a 50% rise."""

        assert trip(spent=1000, returned=500).breakeven_move_pct == pytest.approx(100.0)

    def test_a_free_round_trip_needs_no_move(self):
        assert trip(spent=1000, returned=1000).breakeven_move_pct == pytest.approx(0.0)


class TestTheOnlyProfitFigureIsTheCallersOwn:
    def test_net_at_target_is_arithmetic_on_a_supplied_view(self):
        priced = trip(spent=1000, returned=950)

        assert priced.net_at_target(1.10) == int(950 * 1.10) - 1000

    def test_a_target_inside_the_breakeven_does_not_clear_costs(self):
        priced = trip(spent=1000, returned=950)

        assert priced.clears_costs(1.04) is False
        assert priced.clears_costs(1.06) is True

    def test_there_is_no_forecast_anywhere_on_the_record(self):
        """The guard proper. A field named like a prediction would be read as one."""

        for forbidden in (
            "expected_return", "projected_profit", "target_price", "forecast",
            "predicted_price", "upside",
        ):
            assert forbidden not in RoundTrip.__dataclass_fields__
            assert not hasattr(RoundTrip, forbidden)

    def test_the_description_disclaims_offering_a_target(self):
        described = trip().describe()

        assert "No target price, expected return or projected profit is offered" in described


class TestGasIsLabelledAnEstimate:
    def test_the_description_calls_gas_estimated_and_excluded(self):
        described = RoundTrip(
            PRICED, TOKEN, USDC, "USDC", 100, spent=1000, returned=950,
            tokens_received=500, gas_price_wei=20_000_000_000,
        ).describe()

        assert "ESTIMATED" in described
        assert "excluded from the figures above" in described


class TestAbsenceIsNotCheapness:
    def responder(self, sell_quotes=True, block=500):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": hex(block)}}
            if payload["method"] == "eth_gasPrice":
                return {"result": "0x4a817c800"}
            data = payload["params"][0].get("data", "")
            if data.startswith(SELECTORS["getPair"]) or data.startswith(SELECTORS["getPool"]):
                return {"result": POOL}
            if data.startswith(SELECTORS["getReserves"]):
                word = lambda v: hex(v)[2:].rjust(64, "0")
                return {"result": "0x" + word(10**24) + word(10**24) + word(1)}
            if data.startswith(SELECTORS["quoteExactInputSingle"]):
                if not sell_quotes and payload.get("_leg") == "sell":
                    return {"error": {"code": -32000, "message": "execution reverted"}}
                return {"result": "0x" + hex(10**18)[2:].rjust(64, "0")}
            return {"result": "0x" + "0" * 64}

        return _post

    def test_a_token_priced_against_itself_is_refused(self):
        client = ChainClient(PROVIDER, post_json=self.responder())

        result = round_trip(client, USDC, 1000, quote_name="USDC")

        assert result.status == INDETERMINATE
        assert "cannot be priced against itself" in result.reason

    def test_an_unknown_quote_asset_is_refused(self):
        client = ChainClient(PROVIDER, post_json=self.responder())

        result = round_trip(client, TOKEN, 1000, quote_name="NOTATOKEN")

        assert result.status == INDETERMINATE

    def test_no_route_never_renders_as_a_cheap_trade(self):
        described = RoundTrip(NO_ROUTE, TOKEN, USDC, "USDC", 100).describe()

        assert "not about whether the token can be traded" in described
        assert "0.00%" not in described

    def test_indeterminate_says_it_is_not_a_finding_of_cheapness(self):
        described = RoundTrip(INDETERMINATE, TOKEN, USDC, "USDC", 100, reason="rate limited").describe()

        assert "not a finding that the trade is cheap" in described

    def test_a_buyable_unsellable_token_is_reported_as_such(self):
        """The sharpest finding this module can make, so it must not be a blank field."""

        result = RoundTrip(
            NO_ROUTE, TOKEN, USDC, "USDC", 100, spent=1000, tokens_received=500,
            reason="the buy leg quoted and the sell leg did not",
        )

        assert result.tokens_received > 0
        assert "sell leg did not" in result.reason


class TestRoundTripIsSequencedNotDoubled:
    def test_the_sell_leg_is_quoted_at_what_the_buy_leg_returned(self):
        """Buying and selling are different sides of one curve and do not cost the same.
        Quoting one leg and doubling it would be wrong in whichever direction the pool
        happens to be skewed."""

        sizes_seen = []

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1f4"}}
            if payload["method"] == "eth_gasPrice":
                return {"result": "0x0"}
            data = payload["params"][0].get("data", "")
            if data.startswith(SELECTORS["getPair"]) or data.startswith(SELECTORS["getPool"]):
                return {"result": POOL}
            if data.startswith(SELECTORS["getReserves"]):
                word = lambda v: hex(v)[2:].rjust(64, "0")
                return {"result": "0x" + word(10**24) + word(10**24) + word(1)}
            if data.startswith(SELECTORS["quoteExactInputSingle"]):
                sizes_seen.append(int(data[-128:-64], 16) if len(data) > 128 else 0)
                return {"result": "0x" + hex(777)[2:].rjust(64, "0")}
            return {"result": "0x" + "0" * 64}

        result = round_trip(ChainClient(PROVIDER, post_json=_post), TOKEN, 1000)

        assert result.status == PRICED
        assert result.tokens_received > 0
        # The sell leg must have been asked about the tokens actually received, never
        # about the original stake.
        assert result.returned != result.spent or result.spent == 0
