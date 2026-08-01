"""One review replacing another, which nothing could record until now.

`supersede_decision` is the appeal path: a panel replacing a decision inside one session,
gated on APPEAL_REVIEW. It cannot express what happened with USDC, where a second review
at a higher tier replaced the first. `parent_session_id` existed on `review_sessions` from
the first migration and was never written by anything, so a reader of decision 0001 found
`superseded: False` and believed it.

The guards here all exist because the alternative is a supersession that means nothing:
one review replacing a review of a different subject, a decision replacing one signed
after it, or a review quietly replacing itself.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime
from tests.test_rbe_runtime_service import NOW, prepare_to_consolidation

CHAIR = "human-chair"
LATER = "2026-08-02T00:00:00Z"


def decided(runtime: RBERuntime, review_id: str, *, repository: str | None = None) -> None:
    """Carry one review from initiation to a signed decision."""

    prepare_to_consolidation(runtime, review_id, repository=repository)
    runtime.prepare_decision_candidate(
        review_id, actor=CHAIR, idempotency_key=f"candidate-{review_id}"
    )
    runtime.advance(
        review_id, "GOVERNANCE_VALIDATION", actor=CHAIR, idempotency_key=f"gv-{review_id}"
    )
    runtime.ratify_decision(
        review_id,
        actor=CHAIR,
        board_chair_signature_ref=f"SIG-{review_id}",
        idempotency_key=f"ratify-{review_id}",
        single_authority_rationale="Sole human authority.",
    )


@pytest.fixture
def two_decided_reviews(tmp_path: Path):
    """Two reviews of the same subject, the second signed after the first."""

    runtime = RBERuntime(tmp_path / "supersession.sqlite3", clock=lambda: NOW)
    decided(runtime, "REV-FIRST")
    runtime.clock = lambda: LATER
    decided(runtime, "REV-SECOND")
    return runtime, "REV-FIRST", "REV-SECOND"


@pytest.fixture
def decided_reviews_of_two_subjects(tmp_path: Path):
    runtime = RBERuntime(tmp_path / "subjects.sqlite3", clock=lambda: NOW)
    decided(runtime, "REV-USDC")
    runtime.clock = lambda: LATER
    decided(runtime, "REV-OTHER", repository="ianmcguane681-netizen/Something-Else")
    return runtime, "REV-USDC", "REV-OTHER"


def link(runtime, successor, superseded, actor=CHAIR):
    return runtime.link_review_supersession(
        successor,
        supersedes_session_id=superseded,
        actor=actor,
        idempotency_key=f"supersede-{successor}-{superseded}",
    )


class TestTheLinkIsRecorded:
    def test_the_successor_points_at_what_it_replaced(self, two_decided_reviews):
        runtime, first, second = two_decided_reviews

        link(runtime, second, first)

        assert runtime.repository.get_session(second).parent_session_id == first

    def test_the_replaced_decision_is_marked_superseded(self, two_decided_reviews):
        runtime, first, second = two_decided_reviews

        link(runtime, second, first)

        history = runtime.repository.get_decision_history(first)
        assert any(d.superseded for d in history)

    def test_the_replaced_decision_stays_readable(self, two_decided_reviews):
        """Superseded is a status, not a deletion. The earlier finding set is still the
        record of what was known then, and a reader tracing why it was replaced needs it."""

        runtime, first, second = two_decided_reviews

        link(runtime, second, first)

        assert runtime.repository.get_decision_history(first)

    def test_the_replaced_decision_survives_export(self, two_decided_reviews, tmp_path):
        """The claim above was false where it mattered most.

        `get_decision`, `get_ratification` and `get_publication` all filter
        `superseded = 0`, which is right for "what stands now" and wrong for an export.
        Superseding RBM003-USDC-0001 emptied its own bundle -- decision, ratification and
        publication all null -- leaving a review that appeared never to have decided
        anything. The record of why a decision was replaced is worthless without it.
        """

        from rbe_runtime.artifacts import ArtifactExporter

        runtime, first, second = two_decided_reviews
        link(runtime, second, first)

        out = tmp_path / "superseded-export"
        ArtifactExporter(runtime.repository, runtime.authority).export(first, out)

        import json

        exported = json.loads((out / "decision.json").read_text(encoding="utf-8"))
        assert exported["decision"] is not None, "a superseded decision must still export"
        assert exported["decision"]["status"] == "SUPERSEDED"
        assert exported["ratification"] is not None, "its signature must survive too"

    def test_the_link_is_idempotent(self, two_decided_reviews):
        runtime, first, second = two_decided_reviews

        once = link(runtime, second, first)
        twice = link(runtime, second, first)

        assert once == twice


class TestWhatItRefuses:
    def test_a_review_cannot_supersede_itself(self, two_decided_reviews):
        runtime, _first, second = two_decided_reviews

        with pytest.raises(RBEError) as caught:
            link(runtime, second, second)

        assert caught.value.code == "RBE_SUPERSESSION_SELF_REFERENCE"

    def test_a_different_subject_is_refused(self, decided_reviews_of_two_subjects):
        """A review of one token says nothing about another. Without this a decision
        about USDC could be recorded as replacing one about something else entirely."""

        runtime, usdc, other = decided_reviews_of_two_subjects

        with pytest.raises(RBEError) as caught:
            link(runtime, other, usdc)

        assert caught.value.code == "RBE_SUPERSESSION_SUBJECT_MISMATCH"

    def test_an_earlier_decision_cannot_supersede_a_later_one(self, two_decided_reviews):
        """Ratification order, not artefact order. Artefact versions are opaque strings --
        a block height here, a commit sha elsewhere -- so comparing them generically would
        be guesswork, while when a decision was signed is unambiguous."""

        runtime, first, second = two_decided_reviews

        with pytest.raises(RBEError) as caught:
            link(runtime, first, second)

        assert caught.value.code == "RBE_SUPERSESSION_ORDER"

    def test_only_the_board_chair_may_declare_it(self, two_decided_reviews):
        runtime, first, second = two_decided_reviews

        with pytest.raises(RBEError) as caught:
            link(runtime, second, first, actor="agent:ma")

        assert caught.value.code == "RBE_TRANSITION_ACTOR_MISMATCH"

    def test_an_unknown_review_is_refused(self, two_decided_reviews):
        runtime, _first, second = two_decided_reviews

        with pytest.raises(RBEError) as caught:
            link(runtime, second, "REV-NEVER-EXISTED")

        assert caught.value.code == "RBE_SESSION_NOT_FOUND"
