"""Check a claimed arb from prices you are looking at, with no API and no account.

    python check_arb.py examples/arb/match-odds.json

Every field is one you can read off two screens: the price, the size it is offered at, the
commission, and -- the one that decides it -- each operator's settlement rule, copied
verbatim from their rules page.

That last field is the point of this tool. The arithmetic of arbitrage is a line of code
and every arb calculator on the internet gets it right. What they leave out is whether the
two legs settle the same way, and that is what turns a locked position into a coin flip.
Copy the rules text exactly; do not summarise it, because summarising is where two
different rules become one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from lib.arb import LOCK, Leg, evaluate

TEMPLATE = {
    "market": "Match Odds: Team A v Team B",
    "target_stake": 0,
    "legs": [
        {
            "book": "Betfair Exchange",
            "selection": "Team A",
            "odds": 2.16,
            "max_stake": 5000,
            "commission_pct": 2.0,
            "observed_at": "2026-08-02T12:00:00Z",
            "settlement_rule": "PASTE THE OPERATOR'S RULES TEXT HERE, VERBATIM",
        },
        {
            "book": "Some Bookmaker",
            "selection": "Team B",
            "odds": 2.10,
            "max_stake": 250,
            "commission_pct": 0.0,
            "observed_at": "2026-08-02T12:00:30Z",
            "settlement_rule": "PASTE THE OTHER OPERATOR'S RULES TEXT HERE, VERBATIM",
        },
    ],
}


def load(path: Path) -> tuple[list[Leg], float, str]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    market = str(spec.get("market") or "unnamed market")
    legs = [
        Leg(
            book=str(item["book"]),
            market=market,
            selection=str(item["selection"]),
            decimal_odds=float(item["odds"]),
            settlement_rule=str(item["settlement_rule"]),
            max_stake=float(item["max_stake"]),
            observed_at=str(item.get("observed_at") or ""),
            commission_pct=float(item.get("commission_pct") or 0.0),
        )
        for item in spec["legs"]
    ]
    return legs, float(spec.get("target_stake") or 0.0), market


def observation_gap(legs: list[Leg]) -> str:
    """How far apart the two prices were seen.

    Reported because a cross-venue arb always has one: only a single venue's own feed can
    give two prices at the same instant, and everything else is polled. An arb assembled
    from prices read a minute apart existed at neither of them.
    """

    stamps = sorted({leg.observed_at for leg in legs if leg.observed_at})
    if len(stamps) < 2:
        return "  Observation times were not all recorded, so the gap between the two prices is unknown."
    return (
        f"  Prices were observed between {stamps[0]} and {stamps[-1]}. A cross-venue arb "
        f"is never a single instant; the wider that gap, the less this describes a "
        f"position that existed."
    )


def main(path: str) -> int:
    legs, target, market = load(Path(path))
    finding = evaluate(legs, target_stake=target)

    print(f"{market}\n")
    print(finding.describe())
    print()
    print(observation_gap(legs))

    if finding.status == LOCK:
        print()
        print("  This is a lock at the prices and sizes entered. It is not advice to place")
        print("  it: the void exposure above is real money, and whether that trade is worth")
        print("  making is your judgement and not this tool's.")
    return 0 if finding.status == LOCK else 3


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("Template:\n")
        print(json.dumps(TEMPLATE, indent=2))
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
