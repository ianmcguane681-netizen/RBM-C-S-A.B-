from __future__ import annotations

from pathlib import Path

import pytest

from rbe_runtime.artifacts import ArtifactExporter
from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime
from test_rbe_runtime_service import NOW, advance, prepare_to_consolidation


def completed_runtime(path: Path, review_id: str) -> RBERuntime:
    runtime = RBERuntime(path, clock=lambda: NOW)
    prepare_to_consolidation(runtime, review_id)
    runtime.prepare_decision_candidate(
        review_id,
        actor="human-chair",
        idempotency_key="candidate",
    )
    advance(runtime, review_id, "GOVERNANCE_VALIDATION", 9)
    runtime.ratify_decision(
        review_id,
        actor="human-chair",
        board_chair_signature_ref="SIG-BC-001",
        governance_validator="human-ma",
        governance_validation_ref="SIG-MA-GOV-001",
        idempotency_key="ratify",
    )
    advance(runtime, review_id, "DECIDED", 10)
    runtime.publish_decision(
        review_id,
        actor="human-publication",
        idempotency_key="publish",
    )
    advance(runtime, review_id, "PUBLISHED", 11)
    return runtime


def test_bundle_contains_required_artifacts_and_raw_evidence(tmp_path: Path) -> None:
    review_id = "REV-ARTIFACT-001"
    runtime = completed_runtime(tmp_path / "runtime.sqlite3", review_id)
    exporter = ArtifactExporter(runtime.repository, runtime.authority)
    output = tmp_path / "bundle"
    manifest = exporter.export(review_id, output)
    paths = {entry["path"] for entry in manifest["artifacts"]}
    assert {
        "session.json",
        "package-manifest.json",
        "assignments.json",
        "reports.json",
        "findings.json",
        "decision.json",
        "audit.jsonl",
        "review-report.md",
    }.issubset(paths)
    assert any(path.startswith("evidence/") for path in paths)
    assert ArtifactExporter.verify(output)["valid"] is True

    report = (output / "review-report.md").read_text(encoding="utf-8")
    assert "ADVISORY DRY RUN" in report
    assert "Merge permitted: **false**" in report
    assert "Non-binding recommendation" in report


def test_repeated_export_is_byte_stable(tmp_path: Path) -> None:
    review_id = "REV-ARTIFACT-STABLE"
    runtime = completed_runtime(tmp_path / "runtime.sqlite3", review_id)
    exporter = ArtifactExporter(runtime.repository, runtime.authority)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = exporter.export(review_id, first)
    second_manifest = exporter.export(review_id, second)
    assert second_manifest == first_manifest
    for entry in first_manifest["artifacts"]:
        assert (first / entry["path"]).read_bytes() == (
            second / entry["path"]
        ).read_bytes()


def test_bundle_verifier_detects_tampering(tmp_path: Path) -> None:
    review_id = "REV-ARTIFACT-TAMPER"
    runtime = completed_runtime(tmp_path / "runtime.sqlite3", review_id)
    exporter = ArtifactExporter(runtime.repository, runtime.authority)
    output = tmp_path / "bundle"
    exporter.export(review_id, output)
    (output / "decision.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(RBEError, match="checksum"):
        ArtifactExporter.verify(output)
