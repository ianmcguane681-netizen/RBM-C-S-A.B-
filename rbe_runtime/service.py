"""Application service for the incremental RBE v0.1 workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from controlled_authority.rbm_package import validate_decision_bundle
from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.canonical import (
    canonical_hash,
    deterministic_id,
    sha256_digest,
    utc_now,
)
from rbe_runtime.constants import ENGINE_VERSION, RUNTIME_SCHEMA_VERSION
from rbe_runtime.decision import DecisionEngine
from rbe_runtime.errors import RBEError
from rbe_runtime.models import (
    BoardDecision,
    EvidenceReference,
    ExecutionMode,
    Finding,
    ReadinessAssessment,
    ReviewAssignment,
    ReviewerReport,
    ReviewSession,
)
from rbe_runtime.profile import ProfilePolicy, is_agent_actor
from rbe_runtime.schemas import SchemaRegistry
from rbe_runtime.state_machine import CanonicalStateMachine
from rbe_runtime.storage import ReviewStore, open_sqlite_store
from rbe_runtime.validation import (
    validate_finding_submission,
    validate_initiation,
    validate_remediation_submission,
    validate_report_submission,
)
UTC = timezone.utc


class RBERuntime:
    """Coordinate validation, persistence, lifecycle, and deterministic decisions."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        authority: AuthorityBundle | None = None,
        clock: Callable[[], str] = utc_now,
        repository: ReviewStore | None = None,
    ) -> None:
        self.authority = authority or AuthorityBundle.load()
        self.schemas = SchemaRegistry.from_authority(self.authority)
        self.policy = ProfilePolicy.from_authority(self.authority)
        self.state_machine = CanonicalStateMachine.from_register(
            self.authority.state_machine
        )
        self.decisions = DecisionEngine(self.authority.profile)
        if repository is not None and database_path is not None:
            raise TypeError("Provide either database_path or repository, not both")
        if repository is None:
            if database_path is None:
                raise TypeError("database_path is required when repository is not provided")
            repository = open_sqlite_store(
                database_path,
                self.state_machine,
                clock=clock,
            )
        self.repository: ReviewStore = repository
        self.clock = clock

    def initiate_review(
        self,
        initiation: dict[str, Any],
        *,
        actor: str,
        idempotency_key: str,
        execution_mode: ExecutionMode = ExecutionMode.ADVISORY_DRY_RUN,
    ) -> dict[str, Any]:
        if actor != initiation.get("board_chair"):
            raise RBEError(
                "RBE_INITIATION_ACTOR_MISMATCH",
                "Only the named Board Chair may initiate this review",
                "RBE-ES-ORC-004",
            )
        role_seats = validate_initiation(
            self.authority,
            self.schemas,
            self.policy,
            initiation,
            execution_mode,
        )
        session = ReviewSession(
            session_id=initiation["review_id"],
            target_type="GIT_COMMIT",
            target_id=initiation["repository"],
            target_version=initiation["artefact_sha"],
            methodology_id=initiation["methodology_profile_id"],
            methodology_version=initiation["methodology_version"],
            methodology_checksum=initiation["methodology_checksum"],
            engine_version=ENGINE_VERSION,
            schema_version=RUNTIME_SCHEMA_VERSION,
            status=self.state_machine.initial_state,
            aggregate_version=0,
            execution_mode=execution_mode.value,
            binding=bool(initiation["binding"]),
            created_at=initiation["review_date"],
            created_by=actor,
        )
        assignments = tuple(
            ReviewAssignment(
                assignment_id=deterministic_id(
                    "ASN", session.session_id, seat.role, seat.actor
                ),
                session_id=session.session_id,
                reviewer_role=seat.role,
                reviewer_actor=seat.actor,
                reviewer_spec_id=seat.reviewer_spec_id,
                status="PLANNED",
                sequence=seat.sequence,
                required=True,
                conflict_declared=False,
                has_material_conflict=False,
                assigned_at=initiation["review_date"],
            )
            for seat in role_seats
        )
        return self.repository.create_review(
            session,
            initiation,
            assignments,
            actor=actor,
            idempotency_key=idempotency_key,
            package_root_hash=self.authority.profile_manifest["root_sha256"],
        )

    def register_evidence(
        self,
        session_id: str,
        *,
        locator: str,
        content: bytes,
        description: str,
        source_tier: str | None,
        provenance: dict[str, Any],
        actor: str,
        idempotency_key: str,
        reference_type: str = "FILE",
        reference_id: str | None = None,
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if session.status not in {
            "DRAFT",
            "SUBMITTED",
            "INTAKE_VALIDATION",
            "RETURNED",
            "ACCEPTED",
        }:
            raise RBEError(
                "RBE_EVIDENCE_LOCKED",
                "Evidence cannot be registered after the evidence lock",
                "RBE-ES-ORC-010",
            )
        if not content or not locator.strip() or not description.strip() or not provenance:
            raise RBEError(
                "RBE_EVIDENCE_INCOMPLETE",
                "Evidence requires content, locator, description, and provenance",
                "RBE-ES-ORC-007",
            )
        content_hash = sha256_digest(content)
        reference = EvidenceReference(
            reference_id=reference_id
            or deterministic_id("EVI", session_id, locator, content_hash),
            session_id=session_id,
            reference_type=reference_type,
            locator=locator,
            content_sha256=content_hash,
            description=description,
            source_tier=source_tier,
            provenance=provenance,
            registered_at=self.clock(),
        )
        return self.repository.register_evidence(
            reference,
            content,
            actor=actor,
            idempotency_key=idempotency_key,
        )

    def resubmit_review_package(
        self,
        session_id: str,
        initiation: dict[str, Any],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        previous = self.repository.get_initiation(session_id)
        if session.status != "RETURNED":
            raise RBEError(
                "RBE_SUCCESSOR_PACKAGE_NOT_OPEN",
                "Review-package resubmission is available only in RETURNED state",
                "RBE-ES-ORC-005",
            )
        if actor != previous["board_chair"]:
            raise RBEError(
                "RBE_RESUBMISSION_ACTOR_MISMATCH",
                "Only the named Board Chair may resubmit the review package",
                "RBE-ES-ORC-004",
            )
        validate_initiation(
            self.authority,
            self.schemas,
            self.policy,
            initiation,
            ExecutionMode(session.execution_mode),
        )
        immutable_fields = {
            "review_id",
            "tier",
            "artefact_sha",
            "repository",
            "architecture_authority",
            "methodology_profile_id",
            "methodology_version",
            "methodology_status",
            "methodology_checksum",
            "manifest_root_sha256",
            "human_approval_record",
            "binding",
            "board_chair",
            "methodology_auditor",
            "sceptical_reviewer",
            "specialists",
        }
        changed = sorted(
            field
            for field in immutable_fields
            if initiation.get(field) != previous.get(field)
        )
        if changed:
            raise RBEError(
                "RBE_SUCCESSOR_PACKAGE_IDENTITY_CHANGED",
                "A successor package cannot change sealed review identity or authority",
                "RBE-ES-ORC-010",
                {"fields": changed},
            )
        return self.repository.append_review_package(
            session_id,
            initiation,
            self.authority.profile_manifest["root_sha256"],
            actor=actor,
            idempotency_key=idempotency_key,
        )

    def respond_to_assignment(
        self,
        session_id: str,
        assignment_id: str,
        *,
        actor: str,
        has_material_conflict: bool,
        conflict_basis: str | None,
        human_signature_ref: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if session.status != "ASSIGNMENT":
            raise RBEError(
                "RBE_ASSIGNMENT_RESPONSE_NOT_OPEN",
                "Assignment responses are accepted only in ASSIGNMENT state",
                "RBE-ES-ORC-005",
                {"session_state": session.status},
            )
        return self.repository.record_assignment_response(
            session_id,
            assignment_id,
            actor=actor,
            has_material_conflict=has_material_conflict,
            conflict_basis=conflict_basis,
            human_signature_ref=human_signature_ref,
            idempotency_key=idempotency_key,
        )

    def submit_report(
        self,
        session_id: str,
        assignment_id: str,
        *,
        raw_report: dict[str, Any],
        raw_findings: tuple[dict[str, Any], ...],
        finding_categories: dict[str, str],
        summary: str,
        recommendation: str,
        evidence_reference_ids: tuple[str, ...],
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        assignments = {
            item.assignment_id: item
            for item in self.repository.list_assignments(session_id)
        }
        assignment = assignments.get(assignment_id)
        if assignment is None:
            raise RBEError(
                "RBE_ASSIGNMENT_NOT_FOUND",
                "Review assignment was not found in the session",
                "RBE-ES-ORC-006",
            )
        if actor != assignment.reviewer_actor:
            raise RBEError(
                "RBE_REPORT_ACTOR_MISMATCH",
                "Only the assigned human reviewer may submit this report",
                "RBE-ES-ORC-006",
            )
        self._require_report_phase(session, assignment, assignments)
        evidence = self.repository.list_evidence(session_id)
        reference_ids = validate_report_submission(
            self.schemas,
            self.policy,
            session=session,
            assignment=assignment,
            evidence=evidence,
            raw_record=raw_report,
            summary=summary,
            recommendation=recommendation,
            evidence_reference_ids=evidence_reference_ids,
        )
        declared_findings = tuple(raw_report["finding_ids"])
        received_findings = tuple(item["finding_id"] for item in raw_findings)
        if set(finding_categories) != set(declared_findings):
            raise RBEError(
                "RBE_FINDING_CATEGORY_SET_MISMATCH",
                "Each declared finding requires exactly one normalized category",
                "RBE-ES-DOM-002",
            )
        report = ReviewerReport(
            report_id=raw_report["report_id"],
            session_id=session_id,
            assignment_id=assignment_id,
            report_version=1,
            raw_record=raw_report,
            raw_record_sha256=canonical_hash(raw_report),
            summary=summary,
            recommendation=recommendation,
            finding_ids=declared_findings,
            evidence_reference_ids=reference_ids,
            ai_assisted=bool(raw_report["ai_assistance"].get("used")),
            human_verified=(
                not raw_report["ai_assistance"].get("used")
                or raw_report["ai_assistance"].get("human_verified") is True
            ),
            human_signature_ref=raw_report["human_signature_ref"],
            submitted_at=self.clock(),
        )
        findings: list[Finding] = []
        for raw_finding in raw_findings:
            refs = validate_finding_submission(
                self.schemas,
                session=session,
                source_report=report,
                assignment=assignment,
                evidence=evidence,
                raw_record=raw_finding,
            )
            findings.append(
                Finding(
                    finding_id=raw_finding["finding_id"],
                    session_id=session_id,
                    source_report_id=report.report_id,
                    severity=raw_finding["severity"],
                    category=finding_categories[raw_finding["finding_id"]],
                    title=raw_finding["title"],
                    description=raw_finding["detail"],
                    evidence_reference_ids=refs,
                    status=raw_finding["status"],
                    remediation_required=raw_finding["severity"] in {"SEV-1", "SEV-2"},
                    raw_record=raw_finding,
                    raw_record_sha256=canonical_hash(raw_finding),
                    created_at=raw_finding["date_raised"],
                )
            )
        if set(received_findings) != set(declared_findings):
            raise RBEError(
                "RBE_REPORT_FINDING_SET_MISMATCH",
                "Submitted findings do not match the report declaration",
                "RBE-ES-DOM-002",
            )
        return self.repository.submit_review(
            report,
            tuple(findings),
            actor=actor,
            idempotency_key=idempotency_key,
        )

    def submit_remediation_plan(
        self,
        session_id: str,
        raw_plan: dict[str, Any],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        initiation = self.repository.get_initiation(session_id)
        if self.repository.get_decision_candidate(session_id) is not None:
            raise RBEError(
                "RBE_DECISION_INPUTS_FROZEN",
                "Remediation cannot be added after a decision candidate is frozen",
                "RBE-ES-DEC-001",
            )
        if session.status not in {"CHALLENGE", "CONSOLIDATION"}:
            raise RBEError(
                "RBE_REMEDIATION_SUBMISSION_NOT_OPEN",
                "Remediation is accepted only before decision preparation",
                "RBE-ES-ORC-005",
                {"session_state": session.status},
            )
        if actor != initiation["methodology_auditor"]:
            raise RBEError(
                "RBE_REMEDIATION_ACTOR_MISMATCH",
                "Only the assigned Methodology Auditor may validate remediation",
                "RBE-ES-ORC-004",
            )
        findings = {
            finding.finding_id: finding
            for finding in self.repository.list_findings(session_id)
        }
        plans = validate_remediation_submission(
            self.schemas,
            session=session,
            methodology_auditor=initiation["methodology_auditor"],
            findings=findings,
            raw_record=raw_plan,
        )
        return self.repository.submit_remediation_plans(
            session_id,
            plans,
            actor=actor,
            idempotency_key=idempotency_key,
        )

    def assess_readiness(
        self,
        session_id: str,
        *,
        additional_blockers: tuple[str, ...] = (),
    ) -> ReadinessAssessment:
        session = self.repository.get_session(session_id)
        initiation = self.repository.get_initiation(session_id)
        assignments = self.repository.list_assignments(session_id)
        reports = self.repository.list_reports(session_id)
        report_assignment_ids = {report.assignment_id for report in reports}
        unmet: list[str] = []
        blockers = set(additional_blockers)
        if session.status == "VOID":
            blockers.add("SESSION_VOID")
        if initiation["input_process_status"] != "READY":
            unmet.append("INPUT_PACKAGE_NOT_READY")
        for assignment in assignments:
            if not assignment.conflict_declared:
                unmet.append(f"MISSING_INDEPENDENCE_DECLARATION:{assignment.reviewer_role}")
            if assignment.has_material_conflict:
                blockers.add(f"MATERIAL_CONFLICT:{assignment.reviewer_role}")
            if assignment.required and assignment.assignment_id not in report_assignment_ids:
                unmet.append(f"MISSING_REPORT:{assignment.reviewer_role}")
            if assignment.required and assignment.status != "COMPLETED":
                unmet.append(f"INCOMPLETE_ASSIGNMENT:{assignment.reviewer_role}")

        assignment_by_id = {
            assignment.assignment_id: assignment for assignment in assignments
        }
        specialist_sufficiency = [
            report.raw_record["evidence_sufficiency"]
            for report in reports
            if assignment_by_id[report.assignment_id].reviewer_role not in {"MA", "SR"}
        ]
        substantive_sufficient = bool(specialist_sufficiency) and (
            "INSUFFICIENT" not in specialist_sufficiency
            and "SUFFICIENT" in specialist_sufficiency
        )
        if session.status == "VOID":
            process_status = "VOID"
        elif blockers:
            process_status = "BLOCKED"
        elif unmet:
            process_status = "PROCEDURALLY_INCOMPLETE"
        else:
            process_status = "READY"
        return ReadinessAssessment(
            process_status=process_status,
            unmet_prerequisites=tuple(sorted(set(unmet))),
            process_blockers=tuple(sorted(blockers)),
            substantive_evidence_sufficient=substantive_sufficient,
        )

    def prepare_decision_candidate(
        self,
        session_id: str,
        *,
        actor: str,
        idempotency_key: str,
        process_blockers: tuple[str, ...] = (),
        counter_evidence_reference_ids: tuple[str, ...] = (),
        blocker_resolution_evidence_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        initiation = self.repository.get_initiation(session_id)
        if actor != initiation["board_chair"]:
            raise RBEError(
                "RBE_DECISION_ASSEMBLER_MISMATCH",
                "Only the named Board Chair may assemble the decision candidate",
                "RBE-ES-ORC-004",
            )
        if session.status not in {"CONSOLIDATION", "BLOCKED"}:
            raise RBEError(
                "RBE_DECISION_PREPARATION_NOT_OPEN",
                "Decision candidates are prepared in CONSOLIDATION or BLOCKED",
                "RBE-ES-ORC-005",
                {"session_state": session.status},
            )
        evidence = self.repository.list_evidence(session_id)
        unknown_counter = sorted(
            set(counter_evidence_reference_ids) - set(evidence)
        )
        unknown_resolution = sorted(
            set(blocker_resolution_evidence_ids) - set(evidence)
        )
        if unknown_counter or unknown_resolution:
            raise RBEError(
                "RBE_UNKNOWN_EVIDENCE_REFERENCE",
                "Decision inputs reference evidence outside the session",
                "RBE-ES-ORC-007",
                {
                    "counter_evidence": unknown_counter,
                    "resolution_evidence": unknown_resolution,
                },
            )
        previous = self.repository.get_decision_candidate(session_id)
        if (
            session.status == "BLOCKED"
            and previous is not None
            and previous["evaluation"].process_status == "BLOCKED"
            and not process_blockers
            and not blocker_resolution_evidence_ids
        ):
            raise RBEError(
                "RBE_BLOCKER_RESOLUTION_EVIDENCE_REQUIRED",
                "Clearing a recorded blocker requires registered resolution evidence",
                "RBE-ES-ORC-012",
            )
        readiness = self.assess_readiness(
            session_id,
            additional_blockers=process_blockers,
        )
        if readiness.process_status == "PROCEDURALLY_INCOMPLETE":
            raise RBEError(
                "RBE_REVIEW_NOT_READY_FOR_CONSOLIDATION",
                "Required procedural records are incomplete",
                "RBE-ES-ORC-011",
                {"unmet_prerequisites": list(readiness.unmet_prerequisites)},
            )
        findings = self.repository.list_findings(session_id)
        accepted_remediation = tuple(
            sorted(
                plan.finding_id
                for plan in self.repository.list_remediation_plans(session_id)
                if plan.status == "ACCEPTED"
            )
        )
        evaluation = self.decisions.evaluate(
            findings=findings,
            process_status=readiness.process_status,
            substantive_evidence_sufficient=(
                readiness.substantive_evidence_sufficient
            ),
            accepted_remediation_finding_ids=accepted_remediation,
            counter_evidence=tuple(sorted(counter_evidence_reference_ids)),
            process_blockers=readiness.process_blockers,
        )
        manifest = self._decision_input_manifest(
            session_id,
            readiness,
            blocker_resolution_evidence_ids,
        )
        result = self.repository.save_decision_candidate(
            session_id,
            evaluation,
            manifest,
            actor=actor,
            idempotency_key=idempotency_key,
        )
        return {**result, "readiness": readiness.to_dict()}

    def ratify_decision(
        self,
        session_id: str,
        *,
        actor: str,
        board_chair_signature_ref: str,
        governance_validator: str | None = None,
        governance_validation_ref: str | None = None,
        idempotency_key: str,
        single_authority_rationale: str = "",
    ) -> dict[str, Any]:
        """Sign the decision.

        Passing a governance validator ratifies under the ordinary four-eyes
        control. Omitting it ratifies under single authority, which the profile
        permits only while non-binding and which is recorded permanently on the
        decision so it is never mistaken for a two-signature one.
        """

        session = self.repository.get_session(session_id)
        initiation = self.repository.get_initiation(session_id)
        if session.status != "GOVERNANCE_VALIDATION":
            raise RBEError(
                "RBE_RATIFICATION_NOT_OPEN",
                "Ratification is available only in GOVERNANCE_VALIDATION",
                "RBE-ES-ORC-005",
            )
        single_authority = governance_validator is None
        if single_authority:
            self._require_single_authority_permitted(actor, initiation)
        elif actor != initiation["board_chair"] or governance_validator != initiation[
            "methodology_auditor"
        ]:
            raise RBEError(
                "RBE_RATIFICATION_ACTOR_MISMATCH",
                "Ratification actors must match the initiated Board Chair and MA",
                "RBE-ES-ORC-004",
            )
        else:
            self._require_human_ratifiers(actor, governance_validator)
        candidate = self.repository.get_decision_candidate(session_id)
        if candidate is None:
            raise RBEError(
                "RBE_DECISION_CANDIDATE_MISSING",
                "No frozen machine decision candidate exists",
                "RBE-ES-ORC-011",
            )
        evaluation = candidate["evaluation"]
        if evaluation.process_status != "READY":
            raise RBEError(
                "RBE_NON_READY_DECISION_CANNOT_BE_RATIFIED",
                "Only a READY candidate may become a signed decision",
                "RBE-ES-DEC-004",
            )
        signed_at = self.clock()
        profile = self.authority.profile
        merge_permitted = bool(
            profile["status"] == "ACTIVE"
            and profile["binding"]
            and evaluation.outcome in {"PASS", "PASS_WITH_FINDINGS"}
            and not single_authority
        )
        decision = BoardDecision(
            decision_id=deterministic_id(
                "DEC", session_id, candidate["candidate_id"], evaluation.snapshot_hash
            ),
            session_id=session_id,
            status="SIGNED",
            binding=bool(profile["binding"]),
            merge_permitted=merge_permitted,
            execution_mode=session.execution_mode,
            evaluation=evaluation,
            finding_snapshot_hash=evaluation.snapshot_hash,
            artifact_manifest_hash=candidate["artifact_manifest_hash"],
            computed_at=candidate["computed_at"],
            signed_at=signed_at,
            single_authority=single_authority,
        )
        return self.repository.save_decision(
            decision,
            candidate["artifact_manifest"],
            candidate["candidate_id"],
            {
                "board_chair": actor,
                "board_chair_signature_ref": board_chair_signature_ref,
                "governance_validator": governance_validator,
                "governance_validation_ref": governance_validation_ref,
                "single_authority_rationale": single_authority_rationale,
            },
            actor=actor,
            idempotency_key=idempotency_key,
        )

    def _require_single_authority_permitted(
        self, actor: str, initiation: dict[str, Any]
    ) -> None:
        """Single authority is a labelled reduction, not a relaxation.

        It exists so a one-human organisation can sign a decision at all. It is
        refused once the methodology is binding, because a binding decision signed
        by one person is exactly what the four-eyes control prevents.
        """

        policy = self.authority.profile.get("single_authority_policy") or {}
        if policy.get("single_authority_permitted") is not True:
            raise RBEError(
                "RBE_SINGLE_AUTHORITY_NOT_PERMITTED",
                "This methodology does not permit single-authority ratification",
                "RBE-ES-DEC-005",
            )
        profile = self.authority.profile
        if policy.get("permitted_only_when_profile_non_binding") is True and (
            profile["status"] == "ACTIVE" or profile["binding"]
        ):
            raise RBEError(
                "RBE_SINGLE_AUTHORITY_FORBIDDEN_WHEN_BINDING",
                "A binding methodology requires two separated human authorities",
                "RBE-ES-DEC-005",
                {"profile_status": profile["status"], "binding": profile["binding"]},
            )
        if is_agent_actor(actor):
            raise RBEError(
                "RBE_RATIFICATION_AUTHORITY_NOT_HUMAN",
                "Ratification requires human authorities; an agent may review but not sign",
                "RBE-ES-DES-002",
                {"actors": [actor]},
            )
        if policy.get("authority_must_be_board_chair") is True and actor != initiation[
            "board_chair"
        ]:
            raise RBEError(
                "RBE_SINGLE_AUTHORITY_MUST_BE_CHAIR",
                "Only the named Board Chair may ratify under single authority",
                "RBE-ES-ORC-004",
            )

    def _require_human_ratifiers(self, chair: str, validator: str) -> None:
        """Ratification is a human authority, whoever did the reviewing.

        The profile permits agent-held reviewer seats but keeps ratification and
        publication human. Without this check an agent seated as Methodology
        Auditor would also be signing the decision it reviewed, which is both
        non-human authority and a collapse of the four-eyes control.
        """

        policy = self.authority.profile.get("agent_seat_policy") or {}
        if policy.get("ratification_authority_must_be_human") is not True:
            return
        non_human = sorted(
            actor for actor in (chair, validator) if is_agent_actor(actor)
        )
        if non_human:
            raise RBEError(
                "RBE_RATIFICATION_AUTHORITY_NOT_HUMAN",
                "Ratification requires human authorities; an agent may review but not sign",
                "RBE-ES-DES-002",
                {"actors": non_human},
            )

    def _require_human_publisher(self, actor: str) -> None:
        policy = self.authority.profile.get("agent_seat_policy") or {}
        if policy.get("publication_authority_must_be_human") is not True:
            return
        if is_agent_actor(actor):
            raise RBEError(
                "RBE_PUBLICATION_AUTHORITY_NOT_HUMAN",
                "Publication requires a human authority",
                "RBE-ES-DES-002",
                {"actor": actor},
            )

    def supersede_published_decision(
        self,
        session_id: str,
        *,
        actor: str,
        board_chair_signature_ref: str,
        governance_validator: str,
        governance_validation_ref: str,
        appeal_reference: str,
        idempotency_key: str,
        process_blockers: tuple[str, ...] = (),
        counter_evidence_reference_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Replace a published decision with an appeal panel's successor.

        The original record is never rewritten: it is flagged SUPERSEDED, stays in
        the history, and the successor is computed, ratified and recorded through
        the same machinery as any other decision. The appeal reference enters the
        successor's decision-input manifest, so the successor is content-addressed
        to the appeal that produced it and cannot collide with the original.
        """

        session = self.repository.get_session(session_id)
        initiation = self.repository.get_initiation(session_id)
        if session.status != "APPEAL_REVIEW":
            raise RBEError(
                "RBE_SUPERSESSION_NOT_OPEN",
                "A decision is superseded only during APPEAL_REVIEW",
                "RBE-ES-ORC-005",
                {"session_state": session.status},
            )
        if actor != initiation["board_chair"] or governance_validator != initiation[
            "methodology_auditor"
        ]:
            raise RBEError(
                "RBE_RATIFICATION_ACTOR_MISMATCH",
                "Ratification actors must match the initiated Board Chair and MA",
                "RBE-ES-ORC-004",
            )
        self._require_human_ratifiers(actor, governance_validator)
        if not appeal_reference.strip():
            raise RBEError(
                "RBE_APPEAL_REFERENCE_REQUIRED",
                "Supersession must cite the appeal it resolves",
                "RBE-ES-DEC-005",
            )
        current = self.repository.get_decision(session_id)
        history = self.repository.get_decision_history(session_id)
        recorded = [item for item in history if item.superseded]
        if recorded:
            # A replay arrives after the original has already been flipped, so
            # the repository's idempotency cache is unreachable from here; the
            # service must recognise the recorded supersession itself. A session
            # sees at most one supersession, so any different appeal is a conflict.
            latest_candidate = self.repository.get_decision_candidate(session_id)
            if (
                current is None
                or latest_candidate is None
                or latest_candidate["artifact_manifest"].get("appeal_reference")
                != appeal_reference
            ):
                raise RBEError(
                    "RBE_SUPERSESSION_ALREADY_RECORDED",
                    "This session's decision has already been superseded by a different appeal",
                    "RBE-ES-LIF-005",
                    {"superseded_decision_id": recorded[-1].decision_id},
                )
            return {
                "superseded_decision_id": recorded[-1].decision_id,
                "successor": current.to_dict(),
            }
        if current is None or self.repository.get_publication(session_id) is None:
            raise RBEError(
                "RBE_UNPUBLISHED_DECISION_CANNOT_BE_SUPERSEDED",
                "Only a published decision can be superseded on appeal",
                "RBE-ES-DEC-005",
            )
        evidence = self.repository.list_evidence(session_id)
        unknown_counter = sorted(set(counter_evidence_reference_ids) - set(evidence))
        if unknown_counter:
            raise RBEError(
                "RBE_UNKNOWN_EVIDENCE_REFERENCE",
                "Decision inputs reference evidence outside the session",
                "RBE-ES-ORC-007",
                {"counter_evidence": unknown_counter},
            )
        readiness = self.assess_readiness(
            session_id, additional_blockers=process_blockers
        )
        findings = self.repository.list_findings(session_id)
        accepted_remediation = tuple(
            sorted(
                plan.finding_id
                for plan in self.repository.list_remediation_plans(session_id)
                if plan.status == "ACCEPTED"
            )
        )
        evaluation = self.decisions.evaluate(
            findings=findings,
            process_status=readiness.process_status,
            substantive_evidence_sufficient=readiness.substantive_evidence_sufficient,
            accepted_remediation_finding_ids=accepted_remediation,
            counter_evidence=tuple(sorted(counter_evidence_reference_ids)),
            process_blockers=readiness.process_blockers,
        )
        if evaluation.process_status != "READY":
            raise RBEError(
                "RBE_NON_READY_DECISION_CANNOT_BE_RATIFIED",
                "Only a READY candidate may become a signed decision",
                "RBE-ES-DEC-004",
            )
        manifest = self._decision_input_manifest(session_id, readiness, ())
        manifest["appeal_reference"] = appeal_reference
        candidate = self.repository.save_decision_candidate(
            session_id,
            evaluation,
            manifest,
            actor=actor,
            idempotency_key=f"{idempotency_key}-candidate",
        )
        signed_at = self.clock()
        profile = self.authority.profile
        merge_permitted = bool(
            profile["status"] == "ACTIVE"
            and profile["binding"]
            and evaluation.outcome in {"PASS", "PASS_WITH_FINDINGS"}
        )
        successor = BoardDecision(
            decision_id=deterministic_id(
                "DEC", session_id, candidate["candidate_id"], evaluation.snapshot_hash
            ),
            session_id=session_id,
            status="SIGNED",
            binding=bool(profile["binding"]),
            merge_permitted=merge_permitted,
            execution_mode=session.execution_mode,
            evaluation=evaluation,
            finding_snapshot_hash=evaluation.snapshot_hash,
            artifact_manifest_hash=candidate["artifact_manifest_hash"],
            computed_at=candidate["computed_at"],
            signed_at=signed_at,
        )
        return self.repository.supersede_decision(
            successor,
            candidate["artifact_manifest"],
            candidate["candidate_id"],
            {
                "board_chair": actor,
                "board_chair_signature_ref": board_chair_signature_ref,
                "governance_validator": governance_validator,
                "governance_validation_ref": governance_validation_ref,
            },
            superseded_decision_id=current.decision_id,
            appeal_reference=appeal_reference,
            actor=actor,
            idempotency_key=idempotency_key,
        )

    def publish_decision(
        self,
        session_id: str,
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        # SUPERSEDED is included because the successor decision must be published
        # before the session can reach FINAL with a successor_publication_id.
        if session.status not in {"DECIDED", "SUPERSEDED"}:
            raise RBEError(
                "RBE_PUBLICATION_NOT_OPEN",
                "Publication is available only after DECIDED",
                "RBE-ES-API-003",
            )
        self._require_human_publisher(actor)
        decision = self.repository.get_decision(session_id)
        ratification = self.repository.get_ratification(session_id)
        candidate = self.repository.get_decision_candidate(session_id)
        if decision is None or ratification is None or candidate is None:
            raise RBEError(
                "RBE_PUBLICATION_PACKAGE_INCOMPLETE",
                "Publication requires candidate, decision, and ratification records",
                "RBE-ES-ORC-011",
            )
        initiation = self.repository.get_initiation(session_id)
        findings = self.repository.list_findings(session_id)
        unresolved_statuses = set(
            self.authority.profile["unresolved_finding_statuses"]
        )
        unresolved = [item for item in findings if item.status in unresolved_statuses]
        accepted_remediation = {
            plan.finding_id
            for plan in self.repository.list_remediation_plans(session_id)
            if plan.status == "ACCEPTED"
        }
        snapshot = {
            "snapshot_sha256": decision.finding_snapshot_hash,
            "unresolved_sev1": sum(item.severity == "SEV-1" for item in unresolved),
            "unresolved_sev2": sum(item.severity == "SEV-2" for item in unresolved),
            "accepted_sev2_remediation": sum(
                item.severity == "SEV-2" and item.finding_id in accepted_remediation
                for item in unresolved
            ),
            "unresolved_finding_ids": sorted(item.finding_id for item in unresolved),
        }
        profile = self.authority.profile
        common = {
            "review_id": session_id,
            "artefact_sha": session.target_version,
            "methodology_profile_id": profile["profile_id"],
            "methodology_version": profile["version"],
            "methodology_status": profile["status"],
            "methodology_checksum": profile["checksum"],
            "binding": decision.binding,
            "process_status": decision.evaluation.process_status,
            "outcome": decision.evaluation.outcome,
            "merge_permitted": decision.merge_permitted,
            "board_chair": ratification["board_chair"],
            "governance_validator": ratification["governance_validator"],
            "single_authority": decision.single_authority,
        }
        board_record = {
            "schema_version": "2.2.0",
            **common,
            "tier": initiation["tier"],
            "finding_snapshot": snapshot,
            "substantive_evidence_sufficient": candidate["artifact_manifest"][
                "substantive_evidence_sufficient"
            ],
            "decision_basis": decision.evaluation.explanation,
            "board_chair_signature_ref": ratification[
                "board_chair_signature_ref"
            ],
            "governance_validation_ref": ratification[
                "governance_validation_ref"
            ],
            "decision_date": decision.signed_at,
            "correction_refs": [],
        }
        published_at = self.clock()
        parsed = datetime.fromisoformat(published_at[:-1] + "+00:00")
        expires_at = (parsed + timedelta(hours=72)).astimezone(UTC).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        indicator = {
            "schema_version": "2.2.0",
            **common,
            "review_risk_tier": initiation["tier"],
            "publication_authority": actor,
            "published_at": published_at,
            "unresolved_sev1_count": snapshot["unresolved_sev1"],
            "unresolved_sev2_count": snapshot["unresolved_sev2"],
            "expires_at": expires_at,
            "correction_ref": None,
        }
        self.schemas.validate("tpl-bdr", board_record)
        self.schemas.validate("tpl-mri", indicator)
        try:
            validate_decision_bundle(
                initiation,
                board_record,
                indicator,
                profile=profile,
                manifest=self.authority.profile_manifest,
            )
        except ValueError as exc:
            raise RBEError(
                "RBE_PUBLICATION_BUNDLE_INVALID",
                "The RBM decision bundle failed cross-record validation",
                "RBE-ES-SCH-008",
                {"validation_error": str(exc)},
            ) from exc
        publication = self.repository.save_publication(
            session_id,
            decision.decision_id,
            indicator,
            actor=actor,
            idempotency_key=idempotency_key,
        )
        return {
            **publication,
            "board_decision_record": board_record,
        }

    def advance(
        self,
        session_id: str,
        target_state: str,
        *,
        actor: str,
        idempotency_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        initiation = self.repository.get_initiation(session_id)
        if actor != initiation["board_chair"]:
            raise RBEError(
                "RBE_TRANSITION_ACTOR_MISMATCH",
                "Only the named Board Chair may advance the review lifecycle",
                "RBE-ES-ORC-004",
            )
        self.state_machine.require_transition(session.status, target_state)
        self._require_transition_prerequisites(
            session,
            target_state,
            metadata or {},
        )
        return self.repository.transition(
            session_id,
            target_state,
            actor=actor,
            idempotency_key=idempotency_key,
            expected_version=session.aggregate_version,
            metadata=metadata,
        )

    def _require_report_phase(
        self,
        session: ReviewSession,
        assignment: ReviewAssignment,
        assignments: dict[str, ReviewAssignment],
    ) -> None:
        role = assignment.reviewer_role
        if role not in {"MA", "SR"} and session.status != "INDEPENDENT_REVIEW":
            raise RBEError(
                "RBE_SPECIALIST_REVIEW_NOT_OPEN",
                "Specialist reports belong to INDEPENDENT_REVIEW",
                "RBE-ES-ORC-005",
            )
        if role in {"MA", "SR"} and session.status != "CHALLENGE":
            raise RBEError(
                "RBE_GOVERNANCE_REVIEW_NOT_OPEN",
                "SR and MA reports belong to the CHALLENGE phase",
                "RBE-ES-ORC-005",
            )
        if role == "SR":
            incomplete_specialists = [
                item.reviewer_role
                for item in assignments.values()
                if item.reviewer_role not in {"MA", "SR"}
                and item.status != "COMPLETED"
            ]
            if incomplete_specialists:
                raise RBEError(
                    "RBE_SR_INPUTS_INCOMPLETE",
                    "Sceptical review requires all specialist reports",
                    "RBE-ES-ORC-005",
                    {"roles": sorted(incomplete_specialists)},
                )
        if role == "MA":
            incomplete_others = [
                item.reviewer_role
                for item in assignments.values()
                if item.reviewer_role != "MA" and item.status != "COMPLETED"
            ]
            if incomplete_others:
                raise RBEError(
                    "RBE_MA_INPUTS_INCOMPLETE",
                    "Methodology audit closes only after all other reports",
                    "RBE-ES-ORC-005",
                    {"roles": sorted(incomplete_others)},
                )

    def _require_transition_prerequisites(
        self,
        session: ReviewSession,
        target: str,
        metadata: dict[str, Any],
    ) -> None:
        source = session.status
        initiation = self.repository.get_initiation(session.session_id)
        assignments = self.repository.list_assignments(session.session_id)
        evidence = self.repository.list_evidence(session.session_id)
        candidate = self.repository.get_decision_candidate(session.session_id)
        decision = self.repository.get_decision(session.session_id)
        publication = self.repository.get_publication(session.session_id)

        if (source, target) == ("INTAKE_VALIDATION", "ACCEPTED") and initiation[
            "input_process_status"
        ] != "READY":
            self._prerequisite_error("INPUT_PACKAGE_NOT_READY")
        if (source, target) == ("INTAKE_VALIDATION", "RETURNED") and initiation[
            "input_process_status"
        ] == "READY":
            self._prerequisite_error("NO_INTAKE_DEFECT_RECORDED")
        if (source, target) == ("RETURNED", "SUBMITTED"):
            latest_package = self.repository.get_latest_package(session.session_id)
            if (
                latest_package["package_version"] <= 1
                or metadata.get("successor_package_id")
                != latest_package["package_id"]
            ):
                self._prerequisite_error("SUCCESSOR_SUBMISSION_REQUIRED")
        if (source, target) == ("RETURNED", "WITHDRAWN") and not metadata.get(
            "withdrawal_confirmation"
        ):
            self._prerequisite_error("WITHDRAWAL_CONFIRMATION_REQUIRED")
        if (source, target) == ("ACCEPTED", "EVIDENCE_LOCKED") and not evidence:
            self._prerequisite_error("NO_REGISTERED_EVIDENCE")
        if (source, target) == ("EVIDENCE_LOCKED", "ASSIGNMENT") and not assignments:
            self._prerequisite_error("NO_REQUIRED_ASSIGNMENTS")
        if (source, target) == ("ASSIGNMENT", "INDEPENDENT_REVIEW"):
            incomplete = [
                item.reviewer_role
                for item in assignments
                if item.required
                and (
                    item.status != "ACCEPTED"
                    or not item.conflict_declared
                    or item.has_material_conflict
                )
            ]
            if incomplete:
                self._prerequisite_error(
                    "ASSIGNMENT_ACCEPTANCE_OR_CONFLICT_CHECK_INCOMPLETE",
                    roles=sorted(incomplete),
                )
        if (source, target) == ("INDEPENDENT_REVIEW", "CHALLENGE"):
            incomplete = [
                item.reviewer_role
                for item in assignments
                if item.reviewer_role not in {"MA", "SR"}
                and item.status != "COMPLETED"
            ]
            if incomplete:
                self._prerequisite_error(
                    "SPECIALIST_REPORTS_INCOMPLETE", roles=sorted(incomplete)
                )
        if (source, target) == ("CHALLENGE", "CLARIFICATION") and not metadata.get(
            "clarification_scope"
        ):
            self._prerequisite_error("CLARIFICATION_SCOPE_REQUIRED")
        if (source, target) == ("CLARIFICATION", "INDEPENDENT_REVIEW") and not metadata.get(
            "material_answer_requires_reassessment"
        ):
            self._prerequisite_error("MATERIAL_REASSESSMENT_REQUIRED")
        if (source, target) == ("CLARIFICATION", "CHALLENGE") and not metadata.get(
            "response_reference"
        ):
            self._prerequisite_error("CLARIFICATION_RESPONSE_REQUIRED")
        if (source, target) == ("CHALLENGE", "CONSOLIDATION"):
            incomplete = [
                item.reviewer_role
                for item in assignments
                if item.required and item.status != "COMPLETED"
            ]
            if incomplete:
                self._prerequisite_error(
                    "REQUIRED_REPORTS_INCOMPLETE", roles=sorted(incomplete)
                )
        if (source, target) == ("CONSOLIDATION", "GOVERNANCE_VALIDATION") and candidate is None:
            self._prerequisite_error("DECISION_CANDIDATE_MISSING")
        if (source, target) == ("GOVERNANCE_VALIDATION", "BLOCKED") and (
            candidate is None or candidate["evaluation"].process_status != "BLOCKED"
        ):
            self._prerequisite_error("BLOCKING_CONDITION_NOT_RECORDED")
        if (source, target) == ("BLOCKED", "GOVERNANCE_VALIDATION") and (
            candidate is None or candidate["evaluation"].process_status != "READY"
        ):
            self._prerequisite_error("BLOCKING_CONDITION_NOT_RESOLVED")
        if (source, target) == ("BLOCKED", "VOID") and not metadata.get(
            "invalidation_reason"
        ):
            self._prerequisite_error("INVALIDATION_REASON_REQUIRED")
        if (source, target) == ("GOVERNANCE_VALIDATION", "DECIDED") and (
            decision is None or decision.status != "SIGNED"
        ):
            self._prerequisite_error("SIGNED_DECISION_MISSING")
        if (source, target) == ("DECIDED", "PUBLISHED") and publication is None:
            self._prerequisite_error("CONTROLLED_PUBLICATION_MISSING")
        metadata_requirements = {
            ("PUBLISHED", "APPEALED"): "appeal_record_id",
            ("PUBLISHED", "FINAL"): "appeal_window_closed_at",
            ("APPEALED", "APPEAL_REVIEW"): "appeal_panel_reference",
            ("APPEAL_REVIEW", "UPHELD"): "appeal_rationale",
            ("APPEAL_REVIEW", "SUPERSEDED"): "successor_decision_id",
            ("APPEAL_REVIEW", "REMANDED"): "remand_scope",
            ("REMANDED", "ASSIGNMENT"): "successor_session_id",
            ("UPHELD", "FINAL"): "appeal_report_id",
            ("SUPERSEDED", "FINAL"): "successor_publication_id",
            ("FINAL", "ARCHIVED"): "archive_integrity_reference",
        }
        required_metadata = metadata_requirements.get((source, target))
        if required_metadata and not metadata.get(required_metadata):
            self._prerequisite_error(
                f"{required_metadata.upper()}_REQUIRED"
            )
        # These two transitions previously checked only that the metadata field
        # was non-empty, so any string passed as a successor. They now have to
        # name records that actually exist in the store.
        if (source, target) == ("APPEAL_REVIEW", "SUPERSEDED"):
            history = self.repository.get_decision_history(session.session_id)
            superseded_recorded = any(item.superseded for item in history)
            if (
                decision is None
                or not superseded_recorded
                or metadata.get("successor_decision_id") != decision.decision_id
            ):
                self._prerequisite_error(
                    "SUCCESSOR_DECISION_NOT_RECORDED",
                    successor_decision_id=metadata.get("successor_decision_id"),
                    current_decision_id=None if decision is None else decision.decision_id,
                )
        if (source, target) == ("SUPERSEDED", "FINAL") and (
            publication is None
            or metadata.get("successor_publication_id")
            != publication["publication_id"]
        ):
            self._prerequisite_error(
                "SUCCESSOR_PUBLICATION_NOT_RECORDED",
                successor_publication_id=metadata.get("successor_publication_id"),
            )

    def _decision_input_manifest(
        self,
        session_id: str,
        readiness: ReadinessAssessment,
        blocker_resolution_evidence_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        evidence = self.repository.list_evidence(session_id)
        reports = self.repository.list_reports(session_id)
        findings = self.repository.list_findings(session_id)
        plans = self.repository.list_remediation_plans(session_id)
        return {
            "schema_id": "rbe.decision-input-manifest",
            "schema_version": "1.0.0",
            "session_id": session_id,
            "profile": {
                "id": self.authority.profile["profile_id"],
                "version": self.authority.profile["version"],
                "checksum": self.authority.profile["checksum"],
                "status": self.authority.profile["status"],
            },
            "substantive_evidence_sufficient": (
                readiness.substantive_evidence_sufficient
            ),
            "process_status": readiness.process_status,
            "process_blockers": list(readiness.process_blockers),
            "blocker_resolution_evidence_ids": sorted(
                blocker_resolution_evidence_ids
            ),
            "evidence": [
                {
                    "reference_id": item.reference_id,
                    "content_sha256": item.content_sha256,
                }
                for item in sorted(evidence.values(), key=lambda value: value.reference_id)
            ],
            "reports": [
                {
                    "report_id": item.report_id,
                    "raw_record_sha256": item.raw_record_sha256,
                }
                for item in reports
            ],
            "findings": [
                {
                    "finding_id": item.finding_id,
                    "raw_record_sha256": item.raw_record_sha256,
                }
                for item in findings
            ],
            "remediation_plans": [
                {
                    "plan_id": item.plan_id,
                    "raw_record_sha256": item.raw_record_sha256,
                    "status": item.status,
                }
                for item in plans
            ],
        }

    @staticmethod
    def _prerequisite_error(code: str, **details: Any) -> None:
        raise RBEError(
            "RBE_TRANSITION_PREREQUISITE_FAILED",
            f"Transition prerequisite failed: {code}",
            "RBE-ES-ORC-012",
            {"prerequisite": code, **details},
        )
