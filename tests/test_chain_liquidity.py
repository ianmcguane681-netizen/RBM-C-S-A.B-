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
    V3_FEE_TIERS,
    SELECTORS,
    UNISWAP_V2_FACTORY,
    UNISWAP_V3_FACTORY,
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
        """Asserted by composition rather than a count. A magic number here would have to
        be edited every time a venue is added, and editing it is exactly the moment
        someone stops noticing what the number is for."""

        client = ChainClient(PROVIDER, post_json=self.responder())

        finding = exit_cost(client, "0xtok", (100,), quotes={"WETH": WETH})

        assert any("uniswap-v2" in v for v in finding.venues_probed)
        assert sum("uniswap-v3" in v for v in finding.venues_probed) == len(V3_FEE_TIERS)
        assert str(len(finding.venues_probed)) in finding.describe()


class TestV2IsProbed:
    """The regression test for a shipped defect.

    `v2_pair` was written and never called. `exit_cost` probed only V3 fee tiers, so a
    token trading solely on Uniswap V2 -- most older and smaller tokens -- returned
    NO_VENUE_FOUND while having real liquidity. A false absence, produced by the module
    written to refuse false absences.
    """

    def v2_only_responder(self, reserve_token=10**24, reserve_quote=10**21, block=400):
        """A world where the V2 factory has a pair and the V3 factory has nothing."""

        pair = "0x" + "cc".rjust(64, "0")
        reserves = "0x" + hex(reserve_token)[2:].rjust(64, "0") + hex(reserve_quote)[2:].rjust(64, "0") + "0" * 64

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": hex(block)}}
            call = payload["params"][0]
            target = call.get("to", "").lower()
            data = call.get("data", "")
            if target == UNISWAP_V2_FACTORY.lower():
                return {"result": pair}
            if target == UNISWAP_V3_FACTORY.lower():
                return {"result": ZERO}
            if data.startswith(SELECTORS["getReserves"]):
                return {"result": reserves}
            if data.startswith(SELECTORS["token0"]):
                return {"result": "0x" + "tok".encode().hex().rjust(64, "0")}
            return {"result": ZERO}

        return _post

    def test_a_v2_only_token_is_quoted_not_reported_absent(self):
        client = ChainClient(PROVIDER, post_json=self.v2_only_responder())

        finding = exit_cost(client, "0xtok", (10**18,), quotes={"WETH": WETH})

        assert finding.status == QUOTED, "V2-only liquidity must not read as NO_VENUE_FOUND"
        assert any(q.venue.startswith("uniswap-v2") for q in finding.quotes)

    def test_v2_is_listed_among_the_probed_venues(self):
        """So that a genuine NO_VENUE_FOUND can be trusted to have looked there."""

        client = ChainClient(PROVIDER, post_json=self.v2_only_responder())

        finding = exit_cost(client, "0xtok", (10**18,), quotes={"WETH": WETH})

        assert any("uniswap-v2" in v for v in finding.venues_probed)

    def test_the_constant_product_fee_is_applied(self):
        """Omitting the 0.3% fee overstates the proceeds of every exit, consistently and
        in the flattering direction."""

        from connectors.chain_liquidity import quote_v2_exit

        client = ChainClient(PROVIDER, post_json=self.v2_only_responder(
            reserve_token=10**24, reserve_quote=10**24))

        quoted = quote_v2_exit(client, "0xtok", WETH, 10**18)

        # With equal reserves and a tiny trade, output approaches size * 0.997.
        assert quoted is not None
        assert quoted.amount_out < 10**18
        assert quoted.amount_out > 10**18 * 0.996

    def test_v2_and_v3_compete_on_one_best_execution_curve(self):
        """The point of fixing the gap: a seller takes the better of the two."""

        finding = LiquidityFinding(QUOTED, "0xtok", 100, (
            quote(100, 90, "uniswap-v2", 3000),
            quote(100, 99, "uniswap-v3-500", 500),
        ))

        assert finding.best_by_size()[0].venue == "uniswap-v3-500"


