from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.canonical import canonical_hash, sha256_digest
from rbe_runtime.errors import RBEError
from rbe_runtime.models import (
    EvidenceReference,
    ReviewAssignment,
    ReviewerReport,
    ReviewSession,
)
from rbe_runtime.repository import SQLiteRepository
from rbe_runtime.state_machine import CanonicalStateMachine


NOW = "2026-07-20T09:00:00Z"


def make_repository(path: Path) -> SQLiteRepository:
    authority = AuthorityBundle.load()
    machine = CanonicalStateMachine.from_register(authority.state_machine)
    return SQLiteRepository(path, machine, clock=lambda: NOW)


def make_session(authority: AuthorityBundle) -> ReviewSession:
    return ReviewSession(
        session_id="REV-PERSIST-001",
        target_type="GIT_COMMIT",
        target_id="ianmcguane681-netizen/Project-Xchange",
        target_version="abcdef1234567890",
        methodology_id="RBM-001",
        methodology_version="2.0.0",
        methodology_checksum=authority.profile["checksum"],
        engine_version="0.1.0",
        schema_version="1.0.0",
        status="DRAFT",
        aggregate_version=0,
        execution_mode="ADVISORY_DRY_RUN",
        binding=False,
        created_at=NOW,
        created_by="human-chair",
    )


def make_assignments() -> tuple[ReviewAssignment, ...]:
    return tuple(
        ReviewAssignment(
            assignment_id=f"ASN-{index:03d}",
            session_id="REV-PERSIST-001",
            reviewer_role=role,
            reviewer_actor=actor,
            reviewer_spec_id=spec,
            status="PLANNED",
            sequence=index,
            required=True,
            conflict_declared=False,
            has_material_conflict=False,
            assigned_at=NOW,
        )
        for index, (role, actor, spec) in enumerate(
            (
                ("MA", "human-ma", "RBS-001"),
                ("SAA", "human-saa", "RBS-002"),
                ("QRA", "human-qra", "RBS-005"),
                ("SR", "human-sr", "RBS-008"),
            ),
            start=1,
        )
    )


def create_review(repo: SQLiteRepository) -> dict[str, object]:
    authority = AuthorityBundle.load()
    return repo.create_review(
        make_session(authority),
        {"schema_version": "2.2.0", "review_id": "REV-PERSIST-001"},
        make_assignments(),
        actor="human-chair",
        idempotency_key="create-001",
        package_root_hash=authority.profile_manifest["root_sha256"],
    )


def evidence_reference(content: bytes = b"controlled evidence") -> EvidenceReference:
    return EvidenceReference(
        reference_id="EVI-PERSIST-001",
        session_id="REV-PERSIST-001",
        reference_type="FILE",
        locator="repo://src/example.py#L1",
        content_sha256=sha256_digest(content),
        description="Preserved source excerpt",
        source_tier="T1",
        provenance={"commit": "abcdef1234567890", "collector": "human-chair"},
        registered_at=NOW,
    )


