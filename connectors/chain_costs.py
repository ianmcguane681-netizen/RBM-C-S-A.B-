"""What a round trip costs, measured rather than forecast.

The board says whether a token is what it claims. That is a hygiene check and not a reason
to buy anything. This module answers the separate, narrower question a holder actually
faces: **how far does the price have to move before I am even?**

Everything here is a measurement at a block height. There is no forecast, no target price,
no expected return and no "projected profit" — because producing one would require a view
this system does not have, and a fabricated number printed beside measured ones borrows
their credibility. That is the sentinel defect at the level where it costs money.

The one honest way to reach a profit figure is for a human to supply the target themselves,
which `net_at_target` does: arithmetic on the caller's thesis, clearly labelled as theirs.

The round trip is simulated in a single quote asset, in sequence:

    spend Q of the quote asset  ->  receive T tokens  ->  sell exactly T  ->  receive Q'

`(Q - Q') / Q` is the breakeven move. Both legs carry the venue's real fee because both are
quoted from the pool rather than from a formula, and staying inside one asset means the two
numbers are comparable — the mistake that made `best_by_size` name DAI best execution on
the strength of having eighteen decimals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from connectors.chain import ChainAccessError, ChainClient
from connectors.chain_liquidity import (
    QUOTE_TOKENS,
    V3_FEE_TIERS,
    ExitQuote,
    quote_v2_exit,
    quote_v3_exit,
)
from lib.http_retry import TransientRetrievalError

PRICED = "PRICED"
NO_ROUTE = "NO_ROUTE"
INDETERMINATE = "INDETERMINATE"

# Two swaps, generously. A measurement would need a simulated transaction; this is an
# estimate and is labelled as one everywhere it appears, because a stated assumption is
# honest and a silent one is not.
ASSUMED_SWAP_GAS = 180_000
SWAPS_PER_ROUND_TRIP = 2


@dataclass(frozen=True, slots=True)
class RoundTrip:
    """Buy then sell, at one size, in one quote asset, at one block."""

    status: str
    token: str
    quote_asset: str
    quote_name: str
    block_number: int
    spent: int = 0
    tokens_received: int = 0
    returned: int = 0
    entry_venue: str = ""
    exit_venue: str = ""
    gas_price_wei: int = 0
    reason: str = ""

    @property
    def round_trip_loss(self) -> float:
        """Fraction of the stake consumed by going in and coming straight back out."""

        if not self.spent:
            return 0.0
        return (self.spent - self.returned) / self.spent

    @property
    def breakeven_move_pct(self) -> float:
        """How far the price must rise before the position is worth what it cost.

        Not the same as the round-trip loss. Losing 5% of the stake needs a 5.26% rise to
        recover, because the gain is earned on what is left. Reporting the loss as the
        required move understates it, always in the flattering direction.
        """

        if not self.returned:
            return 0.0
        return (self.spent - self.returned) / self.returned * 100.0

    def net_at_target(self, target_multiple: float) -> int:
        """What the caller nets if the price moves as THEY say it will.

        `target_multiple` is the caller's thesis and nothing else: 1.10 means they expect a
        10% rise. This module has no opinion on whether that happens, and the arithmetic
        below must never be presented as though it did.
        """

        return int(self.returned * target_multiple) - self.spent

    def clears_costs(self, target_multiple: float) -> bool:
        return self.net_at_target(target_multiple) > 0

    def describe(self) -> str:
        if self.status == NO_ROUTE:
            return (
                f"No route both ways for {self.token} in {self.quote_name} at block "
                f"{self.block_number}. This is a statement about the venues probed, not "
                f"about whether the token can be traded."
            )
        if self.status == INDETERMINATE:
            return (
                f"Round-trip cost could not be established at block {self.block_number}: "
                f"{self.reason}. This is not a finding that the trade is cheap."
            )
        gas = self.gas_price_wei * ASSUMED_SWAP_GAS * SWAPS_PER_ROUND_TRIP
        return "\n".join([
            f"Round trip at block {self.block_number}, priced in {self.quote_name}:",
            f"  spend        {self.spent:,} {self.quote_name} via {self.entry_venue}",
            f"  receive      {self.tokens_received:,} token units",
            f"  sell back    {self.returned:,} {self.quote_name} via {self.exit_venue}",
            f"  cost of the round trip   {self.round_trip_loss * 100:.2f}% of the stake",
            f"  BREAKEVEN: the price must rise {self.breakeven_move_pct:.2f}% before you "
            f"are even",
            f"  gas, ESTIMATED at {ASSUMED_SWAP_GAS:,} units x {SWAPS_PER_ROUND_TRIP} "
            f"swaps: {gas / 10**18:.5f} ETH, excluded from the figures above",
            "  No target price, expected return or projected profit is offered. Those "
            "require a view this measurement does not contain.",
        ])


def _best_quote(
    client: ChainClient, sell: str, receive: str, size: int, name: str, **kw: Any
) -> ExitQuote | None:
    """The best price obtainable selling `size` of `sell` into `receive`.

    Every venue is probed and the best taken, which is what a seller gets. Comparison is
    safe here because every candidate is denominated in the same asset.
    """

    best: ExitQuote | None = None
    candidates = []
    try:
        candidates.append(quote_v2_exit(client, sell, receive, size, quote_name=name, **kw))
        for fee in V3_FEE_TIERS:
            candidates.append(
                quote_v3_exit(client, sell, receive, fee, size, quote_name=name, **kw)
            )
    except (TransientRetrievalError, ChainAccessError):
        return None
    for quoted in candidates:
        if quoted and (best is None or quoted.amount_out > best.amount_out):
            best = quoted
    return best


def round_trip(
    client: ChainClient,
    token: str,
    stake: int,
    *,
    quote_name: str = "USDC",
    quote_asset: str = "",
    **kw: Any,
) -> RoundTrip:
    """Buy `stake` worth of `token`, then sell every unit straight back.

    Sequenced rather than assumed symmetric. Buying and selling are different sides of the
    same curve and do not cost the same, so quoting one and doubling it would be wrong in
    whichever direction the pool happens to be skewed.
    """

    asset = quote_asset or QUOTE_TOKENS.get(quote_name, "")
    if not asset:
        return RoundTrip(INDETERMINATE, token, "", quote_name, 0,
                         reason=f"no address known for quote asset {quote_name}")
    if asset.lower() == token.lower():
        return RoundTrip(INDETERMINATE, token, asset, quote_name, 0,
                         reason="a token cannot be priced against itself")

    entry = _best_quote(client, asset, token, stake, quote_name, **kw)
    if entry is None or entry.amount_out <= 0:
        return RoundTrip(NO_ROUTE, token, asset, quote_name, 0,
                         reason="no venue quoted the buy leg")

    exit_leg = _best_quote(client, token, asset, entry.amount_out, quote_name, **kw)
    if exit_leg is None or exit_leg.amount_out <= 0:
        # A token that can be bought and not sold is the sharpest finding this module can
        # produce, and it must never render as a missing number.
        return RoundTrip(
            NO_ROUTE, token, asset, quote_name, entry.block_number,
            spent=stake, tokens_received=entry.amount_out,
            entry_venue=entry.venue,
            reason="the buy leg quoted and the sell leg did not",
        )

    try:
        gas_price = int(str(client.read("eth_gasPrice", []).value or "0x0"), 16)
    except (TransientRetrievalError, ChainAccessError):
        gas_price = 0

    return RoundTrip(
        status=PRICED,
        token=token,
        quote_asset=asset,
        quote_name=quote_name,
        block_number=exit_leg.block_number,
        spent=stake,
        tokens_received=entry.amount_out,
        returned=exit_leg.amount_out,
        entry_venue=entry.venue,
        exit_venue=exit_leg.venue,
        gas_price_wei=gas_price,
    )


def largest_stake_within(
    client: ChainClient,
    token: str,
    ceiling_pct: float,
    *,
    candidates: Sequence[int],
    quote_name: str = "USDC",
    **kw: Any,
) -> tuple[int, RoundTrip | None]:
    """The biggest stake whose round trip stays under `ceiling_pct`.

    Chosen from stated candidates rather than searched, so the answer is always one of a
    set the caller can see. A binary search would report a size nobody asked about and
    hide how coarse the sampling was.
    """

    best_size, best_trip = 0, None
    for size in sorted(candidates):
        trip = round_trip(client, token, size, quote_name=quote_name, **kw)
        if trip.status != PRICED or trip.round_trip_loss * 100 > ceiling_pct:
            break
        best_size, best_trip = size, trip
    return best_size, best_trip