class TestQuoteAssetsAreNotComparable:
    """The same defect as the class above, one axis over, found live on USDC.

    `price()` is `amount_out / size_in` in RAW token units. Across quote assets that is
    not a price comparison, it is a decimals comparison: DAI (18 decimals, trading near
    a dollar) yields ~1e12 while USDT (6 decimals, trading near the same dollar) yields
    ~1. Whichever asset carries more decimals wins every size, regardless of execution.

    The Tier 2 USDC review quoted one asset, so the fault could not appear. Acting on the
    sceptical reviewer's finding -- quote more assets -- produced it immediately, with DAI
    named best execution at every size and a 99.14% slippage figure whose baseline and
    worst case were different pools.

    A cross-asset best price needs a common numéraire, which needs an oracle this profile
    does not have. So it is refused rather than approximated.
    """

    DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    USDT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

    def mixed(self):
        """One size, two assets, both trading at par. Only the decimals differ."""

        return LiquidityFinding(QUOTED, "0xtok", 100, (
            ExitQuote("uniswap-v3-100/DAI", 10**10, 9_990 * 10**18, self.DAI, 100, 100),
            # The genuinely better execution: 0.05% more out, in an asset with 6 decimals.
            ExitQuote("uniswap-v3-100/USDT", 10**10, 9_995 * 10**6, self.USDT, 100, 100),
        ))

    def test_a_curve_across_quote_assets_is_refused_rather_than_computed(self):
        with pytest.raises(ValueError, match="quote asset"):
            self.mixed().best_by_size()

    def test_naming_the_quote_asset_gives_a_curve(self):
        best = self.mixed().best_by_size(self.USDT)

        assert len(best) == 1
        assert best[0].quote_token == self.USDT

    def test_the_asset_with_more_decimals_is_not_declared_best(self):
        """The regression proper. Raw-magnitude comparison picks DAI here, always."""

        assert self.mixed().best_by_size(self.DAI)[0].amount_out == 9_990 * 10**18
        assert self.mixed().best_by_size(self.USDT)[0].amount_out == 9_995 * 10**6

    def test_one_quote_asset_still_needs_no_argument(self):
        """Single-asset findings keep working without ceremony."""

        finding = LiquidityFinding(QUOTED, "0xtok", 100, (quote(100, 99), quote(100, 90)))

        assert finding.best_by_size()[0].amount_out == 99

    def test_slippage_is_reported_per_quote_asset(self):
        curves = self.mixed().curves_by_quote()

        assert set(curves) == {self.DAI, self.USDT}

    def test_the_description_states_that_assets_are_not_compared(self):
        described = self.mixed().describe()

        assert "not compared across quote assets" in described

    def test_the_description_never_names_one_asset_as_best_overall(self):
        described = self.mixed().describe().lower()

        for overreach in ("best execution across", "best overall", "cheapest exit"):
            assert overreach not in described


class TestAVenueIsAPoolNotAFeeTier:
    """15 probed venues collapsed to 5, because the label omitted the quote asset."""

    def test_the_quote_asset_appears_in_the_venue_label(self):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            data = payload["params"][0].get("data", "")
            if data.startswith(SELECTORS["getPair"]) or data.startswith(SELECTORS["getPool"]):
                return {"result": POOL}
            if data.startswith(SELECTORS["getReserves"]):
                word = lambda v: hex(v)[2:].rjust(64, "0")
                return {"result": "0x" + word(10**24) + word(10**24) + word(1)}
            return {"result": "0x" + hex(10**18)[2:].rjust(64, "0")}

        finding = exit_cost(ChainClient(PROVIDER, post_json=_post), "0xtok", (100,),
                            quotes={"WETH": WETH, "USDT": TestQuoteAssetsAreNotComparable.USDT})

        assert any(v.endswith("/WETH") for v in finding.venues_probed)
        assert any(q.venue.endswith("/USDT") for q in finding.quotes)
        # The count that was wrong: two assets on the same fee tier are two pools, and
        # a label without the asset counts them as one.
        assert len({q.venue for q in finding.quotes}) > len(
            {q.venue.split("/")[0] for q in finding.quotes}
        )


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
