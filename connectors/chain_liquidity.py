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
from typing import Any, Sequence

from connectors.chain import ChainAccessError, ChainClient
from lib.http_retry import TransientRetrievalError
from lib.shares import format_share

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


@dataclass(frozen=True, slots=True)
class PoolComposition:
    """Who owns the liquidity, which is a different question from how much there is.

    The three categories are never summed. Burned LP is permanent; locked LP returns on a
    schedule; project-held LP can leave at any moment. A single "not really available"
    figure would hide the distinction a holder most needs -- headline depth that is mostly
    the project's own liquidity is exactly the case CG-05 names.
    """

    pair: str
    block_number: int
    lp_total_supply: int
    burned: tuple[tuple[str, int], ...] = ()
    locked: tuple[tuple[str, int], ...] = ()
    project_held: tuple[tuple[str, int], ...] = ()
    # Uniswap V3 positions are NFTs held by a position manager rather than fungible LP
    # tokens, so this analysis does not reach them. Stated rather than omitted: a V2-only
    # composition presented as complete would understate project-held depth on any token
    # whose real liquidity sits in V3.
    covers_v3: bool = False

    def _share(self, amount: int) -> float:
        return (amount / self.lp_total_supply * 100.0) if self.lp_total_supply else 0.0

    @property
    def burned_share(self) -> float:
        return self._share(sum(a for _, a in self.burned))

    @property
    def locked_share(self) -> float:
        return self._share(sum(a for _, a in self.locked))

    @property
    def project_share(self) -> float:
        return self._share(sum(a for _, a in self.project_held))

    def describe(self) -> str:
        lines = [
            f"LP ownership of {self.pair} at block {self.block_number} "
            f"(supply {self.lp_total_supply:,}):",
            f"  burned        {format_share(sum(a for _, a in self.burned), self.lp_total_supply):>12}  permanent",
            f"  locked        {format_share(sum(a for _, a in self.locked), self.lp_total_supply):>12}  returns on a schedule",
            f"  project-held  {format_share(sum(a for _, a in self.project_held), self.lp_total_supply):>12}  can be withdrawn at any time",
            "  These are reported separately and are not summed.",
        ]
        if not self.covers_v3:
            lines.append(
                "  Uniswap V3 positions are NFTs and are NOT covered by this analysis, so "
                "liquidity held there is neither counted nor excluded."
            )
        return "\n".join(lines)


def pool_ownership(
    client: ChainClient,
    pair: str,
    *,
    burn_addresses: Sequence[str] = (),
    locker_addresses: Sequence[str] = (),
    project_addresses: Sequence[str] = (),
    **kw: Any,
) -> PoolComposition:
    """Read LP ownership. A V2 pair is itself an ERC-20, so this needs no new machinery.

    Callers supply the three address groups because only the caller knows which is which:
    the same address is a treasury to one project and a locker to another, and guessing
    would put withdrawable liquidity in the permanent column.
    """

    from connectors.chain_queries import balance_of, total_supply

    supply_reading = total_supply(client, pair, **kw)
    supply = int(str(supply_reading.value or "0x0"), 16)

    def _balances(addresses: Sequence[str]) -> tuple[tuple[str, int], ...]:
        out: list[tuple[str, int]] = []
        for address in addresses:
            try:
                reading = balance_of(client, pair, address, **kw)
            except ChainAccessError:
                continue
            amount = int(str(reading.value or "0x0"), 16)
            if amount > 0:
                out.append((address, amount))
        return tuple(out)

    return PoolComposition(
        pair=pair,
        block_number=supply_reading.block_number,
        lp_total_supply=supply,
        burned=_balances(burn_addresses),
        locked=_balances(locker_addresses),
        project_held=_balances(project_addresses),
    )


def v2_reserves(client: ChainClient, pair: str, token: str, **kw: Any) -> tuple[int, int, int]:
    """Reserves of a V2 pair, oriented so the first is the token being sold.

    `getReserves` returns them in token0/token1 order, which is address-sorted and has
    nothing to do with which side the caller is selling. Getting the orientation wrong
    inverts the price and produces a quote that is wrong by the square of the ratio while
    still looking like a number.
    """

    reading = client.read("eth_call", [{"to": pair, "data": SELECTORS["getReserves"]}], **kw)
    raw = str(reading.value or "")
    if len(raw) < 130:
        raise ChainAccessError(f"{pair} did not return reserves")
    reserve0 = int(raw[2:66], 16)
    reserve1 = int(raw[66:130], 16)

    token0_reading = client.read("eth_call", [{"to": pair, "data": SELECTORS["token0"]}], **kw)
    token0 = "0x" + str(token0_reading.value)[-40:]
    if token0.lower() == token.lower():
        return reserve0, reserve1, reading.block_number
    return reserve1, reserve0, reading.block_number


def quote_v2_exit(
    client: ChainClient, token: str, quote: str, size_in: int, **kw: Any
) -> ExitQuote | None:
    """Constant-product output, exactly.

    V2 is closed form, so unlike V3 there is nothing to approximate and no quoter needed:

        out = (in * 997 * reserve_out) / (reserve_in * 1000 + in * 997)

    The 997/1000 is the 0.3% fee, taken on the input. Omitting it would overstate the
    proceeds of every exit by 0.3%, consistently and in the flattering direction.
    """

    try:
        pair = v2_pair(client, token, quote, **kw)
    except ChainAccessError:
        return None
    if not pair:
        return None
    try:
        reserve_in, reserve_out, block_number = v2_reserves(client, pair, token, **kw)
    except ChainAccessError:
        return None
    if reserve_in <= 0 or reserve_out <= 0:
        return None

    amount_in_with_fee = size_in * 997
    amount_out = (amount_in_with_fee * reserve_out) // (reserve_in * 1000 + amount_in_with_fee)
    if amount_out <= 0:
        return None
    return ExitQuote(
        venue="uniswap-v2",
        size_in=size_in,
        amount_out=amount_out,
        quote_token=quote,
        block_number=block_number,
        fee_tier=3000,
    )


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

        # V2 first, and not as an afterthought. An earlier version defined `v2_pair` and
        # never called it, so a token trading only on V2 -- which is most older and smaller
        # tokens -- returned NO_VENUE_FOUND while having real liquidity. A false absence,
        # produced by the module written to refuse false absences.
        v2_venue = f"uniswap-v2/{name}"
        probed.append(v2_venue)
        for size in sizes:
            try:
                quoted = quote_v2_exit(client, token, quote_token, size, **kw)
            except TransientRetrievalError:
                unreachable.append(f"{v2_venue}@{size}")
                continue
            if quoted:
                block_number = quoted.block_number
                collected.append(quoted)

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
