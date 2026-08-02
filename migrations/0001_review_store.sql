-- Review store, derived from the live SQLite schema by tools/pg_schema.py.
-- Do not edit by hand: regenerate. Hand-transcription is how RBM-004 shipped
-- with another profile's identity welded into its schemas.

BEGIN;

CREATE SCHEMA IF NOT EXISTS board;
SET search_path TO board, public;

CREATE TABLE audit_log (
            audit_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            sequence BIGINT NOT NULL CHECK (sequence > 0),
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

CREATE TABLE board_decisions (
            decision_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            status TEXT NOT NULL,
            binding BIGINT NOT NULL CHECK (binding IN (0, 1)),
            merge_permitted BIGINT NOT NULL CHECK (merge_permitted IN (0, 1)),
            execution_mode TEXT NOT NULL,
            evaluation_json TEXT NOT NULL,
            finding_snapshot_hash TEXT NOT NULL,
            artifact_manifest_hash TEXT NOT NULL,
            artifact_manifest_json TEXT NOT NULL,
            computed_at TEXT NOT NULL,
            signed_at TEXT,
            published_at TEXT,
            published_by TEXT,
            superseded BIGINT NOT NULL DEFAULT 0 CHECK (superseded IN (0, 1))
        , single_authority BIGINT NOT NULL DEFAULT 0
            CHECK (single_authority IN (0, 1)));

CREATE TABLE conflict_declarations (
            declaration_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            assignment_id TEXT NOT NULL UNIQUE REFERENCES review_assignments(assignment_id),
            actor TEXT NOT NULL,
            has_material_conflict BIGINT NOT NULL CHECK (has_material_conflict IN (0, 1)),
            basis TEXT,
            human_signature_ref TEXT NOT NULL,
            declared_at TEXT NOT NULL
        );

CREATE TABLE decision_candidates (
            candidate_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            candidate_version BIGINT NOT NULL CHECK (candidate_version > 0),
            evaluation_json TEXT NOT NULL,
            finding_snapshot_hash TEXT NOT NULL,
            artifact_manifest_hash TEXT NOT NULL,
            artifact_manifest_json TEXT NOT NULL,
            computed_at TEXT NOT NULL,
            computed_by TEXT NOT NULL,
            supersedes_candidate_id TEXT REFERENCES decision_candidates(candidate_id),
            UNIQUE (session_id, candidate_version)
        );

CREATE TABLE "decision_ratifications" (
            decision_id TEXT PRIMARY KEY REFERENCES board_decisions(decision_id),
            candidate_id TEXT NOT NULL UNIQUE REFERENCES decision_candidates(candidate_id),
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            board_chair TEXT NOT NULL,
            board_chair_signature_ref TEXT NOT NULL,
            governance_validator TEXT,
            governance_validation_ref TEXT,
            ratified_at TEXT NOT NULL, single_authority_rationale TEXT,
            CHECK (
                (governance_validator IS NULL AND governance_validation_ref IS NULL)
                OR (governance_validator IS NOT NULL AND governance_validation_ref IS NOT NULL)
            )
        );

CREATE TABLE evidence_references (
            reference_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            reference_type TEXT NOT NULL,
            locator TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            content_blob BYTEA NOT NULL,
            description TEXT NOT NULL,
            source_tier TEXT,
            provenance_json TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            UNIQUE (session_id, locator, content_sha256)
        );

CREATE TABLE finding_evidence_links (
            finding_id TEXT NOT NULL REFERENCES findings(finding_id),
            reference_id TEXT NOT NULL REFERENCES evidence_references(reference_id),
            PRIMARY KEY (finding_id, reference_id)
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
            remediation_required BIGINT NOT NULL CHECK (remediation_required IN (0, 1)),
            raw_record_json TEXT NOT NULL,
            raw_record_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            supersedes_finding_id TEXT REFERENCES findings(finding_id)
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

CREATE TABLE "publications" (
            publication_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            decision_id TEXT NOT NULL UNIQUE REFERENCES board_decisions(decision_id),
            publication_authority TEXT NOT NULL,
            indicator_json TEXT NOT NULL,
            indicator_sha256 TEXT NOT NULL,
            published_at TEXT NOT NULL
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

CREATE TABLE report_evidence_links (
            report_id TEXT NOT NULL REFERENCES review_reports(report_id),
            reference_id TEXT NOT NULL REFERENCES evidence_references(reference_id),
            PRIMARY KEY (report_id, reference_id)
        );

CREATE TABLE review_assignments (
            assignment_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            reviewer_role TEXT NOT NULL,
            reviewer_actor TEXT NOT NULL,
            reviewer_spec_id TEXT NOT NULL,
            status TEXT NOT NULL,
            sequence BIGINT NOT NULL CHECK (sequence > 0),
            required BIGINT NOT NULL CHECK (required IN (0, 1)),
            conflict_declared BIGINT NOT NULL CHECK (conflict_declared IN (0, 1)),
            has_material_conflict BIGINT NOT NULL CHECK (has_material_conflict IN (0, 1)),
            assigned_at TEXT NOT NULL,
            accepted_at TEXT,
            completed_at TEXT,
            UNIQUE (session_id, reviewer_role),
            UNIQUE (session_id, sequence)
        );

CREATE TABLE review_packages (
            package_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            package_version BIGINT NOT NULL CHECK (package_version > 0),
            schema_name TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL,
            package_root_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (session_id, package_version)
        );

CREATE TABLE review_reports (
            report_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES review_sessions(session_id),
            assignment_id TEXT NOT NULL REFERENCES review_assignments(assignment_id),
            report_version BIGINT NOT NULL CHECK (report_version > 0),
            raw_record_json TEXT NOT NULL,
            raw_record_sha256 TEXT NOT NULL,
            summary TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            finding_ids_json TEXT NOT NULL,
            evidence_reference_ids_json TEXT NOT NULL,
            ai_assisted BIGINT NOT NULL CHECK (ai_assisted IN (0, 1)),
            human_verified BIGINT NOT NULL CHECK (human_verified IN (0, 1)),
            human_signature_ref TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            supersedes_report_id TEXT REFERENCES review_reports(report_id),
            UNIQUE (assignment_id, report_version)
        );

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
            aggregate_version BIGINT NOT NULL,
            execution_mode TEXT NOT NULL,
            binding BIGINT NOT NULL CHECK (binding IN (0, 1)),
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            completed_at TEXT,
            parent_session_id TEXT REFERENCES review_sessions(session_id)
        );

CREATE TABLE schema_migrations (
                    version BIGINT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );

-- Row security: deny by default, on every table, before any data lands.
-- A permissive default plus a public repository is how a published decision
-- becomes editable by anyone holding an anon key.

ALTER TABLE "audit_log" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "audit_log" FORCE ROW LEVEL SECURITY;
ALTER TABLE "board_decisions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "board_decisions" FORCE ROW LEVEL SECURITY;
ALTER TABLE "conflict_declarations" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "conflict_declarations" FORCE ROW LEVEL SECURITY;
ALTER TABLE "decision_candidates" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "decision_candidates" FORCE ROW LEVEL SECURITY;
ALTER TABLE "decision_ratifications" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "decision_ratifications" FORCE ROW LEVEL SECURITY;
ALTER TABLE "evidence_references" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "evidence_references" FORCE ROW LEVEL SECURITY;
ALTER TABLE "finding_evidence_links" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "finding_evidence_links" FORCE ROW LEVEL SECURITY;
ALTER TABLE "findings" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "findings" FORCE ROW LEVEL SECURITY;
ALTER TABLE "idempotency_keys" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "idempotency_keys" FORCE ROW LEVEL SECURITY;
ALTER TABLE "publications" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "publications" FORCE ROW LEVEL SECURITY;
ALTER TABLE "remediation_plans" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "remediation_plans" FORCE ROW LEVEL SECURITY;
ALTER TABLE "report_evidence_links" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "report_evidence_links" FORCE ROW LEVEL SECURITY;
ALTER TABLE "review_assignments" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "review_assignments" FORCE ROW LEVEL SECURITY;
ALTER TABLE "review_packages" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "review_packages" FORCE ROW LEVEL SECURITY;
ALTER TABLE "review_reports" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "review_reports" FORCE ROW LEVEL SECURITY;
ALTER TABLE "review_sessions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "review_sessions" FORCE ROW LEVEL SECURITY;
ALTER TABLE "schema_migrations" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "schema_migrations" FORCE ROW LEVEL SECURITY;

-- Immutability by grant rather than by trigger. A trigger can be dropped by
-- whoever can write; a revoked privilege cannot be restored by the role it was
-- revoked from, so the guarantee holds against the application itself.

REVOKE UPDATE, DELETE ON "review_packages" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "evidence_references" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "conflict_declarations" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "review_reports" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "findings" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "decision_candidates" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "decision_ratifications" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "publications" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "audit_log" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "report_evidence_links" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "finding_evidence_links" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "remediation_plans" FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON "board_decisions" FROM PUBLIC, anon, authenticated;

COMMIT;

-- 17 table(s) derived; 13 marked append-only.
