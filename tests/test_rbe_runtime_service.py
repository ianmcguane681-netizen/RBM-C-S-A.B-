from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError
from rbe_runtime.models import ExecutionMode
from rbe_runtime.repository import SQLiteRepository
from rbe_runtime.service import RBERuntime
from rbe_runtime.state_machine import CanonicalStateMachine
from rbe_runtime.storage import ReviewStore


NOW = "2026-07-20T12:00:00Z"


def test_runtime_accepts_repository_through_storage_port(tmp_path: Path) -> None:
    authority = AuthorityBundle.load()
    state_machine = CanonicalStateMachine.from_register(authority.state_machine)
    repository = SQLiteRepository(
        tmp_path / "injected.sqlite3",
        state_machine,
        clock=lambda: NOW,
    )

    assert isinstance(repository, ReviewStore)
    runtime = RBERuntime(
        authority=authority,
        clock=lambda: NOW,
        repository=repository,
    )
    assert runtime.repository is repository


def initiation(authority: AuthorityBundle, review_id: str) -> dict[str, Any]:
    profile = authority.profile
    return {
        "schema_version": "2.2.0",
        "review_id": review_id,
        "review_date": NOW,
        "trigger": "RBE runtime golden scenario",
        "tier": 1,
        "tier_rationale": "Foundation runtime review fixture",
        "artefact_sha": "abcdef1234567890",
        "repository": "ianmcguane681-netizen/Project-Xchange",
        "architecture_authority": "RBE-001 v1.1.0",
        "methodology_profile_id": profile["profile_id"],
        "methodology_version": profile["version"],
        "methodology_status": profile["status"],
        "methodology_checksum": profile["checksum"],
        "manifest_root_sha256": authority.profile_manifest["root_sha256"],
        "human_approval_record": profile["human_approval_record"],
        "binding": profile["binding"],
        "board_chair": "human-chair",
        "methodology_auditor": "human-ma",
        "sceptical_reviewer": "human-sr",
        "specialists": {
            "saa": "human-saa",
            "bca": None,
            "dea": None,
            "qra": "human-qra",
            "spa": None,
            "poa": None,
        },
        "input_process_status": "READY",
    }


def report_record(
    review_id: str,
    role: str,
    actor: str,
    spec_id: str,
    *,
    finding_ids: tuple[str, ...] = (),
    evidence_sufficiency: str = "SUFFICIENT",
) -> dict[str, Any]:
    return {
        "schema_version": "2.2.0",
        "report_id": f"RPT-{review_id}-{role}",
        "review_id": review_id,
        "reviewer": actor,
        "reviewer_role": role,
        "reviewer_spec_id": spec_id,
        "reviewer_spec_version": "2.2.0",
        "artefact_sha": "abcdef1234567890",
        "finding_ids": list(finding_ids),
        "evidence_sufficiency": evidence_sufficiency,
        "missing_evidence": (
            ["Additional reproducible evidence is required."]
            if evidence_sufficiency == "INSUFFICIENT"
            else []
        ),
        "ai_assistance": {
            "used": False,
            "human_verified": False,
            "method": None,
        },
        "human_signature_ref": f"SIG-{review_id}-{role}",
    }


def finding_record(review_id: str, finding_id: str, severity: str) -> dict[str, Any]:
    return {
        "schema_version": "2.2.0",
        "finding_id": finding_id,
        "review_id": review_id,
        "reviewer": "human-saa",
        "reviewer_role": "SAA",
        "artefact_version": "abcdef1234567890",
        "date_raised": NOW,
        "severity": severity,
        "spec_reference": "RBS-002 section 7",
        "title": f"{severity} deterministic fixture",
        "detail": "The preserved evidence demonstrates the scoped finding.",
        "evidence_tier": "T1",
        "evidence_reference": f"EVI-{review_id}",
        "ai_assistance": {
            "used": False,
            "description": None,
            "human_verified": False,
        },
        "status": "OPEN",
        "remediation_requirement": (
            "Provide controlled resolution evidence."
            if severity in {"SEV-1", "SEV-2"}
            else None
        ),
        "target_resolution_date": (
            "2026-08-01" if severity in {"SEV-1", "SEV-2"} else None
        ),
        "closure": None,
    }


