"""Agent reviewer seats, and the independence rules that make them a board.

Five agents from one model, given the same brief and the same document, will
mostly agree - with each other and with the thing they are reviewing. That is not
five reviews. It is one review with five signatures, and it is more dangerous than
no board because it looks like assurance.

So independence here is structural rather than aspirational:

* each seat carries its own instruction version, and the runtime refuses a board
  whose seats share one;
* the sceptical seat is *given* a brief with the proposed outcome removed, so it
  cannot agree with a conclusion it was never shown;
* the model behind each seat is recorded, and a shared model is recorded as shared
  rather than quietly passed off as two opinions.

A board of agents that never dissents is not providing assurance. Dissent rate is
a health signal, which is why `board_health` reports it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from guards.agent_guard import AgentOutputKind, record_agent_output
from rbe_runtime.canonical import canonical_hash

AGENT_ACTOR_PREFIX = "agent:"

# What each seat is for, in the terms its brief is written in.
SEAT_BRIEFS: dict[str, str] = {
    "MA": "Did this review follow its own methodology? Judge process, not conclusions.",
    "DEA": "Is the evidence real, traceable, and does it support what is claimed of it?",
    "SAA": "Is the architecture sound, and will it hold under change?",
    "QRA": "Does it work, and how would we know? Is it tested where it matters?",
    "BCA": "Is the commercial case honest, or is it wishful?",
    "SPA": "What could leak, break, or expose someone?",
    "POA": "Can this be run at cost without falling over?",
    "SR": "What does this evidence fail to establish? Argue against it.",
}

# The seat whose value depends entirely on not being told the answer first.
BLIND_SEATS = frozenset({"SR"})


class SeatConfigurationError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class AgentSeat:
    role: str
    model: str
    instruction_version: str
    name: str = ""

    @property
    def actor(self) -> str:
        return f"{AGENT_ACTOR_PREFIX}{self.name or self.role.lower()}"

    @property
    def brief(self) -> str:
        return SEAT_BRIEFS.get(self.role, "Review this material against your specification.")

    @property
    def is_blind(self) -> bool:
        return self.role in BLIND_SEATS

    def method(self) -> str:
        """Recorded on every report so a reader knows what produced it."""

        return f"{self.model}/{self.instruction_version}"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.update(actor=self.actor, method=self.method(), blind=self.is_blind)
        return value


@dataclass(frozen=True, slots=True)
class SeatBrief:
    """What a seat is actually shown. Blind seats get less, by construction."""

    role: str
    question: str
    evidence: tuple[dict[str, Any], ...]
    target: dict[str, Any]
    proposed_outcome: str | None
    blind: bool
    brief_hash: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = [dict(item) for item in self.evidence]
        return value


def require_independent_seats(seats: list[AgentSeat]) -> None:
    """Refuse a board whose seats are not meaningfully different from each other."""

    if not seats:
        raise SeatConfigurationError("NO_AGENT_SEATS", "No agent seats were configured")
    roles = [seat.role for seat in seats]
    if len(roles) != len(set(roles)):
        raise SeatConfigurationError(
            "DUPLICATE_SEAT_ROLE", "A role is held by more than one agent seat"
        )
    actors = [seat.actor for seat in seats]
    if len(actors) != len(set(actors)):
        raise SeatConfigurationError(
            "DUPLICATE_SEAT_ACTOR", "Two seats share an actor identity"
        )
    versions = [seat.instruction_version for seat in seats]
    if len(versions) != len(set(versions)):
        raise SeatConfigurationError(
            "SHARED_INSTRUCTION_VERSION",
            "Seats share an instruction version, so they are not independent reviewers",
            {"instruction_versions": sorted(versions)},
        )


def shared_model_note(seats: list[AgentSeat]) -> str | None:
    """State plainly when seats share a model, rather than leaving it unsaid."""

    models = {seat.model for seat in seats}
    if len(models) < len(seats):
        return (
            "Seats share a model, so their reviews are correlated to that extent: "
            + ", ".join(sorted(models))
        )
    return None


def build_brief(
    seat: AgentSeat,
    *,
    target: dict[str, Any],
    evidence: list[dict[str, Any]],
    proposed_outcome: str | None,
) -> SeatBrief:
    """Assemble what a seat sees.

    For a blind seat the proposed outcome is dropped here, at the point the brief
    is built, rather than being passed along with an instruction not to look at
    it. A seat cannot rubber-stamp a conclusion it never received.
    """

    blind = seat.is_blind
    visible_outcome = None if blind else proposed_outcome
    visible_target = dict(target)
    if blind:
        for key in ("proposed_outcome", "outcome", "recommendation", "verdict", "conclusion"):
            visible_target.pop(key, None)
    payload = {
        "role": seat.role,
        "question": seat.brief,
        "evidence": evidence,
        "target": visible_target,
        "proposed_outcome": visible_outcome,
    }
    return SeatBrief(
        role=seat.role,
        question=seat.brief,
        evidence=tuple(evidence),
        target=visible_target,
        proposed_outcome=visible_outcome,
        blind=blind,
        brief_hash=canonical_hash(payload),
    )


def seat_output(
    seat: AgentSeat,
    *,
    summary: str,
    body: dict[str, Any],
    evidence_ids: tuple[str, ...],
    verified_by: str,
    verified_at: str,
    produced_at: str | None = None,
):
    """Record a seat's work as agent output - analysis, never evidence."""

    return record_agent_output(
        agent_id=seat.actor,
        model=seat.model,
        instruction_version=seat.instruction_version,
        kind=AgentOutputKind.ANALYSIS,
        summary=summary,
        body=body,
        input_evidence_ids=evidence_ids,
        produced_at=produced_at,
        human_reviewed_by=verified_by,
        human_reviewed_at=verified_at,
    )


def board_health(seat_findings: dict[str, int]) -> dict[str, Any]:
    """A board that never dissents is not providing assurance.

    `seat_findings` maps role to the number of challenges that seat raised.
    """

    total = sum(seat_findings.values())
    silent = sorted(role for role, count in seat_findings.items() if count == 0)
    return {
        "seats": len(seat_findings),
        "challenges_raised": total,
        "silent_seats": silent,
        "dissent_observed": total > 0,
        "note": (
            "No seat raised a challenge. Treat this as a signal about the board, "
            "not a clean bill of health for the target."
            if total == 0
            else f"{total} challenge(s) raised across {len(seat_findings)} seat(s)."
        ),
    }