def test_migration_enables_foreign_keys_and_refuses_newer_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rbe.sqlite3"
    repo = make_repository(path)
    connection = repo._connect()
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        connection.execute(
            "INSERT INTO schema_migrations VALUES (?, ?, ?)",
            (999, "sha256:not-supported", NOW),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(RBEError, match="newer than"):
        make_repository(path)


def test_create_review_is_idempotent_and_audited(tmp_path: Path) -> None:
    repo = make_repository(tmp_path / "rbe.sqlite3")
    first = create_review(repo)
    replay = create_review(repo)
    assert replay == first
    assert repo.get_session("REV-PERSIST-001").status == "DRAFT"
    assert len(repo.list_assignments("REV-PERSIST-001")) == 4
    assert [event.event_type for event in repo.list_audit("REV-PERSIST-001")] == [
        "SESSION_CREATED"
    ]

    authority = AuthorityBundle.load()
    with pytest.raises(RBEError, match="different payload"):
        repo.create_review(
            make_session(authority),
            {"schema_version": "2.2.0", "review_id": "CHANGED"},
            make_assignments(),
            actor="human-chair",
            idempotency_key="create-001",
            package_root_hash=authority.profile_manifest["root_sha256"],
        )
    assert repo.list_audit("REV-PERSIST-001")[-1].event_type == "IDEMPOTENCY_CONFLICT"


def test_transition_and_audit_commit_atomically(tmp_path: Path) -> None:
    repo = make_repository(tmp_path / "rbe.sqlite3")
    create_review(repo)
    accepted = repo.transition(
        "REV-PERSIST-001",
        "SUBMITTED",
        actor="human-chair",
        idempotency_key="transition-001",
        expected_version=0,
    )
    replay = repo.transition(
        "REV-PERSIST-001",
        "SUBMITTED",
        actor="human-chair",
        idempotency_key="transition-001",
        expected_version=0,
    )
    assert replay == accepted
    assert repo.get_session("REV-PERSIST-001").aggregate_version == 1

    with pytest.raises(RBEError, match="not reachable"):
        repo.transition(
            "REV-PERSIST-001",
            "ACCEPTED",
            actor="human-chair",
            idempotency_key="transition-invalid",
            expected_version=1,
        )
    assert repo.get_session("REV-PERSIST-001").status == "SUBMITTED"
    events = repo.list_audit("REV-PERSIST-001")
    assert [event.event_type for event in events] == [
        "SESSION_CREATED",
        "STATE_TRANSITIONED",
        "COMMAND_REJECTED",
    ]
    assert repo.verify_audit("REV-PERSIST-001")["entries_verified"] == 3


def test_evidence_bytes_and_provenance_are_preserved(tmp_path: Path) -> None:
    repo = make_repository(tmp_path / "rbe.sqlite3")
    create_review(repo)
    content = b"controlled evidence"
    reference = evidence_reference(content)
    repo.register_evidence(
        reference,
        content,
        actor="human-chair",
        idempotency_key="evidence-001",
    )
    stored = repo.list_evidence("REV-PERSIST-001")[reference.reference_id]
    assert stored.provenance == reference.provenance
    assert repo.get_evidence_content(reference.reference_id) == content

    bad_reference = EvidenceReference(
        **{
            **reference.to_dict(),
            "reference_id": "EVI-PERSIST-BAD",
            "content_sha256": "sha256:" + "0" * 64,
        }
    )
    with pytest.raises(RBEError, match="does not match"):
        repo.register_evidence(
            bad_reference,
            b"different",
            actor="human-chair",
            idempotency_key="evidence-bad",
        )
    assert "EVI-PERSIST-BAD" not in repo.list_evidence("REV-PERSIST-001")


def test_conflicts_are_durable_and_block_assignment_acceptance(tmp_path: Path) -> None:
    repo = make_repository(tmp_path / "rbe.sqlite3")
    create_review(repo)
    accepted = repo.record_assignment_response(
        "REV-PERSIST-001",
        "ASN-002",
        actor="human-saa",
        has_material_conflict=False,
        conflict_basis=None,
        human_signature_ref="SIG-SAA-IND-001",
        idempotency_key="assignment-saa",
    )
    declined = repo.record_assignment_response(
        "REV-PERSIST-001",
        "ASN-003",
        actor="human-qra",
        has_material_conflict=True,
        conflict_basis="Reviewer authored the test evidence under review.",
        human_signature_ref="SIG-QRA-IND-001",
        idempotency_key="assignment-qra",
    )
    assert accepted["status"] == "ACCEPTED"
    assert declined["status"] == "DECLINED"
    assignments = {item.assignment_id: item for item in repo.list_assignments("REV-PERSIST-001")}
    assert assignments["ASN-002"].conflict_declared
    assert assignments["ASN-003"].has_material_conflict

    connection = repo._connect()
    try:
        declaration = connection.execute(
            "SELECT * FROM conflict_declarations WHERE assignment_id = 'ASN-003'"
        ).fetchone()
    finally:
        connection.close()
    assert declaration["basis"] == "Reviewer authored the test evidence under review."


def test_report_records_are_append_only(tmp_path: Path) -> None:
    repo = make_repository(tmp_path / "rbe.sqlite3")
    create_review(repo)
    content = b"controlled evidence"
    reference = evidence_reference(content)
    repo.register_evidence(
        reference,
        content,
        actor="human-chair",
        idempotency_key="evidence-001",
    )
    repo.record_assignment_response(
        "REV-PERSIST-001",
        "ASN-002",
        actor="human-saa",
        has_material_conflict=False,
        conflict_basis=None,
        human_signature_ref="SIG-SAA-IND-001",
        idempotency_key="assignment-saa",
    )
    raw = {
        "schema_version": "2.2.0",
        "report_id": "RPT-PERSIST-001",
        "review_id": "REV-PERSIST-001",
    }
    report = ReviewerReport(
        report_id="RPT-PERSIST-001",
        session_id="REV-PERSIST-001",
        assignment_id="ASN-002",
        report_version=1,
        raw_record=raw,
        raw_record_sha256=canonical_hash(raw),
        summary="No findings were declared in this persistence fixture.",
        recommendation="Monitoring",
        finding_ids=(),
        evidence_reference_ids=(reference.reference_id,),
        ai_assisted=False,
        human_verified=True,
        human_signature_ref="SIG-SAA-001",
        submitted_at=NOW,
    )
    result = repo.submit_review(
        report,
        (),
        actor="human-saa",
        idempotency_key="report-saa",
    )
    assert result["assignment_status"] == "COMPLETED"
    assert repo.list_reports("REV-PERSIST-001") == (report,)

    connection = repo._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE review_reports SET summary = 'changed' WHERE report_id = ?",
                (report.report_id,),
            )
    finally:
        connection.close()


def test_audit_verifier_detects_out_of_band_tampering(tmp_path: Path) -> None:
    repo = make_repository(tmp_path / "rbe.sqlite3")
    create_review(repo)
    connection = repo._connect()
    try:
        connection.execute("DROP TRIGGER audit_log_no_update")
        connection.execute(
            "UPDATE audit_log SET event_type = 'TAMPERED' WHERE sequence = 1"
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(RBEError, match="failed verification"):
        repo.verify_audit("REV-PERSIST-001")
