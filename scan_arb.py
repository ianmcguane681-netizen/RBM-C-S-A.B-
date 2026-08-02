"""Pull odds from every configured book and find combinations that imply under 100%.

    python scan_arb.py                       list the sports currently in season
    python scan_arb.py soccer_epl            scan one sport via the aggregator
    python scan_arb.py --market 1.234567     scan named exchange markets directly
    python scan_arb.py soccer_epl --json     machine-readable, for a scheduler

**Aggregator and exchange results are NOT merged, and that is a known gap rather than an
oversight.** An aggregator names a market by its teams and time; Betfair names it
`1.234567`. Matching one to the other needs fuzzy name resolution across sources, and a
wrong match is worse than no match: it would pair a price from one fixture with a price
from another and compute a margin across two different events. Until that is solved with
its own gate, the two paths run separately and each says which books it covered.

Discovery only. Every result is an `ArbCandidate` and never a position, because two
preconditions are unmet by construction and no feed can meet them:

    available stake     an odds feed returns odds, not liquidity
    settlement rules    an aggregator does not carry each book's terms

Both are confirmed at the book, by a person, and only then does `check_arb.py` have
something it can verify. The only real position this board has examined had a positive
margin net of commission and was refused because one leg voided on abandonment while the
other stood — the gate that caught it reads prose no feed returns.

Exit codes:

    0   scanned, and nothing implied under 100%
    1   at least one candidate found
    2   no source is configured, so nothing was scanned

Setup, on a machine you control:

    mkdir -p ~/.oddsapi && chmod 700 ~/.oddsapi
    printf '%s' 'your-key' > ~/.oddsapi/key && chmod 600 ~/.oddsapi/key
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from connectors.oddsapi import H2H, OddsApiSource
from lib.arbfind import ARB_CANDIDATE, quotes_from_legs, scan_markets
from lib.seen import SeenRegister, arb_identity
from lib.store import LOST

REGISTER = Path("data/seen-register.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def exchange_quotes(markets: Sequence[str]) -> tuple[tuple, list[str]]:
    """Every configured exchange, for the markets named. Silence is reported, not skipped.

    Exchanges are worth more than a wider feed for one reason: they return the size
    available at the price. A candidate whose legs all came from exchanges has one fewer
    unread precondition, and `unmet_preconditions` computes that per quote rather than
    assuming the weakest source.
    """

    from connectors.betfair import BetfairSource
    from connectors.smarkets import SmarketsSource

    collected: list = []
    silent: list[str] = []
    for build in (BetfairSource.from_directory, SmarketsSource.from_directory):
        try:
            source = build()
        except Exception as error:  # noqa: BLE001 - a bad directory is not a crash
            silent.append(f"{build.__qualname__.split('.')[0]}: {error}"[:100])
            continue
        for market in markets:
            try:
                answer = source.quote(market)
            except Exception as error:  # noqa: BLE001
                silent.append(f"{source.name} on {market}: {error}"[:100])
                continue
            if answer.status != "CONFIGURED":
                silent.append(f"{source.name}: {answer.reason or answer.status}"[:100])
                break
            collected.extend(quotes_from_legs(answer.legs))
    return tuple(collected), silent


def scan_exchanges(market_ids: Sequence[str]) -> int:
    """Exchanges only, for markets named by their own identifiers.

    Worth running on its own even though exchange-versus-exchange arbs are rare: these are
    the only sources that return the size at the price AND the rules text, so a candidate
    found here has both preconditions readable rather than one.
    """

    quotes, silent = exchange_quotes(market_ids)
    for note in silent:
        print(f"  NOT COVERED  {note}")
    if not quotes:
        print("\nNo exchange answered. NOTHING was scanned, which is not a finding that "
              "no arb exists.")
        return 2

    markets: dict[str, set] = {}
    for quote in quotes:
        markets.setdefault(quote.market, set()).add(quote.selection)
    result = scan_markets({m: tuple(sorted(s)) for m, s in markets.items()}, quotes)
    print(result.describe())
    return 1 if result.arbs else 0


def main(sport: str, *, as_json: bool) -> int:
    source = OddsApiSource.from_directory()
    if not source.is_configured:
        print(source.quote("any").describe())
        print("\nNo source is configured, so NOTHING was scanned. This is not a finding "
              "that no arb exists.")
        return 2

    if not sport:
        available = source.sports()
        print(f"{len(available)} sport(s) in season. Quota: {source.usage.describe()}\n")
        for key in available:
            print(f"  {key}")
        print("\nPick one and run: python scan_arb.py <sport>")
        return 0

    quotes = source.quotes(sport, market=H2H)
    if not quotes:
        print(f"{sport}: the feed answered and returned no prices. Quota: "
              f"{source.usage.describe()}")
        return 0

    # Outcome set per market taken from the union of what the books quoted. Weaker than
    # taking it from the sport, and the limitation is stated rather than hidden: if NO book
    # quoted the draw, that market reads two-way and would be evaluated as complete.
    markets: dict[str, tuple[str, ...]] = {}
    for quote in quotes:
        markets.setdefault(quote.market, set()).add(quote.selection)  # type: ignore[arg-type]
    markets = {m: tuple(sorted(s)) for m, s in markets.items()}  # type: ignore[union-attr]

    result = scan_markets(markets, quotes)

    register = SeenRegister.load(REGISTER)
    if register.status.state == LOST:
        print(register.status.describe())
        print()

    fresh = []
    for candidate in result.arbs:
        identity = arb_identity(
            candidate.market, [(q.book, q.selection) for q in candidate.quotes]
        )
        verdict = register.check(identity)
        fresh.append((candidate, verdict))
        if register.readable:
            register.record(identity, _now())
    if register.readable:
        register.save()

    if as_json:
        print(json.dumps({
            "sport": sport,
            "quota_remaining": source.usage.remaining,
            "books": list(result.books_seen),
            "markets_examined": result.markets_examined,
            "incomplete_markets": len(result.incomplete),
            "candidates": [
                {
                    "market": c.market,
                    "implied_pct": round(c.total_implied_pct, 4),
                    "margin_pct": round(c.margin_pct, 4),
                    "seen": v.status,
                    "legs": [
                        {"book": q.book, "selection": q.selection,
                         "decimal_odds": q.decimal_odds, "observed_at": q.observed_at}
                        for q in c.quotes
                    ],
                    "unmet_preconditions": list(c.unmet_preconditions),
                }
                for c, v in fresh
            ],
        }, indent=2))
    else:
        print(result.describe())
        print(f"\nQuota: {source.usage.describe()}")
        for candidate, verdict in fresh:
            if verdict.status != "NEW":
                print(f"  {candidate.market}: {verdict.describe()}")

    return 1 if result.arbs else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        raise SystemExit(0)
    if "--market" in argv:
        ids = argv[argv.index("--market") + 1:]
        raise SystemExit(scan_exchanges([i for i in ids if not i.startswith("--")]))
    args = [a for a in argv if not a.startswith("--")]
    raise SystemExit(main(args[0] if args else "", as_json="--json" in argv))
