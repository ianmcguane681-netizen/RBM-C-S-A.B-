"""Appeal supersession is now recordable without weakening immutability.

RBM-001 has always declared APPEAL_REVIEW -> SUPERSEDED, but the version 1 schema
made it impossible to record: decisions rejected every UPDATE, the partial unique
index blocked a second decision, and ratifications and publications were unique
per session. The record could therefore keep asserting a decision that had been
overturned.

Migration 2 legalises exactly one mutation - flipping a signed decision to
SUPERSEDED with every other column unchanged - and moves ratification and
publication uniqueness from the session to the decision. Everything else stays as
frozen as before, and these tests hold it there.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.canonical import sha256_digest
from rbe_runtime.errors import RBEError
from rbe_runtime.repository import MIGRATIONS, SQLiteRepository
from rbe_runtime.service import RBERuntime
from rbe_runtime.state_machine import CanonicalStateMachine
from tests.test_rbe_runtime_service import NOW, prepare_to_consolidation

APPEAL = {
    "appeal_record_id": "APL-0001",
    "appeal_panel_reference": "PANEL-0001",
    "appeal_reference": "APL-0001",
}


def runtime_at_published(tmp_path: Path, review_id: str = "REV-APPEAL") -> RBERuntime:
    runtime = RBERuntime(tmp_path / "appeal.sqlite3", clock=lambda: NOW)
    prepare_to_consolidation(runtime, review_id)
    runtime.prepare_decision_candidate(
        review_id, actor="human-chair", idempotency_key="candidate"
    )
    runtime.advance(
        review_id, "GOVERNANCE_VALIDATION", actor="human-chair", idempotency_key="s09"
    )
    runtime.ratify_decision(
        review_id,
        actor="human-chair",
        board_chair_signature_ref="SIG-BC-1",
        governance_validator="human-ma",
        governance_validation_ref="SIG-GV-1",
        idempotency_key="ratify",
    )
    runtime.advance(review_id, "DECIDED", actor="human-chair", idempotency_key="s10")
    runtime.publish_decision(
        review_id, actor="human-publisher", idempotency_key="publish"
    )
    runtime.advance(review_id, "PUBLISHED", actor="human-chair", idempotency_key="s11")
    return runtime


def to_appeal_review(runtime: RBERuntime, review_id: str = "REV-APPEAL") -> None:
    runtime.advance(
        review_id,
        "APPEALED",
        actor="human-chair",
        idempotency_key="s12",
        metadata={"appeal_record_id": APPEAL["appeal_record_id"]},
    )
    runtime.advance(
        review_id,
        "APPEAL_REVIEW",
        actor="human-chair",
        idempotency_key="s13",
        metadata={"appeal_panel_reference": APPEAL["appeal_panel_reference"]},
    )


def supersede(runtime: RBERuntime, review_id: str = "REV-APPEAL"):
    return runtime.supersede_published_decision(
        review_id,
        actor="human-chair",
        board_chair_signature_ref="SIG-BC-2",
        governance_validator="human-ma",
        governance_validation_ref="SIG-GV-2",
        appeal_reference=APPEAL["appeal_reference"],
        idempotency_key="supersede",
    )


# ---------------------------------------------------------------------------
# Schema: the single legal mutation
# ---------------------------------------------------------------------------


def test_only_the_supersession_flip_is_a_legal_update(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)
    decision = runtime.repository.get_decision("REV-APPEAL")
    connection = sqlite3.connect(tmp_path / "appeal.sqlite3")

    # Any other column stays frozen.
    with pytest.raises(sqlite3.IntegrityError, match="only recording supersession"):
        connection.execute(
            "UPDATE board_decisions SET merge_permitted = 1 WHERE decision_id = ?",
            (decision.decision_id,),
        )
    # The flip cannot smuggle another change alongside it.
    with pytest.raises(sqlite3.IntegrityError, match="only recording supersession"):
        connection.execute(
            """
            UPDATE board_decisions
            SET superseded = 1, status = 'SUPERSEDED', merge_permitted = 1
            WHERE decision_id = ?
            """,
            (decision.decision_id,),
        )
    # The flip itself is legal...
    connection.execute(
        """
        UPDATE board_decisions SET superseded = 1, status = 'SUPERSEDED'
        WHERE decision_id = ?
        """,
        (decision.decision_id,),
    )
    # ...and irreversible: a superseded decision can never come back.
    with pytest.raises(sqlite3.IntegrityError, match="only recording supersession"):
        connection.execute(
            "UPDATE board_decisions SET superseded = 0, status = 'SIGNED' WHERE decision_id = ?",
            (decision.decision_id,),
        )
    connection.rollback()
    connection.close()


def test_delete_remains_impossible(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)
    decision = runtime.repository.get_decision("REV-APPEAL")
    connection = sqlite3.connect(tmp_path / "appeal.sqlite3")

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute(
            "DELETE FROM board_decisions WHERE decision_id = ?", (decision.decision_id,)
        )
    connection.close()


# ---------------------------------------------------------------------------
# Migration: version 1 databases upgrade in place
# ---------------------------------------------------------------------------


def test_v1_database_upgrades_in_place(tmp_path: Path):
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL
        )
        """
    )
    connection.executescript(MIGRATIONS[0][1])
    connection.execute(
        "INSERT INTO schema_migrations VALUES (1, ?, ?)",
        (sha256_digest(MIGRATIONS[0][1].encode("utf-8")), NOW),
    )
    connection.execute(
        """
        INSERT INTO review_sessions VALUES (
            'S-LEGACY','GIT_COMMIT','repo','abc','RBM-001','2.0.0','sha256:x',
            'engine','1.0.0','DRAFT',0,'ADVISORY_DRY_RUN',0,?, 'chair',NULL,NULL
        )
        """,
        (NOW,),
    )
    connection.commit()
    connection.close()

    authority = AuthorityBundle.load()
    repository = SQLiteRepository(
        path,
        CanonicalStateMachine.from_register(authority.state_machine),
        clock=lambda: NOW,
    )

    assert repository.get_session("S-LEGACY").session_id == "S-LEGACY"
    connection = sqlite3.connect(path)
    versions = [
        row[0]
        for row in connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
    ]
    ratification_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'decision_ratifications'"
    ).fetchone()[0]
    connection.close()
    # Against MIGRATIONS rather than a literal, because the claim under test is "a v1
    # database ends up fully migrated", not "there are exactly three migrations". The
    # literal version failed the moment a fourth was added, which tested the wrong thing.
    assert versions == [version for version, _ in MIGRATIONS]
    # Per-session uniqueness is gone; per-decision uniqueness remains, and the
    # governance validator is nullable for single-authority ratification.
    assert "session_id TEXT NOT NULL UNIQUE" not in ratification_sql


