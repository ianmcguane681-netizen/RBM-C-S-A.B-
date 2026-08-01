"""One human may sign, and the record says so forever.

Ratification requires two separated humans, so a one-human organisation could
conduct a complete review and never sign the result. v2.2.0 permits a single named
Board Chair to ratify while the methodology is non-binding, recorded permanently
as single_authority.

The reduction is labelled rather than hidden, and it is fenced: refused once the
profile is ACTIVE, refused for agents, refused for anyone but the chair, and never
merge-permitted. The outcome still comes from the deterministic gates, so a single
authority attests to the process rather than choosing the result.
"""
from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime
from tests.test_rbe_runtime_service import NOW, prepare_to_consolidation


def at_governance_validation(tmp_path: Path, review_id: str = "REV-SOLO") -> RBERuntime:
    runtime = RBERuntime(tmp_path / "solo.sqlite3", clock=lambda: NOW)
    prepare_to_consolidation(runtime, review_id)
    runtime.prepare_decision_candidate(
        review_id, actor="human-chair", idempotency_key="candidate"
    )
    runtime.advance(
        review_id, "GOVERNANCE_VALIDATION", actor="human-chair", idempotency_key="s09"
    )
    return runtime


def sign_alone(runtime: RBERuntime, review_id: str = "REV-SOLO", actor: str = "human-chair"):
    return runtime.ratify_decision(
        review_id,
        actor=actor,
        board_chair_signature_ref="SIG-BC-SOLO",
        idempotency_key="ratify-solo",
        single_authority_rationale="Sole human authority.",
    )


def test_profile_permits_single_authority_only_while_non_binding():
    policy = AuthorityBundle.load().profile["single_authority_policy"]

    assert policy["single_authority_permitted"] is True
    assert policy["permitted_only_when_profile_non_binding"] is True
    assert policy["never_binding"] is True
    assert policy["never_merge_permitted"] is True
    assert policy["authority_must_be_human"] is True
    assert policy["authority_must_be_board_chair"] is True


def test_one_human_can_sign_and_the_decision_records_it(tmp_path: Path):
    runtime = at_governance_validation(tmp_path)

    result = sign_alone(runtime)

    assert result["single_authority"] is True
    assert result["status"] == "SIGNED"
    assert result["binding"] is False
    assert result["merge_permitted"] is False
    decision = runtime.repository.get_decision("REV-SOLO")
    assert decision.single_authority is True


def test_the_outcome_is_still_computed_not_chosen(tmp_path: Path):
    """A single authority attests to the process; it cannot pick the result."""
    runtime = at_governance_validation(tmp_path)
    candidate = runtime.repository.get_decision_candidate("REV-SOLO")

    result = sign_alone(runtime)

    assert result["evaluation"]["outcome"] == candidate["evaluation"].outcome


def test_no_governance_validator_is_recorded(tmp_path: Path):
    """Naming the chair twice would fabricate a second signatory."""
    runtime = at_governance_validation(tmp_path)
    sign_alone(runtime)

    ratification = runtime.repository.get_ratification("REV-SOLO")

    assert ratification["board_chair"] == "human-chair"
    assert ratification["governance_validator"] is None
    assert ratification["governance_validation_ref"] is None


def test_an_agent_cannot_sign_alone(tmp_path: Path):
    runtime = at_governance_validation(tmp_path, "REV-AGENT-SOLO")

    with pytest.raises(RBEError) as exc:
        runtime.ratify_decision(
            "REV-AGENT-SOLO",
            actor="agent:chair",
            board_chair_signature_ref="SIG",
            idempotency_key="r",
        )

    assert exc.value.code in {
        "RBE_RATIFICATION_AUTHORITY_NOT_HUMAN",
        "RBE_SINGLE_AUTHORITY_MUST_BE_CHAIR",
    }


def test_only_the_board_chair_may_sign_alone(tmp_path: Path):
    runtime = at_governance_validation(tmp_path)

    with pytest.raises(RBEError) as exc:
        sign_alone(runtime, actor="human-qra")

    assert exc.value.code == "RBE_SINGLE_AUTHORITY_MUST_BE_CHAIR"


