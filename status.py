"""Every lane, in one place, in the same units — the data layer any UI reads.

    python status.py
    python status.py --json     the same state, for a front end to render

A dashboard that tiles five different views is five dashboards on one page. What makes
several revenue lines one system is not a shared screen but a **shared unit of account**:
every lane answers the same three questions, in the same currency, with the same word for
"not known".

    how much capital is in this lane
    what is it worth now, or is it UNPRICED
    what is outstanding — obligations, unread evidence, unratified decisions

That is the whole report and it needs no forecast. Nothing here predicts a price, a sale, or
a return. It states what was put in, what can currently be marked, and what is owed.

**What it refuses to do.** No total that mixes priced and unpriced holdings. No percentage of
a portfolio whose denominator excludes what could not be valued without saying so. No
lane-level health figure, because a single number over five heterogeneous lanes is the
scoring model argued against at length in `lib/candidates.py`, wearing a friendlier name.

An operating lane resting at UNPRICED is normal, not broken: inventory bought for resale and
hours sunk into something being built have a cost and no mark until something sells. The
report says so rather than showing them as worthless or leaving them out silently.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from lib.portfolio import LANES, Portfolio
from lib.preflight import BLOCKED, DEGRADED, all_lanes
from lib.store import LOST

def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


BOOK = Path("data/portfolio.json")
LEDGER = Path("data/monitor-ledger.json")
REGISTER = Path("data/seen-register.json")


def capital_panel() -> list[str]:
    """What is deployed, per lane, and what could not be marked."""

    book = Portfolio(BOOK)
    lines = ["CAPITAL"]

    if book.status.state == LOST:
        lines.append(f"  {book.status.describe()}")
        lines.append("")
        return lines
    if not len(book):
        lines.append("  No entries recorded. This is an empty book, not a zero balance:")
        lines.append("  nothing has been entered, so nothing is known about what is held.")
        lines.append("")
        return lines

    positions = book.positions()
    # No price source is wired for any lane yet, so every holding marks UNPRICED. That is
    # the honest state and it is stated rather than shown as zero.
    valuations = [p.value_at(None) for p in positions]
    exposure = book.exposure(valuations)

    by_lane: dict[str, float] = {}
    for position in positions:
        by_lane[position.lane] = by_lane.get(position.lane, 0.0) + position.cost_basis

    for lane in LANES:
        cost = by_lane.get(lane, 0.0)
        if not cost:
            continue
        held = [p.asset for p in positions if p.lane == lane]
        lines.append(f"  {lane:<10} {cost:>12,.2f} at cost   {', '.join(held)}")

    lines.append("")
    lines.append(f"  {exposure.describe()}")
    lines.append("")
    return lines


def obligations_panel() -> list[str]:
    """What the monitor's last run compels, and whether its memory survived."""

    from lib.ledger import Ledger

    lines = ["OBLIGATIONS"]
    ledger = Ledger(LEDGER)

    if ledger.status.state == LOST:
        lines.append(f"  {ledger.status.describe()}")
        lines.append("")
        return lines
    if not len(ledger):
        lines.append("  The monitor has never run. No facts are being watched, which is")
        lines.append("  different from watching facts and finding nothing changed.")
        lines.append("")
        return lines

    lines.append(f"  {len(ledger)} fact(s) baselined. Obligations arise from CHANGES, and")
    lines.append("  a change is only visible on the run that observes it — run monitor.py")
    lines.append("  to compare, not this report.")
    lines.append("")
    return lines


def evidence_panel() -> list[str]:
    """Which lanes can currently read anything at all."""

    lines = ["EVIDENCE"]
    for lane in all_lanes():
        mark = {BLOCKED: "BLOCKED ", DEGRADED: "DEGRADED"}.get(lane.status, "READY   ")
        missing = ", ".join(r.name for r in lane.missing) or "nothing missing"
        lines.append(f"  {mark}  {lane.lane:<8} {missing}")
    lines.append("")
    lines.append("  A lane that can read its evidence has not thereby concluded anything.")
    lines.append("")
    return lines


def boards_panel() -> list[str]:
    """Reviews that exist, and where each one is stuck."""

    import sqlite3

    lines = ["BOARDS"]
    store = Path("data/review_board.sqlite3")
    if not store.is_file():
        lines.append("  No review store on disk. The container was reclaimed, or no review")
        lines.append("  has been convened here. These are not the same and this cannot tell")
        lines.append("  them apart — the store carries no receipt yet.")
        lines.append("")
        return lines

    try:
        rows = sqlite3.connect(f"file:{store}?mode=ro", uri=True).execute(
            "SELECT session_id, status FROM review_sessions ORDER BY session_id"
        ).fetchall()
    except sqlite3.Error as error:
        lines.append(f"  UNREADABLE: {error}. NOT a finding that no reviews exist.")
        lines.append("")
        return lines

    for session_id, status in rows:
        waiting = " — awaiting ratification" if status == "GOVERNANCE_VALIDATION" else ""
        lines.append(f"  {session_id:<22} {status}{waiting}")
    lines.append("")
    return lines


