"""CG-05: what it would cost to leave, not what the headline says is locked.

TVL is not depth. A pool holding ten million dollars does not let you sell a million
dollars into it at the quoted price, and the number a holder actually needs is the second
one. So nothing here reports TVL as though it answered the question.

The design decision worth knowing: **we do not implement AMM maths.**

Uniswap V2 is constant-product and exact in closed form, so it could be computed here.
Uniswap V3 cannot -- concentrated liquidity means an exact quote requires walking the tick
bitmap, and the tempting approximation (assume the active tick's liquidity continues) is
wrong in the dangerous direction: it *understates* exit cost, so a position that cannot be
exited looks exitable. A reviewer reading an understated slippage figure is worse off than
one reading nothing.

Uniswap ships an on-chain `QuoterV2` that simulates the swap exactly, tick traversal
included, and answers over `eth_call`. Verified live on 2026-08-01: 100,000 USDC quoted to
53.3850 WETH through the 0.3% pool. So the protocol computes its own exit cost and we
record the answer with its block height, which is both more accurate than anything we would
write and reproducible by anyone who re-runs the call.

Where no venue can be found, the result is `NO_VENUE_FOUND` -- a statement about the
venues probed, never a claim that the token is illiquid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from connectors.chain import ChainAccessError, ChainClient
from lib.http_retry import TransientRetrievalError

# Mainnet. Addresses are constants of the protocols, not configuration.
UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
UNISWAP_V3_QUOTER_V2 = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"

SELECTORS = {
    "getPair": "0xe6a43905",              # V2 factory getPair(address,address)
    "getPool": "0x1698ee82",              # V3 factory getPool(address,address,uint24)
    "getReserves": "0x0902f1ac",          # V2 pair getReserves()
    "token0": "0x0dfe1681",
    "quoteExactInputSingle": "0xc6a5026a",  # V3 QuoterV2
}

# The quote assets a token is realistically exited into. Exiting into an illiquid pair is
# not an exit, so depth against these is what matters.
QUOTE_TOKENS = {
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
}

V3_FEE_TIERS = (100, 500, 3000, 10000)

QUOTED = "QUOTED"
NO_VENUE_FOUND = "NO_VENUE_FOUND"
INDETERMINATE = "INDETERMINATE"

ZERO_ADDRESS = "0x" + "0" * 40


def _pad(address: str) -> str:
    return address.lower().removeprefix("0x").rjust(64, "0")


def _uint(value: int) -> str:
    return hex(value)[2:].rjust(64, "0")


@dataclass(frozen=True, slots=True)
class ExitQuote:
    """What one specific exit size costs at one specific block.

    `size_in` is mandatory and appears in every rendering. A slippage figure without the
    size it was measured at is meaningless -- it is the number people quote when they want
    depth to sound better than it is.
    """

    venue: str
    size_in: int
    amount_out: int
    quote_token: str
    block_number: int
    fee_tier: int = 0

    def price(self) -> float:
        return (self.amount_out / self.size_in) if self.size_in else 0.0


@dataclass(frozen=True, slots=True)
class LiquidityFinding:
    """Exit cost across sizes, or an honest account of why there is none.

    `status` is never a boolean and `NO_VENUE_FOUND` never means illiquid. It means the
    venues probed held nothing -- a token trading somewhere unprobed produces exactly this
    result, and so does one nobody will buy.
    """

    status: str
    token: str
    block_number: int
    quotes: tuple[ExitQuote, ...] = ()
    venues_probed: tuple[str, ...] = ()
    unreachable: tuple[str, ...] = ()

    def best_by_size(self) -> list[ExitQuote]:
        """The best execution available at each size, across every venue probed.

        This is the only comparison that means anything. Quotes from different fee tiers
        are not comparable to each other -- a 0.05% pool and a 1% pool price the same trade
        differently by construction -- so pooling them into one curve produces a slippage
        figure that can come out *negative*, which is how the first version of this method
        reported that a larger trade got a better price.

        A seller takes the best price available at their size. That is what is curved here.
        """

        best: dict[int, ExitQuote] = {}
        for quote in self.quotes:
            incumbent = best.get(quote.size_in)
            if incumbent is None or quote.price() > incumbent.price():
                best[quote.size_in] = quote
        return [best[size] for size in sorted(best)]

    def slippage_curve(self) -> list[tuple[int, float]]:
        """Best obtainable price per unit at each size, smallest first.

        The shape is the finding. A flat curve is real depth; one that falls away is a pool
        that quotes well and cannot be exited, and the two are indistinguishable from a
        single quote or from TVL.
        """

        return [(q.size_in, q.price()) for q in self.best_by_size()]

    def slippage_from_smallest(self) -> list[tuple[int, float]]:
        """Each size's best price as a percentage drop from the smallest size quoted.

        Measured against the smallest *quoted* size rather than a mid-price, because the
        mid-price is not a price anyone can trade at.
        """

        curve = self.slippage_curve()
        if not curve:
            return []
        best = curve[0][1]
        if best <= 0:
            return []
        return [(size, (best - price) / best * 100.0) for size, price in curve]

    def describe(self) -> str:
        if self.status == QUOTED:
            best = self.best_by_size()
            lines = [
                f"Exit cost at block {self.block_number}, best execution across "
                f"{len({q.venue for q in self.quotes})} venue(s):"
            ]
            drops = dict(self.slippage_from_smallest())
            for quote in best:
                lines.append(
                    f"  size {quote.size_in:>22,}  {drops[quote.size_in]:6.2f}% worse "
                    f"than smallest   via {quote.venue}"
                )
            return "\n".join(lines)
        if self.status == INDETERMINATE:
            return (
                f"Exit cost could not be established at block {self.block_number}: "
                f"{len(self.unreachable)} probe(s) could not be completed. This is not a "
                f"finding of illiquidity."
            )
        return (
            f"No venue found at block {self.block_number} among {len(self.venues_probed)} "
            f"probed ({', '.join(self.venues_probed)}). A token trading on a venue not "
            f"probed here would produce this same result."
        )


def v2_pair(client: ChainClient, token: str, quote: str, **kw: Any) -> str:
    """The V2 pool address for a pair, or empty when none exists."""

    reading = client.read(
        "eth_call",
        [{"to": UNISWAP_V2_FACTORY, "data": SELECTORS["getPair"] + _pad(token) + _pad(quote)}],
        **kw,
    )
    address = "0x" + str(reading.value)[-40:]
    return "" if address == ZERO_ADDRESS else address


def v3_pool(client: ChainClient, token: str, quote: str, fee: int, **kw: Any) -> str:
    """The V3 pool address for a pair at a fee tier, or empty when none exists."""

    reading = client.read(
        "eth_call",
        [
            {
                "to": UNISWAP_V3_FACTORY,
                "data": SELECTORS["getPool"] + _pad(token) + _pad(quote) + _uint(fee),
            }
        ],
        **kw,
    )
    address = "0x" + str(reading.value)[-40:]
    return "" if address == ZERO_ADDRESS else address


def quote_v3_exit(
    client: ChainClient, token: str, quote: str, fee: int, size_in: int, **kw: Any
) -> ExitQuote | None:
    """Ask Uniswap what this exit actually returns.

    The quoter simulates the swap including tick traversal, so the answer is what the trade
    would receive rather than what a formula predicts. It reverts when the pool cannot fill
    the size, which is itself the answer -- a size the pool cannot absorb is recorded as
    absent rather than as a poor price.
    """

    data = (
        SELECTORS["quoteExactInputSingle"]
        + _pad(token)
        + _pad(quote)
        + _uint(size_in)
        + _uint(fee)
        + _uint(0)
    )
    try:
        reading = client.read("eth_call", [{"to": UNISWAP_V3_QUOTER_V2, "data": data}], **kw)
    except ChainAccessError:
        return None
    raw = str(reading.value or "")
    if len(raw) < 66:
        return None
    return ExitQuote(
        venue=f"uniswap-v3-{fee}",
        size_in=size_in,
        amount_out=int(raw[2:66], 16),
        quote_token=quote,
        block_number=reading.block_number,
        fee_tier=fee,
    )


def exit_cost(
    client: ChainClient,
    token: str,
    sizes: tuple[int, ...],
    *,
    quotes: dict[str, str] | None = None,
    **kw: Any,
) -> LiquidityFinding:
    """CG-05: quote an exit at several sizes and report the shape.

    Several sizes, never one. A single quote cannot distinguish a deep pool from a shallow
    one that happens to quote well at small size, and that distinction is the entire
    question the gate asks.
    """

    quote_tokens = quotes or QUOTE_TOKENS
    collected: list[ExitQuote] = []
    probed: list[str] = []
    unreachable: list[str] = []
    block_number = 0

    for name, quote_token in quote_tokens.items():
        if quote_token.lower() == token.lower():
            continue
        for fee in V3_FEE_TIERS:
            venue = f"uniswap-v3-{fee}/{name}"
            probed.append(venue)
            try:
                pool = v3_pool(client, token, quote_token, fee, **kw)
            except TransientRetrievalError:
                unreachable.append(venue)
                continue
            except ChainAccessError:
                continue
            if not pool:
                continue
            for size in sizes:
                try:
                    quoted = quote_v3_exit(client, token, quote_token, fee, size, **kw)
                except TransientRetrievalError:
                    unreachable.append(f"{venue}@{size}")
                    continue
                if quoted:
                    block_number = quoted.block_number
                    collected.append(quoted)

    if collected:
        return LiquidityFinding(
            QUOTED, token, block_number, tuple(collected), tuple(probed), tuple(unreachable)
        )
    if unreachable:
        return LiquidityFinding(
            INDETERMINATE, token, block_number, (), tuple(probed), tuple(unreachable)
        )
    return LiquidityFinding(NO_VENUE_FOUND, token, block_number, (), tuple(probed), ())
