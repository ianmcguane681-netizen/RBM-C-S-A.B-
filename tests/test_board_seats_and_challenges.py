"""Agent seats are only a board if they can disagree with each other.

The failure mode these tests exist for is a board of agents that shares a model,
a brief and a conclusion, agrees with itself, and produces consensus that reads as
assurance. Independence here has to be structural, because a reviewer instructed
to ignore the answer it was given has still been given the answer.
"""
from __future__ import annotations

import pytest

from board import (
    AgentSeat,
    ChallengeSheet,
    NoChallenge,
    SeatConfigurationError,
    board_health,
    build_brief,
    render_review,
    require_independent_seats,
    seat_output,
    shared_model_note,
    sort_sheets,
    summarise,
    to_finding_record,
)
from guards.agent_guard import AgentGovernanceError, assert_not_evidence

TARGET = {
    "study_id": "EXAMPLE-001",
    "proposed_outcome": "PASS",
    "recommendation": "Proceed to next gate",
}
EVIDENCE = [{"evidence_id": "EV-1", "sha256": "abc"}]


def seats() -> list[AgentSeat]:
    return [
        AgentSeat(role="DEA", model="model-a", instruction_version="DEA-001"),
        AgentSeat(role="QRA", model="model-b", instruction_version="QRA-001"),
        AgentSeat(role="SR", model="model-c", instruction_version="SR-001"),
    ]


# --------------------------------------------------------------------------
# Independence
# --------------------------------------------------------------------------


def test_independent_seats_are_accepted():
    require_independent_seats(seats())


def test_seats_sharing_an_instruction_version_are_refused():
    """Same brief means the same review twice, not two reviews."""
    board = seats()
    board[1] = AgentSeat(role="QRA", model="model-b", instruction_version="DEA-001")

    with pytest.raises(SeatConfigurationError) as exc:
        require_independent_seats(board)

    assert exc.value.code == "SHARED_INSTRUCTION_VERSION"


def test_one_agent_cannot_hold_two_seats():
    board = [
        AgentSeat(role="DEA", model="m", instruction_version="V1", name="solo"),
        AgentSeat(role="QRA", model="m", instruction_version="V2", name="solo"),
    ]

    with pytest.raises(SeatConfigurationError) as exc:
        require_independent_seats(board)

    assert exc.value.code == "DUPLICATE_SEAT_ACTOR"


def test_empty_board_is_refused():
    with pytest.raises(SeatConfigurationError) as exc:
        require_independent_seats([])

    assert exc.value.code == "NO_AGENT_SEATS"


def test_a_shared_model_is_stated_rather_than_left_unsaid():
    board = [
        AgentSeat(role="DEA", model="same", instruction_version="V1"),
        AgentSeat(role="QRA", model="same", instruction_version="V2"),
    ]

    assert "correlated" in shared_model_note(board)
    assert shared_model_note(seats()) is None


def test_seat_actor_uses_the_agent_prefix_the_runtime_recognises():
    assert seats()[0].actor == "agent:dea"


# --------------------------------------------------------------------------
# Blindness of the sceptical seat
# --------------------------------------------------------------------------


def test_the_sceptical_seat_never_receives_the_proposed_outcome():
    """It cannot rubber-stamp a conclusion it was never shown."""
    sceptic = AgentSeat(role="SR", model="m", instruction_version="SR-001")

    brief = build_brief(sceptic, target=TARGET, evidence=EVIDENCE, proposed_outcome="PASS")

    assert brief.blind is True
    assert brief.proposed_outcome is None
    assert "proposed_outcome" not in brief.target
    assert "recommendation" not in brief.target
    # It still gets the evidence and its adversarial question.
    assert brief.evidence == tuple(EVIDENCE)
    assert "fail to establish" in brief.question


def test_a_sighted_seat_does_receive_the_proposed_outcome():
    analyst = AgentSeat(role="DEA", model="m", instruction_version="DEA-001")

    brief = build_brief(analyst, target=TARGET, evidence=EVIDENCE, proposed_outcome="PASS")

    assert brief.blind is False
    assert brief.proposed_outcome == "PASS"
    assert brief.target["proposed_outcome"] == "PASS"


def test_blind_and_sighted_briefs_hash_differently():
    sceptic = AgentSeat(role="SR", model="m", instruction_version="SR-001")
    analyst = AgentSeat(role="DEA", model="m", instruction_version="DEA-001")

    blind = build_brief(sceptic, target=TARGET, evidence=EVIDENCE, proposed_outcome="PASS")
    sighted = build_brief(analyst, target=TARGET, evidence=EVIDENCE, proposed_outcome="PASS")

    assert blind.brief_hash != sighted.brief_hash


