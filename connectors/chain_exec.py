"""A chain swap computed to the last byte and deliberately left unsigned.

Every other execution adapter in this repository can place. This one cannot, and the
refusal is structural rather than a setting: there is no key path, no signing library, no
`send`, and `sign()` raises whatever you pass it.

## Why this lane alone is built this way

`lib/reaper.NEVER_AUTONOMOUS` already refuses autonomous placement for the chain lane. That
is a policy, and a policy is a thing somebody can change at eleven at night. This is the
same conclusion expressed as an absence: an adapter that never had the capability cannot be
talked into using it.

The reasons are specific to chains rather than general caution. A signed transaction is
atomic and irreversible — there is no order to cancel, no counterparty to ring and no
chargeback. The key that signs a 200 USDC swap is usually the key that controls everything
else in the wallet, so the blast radius of a bug is not the size of the position. And a
swap broadcast without a floor on what comes back is an invitation to be sandwiched, which
is not a tail risk but a business somebody runs.

## What it does produce

A plan a person signs in a wallet they control, with the two things a hand-built
transaction usually gets wrong already in it:

**A minimum output, computed from a live quote and a stated tolerance.** `amountOutMin` is
what stands between a swap and a sandwich, and a plan without one would be worse than no
plan at all because it would look complete.

**An exact-amount approval, never unlimited.** An unlimited allowance is the single most
common way tokens leave a wallet long after the trade that granted it. If the existing
allowance already covers the swap, no approval step is emitted; the allowance is READ, and
if it cannot be read the plan refuses rather than assuming either way.

Every input is read from the chain and pinned to a block. A read that fails makes the plan
NOT_BUILDABLE with the reason stated — never a default gas price, never a zero nonce.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from connectors.chain import ChainAccessError, ChainClient
from lib.http_retry import TransientRetrievalError
from lib.thesis import PERMITTED

#: The transaction was fully computed. Nothing was signed and nothing was sent.
UNSIGNED = "UNSIGNED"
#: Something required could not be read. NOT a plan with defaults in the gaps.
NOT_BUILDABLE = "NOT_BUILDABLE"
#: A condition said no — no permission, an unusable tolerance, an unquotable route.
REFUSED = "REFUSED"

UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"

SELECTORS = {
    "approve": "0x095ea7b3",              # approve(address,uint256)
    "allowance": "0xdd62ed3e",            # allowance(address,address)
    "getAmountsOut": "0xd06ca61f",        # getAmountsOut(uint256,address[])
    "swapExactTokensForTokens": "0x38ed1739",
}

#: Generous, stated, and used only as a ceiling the wallet will lower when it simulates.
APPROVE_GAS = 60_000
SWAP_GAS = 220_000

#: Above this a "tolerance" is not protection, it is a blank cheque to a sandwicher.
MAX_SLIPPAGE_BPS = 500


class SigningRefused(RuntimeError):
    """Raised by anything that would put a key near this transaction."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _pad(address: str) -> str:
    return address.lower().removeprefix("0x").rjust(64, "0")


def _uint(value: int) -> str:
    return hex(int(value))[2:].rjust(64, "0")


def encode_approve(spender: str, amount: int) -> str:
    return SELECTORS["approve"] + _pad(spender) + _uint(amount)


def encode_amounts_out(amount_in: int, path: tuple[str, ...]) -> str:
    """`getAmountsOut(uint256,address[])`; the array is a tail at offset 0x40."""

    head = _uint(amount_in) + _uint(0x40)
    tail = _uint(len(path)) + "".join(_pad(step) for step in path)
    return SELECTORS["getAmountsOut"] + head + tail


def encode_swap(
    amount_in: int, amount_out_min: int, path: tuple[str, ...], to: str, deadline: int
) -> str:
    """`swapExactTokensForTokens`; five head words, so the array offset is 0xA0."""

    head = (_uint(amount_in) + _uint(amount_out_min) + _uint(0xA0)
            + _pad(to) + _uint(deadline))
    tail = _uint(len(path)) + "".join(_pad(step) for step in path)
    return SELECTORS["swapExactTokensForTokens"] + head + tail


def decode_amounts_out(raw: str) -> tuple[int, ...]:
    """The returned `uint256[]`: an offset word, a length word, then the elements."""

    body = str(raw or "").removeprefix("0x")
    if len(body) < 128:
        return ()
    words = [body[i:i + 64] for i in range(0, len(body), 64)]
    length = int(words[1], 16)
    if length <= 0 or len(words) < 2 + length:
        return ()
    return tuple(int(word, 16) for word in words[2:2 + length])


