from __future__ import annotations

import copy
import json

import pytest

from controlled_authority import rbm_package as rbm


def test_manifest_uses_canonical_cross_platform_path_order() -> None:
    paths = [
        path.relative_to(rbm.PACKAGE_ROOT).as_posix()
        for path in rbm.controlled_files()
    ]
    manifest = json.loads(rbm.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert paths == sorted(paths, key=lambda value: (value.casefold(), value))
    assert [item["path"] for item in manifest["files"]] == paths


def _decision_bundle(
    *, active: bool = False, merge_permitted: bool = False
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    profile = json.loads(rbm.PROFILE_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(rbm.MANIFEST_PATH.read_text(encoding="utf-8"))
    if active:
        profile["status"] = "ACTIVE"
        profile["binding"] = True
        profile["human_approval_record"] = "APR-001"
        profile["checksum"] = rbm.calculate_profile_checksum(profile)

    common = {
        "review_id": "REV-001",
        "artefact_sha": "abcdef1234567890",
        "methodology_profile_id": "RBM-001",
        "methodology_version": "2.2.0",
        "methodology_status": profile["status"],
        "methodology_checksum": profile["checksum"],
        "binding": profile["binding"],
    }
    initiation: dict[str, object] = {
        **common,
        "tier": 3,
        "manifest_root_sha256": manifest["root_sha256"],
        "human_approval_record": profile["human_approval_record"],
        "board_chair": "human-chair",
        "methodology_auditor": "human-ma",
        "sceptical_reviewer": "human-sr",
        "specialists": {
            "saa": "human-saa",
            "bca": "human-bca",
            "dea": "human-dea",
            "qra": "human-qra",
            "spa": "human-spa",
            "poa": "human-poa",
        },
        "input_process_status": "READY",
    }
    decision: dict[str, object] = {
        **common,
        "tier": 3,
        "process_status": "READY",
        "outcome": "PASS",
        "finding_snapshot": {
            "unresolved_sev1": 0,
            "unresolved_sev2": 0,
            "accepted_sev2_remediation": 0,
        },
        "substantive_evidence_sufficient": True,
        "merge_permitted": merge_permitted,
        "board_chair": "human-chair",
        "board_chair_signature_ref": "SIG-BC-001",
        "governance_validator": "human-ma",
        "governance_validation_ref": "SIG-MA-001",
    }
    indicator: dict[str, object] = {
        **common,
        "review_risk_tier": 3,
        "process_status": "READY",
        "outcome": "PASS",
        "merge_permitted": merge_permitted,
        "board_chair": "human-chair",
        "governance_validator": "human-ma",
        "publication_authority": "automation-publication-control",
        "unresolved_sev1_count": 0,
        "unresolved_sev2_count": 0,
    }
    return initiation, decision, indicator, profile, manifest


def test_rbm001_package_is_reproducible_and_valid() -> None:
    rbm.validate_package()


def test_controlled_package_uses_canonical_lf_endings() -> None:
    for path in [*rbm.controlled_files(), rbm.MANIFEST_PATH]:
        if path.suffix.lower() in rbm.CONTROLLED_TEXT_SUFFIXES:
            assert b"\r" not in path.read_bytes(), path


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {
                "process_status": "READY",
                "unresolved_sev1": 1,
                "unresolved_sev2": 0,
                "accepted_sev2_remediation": 0,
                "substantive_evidence_sufficient": False,
            },
            "FAIL",
        ),
        (
            {
                "process_status": "READY",
                "unresolved_sev1": 0,
                "unresolved_sev2": 2,
                "accepted_sev2_remediation": 2,
                "substantive_evidence_sufficient": True,
            },
            "FAIL",
        ),
        (
            {
                "process_status": "READY",
                "unresolved_sev1": 0,
                "unresolved_sev2": 1,
                "accepted_sev2_remediation": 0,
                "substantive_evidence_sufficient": True,
            },
            "FAIL",
        ),
        (
            {
                "process_status": "READY",
                "unresolved_sev1": 0,
                "unresolved_sev2": 0,
                "accepted_sev2_remediation": 0,
                "substantive_evidence_sufficient": False,
            },
            "INSUFFICIENT_EVIDENCE",
        ),
        (
            {
                "process_status": "READY",
                "unresolved_sev1": 0,
                "unresolved_sev2": 1,
                "accepted_sev2_remediation": 1,
                "substantive_evidence_sufficient": True,
            },
            "PASS_WITH_FINDINGS",
        ),
        (
            {
                "process_status": "READY",
                "unresolved_sev1": 0,
                "unresolved_sev2": 0,
                "accepted_sev2_remediation": 0,
                "substantive_evidence_sufficient": True,
            },
            "PASS",
        ),
    ],
)
def test_decision_precedence_is_total_and_deterministic(
    kwargs: dict[str, object], expected: str
) -> None:
    assert rbm.evaluate_outcome(**kwargs) == expected


