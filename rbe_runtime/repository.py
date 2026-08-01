"""SQLite persistence with atomic commands and a hash-chained audit trail."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, TypeVar

from rbe_runtime.canonical import (
    canonical_hash,
    canonical_json,
    deterministic_id,
    sha256_digest,
    utc_now,
)
from rbe_runtime.constants import RUNTIME_SCHEMA_VERSION
from rbe_runtime.errors import RBEError
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


T = TypeVar("T")


MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE review_sessions (
            session_id TEXT PRIMARY KEY,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_version TEXT NOT NULL,
            methodology_id TEXT NOT NULL,
            methodology_version TEXT NOT NULL,
            methodology_checksum TEXT NOT NULL,
            engine_version TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            status TEXT NOT NULL,
            aggregate_version INTEGER NOT NULL,
            execution_mode TEXT NOT NULL,
            binding INTEGER NOT NULL CHECK (binding IN (0, 1)),
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            completed_at TEXT,
            parent_session_id TEXT REFERENCES review_sessions(session_id)
        );

        CREATE TABLE review_packages (
            package_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            package_version INTEGER NOT NULL CHECK (package_version > 0),
            schema_name TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL,
            package_root_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (session_id, package_version)
        );

        CREATE TABLE review_assignments (
            assignment_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            reviewer_role TEXT NOT NULL,
            reviewer_actor TEXT NOT NULL,
            reviewer_spec_id TEXT NOT NULL,
            status TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence > 0),
            required INTEGER NOT NULL CHECK (required IN (0, 1)),
            conflict_declared INTEGER NOT NULL CHECK (conflict_declared IN (0, 1)),
            has_material_conflict INTEGER NOT NULL CHECK (has_material_conflict IN (0, 1)),
            assigned_at TEXT NOT NULL,
            accepted_at TEXT,
            completed_at TEXT,
            UNIQUE (session_id, reviewer_role),
            UNIQUE (session_id, sequence)
        );

        CREATE TABLE evidence_references (
            reference_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            reference_type TEXT NOT NULL,
            locator TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            content_blob BLOB NOT NULL,
            description TEXT NOT NULL,
            source_tier TEXT,
            provenance_json TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            UNIQUE (session_id, locator, content_sha256)
        );

        CREATE TABLE conflict_declarations (
            declaration_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            assignment_id TEXT NOT NULL UNIQUE REFERENCES review_assignments(assignment_id),
            actor TEXT NOT NULL,
            has_material_conflict INTEGER NOT NULL CHECK (has_material_conflict IN (0, 1)),
            basis TEXT,
            human_signature_ref TEXT NOT NULL,
            declared_at TEXT NOT NULL
        );

        CREATE TABLE review_reports (
            report_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            assignment_id TEXT NOT NULL REFERENCES review_assignments(assignment_id),
            report_version INTEGER NOT NULL CHECK (report_version > 0),
            raw_record_json TEXT NOT NULL,
            raw_record_sha256 TEXT NOT NULL,
            summary TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            finding_ids_json TEXT NOT NULL,
            evidence_reference_ids_json TEXT NOT NULL,
            ai_assisted INTEGER NOT NULL CHECK (ai_assisted IN (0, 1)),
            human_verified INTEGER NOT NULL CHECK (human_verified IN (0, 1)),
            human_signature_ref TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            supersedes_report_id TEXT REFERENCES review_reports(report_id),
            UNIQUE (assignment_id, report_version)
        );

        CREATE TABLE report_evidence_links (
            report_id TEXT NOT NULL REFERENCES review_reports(report_id),
            reference_id TEXT NOT NULL REFERENCES evidence_references(reference_id),
            PRIMARY KEY (report_id, reference_id)
        );

        CREATE TABLE findings (
            finding_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            source_report_id TEXT NOT NULL REFERENCES review_reports(report_id),
            severity TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            evidence_reference_ids_json TEXT NOT NULL,
            status TEXT NOT NULL,
            remediation_required INTEGER NOT NULL CHECK (remediation_required IN (0, 1)),
            raw_record_json TEXT NOT NULL,
            raw_record_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            supersedes_finding_id TEXT REFERENCES findings(finding_id)
        );

        CREATE TABLE remediation_plans (
            plan_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            finding_id TEXT NOT NULL REFERENCES findings(finding_id),
            owner TEXT NOT NULL,
            action TEXT NOT NULL,
            due_date TEXT,
            status TEXT NOT NULL,
            verification_evidence_ids_json TEXT NOT NULL,
            raw_record_json TEXT NOT NULL,
            raw_record_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            supersedes_plan_id TEXT REFERENCES remediation_plans(plan_id),
            UNIQUE (document_id, finding_id)
        );

        CREATE TABLE finding_evidence_links (
            finding_id TEXT NOT NULL REFERENCES findings(finding_id),
            reference_id TEXT NOT NULL REFERENCES evidence_references(reference_id),
            PRIMARY KEY (finding_id, reference_id)
        );

        CREATE TABLE decision_candidates (
            candidate_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            candidate_version INTEGER NOT NULL CHECK (candidate_version > 0),
            evaluation_json TEXT NOT NULL,
            finding_snapshot_hash TEXT NOT NULL,
            artifact_manifest_hash TEXT NOT NULL,
            artifact_manifest_json TEXT NOT NULL,
            computed_at TEXT NOT NULL,
            computed_by TEXT NOT NULL,
            supersedes_candidate_id TEXT REFERENCES decision_candidates(candidate_id),
            UNIQUE (session_id, candidate_version)
        );

        CREATE TABLE board_decisions (
            decision_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            status TEXT NOT NULL,
            binding INTEGER NOT NULL CHECK (binding IN (0, 1)),
            merge_permitted INTEGER NOT NULL CHECK (merge_permitted IN (0, 1)),
            execution_mode TEXT NOT NULL,
            evaluation_json TEXT NOT NULL,
            finding_snapshot_hash TEXT NOT NULL,
            artifact_manifest_hash TEXT NOT NULL,
            artifact_manifest_json TEXT NOT NULL,
            computed_at TEXT NOT NULL,
            signed_at TEXT,
            published_at TEXT,
            published_by TEXT,
            superseded INTEGER NOT NULL DEFAULT 0 CHECK (superseded IN (0, 1))
        );
        CREATE UNIQUE INDEX one_current_decision_per_session
            ON board_decisions(session_id) WHERE superseded = 0;

        CREATE TABLE decision_ratifications (
            decision_id TEXT PRIMARY KEY REFERENCES board_decisions(decision_id),
            candidate_id TEXT NOT NULL UNIQUE REFERENCES decision_candidates(candidate_id),
            session_id TEXT NOT NULL UNIQUE REFERENCES review_sessions(session_id),
            board_chair TEXT NOT NULL,
            board_chair_signature_ref TEXT NOT NULL,
            governance_validator TEXT NOT NULL,
            governance_validation_ref TEXT NOT NULL,
            ratified_at TEXT NOT NULL
        );

        CREATE TABLE publications (
            publication_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE REFERENCES review_sessions(session_id),
            decision_id TEXT NOT NULL UNIQUE REFERENCES board_decisions(decision_id),
            publication_authority TEXT NOT NULL,
            indicator_json TEXT NOT NULL,
            indicator_sha256 TEXT NOT NULL,
            published_at TEXT NOT NULL
        );

        CREATE TABLE audit_log (
            audit_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            sequence INTEGER NOT NULL CHECK (sequence > 0),
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            previous_hash TEXT,
            entry_hash TEXT NOT NULL,
            schema_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            UNIQUE (session_id, sequence)
        );

        CREATE TABLE idempotency_keys (
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            command_name TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (session_id, command_name, idempotency_key)
        );

        CREATE TRIGGER review_packages_no_update
        BEFORE UPDATE ON review_packages BEGIN SELECT RAISE(ABORT, 'review_packages are immutable'); END;
        CREATE TRIGGER review_packages_no_delete
        BEFORE DELETE ON review_packages BEGIN SELECT RAISE(ABORT, 'review_packages are append-only'); END;
        CREATE TRIGGER evidence_references_no_update
        BEFORE UPDATE ON evidence_references BEGIN SELECT RAISE(ABORT, 'evidence_references are immutable'); END;
        CREATE TRIGGER evidence_references_no_delete
        BEFORE DELETE ON evidence_references BEGIN SELECT RAISE(ABORT, 'evidence_references are append-only'); END;
        CREATE TRIGGER conflict_declarations_no_update
        BEFORE UPDATE ON conflict_declarations BEGIN SELECT RAISE(ABORT, 'conflict_declarations are immutable'); END;
        CREATE TRIGGER conflict_declarations_no_delete
        BEFORE DELETE ON conflict_declarations BEGIN SELECT RAISE(ABORT, 'conflict_declarations are append-only'); END;
        CREATE TRIGGER review_reports_no_update
        BEFORE UPDATE ON review_reports BEGIN SELECT RAISE(ABORT, 'review_reports are immutable'); END;
        CREATE TRIGGER review_reports_no_delete
        BEFORE DELETE ON review_reports BEGIN SELECT RAISE(ABORT, 'review_reports are append-only'); END;
        CREATE TRIGGER findings_no_update
        BEFORE UPDATE ON findings BEGIN SELECT RAISE(ABORT, 'findings are immutable'); END;
        CREATE TRIGGER findings_no_delete
        BEFORE DELETE ON findings BEGIN SELECT RAISE(ABORT, 'findings are append-only'); END;
        CREATE TRIGGER remediation_plans_no_update
        BEFORE UPDATE ON remediation_plans BEGIN SELECT RAISE(ABORT, 'remediation_plans are immutable'); END;
        CREATE TRIGGER remediation_plans_no_delete
        BEFORE DELETE ON remediation_plans BEGIN SELECT RAISE(ABORT, 'remediation_plans are append-only'); END;
        CREATE TRIGGER decision_candidates_no_update
        BEFORE UPDATE ON decision_candidates BEGIN SELECT RAISE(ABORT, 'decision_candidates are immutable'); END;
        CREATE TRIGGER decision_candidates_no_delete
        BEFORE DELETE ON decision_candidates BEGIN SELECT RAISE(ABORT, 'decision_candidates are append-only'); END;
        CREATE TRIGGER board_decisions_no_update
        BEFORE UPDATE ON board_decisions BEGIN SELECT RAISE(ABORT, 'board_decisions are immutable'); END;
        CREATE TRIGGER board_decisions_no_delete
        BEFORE DELETE ON board_decisions BEGIN SELECT RAISE(ABORT, 'board_decisions are append-only'); END;
        CREATE TRIGGER decision_ratifications_no_update
        BEFORE UPDATE ON decision_ratifications BEGIN SELECT RAISE(ABORT, 'decision_ratifications are immutable'); END;
        CREATE TRIGGER decision_ratifications_no_delete
        BEFORE DELETE ON decision_ratifications BEGIN SELECT RAISE(ABORT, 'decision_ratifications are append-only'); END;
        CREATE TRIGGER publications_no_update
        BEFORE UPDATE ON publications BEGIN SELECT RAISE(ABORT, 'publications are immutable'); END;
        CREATE TRIGGER publications_no_delete
        BEFORE DELETE ON publications BEGIN SELECT RAISE(ABORT, 'publications are append-only'); END;
        CREATE TRIGGER audit_log_no_update
        BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
        CREATE TRIGGER audit_log_no_delete
        BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;

        CREATE INDEX assignments_by_session ON review_assignments(session_id, sequence);
        CREATE INDEX evidence_by_session ON evidence_references(session_id, reference_id);
        CREATE INDEX reports_by_session ON review_reports(session_id, report_id);
        CREATE INDEX findings_by_session ON findings(session_id, severity, finding_id);
        CREATE INDEX audit_by_session ON audit_log(session_id, sequence);
        """,
    ),
    (
        2,
        """
        -- Appeal supersession. RBM-001 declares APPEAL_REVIEW -> SUPERSEDED, but
        -- version 1 made it unrecordable: board_decisions rejected every UPDATE,
        -- the partial unique index blocked a second decision while superseded
        -- stayed 0, and ratifications/publications were unique per session.
        --
        -- The immutability model is preserved. Exactly one mutation becomes legal:
        -- flipping a signed decision to SUPERSEDED with every other column
        -- unchanged. Nullable columns are compared with IS so NULLs match.
        DROP TRIGGER board_decisions_no_update;
        CREATE TRIGGER board_decisions_no_update
        BEFORE UPDATE ON board_decisions
        WHEN NOT (
            OLD.superseded = 0 AND NEW.superseded = 1
            AND OLD.status = 'SIGNED' AND NEW.status = 'SUPERSEDED'
            AND NEW.decision_id = OLD.decision_id
            AND NEW.session_id = OLD.session_id
            AND NEW.binding = OLD.binding
            AND NEW.merge_permitted = OLD.merge_permitted
            AND NEW.execution_mode = OLD.execution_mode
            AND NEW.evaluation_json = OLD.evaluation_json
            AND NEW.finding_snapshot_hash = OLD.finding_snapshot_hash
            AND NEW.artifact_manifest_hash = OLD.artifact_manifest_hash
            AND NEW.artifact_manifest_json = OLD.artifact_manifest_json
            AND NEW.computed_at = OLD.computed_at
            AND NEW.signed_at IS OLD.signed_at
            AND NEW.published_at IS OLD.published_at
            AND NEW.published_by IS OLD.published_by
        )
        BEGIN SELECT RAISE(ABORT, 'board_decisions permit only recording supersession'); END;

        -- A session may now hold one ratification and one publication per
        -- decision, not one ever. Uniqueness moves from session_id to the
        -- decision, which the partial index already limits to one current row.
        CREATE TABLE decision_ratifications_v2 (
            decision_id TEXT PRIMARY KEY REFERENCES board_decisions(decision_id),
            candidate_id TEXT NOT NULL UNIQUE REFERENCES decision_candidates(candidate_id),
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            board_chair TEXT NOT NULL,
            board_chair_signature_ref TEXT NOT NULL,
            governance_validator TEXT NOT NULL,
            governance_validation_ref TEXT NOT NULL,
            ratified_at TEXT NOT NULL
        );
        INSERT INTO decision_ratifications_v2 SELECT * FROM decision_ratifications;
        DROP TABLE decision_ratifications;
        ALTER TABLE decision_ratifications_v2 RENAME TO decision_ratifications;
        CREATE INDEX ratifications_by_session ON decision_ratifications(session_id);
        CREATE TRIGGER decision_ratifications_no_update
        BEFORE UPDATE ON decision_ratifications BEGIN SELECT RAISE(ABORT, 'decision_ratifications are immutable'); END;
        CREATE TRIGGER decision_ratifications_no_delete
        BEFORE DELETE ON decision_ratifications BEGIN SELECT RAISE(ABORT, 'decision_ratifications are append-only'); END;

        CREATE TABLE publications_v2 (
            publication_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            decision_id TEXT NOT NULL UNIQUE REFERENCES board_decisions(decision_id),
            publication_authority TEXT NOT NULL,
            indicator_json TEXT NOT NULL,
            indicator_sha256 TEXT NOT NULL,
            published_at TEXT NOT NULL
        );
        INSERT INTO publications_v2 SELECT * FROM publications;
        DROP TABLE publications;
        ALTER TABLE publications_v2 RENAME TO publications;
        CREATE INDEX publications_by_session ON publications(session_id);
        CREATE TRIGGER publications_no_update
        BEFORE UPDATE ON publications BEGIN SELECT RAISE(ABORT, 'publications are immutable'); END;
        CREATE TRIGGER publications_no_delete
        BEFORE DELETE ON publications BEGIN SELECT RAISE(ABORT, 'publications are append-only'); END;
        """,
    ),
    (
        3,
        """
        -- Single-authority advisory ratification. An organisation with one human
        -- cannot satisfy the four-eyes control, so previously it could conduct a
        -- full review and never sign the result. This records a one-signature
        -- decision as exactly that, permanently, rather than inventing a second
        -- signatory or quietly relaxing the control.
        ALTER TABLE board_decisions
            ADD COLUMN single_authority INTEGER NOT NULL DEFAULT 0
            CHECK (single_authority IN (0, 1));

        -- The supersession trigger enumerates the columns that must not change.
        -- It has to learn about the new one, or a supersession could silently flip
        -- a two-signature decision into a single-authority one.
        DROP TRIGGER board_decisions_no_update;
        CREATE TRIGGER board_decisions_no_update
        BEFORE UPDATE ON board_decisions
        WHEN NOT (
            OLD.superseded = 0 AND NEW.superseded = 1
            AND OLD.status = 'SIGNED' AND NEW.status = 'SUPERSEDED'
            AND NEW.decision_id = OLD.decision_id
            AND NEW.session_id = OLD.session_id
            AND NEW.binding = OLD.binding
            AND NEW.merge_permitted = OLD.merge_permitted
            AND NEW.execution_mode = OLD.execution_mode
            AND NEW.evaluation_json = OLD.evaluation_json
            AND NEW.finding_snapshot_hash = OLD.finding_snapshot_hash
            AND NEW.artifact_manifest_hash = OLD.artifact_manifest_hash
            AND NEW.artifact_manifest_json = OLD.artifact_manifest_json
            AND NEW.computed_at = OLD.computed_at
            AND NEW.signed_at IS OLD.signed_at
            AND NEW.published_at IS OLD.published_at
            AND NEW.published_by IS OLD.published_by
            AND NEW.single_authority = OLD.single_authority
        )
        BEGIN SELECT RAISE(ABORT, 'board_decisions permit only recording supersession'); END;

        -- A single-authority ratification has no governance validator. Recording
        -- the chair in that column instead would fabricate a second signatory, so
        -- the column becomes nullable and is left empty.
        CREATE TABLE decision_ratifications_v3 (
            decision_id TEXT PRIMARY KEY REFERENCES board_decisions(decision_id),
            candidate_id TEXT NOT NULL UNIQUE REFERENCES decision_candidates(candidate_id),
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            board_chair TEXT NOT NULL,
            board_chair_signature_ref TEXT NOT NULL,
            governance_validator TEXT,
            governance_validation_ref TEXT,
            ratified_at TEXT NOT NULL,
            CHECK (
                (governance_validator IS NULL AND governance_validation_ref IS NULL)
                OR (governance_validator IS NOT NULL AND governance_validation_ref IS NOT NULL)
            )
        );
        INSERT INTO decision_ratifications_v3 SELECT * FROM decision_ratifications;
        DROP TABLE decision_ratifications;
        ALTER TABLE decision_ratifications_v3 RENAME TO decision_ratifications;
        CREATE INDEX ratifications_by_session ON decision_ratifications(session_id);
        CREATE TRIGGER decision_ratifications_no_update
        BEFORE UPDATE ON decision_ratifications BEGIN SELECT RAISE(ABORT, 'decision_ratifications are immutable'); END;
        CREATE TRIGGER decision_ratifications_no_delete
        BEFORE DELETE ON decision_ratifications BEGIN SELECT RAISE(ABORT, 'decision_ratifications are append-only'); END;
        """,
    ),
)


