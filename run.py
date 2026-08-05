"""Fire every lane that is due, hold the ones that are not, and show what awaits you.

    python run.py                 what would run, and why the rest would not
    python run.py --go            actually run them
    python run.py --queue         just the human queue
    python run.py --reap [lane]   every lane, or one of arb/crypto/stocks; places where
                                  the mode allows
    python run.py --reap --dry    the same, and sends nothing whatever the mode says
    python run.py --reap --json   the same run, as the UI contract instead of prose
    python run.py --manual "reason"          take the wheel: lanes keep running, you place
    python run.py --resume "Your Name" "reason"   hand placing back to the machine
    python run.py --resolve DEC-0001 "confirmed and placed"

The orchestration layer. Lanes run on their own cadences, some feed others, and everything
producing work for a person joins one queue.

**The queue is the throttle.** Every lane produces something a human has to act on, and a
human's capacity does not rise because more lanes were added. Past the limit, lanes that
would add more are `HELD`. That is deliberate and it is the opposite of what a dashboard
usually does: the system reports being busiest exactly when it is least able to act, so this
one stops instead.

**A lane that did not run is never shown as a lane that found nothing.** `NOT_DUE`,
`NEVER_RAN`, `HELD` and `FAILED` are four different facts and none of them is a result.

`--reap` is the other half and works the same way. It runs the arb, stocks and chain
reapers from `data/reapers.json` — look, screen, gate, authorise, size — and a lane nobody
configured is reported as `NOT_CONFIGURED` rather than folded in beside the lanes that
looked and found nothing.

**A lane places only when its mode is AUTONOMOUS**, which needs an explicit
`autonomous_execution: true` and no `data/MANUAL` or `data/HALT` overriding it. Every
lane's mode is printed above its harvest, so what is about to happen appears above the
thing that happens. `--dry` sends nothing whatever the modes say, because "show me what it
would do" is a fair question about a live system and answering it should not mean editing
config. The arb lane has no adapter (bookmakers take no orders from programs) and the chain
lane cannot sign; both report that rather than looking unfinished.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lib.orchestrator import HELD, Lane, Orchestrator

STATE = Path("data/orchestrator.json")

#: How often each reaper lane is worth re-running, against how fast its underlying thing
#: actually moves. Odds move in seconds and a scan is bounded by API quota; chain state and
#: filings move slowly.
#:
#: **Arb is set by the quota, not by the odds**, and the arithmetic is worth keeping.
#:
#: A free tier is 500 requests a MONTH, which is 16.4 a day. A request costs one credit
#: per market per region, so the shipped example config — two sports, `uk,eu`, one market
#: — spends four credits a run. At the old thirty minutes, with `arb-scan` asking on the
#: same cadence, that was ~288 a day: the whole allowance in under two days, ending in a
#: lane that reports no arb because the key is spent.
#:
#: Eight hours is the longest of the honest options and the one that fits the config this
#: repository actually ships: 3 runs x 4 credits, plus a daily `arb-scan` at 2, is 14 a
#: day. Narrow to one sport with the bookmakers filter on and the same budget buys a
#: three-hour cadence. `connectors.oddsapi.credits_per_day` computes it for the config in
#: front of you rather than leaving this comment to go stale, and preflight prints it
#: before a key is ever placed.
#:
#: The odds would justify every five minutes. The allowance will not, and the allowance is
#: the binding constraint until the tier is paid for.
REAP_CADENCES = {"arb": 8 * 3600, "crypto": 6 * 3600, "stocks": 24 * 3600}

#: What a lane nobody has given a cadence gets. Six hours is chosen to be unremarkable —
#: often enough to be useful, rare enough that a new lane cannot quietly exhaust a free
#: tier before anybody has decided what its real cadence should be.
DEFAULT_REAP_CADENCE = 6 * 3600


def _reaper_lanes() -> tuple[Lane, ...]:
    """A scheduler entry per reaper lane, generated from the registry rather than listed.

    These were three hand-written `Lane` entries, which meant a fourth reaper assembled,
    placed and appeared on the dashboard while never once being RUN — the failure is
    silence, and silence from a scheduler looks exactly like a quiet market. More lanes are
    planned, so the list is derived and an unlisted cadence falls back to a stated default
    instead of the lane going unscheduled.
    """

    from lib.reaping import LANES as REAPER_LANES

    return tuple(
        Lane(
            name=f"reap-{lane}",
            command=("python", "run.py", "--reap", lane),
            cadence_seconds=REAP_CADENCES.get(lane, DEFAULT_REAP_CADENCE),
            produces_decisions=True,
            findings_exit_codes=(1,),
            # 2 means NOTHING WAS LOOKED AT. A scheduler must not turn a blind lane into
            # a quiet market by treating that as a successful run.
            unconfigured_exit_codes=(2,),
        )
        for lane in REAPER_LANES
    )


#: The lanes, their cadences, and what each one costs a person.
#:
#: Cadences are chosen against how fast the underlying thing actually moves, not against how
#: often it would be nice to look. Chain state and filings change slowly; odds change in
#: seconds, and a scan is bounded by an API quota rather than by usefulness.
LANES = (
    Lane(
        name="monitor",
        command=("python", "monitor.py", "examples/monitor/watchlist.example.json"),
        cadence_seconds=6 * 3600,
        produces_decisions=True,
        # 4 = a material change: a prior review may no longer hold.
        # 5 = the ledger itself was lost, which is not a finding about the world.
        findings_exit_codes=(4, 5),
    ),
    Lane(
        name="arb-scan",
        command=("python", "scan_arb.py", "soccer_epl", "--json"),
        # Daily, and it used to be every 30 minutes alongside `reap-arb` on the same
        # cadence — two lanes buying the same prices from the same key. This one is the
        # discovery view a person reads; `reap-arb` is the one that reaches a sized
        # instruction. Keeping both at half-hourly spent the month's allowance in two days
        # to answer the same question twice.
        cadence_seconds=24 * 3600,
        produces_decisions=True,
        findings_exit_codes=(1,),
        # 2 = no odds source configured, or the quota floor stopped the scan. Not a crash,
        # and not "no arb exists".
        unconfigured_exit_codes=(2,),
    ),
    Lane(
        name="status",
        command=("python", "status.py"),
        cadence_seconds=24 * 3600,
        # Produces no work for a person: it reports, it does not ask. So it is never HELD,
        # and it is the one lane that still runs when the queue is full — which is exactly
        # when somebody most needs to see the state.
        produces_decisions=False,
    ),
    Lane(
        name="preflight",
        command=("python", "preflight.py"),
        cadence_seconds=24 * 3600,
        produces_decisions=False,
        # 1 = a lane is DEGRADED, 2 = a lane is BLOCKED. Both are the report doing its job.
        unconfigured_exit_codes=(1, 2),
    ),
) + _reaper_lanes()


def _run_one(lane: Lane, orchestrator: Orchestrator) -> None:
    try:
        result = subprocess.run(
            list(lane.command), capture_output=True, text=True, timeout=600, check=False
        )
        code, detail = result.returncode, (result.stdout or result.stderr or "")
    except (OSError, subprocess.SubprocessError) as error:
        code, detail = -1, f"{type(error).__name__}: {error}"

    run = orchestrator.record_run(lane, code, detail)
    print(f"  {run.status:<9} {lane.name} (exit {code})")

    if run.status == "FINDINGS" and lane.produces_decisions:
        raised = orchestrator.raise_decision(
            lane.name,
            # STABLE across runs, so the same standing finding does not queue hourly.
            # Resolving it and seeing it again means the condition genuinely recurred.
            subject=f"{lane.name} exited {code}",
            question=(
                "This lane exited with a code meaning it found something. Read its output "
                "and decide what, if anything, it obliges."
            ),
        )
        if raised:
            print(f"            -> queued {raised.decision_id}")
        else:
            # Already open for this subject. Not raising again is the point: a lane on a
            # cadence re-observes the same standing item every cycle.
            print("            -> already queued, not raised again")


def main(go: bool) -> int:
    orchestrator = Orchestrator(LANES, STATE)
    if not orchestrator.readable:
        print(f"REFUSING TO RUN: orchestrator state could not be read "
              f"({orchestrator.reason}).")
        print("Re-running everything would raise every decision already answered.")
        return 2

    plan = orchestrator.plan()
    print("PLAN")
    for verdict in plan:
        print(verdict.describe())
    print()

    if not go:
        print("Nothing was run. Use --go to run the lanes marked RUN.")
        print()
        print(orchestrator.describe_queue())
        return 0

    print("RUNNING")
    lanes = {lane.name: lane for lane in LANES}
    for verdict in plan:
        if verdict.should_run:
            _run_one(lanes[verdict.lane], orchestrator)
    print()

    orchestrator.save()
    print(orchestrator.describe_queue())
    return 1 if orchestrator.open_decisions else 0


def reap(lane: str = "", dry: bool = False, *, as_json: bool = False) -> int:
    """Every configured lane, or one named lane, sized — and placed where the mode allows.

    A lane places only when its mode is AUTONOMOUS, which requires an explicit
    `autonomous_execution: true` with no `data/MANUAL` or `data/HALT` overriding it. The
    mode for every lane is printed before the harvests, so what will happen is visible
    above the thing that happens.

    `--dry` forces research-only regardless of mode. It exists because "I want to see what
    it would do" is a question people ask about live systems, and the answer should not
    require editing config.

    `--json` changes the rendering and nothing else. It is the same run, placing under the
    same modes — reading a live lane through a UI must not be a quieter way of running it,
    and pairing it with `--dry` is how you look without sending.

    Exit codes match the rest of the repository's convention: 1 means something wants a
    person, 2 means nothing was looked at. They are identical in both renderings, because
    a caller that switched to JSON and started reading 0 where it read 2 would be told a
    broken pipeline was a quiet morning by the act of asking for machine-readable output.

        0   every configured lane looked, and nothing reached READY
        1   at least one instruction is waiting for a person
        2   NOTHING WAS LOOKED AT — no lane configured, the config would not parse, or
            every configured lane failed to look. The third case is the one worth having
            a distinct code for: a scheduler treating it as 0 would read a broken
            pipeline as a quiet morning, every morning.
    """

    from lib.reaping import LANES as REAPER_LANES
    from lib.reaping import reap as run_reapers
    from lib.ui_contract import SCHEMA_VERSION

    if lane and lane not in REAPER_LANES:
        choices = ", ".join(REAPER_LANES[:-1]) + f" or {REAPER_LANES[-1]}"
        refusal = f"unknown reaper lane {lane!r}; choose {choices}"
        if as_json:
            print(json.dumps({"schema_version": SCHEMA_VERSION, "status": "REFUSED",
                              "reason": refusal}, indent=2))
        else:
            print(f"Unknown reaper lane {lane!r}. Choose {choices}.")
        return 2

    reaping = run_reapers(lanes=(lane,) if lane else None, place=not dry)
    print(json.dumps(reaping.to_dict(), indent=2) if as_json else reaping.describe())

    if reaping.refusal or not reaping.ready or not reaping.looked:
        return 2
    if any(p.needs_a_person for p in reaping.placements):
        return 1
    return 1 if any(h.status == "READY" for h in reaping.harvests) else 0


def take_over(reason: str, lane: str = "") -> int:
    """Drop to owner-operating. The lanes keep looking; nothing places itself.

    Deliberately not the same as `data/HALT`. A stopped system tells you nothing, so taking
    the wheel must not also mean going blind — every lane still looks, screens, gates,
    authorises and sizes, and each instruction waits for you.
    """

    from lib.operating import take_the_wheel

    path = take_the_wheel(Path("data"), reason, lane=lane)
    scope = f"the {lane} lane" if lane else "every lane"
    print(f"OWNER OPERATING MANUALLY  {scope}")
    print(f"  {path} written.")
    print("  The lanes keep running and keep producing sized instructions. Nothing is "
          "placed automatically.")
    print("  This beats the config: a switch a setting could override would not be a "
          "switch.")
    print()
    print('  Hand it back with:  python run.py --resume "Your Name" "what you checked"')
    return 0


def hand_back(by: str, reason: str, lane: str = "") -> int:
    """Resume autonomous placement. A named person, with a stated reason."""

    from lib.operating import resume

    try:
        switched = resume(Path("data"), by, reason, lane=lane)
    except ValueError as error:
        print(f"REFUSED  {error}")
        return 2

    if not switched:
        print("Nothing was switched to manual, so there is nothing to hand back. The mode "
              "is whatever the config says.")
        return 0
    print(f"Autonomous placement resumed by {by}: {reason}")
    print("  Check what it will actually do before walking away:  python run.py --reap")
    return 0


def resolve(decision_id: str, resolution: str) -> int:
    orchestrator = Orchestrator(LANES, STATE)
    if not orchestrator.resolve(decision_id, resolution):
        print(f"No open decision {decision_id}.")
        return 2
    orchestrator.save()
    print(f"{decision_id} resolved: {resolution}")
    print()
    print(orchestrator.describe_queue())
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        raise SystemExit(0)
    if "--resolve" in argv:
        rest = argv[argv.index("--resolve") + 1:]
        if len(rest) < 2:
            print("Usage: python run.py --resolve DEC-0001 'what you did'")
            raise SystemExit(2)
        raise SystemExit(resolve(rest[0], " ".join(rest[1:])))
    if "--manual" in argv:
        rest = [a for a in argv[argv.index("--manual") + 1:] if not a.startswith("--")]
        if not rest:
            print('Usage: python run.py --manual "why you are taking the wheel" [lane]')
            raise SystemExit(2)
        raise SystemExit(take_over(rest[0], rest[1] if len(rest) > 1 else ""))
    if "--resume" in argv:
        rest = [a for a in argv[argv.index("--resume") + 1:] if not a.startswith("--")]
        if len(rest) < 2:
            print('Usage: python run.py --resume "Your Name" "what you checked" [lane]')
            raise SystemExit(2)
        raise SystemExit(hand_back(rest[0], rest[1], rest[2] if len(rest) > 2 else ""))
    if "--reap" in argv:
        # Flags filtered out: `--reap --dry` otherwise reads --dry as a lane name.
        rest = [a for a in argv[argv.index("--reap") + 1:] if not a.startswith("--")]
        raise SystemExit(reap(rest[0] if rest else "", dry="--dry" in argv,
                              as_json="--json" in argv))
    if "--queue" in argv:
        raise SystemExit(0 if not print(Orchestrator(LANES, STATE).describe_queue()) else 0)
    raise SystemExit(main("--go" in argv))