def as_json() -> dict:
    """The same state, for a front end.

    **Unpriced holdings emit `null`, never `0`.** A dashboard rendering `€0.00` for a
    holding nobody could price puts the defect back at the presentation layer, after the
    whole stack was built to avoid it. A front end that cannot handle a null should show
    the word UNPRICED, and one that cannot do that should not show the figure.

    Likewise a lane that is not configured emits its status, never an empty list of
    findings. Nought arbs found and nought sources configured are different facts.
    """

    from lib.orchestrator import Orchestrator
    from lib.portfolio import Portfolio
    from lib.preflight import all_lanes
    from run import LANES

    book = Portfolio(BOOK)
    positions = book.positions()
    valuations = [p.value_at(None) for p in positions]
    exposure = book.exposure(valuations)

    orchestrator = Orchestrator(LANES, Path("data/orchestrator.json"))
    lanes = all_lanes()

    boards = []
    store = Path("data/review_board.sqlite3")
    if store.is_file():
        try:
            boards = [
                {"review": r, "state": s}
                for r, s in sqlite3.connect(f"file:{store}?mode=ro", uri=True).execute(
                    "SELECT session_id, status FROM review_sessions ORDER BY session_id")
            ]
        except sqlite3.Error:
            boards = []

    return {
        "generated_at": _now(),
        "capital": {
            # None, not 0.0, in BOTH failure cases -- and the second was found by running
            # this. An empty book has no unpriced assets, so `is_complete` reads true and
            # the total emitted 0.0, which a front end renders as a known balance of zero.
            # The text panel already said "an empty book, not a zero balance"; the JSON
            # layer had quietly reintroduced the very defect this file argues against.
            "priced_value": (
                exposure.priced_value
                if positions and exposure.is_complete else None
            ),
            "value_status": (
                "EMPTY_BOOK" if not positions
                else "PRICED" if exposure.is_complete else "PARTIALLY_UNPRICED"
            ),
            "currency": exposure.currency,
            "cost_basis": exposure.cost_basis,
            "is_complete": bool(positions) and exposure.is_complete,
            "unpriced_assets": list(exposure.unpriced_assets),
            "by_lane_cost": {
                lane: sum(p.cost_basis for p in positions if p.lane == lane)
                for lane in {p.lane for p in positions}
            },
            "positions": [
                {"asset": p.asset, "lane": p.lane, "quantity": p.quantity,
                 "cost_basis": p.cost_basis, "currency": p.currency,
                 "value": None, "value_status": "UNPRICED"}
                for p in positions
            ],
            "store_state": book.status.state,
        },
        "decisions": {
            "open": len(orchestrator.open_decisions),
            "limit": orchestrator.queue_limit,
            "queue_is_full": orchestrator.queue_is_full,
            "items": [
                {"id": d.decision_id, "lane": d.lane, "subject": d.subject,
                 "question": d.question, "raised_at": d.raised_at}
                for d in orchestrator.open_decisions
            ],
        },
        "engines": [
            {"lane": lane.lane, "status": lane.status,
             "missing": [r.name for r in lane.missing],
             "summary": lane.summary}
            for lane in lanes
        ],
        "boards": boards,
        "recent_runs": [
            {"lane": r.lane, "at": r.started_at, "status": r.status, "exit": r.exit_code}
            for r in orchestrator.runs[-10:]
        ],
        "refused_fields": {
            # Named so a front end cannot quietly invent them. Every one is argued
            # against in lib/candidates.py or docs/reference-system.md.
            "risk_score": "no scalar over heterogeneous lanes; report unmet preconditions",
            "daily_pnl": "needs a price source; UNPRICED holdings make it unknowable",
            "best_performer": "a ranking is a soft score and invites rotating into what "
                              "just worked",
            "expected_profit": "returns here are GUARANTEED-if-preconditions-hold, not "
                               "probability weighted",
        },
    }


def main() -> int:
    panels = capital_panel() + obligations_panel() + evidence_panel() + boards_panel()
    print("\n".join(panels))
    print("=" * 74)
    print("No figure above is a forecast. Nothing here predicts a price, a sale or a")
    print("return, and there is no score: five heterogeneous lanes summed to one number")
    print("would hide exactly the differences that make them five lanes.")
    return 0


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        raise SystemExit(0)
    if "--json" in sys.argv:
        print(json.dumps(as_json(), indent=2))
        raise SystemExit(0)
    raise SystemExit(main())