@dataclass(frozen=True, slots=True)
class UnsignedTransaction:
    """Every field a wallet needs, and no way to sign it here."""

    purpose: str
    chain_id: int
    from_address: str
    to: str
    data: str
    value: int
    gas_limit: int
    max_fee_per_gas: int
    max_priority_fee_per_gas: int
    nonce: int

    def sign(self, *_args: Any, **_kwargs: Any) -> None:
        raise SigningRefused(
            "this adapter does not sign. A chain transaction is atomic and irreversible, "
            "there is no order to cancel and no counterparty to ring, and the key that "
            "signs it controls everything else in the wallet. Export the fields and sign "
            "in a wallet you control."
        )

    #: Same refusal, so neither name is a way round the other.
    send = sign
    broadcast = sign

    def as_wallet_fields(self) -> dict[str, Any]:
        """Hex-encoded, in the shape a wallet's raw-transaction form expects."""

        return {
            "chainId": hex(self.chain_id),
            "from": self.from_address,
            "to": self.to,
            "data": self.data,
            "value": hex(self.value),
            "gas": hex(self.gas_limit),
            "maxFeePerGas": hex(self.max_fee_per_gas),
            "maxPriorityFeePerGas": hex(self.max_priority_fee_per_gas),
            "nonce": hex(self.nonce),
        }

    def describe(self) -> str:
        fee = self.gas_limit * self.max_fee_per_gas / 10**18
        return "\n".join([
            f"  {self.purpose}",
            f"    to     {self.to}",
            f"    nonce  {self.nonce}   gas {self.gas_limit:,} @ "
            f"{self.max_fee_per_gas / 10**9:.2f} gwei max  (up to {fee:.5f} ETH)",
            f"    data   {self.data[:74]}{'…' if len(self.data) > 74 else ''}",
        ])


@dataclass(frozen=True, slots=True)
class SwapPlan:
    """What to sign, in order, or precisely why there is nothing to sign."""

    status: str
    token_in: str
    token_out: str
    amount_in: int = 0
    quoted_out: int = 0
    min_out: int = 0
    slippage_bps: int = 0
    block_number: int = 0
    deadline: int = 0
    steps: tuple[UnsignedTransaction, ...] = ()
    existing_allowance: int = -1
    reason: str = ""
    at: str = ""

    @property
    def tolerated_loss(self) -> int:
        return self.quoted_out - self.min_out

    def sign(self, *_args: Any, **_kwargs: Any) -> None:
        raise SigningRefused(
            "this adapter does not sign. Sign the steps in a wallet you control."
        )

    send = sign

    def describe(self) -> str:
        if self.status == NOT_BUILDABLE:
            return (f"NOT_BUILDABLE  {self.token_in} -> {self.token_out}\n  {self.reason}\n"
                    f"  Nothing was computed. This is not a finding that the swap is "
                    f"unavailable or that it would be cheap.")
        if self.status == REFUSED:
            return f"REFUSED  {self.token_in} -> {self.token_out}\n  {self.reason}"

        lines = [
            f"UNSIGNED SWAP  {self.token_in} -> {self.token_out}   block "
            f"{self.block_number}",
            f"  in       {self.amount_in:,} units",
            f"  quoted   {self.quoted_out:,} units out",
            f"  FLOOR    {self.min_out:,} units — the swap reverts below this. "
            f"{self.slippage_bps} bps tolerated, {self.tolerated_loss:,} units at risk.",
            f"  deadline {self.deadline} (unix); after it the swap reverts rather than "
            f"executing at whatever the price became.",
            "",
            f"{len(self.steps)} transaction(s) TO SIGN YOURSELF, in this order:",
        ]
        lines += [step.describe() for step in self.steps]
        if self.existing_allowance >= 0:
            lines.append(
                f"\n  allowance already granted to the router: "
                f"{self.existing_allowance:,} units"
                + (" — sufficient, so no approval step is included."
                   if self.existing_allowance >= self.amount_in else
                   " — short, so an EXACT-AMOUNT approval is included. Never unlimited: "
                   "an unlimited allowance is how tokens leave a wallet months after the "
                   "trade that granted it.")
            )
        lines += [
            "",
            "NOTHING HAS BEEN SIGNED AND NOTHING HAS BEEN SENT. This adapter has no key "
            "path and no send method; a chain transaction is atomic and irreversible, and "
            "the key that signs it controls the rest of the wallet.",
            "BEFORE YOU SIGN, CHECK BY EYE",
            "  - the token addresses are the ones you meant, character for character",
            "  - the recipient is your own address",
            "  - your wallet's simulation agrees with the quoted output above",
        ]
        return "\n".join(lines)