def test_single_authority_is_refused_under_a_binding_methodology(tmp_path: Path):
    """The fence that stops this becoming a backdoor to binding decisions."""
    authority = AuthorityBundle.load()
    binding = copy.deepcopy(authority.profile)
    binding["status"] = "ACTIVE"
    binding["binding"] = True
    runtime = RBERuntime(tmp_path / "binding.sqlite3", clock=lambda: NOW)
    # `replace` rather than a field-by-field rebuild: the bundle gained a `spec` field
    # when the runtime learned to carry more than one profile, and a test that
    # enumerates fields has to be edited every time one is added.
    runtime.authority = dataclasses.replace(authority, profile=binding)

    with pytest.raises(RBEError) as exc:
        runtime._require_single_authority_permitted(
            "human-chair", {"board_chair": "human-chair"}
        )

    assert exc.value.code == "RBE_SINGLE_AUTHORITY_FORBIDDEN_WHEN_BINDING"


def test_four_eyes_ratification_still_works(tmp_path: Path):
    """The ordinary path is unchanged for organisations with two humans."""
    runtime = at_governance_validation(tmp_path, "REV-TWO")

    result = runtime.ratify_decision(
        "REV-TWO",
        actor="human-chair",
        board_chair_signature_ref="SIG-BC",
        governance_validator="human-ma",
        governance_validation_ref="SIG-GV",
        idempotency_key="ratify-two",
    )

    assert result["single_authority"] is False
    ratification = runtime.repository.get_ratification("REV-TWO")
    assert ratification["governance_validator"] == "human-ma"


def test_the_chair_may_publish_their_own_single_authority_decision(tmp_path: Path):
    """The same separation cannot be met, so it is permitted and stays recorded."""
    runtime = at_governance_validation(tmp_path)
    sign_alone(runtime)
    runtime.advance("REV-SOLO", "DECIDED", actor="human-chair", idempotency_key="s10")

    publication = runtime.publish_decision(
        "REV-SOLO", actor="human-chair", idempotency_key="pub"
    )

    assert publication["indicator"]["single_authority"] is True
    assert publication["indicator"]["merge_permitted"] is False


def test_a_two_signature_decision_still_needs_a_separate_publisher(tmp_path: Path):
    runtime = at_governance_validation(tmp_path, "REV-TWO2")
    runtime.ratify_decision(
        "REV-TWO2",
        actor="human-chair",
        board_chair_signature_ref="SIG-BC",
        governance_validator="human-ma",
        governance_validation_ref="SIG-GV",
        idempotency_key="ratify",
    )
    runtime.advance("REV-TWO2", "DECIDED", actor="human-chair", idempotency_key="s10")

    with pytest.raises(RBEError) as exc:
        runtime.publish_decision("REV-TWO2", actor="human-chair", idempotency_key="pub")

    # The bundle validator reaches this rule before the repository does, so the
    # reported code is the outer one. What matters is that the separation holds.
    assert exc.value.code in {
        "RBE_PUBLICATION_ROLE_CONFLICT",
        "RBE_PUBLICATION_BUNDLE_INVALID",
    }
    assert "must differ" in json.dumps(exc.value.details)


def test_the_published_single_authority_decision_is_on_record():
    """The first fully completed decision the system has ever produced."""
    manifest = Path("data/review_0004_passed_with_findings/bundle-manifest.json")
    if not manifest.is_file():  # pragma: no cover - only present after a live run
        pytest.skip("no exported review bundle in this checkout")
    bundle = json.loads(manifest.read_text(encoding="utf-8"))
    decision = json.loads(Path("data/review_0004_passed_with_findings/decision.json").read_text(encoding="utf-8"))

    assert bundle["outcome"] == "PASS_WITH_FINDINGS"
    assert bundle["binding"] is False
    assert bundle["merge_permitted"] is False
    assert bundle["methodology"]["version"] == "2.2.0"
    assert decision["decision"]["single_authority"] is True
    assert decision["ratification"]["governance_validator"] is None
    assert decision["publication"]["publication_authority"] == "ian.mcguane"