class SQLiteRepository:
    """Durable repository for a single-node, non-production RBE runtime."""

    def __init__(
        self,
        path: str | Path,
        state_machine: CanonicalStateMachine,
        *,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.path = Path(path)
        self.state_machine = state_machine
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()
        self.verify_all_audits()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            connection.close()
            raise RBEError(
                "RBE_SQLITE_FOREIGN_KEYS_DISABLED",
                "SQLite foreign-key enforcement could not be enabled",
                "RBE-ES-PER-001",
            )
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _migrate(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
            rows = connection.execute(
                "SELECT version, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
            supported = {version: sha256_digest(sql.encode("utf-8")) for version, sql in MIGRATIONS}
            if rows and rows[-1]["version"] > max(supported):
                raise RBEError(
                    "RBE_DATABASE_SCHEMA_TOO_NEW",
                    "The database schema is newer than this runtime supports",
                    "RBE-ES-PER-005",
                    {
                        "database_version": rows[-1]["version"],
                        "runtime_schema_version": RUNTIME_SCHEMA_VERSION,
                    },
                )
            for row in rows:
                if supported.get(row["version"]) != row["checksum"]:
                    raise RBEError(
                        "RBE_MIGRATION_CHECKSUM_MISMATCH",
                        "An applied database migration checksum has changed",
                        "RBE-ES-PER-004",
                        {"version": row["version"]},
                    )
            applied = {row["version"] for row in rows}
            for version, sql in MIGRATIONS:
                if version in applied:
                    continue
                connection.executescript(sql)
                connection.execute(
                    "INSERT INTO schema_migrations(version, checksum, applied_at) VALUES (?, ?, ?)",
                    (version, supported[version], self.clock()),
                )
                connection.commit()
        finally:
            connection.close()

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        *,
        session_id: str,
        event_type: str,
        actor: str,
        occurred_at: str,
        payload: dict[str, Any],
    ) -> AuditEntry:
        previous = connection.execute(
            """
            SELECT sequence, entry_hash FROM audit_log
            WHERE session_id = ? ORDER BY sequence DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        sequence = 1 if previous is None else previous["sequence"] + 1
        previous_hash = None if previous is None else previous["entry_hash"]
        hash_payload = {
            "session_id": session_id,
            "sequence": sequence,
            "event_type": event_type,
            "actor": actor,
            "occurred_at": occurred_at,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        entry_hash = canonical_hash(hash_payload)
        entry = AuditEntry(
            audit_id=deterministic_id(
                "AUD", session_id, str(sequence), entry_hash
            ),
            session_id=session_id,
            sequence=sequence,
            event_type=event_type,
            actor=actor,
            occurred_at=occurred_at,
            payload=payload,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        connection.execute(
            """
            INSERT INTO audit_log(
                audit_id, session_id, sequence, event_type, actor, occurred_at,
                payload_json, previous_hash, entry_hash, schema_id, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.audit_id,
                entry.session_id,
                entry.sequence,
                entry.event_type,
                entry.actor,
                entry.occurred_at,
                canonical_json(entry.payload),
                entry.previous_hash,
                entry.entry_hash,
                entry.schema_id,
                entry.schema_version,
            ),
        )
        return entry

    def _session_exists(self, connection: sqlite3.Connection, session_id: str) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM review_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            is not None
        )

    def _run_idempotent(
        self,
        *,
        session_id: str,
        command_name: str,
        idempotency_key: str,
        actor: str,
        payload: dict[str, Any],
        operation: Callable[[sqlite3.Connection, str], dict[str, Any]],
    ) -> dict[str, Any]:
        if not idempotency_key.strip():
            raise RBEError(
                "RBE_IDEMPOTENCY_KEY_REQUIRED",
                "A non-empty idempotency key is required",
                "RBE-ES-LIF-005",
            )
        payload_hash = canonical_hash(payload)
        connection = self._connect()
        pending_error: RBEError | None = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT payload_hash, result_json FROM idempotency_keys
                WHERE session_id = ? AND command_name = ? AND idempotency_key = ?
                """,
                (session_id, command_name, idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] == payload_hash:
                    connection.rollback()
                    return json.loads(existing["result_json"])
                now = self.clock()
                self._append_audit(
                    connection,
                    session_id=session_id,
                    event_type="IDEMPOTENCY_CONFLICT",
                    actor=actor,
                    occurred_at=now,
                    payload={
                        "command": command_name,
                        "idempotency_key": idempotency_key,
                        "original_payload_hash": existing["payload_hash"],
                        "received_payload_hash": payload_hash,
                    },
                )
                connection.commit()
                raise RBEError(
                    "RBE_IDEMPOTENCY_CONFLICT",
                    "The idempotency key was already used with a different payload",
                    "RBE-ES-LIF-005",
                )

            now = self.clock()
            connection.execute("SAVEPOINT command_operation")
            try:
                result = operation(connection, now)
            except RBEError as exc:
                connection.execute("ROLLBACK TO command_operation")
                connection.execute("RELEASE command_operation")
                if self._session_exists(connection, session_id):
                    self._append_audit(
                        connection,
                        session_id=session_id,
                        event_type="COMMAND_REJECTED",
                        actor=actor,
                        occurred_at=now,
                        payload={
                            "command": command_name,
                            "error_code": exc.code,
                            "payload_hash": payload_hash,
                        },
                    )
                connection.commit()
                pending_error = exc
                result = {}
            except sqlite3.IntegrityError as exc:
                connection.execute("ROLLBACK TO command_operation")
                connection.execute("RELEASE command_operation")
                pending_error = RBEError(
                    "RBE_PERSISTENCE_CONSTRAINT",
                    "The command violates a durable record constraint",
                    "RBE-ES-PER-001",
                    {"constraint": str(exc)},
                )
                if self._session_exists(connection, session_id):
                    self._append_audit(
                        connection,
                        session_id=session_id,
                        event_type="COMMAND_REJECTED",
                        actor=actor,
                        occurred_at=now,
                        payload={
                            "command": command_name,
                            "error_code": pending_error.code,
                            "payload_hash": payload_hash,
                        },
                    )
                connection.commit()
                result = {}
            else:
                connection.execute("RELEASE command_operation")
                connection.execute(
                    """
                    INSERT INTO idempotency_keys(
                        session_id, command_name, idempotency_key,
                        payload_hash, result_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        command_name,
                        idempotency_key,
                        payload_hash,
                        canonical_json(result),
                        now,
                    ),
                )
                connection.commit()
            if pending_error is not None:
                raise pending_error
            return result
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def create_review(
        self,
        session: ReviewSession,
        initiation: dict[str, Any],
        assignments: Iterable[ReviewAssignment],
        *,
        actor: str,
        idempotency_key: str,
        package_root_hash: str,
    ) -> dict[str, Any]:
        assignment_list = tuple(assignments)
        payload = {
            "session": session.to_dict(),
            "initiation": initiation,
            "assignments": [item.to_dict() for item in assignment_list],
            "package_root_hash": package_root_hash,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            connection.execute(
                """
                INSERT INTO review_sessions VALUES (
                    :session_id, :target_type, :target_id, :target_version,
                    :methodology_id, :methodology_version, :methodology_checksum,
                    :engine_version, :schema_version, :status, :aggregate_version,
                    :execution_mode, :binding, :created_at, :created_by,
                    :completed_at, :parent_session_id
                )
                """,
                {**session.to_dict(), "binding": int(session.binding)},
            )
            raw_sha256 = canonical_hash(initiation)
            package_id = deterministic_id("PKG", session.session_id, raw_sha256)
            connection.execute(
                """
                INSERT INTO review_packages VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    session.session_id,
                    1,
                    "tpl-rir",
                    canonical_json(initiation),
                    raw_sha256,
                    package_root_hash,
                    now,
                ),
            )
            for assignment in assignment_list:
                connection.execute(
                    """
                    INSERT INTO review_assignments VALUES (
                        :assignment_id, :session_id, :reviewer_role,
                        :reviewer_actor, :reviewer_spec_id, :status, :sequence,
                        :required, :conflict_declared, :has_material_conflict,
                        :assigned_at, :accepted_at, :completed_at
                    )
                    """,
                    {
                        **assignment.to_dict(),
                        "required": int(assignment.required),
                        "conflict_declared": int(assignment.conflict_declared),
                        "has_material_conflict": int(
                            assignment.has_material_conflict
                        ),
                    },
                )
            self._append_audit(
                connection,
                session_id=session.session_id,
                event_type="SESSION_CREATED",
                actor=actor,
                occurred_at=now,
                payload={
                    "initial_state": session.status,
                    "package_id": package_id,
                    "package_sha256": raw_sha256,
                    "assignment_ids": sorted(
                        item.assignment_id for item in assignment_list
                    ),
                    "binding": session.binding,
                    "execution_mode": session.execution_mode,
                },
            )
            return {
                "session_id": session.session_id,
                "status": session.status,
                "aggregate_version": session.aggregate_version,
                "package_id": package_id,
                "assignment_ids": sorted(
                    item.assignment_id for item in assignment_list
                ),
            }

        return self._run_idempotent(
            session_id=session.session_id,
            command_name="create_review",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def transition(
        self,
        session_id: str,
        target_state: str,
        *,
        actor: str,
        idempotency_key: str,
        expected_version: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "target_state": target_state,
            "expected_version": expected_version,
            "metadata": metadata or {},
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            row = connection.execute(
                "SELECT * FROM review_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise RBEError(
                    "RBE_SESSION_NOT_FOUND",
                    "Review session was not found",
                    "RBE-ES-LIF-002",
                    {"session_id": session_id},
                )
            source_state = row["status"]
            self.state_machine.require_transition(source_state, target_state)
            if row["aggregate_version"] != expected_version:
                raise RBEError(
                    "RBE_CONCURRENCY_CONFLICT",
                    "The review session changed after it was read",
                    "RBE-ES-LIF-002",
                    {
                        "expected_version": expected_version,
                        "actual_version": row["aggregate_version"],
                    },
                )
            new_version = expected_version + 1
            completed_at = now if target_state in self.state_machine.terminal_states else None
            updated = connection.execute(
                """
                UPDATE review_sessions
                SET status = ?, aggregate_version = ?, completed_at = ?
                WHERE session_id = ? AND status = ? AND aggregate_version = ?
                """,
                (
                    target_state,
                    new_version,
                    completed_at,
                    session_id,
                    source_state,
                    expected_version,
                ),
            )
            if updated.rowcount != 1:
                raise RBEError(
                    "RBE_CONCURRENCY_CONFLICT",
                    "The transition lost an optimistic concurrency race",
                    "RBE-ES-LIF-002",
                )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type="STATE_TRANSITIONED",
                actor=actor,
                occurred_at=now,
                payload={
                    "source_state": source_state,
                    "target_state": target_state,
                    "aggregate_version": new_version,
                    "metadata": metadata or {},
                },
            )
            return {
                "session_id": session_id,
                "source_state": source_state,
                "status": target_state,
                "aggregate_version": new_version,
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="transition",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def register_evidence(
        self,
        reference: EvidenceReference,
        content: bytes,
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        computed_hash = sha256_digest(content)
        payload = {
            "reference": reference.to_dict(),
            "computed_content_sha256": computed_hash,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            if computed_hash != reference.content_sha256:
                raise RBEError(
                    "RBE_EVIDENCE_HASH_MISMATCH",
                    "Evidence content does not match its declared SHA-256",
                    "RBE-ES-SEC-004",
                    {
                        "declared": reference.content_sha256,
                        "computed": computed_hash,
                    },
                )
            connection.execute(
                """
                INSERT INTO evidence_references(
                    reference_id, session_id, reference_type, locator,
                    content_sha256, content_blob, description, source_tier,
                    provenance_json, registered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reference.reference_id,
                    reference.session_id,
                    reference.reference_type,
                    reference.locator,
                    reference.content_sha256,
                    content,
                    reference.description,
                    reference.source_tier,
                    canonical_json(reference.provenance),
                    reference.registered_at,
                ),
            )
            self._append_audit(
                connection,
                session_id=reference.session_id,
                event_type="EVIDENCE_REGISTERED",
                actor=actor,
                occurred_at=now,
                payload={
                    "reference_id": reference.reference_id,
                    "content_sha256": computed_hash,
                    "locator": reference.locator,
                    "provenance_sha256": canonical_hash(reference.provenance),
                },
            )
            return reference.to_dict()

        return self._run_idempotent(
            session_id=reference.session_id,
            command_name="register_evidence",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

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
    ) -> dict[str, Any]:
        payload = {
            "assignment_id": assignment_id,
            "has_material_conflict": has_material_conflict,
            "conflict_basis": conflict_basis,
            "human_signature_ref": human_signature_ref,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            row = connection.execute(
                """
                SELECT * FROM review_assignments
                WHERE assignment_id = ? AND session_id = ?
                """,
                (assignment_id, session_id),
            ).fetchone()
            if row is None:
                raise RBEError(
                    "RBE_ASSIGNMENT_NOT_FOUND",
                    "Review assignment was not found in the session",
                    "RBE-ES-ORC-006",
                )
            if row["reviewer_actor"] != actor:
                raise RBEError(
                    "RBE_ASSIGNMENT_ACTOR_MISMATCH",
                    "Only the assigned human reviewer may accept the assignment",
                    "RBE-ES-ORC-006",
                )
            if row["status"] != "PLANNED":
                raise RBEError(
                    "RBE_ASSIGNMENT_ALREADY_RESPONDED",
                    "The assignment already has a recorded response",
                    "RBE-ES-ORC-008",
                    {"assignment_status": row["status"]},
                )
            if has_material_conflict and not (conflict_basis or "").strip():
                raise RBEError(
                    "RBE_CONFLICT_BASIS_REQUIRED",
                    "A material conflict declaration requires a recorded basis",
                    "RBE-ES-ORC-003",
                )
            if not human_signature_ref.strip():
                raise RBEError(
                    "RBE_INDEPENDENCE_SIGNATURE_REQUIRED",
                    "A human signature reference is required for the declaration",
                    "RBE-ES-ORC-003",
                )
            status = "DECLINED" if has_material_conflict else "ACCEPTED"
            declaration_id = deterministic_id(
                "CFD", session_id, assignment_id, actor, now
            )
            connection.execute(
                """
                INSERT INTO conflict_declarations(
                    declaration_id, session_id, assignment_id, actor,
                    has_material_conflict, basis, human_signature_ref, declared_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    declaration_id,
                    session_id,
                    assignment_id,
                    actor,
                    int(has_material_conflict),
                    conflict_basis,
                    human_signature_ref,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE review_assignments
                SET status = ?, conflict_declared = 1,
                    has_material_conflict = ?, accepted_at = ?
                WHERE assignment_id = ?
                """,
                (
                    status,
                    int(has_material_conflict),
                    None if has_material_conflict else now,
                    assignment_id,
                ),
            )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type=(
                    "ASSIGNMENT_CONFLICT_DECLARED"
                    if has_material_conflict
                    else "ASSIGNMENT_ACCEPTED"
                ),
                actor=actor,
                occurred_at=now,
                payload={
                    "assignment_id": assignment_id,
                    "declaration_id": declaration_id,
                    "status": status,
                    "has_material_conflict": has_material_conflict,
                    "human_signature_ref": human_signature_ref,
                    "conflict_basis_hash": (
                        canonical_hash(conflict_basis) if conflict_basis else None
                    ),
                },
            )
            return {
                "assignment_id": assignment_id,
                "status": status,
                "has_material_conflict": has_material_conflict,
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="record_assignment_response",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def submit_review(
        self,
        report: ReviewerReport,
        findings: Iterable[Finding],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        finding_list = tuple(findings)
        payload = {
            "report": report.to_dict(),
            "findings": [finding.to_dict() for finding in finding_list],
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            assignment = connection.execute(
                "SELECT * FROM review_assignments WHERE assignment_id = ?",
                (report.assignment_id,),
            ).fetchone()
            if assignment is None or assignment["session_id"] != report.session_id:
                raise RBEError(
                    "RBE_ASSIGNMENT_SESSION_MISMATCH",
                    "Report assignment does not belong to the report session",
                    "RBE-ES-DOM-001",
                )
            if assignment["status"] != "ACCEPTED":
                raise RBEError(
                    "RBE_ASSIGNMENT_NOT_ACCEPTED",
                    "Only accepted assignments may submit a report",
                    "RBE-ES-ORC-006",
                )
            received_findings = {finding.finding_id for finding in finding_list}
            if received_findings != set(report.finding_ids):
                raise RBEError(
                    "RBE_REPORT_FINDING_SET_MISMATCH",
                    "Submitted findings do not match the report declaration",
                    "RBE-ES-DOM-002",
                    {
                        "declared": sorted(report.finding_ids),
                        "received": sorted(received_findings),
                    },
                )
            connection.execute(
                """
                INSERT INTO review_reports VALUES (
                    :report_id, :session_id, :assignment_id, :report_version,
                    :raw_record_json, :raw_record_sha256, :summary,
                    :recommendation, :finding_ids_json,
                    :evidence_reference_ids_json, :ai_assisted,
                    :human_verified, :human_signature_ref, :submitted_at,
                    :supersedes_report_id
                )
                """,
                {
                    **report.to_dict(),
                    "raw_record_json": canonical_json(report.raw_record),
                    "finding_ids_json": canonical_json(list(report.finding_ids)),
                    "evidence_reference_ids_json": canonical_json(
                        list(report.evidence_reference_ids)
                    ),
                    "ai_assisted": int(report.ai_assisted),
                    "human_verified": int(report.human_verified),
                },
            )
            for reference_id in report.evidence_reference_ids:
                connection.execute(
                    "INSERT INTO report_evidence_links VALUES (?, ?)",
                    (report.report_id, reference_id),
                )
            for finding in finding_list:
                if (
                    finding.session_id != report.session_id
                    or finding.source_report_id != report.report_id
                ):
                    raise RBEError(
                        "RBE_FINDING_CROSS_RECORD_MISMATCH",
                        "A finding does not belong to its submitted report",
                        "RBE-ES-DOM-002",
                    )
                connection.execute(
                    """
                    INSERT INTO findings VALUES (
                        :finding_id, :session_id, :source_report_id, :severity,
                        :category, :title, :description,
                        :evidence_reference_ids_json, :status,
                        :remediation_required,
                        :raw_record_json, :raw_record_sha256, :created_at,
                        :supersedes_finding_id
                    )
                    """,
                    {
                        **finding.to_dict(),
                        "evidence_reference_ids_json": canonical_json(
                            list(finding.evidence_reference_ids)
                        ),
                        "remediation_required": int(finding.remediation_required),
                        "raw_record_json": canonical_json(finding.raw_record),
                    },
                )
                for reference_id in finding.evidence_reference_ids:
                    connection.execute(
                        "INSERT INTO finding_evidence_links VALUES (?, ?)",
                        (finding.finding_id, reference_id),
                    )
            connection.execute(
                """
                UPDATE review_assignments
                SET status = 'COMPLETED', completed_at = ?
                WHERE assignment_id = ?
                """,
                (now, report.assignment_id),
            )
            self._append_audit(
                connection,
                session_id=report.session_id,
                event_type="REVIEW_REPORT_SUBMITTED",
                actor=actor,
                occurred_at=now,
                payload={
                    "assignment_id": report.assignment_id,
                    "report_id": report.report_id,
                    "report_sha256": report.raw_record_sha256,
                    "finding_ids": sorted(received_findings),
                },
            )
            return {
                "report_id": report.report_id,
                "finding_ids": sorted(received_findings),
                "assignment_status": "COMPLETED",
            }

        return self._run_idempotent(
            session_id=report.session_id,
            command_name="submit_review",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def submit_remediation_plans(
        self,
        session_id: str,
        plans: Iterable[RemediationPlan],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        plan_list = tuple(plans)
        payload = {"plans": [plan.to_dict() for plan in plan_list]}

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            for plan in plan_list:
                if plan.session_id != session_id:
                    raise RBEError(
                        "RBE_REMEDIATION_SESSION_MISMATCH",
                        "A remediation plan does not belong to the target session",
                        "RBE-ES-DOM-002",
                    )
                connection.execute(
                    """
                    INSERT INTO remediation_plans VALUES (
                        :plan_id, :document_id, :session_id, :finding_id,
                        :owner, :action, :due_date, :status,
                        :verification_evidence_ids_json, :raw_record_json,
                        :raw_record_sha256, :created_at, :supersedes_plan_id
                    )
                    """,
                    {
                        **plan.to_dict(),
                        "verification_evidence_ids_json": canonical_json(
                            list(plan.verification_evidence_ids)
                        ),
                        "raw_record_json": canonical_json(plan.raw_record),
                    },
                )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type="REMEDIATION_PLAN_SUBMITTED",
                actor=actor,
                occurred_at=now,
                payload={
                    "plan_ids": sorted(plan.plan_id for plan in plan_list),
                    "accepted_finding_ids": sorted(
                        plan.finding_id
                        for plan in plan_list
                        if plan.status == "ACCEPTED"
                    ),
                },
            )
            return {
                "plan_ids": sorted(plan.plan_id for plan in plan_list),
                "accepted_finding_ids": sorted(
                    plan.finding_id
                    for plan in plan_list
                    if plan.status == "ACCEPTED"
                ),
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="submit_remediation_plans",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def get_session(self, session_id: str) -> ReviewSession:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM review_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RBEError(
                "RBE_SESSION_NOT_FOUND",
                "Review session was not found",
                "RBE-ES-LIF-002",
                {"session_id": session_id},
            )
        return self._session_from_row(row)

    def get_initiation(self, session_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT raw_json FROM review_packages
                WHERE session_id = ? ORDER BY package_version DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RBEError(
                "RBE_REVIEW_PACKAGE_NOT_FOUND",
                "Review initiation package was not found",
                "RBE-ES-ORC-011",
                {"session_id": session_id},
            )
        return json.loads(row["raw_json"])

    def get_latest_package(self, session_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT * FROM review_packages
                WHERE session_id = ? ORDER BY package_version DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RBEError(
                "RBE_REVIEW_PACKAGE_NOT_FOUND",
                "Review initiation package was not found",
                "RBE-ES-ORC-011",
            )
        return {
            "package_id": row["package_id"],
            "session_id": row["session_id"],
            "package_version": row["package_version"],
            "schema_name": row["schema_name"],
            "raw_record": json.loads(row["raw_json"]),
            "raw_sha256": row["raw_sha256"],
            "package_root_hash": row["package_root_hash"],
            "created_at": row["created_at"],
        }

    def append_review_package(
        self,
        session_id: str,
        initiation: dict[str, Any],
        package_root_hash: str,
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {
            "initiation": initiation,
            "package_root_hash": package_root_hash,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            session = connection.execute(
                "SELECT status FROM review_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None or session["status"] != "RETURNED":
                raise RBEError(
                    "RBE_SUCCESSOR_PACKAGE_NOT_OPEN",
                    "A successor package may be appended only in RETURNED state",
                    "RBE-ES-ORC-005",
                )
            previous = connection.execute(
                """
                SELECT package_id, package_version FROM review_packages
                WHERE session_id = ? ORDER BY package_version DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            version = previous["package_version"] + 1
            raw_hash = canonical_hash(initiation)
            package_id = deterministic_id(
                "PKG", session_id, str(version), raw_hash
            )
            connection.execute(
                """
                INSERT INTO review_packages VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    session_id,
                    version,
                    "tpl-rir",
                    canonical_json(initiation),
                    raw_hash,
                    package_root_hash,
                    now,
                ),
            )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type="REVIEW_PACKAGE_RESUBMITTED",
                actor=actor,
                occurred_at=now,
                payload={
                    "package_id": package_id,
                    "package_version": version,
                    "package_sha256": raw_hash,
                    "supersedes_package_id": previous["package_id"],
                },
            )
            return {
                "package_id": package_id,
                "package_version": version,
                "package_sha256": raw_hash,
                "supersedes_package_id": previous["package_id"],
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="append_review_package",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def save_decision_candidate(
        self,
        session_id: str,
        evaluation: DecisionEvaluation,
        artifact_manifest: dict[str, Any],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        manifest_hash = canonical_hash(artifact_manifest)
        candidate_id = deterministic_id(
            "DCA", session_id, evaluation.snapshot_hash, manifest_hash
        )
        payload = {
            "candidate_id": candidate_id,
            "evaluation": evaluation.to_dict(),
            "artifact_manifest": artifact_manifest,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            previous = connection.execute(
                """
                SELECT candidate_id, candidate_version FROM decision_candidates
                WHERE session_id = ? ORDER BY candidate_version DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            candidate_version = (
                1 if previous is None else previous["candidate_version"] + 1
            )
            supersedes = None if previous is None else previous["candidate_id"]
            connection.execute(
                """
                INSERT INTO decision_candidates(
                    candidate_id, session_id, candidate_version, evaluation_json,
                    finding_snapshot_hash, artifact_manifest_hash,
                    artifact_manifest_json, computed_at, computed_by,
                    supersedes_candidate_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    session_id,
                    candidate_version,
                    canonical_json(evaluation.to_dict()),
                    evaluation.snapshot_hash,
                    manifest_hash,
                    canonical_json(artifact_manifest),
                    now,
                    actor,
                    supersedes,
                ),
            )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type="DECISION_CANDIDATE_COMPUTED",
                actor=actor,
                occurred_at=now,
                payload={
                    "candidate_id": candidate_id,
                    "candidate_version": candidate_version,
                    "supersedes_candidate_id": supersedes,
                    "process_status": evaluation.process_status,
                    "outcome": evaluation.outcome,
                    "snapshot_hash": evaluation.snapshot_hash,
                    "artifact_manifest_hash": manifest_hash,
                },
            )
            return {
                "candidate_id": candidate_id,
                "candidate_version": candidate_version,
                "session_id": session_id,
                "evaluation": evaluation.to_dict(),
                "artifact_manifest": artifact_manifest,
                "artifact_manifest_hash": manifest_hash,
                "computed_at": now,
                "computed_by": actor,
                "supersedes_candidate_id": supersedes,
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="save_decision_candidate",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def get_decision_candidate(self, session_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT * FROM decision_candidates
                WHERE session_id = ? ORDER BY candidate_version DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return {
            "candidate_id": row["candidate_id"],
            "candidate_version": row["candidate_version"],
            "session_id": row["session_id"],
            "evaluation": self._evaluation_from_data(
                json.loads(row["evaluation_json"])
            ),
            "artifact_manifest": json.loads(row["artifact_manifest_json"]),
            "artifact_manifest_hash": row["artifact_manifest_hash"],
            "computed_at": row["computed_at"],
            "computed_by": row["computed_by"],
            "supersedes_candidate_id": row["supersedes_candidate_id"],
        }

    def _require_valid_signed_decision(
        self,
        connection: sqlite3.Connection,
        decision: BoardDecision,
        artifact_manifest: dict[str, Any],
        candidate_id: str,
        ratification: dict[str, str],
    ) -> None:
        if canonical_hash(artifact_manifest) != decision.artifact_manifest_hash:
            raise RBEError(
                "RBE_ARTIFACT_MANIFEST_HASH_MISMATCH",
                "Decision manifest does not match its canonical hash",
                "RBE-ES-PER-003",
            )
        candidate = connection.execute(
            "SELECT * FROM decision_candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if candidate is None or candidate["session_id"] != decision.session_id:
            raise RBEError(
                "RBE_DECISION_CANDIDATE_MISMATCH",
                "Ratification must reference the session's frozen candidate",
                "RBE-ES-PER-003",
            )
        if (
            candidate["evaluation_json"]
            != canonical_json(decision.evaluation.to_dict())
            or candidate["artifact_manifest_hash"]
            != decision.artifact_manifest_hash
        ):
            raise RBEError(
                "RBE_DECISION_CANDIDATE_CHANGED",
                "Ratification cannot alter the machine-computed candidate",
                "RBE-ES-DEC-005",
            )
        if not str(ratification.get("board_chair") or "").strip() or not str(
            ratification.get("board_chair_signature_ref") or ""
        ).strip():
            raise RBEError(
                "RBE_RATIFICATION_INVALID",
                "Decision ratification requires a signed Board Chair",
                "RBE-ES-DEC-005",
            )
        validator = ratification.get("governance_validator")
        validation_ref = ratification.get("governance_validation_ref")
        if decision.single_authority:
            # A single-authority record must leave the validator empty rather than
            # naming the chair twice, which would fabricate a second signatory.
            if validator or validation_ref:
                raise RBEError(
                    "RBE_SINGLE_AUTHORITY_HAS_VALIDATOR",
                    "A single-authority decision must not name a governance validator",
                    "RBE-ES-DEC-005",
                )
        elif (
            not str(validator or "").strip()
            or not str(validation_ref or "").strip()
            or ratification["board_chair"] == validator
        ):
            raise RBEError(
                "RBE_RATIFICATION_INVALID",
                "Decision ratification requires separated, signed human authorities",
                "RBE-ES-DEC-005",
            )
        if decision.status != "SIGNED" or decision.signed_at is None:
            raise RBEError(
                "RBE_SIGNED_DECISION_REQUIRED",
                "Ratification must create a signed decision record",
                "RBE-ES-DEC-005",
            )

    def _insert_signed_decision(
        self,
        connection: sqlite3.Connection,
        decision: BoardDecision,
        artifact_manifest: dict[str, Any],
        candidate_id: str,
        ratification: dict[str, str],
    ) -> None:
        connection.execute(
            """
            INSERT INTO board_decisions(
                decision_id, session_id, status, binding, merge_permitted,
                execution_mode, evaluation_json, finding_snapshot_hash,
                artifact_manifest_hash, artifact_manifest_json, computed_at,
                signed_at, published_at, published_by, superseded, single_authority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                decision.decision_id,
                decision.session_id,
                decision.status,
                int(decision.binding),
                int(decision.merge_permitted),
                decision.execution_mode,
                canonical_json(decision.evaluation.to_dict()),
                decision.finding_snapshot_hash,
                decision.artifact_manifest_hash,
                canonical_json(artifact_manifest),
                decision.computed_at,
                decision.signed_at,
                decision.published_at,
                decision.published_by,
                int(decision.single_authority),
            ),
        )
        connection.execute(
            """
            INSERT INTO decision_ratifications(
                decision_id, candidate_id, session_id, board_chair,
                board_chair_signature_ref, governance_validator,
                governance_validation_ref, ratified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                candidate_id,
                decision.session_id,
                ratification["board_chair"],
                ratification["board_chair_signature_ref"],
                ratification.get("governance_validator"),
                ratification.get("governance_validation_ref"),
                decision.signed_at,
            ),
        )

    def save_decision(
        self,
        decision: BoardDecision,
        artifact_manifest: dict[str, Any],
        candidate_id: str,
        ratification: dict[str, str],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {
            "decision": decision.to_dict(),
            "artifact_manifest": artifact_manifest,
            "candidate_id": candidate_id,
            "ratification": ratification,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            self._require_valid_signed_decision(
                connection, decision, artifact_manifest, candidate_id, ratification
            )
            self._insert_signed_decision(
                connection, decision, artifact_manifest, candidate_id, ratification
            )
            self._append_audit(
                connection,
                session_id=decision.session_id,
                event_type="DECISION_RATIFIED",
                actor=actor,
                occurred_at=now,
                payload={
                    "decision_id": decision.decision_id,
                    "candidate_id": candidate_id,
                    "decision_status": decision.status,
                    "process_status": decision.evaluation.process_status,
                    "outcome": decision.evaluation.outcome,
                    "snapshot_hash": decision.evaluation.snapshot_hash,
                    "artifact_manifest_hash": decision.artifact_manifest_hash,
                    "binding": decision.binding,
                    "merge_permitted": decision.merge_permitted,
                },
            )
            return decision.to_dict()

        return self._run_idempotent(
            session_id=decision.session_id,
            command_name="save_decision",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def get_decision(self, session_id: str) -> BoardDecision | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT * FROM board_decisions
                WHERE session_id = ? AND superseded = 0
                """,
                (session_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return self._decision_from_row(row)

    def _decision_from_row(self, row: sqlite3.Row) -> BoardDecision:
        evaluation = self._evaluation_from_data(json.loads(row["evaluation_json"]))
        return BoardDecision(
            decision_id=row["decision_id"],
            session_id=row["session_id"],
            status=row["status"],
            binding=bool(row["binding"]),
            merge_permitted=bool(row["merge_permitted"]),
            execution_mode=row["execution_mode"],
            evaluation=evaluation,
            finding_snapshot_hash=row["finding_snapshot_hash"],
            artifact_manifest_hash=row["artifact_manifest_hash"],
            computed_at=row["computed_at"],
            signed_at=row["signed_at"],
            published_at=row["published_at"],
            published_by=row["published_by"],
            superseded=bool(row["superseded"]),
            single_authority=bool(row["single_authority"]),
        )

    def get_decision_history(self, session_id: str) -> tuple[BoardDecision, ...]:
        """Every decision the session has held, superseded ones included.

        The overturned record stays readable on purpose: the point of an appeal
        trail is that both the original and its successor remain in evidence.
        """

        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM board_decisions
                WHERE session_id = ? ORDER BY superseded DESC, rowid
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(self._decision_from_row(row) for row in rows)

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
    ) -> dict[str, Any]:
        payload = {
            "successor": successor.to_dict(),
            "artifact_manifest": artifact_manifest,
            "candidate_id": candidate_id,
            "ratification": ratification,
            "superseded_decision_id": superseded_decision_id,
            "appeal_reference": appeal_reference,
        }

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            current = connection.execute(
                """
                SELECT decision_id FROM board_decisions
                WHERE session_id = ? AND superseded = 0
                """,
                (successor.session_id,),
            ).fetchone()
            if current is None or current["decision_id"] != superseded_decision_id:
                raise RBEError(
                    "RBE_SUPERSEDED_DECISION_MISMATCH",
                    "Supersession must name the session's current decision",
                    "RBE-ES-DEC-005",
                    {
                        "current_decision_id": None if current is None else current["decision_id"],
                        "superseded_decision_id": superseded_decision_id,
                    },
                )
            published = connection.execute(
                "SELECT 1 FROM publications WHERE decision_id = ?",
                (superseded_decision_id,),
            ).fetchone()
            if published is None:
                raise RBEError(
                    "RBE_UNPUBLISHED_DECISION_CANNOT_BE_SUPERSEDED",
                    "Only a published decision can be superseded on appeal",
                    "RBE-ES-DEC-005",
                )
            if successor.decision_id == superseded_decision_id:
                raise RBEError(
                    "RBE_SUCCESSOR_DECISION_IDENTICAL",
                    "A decision cannot supersede itself",
                    "RBE-ES-DEC-005",
                )
            if not appeal_reference.strip():
                raise RBEError(
                    "RBE_APPEAL_REFERENCE_REQUIRED",
                    "Supersession must cite the appeal it resolves",
                    "RBE-ES-DEC-005",
                )
            self._require_valid_signed_decision(
                connection, successor, artifact_manifest, candidate_id, ratification
            )
            # The one legal mutation: the trigger permits exactly this flip and
            # aborts anything else, so the original record cannot be rewritten.
            connection.execute(
                """
                UPDATE board_decisions
                SET superseded = 1, status = 'SUPERSEDED'
                WHERE decision_id = ? AND superseded = 0
                """,
                (superseded_decision_id,),
            )
            self._insert_signed_decision(
                connection, successor, artifact_manifest, candidate_id, ratification
            )
            self._append_audit(
                connection,
                session_id=successor.session_id,
                event_type="DECISION_SUPERSEDED",
                actor=actor,
                occurred_at=now,
                payload={
                    "superseded_decision_id": superseded_decision_id,
                    "successor_decision_id": successor.decision_id,
                    "appeal_reference": appeal_reference,
                    "successor_candidate_id": candidate_id,
                    "successor_snapshot_hash": successor.evaluation.snapshot_hash,
                },
            )
            self._append_audit(
                connection,
                session_id=successor.session_id,
                event_type="DECISION_RATIFIED",
                actor=actor,
                occurred_at=now,
                payload={
                    "decision_id": successor.decision_id,
                    "candidate_id": candidate_id,
                    "decision_status": successor.status,
                    "process_status": successor.evaluation.process_status,
                    "outcome": successor.evaluation.outcome,
                    "snapshot_hash": successor.evaluation.snapshot_hash,
                    "artifact_manifest_hash": successor.artifact_manifest_hash,
                    "binding": successor.binding,
                    "merge_permitted": successor.merge_permitted,
                },
            )
            return {
                "superseded_decision_id": superseded_decision_id,
                "successor": successor.to_dict(),
            }

        return self._run_idempotent(
            session_id=successor.session_id,
            command_name="supersede_decision",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def get_ratification(self, session_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT r.* FROM decision_ratifications r
                JOIN board_decisions d ON d.decision_id = r.decision_id
                WHERE r.session_id = ? AND d.superseded = 0
                """,
                (session_id,),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else dict(row)

    def save_publication(
        self,
        session_id: str,
        decision_id: str,
        indicator: dict[str, Any],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {"decision_id": decision_id, "indicator": indicator}
        indicator_hash = canonical_hash(indicator)
        publication_id = deterministic_id(
            "PUB", session_id, decision_id, indicator_hash
        )

        def operation(connection: sqlite3.Connection, now: str) -> dict[str, Any]:
            ratification = connection.execute(
                """
                SELECT * FROM decision_ratifications
                WHERE session_id = ? AND decision_id = ?
                """,
                (session_id, decision_id),
            ).fetchone()
            if ratification is None:
                raise RBEError(
                    "RBE_RATIFIED_DECISION_REQUIRED",
                    "Publication requires a ratified decision",
                    "RBE-ES-API-003",
                )
            decision_row = connection.execute(
                "SELECT single_authority FROM board_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
            single_authority = bool(decision_row and decision_row["single_authority"])
            conflicting = {
                actor_name
                for actor_name in (
                    ratification["board_chair"],
                    ratification["governance_validator"],
                )
                if actor_name
            }
            # Publication normally requires someone other than the decision
            # authorities. A single-authority decision was signed by one human
            # precisely because no second human exists, so the same separation
            # cannot be met here either; it is permitted and stays recorded on the
            # decision rather than being quietly waived.
            if actor in conflicting and not single_authority:
                raise RBEError(
                    "RBE_PUBLICATION_ROLE_CONFLICT",
                    "Publication authority must differ from decision authorities",
                    "RBE-ES-ORC-003",
                )
            if indicator.get("publication_authority") != actor:
                raise RBEError(
                    "RBE_PUBLICATION_ACTOR_MISMATCH",
                    "Indicator publication authority does not match the actor",
                    "RBE-ES-API-003",
                )
            connection.execute(
                """
                INSERT INTO publications(
                    publication_id, session_id, decision_id,
                    publication_authority, indicator_json,
                    indicator_sha256, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    publication_id,
                    session_id,
                    decision_id,
                    actor,
                    canonical_json(indicator),
                    indicator_hash,
                    indicator["published_at"],
                ),
            )
            self._append_audit(
                connection,
                session_id=session_id,
                event_type="DECISION_PUBLISHED",
                actor=actor,
                occurred_at=now,
                payload={
                    "publication_id": publication_id,
                    "decision_id": decision_id,
                    "indicator_sha256": indicator_hash,
                },
            )
            return {
                "publication_id": publication_id,
                "decision_id": decision_id,
                "indicator": indicator,
                "indicator_sha256": indicator_hash,
            }

        return self._run_idempotent(
            session_id=session_id,
            command_name="save_publication",
            idempotency_key=idempotency_key,
            actor=actor,
            payload=payload,
            operation=operation,
        )

    def get_publication(self, session_id: str) -> dict[str, Any] | None:
        # The publication of the *current* decision. After a supersession this is
        # None until the successor is published, which is exactly what the
        # SUPERSEDED -> FINAL prerequisite needs to observe.
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT p.* FROM publications p
                JOIN board_decisions d ON d.decision_id = p.decision_id
                WHERE p.session_id = ? AND d.superseded = 0
                """,
                (session_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return {
            "publication_id": row["publication_id"],
            "session_id": row["session_id"],
            "decision_id": row["decision_id"],
            "publication_authority": row["publication_authority"],
            "indicator": json.loads(row["indicator_json"]),
            "indicator_sha256": row["indicator_sha256"],
            "published_at": row["published_at"],
        }

    def list_assignments(self, session_id: str) -> tuple[ReviewAssignment, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM review_assignments
                WHERE session_id = ? ORDER BY sequence, assignment_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(self._assignment_from_row(row) for row in rows)

    def list_evidence(self, session_id: str) -> dict[str, EvidenceReference]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM evidence_references
                WHERE session_id = ? ORDER BY reference_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return {
            row["reference_id"]: EvidenceReference(
                reference_id=row["reference_id"],
                session_id=row["session_id"],
                reference_type=row["reference_type"],
                locator=row["locator"],
                content_sha256=row["content_sha256"],
                description=row["description"],
                source_tier=row["source_tier"],
                provenance=json.loads(row["provenance_json"]),
                registered_at=row["registered_at"],
            )
            for row in rows
        }

    def get_evidence_content(self, reference_id: str) -> bytes:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT content_blob FROM evidence_references WHERE reference_id = ?",
                (reference_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RBEError(
                "RBE_EVIDENCE_NOT_FOUND",
                "Evidence reference was not found",
                "RBE-ES-ORC-007",
                {"reference_id": reference_id},
            )
        return bytes(row["content_blob"])

    def list_reports(self, session_id: str) -> tuple[ReviewerReport, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM review_reports
                WHERE session_id = ? ORDER BY report_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(self._report_from_row(row) for row in rows)

    def list_findings(self, session_id: str) -> tuple[Finding, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM findings
                WHERE session_id = ? ORDER BY severity, category, finding_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(self._finding_from_row(row) for row in rows)

    def list_remediation_plans(
        self, session_id: str
    ) -> tuple[RemediationPlan, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM remediation_plans
                WHERE session_id = ? ORDER BY plan_id
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(
            RemediationPlan(
                plan_id=row["plan_id"],
                document_id=row["document_id"],
                session_id=row["session_id"],
                finding_id=row["finding_id"],
                owner=row["owner"],
                action=row["action"],
                due_date=row["due_date"],
                status=row["status"],
                verification_evidence_ids=tuple(
                    json.loads(row["verification_evidence_ids_json"])
                ),
                raw_record=json.loads(row["raw_record_json"]),
                raw_record_sha256=row["raw_record_sha256"],
                created_at=row["created_at"],
                supersedes_plan_id=row["supersedes_plan_id"],
            )
            for row in rows
        )

    def list_audit(self, session_id: str) -> tuple[AuditEntry, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM audit_log
                WHERE session_id = ? ORDER BY sequence
                """,
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return tuple(
            AuditEntry(
                audit_id=row["audit_id"],
                session_id=row["session_id"],
                sequence=row["sequence"],
                event_type=row["event_type"],
                actor=row["actor"],
                occurred_at=row["occurred_at"],
                payload=json.loads(row["payload_json"]),
                previous_hash=row["previous_hash"],
                entry_hash=row["entry_hash"],
                schema_id=row["schema_id"],
                schema_version=row["schema_version"],
            )
            for row in rows
        )

    def verify_audit(self, session_id: str) -> dict[str, Any]:
        entries = self.list_audit(session_id)
        previous_hash: str | None = None
        for expected_sequence, entry in enumerate(entries, start=1):
            payload = {
                "session_id": entry.session_id,
                "sequence": entry.sequence,
                "event_type": entry.event_type,
                "actor": entry.actor,
                "occurred_at": entry.occurred_at,
                "payload": entry.payload,
                "previous_hash": entry.previous_hash,
            }
            if (
                entry.sequence != expected_sequence
                or entry.previous_hash != previous_hash
                or entry.entry_hash != canonical_hash(payload)
            ):
                raise RBEError(
                    "RBE_AUDIT_CHAIN_INVALID",
                    "The session audit chain failed verification",
                    "RBE-ES-AUD-002",
                    {
                        "session_id": session_id,
                        "sequence": entry.sequence,
                    },
                )
            previous_hash = entry.entry_hash
        return {
            "session_id": session_id,
            "entries_verified": len(entries),
            "root_hash": previous_hash,
            "valid": True,
        }

    def verify_all_audits(self) -> None:
        connection = self._connect()
        try:
            session_ids = [
                row["session_id"]
                for row in connection.execute(
                    "SELECT session_id FROM review_sessions ORDER BY session_id"
                ).fetchall()
            ]
        finally:
            connection.close()
        for session_id in session_ids:
            self.verify_audit(session_id)

    @staticmethod
    def _evaluation_from_data(evaluation_data: dict[str, Any]) -> DecisionEvaluation:
        return DecisionEvaluation(
            process_status=evaluation_data["process_status"],
            outcome=evaluation_data["outcome"],
            reason_codes=tuple(evaluation_data["reason_codes"]),
            rules_applied=tuple(evaluation_data["rules_applied"]),
            findings_considered=tuple(evaluation_data["findings_considered"]),
            counter_evidence=tuple(evaluation_data["counter_evidence"]),
            process_blockers=tuple(evaluation_data.get("process_blockers", [])),
            profile_id=evaluation_data["profile_id"],
            profile_version=evaluation_data["profile_version"],
            profile_checksum=evaluation_data["profile_checksum"],
            engine_version=evaluation_data["engine_version"],
            snapshot_hash=evaluation_data["snapshot_hash"],
            explanation=evaluation_data["explanation"],
        )

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> ReviewSession:
        return ReviewSession(
            session_id=row["session_id"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            target_version=row["target_version"],
            methodology_id=row["methodology_id"],
            methodology_version=row["methodology_version"],
            methodology_checksum=row["methodology_checksum"],
            engine_version=row["engine_version"],
            schema_version=row["schema_version"],
            status=row["status"],
            aggregate_version=row["aggregate_version"],
            execution_mode=row["execution_mode"],
            binding=bool(row["binding"]),
            created_at=row["created_at"],
            created_by=row["created_by"],
            completed_at=row["completed_at"],
            parent_session_id=row["parent_session_id"],
        )

    @staticmethod
    def _assignment_from_row(row: sqlite3.Row) -> ReviewAssignment:
        return ReviewAssignment(
            assignment_id=row["assignment_id"],
            session_id=row["session_id"],
            reviewer_role=row["reviewer_role"],
            reviewer_actor=row["reviewer_actor"],
            reviewer_spec_id=row["reviewer_spec_id"],
            status=row["status"],
            sequence=row["sequence"],
            required=bool(row["required"]),
            conflict_declared=bool(row["conflict_declared"]),
            has_material_conflict=bool(row["has_material_conflict"]),
            assigned_at=row["assigned_at"],
            accepted_at=row["accepted_at"],
            completed_at=row["completed_at"],
        )

    @staticmethod
    def _report_from_row(row: sqlite3.Row) -> ReviewerReport:
        return ReviewerReport(
            report_id=row["report_id"],
            session_id=row["session_id"],
            assignment_id=row["assignment_id"],
            report_version=row["report_version"],
            raw_record=json.loads(row["raw_record_json"]),
            raw_record_sha256=row["raw_record_sha256"],
            summary=row["summary"],
            recommendation=row["recommendation"],
            finding_ids=tuple(json.loads(row["finding_ids_json"])),
            evidence_reference_ids=tuple(
                json.loads(row["evidence_reference_ids_json"])
            ),
            ai_assisted=bool(row["ai_assisted"]),
            human_verified=bool(row["human_verified"]),
            human_signature_ref=row["human_signature_ref"],
            submitted_at=row["submitted_at"],
            supersedes_report_id=row["supersedes_report_id"],
        )

    @staticmethod
    def _finding_from_row(row: sqlite3.Row) -> Finding:
        return Finding(
            finding_id=row["finding_id"],
            session_id=row["session_id"],
            source_report_id=row["source_report_id"],
            severity=row["severity"],
            category=row["category"],
            title=row["title"],
            description=row["description"],
            evidence_reference_ids=tuple(
                json.loads(row["evidence_reference_ids_json"])
            ),
            status=row["status"],
            remediation_required=bool(row["remediation_required"]),
            raw_record=json.loads(row["raw_record_json"]),
            raw_record_sha256=row["raw_record_sha256"],
            created_at=row["created_at"],
            supersedes_finding_id=row["supersedes_finding_id"],
        )