# ---------------------------------------------------------------------------
# The full appeal lifecycle
# ---------------------------------------------------------------------------


def test_appeal_supersession_end_to_end(tmp_path: Path):
    review_id = "REV-APPEAL"
    runtime = runtime_at_published(tmp_path)
    original = runtime.repository.get_decision(review_id)
    to_appeal_review(runtime, review_id)

    result = supersede(runtime, review_id)
    successor_id = result["successor"]["decision_id"]
    assert successor_id != original.decision_id
    assert result["superseded_decision_id"] == original.decision_id

    # The current decision is the successor; the original stays readable,
    # flagged, and marked SUPERSEDED - not rewritten, not erased.
    current = runtime.repository.get_decision(review_id)
    assert current.decision_id == successor_id
    history = runtime.repository.get_decision_history(review_id)
    assert {item.decision_id: item.superseded for item in history} == {
        original.decision_id: True,
        successor_id: False,
    }
    superseded_row = next(item for item in history if item.superseded)
    assert superseded_row.status == "SUPERSEDED"
    assert superseded_row.evaluation.snapshot_hash == original.evaluation.snapshot_hash

    # Lifecycle: SUPERSEDED requires the real successor id, then FINAL requires
    # the successor's real publication.
    runtime.advance(
        review_id,
        "SUPERSEDED",
        actor="human-chair",
        idempotency_key="s14",
        metadata={"successor_decision_id": successor_id},
    )
    publication = runtime.publish_decision(
        review_id, actor="human-publisher", idempotency_key="publish-successor"
    )
    runtime.advance(
        review_id,
        "FINAL",
        actor="human-chair",
        idempotency_key="s15",
        metadata={"successor_publication_id": publication["publication_id"]},
    )
    assert runtime.repository.get_session(review_id).status == "FINAL"

    # The audit chain records the supersession and still verifies.
    audit = runtime.repository.list_audit(review_id)
    superseded_events = [item for item in audit if item.event_type == "DECISION_SUPERSEDED"]
    assert len(superseded_events) == 1
    assert superseded_events[0].payload["superseded_decision_id"] == original.decision_id
    assert superseded_events[0].payload["successor_decision_id"] == successor_id
    assert superseded_events[0].payload["appeal_reference"] == APPEAL["appeal_reference"]
    assert runtime.repository.verify_audit(review_id)["valid"] is True


def test_supersession_is_idempotent(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)
    to_appeal_review(runtime)

    first = supersede(runtime)
    second = supersede(runtime)

    assert first == second
    assert len(runtime.repository.get_decision_history("REV-APPEAL")) == 2


def test_a_second_appeal_cannot_reuse_the_recorded_supersession(tmp_path: Path):
    """Replay with the same appeal is idempotent; a different appeal is a conflict."""
    runtime = runtime_at_published(tmp_path)
    to_appeal_review(runtime)
    supersede(runtime)

    with pytest.raises(RBEError) as exc:
        runtime.supersede_published_decision(
            "REV-APPEAL",
            actor="human-chair",
            board_chair_signature_ref="SIG-BC-3",
            governance_validator="human-ma",
            governance_validation_ref="SIG-GV-3",
            appeal_reference="APL-DIFFERENT",
            idempotency_key="supersede-2",
        )

    assert exc.value.code == "RBE_SUPERSESSION_ALREADY_RECORDED"