# --------------------------------------------------------------------------
# Seat output is analysis, never evidence
# --------------------------------------------------------------------------


def test_seat_output_cannot_be_used_as_evidence():
    output = seat_output(
        seats()[0],
        summary="Attribution rests on case captions.",
        body={"severity": "SEV-2"},
        evidence_ids=("EV-1",),
        verified_by="a-human",
        verified_at="2026-07-26T00:00:00Z",
    )

    assert output.is_evidence is False
    # The seat actor already carries the prefix; it must not be stacked twice.
    assert output.agent_id == "agent:dea"
    assert output.method_used == "agent:dea"
    with pytest.raises(AgentGovernanceError):
        assert_not_evidence(output, position="finding support")


def test_seat_output_records_its_human_verifier():
    output = seat_output(
        seats()[0],
        summary="s",
        body={},
        evidence_ids=(),
        verified_by="a-human",
        verified_at="2026-07-26T00:00:00Z",
    )

    assert output.human_reviewed is True


# --------------------------------------------------------------------------
# Challenge sheets
# --------------------------------------------------------------------------


def sheet(severity: str, seat: str = "Sceptical Review") -> ChallengeSheet:
    return ChallengeSheet(
        seat=seat,
        severity=severity,
        target="A claim",
        problem="It does not hold.",
        impact="It matters because of X.",
        fix="Do Y.",
        evidence_ids=("EV-1",),
    )


def test_sheets_are_ordered_worst_first():
    ordered = sort_sheets([sheet("SEV-3"), sheet("SEV-1"), sheet("SEV-2")])

    assert [item.severity for item in ordered] == ["SEV-1", "SEV-2", "SEV-3"]


def test_a_blocking_sheet_is_reported_as_blocking():
    result = summarise([sheet("SEV-1"), sheet("SEV-3")])

    assert result["blocking"] == 1
    assert result["decision_blocked"] is True


def test_only_sev3_does_not_block():
    assert summarise([sheet("SEV-3")])["decision_blocked"] is False


def test_rendering_labels_notes_differently_from_challenges():
    assert render_review([sheet("SEV-1")]).startswith("CHALLENGE   SEV-1")
    assert render_review([sheet("SEV-3")]).startswith("NOTE   SEV-3")


def test_a_seat_can_report_finding_nothing():
    rendered = render_review([], [NoChallenge("QA & Reliability", "Gate logic coverage")])

    assert "NO CHALLENGE" in rendered
    assert "Nothing that changes the verdict" in rendered


def test_an_empty_board_says_so_rather_than_looking_clean():
    assert render_review([], []) == "No seat reported. The board did not sit."


def test_sheets_become_finding_records_declaring_ai_use():
    record = to_finding_record(
        sheet("SEV-2"),
        review_id="REV-1",
        finding_id="FND-1",
        reviewer="agent:sr",
        reviewer_role="SR",
        artefact_version="abcdef1234567890",
        date_raised="2026-07-26T00:00:00Z",
        spec_reference="RBS-008 section 7",
        evidence_reference="EVI-1",
        ai_description="model-c/SR-001",
    )

    assert record["ai_assistance"] == {
        "used": True,
        "description": "model-c/SR-001",
        "human_verified": True,
    }
    assert record["remediation_requirement"] == "Do Y."


def test_a_note_carries_no_remediation_requirement():
    record = to_finding_record(
        sheet("SEV-3"),
        review_id="REV-1",
        finding_id="FND-1",
        reviewer="agent:bca",
        reviewer_role="BCA",
        artefact_version="abcdef1234567890",
        date_raised="2026-07-26T00:00:00Z",
        spec_reference="RBS-003 section 7",
        evidence_reference="EVI-1",
        ai_description="model-x/BCA-001",
    )

    assert record["remediation_requirement"] is None


# --------------------------------------------------------------------------
# Board health
# --------------------------------------------------------------------------


def test_a_silent_board_is_flagged_not_congratulated():
    health = board_health({"DEA": 0, "QRA": 0, "SR": 0})

    assert health["dissent_observed"] is False
    assert health["silent_seats"] == ["DEA", "QRA", "SR"]
    assert "not a clean bill of health" in health["note"]


def test_a_dissenting_board_reports_its_challenges():
    health = board_health({"DEA": 1, "QRA": 0, "SR": 2})

    assert health["dissent_observed"] is True
    assert health["challenges_raised"] == 3
    assert health["silent_seats"] == ["QRA"]
