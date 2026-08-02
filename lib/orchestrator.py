"""Several lanes running on their own cadences, feeding each other, with a human in the loop.

The missing piece. Every lane in this repository is a manual invocation: `monitor.py`,
`scan_arb.py`, `check_stock.py`, `check_token.py`. Nothing fires them, nothing connects
them, and nothing collects what they produce that needs a person.

Three things this has to get right, and the third is the one nobody builds.

**A lane that did not run must not look like a lane that ran and found nothing.** The
recurring defect, pointed at a scheduler. A crashed runner, a cadence not yet elapsed and a
clean run with no findings are three different facts, and a dashboard showing "0 alerts" for
all three is worse than no dashboard.

    COMPLETED   ran, exited cleanly
    FINDINGS    ran, exited with a code meaning it found something
    FAILED      ran, and did not exit cleanly
    NOT_DUE     the cadence has not elapsed. Not a result.
    NEVER_RAN   no record of this lane ever running. Not a result either.
    HELD        deliberately not run, because the human queue is too deep

**Chaining is by declared output, not by hope.** A lane that consumes another's output
records which run it consumed. If the upstream lane has not run, the downstream one reports
`NOT_DUE` against a named dependency rather than running against nothing.

**The orchestrator slows down when the queue is deep.** This is the part that matters and
the part that is normally left out. Every lane produces work for a person — a candidate to
confirm, a report to verify, a decision to ratify — and a person's capacity does not rise
because more lanes were added. An orchestrator that fires regardless converts a backlog into
a bigger backlog and calls it throughput.

So `HELD` exists, and a lane whose output would join a queue already past its limit is not
run. The queue depth is the throttle, deliberately, because the alternative is a system that
looks busiest exactly when it is least able to act on anything.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

COMPLETED = "COMPLETED"
FINDINGS = "FINDINGS"
FAILED = "FAILED"
#: Ran, and reported that it cannot see enough to answer. Found by running this: preflight
#: and scan_arb both exit 2 meaning "no source is configured", which was landing as FAILED.
#: A lane saying "I am not wired up" is telling the truth, and a crash is not.
UNCONFIGURED = "UNCONFIGURED"
NOT_DUE = "NOT_DUE"
NEVER_RAN = "NEVER_RAN"
HELD = "HELD"

OPEN = "OPEN"
RESOLVED = "RESOLVED"

#: Past this many open items, lanes that would add more are HELD. A number rather than a
#: judgement, chosen in advance, for the same reason the obligation table is.
DEFAULT_QUEUE_LIMIT = 12


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(when: datetime) -> str:
    return when.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@dataclass(frozen=True, slots=True)
class Lane:
    """One thing that runs, how often, and what it needs first."""

    name: str
    command: tuple[str, ...]
    cadence_seconds: int
    #: What a person has to do with this lane's output, if anything. A lane that produces
    #: no human work never contributes to the queue and is never HELD.
    produces_decisions: bool = False
    #: Lanes whose output this one consumes. Named, so a downstream lane reports a missing
    #: dependency rather than running against nothing and reporting a clean result.
    consumes: tuple[str, ...] = ()
    #: Exit codes meaning "ran fine and found something worth a look", as opposed to
    #: failure. monitor.py exits 4 on a material change; scan_arb.py exits 1 on a candidate.
    findings_exit_codes: tuple[int, ...] = ()
    #: Exit codes meaning "ran fine and cannot see enough to answer". Distinct from both a
    #: clean run and a crash, because the response is to supply a credential rather than to
    #: debug anything.
    unconfigured_exit_codes: tuple[int, ...] = ()
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class Run:
    lane: str
    started_at: str
    status: str
    exit_code: int = 0
    detail: str = ""

    @property
    def was_attempted(self) -> bool:
        return self.status in {COMPLETED, FINDINGS, FAILED, UNCONFIGURED}


@dataclass(frozen=True, slots=True)
class Decision:
    """One thing waiting on a person. The queue this whole design throttles against."""

    decision_id: str
    lane: str
    subject: str
    question: str
    raised_at: str
    status: str = OPEN
    resolved_at: str = ""
    resolution: str = ""


@dataclass(frozen=True, slots=True)
class Verdict:
    """Whether a lane runs now, and why not if not."""

    lane: str
    status: str
    reason: str = ""
    last_run: str = ""

    @property
    def should_run(self) -> bool:
        return self.status == COMPLETED

    def describe(self) -> str:
        if self.status == COMPLETED:
            return f"  RUN      {self.lane}"
        return f"  {self.status:<8} {self.lane}: {self.reason}"


class Orchestrator:
    """Decides what runs, records what ran, and holds the human queue."""

    def __init__(
        self,
        lanes: Sequence[Lane],
        path: str | Path,
        *,
        queue_limit: int = DEFAULT_QUEUE_LIMIT,
    ) -> None:
        self.lanes = tuple(lanes)
        self.path = Path(path)
        self.queue_limit = queue_limit
        self.runs: list[Run] = []
        self.decisions: list[Decision] = []
        self.readable = True
        self.reason = ""

        if self.path.is_file():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                self.runs = [Run(**r) for r in payload.get("runs", [])]
                self.decisions = [Decision(**d) for d in payload.get("decisions", [])]
            except (OSError, ValueError, TypeError) as error:
                # A state file that will not parse has NOT been read. Treating it as empty
                # would re-run everything and re-raise every decision already answered.
                self.readable = False
                self.reason = f"{type(error).__name__}: {error}"[:120]

    @property
    def open_decisions(self) -> tuple[Decision, ...]:
        return tuple(d for d in self.decisions if d.status == OPEN)

    @property
    def queue_is_full(self) -> bool:
        return len(self.open_decisions) >= self.queue_limit

    def last_run(self, lane: str) -> Run | None:
        attempts = [r for r in self.runs if r.lane == lane and r.was_attempted]
        return max(attempts, key=lambda r: r.started_at) if attempts else None

    def plan(self, *, now: datetime | None = None) -> tuple[Verdict, ...]:
        """What would run, and the reason for everything that would not.

        Never returns a bare list of things to run: a lane held back is a fact a person
        needs, and omitting it is how a scheduler quietly stops doing half its job.
        """

        moment = now or _now()
        if not self.readable:
            return tuple(
                Verdict(lane.name, FAILED,
                        f"orchestrator state could not be read ({self.reason}); refusing "
                        f"to run, because re-running everything would re-raise decisions "
                        f"already answered")
                for lane in self.lanes
            )

        verdicts: list[Verdict] = []
        for lane in self.lanes:
            if not lane.enabled:
                verdicts.append(Verdict(lane.name, NOT_DUE, "disabled"))
                continue

            missing = [
                name for name in lane.consumes
                if self.last_run(name) is None
            ]
            if missing:
                verdicts.append(Verdict(
                    lane.name, NOT_DUE,
                    f"depends on {', '.join(missing)}, which has never run. Running this "
                    f"now would produce a clean result over no input.",
                ))
                continue

            if lane.produces_decisions and self.queue_is_full:
                verdicts.append(Verdict(
                    lane.name, HELD,
                    f"{len(self.open_decisions)} decision(s) already open against a limit "
                    f"of {self.queue_limit}. More output would be a bigger backlog, not "
                    f"more throughput.",
                ))
                continue

            previous = self.last_run(lane.name)
            if previous is None:
                verdicts.append(Verdict(lane.name, COMPLETED, "never run", ""))
                continue

            started = _parse(previous.started_at)
            if started is None:
                verdicts.append(Verdict(lane.name, COMPLETED, "last run time unreadable"))
                continue

            due_at = started + timedelta(seconds=lane.cadence_seconds)
            if moment < due_at:
                verdicts.append(Verdict(
                    lane.name, NOT_DUE,
                    f"next due {_stamp(due_at)}", previous.started_at,
                ))
                continue

            verdicts.append(Verdict(lane.name, COMPLETED, "due", previous.started_at))
        return tuple(verdicts)

    def record_run(self, lane: Lane, exit_code: int, detail: str = "",
                   *, now: datetime | None = None) -> Run:
        status = FAILED
        if exit_code == 0:
            status = COMPLETED
        elif exit_code in lane.findings_exit_codes:
            status = FINDINGS
        elif exit_code in lane.unconfigured_exit_codes:
            status = UNCONFIGURED
        run = Run(lane.name, _stamp(now or _now()), status, exit_code, detail[:400])
        self.runs.append(run)
        return run

    def raise_decision(self, lane: str, subject: str, question: str,
                       *, now: datetime | None = None) -> Decision | None:
        """Add to the queue, unless the same subject is already open.

        Deduplicated on (lane, subject) because a lane running on a cadence will re-observe
        the same standing item every cycle, and a queue that grew by one every hour would
        be noise rather than a queue.

        The subject must therefore be STABLE across runs. An earlier version built it from
        the run timestamp, which made every subject unique and the deduplication dead code
        that looked like it worked -- found by running this, not by reading it.
        """

        if any(d.status == OPEN and d.lane == lane and d.subject == subject
               for d in self.decisions):
            return None
        decision = Decision(
            decision_id=f"DEC-{len(self.decisions) + 1:04d}",
            lane=lane, subject=subject, question=question,
            raised_at=_stamp(now or _now()),
        )
        self.decisions.append(decision)
        return decision

    def resolve(self, decision_id: str, resolution: str,
                *, now: datetime | None = None) -> bool:
        for index, decision in enumerate(self.decisions):
            if decision.decision_id == decision_id and decision.status == OPEN:
                self.decisions[index] = Decision(
                    **{**asdict(decision), "status": RESOLVED,
                       "resolved_at": _stamp(now or _now()), "resolution": resolution}
                )
                return True
        return False

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError(
                "refusing to overwrite orchestrator state that could not be read: every "
                "answered decision would be raised again"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Runs are trimmed; decisions never are. A run is a fact about the past, a decision
        # may still be waiting on somebody.
        self.path.write_text(json.dumps({
            "runs": [asdict(r) for r in self.runs[-500:]],
            "decisions": [asdict(d) for d in self.decisions],
        }, indent=2) + "\n", encoding="utf-8")

    def describe_queue(self) -> str:
        pending = self.open_decisions
        if not pending:
            return (
                "AWAITING YOUR CALL: 0. Nothing is waiting on you. That covers decisions "
                "raised by lanes that ran, and says nothing about lanes that did not."
            )
        lines = [f"AWAITING YOUR CALL: {len(pending)} of {self.queue_limit}"]
        if self.queue_is_full:
            lines.append(
                "  QUEUE FULL. Lanes producing decisions are HELD until this drops. That "
                "is deliberate: more output against a full queue is a bigger backlog, not "
                "more throughput."
            )
        for decision in pending:
            lines.append(f"  {decision.decision_id}  [{decision.lane}] {decision.subject}")
            lines.append(f"           {decision.question}")
        return "\n".join(lines)
