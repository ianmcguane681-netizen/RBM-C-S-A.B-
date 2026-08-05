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
from lib.store import LOST, UNREADABLE

def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


BOOK = Path("data/portfolio.json")
LEDGER = Path("data/monitor-ledger.json")
REGISTER = Path("data/seen-register.json")
REAPER_CONFIG = Path("data/reapers.json")
OUTCOMES = Path("data/outcomes.json")
#: Imported, never restated. This file held its own copy of the lane list, so a fourth
#: lane would have been assembled, scheduled and placed while remaining invisible on the
#: money panel — the one screen whose job is to show every lane that can spend. More lanes
#: than these three are planned, which makes a second list a defect waiting for a date.
from lib.reaping import LANES as MONEY_LANES  # noqa: E402


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


def _reap_history(limit: int = 10) -> dict:
    """What the lanes reported, kept after the processes that reported it.

    UNREADABLE and empty are separate, and the difference matters here more than most:
    "no run has been recorded" is a fact about this system, while "the journal will not
    open" is a fact about a file — and rendering the second as the first would say a
    system that has been running for weeks has never run.
    """

    from lib.journal import Journal
    from lib.reaping import JOURNAL

    journal = Journal(JOURNAL)
    if not journal.readable:
        return {"status": "UNREADABLE", "reason": journal.reason, "runs": None,
                "counts": journal.counts()}
    runs = journal.recent_runs(limit)
    return {
        "status": "READABLE" if runs else "EMPTY",
        "reason": None,
        "runs": [dict(run) for run in runs],
        "counts": journal.counts(),
    }


def _capital_state(book, positions, exposure) -> dict:
    """The capital block, keeping a book that vanished apart from a book that is empty.

    **Three different nothings were rendering as one zero.** A portfolio file that never
    existed, one that existed and is now unreadable or gone, and one that is genuinely
    empty all produce nought positions, and every figure derived from them came out `0.0`.
    The dashboard put that in the largest type on the page as `CAPITAL AT COST €0.00`
    beside the word EMPTY_BOOK — a measured balance, assembled from a missing file.

    The text panel never made this mistake: `capital_panel` returns early on LOST and says
    in as many words that an empty book is "not a zero balance: nothing has been entered,
    so nothing is known about what is held". `as_json` did not check the store state at
    all, so a vanished portfolio reported an empty one. That is this repository's founding
    defect and its most consequential form — the vanished ledger reporting FIRST_SEEN.

    So `cost_basis` is `None` in every one of the three cases rather than `0.0`. An empty
    book gets a null too, deliberately: the panel's wording is that nothing is KNOWN, not
    that nothing is held, and the JSON has no business being more confident than the prose
    it mirrors. A real total is emitted only when there are real positions behind it.

    **And `cost_basis` is now summed from the positions rather than taken from
    `Exposure`.** `Exposure.cost_basis` is the cost of the PRICED subset — it accumulates
    only where a valuation came back — so with no price source wired for any lane, which
    is the current state of every lane, it is `0.0` however much is held. The dashboard
    labels that figure CAPITAL AT COST. A fully stocked book was therefore rendering as
    €0.00 too, and the empty-book case was only the most obvious instance of it.

    What was paid is knowable without any price source, which is exactly why it is the
    figure worth showing while pricing is unwired. The priced subset keeps its own name in
    `priced_value`, null until the valuation is complete.
    """

    unknown = {
        "priced_value": None,
        "cost_basis": None,
        "priced_cost_basis": None,
        "is_complete": False,
        "unpriced_assets": [],
        "by_lane_cost": {},
        "positions": [],
        "currency": exposure.currency,
        "store_state": book.status.state,
    }

    if book.status.state in {LOST, UNREADABLE}:
        # Reported apart from an empty book, and the reason carried, because these are the
        # cases where a zero is not merely unfounded but actively wrong: there WAS a book.
        return {**unknown, "value_status": book.status.state,
                "reason": book.status.describe()}

    if not positions:
        return {**unknown, "reason": None,
                "value_status": "EMPTY_BOOK" if BOOK.is_file() else "NOT_CONFIGURED"}

    return {
        "priced_value": exposure.priced_value if exposure.is_complete else None,
        "value_status": "PRICED" if exposure.is_complete else "PARTIALLY_UNPRICED",
        "currency": exposure.currency,
        "cost_basis": sum(p.cost_basis for p in positions),
        "priced_cost_basis": exposure.cost_basis,
        "is_complete": exposure.is_complete,
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
        "reason": None,
    }


