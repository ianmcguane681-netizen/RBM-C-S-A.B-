"""TVL is not depth, and a single quote is not a curve.

CG-05 asks what it costs to leave. Two things make that question easy to answer wrongly.

The first is Uniswap V3. An exact quote requires walking the tick bitmap, and the tempting
approximation -- assume the active tick's liquidity continues -- fails in the dangerous
direction: it understates exit cost, so a position that cannot be exited looks exitable.
We ask the protocol's own quoter instead and never reimplement the maths.

The second bit me while building this. Quotes from different fee tiers are not comparable
to each other, so pooling them into one curve produced slippage that came out *negative* --
the first version reported that a larger trade got a better price. A seller takes the best
price available at their size, and that is what must be curved.
"""
from __future__ import annotations

import pytest

from connectors.chain import ChainClient, ChainProvider
from connectors.chain_liquidity import (
    INDETERMINATE,
    NO_VENUE_FOUND,
    QUOTED,
    UNISWAP_V3_QUOTER_V2,
    ExitQuote,
    LiquidityFinding,
    exit_cost,
)

PROVIDER = ChainProvider(
    name="fake", url="https://example.test", chain="testnet",
    max_log_range=50, archive="yes",
)
ZERO = "0x" + "0" * 64
POOL = "0x" + "ab".rjust(64, "0")
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


def quote(size, out, venue="uniswap-v3-500", fee=500, block=100):
    return ExitQuote(venue=venue, size_in=size, amount_out=out,
                     quote_token=WETH, block_number=block, fee_tier=fee)


class TestBestExecutionNotPooledQuotes:
    """The bug this class exists for produced a negative slippage figure."""

    def test_the_best_price_at_each_size_is_what_is_curved(self):
        finding = LiquidityFinding(QUOTED, "0xtok", 100, (
            quote(100, 90, "uniswap-v3-10000", 10000),   # 1% pool, worse
            quote(100, 99, "uniswap-v3-500", 500),       # 0.05% pool, better
        ))

        best = finding.best_by_size()

        assert len(best) == 1
        assert best[0].amount_out == 99
        assert best[0].venue == "uniswap-v3-500"

    def test_slippage_is_never_negative_for_a_well_formed_pool(self):
        """A larger trade cannot get a better price than a smaller one at best execution.
        The first implementation reported exactly that by comparing across fee tiers."""

        finding = LiquidityFinding(QUOTED, "0xtok", 100, (
            quote(100, 100), quote(1000, 995), quote(10000, 9800),
            # a worse venue at every size, which must never win
            quote(100, 80, "uniswap-v3-10000", 10000),
            quote(1000, 800, "uniswap-v3-10000", 10000),
            quote(10000, 8000, "uniswap-v3-10000", 10000),
        ))

        drops = finding.slippage_from_smallest()

        assert [size for size, _ in drops] == [100, 1000, 10000]
        assert all(drop >= 0 for _, drop in drops)

    def test_the_curve_reports_each_size_once(self):
        """Four fee tiers used to produce four rows per size, which reads as four sizes."""

        finding = LiquidityFinding(QUOTED, "0xtok", 100, tuple(
            quote(100, 100 - fee // 100, f"uniswap-v3-{fee}", fee)
            for fee in (100, 500, 3000, 10000)
        ))

        assert len(finding.slippage_curve()) == 1

    def test_slippage_rises_with_size(self):
        finding = LiquidityFinding(QUOTED, "0xtok", 100, (
            quote(1, 10), quote(10, 99), quote(100, 900),
        ))

        drops = dict(finding.slippage_from_smallest())

        assert drops[1] == pytest.approx(0.0)
        assert drops[10] > drops[1]
        assert drops[100] > drops[10]

    def test_the_venue_that_gave_the_best_price_is_named(self):
        """A reviewer needs to know the exit depends on one pool."""

        finding = LiquidityFinding(QUOTED, "0xtok", 100, (
            quote(100, 99, "uniswap-v3-500", 500),
            quote(100, 90, "uniswap-v3-3000", 3000),
        ))

        assert "uniswap-v3-500" in finding.describe()


class TestAbsenceOfVenueIsNotIlliquidity:
    def responder(self, pool=ZERO, block=500):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": hex(block)}}
            return {"result": pool}

        return _post

    def test_no_pool_anywhere_reports_no_venue_found(self):
        client = ChainClient(PROVIDER, post_json=self.responder())

        finding = exit_cost(client, "0xtok", (100,), quotes={"WETH": WETH})

        assert finding.status == NO_VENUE_FOUND

    def test_the_wording_never_claims_illiquidity(self):
        finding = LiquidityFinding(NO_VENUE_FOUND, "0xtok", 5, (), ("uniswap-v3-500/WETH",))

        described = finding.describe().lower()

        assert "illiquid" not in described
        assert "no liquidity" not in described
        assert "would produce this same result" in described

    def test_indeterminate_is_explicitly_not_a_finding_of_illiquidity(self):
        finding = LiquidityFinding(INDETERMINATE, "0xtok", 5, (), (), ("v3/WETH",))

        assert "not a finding of illiquidity" in finding.describe()

    def test_a_transient_failure_yields_indeterminate_not_no_venue(self):
        """Concluding 'nowhere to sell' from probes that never ran is the EG-02 defect."""

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            return {"error": {"code": -32005, "message": "rate limit exceeded"}}

        finding = exit_cost(ChainClient(PROVIDER, post_json=_post), "0xt", (1,),
                            quotes={"WETH": WETH})

        assert finding.status == INDETERMINATE
        assert finding.unreachable

    def test_every_probed_venue_is_recorded_so_absence_can_be_judged(self):
        client = ChainClient(PROVIDER, post_json=self.responder())

        finding = exit_cost(client, "0xtok", (100,), quotes={"WETH": WETH})

        assert len(finding.venues_probed) == 4  # one per fee tier
        assert str(len(finding.venues_probed)) in finding.describe()


class TestSizeIsAlwaysCarried:
    def test_a_quote_records_the_size_it_was_measured_at(self):
        """A slippage figure without its size is the number people quote when they want
        depth to sound better than it is."""

        q = quote(10_000, 9_800)

        assert q.size_in == 10_000
        assert q.price() == pytest.approx(0.98)

    def test_a_zero_size_does_not_produce_a_price(self):
        assert quote(0, 100).price() == 0.0

    def test_the_pool_is_asked_rather_than_a_formula_applied(self):
        """The quoter address is the protocol's own. If this test starts failing because
        someone replaced the call with arithmetic, that is the regression it guards."""

        seen = []

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            target = payload["params"][0].get("to", "")
            seen.append(target)
            return {"result": POOL}

        exit_cost(ChainClient(PROVIDER, post_json=_post), "0xtok", (100,),
                  quotes={"WETH": WETH})

        assert UNISWAP_V3_QUOTER_V2 in seen
