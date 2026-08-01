"""Source-agnostic domain records for the RBE Foundation runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ExecutionMode(StrEnum):
    ADVISORY_DRY_RUN = "ADVISORY_DRY_RUN"
    BINDING_LIVE = "BINDING_LIVE"


class ProcessStatus(StrEnum):
    READY = "READY"
    PROCEDURALLY_INCOMPLETE = "PROCEDURALLY_INCOMPLETE"
    BLOCKED = "BLOCKED"
    VOID = "VOID"


class Outcome(StrEnum):
    PASS = "PASS"
    PASS_WITH_FINDINGS = "PASS_WITH_FINDINGS"
    FAIL = "FAIL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DEFER_FOR_FURTHER_RESEARCH = "DEFER_FOR_FURTHER_RESEARCH"


class AssignmentStatus(StrEnum):
    PLANNED = "PLANNED"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


class DecisionStatus(StrEnum):
    DRAFT_CANDIDATE = "DRAFT_CANDIDATE"
    SIGNED = "SIGNED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class FindingStatus(StrEnum):
    OPEN = "OPEN"
    CONTESTED = "CONTESTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"
    WITHDRAWN = "WITHDRAWN"
    WAIVED = "WAIVED"


@dataclass(frozen=True, slots=True)
class ReadinessAssessment:
    process_status: str
    unmet_prerequisites: tuple[str, ...]
    process_blockers: tuple[str, ...]
    substantive_evidence_sufficient: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["unmet_prerequisites"] = list(self.unmet_prerequisites)
        value["process_blockers"] = list(self.process_blockers)
        return value


@dataclass(frozen=True, slots=True)
class ReviewSession:
    session_id: str
    target_type: str
    target_id: str
    target_version: str
    methodology_id: str
    methodology_version: str
    methodology_checksum: str
    engine_version: str
    schema_version: str
    status: str
    aggregate_version: int
    execution_mode: str
    binding: bool
    created_at: str
    created_by: str
    completed_at: str | None = None
    parent_session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    reference_id: str
    session_id: str
    reference_type: str
    locator: str
    content_sha256: str
    description: str
    source_tier: str | None
    provenance: dict[str, Any]
    registered_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewAssignment:
    assignment_id: str
    session_id: str
    reviewer_role: str
    reviewer_actor: str
    reviewer_spec_id: str
    status: str
    sequence: int
    required: bool
    conflict_declared: bool
    has_material_conflict: bool
    assigned_at: str
    accepted_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewerReport:
    report_id: str
    session_id: str
    assignment_id: str
    report_version: int
    raw_record: dict[str, Any]
    raw_record_sha256: str
    summary: str
    recommendation: str
    finding_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    ai_assisted: bool
    human_verified: bool
    human_signature_ref: str
    submitted_at: str
    supersedes_report_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["finding_ids"] = list(self.finding_ids)
        value["evidence_reference_ids"] = list(self.evidence_reference_ids)
        return value


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    session_id: str
    source_report_id: str
    severity: str
    category: str
    title: str
    description: str
    evidence_reference_ids: tuple[str, ...]
    status: str
    remediation_required: bool
    raw_record: dict[str, Any]
    raw_record_sha256: str
    created_at: str
    supersedes_finding_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_reference_ids"] = list(self.evidence_reference_ids)
        return value


@dataclass(frozen=True, slots=True)
class RemediationPlan:
    plan_id: str
    document_id: str
    session_id: str
    finding_id: str
    owner: str
    action: str
    due_date: str | None
    status: str
    verification_evidence_ids: tuple[str, ...]
    raw_record: dict[str, Any]
    raw_record_sha256: str
    created_at: str
    supersedes_plan_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["verification_evidence_ids"] = list(self.verification_evidence_ids)
        return value


@dataclass(frozen=True, slots=True)
class DecisionEvaluation:
    process_status: str
    outcome: str | None
    reason_codes: tuple[str, ...]
    rules_applied: tuple[str, ...]
    findings_considered: tuple[str, ...]
    counter_evidence: tuple[str, ...]
    process_blockers: tuple[str, ...]
    profile_id: str
    profile_version: str
    profile_checksum: str
    engine_version: str
    snapshot_hash: str
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for field_name in (
            "reason_codes",
            "rules_applied",
            "findings_considered",
            "counter_evidence",
            "process_blockers",
        ):
            value[field_name] = list(value[field_name])
        return value


@dataclass(frozen=True, slots=True)
class BoardDecision:
    decision_id: str
    session_id: str
    status: str
    binding: bool
    merge_permitted: bool
    execution_mode: str
    evaluation: DecisionEvaluation
    finding_snapshot_hash: str
    artifact_manifest_hash: str
    computed_at: str
    signed_at: str | None = None
    published_at: str | None = None
    published_by: str | None = None
    superseded: bool = False
    # True when one human ratified alone because the four-eyes control could not
    # be satisfied. Recorded permanently so the decision is never mistaken for a
    # two-signature one.
    single_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evaluation"] = self.evaluation.to_dict()
        return value


@dataclass(frozen=True, slots=True)
class AuditEntry:
    audit_id: str
    session_id: str
    sequence: int
    event_type: str
    actor: str
    occurred_at: str
    payload: dict[str, Any]
    previous_hash: str | None
    entry_hash: str
    schema_id: str = "rbe.audit-entry"
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