def _controls_for(lane: str, settings: dict, *, directory: Path):
    """One lane's ring-fence and breakers, built by the code that actually runs the lane.

    Returns `(breakers, invalid_reason)`; exactly one is set.

    **This delegates to `lib.reaping.breakers_for` rather than constructing a `Ringfence`
    here, and the reason is a defect this panel had.** It built its own, and dropped
    `max_deployed_pct` and `max_concurrent_positions` on the way, so a lane configured to
    keep 20% deployed was described against the dataclass default of 40. It also omitted
    the outcome ledger, which `Breakers` documents as the thing without which the
    deployed-capital control cannot be evaluated at all.

    Nothing visible was wrong yet, because this panel only reads the breaker state off
    disk. That is what makes it worth removing: two notions of what a lane's limits are,
    agreeing today, with nothing to make the disagreement visible on the day it starts.
    `positions.py --apply` states the same rule in its own docstring.
    """

    from lib.reaping import breakers_for

    try:
        return breakers_for(lane, settings, directory=directory,
                            kill_switch=directory / "HALT"), ""
    except (KeyError, TypeError, ValueError) as error:
        return None, f"{type(error).__name__}: {error}"


def money_panel(
    *,
    config_path: Path = REAPER_CONFIG,
    directory: Path = Path("data"),
    ledger_path: Path = OUTCOMES,
) -> list[str]:
    """Authority, controls and exposure for every lane that can move money."""

    from lib.operating import modes_for
    from lib.outcomes import OutcomeLedger, describe_ledger
    from lib.reaping import load_config

    lines = ["MONEY LANES"]
    config, config_error = load_config(config_path)
    ledger = OutcomeLedger(ledger_path)
    modes = modes_for(MONEY_LANES, config, directory=directory, ledger=ledger)

    for lane, mode in zip(MONEY_LANES, modes):
        lines.append(f"  {lane.upper()}")
        lines += [f"    {line}" for line in mode.describe().splitlines()]

        settings = config.get(lane) or {}
        if config_error:
            lines.append(
                f"    UNREADABLE  {config_path} would not parse ({config_error}). The "
                f"ring-fence and authority are unknown, so this lane must not operate."
            )
        elif not settings or not settings.get("enabled", True):
            lines.append(
                "    NOT_CONFIGURED  No ring-fence is configured. This is not a zero "
                "balance or zero exposure. Configure the lane before allowing it to run."
            )
        else:
            breakers, invalid = _controls_for(lane, settings, directory=directory)
            if invalid:
                lines.append(
                    f"    UNREADABLE  ring-fence configuration is invalid "
                    f"({invalid}). Correct {config_path}; an "
                    f"unknown limit is not a satisfied limit."
                )
            else:
                ring = breakers.ringfence
                lines.append(
                    f"    RING-FENCE  {ring.starting_balance:,.2f} {ring.currency}"
                )
                breaker_path = directory / f"breakers-{lane}.json"
                if not breaker_path.is_file():
                    lines.append(
                        f"    BREAKER  NOT_CONFIGURED  {breaker_path} does not exist. "
                        f"This is not an armed breaker with no losses; configure and "
                        f"initialise it before the lane operates."
                    )
                elif not breakers.readable:
                    lines.append(
                        f"    BREAKER  UNREADABLE  {breakers.reason}. Repair or "
                        f"restore {breaker_path}; an unknown loss history must stop "
                        f"the lane."
                    )
                elif breakers.state.is_armed:
                    lines.append("    BREAKER  ARMED")
                else:
                    lines.append(
                        f"    BREAKER  {breakers.state.status}  "
                        f"{breakers.state.tripped_by} at {breakers.state.tripped_at}"
                    )
                    lines.append(
                        "      It does not self-clear. A named person must "
                        "investigate and reset it with a recorded reason."
                    )

        if not ledger_path.is_file():
            lines.append(
                f"    POSITIONS  NOT_CONFIGURED  {ledger_path} does not exist. This is "
                f"not 0.00 at risk; initialise the outcome ledger before placing."
            )
        else:
            lines += [f"    {line}" for line in
                      describe_ledger(ledger, lane=lane).splitlines()]
        lines.append("")

    return lines


