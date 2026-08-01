from __future__ import annotations

import copy

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.canonical import canonical_hash
from rbe_runtime.decision import DecisionEngine
from rbe_runtime.errors import RBEError
from rbe_runtime.models import Finding


def finding(
    finding_id: str,
    severity: str,
    *,
    status: str = "OPEN",
) -> Finding:
    raw = {"finding_id": finding_id, "severity": severity, "status": status}
    return Finding(
        finding_id=finding_id,
        session_id="REV-DECISION-001",
        source_report_id=f"RPT-{finding_id}",
        severity=severity,
        category="ARCHITECTURE",
        title=f"Finding {finding_id}",
        description="Deterministic decision fixture.",
        evidence_reference_ids=("EVI-001",),
        status=status,
        remediation_required=severity in {"SEV-1", "SEV-2"},
        raw_record=raw,
        raw_record_sha256=canonical_hash(raw),
        created_at="2026-07-20T10:00:00Z",
    )


@pytest.fixture(scope="module")
def engine() -> DecisionEngine:
    return DecisionEngine(AuthorityBundle.load().profile)


@pytest.mark.parametrize(
    ("findings", "sufficient", "accepted_remediation", "expected"),
    [
        ((finding("F1", "SEV-1"),), True, (), "FAIL"),
        (
            (finding("F1", "SEV-2"), finding("F2", "SEV-2")),
            True,
            ("F1", "F2"),
            "FAIL",
        ),
        ((finding("F1", "SEV-2"),), True, (), "FAIL"),
        ((), False, (), "INSUFFICIENT_EVIDENCE"),
        (
            (finding("F1", "SEV-2"),),
            True,
            ("F1",),
            "PASS_WITH_FINDINGS",
        ),
        ((), True, (), "PASS"),
    ],
)
def test_profile_rules_produce_all_golden_outcomes(
    engine: DecisionEngine,
    findings: tuple[Finding, ...],
    sufficient: bool,
    accepted_remediation: tuple[str, ...],
    expected: str,
) -> None:
    evaluation = engine.evaluate(
        findings=findings,
        process_status="READY",
        substantive_evidence_sufficient=sufficient,
        accepted_remediation_finding_ids=accepted_remediation,
    )
    assert evaluation.outcome == expected
    assert evaluation.reason_codes[0].startswith("RBM-DEC-")


@pytest.mark.parametrize(
    "status", ["PROCEDURALLY_INCOMPLETE", "BLOCKED", "VOID"]
)
def test_non_ready_process_has_no_substantive_outcome(
    engine: DecisionEngine, status: str
) -> None:
    evaluation = engine.evaluate(
        findings=(finding("F1", "SEV-1"),),
        process_status=status,
        substantive_evidence_sufficient=True,
    )
    assert evaluation.outcome is None
    assert evaluation.reason_codes == (f"PROCESS_{status}",)


def test_fail_precedence_wins_over_insufficient_evidence(
    engine: DecisionEngine,
) -> None:
    evaluation = engine.evaluate(
        findings=(finding("F1", "SEV-1"),),
        process_status="READY",
        substantive_evidence_sufficient=False,
    )
    assert evaluation.outcome == "FAIL"
    assert evaluation.reason_codes == ("RBM-DEC-001",)


def test_finding_order_and_repeated_runs_do_not_change_evaluation(
    engine: DecisionEngine,
) -> None:
    findings = (
        finding("F2", "SEV-3"),
        finding("F1", "SEV-2"),
    )
    forward = engine.evaluate(
        findings=findings,
        process_status="READY",
        substantive_evidence_sufficient=True,
        accepted_remediation_finding_ids=("F1",),
        counter_evidence=("EVI-003", "EVI-002"),
    )
    reverse = engine.evaluate(
        findings=tuple(reversed(findings)),
        process_status="READY",
        substantive_evidence_sufficient=True,
        accepted_remediation_finding_ids=("F1",),
        counter_evidence=("EVI-002", "EVI-003"),
    )
    assert reverse == forward
    assert all(
        engine.evaluate(
            findings=findings,
            process_status="READY",
            substantive_evidence_sufficient=True,
            accepted_remediation_finding_ids=("F1",),
            counter_evidence=("EVI-003", "EVI-002"),
        )
        == forward
        for _ in range(100)
    )


def test_unsafe_or_incomplete_profile_rules_fail_closed() -> None:
    profile = copy.deepcopy(AuthorityBundle.load().profile)
    profile["decision_precedence"][0]["condition"] = "__import__('os').system('x')"
    with pytest.raises(RBEError, match="Unsupported syntax"):
        DecisionEngine(profile)

    profile = copy.deepcopy(AuthorityBundle.load().profile)
    profile["decision_precedence"] = profile["decision_precedence"][:-1]
    with pytest.raises(RBEError, match="do not cover"):
        DecisionEngine(profile)


def test_unknown_remediation_finding_fails_closed(engine: DecisionEngine) -> None:
    with pytest.raises(RBEError, match="unknown finding"):
        engine.evaluate(
            findings=(),
            process_status="READY",
            substantive_evidence_sufficient=True,
            accepted_remediation_finding_ids=("FND-UNKNOWN",),
        )
