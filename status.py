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


def _pricing_for(positions, source=None):
    """One look at a price source, resolved at call time rather than at import.

    `source=None` means "build the default", not "no source" — the two would be the same
    argument otherwise, and the second is what a test injects a fake for. The default is
    constructed here rather than bound as a default argument, for the reason
    `lib.reaping.reap` records: an import-time default once wrote a journal into the live
    `data/`.
    """

    from lib.pricing import alpaca_prices, value_book

    return value_book(positions, source if source is not None else alpaca_prices())


def capital_panel(source=None) -> list[str]:
    """What is deployed, per lane, what it is worth now, and what could not be marked."""

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
    pricing = _pricing_for(positions, source)
    valuations = pricing.valuations
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
    lines.append(f"  {pricing.describe()}")
    for valuation in valuations:
        lines.append(f"    {valuation.describe()}")
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


def _odds_quota(settings: dict) -> dict:
    """What the odds key has left, and what the current cadence will do to it.

    Running out reads as no arbs, which makes the remaining count a safety control rather
    than a statistic — so it belongs on the page beside the breakers. UNKNOWN is carried
    through as null: nothing has measured it yet is not the same as nothing is left.
    """

    from connectors.oddsapi import (
        FREE_TIER_MONTHLY,
        MINIMUM_REMAINING,
        USAGE,
        Usage,
        credits_per_day,
        describe_burn,
    )

    quota = dict(Usage.load(USAGE).to_dict())
    quota["floor"] = MINIMUM_REMAINING
    try:
        from run import REAP_CADENCES

        sports = len(settings.get("sports") or ())
        if sports:
            daily = credits_per_day(
                sports=sports, cadence_seconds=REAP_CADENCES["arb"],
                bookmakers=tuple(settings.get("bookmakers") or ()),
            )
            quota["credits_per_day"] = daily
            quota["fits"] = daily <= FREE_TIER_MONTHLY / 30.4
            quota["burn"] = describe_burn(daily).split(" — ")[0]
        else:
            quota["credits_per_day"] = None
            quota["fits"] = None
            quota["burn"] = None
    except Exception as error:  # noqa: BLE001 - an estimate that raises is not a status
        quota["credits_per_day"] = None
        quota["fits"] = None
        quota["burn"] = f"not computable ({type(error).__name__})"
    return quota


def _scheduler_state() -> dict:
    """Whether anything is actually running the lanes, and when it last did.

    **This is the state whose absence is invisible.** Every lane has a cadence, and until
    `run.py --serve` existed nothing invoked them: the Procfile declared a web process and
    no worker, and there was no cron entry or timer anywhere. A system in that condition
    renders perfectly — the dashboard loads, the ledger is intact, every lane reports the
    state it was last left in — and nothing runs.

    So a supervisor that has stopped must not read the same as one that has nothing to do.
    NEVER_STARTED, RUNNING and STALE are three different facts, and STALE is the one that
    costs: it means the cadences on this page are describing an intention.
    """

    from run import HEARTBEAT, TICK_SECONDS

    if not HEARTBEAT.is_file():
        return {"status": "NEVER_STARTED", "last_tick_at": None, "ticks": None,
                "reason": ("No supervisor has run. Every cadence on this page is an "
                           "intention until `python run.py --serve` is running.")}
    try:
        beat = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return {"status": "UNREADABLE", "last_tick_at": None, "ticks": None,
                "reason": f"{type(error).__name__}: {error}"}

    last = str(beat.get("last_tick_at") or "")
    tick = int(beat.get("tick_seconds") or TICK_SECONDS)
    age = _age_seconds(last)
    # Three missed ticks, so an ordinary slow run does not read as a dead supervisor.
    stale = age is None or age > tick * 3
    return {
        "status": "STALE" if stale else "RUNNING",
        "last_tick_at": last or None,
        "ticks": beat.get("ticks"),
        "age_seconds": age,
        "tick_seconds": tick,
        "reason": (("The heartbeat has stopped moving, so no lane is being run whatever "
                    "its cadence says.") if stale else None),
    }


def _age_seconds(stamp: str) -> float | None:
    """Seconds since an ISO stamp, or None. An unreadable stamp is never young."""

    from datetime import datetime, timezone

    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) - moment).total_seconds()


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