@pytest.mark.parametrize(
    "status", ["PROCEDURALLY_INCOMPLETE", "BLOCKED", "VOID"]
)
def test_non_ready_process_never_produces_an_outcome(status: str) -> None:
    assert (
        rbm.evaluate_outcome(
            process_status=status,
            unresolved_sev1=3,
            unresolved_sev2=3,
            accepted_sev2_remediation=0,
            substantive_evidence_sufficient=True,
        )
        is None
    )


def test_invalid_remediation_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        rbm.evaluate_outcome(
            process_status="READY",
            unresolved_sev1=0,
            unresolved_sev2=0,
            accepted_sev2_remediation=1,
            substantive_evidence_sufficient=True,
        )


def test_release_candidate_cannot_authorise_merge() -> None:
    for outcome in rbm.OUTCOMES:
        assert not rbm.is_merge_permitted(
            profile_status="RELEASE_CANDIDATE",
            binding=False,
            process_status="READY",
            outcome=outcome,
        )


def test_only_active_pass_class_outcomes_can_authorise_merge() -> None:
    assert rbm.is_merge_permitted(
        profile_status="ACTIVE",
        binding=True,
        process_status="READY",
        outcome="PASS",
    )
    assert rbm.is_merge_permitted(
        profile_status="ACTIVE",
        binding=True,
        process_status="READY",
        outcome="PASS_WITH_FINDINGS",
    )
    assert not rbm.is_merge_permitted(
        profile_status="ACTIVE",
        binding=True,
        process_status="READY",
        outcome="INSUFFICIENT_EVIDENCE",
    )


def test_profile_keeps_human_activation_gate_open() -> None:
    profile = json.loads(rbm.PROFILE_PATH.read_text(encoding="utf-8"))
    assert profile["status"] == "RELEASE_CANDIDATE"
    assert profile["binding"] is False
    assert profile["human_approval_record"] is None
    assert "INSUFFICIENT_EVIDENCE" in profile["permitted_outcomes"]
    assert profile["role_policy"]["distinct_human_per_board_role"] is True


def test_every_reviewer_prompt_is_non_authoritative() -> None:
    specs = sorted((rbm.PACKAGE_ROOT / "specs").glob("RBS-*.md"))
    assert len(specs) == 8
    for spec in specs:
        text = spec.read_text(encoding="utf-8")
        assert "non-authoritative AI assistant" in text
        assert "unsigned draft" in text
        assert "## 10. Board Decision Contribution" in text


def test_machine_contract_covers_reviewer_and_remediation_records() -> None:
    assert (rbm.SCHEMA_ROOT / "tpl-rrr.schema.json").is_file()
    assert (rbm.SCHEMA_ROOT / "tpl-rmp.schema.json").is_file()
    bdr = json.loads(
        (rbm.SCHEMA_ROOT / "tpl-bdr.schema.json").read_text(encoding="utf-8")
    )
    assert "process_status" in bdr["properties"]
    assert "INSUFFICIENT_EVIDENCE" in bdr["properties"]["outcome"]["enum"]
    assert "governance_validator" in bdr["required"]


def test_profile_maps_every_canonical_rbe_state_once() -> None:
    profile = json.loads(rbm.PROFILE_PATH.read_text(encoding="utf-8"))
    mapped = [
        state
        for states in profile["canonical_lifecycle_mapping"].values()
        for state in states
    ]
    assert set(mapped) == rbm.CANONICAL_RBE_STATES
    assert len(mapped) == len(set(mapped))


def test_release_candidate_decision_bundle_is_valid_but_cannot_merge() -> None:
    initiation, decision, indicator, profile, manifest = _decision_bundle()
    rbm.validate_decision_bundle(
        initiation, decision, indicator, profile=profile, manifest=manifest
    )
    assert decision["merge_permitted"] is False


def test_decision_bundle_rejects_release_candidate_merge_claim() -> None:
    initiation, decision, indicator, profile, manifest = _decision_bundle(
        merge_permitted=True
    )
    with pytest.raises(rbm.PackageValidationError, match="outside the guard"):
        rbm.validate_decision_bundle(
            initiation, decision, indicator, profile=profile, manifest=manifest
        )


def test_active_bundle_requires_human_approval_and_separated_publication() -> None:
    initiation, decision, indicator, profile, manifest = _decision_bundle(
        active=True, merge_permitted=True
    )
    rbm.validate_decision_bundle(
        initiation, decision, indicator, profile=profile, manifest=manifest
    )

    conflicted = copy.deepcopy(indicator)
    conflicted["publication_authority"] = decision["governance_validator"]
    with pytest.raises(rbm.PackageValidationError, match="Publication authority"):
        rbm.validate_decision_bundle(
            initiation, decision, conflicted, profile=profile, manifest=manifest
        )


def test_active_profile_without_human_approval_is_rejected() -> None:
    profile = json.loads(rbm.PROFILE_PATH.read_text(encoding="utf-8"))
    profile["status"] = "ACTIVE"
    profile["binding"] = True
    profile["human_approval_record"] = None
    profile["checksum"] = rbm.calculate_profile_checksum(profile)
    with pytest.raises(rbm.PackageValidationError, match="human approval"):
        rbm._validate_profile(profile)
