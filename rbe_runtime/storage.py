"""Persistence boundary for the RBE runtime.

Business workflow services depend on :class:`ReviewStore`, not on SQLite.  The
Foundation runtime wires SQLite through ``open_sqlite_store`` as its default local
adapter; another durable backend can implement the same contract without changing
review orchestration or artifact generation.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from rbe_runtime.models import (
    AuditEntry,
    BoardDecision,
    DecisionEvaluation,
    EvidenceReference,
    Finding,
    RemediationPlan,
    ReviewAssignment,
    ReviewerReport,
    ReviewSession,
)
from rbe_runtime.state_machine import CanonicalStateMachine


@runtime_checkable
class ReviewStore(Protocol):
    """Port required by review orchestration and artifact export."""

    def create_review(
        self,
        session: ReviewSession,
        initiation: dict[str, Any],
        assignments: Iterable[ReviewAssignment],
        *,
        actor: str,
        idempotency_key: str,
        package_root_hash: str,
    ) -> dict[str, Any]: ...

    def transition(
        self,
        session_id: str,
        target_state: str,
        *,
        actor: str,
        idempotency_key: str,
        expected_version: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def register_evidence(
        self,
        reference: EvidenceReference,
        content: bytes,
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def record_assignment_response(
        self,
        session_id: str,
        assignment_id: str,
        *,
        actor: str,
        has_material_conflict: bool,
        conflict_basis: str | None,
        human_signature_ref: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def submit_review(
        self,
        report: ReviewerReport,
        findings: Iterable[Finding],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def submit_remediation_plans(
        self,
        session_id: str,
        plans: Iterable[RemediationPlan],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def get_session(self, session_id: str) -> ReviewSession: ...

    def get_initiation(self, session_id: str) -> dict[str, Any]: ...

    def get_latest_package(self, session_id: str) -> dict[str, Any]: ...

    def append_review_package(
        self,
        session_id: str,
        initiation: dict[str, Any],
        package_root_hash: str,
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def save_decision_candidate(
        self,
        session_id: str,
        evaluation: DecisionEvaluation,
        artifact_manifest: dict[str, Any],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def get_decision_candidate(self, session_id: str) -> dict[str, Any] | None: ...

    def save_decision(
        self,
        decision: BoardDecision,
        artifact_manifest: dict[str, Any],
        candidate_id: str,
        ratification: dict[str, str],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def get_decision(self, session_id: str) -> BoardDecision | None: ...

    def get_decision_history(self, session_id: str) -> tuple[BoardDecision, ...]: ...

    def supersede_decision(
        self,
        successor: BoardDecision,
        artifact_manifest: dict[str, Any],
        candidate_id: str,
        ratification: dict[str, str],
        *,
        superseded_decision_id: str,
        appeal_reference: str,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def get_ratification(self, session_id: str) -> dict[str, Any] | None: ...

    def save_publication(
        self,
        session_id: str,
        decision_id: str,
        indicator: dict[str, Any],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def get_publication(self, session_id: str) -> dict[str, Any] | None: ...

    def list_assignments(self, session_id: str) -> tuple[ReviewAssignment, ...]: ...

    def list_evidence(self, session_id: str) -> dict[str, EvidenceReference]: ...

    def get_evidence_content(self, reference_id: str) -> bytes: ...

    def list_reports(self, session_id: str) -> tuple[ReviewerReport, ...]: ...

    def list_findings(self, session_id: str) -> tuple[Finding, ...]: ...

    def list_remediation_plans(
        self, session_id: str
    ) -> tuple[RemediationPlan, ...]: ...

    def list_audit(self, session_id: str) -> tuple[AuditEntry, ...]: ...

    def verify_audit(self, session_id: str) -> dict[str, Any]: ...

    def verify_all_audits(self) -> None: ...


def open_sqlite_store(
    path: str | Path,
    state_machine: CanonicalStateMachine,
    *,
    clock: Callable[[], str],
) -> ReviewStore:
    """Create the Foundation SQLite adapter behind the storage port."""

    from rbe_runtime.repository import SQLiteRepository

    return SQLiteRepository(path, state_machine, clock=clock)
