from __future__ import annotations

import copy

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError
from rbe_runtime.models import (
    EvidenceReference,
    ExecutionMode,
    ReviewAssignment,
    ReviewerReport,
    ReviewSession,
)
from rbe_runtime.profile import ProfilePolicy
from rbe_runtime.schemas import SchemaRegistry
from rbe_runtime.validation import (
    validate_finding_submission,
    validate_initiation,
    validate_report_submission,
)


@pytest.fixture(scope="module")
def authority() -> AuthorityBundle:
    return AuthorityBundle.load()


@pytest.fixture(scope="module")
def schemas(authority: AuthorityBundle) -> SchemaRegistry:
    return SchemaRegistry.from_authority(authority)


@pytest.fixture(scope="module")
def policy(authority: AuthorityBundle) -> ProfilePolicy:
    return ProfilePolicy.from_authority(authority)


def valid_initiation(authority: AuthorityBundle) -> dict[str, object]:
    profile = authority.profile
    return {
        "schema_version": "2.2.0",
        "review_id": "REV-RUNTIME-001",
        "review_date": "2026-07-19T09:00:00Z",
        "trigger": "RBE runtime v0.1 implementation review",
        "tier": 1,
        "tier_rationale": "Foundation runtime with no live authority",
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


def valid_session(authority: AuthorityBundle) -> ReviewSession:
    return ReviewSession(
        session_id="REV-RUNTIME-001",
        target_type="GIT_COMMIT",
        target_id="ianmcguane681-netizen/Project-Xchange",
        target_version="abcdef1234567890",
        methodology_id="RBM-001",
        methodology_version="2.2.0",
        methodology_checksum=authority.profile["checksum"],
        engine_version="0.1.0",
        schema_version="1.0.0",
        status="INDEPENDENT_REVIEW",
        aggregate_version=7,
        execution_mode="ADVISORY_DRY_RUN",
        binding=False,
        created_at="2026-07-19T09:00:00Z",
        created_by="human-chair",
    )


def valid_assignment() -> ReviewAssignment:
    return ReviewAssignment(
        assignment_id="ASN-001",
        session_id="REV-RUNTIME-001",
        reviewer_role="SAA",
        reviewer_actor="human-saa",
        reviewer_spec_id="RBS-002",
        status="ACCEPTED",
        sequence=2,
        required=True,
        conflict_declared=True,
        has_material_conflict=False,
        assigned_at="2026-07-19T09:05:00Z",
        accepted_at="2026-07-19T09:06:00Z",
    )


def valid_evidence() -> dict[str, EvidenceReference]:
    evidence = EvidenceReference(
        reference_id="EVI-001",
        session_id="REV-RUNTIME-001",
        reference_type="FILE",
        locator="repo://src/example.py#L1",
        content_sha256="sha256:" + "1" * 64,
        description="Immutable source excerpt",
        source_tier="T1",
        provenance={"commit": "abcdef1234567890", "captured_by": "human-chair"},
        registered_at="2026-07-19T09:02:00Z",
    )
    return {evidence.reference_id: evidence}


def valid_report_record() -> dict[str, object]:
    return {
        "schema_version": "2.2.0",
        "report_id": "RPT-001",
        "review_id": "REV-RUNTIME-001",
        "reviewer": "human-saa",
        "reviewer_role": "SAA",
        "reviewer_spec_id": "RBS-002",
        "reviewer_spec_version": "2.2.0",
        "artefact_sha": "abcdef1234567890",
        "finding_ids": ["FND-001"],
        "evidence_sufficiency": "SUFFICIENT",
        "missing_evidence": [],
        "ai_assistance": {
            "used": False,
            "human_verified": False,
            "method": None,
        },
        "human_signature_ref": "SIG-SAA-001",
    }


def normalized_report() -> ReviewerReport:
    raw = valid_report_record()
    return ReviewerReport(
        report_id="RPT-001",
        session_id="REV-RUNTIME-001",
        assignment_id="ASN-001",
        report_version=1,
        raw_record=raw,
        raw_record_sha256="sha256:" + "2" * 64,
        summary="Architecture controls reviewed against preserved evidence.",
        recommendation="Monitoring",
        finding_ids=("FND-001",),
        evidence_reference_ids=("EVI-001",),
        ai_assisted=False,
        human_verified=True,
        human_signature_ref="SIG-SAA-001",
        submitted_at="2026-07-19T09:10:00Z",
    )


def valid_finding_record() -> dict[str, object]:
    return {
        "schema_version": "2.2.0",
        "finding_id": "FND-001",
        "review_id": "REV-RUNTIME-001",
        "reviewer": "human-saa",
        "reviewer_role": "SAA",
        "artefact_version": "abcdef1234567890",
        "date_raised": "2026-07-19T09:09:00Z",
        "severity": "SEV-3",
        "spec_reference": "RBS-002 section 7",
        "title": "Example traceable finding",
        "detail": "The finding is supported by the registered source excerpt.",
        "evidence_tier": "T1",
        "evidence_reference": "EVI-001",
        "ai_assistance": {
            "used": False,
            "description": None,
            "human_verified": False,
        },
        "status": "OPEN",
        "remediation_requirement": None,
        "target_resolution_date": None,
        "closure": None,
    }


def test_valid_initiation_builds_profile_driven_role_plan(
    authority: AuthorityBundle,
    schemas: SchemaRegistry,
    policy: ProfilePolicy,
) -> None:
    seats = validate_initiation(
        authority,
        schemas,
        policy,
        valid_initiation(authority),
        ExecutionMode.ADVISORY_DRY_RUN,
    )
    assert [seat.role for seat in seats] == ["MA", "QRA", "SAA", "SR"]
    assert [seat.reviewer_spec_id for seat in seats] == [
        "RBS-001",
        "RBS-005",
        "RBS-002",
        "RBS-008",
    ]


def test_initiation_rejects_profile_mismatch_and_unknown_fields(
    authority: AuthorityBundle,
    schemas: SchemaRegistry,
    policy: ProfilePolicy,
) -> None:
    wrong_checksum = valid_initiation(authority)
    wrong_checksum["methodology_checksum"] = "sha256:" + "0" * 64
    with pytest.raises(RBEError, match="authority bundle"):
        validate_initiation(
            authority,
            schemas,
            policy,
            wrong_checksum,
            ExecutionMode.ADVISORY_DRY_RUN,
        )

    extra_field = valid_initiation(authority)
    extra_field["invented_override"] = True
    with pytest.raises(RBEError, match="Additional properties"):
        validate_initiation(
            authority,
            schemas,
            policy,
            extra_field,
            ExecutionMode.ADVISORY_DRY_RUN,
        )


def test_initiation_rejects_quorum_and_role_conflicts(
    authority: AuthorityBundle,
    schemas: SchemaRegistry,
    policy: ProfilePolicy,
) -> None:
    insufficient = valid_initiation(authority)
    insufficient["specialists"]["qra"] = None  # type: ignore[index]
    with pytest.raises(RBEError, match="requires 2 specialists"):
        validate_initiation(
            authority,
            schemas,
            policy,
            insufficient,
            ExecutionMode.ADVISORY_DRY_RUN,
        )

    duplicate = valid_initiation(authority)
    duplicate["sceptical_reviewer"] = "human-ma"
    with pytest.raises(RBEError, match="distinct actors"):
        validate_initiation(
            authority,
            schemas,
            policy,
            duplicate,
            ExecutionMode.ADVISORY_DRY_RUN,
        )


def test_report_requires_known_evidence_and_matching_assignment(
    authority: AuthorityBundle,
    schemas: SchemaRegistry,
    policy: ProfilePolicy,
) -> None:
    references = validate_report_submission(
        schemas,
        policy,
        session=valid_session(authority),
        assignment=valid_assignment(),
        evidence=valid_evidence(),
        raw_record=valid_report_record(),
        summary="Traceable architecture report.",
        recommendation="Monitoring",
        evidence_reference_ids=["EVI-001"],
    )
    assert references == ("EVI-001",)

    with pytest.raises(RBEError, match="not registered"):
        validate_report_submission(
            schemas,
            policy,
            session=valid_session(authority),
            assignment=valid_assignment(),
            evidence=valid_evidence(),
            raw_record=valid_report_record(),
            summary="Traceable architecture report.",
            recommendation="Monitoring",
            evidence_reference_ids=["EVI-404"],
        )


def test_unsigned_ai_cannot_become_authoritative_report(
    authority: AuthorityBundle,
    schemas: SchemaRegistry,
    policy: ProfilePolicy,
) -> None:
    record = valid_report_record()
    record["ai_assistance"] = {"used": True, "human_verified": False}
    with pytest.raises(RBEError, match="human verification"):
        validate_report_submission(
            schemas,
            policy,
            session=valid_session(authority),
            assignment=valid_assignment(),
            evidence=valid_evidence(),
            raw_record=record,
            summary="Unsigned model draft.",
            recommendation="Research",
            evidence_reference_ids=["EVI-001"],
        )

    undeclared = valid_report_record()
    undeclared["ai_assistance"] = {}
    with pytest.raises(RBEError, match="explicitly declare"):
        validate_report_submission(
            schemas,
            policy,
            session=valid_session(authority),
            assignment=valid_assignment(),
            evidence=valid_evidence(),
            raw_record=undeclared,
            summary="Ambiguous assistance metadata.",
            recommendation="Research",
            evidence_reference_ids=["EVI-001"],
        )


def test_finding_preserves_report_and_evidence_lineage(
    authority: AuthorityBundle,
    schemas: SchemaRegistry,
) -> None:
    references = validate_finding_submission(
        schemas,
        session=valid_session(authority),
        source_report=normalized_report(),
        assignment=valid_assignment(),
        evidence=valid_evidence(),
        raw_record=valid_finding_record(),
    )
    assert references == ("EVI-001",)

    mismatch = copy.deepcopy(valid_finding_record())
    mismatch["finding_id"] = "FND-NOT-IN-REPORT"
    with pytest.raises(RBEError, match="source report"):
        validate_finding_submission(
            schemas,
            session=valid_session(authority),
            source_report=normalized_report(),
            assignment=valid_assignment(),
            evidence=valid_evidence(),
            raw_record=mismatch,
        )