def money_state(
    *,
    config_path: Path = REAPER_CONFIG,
    directory: Path = Path("data"),
    ledger_path: Path = OUTCOMES,
) -> list[dict]:
    """The money panel's third states in fields a front end cannot flatten to zero."""

    from lib.operating import modes_for
    from lib.outcomes import OutcomeLedger
    from lib.reaping import load_config

    config, config_error = load_config(config_path)
    ledger = OutcomeLedger(ledger_path)
    modes = modes_for(MONEY_LANES, config, directory=directory, ledger=ledger)
    states = []

    for lane, mode in zip(MONEY_LANES, modes):
        settings = config.get(lane) or {}
        item = {
            "lane": lane,
            "mode": mode.mode,
            "mode_source": mode.source,
            "places_without_asking": mode.may_place,
            "balance": None,
            "currency": None,
            "breaker": {"status": "NOT_CONFIGURED"},
            "positions": {"status": "NOT_CONFIGURED", "open": None,
                          "unsettled_exposure": None, "stale_open": None},
        }

        if config_error:
            item["breaker"] = {"status": "UNREADABLE", "reason": config_error}
        elif settings and settings.get("enabled", True):
            breakers, invalid = _controls_for(lane, settings, directory=directory)
            if invalid:
                item["breaker"] = {"status": "UNREADABLE", "reason": invalid}
            else:
                item["balance"] = breakers.ringfence.starting_balance
                item["currency"] = breakers.ringfence.currency
                if (directory / f"breakers-{lane}.json").is_file():
                    if breakers.readable:
                        item["breaker"] = {
                            "status": breakers.state.status,
                            "tripped_by": breakers.state.tripped_by or None,
                            "tripped_at": breakers.state.tripped_at or None,
                            "self_clears": False,
                        }
                    else:
                        item["breaker"] = {
                            "status": "UNREADABLE", "reason": breakers.reason,
                        }

        if ledger_path.is_file():
            if ledger.readable:
                live = ledger.live(lane)
                stale = ledger.stale_open(lane=lane)
                item["positions"] = {
                    "status": "READABLE",
                    "open": len(live),
                    "unsettled_exposure": ledger.unsettled_exposure(lane),
                    "stale_open": len(stale),
                    "daily_loss_limit_can_see_exposure": False,
                }
            else:
                item["positions"] = {
                    "status": "UNREADABLE", "reason": ledger.reason,
                    "open": None, "unsettled_exposure": None, "stale_open": None,
                }
        states.append(item)

    return states


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

    from lib.ui_contract import SCHEMA_VERSION

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        # Every figure null unless there are real positions behind it, and a book that
        # vanished reported apart from one that is empty. See `_capital_state`.
        "capital": _capital_state(book, positions, exposure),
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
        "money_lanes": money_state(),
        "boards": boards,
        # The scheduler's view: which lane fired, when, and with what exit code.
        "recent_runs": [
            {"lane": r.lane, "at": r.started_at, "status": r.status, "exit": r.exit_code}
            for r in orchestrator.runs[-10:]
        ],
        # The journal's view, which is a different question. `recent_runs` above says a
        # process ran and what it exited with; this says what the lanes actually reported
        # and whether anything was submitted — the only record that outlives the run, and
        # the only thing that can answer whether a function has produced anything real.
        "reap_history": _reap_history(),
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
    panels = (capital_panel() + money_panel() + obligations_panel() + evidence_panel()
              + boards_panel())
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
