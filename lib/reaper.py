"""A lane worked end to end, autonomously, stopping exactly where a person is required.

A reaper takes one lane from "look" to "here is a sized instruction that is permitted", and
does everything in between without being asked. What it never does is place it.

    look  →  screen  →  veto check  →  authorise  →  size  →  READY, or a stated refusal

## The board is optional here, and that is the point

Until now the veto input could only come from a published board decision, which meant a
lane could not act without convening six seats, drafting six reports and ratifying. For a
solo operator spending their own money that ceremony proves rigour to an audience that does
not exist — the audit chain earns its keep when somebody else must be convinced.

So `gate_findings` runs the same checks the board reads, directly, and returns findings in
the shape `lib.thesis.evaluate` already accepts. The gates are the part that catches things
that cost money; the ceremony is the part that proves it to a third party. A reaper uses the
first and skips the second, and a formal review remains available for a position large
enough to want a record of.

**The veto is not weakened by this.** The same findings block; they simply arrive without a
convening. What is lost is the audit chain, and that loss is stated in the harvest rather
than glossed, so a decision taken this way is never mistaken for one taken under review.

## What a reaper reports

    READY            screened, not vetoed, authorised, sized. A person places it.
    REFUSED          something said no, and the harvest names which
    INDETERMINATE    something could not be evaluated. Not a refusal, and not permission.
    NOTHING_FOUND    it looked properly and there was nothing
    COULD_NOT_LOOK   it did not look. NOT the same as finding nothing.

The last pair is the recurring defect at the level of the whole lane. A reaper whose source
was down and a reaper that scanned six books and found nothing both produce an empty list,
and reporting them alike is how a system convinces somebody the market is quiet.

## The breakers are consulted last, after the size exists

A breaker needs a number to check, so it cannot run before sizing. That makes it the LAST
gate rather than the first, which is the right place for a different reason too: everything
before it is about whether this particular thing is a good idea, and the breakers are about
whether the lane should be doing anything at all. A tripped breaker refuses a perfectly good
candidate, and that is the point.

Refusing to wire them in and remembering to call them separately would work until the
evening somebody forgot, so a reaper without breakers cannot produce READY at all.

## Autonomy stops before money

`autonomous_execution` exists, defaults to `False`, and is refused outright for the chain
lane. A reaper may look, screen, gate, authorise and size without being asked. Placing is a
separate deliberate act, because everything upstream of it is reversible and it is not.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

READY = "READY"
REFUSED = "REFUSED"
INDETERMINATE = "INDETERMINATE"
NOTHING_FOUND = "NOTHING_FOUND"
COULD_NOT_LOOK = "COULD_NOT_LOOK"

#: Lanes where autonomous placement is refused whatever the configuration says. Chain
#: transactions are atomic, irreversible and signed with keys that control everything else
#: in the wallet; there is no order to cancel and no counterparty to ring.
NEVER_AUTONOMOUS = frozenset({"crypto", "chain"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _stage_reason(verdict: Any, prefix: str) -> str:
    """Name the deciding stage AND carry its detail up.

    Without the detail an unmeasured cascade reports "a stage was not measured", which is
    true and useless: the whole value of the arb lane's first stage is that it says which
    two books need their rules read. A refusal a person cannot act on is a refusal they
    will learn to skim.
    """

    stage = getattr(verdict, "decided_by", None)
    name = getattr(stage, "name", "a stage")
    detail = str(getattr(stage, "detail", "") or "").strip()
    return f"{prefix} {name}" + (f": {detail}" if detail else "")


@dataclass(frozen=True, slots=True)
class Unworthy:
    """Sized successfully, and not worth placing.

    The distinction the rest of this repository keeps making, at the one place `size` would
    otherwise collapse it. `None` from `size` means a constraint could not be measured,
    which is INDETERMINATE. A slip that priced correctly and came out under the return
    floor is a MEASURED refusal, and reporting it as INDETERMINATE would put "I could not
    work out how much" and "I worked it out and it is not worth it" in the same bucket.
    """

    reason: str


def gate_findings(readings: Sequence[Any]) -> list[dict]:
    """Turn gate output into findings, without convening anything.

    Accepts anything carrying a `status` and a `describe()` — the shape every connector
    finding in this repository already has. A status naming a third state
    (`NO_VENUE_FOUND`, `NOT_ASSESSED`, `UNREADABLE`, `NOT_CONFIGURED`) becomes a finding
    that BLOCKS at SEV-2, because a gate that could not be assessed has not been passed.

    That is deliberately stricter than a board, which would record an unassessed gate as an
    omission and carry on. Without seats to weigh it, an unreadable gate has to stop things
    on its own or it stops nothing at all.

    A reading may carry a boolean `blocking` and that overrides the name. Sniffing the
    status string is a decent default for the connector readings written before this
    existed, but it makes whether a gate stops the lane depend on how somebody spelled a
    constant — `STAKE_UNREAD` blocks nothing while `STAKE_NOT_READ` blocks everything, for
    no reason a reader could infer. A gate that knows whether it is a precondition says so.
    """

    findings: list[dict] = []
    for index, reading in enumerate(readings):
        status = str(getattr(reading, "status", "") or "")
        if not status:
            continue
        declared = getattr(reading, "blocking", None)
        blocking = declared if isinstance(declared, bool) else any(
            marker in status
            for marker in ("NOT_", "NO_", "UNREADABLE", "UNKNOWN", "MISMATCH",
                           "INDETERMINATE", "FAIL")
        )
        if not blocking:
            continue
        describe = getattr(reading, "describe", None)
        findings.append({
            "finding_id": f"GATE-{index + 1:03d}",
            "severity": "SEV-2",
            "status": "OPEN",
            "title": status,
            "detail": describe() if callable(describe) else str(reading),
            "source": "gate_findings (no board convened)",
        })
    return findings


@dataclass(frozen=True, slots=True)
class Harvest:
    """What one reaper run produced, and precisely why if it produced nothing."""

    lane: str
    status: str
    at: str = ""
    subject: str = ""
    reason: str = ""
    #: The sized, permitted instruction, when there is one. Never partially filled in.
    instruction: Any = None
    permission: Any = None
    sources_asked: int = 0
    sources_answered: int = 0
    #: True when no board decision backed the veto. Stated so a decision taken this way is
    #: never mistaken for one taken under review.
    board_convened: bool = False

    @property
    def coverage(self) -> str:
        if not self.sources_asked:
            return "no sources declared"
        return f"{self.sources_answered} of {self.sources_asked} source(s) answered"

    def describe(self) -> str:
        head = f"{self.status}  [{self.lane}]" + (f"  {self.subject}" if self.subject else "")
        lines = [head]
        if self.reason:
            lines.append(f"  {self.reason}")

        if self.status == COULD_NOT_LOOK:
            lines.append(
                "  This lane did NOT look. It is not a report that there was nothing to "
                "find, and a run of these in a row is a broken pipeline rather than a "
                "quiet market."
            )
        elif self.status == NOTHING_FOUND:
            lines.append(f"  Looked properly: {self.coverage}. Nothing met the criteria.")
            if self.sources_answered < self.sources_asked:
                lines.append(
                    "  Something better may exist at a source that did not answer."
                )
        elif self.status == READY:
            lines.append(
                "  Screened, not vetoed, authorised and sized. NOTHING HAS BEEN PLACED. "
                "A person places it."
            )
        elif self.status == INDETERMINATE:
            lines.append(
                "  A condition could not be evaluated. That is not a refusal and it is not "
                "permission."
            )

        if self.status in {READY, REFUSED, INDETERMINATE} and not self.board_convened:
            lines.append(
                "  No board was convened. The same gates blocked or did not block, and "
                "there is no audit chain behind this — it is a working decision, not a "
                "reviewed one."
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Stable UI state; absent instructions and permissions remain null."""

        def serialise(value: Any) -> Any:
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            if hasattr(value, "to_dict"):
                return value.to_dict()
            if is_dataclass(value):
                return {key: serialise(item) for key, item in asdict(value).items()}
            if isinstance(value, (tuple, list)):
                return [serialise(item) for item in value]
            if isinstance(value, dict):
                return {str(key): serialise(item) for key, item in value.items()}
            return str(value)

        return {
            "lane": self.lane,
            "status": self.status,
            "at": self.at or None,
            "subject": self.subject or None,
            "reason": self.reason or None,
            "instruction": serialise(self.instruction),
            "permission": serialise(self.permission),
            "sources": {
                "status": "KNOWN" if self.sources_asked else "NOT_DECLARED",
                "asked": self.sources_asked if self.sources_asked else None,
                "answered": self.sources_answered if self.sources_asked else None,
            },
            "board_convened": self.board_convened,
        }


