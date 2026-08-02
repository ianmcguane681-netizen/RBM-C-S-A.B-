"""Both panels and one decision: what the board found, what the trade costs, and yours.

    python trade_sheet.py examples/crypto-board/decision-0002 \
        0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 100000 --target 1.10

Three panels, deliberately separated because they come from three different places and
carry three different weights:

    BOARD    what was established about the asset, and whether any action is permitted.
             Comes from a published decision record somebody signed.

    COST     what a round trip costs at your size, measured at a block height.
             Comes from the pools, right now. No forecast.

    YOURS    arithmetic on a target price YOU supplied. The system has no view on whether
             the price gets there and never pretends to.

The separation is the point. A green board verdict beside an entry price reads as though
the board endorsed the trade. It did not and cannot: it checked whether a contract is what
it claims, which is hygiene, not an edge. Keeping the panels apart is what stops one
lending its credibility to the other.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from connectors.chain import ChainClient, best_for
from connectors.chain_costs import PRICED, round_trip
from rbe_runtime.mandate import PERMITTED, ProposedAction, evaluate


def board_panel(bundle: Path, subject: str, now: str) -> str:
    package = json.loads((bundle / "decision.json").read_text(encoding="utf-8"))
    session = json.loads((bundle / "session.json").read_text(encoding="utf-8"))
    reports_doc = json.loads((bundle / "reports.json").read_text(encoding="utf-8"))
    findings_doc = json.loads((bundle / "findings.json").read_text(encoding="utf-8"))

    reports = reports_doc.get("reports", []) if isinstance(reports_doc, dict) else reports_doc
    findings = findings_doc.get("findings", []) if isinstance(findings_doc, dict) else findings_doc

    finding = evaluate(
        package, ProposedAction(subject), now=now,
        session=session, reports=reports if isinstance(reports, list) else [],
    )

    lines = ["BOARD", finding.describe(), ""]
    blocking = [f for f in findings if str(f.get("severity", "")) in {"SEV-1", "SEV-2"}]
    if blocking:
        lines.append(f"  {len(blocking)} blocking finding(s):")
        for item in blocking:
            raw = item.get("raw_record") or item
            lines.append(f"    {item.get('severity','')}  {raw.get('title', item.get('finding_id',''))}")
    return "\n".join(lines)


def cost_panel(token: str, stake_units: int, quote_name: str) -> tuple[str, object]:
    client = ChainClient(best_for("state"))
    trip = round_trip(client, token, stake_units, quote_name=quote_name)
    return "COST\n" + trip.describe(), trip


def your_panel(trip, target: float | None, decimals: int) -> str:
    if target is None:
        return (
            "YOURS\n  No target supplied, so no profit figure is shown. This system does "
            "not produce one: a projected return printed beside measured costs borrows "
            "their credibility and has none of its own.\n"
            "  Pass --target 1.10 to see the arithmetic on YOUR view of a 10% rise."
        )
    if getattr(trip, "status", "") != PRICED:
        return "YOURS\n  The round trip could not be priced, so there is nothing to compute against."
    net = trip.net_at_target(target)
    verdict = "clears" if trip.clears_costs(target) else "does NOT clear"
    return "\n".join([
        "YOURS",
        f"  Your target: a {(target - 1) * 100:+.2f}% move. This is your view and the "
        f"system has no opinion on it.",
        f"  Breakeven needs {trip.breakeven_move_pct:.2f}%, so your target {verdict} costs.",
        f"  Net at your target: {net / 10**decimals:,.2f} {trip.quote_name} on a stake of "
        f"{trip.spent / 10**decimals:,.2f}",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Exported decision directory")
    parser.add_argument("token", help="Token address to price")
    parser.add_argument("stake", type=float, help="Stake in whole quote-asset units")
    parser.add_argument("--quote", default="USDC")
    parser.add_argument("--quote-decimals", type=int, default=6)
    parser.add_argument("--target", type=float, default=None,
                        help="YOUR target as a multiple, e.g. 1.10 for a 10%% rise")
    parser.add_argument("--now", default="")
    args = parser.parse_args()

    if not os.environ.get("QUICKNODE_ETHEREUM_URL"):
        print("WARNING: QUICKNODE_ETHEREUM_URL is not set; quotes may be unreliable.\n")

    bundle = Path(args.bundle)
    session = json.loads((bundle / "session.json").read_text(encoding="utf-8"))
    subject = (session.get("initiation") or {}).get("repository", "")
    now = args.now or json.loads(
        (bundle / "decision.json").read_text(encoding="utf-8")
    )["publication"]["indicator"]["published_at"]

    print(board_panel(bundle, subject, now))
    print()
    costs, trip = cost_panel(args.token, int(args.stake * 10**args.quote_decimals), args.quote)
    print(costs)
    print()
    print(your_panel(trip, args.target, args.quote_decimals))
    print()
    print("=" * 72)
    print("ACCEPT or DECLINE is yours. The board says whether action is permitted; the")
    print("cost panel says what it would cost; neither says whether it is a good idea.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
