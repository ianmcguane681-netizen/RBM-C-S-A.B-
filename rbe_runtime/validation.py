"""Cross-record validation for RBE sessions and RBM records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.constants import RBE_RELEASE
from rbe_runtime.canonical import canonical_hash, deterministic_id
from rbe_runtime.errors import RBEError
from rbe_runtime.models import (
    ExecutionMode,
    EvidenceReference,
    ReviewAssignment,
    ReviewerReport,
    ReviewSession,
    Finding,
    RemediationPlan,
)
from rbe_runtime.profile import ProfilePolicy, RoleSeat, is_agent_actor
from rbe_runtime.schemas import SchemaRegistry


RECOMMENDATION_TYPES = frozenset(
    {
        "Corrective",
        "Research",
        "Control",
        "Monitoring",
        "No-build / stop",
        "Proceed to next gate",
    }
)


def validate_initiation(
    authority: AuthorityBundle,
    schemas: SchemaRegistry,
    policy: ProfilePolicy,
    initiation: dict[str, Any],
    execution_mode: ExecutionMode,
) -> tuple[RoleSeat, ...]:
    schemas.validate("tpl-rir", initiation)
    authority.require_execution_mode(execution_mode)
    profile = authority.profile
    manifest = authority.profile_manifest
    expected = {
        "architecture_authority": f"RBE-001 v{RBE_RELEASE}",
        "methodology_profile_id": profile["profile_id"],
        "methodology_version": profile["version"],
        "methodology_status": profile["status"],
        "methodology_checksum": profile["checksum"],
        "manifest_root_sha256": manifest["root_sha256"],
        "human_approval_record": profile["human_approval_record"],
        "binding": profile["binding"],
    }
    mismatches = {
        field: {"expected": value, "received": initiation.get(field)}
        for field, value in expected.items()
        if initiation.get(field) != value
    }
    if mismatches:
        raise RBEError(
            "RBE_INITIATION_AUTHORITY_MISMATCH",
            "The initiation record does not match the loaded authority bundle",
            "RBE-ES-DEC-002",
            {"fields": mismatches},
        )
    if execution_mode == ExecutionMode.ADVISORY_DRY_RUN and initiation["binding"]:
        raise RBEError(
            "RBE_ADVISORY_BINDING_FORBIDDEN",
            "An advisory dry run cannot claim binding authority",
            "RBE-ES-DEC-002",
        )
    return policy.plan_roles(initiation)


def require_known_evidence(
    reference_ids: Iterable[str], evidence: Mapping[str, EvidenceReference]
) -> tuple[str, ...]:
    ids = tuple(reference_ids)
    unknown = sorted(set(ids) - set(evidence))
    if unknown:
        raise RBEError(
            "RBE_UNKNOWN_EVIDENCE_REFERENCE",
            "A record references evidence that is not registered in the session",
            "RBE-ES-ORC-007",
            {"reference_ids": unknown},
        )
    return ids


def validate_report_submission(
    schemas: SchemaRegistry,
    policy: ProfilePolicy,
    *,
    session: ReviewSession,
    assignment: ReviewAssignment,
    evidence: Mapping[str, EvidenceReference],
    raw_record: dict[str, Any],
    summary: str,
    recommendation: str,
    evidence_reference_ids: Iterable[str],
) -> tuple[str, ...]:
    schemas.validate("tpl-rrr", raw_record)
    if not summary.strip() or recommendation not in RECOMMENDATION_TYPES:
        raise RBEError(
            "RBE_REPORT_ENVELOPE_INVALID",
            "RBE report summary and a canonical non-binding recommendation are required",
            "RBE-ES-DOM-001",
            {"permitted_recommendations": sorted(RECOMMENDATION_TYPES)},
        )
    if assignment.session_id != session.session_id:
        raise RBEError(
            "RBE_ASSIGNMENT_SESSION_MISMATCH",
            "The assignment does not belong to the report session",
            "RBE-ES-DOM-001",
        )
    if assignment.status != "ACCEPTED":
        raise RBEError(
            "RBE_ASSIGNMENT_NOT_ACCEPTED",
            "Reports may be submitted only for accepted assignments",
            "RBE-ES-ORC-006",
            {"assignment_status": assignment.status},
        )
    expected = {
        "review_id": session.session_id,
        "reviewer": assignment.reviewer_actor,
        "reviewer_role": assignment.reviewer_role,
        "reviewer_spec_id": assignment.reviewer_spec_id,
        "reviewer_spec_version": session.methodology_version,
        "artefact_sha": session.target_version,
    }
    mismatches = {
        field: {"expected": value, "received": raw_record.get(field)}
        for field, value in expected.items()
        if raw_record.get(field) != value
    }
    if mismatches:
        raise RBEError(
            "RBE_REPORT_CROSS_RECORD_MISMATCH",
            "Reviewer report identity does not match its session or assignment",
            "RBE-ES-ORC-006",
            {"fields": mismatches},
        )
    policy.require_role_spec(assignment.reviewer_role, raw_record["reviewer_spec_id"])
    ai = raw_record["ai_assistance"]
    if not isinstance(ai.get("used"), bool):
        raise RBEError(
            "RBE_AI_ASSISTANCE_UNDECLARED",
            "Reviewer reports must explicitly declare whether AI assistance was used",
            "RBE-ES-DES-002",
        )
    ai_used = ai["used"]
    if ai_used and ai.get("human_verified") is not True:
        raise RBEError(
            "RBE_AI_REPORT_UNVERIFIED",
            "AI-assisted report material requires explicit human verification",
            "RBE-ES-FUT-002",
        )
    if is_agent_actor(assignment.reviewer_actor):
        # An agent-held seat cannot file a report claiming a human wrote it.
        if not ai_used:
            raise RBEError(
                "RBE_AGENT_SEAT_MUST_DECLARE_AI",
                "A report from an agent-held seat must declare AI assistance",
                "RBE-ES-DES-002",
                {"role": assignment.reviewer_role},
            )
        if not str(ai.get("method") or "").strip():
            raise RBEError(
                "RBE_AGENT_SEAT_METHOD_REQUIRED",
                "An agent-held seat must record the model and instruction version",
                "RBE-ES-DES-002",
                {"role": assignment.reviewer_role},
            )
    elif raw_record["reviewer"].lower().startswith(("ai:", "model:")):
        raise RBEError(
            "RBE_AI_REVIEWER_NON_AUTHORITATIVE",
            "An AI actor cannot hold an authoritative reviewer assignment",
            "RBE-ES-DES-002",
        )
    return require_known_evidence(evidence_reference_ids, evidence)


def validate_finding_submission(
    schemas: SchemaRegistry,
    *,
    session: ReviewSession,
    source_report: ReviewerReport,
    assignment: ReviewAssignment,
    evidence: Mapping[str, EvidenceReference],
    raw_record: dict[str, Any],
) -> tuple[str, ...]:
    schemas.validate("tpl-fnd", raw_record)
    expected = {
        "review_id": session.session_id,
        "reviewer": assignment.reviewer_actor,
        "reviewer_role": assignment.reviewer_role,
        "artefact_version": session.target_version,
    }
    mismatches = {
        field: {"expected": value, "received": raw_record.get(field)}
        for field, value in expected.items()
        if raw_record.get(field) != value
    }
    if source_report.assignment_id != assignment.assignment_id:
        mismatches["source_report.assignment_id"] = {
            "expected": assignment.assignment_id,
            "received": source_report.assignment_id,
        }
    if raw_record["finding_id"] not in source_report.finding_ids:
        mismatches["finding_id"] = {
            "expected": "an ID declared by the source report",
            "received": raw_record["finding_id"],
        }
    if mismatches:
        raise RBEError(
            "RBE_FINDING_CROSS_RECORD_MISMATCH",
            "Finding identity does not match its source report or assignment",
            "RBE-ES-DOM-002",
            {"fields": mismatches},
        )
    ai = raw_record["ai_assistance"]
    if ai["used"] and not ai["human_verified"]:
        raise RBEError(
            "RBE_AI_FINDING_UNVERIFIED",
            "AI-assisted finding material requires explicit human verification",
            "RBE-ES-FUT-002",
        )
    reference_ids = require_known_evidence(
        [raw_record["evidence_reference"]], evidence
    )
    if not set(reference_ids).issubset(source_report.evidence_reference_ids):
        raise RBEError(
            "RBE_FINDING_EVIDENCE_NOT_IN_REPORT",
            "Finding evidence must be declared by its source report",
            "RBE-ES-DOM-002",
        )
    return reference_ids


def validate_remediation_submission(
    schemas: SchemaRegistry,
    *,
    session: ReviewSession,
    methodology_auditor: str,
    findings: Mapping[str, Finding],
    raw_record: dict[str, Any],
) -> tuple[RemediationPlan, ...]:
    schemas.validate("tpl-rmp", raw_record)
    mismatches: dict[str, Any] = {}
    if raw_record["review_id"] != session.session_id:
        mismatches["review_id"] = {
            "expected": session.session_id,
            "received": raw_record["review_id"],
        }
    if raw_record["ma_reviewer"] != methodology_auditor:
        mismatches["ma_reviewer"] = {
            "expected": methodology_auditor,
            "received": raw_record["ma_reviewer"],
        }
    item_ids = [item["finding_id"] for item in raw_record["items"]]
    if len(item_ids) != len(set(item_ids)):
        mismatches["items.finding_id"] = "finding IDs must be unique"
    unknown = sorted(set(item_ids) - set(findings))
    if unknown:
        mismatches["items.finding_id.unknown"] = unknown
    if mismatches:
        raise RBEError(
            "RBE_REMEDIATION_CROSS_RECORD_MISMATCH",
            "Remediation plan does not match its session, auditor, or findings",
            "RBE-ES-DOM-002",
            {"fields": mismatches},
        )
    raw_hash = canonical_hash(raw_record)
    status = raw_record["ma_decision"]
    return tuple(
        RemediationPlan(
            plan_id=deterministic_id(
                "RMP", session.session_id, raw_record["document_id"], item["finding_id"]
            ),
            document_id=raw_record["document_id"],
            session_id=session.session_id,
            finding_id=item["finding_id"],
            owner=item["responsible_person"],
            action=item["planned_changes"],
            due_date=item["target_completion_date"],
            status=status,
            verification_evidence_ids=(),
            raw_record=raw_record,
            raw_record_sha256=raw_hash,
            created_at=raw_record["date_submitted"],
        )
        for item in sorted(raw_record["items"], key=lambda value: value["finding_id"])
    )
