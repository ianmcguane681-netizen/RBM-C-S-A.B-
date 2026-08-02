"""Every lane, in one place, in the same units — the data layer any UI reads.

    python status.py

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

import sys
from pathlib import Path

from lib.portfolio import LANES, Portfolio
from lib.preflight import BLOCKED, DEGRADED, all_lanes
from lib.store import LOST

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
    raise SystemExit(main())