@dataclass(frozen=True, slots=True)
class Reaper:
    """One lane, worked autonomously up to the point money would move.

    Every stage is a callable supplied by the caller, so this holds the SEQUENCE and the
    refusals and knows nothing about odds, filings or chains. The sequence is the part
    worth getting right once.
    """

    name: str
    lane: str
    #: Returns (subjects, sources_asked, sources_answered). Raising is caught and becomes
    #: COULD_NOT_LOOK, which is the distinction the whole type exists for.
    look: Callable[[], tuple[Sequence[Any], int, int]]
    #: A subject -> cascade verdict with `.verdict` in SURFACED / REFUSED / INDETERMINATE.
    screen: Callable[[Any], Any]
    #: A subject -> gate readings, for the veto. No board involved.
    gates: Callable[[Any], Sequence[Any]]
    #: A subject -> Thesis or None.
    thesis_for: Callable[[Any], Any]
    #: (subject, permission) -> a sized instruction, or None if it cannot be sized.
    size: Callable[[Any, Any], Any]
    #: The lane's circuit breakers. Required to reach READY: a reaper with none cannot
    #: produce a ready instruction at all, because remembering to check them separately
    #: works right up until the evening somebody forgets.
    breakers: Any = None
    #: (instruction) -> (proposed_size, claimed_edge_pct), so the breakers get numbers
    #: rather than having to understand what a bet or an order is.
    measure: Callable[[Any], tuple[float, float]] | None = None
    autonomous_execution: bool = False

    def __post_init__(self) -> None:
        if self.autonomous_execution and self.lane in NEVER_AUTONOMOUS:
            raise ValueError(
                f"autonomous execution is refused for the {self.lane} lane whatever the "
                f"configuration says: a chain transaction is atomic, irreversible and "
                f"signed with keys controlling everything else in the wallet"
            )

    def reap(self) -> tuple[Harvest, ...]:
        """Look once, and carry everything found as far as it honestly goes."""

        from lib.thesis import PERMITTED, evaluate

        try:
            subjects, asked, answered = self.look()
        except Exception as error:  # noqa: BLE001 - any failure to look is COULD_NOT_LOOK
            return (Harvest(
                self.lane, COULD_NOT_LOOK, _now(),
                reason=f"{type(error).__name__}: {error}"[:160],
            ),)

        if not subjects:
            return (Harvest(
                self.lane, NOTHING_FOUND, _now(),
                sources_asked=asked, sources_answered=answered,
            ),)

        harvests: list[Harvest] = []
        for subject in subjects:
            harvests.append(self._work(subject, asked, answered, evaluate, PERMITTED))
        return tuple(harvests)

    def _work(self, subject, asked, answered, evaluate, permitted) -> Harvest:
        name = str(getattr(subject, "market", None) or getattr(subject, "subject", subject))
        common = {"at": _now(), "subject": name,
                  "sources_asked": asked, "sources_answered": answered}

        verdict = self.screen(subject)
        cascade = str(getattr(verdict, "verdict", ""))
        if cascade == "REFUSED":
            return Harvest(self.lane, REFUSED,
                           reason=_stage_reason(verdict, "the cascade refused at"), **common)
        if cascade != "SURFACED":
            return Harvest(self.lane, INDETERMINATE, reason=_stage_reason(
                verdict, "the cascade could not be completed; unmeasured at"), **common)

        try:
            findings = gate_findings(self.gates(subject))
        except Exception as error:  # noqa: BLE001
            # Gates that could not be RUN are not gates that found nothing. None, not [].
            findings = None
            reason = f"gates could not be run: {type(error).__name__}: {error}"[:160]
        else:
            reason = ""

        thesis = self.thesis_for(subject)
        permission = evaluate(thesis, subject=name, findings=findings, proposed_exposure=(
            float(getattr(thesis, "max_exposure", 0.0)) if thesis else 0.0))

        if permission.status != permitted:
            status = INDETERMINATE if permission.status == "INDETERMINATE" else REFUSED
            return Harvest(self.lane, status, permission=permission,
                           reason=reason or f"permission is {permission.status}", **common)

        instruction = self.size(subject, permission)
        if isinstance(instruction, Unworthy):
            return Harvest(self.lane, REFUSED, permission=permission,
                           reason=instruction.reason, **common)
        if instruction is None:
            return Harvest(self.lane, INDETERMINATE, permission=permission, reason=(
                "permitted, and no size could be computed; a constraint was not measured"),
                **common)

        if self.breakers is None:
            # Not an oversight to route around. A lane that can produce a ready
            # instruction with no limits behind it is the thing the breakers exist for.
            return Harvest(self.lane, REFUSED, permission=permission, reason=(
                "no circuit breakers are attached to this lane, so no ring-fence, no "
                "position cap and no kill switch apply. A reaper without them cannot "
                "produce a ready instruction."), **common)

        size, edge = self.measure(instruction) if self.measure else (0.0, 0.0)
        verdict = self.breakers.check(proposed_size=size, claimed_edge_pct=edge)
        if verdict.verdict != "PERMITTED":
            return Harvest(self.lane, REFUSED, instruction=instruction,
                           permission=permission, reason=(
                               f"the breakers blocked it: {', '.join(verdict.blocked_by)}"),
                           **common)

        return Harvest(self.lane, READY, instruction=instruction, permission=permission,
                       **common)