def build_swap_plan(
    client: ChainClient,
    *,
    wallet: str,
    token_in: str,
    token_out: str,
    amount_in: int,
    permission: Any = None,
    slippage_bps: int = 50,
    deadline_seconds: int = 600,
    router: str = UNISWAP_V2_ROUTER,
    now: Callable[[], int] | None = None,
) -> SwapPlan:
    """Read everything, compute the floor, emit the steps. Sign nothing.

    Ordered so the cheap refusals come first and no chain call is made for a swap that was
    never going to be permitted.
    """

    common = {"token_in": token_in, "token_out": token_out, "amount_in": amount_in,
              "slippage_bps": slippage_bps, "at": _now()}

    if permission is not None and getattr(permission, "status", "") != PERMITTED:
        return SwapPlan(REFUSED, reason=(
            f"permission is {getattr(permission, 'status', 'absent')}, not {PERMITTED}. "
            f"An unsigned transaction is still a transaction somebody may sign."), **common)
    if amount_in <= 0:
        return SwapPlan(REFUSED, reason="amount_in must be positive", **common)
    if not 0 < slippage_bps <= MAX_SLIPPAGE_BPS:
        return SwapPlan(REFUSED, reason=(
            f"slippage tolerance must be between 1 and {MAX_SLIPPAGE_BPS} bps. Zero leaves "
            f"no room for the block to move and anything wider is not protection, it is a "
            f"blank cheque to whoever is watching the mempool."), **common)
    if token_in.lower() == token_out.lower():
        return SwapPlan(REFUSED, reason="a token cannot be swapped for itself", **common)

    path = (token_in, token_out)

    try:
        quote = client.read("eth_call", [
            {"to": router, "data": encode_amounts_out(amount_in, path)}])
    except (ChainAccessError, TransientRetrievalError) as error:
        return SwapPlan(NOT_BUILDABLE, reason=(
            f"the router did not quote the swap: {error}"), **common)

    amounts = decode_amounts_out(quote.value)
    if len(amounts) < 2 or amounts[-1] <= 0:
        return SwapPlan(NOT_BUILDABLE, block_number=quote.block_number, reason=(
            "the router returned no output amount for this path. This is a statement "
            "about this route at this block, not about whether the token trades."),
            **common)

    quoted_out = amounts[-1]
    # Floored, so rounding never lands on the permissive side of the tolerance.
    min_out = quoted_out * (10_000 - slippage_bps) // 10_000
    if min_out <= 0:
        return SwapPlan(NOT_BUILDABLE, block_number=quote.block_number, reason=(
            "the computed floor rounds to zero, so the swap would have no protection at "
            "all. The size is too small for the tolerance to mean anything."), **common)

    try:
        allowance_read = client.read("eth_call", [{
            "to": token_in,
            "data": SELECTORS["allowance"] + _pad(wallet) + _pad(router),
        }])
        allowance = int(str(allowance_read.value or "0x0"), 16)
    except (ChainAccessError, TransientRetrievalError, ValueError) as error:
        # Assuming either way is unsafe in a different direction: assume none and the
        # plan wastes an approval; assume enough and the swap reverts after the approval
        # step was skipped. So neither.
        return SwapPlan(NOT_BUILDABLE, block_number=quote.block_number, reason=(
            f"the current allowance could not be read: {error}. Not a finding that it is "
            f"zero, and not a finding that it is sufficient."), **common)

    try:
        chain_id = int(str(client.call("eth_chainId")), 16)
        nonce = int(str(client.call("eth_getTransactionCount", [wallet, "pending"])), 16)
        gas_price = int(str(client.call("eth_gasPrice")), 16)
    except (ChainAccessError, TransientRetrievalError, TypeError, ValueError) as error:
        return SwapPlan(NOT_BUILDABLE, block_number=quote.block_number, reason=(
            f"chain id, nonce or gas price could not be read: {error}. A transaction built "
            f"with a default in any of those three is a transaction that fails or replaces "
            f"one you did not mean to replace."), **common)

    if gas_price <= 0:
        return SwapPlan(NOT_BUILDABLE, block_number=quote.block_number, reason=(
            "the node reported a gas price of zero, which is a measurement failure rather "
            "than a free block."), **common)

    seconds = now() if now is not None else int(datetime.now(timezone.utc).timestamp())
    deadline = seconds + deadline_seconds

    # Doubled as a ceiling: EIP-1559 refunds the difference, and a max fee that the base
    # fee outruns between building and signing produces a transaction that never mines.
    max_fee = gas_price * 2
    priority = min(gas_price, 2 * 10**9)

    steps: list[UnsignedTransaction] = []
    if allowance < amount_in:
        steps.append(UnsignedTransaction(
            purpose=f"1. APPROVE exactly {amount_in:,} units to the router",
            chain_id=chain_id, from_address=wallet, to=token_in,
            data=encode_approve(router, amount_in), value=0,
            gas_limit=APPROVE_GAS, max_fee_per_gas=max_fee,
            max_priority_fee_per_gas=priority, nonce=nonce,
        ))

    steps.append(UnsignedTransaction(
        purpose=(f"{len(steps) + 1}. SWAP {amount_in:,} units, reverting below "
                 f"{min_out:,} out"),
        chain_id=chain_id, from_address=wallet, to=router,
        data=encode_swap(amount_in, min_out, path, wallet, deadline), value=0,
        gas_limit=SWAP_GAS, max_fee_per_gas=max_fee,
        max_priority_fee_per_gas=priority, nonce=nonce + len(steps),
    ))

    return SwapPlan(
        UNSIGNED, quoted_out=quoted_out, min_out=min_out,
        block_number=quote.block_number, deadline=deadline, steps=tuple(steps),
        existing_allowance=allowance, **common,
    )