def advance(
    runtime: RBERuntime,
    review_id: str,
    target: str,
    sequence: int,
) -> None:
    runtime.advance(
        review_id,
        target,
        actor="human-chair",
        idempotency_key=f"state-{sequence:02d}-{target}",
    )


def prepare_to_consolidation(
    runtime: RBERuntime,
    review_id: str,
    *,
    severity: str | None = None,
    insufficient: bool = False,
    repository: str | None = None,
) -> None:
    record = initiation(runtime.authority, review_id)
    if repository is not None:
        # So a test can build two reviews of DIFFERENT subjects in one store, which
        # supersession needs in order to prove it refuses to link them.
        record = {**record, "repository": repository}
    runtime.initiate_review(
        record,
        actor="human-chair",
        idempotency_key="initiate",
        execution_mode=ExecutionMode.ADVISORY_DRY_RUN,
    )
    advance(runtime, review_id, "SUBMITTED", 1)
    advance(runtime, review_id, "INTAKE_VALIDATION", 2)
    advance(runtime, review_id, "ACCEPTED", 3)
    runtime.register_evidence(
        review_id,
        reference_id=f"EVI-{review_id}",
        locator="repo://src/reviewed.py#L1-L4",
        content=b"controlled golden evidence",
        description="Golden scenario source excerpt",
        source_tier="T1",
        provenance={"commit": "abcdef1234567890", "captured_by": "human-chair"},
        actor="human-chair",
        idempotency_key="evidence",
    )
    advance(runtime, review_id, "EVIDENCE_LOCKED", 4)
    advance(runtime, review_id, "ASSIGNMENT", 5)
    assignments = runtime.repository.list_assignments(review_id)
    for assignment in assignments:
        runtime.respond_to_assignment(
            review_id,
            assignment.assignment_id,
            actor=assignment.reviewer_actor,
            has_material_conflict=False,
            conflict_basis=None,
            human_signature_ref=f"SIG-IND-{assignment.reviewer_role}",
            idempotency_key=f"accept-{assignment.reviewer_role}",
        )
    advance(runtime, review_id, "INDEPENDENT_REVIEW", 6)

    assignments_by_role = {
        item.reviewer_role: item
        for item in runtime.repository.list_assignments(review_id)
    }
    for role in ("QRA", "SAA"):
        assignment = assignments_by_role[role]
        finding_id = f"FND-{review_id}-001" if role == "SAA" and severity else None
        findings = (
            (finding_record(review_id, finding_id, severity),)
            if finding_id and severity
            else ()
        )
        runtime.submit_report(
            review_id,
            assignment.assignment_id,
            raw_report=report_record(
                review_id,
                role,
                assignment.reviewer_actor,
                assignment.reviewer_spec_id,
                finding_ids=((finding_id,) if finding_id else ()),
                evidence_sufficiency=(
                    "INSUFFICIENT" if insufficient and role == "SAA" else "SUFFICIENT"
                ),
            ),
            raw_findings=findings,
            finding_categories=(
                {finding_id: "ARCHITECTURE"} if finding_id else {}
            ),
            summary=f"{role} completed the scoped review.",
            recommendation=("Corrective" if finding_id else "Monitoring"),
            evidence_reference_ids=(f"EVI-{review_id}",),
            actor=assignment.reviewer_actor,
            idempotency_key=f"report-{role}",
        )
    advance(runtime, review_id, "CHALLENGE", 7)
    for role in ("SR", "MA"):
        assignment = assignments_by_role[role]
        runtime.submit_report(
            review_id,
            assignment.assignment_id,
            raw_report=report_record(
                review_id,
                role,
                assignment.reviewer_actor,
                assignment.reviewer_spec_id,
                evidence_sufficiency="NOT_APPLICABLE",
            ),
            raw_findings=(),
            finding_categories={},
            summary=f"{role} completed the governed review function.",
            recommendation="Monitoring",
            evidence_reference_ids=(f"EVI-{review_id}",),
            actor=assignment.reviewer_actor,
            idempotency_key=f"report-{role}",
        )
    advance(runtime, review_id, "CONSOLIDATION", 8)


