from __future__ import annotations

import json
from pathlib import Path

from rbe_runtime.cli import main
from test_rbe_runtime_artifacts import completed_runtime


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "rbe_runtime"


def test_authority_cli_reports_release_candidate_boundary(capsys) -> None:
    assert main(["validate-authority"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is True
    assert result["profile_status"] == "RELEASE_CANDIDATE"


def test_cli_exports_and_verifies_bundle(tmp_path: Path, capsys) -> None:
    review_id = "REV-CLI-001"
    database = tmp_path / "runtime.sqlite3"
    completed_runtime(database, review_id)
    output = tmp_path / "bundle"

    assert (
        main(
            [
                "export",
                "--database",
                str(database),
                "--session",
                review_id,
                "--output",
                str(output),
            ]
        )
        == 0
    )
    exported = json.loads(capsys.readouterr().out)
    assert exported["binding"] is False

    assert main(["verify-bundle", "--bundle", str(output)]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["valid"] is True

    assert (
        main(
            [
                "verify-audit",
                "--database",
                str(database),
                "--session",
                review_id,
            ]
        )
        == 0
    )
    audit = json.loads(capsys.readouterr().out)
    assert audit["valid"] is True


def test_cli_failure_is_safe_and_contains_no_traceback(
    tmp_path: Path, capsys
) -> None:
    assert main(["verify-bundle", "--bundle", str(tmp_path / "missing")]) == 2
    error = capsys.readouterr().err
    assert "RBE_BUNDLE_MANIFEST_INVALID" in error
    assert "Traceback" not in error


def test_golden_fixture_catalog_is_closed_and_versioned() -> None:
    fixtures = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(FIXTURE_ROOT.glob("*.json"))
    }
    assert set(fixtures) == {
        "blocked",
        "fail",
        "insufficient_evidence",
        "pass",
        "pass_with_findings",
    }
    assert {item["expected_outcome"] for item in fixtures.values()} == {
        "PASS",
        "PASS_WITH_FINDINGS",
        "FAIL",
        "INSUFFICIENT_EVIDENCE",
        None,
    }
    assert all(item["schema_version"] == "1.0.0" for item in fixtures.values())