def _capital_state(book, positions, exposure, pricing=None) -> dict:
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

    **`priced_value` stays null for a third reason now that a source is wired**: a book
    whose holdings priced in more than one currency has no single total, and `Exposure`
    returns `None` rather than a sum of euro and dollars. A reader must not fill that null
    with the arithmetic this layer refused to do.
    """

    unknown = {
        "priced_value": None,
        "cost_basis": None,
        "priced_cost_basis": None,
        "is_complete": False,
        "unpriced_assets": [],
        "stale_assets": [],
        "by_currency": {},
        "by_lane_cost": {},
        "positions": [],
        "currency": exposure.currency,
        "store_state": book.status.state,
        "pricing": pricing.to_dict() if pricing is not None else None,
    }

    if book.status.state in {LOST, UNREADABLE}:
        # Reported apart from an empty book, and the reason carried, because these are the
        # cases where a zero is not merely unfounded but actively wrong: there WAS a book.
        return {**unknown, "value_status": book.status.state,
                "reason": book.status.describe()}

    if not positions:
        return {**unknown, "reason": None,
                "value_status": "EMPTY_BOOK" if BOOK.is_file() else "NOT_CONFIGURED"}

    valuations = {v.asset: v for v in (pricing.valuations if pricing else ())}
    return {
        "priced_value": exposure.priced_value if exposure.is_complete else None,
        "value_status": _value_status(exposure),
        "currency": exposure.currency,
        "cost_basis": sum(p.cost_basis for p in positions),
        "priced_cost_basis": exposure.cost_basis,
        "is_complete": exposure.is_complete,
        "unpriced_assets": list(exposure.unpriced_assets),
        "stale_assets": list(exposure.stale_assets),
        # Each unit under its own name. A reader wanting one number must decide what rate
        # to use and own that decision; there is none here to borrow.
        "by_currency": dict(exposure.by_currency),
        "by_lane_cost": {
            lane: sum(p.cost_basis for p in positions if p.lane == lane)
            for lane in {p.lane for p in positions}
        },
        "positions": [_position_state(p, valuations.get(p.asset)) for p in positions],
        "store_state": book.status.state,
        "pricing": pricing.to_dict() if pricing is not None else None,
        "reason": None,
    }


def _value_status(exposure) -> str:
    """The book's valuation in one word, with the two incomplete cases told apart.

    `MIXED_CURRENCY` is not a degraded `PARTIALLY_UNPRICED`: every holding may have priced
    perfectly and there is still no total, because the answers are in different units. A
    front end told only "partially unpriced" would go looking for the missing prices.
    """

    if exposure.nothing_priced:
        # Not PARTIALLY_UNPRICED: no part of this book priced. The dashboard renders this
        # word beside a null, and "partially" beside a null reads as a rendering fault.
        return "NOTHING_PRICED"
    if exposure.spans_currencies:
        return "MIXED_CURRENCY"
    if exposure.stale_assets and not exposure.unpriced_assets:
        return "PARTIALLY_STALE"
    return "PRICED" if exposure.is_complete else "PARTIALLY_UNPRICED"


def _position_state(position, valuation) -> dict:
    """One holding, with its value null unless a price actually stands behind it.

    `value_currency` is separate from `currency` deliberately: the second is what the
    holding cost, the first is the unit its price came back in, and on a US quote against
    a euro book they differ. Collapsing them is the defect that once printed `-EUR 38.00`.
    """

    priced = valuation is not None and valuation.value is not None
    return {
        "asset": position.asset,
        "lane": position.lane,
        "quantity": position.quantity,
        "cost_basis": position.cost_basis,
        "currency": position.currency,
        "value": valuation.value if priced else None,
        "value_status": valuation.status if valuation is not None else "UNPRICED",
        "value_currency": valuation.currency if priced else None,
        "unit_price": valuation.unit_price if priced else None,
        "priced_at": (valuation.priced_at or None) if priced else None,
        "price_source": (valuation.source or None) if priced else None,
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
            # What actually came back. The only figure on this page that is money rather
            # than a limit, and the only one that needs no price source to be true.
            lines += [f"    {line}" for line in
                      ledger.realised(lane).describe().splitlines()]
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
            # Present on every lane, so a reader never has to tell a missing key from a
            # lane that has made nothing. NOT_CONFIGURED here means no ledger was read.
            "realised": {"status": "NOT_CONFIGURED", "realised_profit": None,
                         "settled": None, "covers_the_whole_book": False},
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
                # Carried with its exclusions, never as a bare number. A lane showing a
                # realised profit while positions are open and UNKNOWN has reported the
                # result of the part that finished, not the result of the lane.
                # The figure carries its own unit. Rendering it against a currency
                # fetched from somewhere else is how EUR 39.00 and USD -77.00 were
                # added together and printed as one total.
                item["realised"] = {
                    **ledger.realised(lane).to_dict(),
                    "currency": item["currency"],
                }
            else:
                item["positions"] = {
                    "status": "UNREADABLE", "reason": ledger.reason,
                    "open": None, "unsettled_exposure": None, "stale_open": None,
                }

        # Only the arb lane buys its evidence by the request, so only it carries a quota.
        # Absent on the others rather than nulled, because a lane with no metered source
        # has no quota rather than an unknown one.
        if lane == "arb":
            item["quota"] = _odds_quota(config.get("arb") or {})
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


def as_json(source=None) -> dict:
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
    pricing = _pricing_for(positions, source)
    exposure = book.exposure(pricing.valuations)

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
        "capital": _capital_state(book, positions, exposure, pricing),
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
        # Whether anything is running the lanes at all. Every other figure on this page
        # describes what the lanes found; this one says whether they are being asked.
        "scheduler": _scheduler_state(),
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
