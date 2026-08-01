"""Agent output is analysis or a proposal. It is never evidence.

The governing rule is already written down: AI may propose, evidence must prove,
proof gates must decide. That rule holds today only because AI is switched off. It
will come under real pressure the moment agents are good enough to be useful,
because an agent's summary of a complaint looks very much like a finding.

This module makes the rule structural. Agent output is carried by types that
cannot be mistaken for evidence, and `assert_not_evidence` refuses any object that
tries to enter an evidence position while carrying agent provenance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from rbe_runtime.canonical import canonical_hash, deterministic_id, utc_now

AGENT_METHOD_PREFIX = "agent:"


class AgentOutputKind(StrEnum):
    """What an agent produced. Neither value is ever evidence."""

    ANALYSIS = "ANALYSIS"
    PROPOSAL = "PROPOSAL"


class AgentGovernanceError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class AgentOutput:
    """Something an agent said, recorded so it can never be cited as proof."""

    output_id: str
    agent_id: str
    model: str
    instruction_version: str
    kind: str
    summary: str
    body: dict[str, Any]
    input_evidence_ids: tuple[str, ...]
    produced_at: str
    human_reviewed_by: str = ""
    human_reviewed_at: str = ""
    # Fixed, not a parameter. There is no configuration under which agent output
    # becomes evidence, so this is not something a caller can flip.
    is_evidence: bool = field(default=False, init=False)

    @property
    def method_used(self) -> str:
        # Agent ids often already carry the prefix (a board seat's actor is
        # "agent:sr"), so do not stack a second one onto it.
        if self.agent_id.startswith(AGENT_METHOD_PREFIX):
            return self.agent_id
        return f"{AGENT_METHOD_PREFIX}{self.agent_id}"

    @property
    def human_reviewed(self) -> bool:
        return bool(self.human_reviewed_by.strip() and self.human_reviewed_at.strip())

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["input_evidence_ids"] = list(self.input_evidence_ids)
        value["method_used"] = self.method_used
        value["human_reviewed"] = self.human_reviewed
        value["is_evidence"] = False
        return value


def record_agent_output(
    *,
    agent_id: str,
    model: str,
    instruction_version: str,
    kind: AgentOutputKind,
    summary: str,
    body: dict[str, Any],
    input_evidence_ids: tuple[str, ...] = (),
    produced_at: str | None = None,
    human_reviewed_by: str = "",
    human_reviewed_at: str = "",
) -> AgentOutput:
    if not agent_id.strip() or not model.strip() or not instruction_version.strip():
        raise AgentGovernanceError(
            "AGENT_PROVENANCE_INCOMPLETE",
            "Agent output must name the agent, the model, and the instruction version",
        )
    if not summary.strip():
        raise AgentGovernanceError(
            "AGENT_OUTPUT_EMPTY", "Agent output must carry a human-readable summary"
        )
    timestamp = produced_at or utc_now()
    return AgentOutput(
        output_id=deterministic_id(
            "AGT", agent_id, instruction_version, timestamp, canonical_hash(body)
        ),
        agent_id=agent_id,
        model=model,
        instruction_version=instruction_version,
        kind=str(kind),
        summary=summary,
        body=body,
        input_evidence_ids=tuple(sorted(input_evidence_ids)),
        produced_at=timestamp,
        human_reviewed_by=human_reviewed_by,
        human_reviewed_at=human_reviewed_at,
    )


def carries_agent_provenance(candidate: Any) -> bool:
    """True when an object originated from an agent, however it is wrapped."""

    if isinstance(candidate, AgentOutput):
        return True
    if isinstance(candidate, dict):
        method = str(candidate.get("method_used") or candidate.get("method") or "")
        if method.startswith(AGENT_METHOD_PREFIX):
            return True
        return bool(candidate.get("agent_id"))
    return str(getattr(candidate, "method_used", "")).startswith(AGENT_METHOD_PREFIX)


def assert_not_evidence(candidate: Any, *, position: str = "evidence") -> None:
    """Refuse agent output entering a position that requires evidence.

    Call this at the boundary of anything that treats its input as proof. A
    reviewer reading an artifact should never have to work out whether a finding
    was substantiated or merely generated.
    """

    if carries_agent_provenance(candidate):
        raise AgentGovernanceError(
            "AGENT_OUTPUT_IS_NOT_EVIDENCE",
            f"Agent output cannot be used as {position}; record it as analysis or a proposal",
            {"position": position},
        )


def require_human_review(output: AgentOutput) -> AgentOutput:
    """Gate a proposal on a named human having actually looked at it."""

    if not output.human_reviewed:
        raise AgentGovernanceError(
            "AGENT_PROPOSAL_UNREVIEWED",
            "An agent proposal requires a named human reviewer before it can be acted on",
            {"output_id": output.output_id},
        )
    return output