def test_a_fabricated_successor_id_cannot_advance_the_lifecycle(tmp_path: Path):
    """The prerequisite previously checked only that the field was non-empty."""
    runtime = runtime_at_published(tmp_path)
    to_appeal_review(runtime)
    supersede(runtime)

    with pytest.raises(RBEError) as exc:
        runtime.advance(
            "REV-APPEAL",
            "SUPERSEDED",
            actor="human-chair",
            idempotency_key="s14-bad",
            metadata={"successor_decision_id": "DEC-FABRICATED"},
        )

    assert exc.value.details["prerequisite"] == "SUCCESSOR_DECISION_NOT_RECORDED"


def test_superseded_cannot_be_reached_without_a_recorded_successor(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)
    to_appeal_review(runtime)
    current = runtime.repository.get_decision("REV-APPEAL")

    with pytest.raises(RBEError) as exc:
        runtime.advance(
            "REV-APPEAL",
            "SUPERSEDED",
            actor="human-chair",
            idempotency_key="s14-early",
            metadata={"successor_decision_id": current.decision_id},
        )

    assert exc.value.details["prerequisite"] == "SUCCESSOR_DECISION_NOT_RECORDED"


def test_final_requires_the_successors_real_publication(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)
    to_appeal_review(runtime)
    successor_id = supersede(runtime)["successor"]["decision_id"]
    runtime.advance(
        "REV-APPEAL",
        "SUPERSEDED",
        actor="human-chair",
        idempotency_key="s14",
        metadata={"successor_decision_id": successor_id},
    )

    with pytest.raises(RBEError) as exc:
        runtime.advance(
            "REV-APPEAL",
            "FINAL",
            actor="human-chair",
            idempotency_key="s15-early",
            metadata={"successor_publication_id": "PUB-FABRICATED"},
        )

    assert exc.value.details["prerequisite"] == "SUCCESSOR_PUBLICATION_NOT_RECORDED"


def test_supersession_is_only_available_during_appeal_review(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)

    with pytest.raises(RBEError) as exc:
        supersede(runtime)

    assert exc.value.code == "RBE_SUPERSESSION_NOT_OPEN"


def test_supersession_requires_the_appeal_reference(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)
    to_appeal_review(runtime)

    with pytest.raises(RBEError) as exc:
        runtime.supersede_published_decision(
            "REV-APPEAL",
            actor="human-chair",
            board_chair_signature_ref="SIG-BC-2",
            governance_validator="human-ma",
            governance_validation_ref="SIG-GV-2",
            appeal_reference="   ",
            idempotency_key="supersede",
        )

    assert exc.value.code == "RBE_APPEAL_REFERENCE_REQUIRED"


def test_an_unpublished_decision_cannot_be_superseded(tmp_path: Path):
    """Repository-level guard: appeals overturn published decisions only."""
    review_id = "REV-UNPUB"
    runtime = RBERuntime(tmp_path / "unpub.sqlite3", clock=lambda: NOW)
    prepare_to_consolidation(runtime, review_id)
    runtime.prepare_decision_candidate(
        review_id, actor="human-chair", idempotency_key="candidate"
    )
    runtime.advance(
        review_id, "GOVERNANCE_VALIDATION", actor="human-chair", idempotency_key="s09"
    )
    runtime.ratify_decision(
        review_id,
        actor="human-chair",
        board_chair_signature_ref="SIG-BC-1",
        governance_validator="human-ma",
        governance_validation_ref="SIG-GV-1",
        idempotency_key="ratify",
    )
    signed = runtime.repository.get_decision(review_id)

    with pytest.raises(RBEError) as exc:
        runtime.repository.supersede_decision(
            signed,
            {},
            "DCA-any",
            {
                "board_chair": "human-chair",
                "board_chair_signature_ref": "x",
                "governance_validator": "human-ma",
                "governance_validation_ref": "y",
            },
            superseded_decision_id=signed.decision_id,
            appeal_reference="APL-1",
            actor="human-chair",
            idempotency_key="bad-supersede",
        )

    assert exc.value.code == "RBE_UNPUBLISHED_DECISION_CANNOT_BE_SUPERSEDED"


def test_ratification_and_publication_follow_the_current_decision(tmp_path: Path):
    runtime = runtime_at_published(tmp_path)
    original = runtime.repository.get_decision("REV-APPEAL")
    original_ratification = runtime.repository.get_ratification("REV-APPEAL")
    to_appeal_review(runtime)
    successor_id = supersede(runtime)["successor"]["decision_id"]

    ratification = runtime.repository.get_ratification("REV-APPEAL")
    assert original_ratification["decision_id"] == original.decision_id
    assert ratification["decision_id"] == successor_id
    # The successor is not yet published, so the session has no current
    # publication - which is what gates SUPERSEDED -> FINAL.
    assert runtime.repository.get_publication("REV-APPEAL") is None