@pytest.mark.parametrize(
    ("scenario", "severity", "insufficient", "expected"),
    [
        ("pass", None, False, "PASS"),
        ("fail", "SEV-1", False, "FAIL"),
        ("insufficient", None, True, "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_ready_golden_scenarios(
    tmp_path: Path,
    scenario: str,
    severity: str | None,
    insufficient: bool,
    expected: str,
) -> None:
    review_id = f"REV-GOLDEN-{scenario.upper()}"
    runtime = RBERuntime(tmp_path / f"{scenario}.sqlite3", clock=lambda: NOW)
    prepare_to_consolidation(
        runtime,
        review_id,
        severity=severity,
        insufficient=insufficient,
    )
    candidate = runtime.prepare_decision_candidate(
        review_id,
        actor="human-chair",
        idempotency_key="candidate",
    )
    assert candidate["evaluation"]["outcome"] == expected
    assert candidate["evaluation"]["process_status"] == "READY"


def test_pass_with_findings_requires_validated_remediation(tmp_path: Path) -> None:
    review_id = "REV-GOLDEN-PWF"
    runtime = RBERuntime(tmp_path / "pwf.sqlite3", clock=lambda: NOW)
    prepare_to_consolidation(runtime, review_id, severity="SEV-2")
    finding_id = f"FND-{review_id}-001"

    unremediated = runtime.decisions.evaluate(
        findings=runtime.repository.list_findings(review_id),
        process_status="READY",
        substantive_evidence_sufficient=True,
    )
    assert unremediated.outcome == "FAIL"

    runtime.submit_remediation_plan(
        review_id,
        {
            "schema_version": "2.2.0",
            "document_id": "RMP-DOC-PWF-001",
            "review_id": review_id,
            "authoring_team_contact": "human-owner",
            "date_submitted": NOW,
            "items": [
                {
                    "finding_id": finding_id,
                    "root_cause": "A missing deterministic guard.",
                    "planned_changes": "Add and test the required guard.",
                    "responsible_person": "human-owner",
                    "target_completion_date": "2026-08-01",
                    "planned_resolution_evidence": "Commit and passing test output.",
                }
            ],
            "ma_reviewer": "human-ma",
            "ma_decision": "ACCEPTED",
            "ma_signature_ref": "SIG-MA-RMP-001",
        },
        actor="human-ma",
        idempotency_key="remediation",
    )
    candidate = runtime.prepare_decision_candidate(
        review_id,
        actor="human-chair",
        idempotency_key="candidate",
    )
    assert candidate["evaluation"]["outcome"] == "PASS_WITH_FINDINGS"


def test_blocked_golden_scenario_has_no_outcome(tmp_path: Path) -> None:
    review_id = "REV-GOLDEN-BLOCKED"
    runtime = RBERuntime(tmp_path / "blocked.sqlite3", clock=lambda: NOW)
    prepare_to_consolidation(runtime, review_id)
    candidate = runtime.prepare_decision_candidate(
        review_id,
        actor="human-chair",
        idempotency_key="candidate-blocked",
        process_blockers=("INTEGRITY_REVIEW_REQUIRED",),
    )
    assert candidate["evaluation"]["process_status"] == "BLOCKED"
    assert candidate["evaluation"]["outcome"] is None
    advance(runtime, review_id, "GOVERNANCE_VALIDATION", 9)
    advance(runtime, review_id, "BLOCKED", 10)
    assert runtime.repository.get_session(review_id).status == "BLOCKED"


def test_full_advisory_review_publishes_non_binding_indicator(tmp_path: Path) -> None:
    review_id = "REV-GOLDEN-PUBLISH"
    runtime = RBERuntime(tmp_path / "publish.sqlite3", clock=lambda: NOW)
    prepare_to_consolidation(runtime, review_id)
    runtime.prepare_decision_candidate(
        review_id,
        actor="human-chair",
        idempotency_key="candidate",
    )
    advance(runtime, review_id, "GOVERNANCE_VALIDATION", 9)
    decision = runtime.ratify_decision(
        review_id,
        actor="human-chair",
        board_chair_signature_ref="SIG-BC-001",
        governance_validator="human-ma",
        governance_validation_ref="SIG-MA-GOV-001",
        idempotency_key="ratify",
    )
    assert decision["binding"] is False
    assert decision["merge_permitted"] is False
    advance(runtime, review_id, "DECIDED", 10)
    publication = runtime.publish_decision(
        review_id,
        actor="human-publication",
        idempotency_key="publish",
    )
    indicator = publication["indicator"]
    assert indicator["methodology_status"] == "RELEASE_CANDIDATE"
    assert indicator["binding"] is False
    assert indicator["merge_permitted"] is False
    advance(runtime, review_id, "PUBLISHED", 11)
    assert runtime.repository.get_session(review_id).status == "PUBLISHED"
    assert runtime.repository.verify_audit(review_id)["valid"] is True


def test_stage_guards_prevent_late_evidence_and_early_review(tmp_path: Path) -> None:
    review_id = "REV-GUARDS"
    runtime = RBERuntime(tmp_path / "guards.sqlite3", clock=lambda: NOW)
    runtime.initiate_review(
        initiation(runtime.authority, review_id),
        actor="human-chair",
        idempotency_key="initiate",
    )
    advance(runtime, review_id, "SUBMITTED", 1)
    with pytest.raises(RBEError, match="not reachable"):
        advance(runtime, review_id, "ACCEPTED", 2)
    advance(runtime, review_id, "INTAKE_VALIDATION", 3)
    advance(runtime, review_id, "ACCEPTED", 4)
    runtime.register_evidence(
        review_id,
        locator="repo://evidence",
        content=b"evidence",
        description="Evidence",
        source_tier="T1",
        provenance={"commit": "abcdef1234567890"},
        actor="human-chair",
        idempotency_key="evidence",
    )
    advance(runtime, review_id, "EVIDENCE_LOCKED", 5)
    with pytest.raises(RBEError, match="after the evidence lock"):
        runtime.register_evidence(
            review_id,
            locator="repo://late",
            content=b"late",
            description="Late evidence",
            source_tier="T1",
            provenance={"commit": "abcdef1234567890"},
            actor="human-chair",
            idempotency_key="late-evidence",
        )


def test_returned_review_requires_immutable_successor_package(tmp_path: Path) -> None:
    review_id = "REV-RETURNED-001"
    runtime = RBERuntime(tmp_path / "returned.sqlite3", clock=lambda: NOW)
    original = initiation(runtime.authority, review_id)
    original["input_process_status"] = "PROCEDURALLY_INCOMPLETE"
    runtime.initiate_review(
        original,
        actor="human-chair",
        idempotency_key="initiate",
    )
    advance(runtime, review_id, "SUBMITTED", 1)
    advance(runtime, review_id, "INTAKE_VALIDATION", 2)
    advance(runtime, review_id, "RETURNED", 3)
    with pytest.raises(RBEError, match="SUCCESSOR_SUBMISSION_REQUIRED"):
        runtime.advance(
            review_id,
            "SUBMITTED",
            actor="human-chair",
            idempotency_key="premature-resubmit",
            metadata={"successor_package_id": "PKG-NOT-REGISTERED"},
        )

    successor = copy.deepcopy(original)
    successor["input_process_status"] = "READY"
    successor["review_date"] = "2026-07-20T13:00:00Z"
    package = runtime.resubmit_review_package(
        review_id,
        successor,
        actor="human-chair",
        idempotency_key="successor-package",
    )
    runtime.advance(
        review_id,
        "SUBMITTED",
        actor="human-chair",
        idempotency_key="accepted-resubmit",
        metadata={"successor_package_id": package["package_id"]},
    )
    latest = runtime.repository.get_latest_package(review_id)
    assert latest["package_version"] == 2
    assert latest["raw_record"]["input_process_status"] == "READY"
