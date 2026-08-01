"""Agents may review. They may not sign.

v2.1.0 opened reviewer seats to agents while keeping ratification and publication
human. The first real review found that the runtime was not actually enforcing
that: a board could be convened with an agent as Methodology Auditor, and because
the governance validator must be the MA, the agent went on to co-sign the very
decision it had reviewed. That is both non-human authority and a collapse of the
four-eyes control, and it succeeded silently.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError
from rbe_runtime.profile import is_agent_actor
from rbe_runtime.service import RBERuntime
from tests.test_rbe_runtime_service import NOW, initiation


def test_every_automation_prefix_counts_as_an_agent():
    """A seat cannot dodge the rules by choosing a different prefix."""
    for actor in ("agent:sr", "ai:sr", "model:sr", "automation:sr", "AGENT:SR"):
        assert is_agent_actor(actor) is True
    assert is_agent_actor("ian.mcguane") is False


def test_profile_permits_agent_reviewer_seats_but_not_the_chair():
    policy = AuthorityBundle.load().profile["agent_seat_policy"]

    assert policy["agent_seats_permitted"] is True
    assert "BC" in policy["prohibited_agent_roles"]
    assert "BC" not in policy["permitted_agent_roles"]
    assert {"MA", "SR"} <= set(policy["permitted_agent_roles"])
    assert policy["ratification_authority_must_be_human"] is True
    assert policy["publication_authority_must_be_human"] is True


def agent_staffed(authority: AuthorityBundle, review_id: str) -> dict:
    record = initiation(authority, review_id)
    record.update(
        tier=2,
        methodology_auditor="agent:ma",
        sceptical_reviewer="agent:sr",
        specialists={
            "saa": "agent:saa",
            "bca": "agent:bca",
            "dea": "agent:dea",
            "qra": "agent:qra",
            "spa": None,
            "poa": None,
        },
    )
    return record


def test_a_board_can_be_staffed_with_agent_reviewer_seats(tmp_path: Path):
    runtime = RBERuntime(tmp_path / "agents.sqlite3", clock=lambda: NOW)
    record = agent_staffed(runtime.authority, "REV-AGENTS")

    runtime.initiate_review(record, actor="human-chair", idempotency_key="i")

    seats = {
        item.reviewer_role: item.reviewer_actor
        for item in runtime.repository.list_assignments("REV-AGENTS")
    }
    assert seats["SR"] == "agent:sr"
    assert seats["MA"] == "agent:ma"
    assert len(seats) == 6


def test_an_agent_cannot_hold_the_accountable_chair_seat(tmp_path: Path):
    runtime = RBERuntime(tmp_path / "chair.sqlite3", clock=lambda: NOW)
    record = agent_staffed(runtime.authority, "REV-AGENT-CHAIR")
    record["board_chair"] = "agent:chair"

    with pytest.raises(RBEError) as exc:
        runtime.initiate_review(record, actor="agent:chair", idempotency_key="i")

    assert exc.value.code == "RBE_NON_HUMAN_BOARD_ROLE"
    assert exc.value.details["roles"] == ["BC"]


def test_one_agent_cannot_hold_two_seats(tmp_path: Path):
    runtime = RBERuntime(tmp_path / "dup.sqlite3", clock=lambda: NOW)
    record = agent_staffed(runtime.authority, "REV-DUP")
    record["sceptical_reviewer"] = "agent:ma"

    with pytest.raises(RBEError) as exc:
        runtime.initiate_review(record, actor="human-chair", idempotency_key="i")

    assert exc.value.code == "RBE_ROLE_CONFLICT"


def test_an_agent_seat_report_must_declare_ai_and_name_its_model(tmp_path: Path):
    """A report from an agent seat cannot claim a human wrote it."""
    from rbe_runtime.validation import validate_report_submission

    runtime = RBERuntime(tmp_path / "declare.sqlite3", clock=lambda: NOW)
    record = agent_staffed(runtime.authority, "REV-DECLARE")
    runtime.initiate_review(record, actor="human-chair", idempotency_key="i")
    session = runtime.repository.get_session("REV-DECLARE")
    assignment = next(
        item
        for item in runtime.repository.list_assignments("REV-DECLARE")
        if item.reviewer_role == "SR"
    )
    accepted = replace(assignment, status="ACCEPTED")
    raw = {
        "schema_version": "2.2.0",
        "report_id": "RPT-1",
        "review_id": "REV-DECLARE",
        "reviewer": assignment.reviewer_actor,
        "reviewer_role": "SR",
        "reviewer_spec_id": assignment.reviewer_spec_id,
        "reviewer_spec_version": session.methodology_version,
        "artefact_sha": session.target_version,
        "finding_ids": [],
        "evidence_sufficiency": "NOT_APPLICABLE",
        "missing_evidence": [],
        "ai_assistance": {"used": False, "human_verified": False, "method": None},
        "human_signature_ref": "SIG",
    }

    with pytest.raises(RBEError) as exc:
        validate_report_submission(
            runtime.schemas,
            runtime.policy,
            session=session,
            assignment=accepted,
            evidence={},
            raw_record=raw,
            summary="s",
            recommendation="Monitoring",
            evidence_reference_ids=(),
        )

    assert exc.value.code == "RBE_AGENT_SEAT_MUST_DECLARE_AI"


def test_an_agent_cannot_ratify_a_decision(tmp_path: Path):
    """The control the first real review found missing."""
    runtime = RBERuntime(tmp_path / "ratify.sqlite3", clock=lambda: NOW)

    with pytest.raises(RBEError) as exc:
        runtime._require_human_ratifiers("human-chair", "agent:ma")

    assert exc.value.code == "RBE_RATIFICATION_AUTHORITY_NOT_HUMAN"
    assert exc.value.details["actors"] == ["agent:ma"]


def test_an_agent_cannot_publish_a_decision(tmp_path: Path):
    runtime = RBERuntime(tmp_path / "publish.sqlite3", clock=lambda: NOW)

    with pytest.raises(RBEError) as exc:
        runtime._require_human_publisher("agent:publisher")

    assert exc.value.code == "RBE_PUBLICATION_AUTHORITY_NOT_HUMAN"


def test_two_humans_may_ratify(tmp_path: Path):
    runtime = RBERuntime(tmp_path / "humans.sqlite3", clock=lambda: NOW)

    runtime._require_human_ratifiers("human-chair", "human-ma")
    runtime._require_human_publisher("human-publisher")


def test_the_first_real_review_bundle_is_present_and_failed():
    """The board's first act was to reject, and the artefact records it.

    Preserved as run under RBM-001 v2.1.0, before single-authority ratification
    existed. It was never signed, which is why the second review exists.
    """
    manifest = Path("data/review_0001_failed/bundle-manifest.json")
    if not manifest.is_file():  # pragma: no cover - only present after a live run
        pytest.skip("no exported review bundle in this checkout")
    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data["session_id"] == "RBE-GSCF001-0001"
    assert data["outcome"] == "FAIL"
    assert data["binding"] is False
    assert data["merge_permitted"] is False
    assert data["methodology"]["version"] == "2.1.0"
