"""Run all six crypto gates against one token and print what they establish.

    python check_token.py 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

This is the fast path. It produces no decision record, no signatures and no audit chain --
just the facts, pinned to a finalized block, each reproducible by anyone who repeats the
query at that height. Use it to decide whether a token is worth a full review.

The full path is `board open` ... `board decide`, which produces a record somebody else
can check. Use that when the answer needs to survive you.

Needs QUICKNODE_ETHEREUM_URL set. Without an archive-capable provider the historical reads
degrade, and the tool says so rather than quietly returning less.
"""
from __future__ import annotations

import os
import sys

from connectors.chain import ChainClient, best_for
from connectors.chain_clustering import address_distinctness
from connectors.chain_liquidity import QUOTE_TOKENS, exit_cost
from connectors.chain_locks import lock_finding
from connectors.chain_queries import (
    authority_holders,
    is_paused,
    proxy_finding,
    token_identity,
    total_supply,
)

SIZES_IN_TOKENS = (10_000, 1_000_000, 100_000_000)


def main(token: str, log_window: int = 60) -> int:
    if not os.environ.get("QUICKNODE_ETHEREUM_URL"):
        print("WARNING: QUICKNODE_ETHEREUM_URL is not set. Historical reads will be "
              "unreliable and CG-06 cannot be trusted.\n")

    state = ChainClient(best_for("state"))
    block = int(state.read("eth_getBlockByNumber", ["finalized", False]).value["number"], 16)
    at = {"block_number": block}
    print(f"{token} on {state.provider.chain} at finalized block {block:,}")
    print(f"provider {state.provider.name} (archive: {state.provider.archive})\n")

    identity = token_identity(state, token, **at)
    decimals = int(str(identity["decimals"].value), 16)
    supply = int(str(total_supply(state, token, **at).value), 16)

    def text(field: str) -> str:
        """ABI-encoded strings carry length prefixes and null padding. Stripping only
        nulls left the length byte in, so DAI rendered with thirty spaces in front of it."""

        raw = bytes.fromhex(str(identity[field].value)[2:])
        return "".join(chr(b) for b in raw if 32 <= b < 127).strip()

    print("CG-01  identity and supply")
    print(f"   {text('symbol')} ({text('name')}), decimals {decimals} read from the contract")
    print(f"   supply {supply / 10**decimals:,.2f}\n")

    print("CG-04  who controls it")
    proxy = proxy_finding(state, token, **at)
    print(f"   {proxy.describe()}")
    print(f"   authority: {authority_holders(state, token, **at)}")
    print(f"   paused:    {is_paused(state, token, **at)}  "
          f"(false means the switch exists and is off, not that there is none)\n")

    print("CG-03  locks")
    print(f"   {lock_finding(state, token, **at).describe()}\n")

    print("CG-05  what it costs to leave")
    sizes = tuple(n * 10**decimals for n in SIZES_IN_TOKENS)
    quotes = {n: a for n, a in QUOTE_TOKENS.items() if a.lower() != token.lower()}
    print(f"   {exit_cost(state, token, sizes, quotes=quotes, **at).describe()}\n")

    print(f"CG-02  are the addresses distinct  (last {log_window} blocks)")
    logs = ChainClient(best_for("logs"))
    print(f"   {address_distinctness(logs, token, block - log_window + 1, block).describe()}\n")

    print("Every figure above is pinned to a block and reproducible. None of it says "
          "whether to buy.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
