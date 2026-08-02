"""Watch what a review established, and say when it stops being true.

    python monitor.py watchlist.json

A review is a snapshot. This is the part that runs afterwards, on a schedule, and needs no
view of the future at all -- only a memory of the last observation. It answers one question:
*has anything the board relied on moved?*

What it never does is decide anything. A changed implementation address does not mean sell;
it means every fact established about that contract was established about different code,
and whatever you concluded rests on nothing until the review is re-run.

Two facts are watched per lane, chosen because they are the ones that invalidate prior work:

    crypto   the proxy implementation, the admin, owner, minter and pause switch, supply
    stocks   any reporting span refiled at a new value, and any change of XBRL tag

Both are read from the primary source. Neither needs a price feed, and nothing here is a
forecast.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.ledger import Ledger, Observation, summarise

LEDGER = Path("data/monitor-ledger.json")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def watch_token(address: str, stamp: str) -> list[Observation]:
    """CG-01 and CG-04 facts: who controls it, and how much of it there is."""

    from connectors.chain import ChainAccessError, ChainClient, best_for
    from connectors.chain_queries import authority_holders, is_paused, proxy_finding, total_supply
    from lib.http_retry import TransientRetrievalError

    subject = f"ethereum:{address}"
    client = ChainClient(best_for("state"))

    def unreadable(fact: str, why: str) -> Observation:
        return Observation(subject, fact, why[:120], stamp, "ethereum", readable=False)

    facts = ["proxy_status", "implementation", "admin", "owner", "masterMinter",
             "paused", "totalSupply"]
    try:
        block = int(client.read("eth_getBlockByNumber", ["finalized", False]).value["number"], 16)
    except (TransientRetrievalError, ChainAccessError) as error:
        # One failure, one reason, on every fact. Silently returning nothing would let the
        # run look complete.
        return [unreadable(f, f"node unreachable: {error}") for f in facts]

    at = {"block_number": block}
    source = f"ethereum@{block}"
    out: list[Observation] = []
    try:
        proxy = proxy_finding(client, address, **at)
        out.append(Observation(subject, "proxy_status", proxy.status, stamp, source))
        out.append(Observation(subject, "implementation", proxy.implementation or "", stamp, source))
        out.append(Observation(subject, "admin", proxy.admin or "", stamp, source))
    except (TransientRetrievalError, ChainAccessError) as error:
        out += [unreadable(f, str(error)) for f in ("proxy_status", "implementation", "admin")]

    try:
        holders = authority_holders(client, address, **at)
        for role in ("owner", "masterMinter"):
            out.append(Observation(subject, role, str(holders.get(role, "")), stamp, source))
    except (TransientRetrievalError, ChainAccessError) as error:
        out += [unreadable(f, str(error)) for f in ("owner", "masterMinter")]

    try:
        out.append(Observation(subject, "paused", is_paused(client, address, **at), stamp, source))
    except (TransientRetrievalError, ChainAccessError) as error:
        out.append(unreadable("paused", str(error)))

    try:
        supply = int(str(total_supply(client, address, **at).value), 16)
        out.append(Observation(subject, "totalSupply", str(supply), stamp, source))
    except (TransientRetrievalError, ChainAccessError) as error:
        out.append(unreadable("totalSupply", str(error)))
    return out


def watch_filer(ticker: str, stamp: str) -> list[Observation]:
    """SG-02 facts: a period refiled at a new value, and a change of tag."""

    from connectors.edgar import INDETERMINATE, NOT_REPORTED, REPORTED, EdgarClient
    from check_stock import CONCEPTS

    client = EdgarClient()
    subject = f"edgar:{ticker.upper()}"
    out: list[Observation] = []
    try:
        cik = client.cik_for_ticker(ticker)
    except Exception as error:
        return [Observation(subject, "cik", str(error)[:120], stamp, "edgar", readable=False)]

    for label, tags in CONCEPTS.items():
        series = client.first_reported(cik, tags)
        if series.status == INDETERMINATE:
            out.append(Observation(subject, label, series.reason[:120], stamp, "edgar", readable=False))
            continue
        if series.status == NOT_REPORTED:
            out.append(Observation(subject, label, "", stamp, "edgar"))
            continue
        latest = series.latest_annual()
        # The value AND the span it covers. A figure that stayed the same while the latest
        # annual period moved on is not the same fact.
        value = f"{latest.value:.0f}@{latest.duration}" if latest else ""
        out.append(Observation(subject, label, value, stamp, f"edgar:{series.concept}"))
        # The tag itself is watched: a filer switching tags is how a series silently
        # becomes stale, which happened to NVIDIA and to Modine.
        out.append(Observation(subject, f"{label}:tag", series.concept, stamp, "edgar"))
        out.append(Observation(
            subject, f"{label}:restatements", str(len(series.revised_durations())), stamp, "edgar"
        ))
    return out


def main(path: str) -> int:
    watchlist = json.loads(Path(path).read_text(encoding="utf-8"))
    stamp = now()
    observations: list[Observation] = []

    tokens = watchlist.get("tokens", [])
    if tokens and not os.environ.get("QUICKNODE_ETHEREUM_URL"):
        print("WARNING: QUICKNODE_ETHEREUM_URL is not set; chain facts will read as "
              "unreadable rather than unchanged.\n")
    for address in tokens:
        observations += watch_token(address, stamp)
    for ticker in watchlist.get("tickers", []):
        observations += watch_filer(ticker, stamp)

    ledger = Ledger(LEDGER)
    known = len(ledger)
    changes = ledger.compare(observations)
    ledger.record(observations)
    ledger.save()

    print(f"Monitor run {stamp}")
    print(f"  {len(observations)} fact(s) observed across {len(tokens)} token(s) and "
          f"{len(watchlist.get('tickers', []))} filer(s)")
    print(f"  ledger held {known} fact(s) before this run, {len(ledger)} after\n")
    print(summarise(changes))

    # Exit 4 on a material change so a scheduler can act on it without parsing text.
    return 4 if any(c.is_material for c in changes) else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print('Watchlist:\n{\n  "tokens": ["0xA0b8..."],\n  "tickers": ["NET", "MOD"]\n}')
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
