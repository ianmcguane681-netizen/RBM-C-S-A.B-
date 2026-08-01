---
document_id: RBE-001-ES
title: Review Board Engine Engineering Specification
release_version: 1.1.0
status: normalization-release-candidate
publication_date: 2026-07-19
proposed_supersedes: RBE-001-Engineering-Specification-v1.0.0
supersession_effective_on: named-human-principal-architect-approval
source_sha256: 92e159f084ab91d458e57f98d405b7a6146dd6f98db04af76d159b8e09b45ca4
---

# RBE-001 Review Board Engine Engineering Specification

> Normalized implementation contract. Architecture requirements retain the
> `RBE-[DOMAIN]-NNN` namespace; this specification uses
> `RBE-ES-[DOMAIN]-NNN` exclusively.

## Document Control

| Field | Value |
|---|---|
| Document ID | RBE-001-ES |
| Version | 1.1.0 |
| Status | Normalization release candidate - ready for human approval |
| Owner | Project Exchange / Provena |
| Historical source | Engineering Specification v1.0.0, SHA-256 `92e159f084ab91d458e57f98d405b7a6146dd6f98db04af76d159b8e09b45ca4` |
| Architecture authority | RBE-001 Reference Architecture v1.1.0 |
| Target profile | Foundation profile: local, single-process, SQLite |
| Operational limitation | No binding live Board decisions until a methodology profile is ACTIVE |

### Revision History

| Version | Date | Status | Summary |
|---|---|---|---|
| 1.0.0 | 18 Jul 2026 | Historical | Initial implementation specification |
| 1.1.0 | 19 Jul 2026 | Release candidate | Canonical outcomes, state machine, authority order, and requirement namespace |

### Approval Record

| Role | Status |
|---|---|
| Codex technical normalization review | READY |
| Principal Architect | Human approval required |
| Methodology owner | Required for each operational methodology profile |
| Implementation owner | Acknowledgement required before implementation |

### Normative Relationship

The RBE-001 Reference Architecture is the constitutional and domain authority. This Engineering
Specification defines one implementation profile and SHALL NOT create alternate verdicts, states,
roles, or governance powers. An ACTIVE methodology profile supplies decision thresholds, required
review functions, quorum, and its permitted subset of canonical outcomes. The Foundation profile
may be implemented and tested without an active methodology, but it cannot issue binding live
Board decisions.

Every ACTIVE methodology profile must include `INSUFFICIENT_EVIDENCE`. A profile may omit
`DEFER_FOR_FURTHER_RESEARCH` only when bounded research gaps map to `INSUFFICIENT_EVIDENCE`.

### Normative Language

- SHALL / SHALL NOT: mandatory for conformance.
- SHOULD / SHOULD NOT: expected unless an approved exception exists.
- MAY: optional and must not weaken determinism, integrity, independence, or traceability.

### Referenced Standards and Specifications

| Reference | Purpose | Authority |
|---|---|---|
| RBE-001 Reference Architecture v1.1.0 | Constitution, domain semantics, states, and outcomes | Primary RBE authority |
| ACTIVE methodology profile | Thresholds, quorum, role configuration, and permitted outcome subset | Live-case authority within the architecture |
| RBS-* | Role-specific review contracts | Active-profile subordinate authority |
| JSON Schema 2020-12 | Machine-readable contracts | External standard |
| SQLite | Foundation-profile persistence | Non-production implementation constraint |

## Contents

1. Purpose, Scope and Conformance
2. Design Principles
3. System Context and Architecture
4. Canonical Review Lifecycle
5. Domain Model
6. Review Orchestration
7. Deterministic Decision Engine
8. Persistence and Audit
9. Machine-Readable Contracts
10. Human-Readable Artifacts
11. Application Programming Interface
12. User Interface Requirements
13. Security, Integrity and Privacy
14. Reliability and Non-Functional Requirements
15. Testing and Acceptance
16. Versioning and Compatibility
17. Deployment and Operations
18. Explicit Non-Goals and Future Extensions

## 1. Purpose, Scope and Conformance

### 1.1 Purpose

Review Board Engine v1 (RBE v1) is a deterministic governance execution engine. It converts a complete review package, structured reviewer submissions and approved methodology rules into a durable review session, normalized findings, a machine-computed decision and an immutable audit trail. The engine exists to make Review Board execution repeatable, inspectable and automatable without transferring governance authority to software or artificial intelligence.

**RBE-ES-PUR-001** The engine SHALL execute only governance rules that are explicitly defined in the approved methodology or this implementation specification.

**RBE-ES-PUR-002** The engine SHALL produce the same canonical decision and artifact content for identical normalized inputs, methodology version and engine version.

**RBE-ES-PUR-003** The engine SHALL persist sufficient information to reconstruct why every session state, finding status and decision occurred.

**RBE-ES-PUR-004** The engine SHALL produce both machine-readable JSON artifacts and human-readable review artifacts.

### 1.2 Scope

- Creation and management of review sessions.

- Validation and registration of review packages.

- Assignment and sequencing of required reviewer roles.

- Receipt and validation of structured reviewer reports.

- Normalization, deduplication and lifecycle tracking of findings.

- Deterministic computation of a methodology-permitted substantive outcome, with process status recorded separately.

- Persistence of sessions, reports, evidence references, decisions and audit events.

- Export of canonical review bundles.

- A minimal operator interface sufficient to run and inspect sessions.

### 1.3 Out of scope

- Generating methodology or inventing governance rules.

- Replacing accountable human reviewers.

- Autonomous acceptance of evidence or closure of remediation.

- General-purpose project management.

- External identity federation, enterprise SSO or organization-wide role administration.

- Distributed execution, high-availability clustering or multi-region storage.

- Automated market research, evidence discovery or source scraping.

### 1.4 Conformance classes


| Class | Minimum behavior | Required for v1 |
| --- | --- | --- |
| Core Engine | State machine, domain model, decision engine, audit persistence | Yes |
| Artifact Producer | Canonical JSON and Markdown outputs | Yes |
| Operator Application | Session creation, report submission, decision and audit inspection | Yes |


**RBE-ES-CON-001** A conforming RBE v1 implementation SHALL satisfy all requirements marked mandatory and SHALL pass all acceptance tests in Section 15.

**RBE-ES-CON-002** A deviation SHALL be documented as an approved exception with requirement identifier, rationale, risk, owner and expiry or remediation date.


## 2. Design Principles

### Determinism

Decision outcomes are computed by pure, versioned rules over normalized inputs; timestamps and database identifiers must not influence the verdict.

### Methodology supremacy

The engine implements governance; it does not define governance. Ambiguity is surfaced as an error or methodology gap.

### Human accountability

Reviewer and decision-accountable identities remain explicit even when AI-assisted tooling is used.

### Append-only governance

Material review records are never silently rewritten. Corrections create superseding records and retain lineage.

### Evidence traceability

Every material finding and decision reason links to one or more registered evidence references or a clearly stated procedural basis.

### Fail closed

Missing mandatory inputs, invalid schemas or unfulfilled required review roles prevent decision finalization.

### Inspectable operation

Operators and auditors can follow the complete lifecycle from session creation through decision publication.

### Portability

Review artifacts are exportable as implementation-neutral JSON and Markdown.

**RBE-ES-DES-001** The deterministic core SHALL be implemented as side-effect-free decision functions that can be executed independently of the API, database and user interface.

**RBE-ES-DES-002** Artificial intelligence output MAY be stored as reviewer-assistance metadata, but SHALL NOT directly set severity, finding status, quorum status or board decision.

**RBE-ES-DES-003** The engine SHALL reject any attempt to finalize a decision when the methodology version or decision rule set is unknown.

**RBE-ES-DES-004** All identifiers used in exported artifacts SHALL be stable and globally unique within the Review Board system.


## 3. System Context and Architecture

### 3.1 Context

RBE sits after a reviewable implementation, methodology, study or specification has produced a complete review package. It receives the package, orchestrates independent role-based review, aggregates findings and publishes a controlled decision.

    Upstream reviewable object

    |

    v

    Review Package Registry

    |

    v

    Input Validator --> Review Session State Machine

    |

    v

    Assignment Orchestrator

    |

    v

    Structured Reviewer Reports

    |

    v

    Finding Normalization

    |

    v

    Deterministic Decision Engine

    |

    v

    Decision + Artifacts + Audit Bundle

*Figure 1. Logical RBE v1 flow*

### 3.2 Component responsibilities


| Component | Responsibility | Must not do |
| --- | --- | --- |
| Package Registry | Registers target, package manifest, files and checksums | Judge evidence quality |
| Input Validator | Validates schemas, mandatory files, versions and checksums | Repair invalid submissions silently |
| Session Service | Creates sessions and enforces lifecycle | Bypass state transitions |
| Assignment Orchestrator | Creates role assignments and phase gates | Determine verdict |
| Report Service | Accepts structured reviewer reports and validates authorship | Rewrite reviewer conclusions |
| Finding Service | Normalizes, links and tracks finding lineage | Auto-close findings |
| Decision Engine | Applies approved deterministic decision table | Use model inference or voting heuristics |
| Artifact Service | Builds canonical JSON and Markdown bundles | Omit material audit data |


### 3.3 Reference technology profile

- Application language: Python 3.12 or later unless the host repository requires another supported language.

- Persistence: SQLite with foreign keys enabled and migration-managed schema.

- API: local REST service using OpenAPI-described endpoints.

- Schemas: JSON Schema draft 2020-12.

- Human artifacts: UTF-8 Markdown.

- Tests: unit, integration, golden artifact and deterministic replay suites.

**RBE-ES-ARC-001** The implementation SHALL maintain explicit boundaries between domain logic, persistence adapters, API handlers and presentation code.

**RBE-ES-ARC-002** The implementation SHALL support headless command-line execution for test and automation use.

**RBE-ES-ARC-003** The engine SHALL operate without network access after all review package inputs have been registered locally.

**RBE-ES-ARC-004** External services SHALL be optional adapters and SHALL NOT be necessary to compute a decision.


## 4. Canonical Review Lifecycle

### 4.1 State Authority

Chapter 8 of the Reference Architecture and `registers/state_machine.json` define the only
authoritative case states. Engineering adapters MAY expose friendly labels or phase projections,
but those values are non-authoritative and cannot be persisted as alternative case states.

| Category | Canonical states |
|---|---|
| Preparation | `DRAFT`, `SUBMITTED` |
| Admissibility | `INTAKE_VALIDATION`, `RETURNED`, `ACCEPTED` |
| Control establishment | `EVIDENCE_LOCKED`, `ASSIGNMENT` |
| Substantive review | `INDEPENDENT_REVIEW`, `CHALLENGE`, `CLARIFICATION` |
| Decision construction | `CONSOLIDATION`, `GOVERNANCE_VALIDATION`, `BLOCKED` |
| Decision and publication | `DECIDED`, `PUBLISHED` |
| Post-decision | `APPEALED`, `APPEAL_REVIEW`, `UPHELD`, `SUPERSEDED`, `REMANDED` |
| Terminal | `FINAL`, `ARCHIVED`, `VOID`, `WITHDRAWN` |

### 4.2 Transition Rules

**RBE-ES-LIF-001** The implementation SHALL load and enforce the versioned canonical state-machine
register without defining a second state enumeration.

**RBE-ES-LIF-002** Every transition SHALL pass through one domain transition service that validates
prior state, target state, actor authority, expected aggregate version, prerequisites, and required
artifacts.

**RBE-ES-LIF-003** A failed transition SHALL leave authoritative state unchanged, return stable failed-
precondition codes, and append a rejected-transition audit event where governance-relevant.

**RBE-ES-LIF-004** The accepted transition and its audit event SHALL commit atomically.

**RBE-ES-LIF-005** Retrying an accepted transition with the same idempotency key and payload SHALL
return the original result; payload mismatch SHALL be rejected and audited.

**RBE-ES-LIF-006** `ARCHIVED`, `VOID`, and `WITHDRAWN` SHALL be terminal under ordinary commands.

**RBE-ES-LIF-007** Appeal, remand, and re-review SHALL preserve the original decision, create the
successor records required by the canonical state and lineage contracts, and route `REMANDED`
through `ASSIGNMENT` without bypassing role or evidence controls.

### 4.3 Phase Projections

Specialist, methodology, sceptical, commercial, and governance review phases are assignment and
workflow projections inside canonical states. They SHALL NOT become competing case states. The
v1.0.0 engineering-state names are retired and mapped in `registers/state_machine.md`.

### 4.4 Recovery

Lifecycle commands are idempotent and optimistic-concurrency protected. Crash recovery resumes
from durable authoritative state and verifies audit continuity. It never reconstructs state from UI
labels, task queues, or mutable projections.

**RBE-ES-LIF-008** Recovery SHALL not create duplicate assignments, reports, findings, decisions, or
state transitions.

**RBE-ES-LIF-009** Failure after decision evaluation but before governed ratification SHALL preserve
the evaluation as non-authoritative and leave the case in `GOVERNANCE_VALIDATION` or `BLOCKED`.

**RBE-ES-LIF-010** Failure during publication SHALL leave a ratified `DECIDED` record intact and retry
publication without recalculating or mutating the decision.

## 5. Domain Model

The domain model is authoritative. API payloads and database tables may add transport or storage metadata, but may not weaken the constraints below.

### 5.1 ReviewSession


| Field | Type | Constraint |
| --- | --- | --- |
| session_id | UUID/ULID | Required, immutable |
| target_type | enum/string | Required |
| target_id | string | Required |
| target_version | string | Required |
| methodology_id | string | Required |
| methodology_version | semver | Required |
| engine_version | semver | Required |
| schema_version | semver | Required |
| status | SessionStatus | Required |
| parent_session_id | identifier | Optional; required for re-review |
| created_at | UTC timestamp | Required |
| created_by | ActorRef | Required |
| completed_at | UTC timestamp | Optional |


### 5.2 ReviewAssignment


| Field | Type | Constraint |
| --- | --- | --- |
| assignment_id | identifier | Required |
| session_id | identifier | Required |
| reviewer_role | RoleCode | Required |
| reviewer_actor | ActorRef | Required |
| phase | ReviewPhase | Required |
| status | AssignmentStatus | Required |
| sequence | integer | Required, positive |
| required | boolean | Required |
| assigned_at | UTC timestamp | Required |
| accepted_at | UTC timestamp | Optional |
| completed_at | UTC timestamp | Optional |


### 5.3 ReviewerReport


| Field | Type | Constraint |
| --- | --- | --- |
| report_id | identifier | Required |
| assignment_id | identifier | Required |
| report_version | integer | Required, starts at 1 |
| summary | string | Required |
| recommendation | enum | Required but non-binding |
| finding_ids | array | Required; may be empty |
| evidence_reference_ids | array | Required; may be empty |
| attestation | object | Required |
| submitted_at | UTC timestamp | Required |
| supersedes_report_id | identifier | Optional |


### 5.4 Finding


| Field | Type | Constraint |
| --- | --- | --- |
| finding_id | identifier | Required |
| session_id | identifier | Required |
| source_report_id | identifier | Required |
| severity | SEV-1..SEV-4 | Required |
| category | string/enum | Required |
| title | string | Required |
| description | string | Required |
| evidence_reference_ids | array | Required |
| status | FindingStatus | Required |
| remediation_required | boolean | Derived |
| owner | ActorRef | Optional until assigned |
| supersedes_finding_id | identifier | Optional |
| created_at | UTC timestamp | Required |


### 5.5 EvidenceReference


| Field | Type | Constraint |
| --- | --- | --- |
| reference_id | identifier | Required |
| session_id | identifier | Required |
| reference_type | enum | Required |
| locator | string | Required |
| sha256 | hex string | Required for files |
| description | string | Required |
| source_tier | string/enum | Optional |
| registered_at | UTC timestamp | Required |


### 5.6 BoardDecision


| Field | Type | Constraint |
| --- | --- | --- |
| decision_id | identifier | Required |
| session_id | identifier | Required, unique active decision |
| outcome | PASS\|PASS_WITH_FINDINGS\|FAIL\|INSUFFICIENT_EVIDENCE\|DEFER_FOR_FURTHER_RESEARCH | Required when process status is READY |
| process_status | READY\|PROCEDURALLY_INCOMPLETE\|BLOCKED\|VOID | Required |
| rule_set_id | string | Required |
| rule_set_version | semver | Required |
| finding_snapshot_hash | sha256 | Required |
| reason_codes | array | Required |
| explanation | string | Required, generated deterministically |
| computed_at | UTC timestamp | Required |
| status | DRAFT_CANDIDATE\|SIGNED\|PUBLISHED\|SUPERSEDED | Required |
| signed_at | UTC timestamp | Required when status is SIGNED or later |
| published_at | UTC timestamp | Required only when status is PUBLISHED or SUPERSEDED |
| published_by | ActorRef | Required only when status is PUBLISHED or SUPERSEDED |


### 5.7 RemediationPlan


| Field | Type | Constraint |
| --- | --- | --- |
| plan_id | identifier | Required |
| session_id | identifier | Required |
| finding_id | identifier | Required |
| owner | ActorRef | Required |
| action | string | Required |
| due_date | date | Optional |
| status | PlanStatus | Required |
| verification_evidence_ids | array | Optional |
| supersedes_plan_id | identifier | Optional |


### 5.8 AuditEntry


| Field | Type | Constraint |
| --- | --- | --- |
| audit_id | identifier | Required |
| session_id | identifier | Required |
| sequence | integer | Required, monotonic per session |
| event_type | string | Required |
| actor | ActorRef | Required |
| occurred_at | UTC timestamp | Required |
| payload | object | Required |
| previous_hash | sha256 | Required except first |
| entry_hash | sha256 | Required |


### 5.9 Cross-entity invariants

**RBE-ES-DOM-001** Each report SHALL belong to exactly one assignment and one session through that assignment.

**RBE-ES-DOM-002** A finding SHALL reference the report that introduced it and SHALL retain lineage when superseded.

**RBE-ES-DOM-003** Only one non-superseded decision SHALL exist for a session.

**RBE-ES-DOM-004** A report correction SHALL create a new report version; the prior report SHALL remain immutable.

**RBE-ES-DOM-005** A finding severity change SHALL create a superseding finding record or a versioned finding event; it SHALL NOT erase the original severity.

**RBE-ES-DOM-006** All exported timestamps SHALL use RFC 3339 UTC with a Z suffix.


## 6. Review Orchestration

### 6.1 Role and phase configuration

The orchestrator receives a versioned board configuration that defines required roles, phase ordering, whether roles may operate concurrently, and completion prerequisites. Configuration is data, not executable code.

**RBE-ES-ORC-001** The board configuration SHALL have a stable identifier, semantic version and checksum.

**RBE-ES-ORC-002** The orchestrator SHALL create exactly one required assignment for every required role unless the configuration explicitly permits multiple seats.

**RBE-ES-ORC-003** A reviewer actor SHALL NOT satisfy two independence-conflicting roles in the same session.

**RBE-ES-ORC-004** The engine SHALL validate reviewer-role eligibility before assignment.

**RBE-ES-ORC-005** The next phase SHALL not open until all mandatory assignments in the current phase are completed or formally waived under an approved methodology rule.

### 6.2 Report submission

**RBE-ES-ORC-006** A report submission SHALL validate schema, assignment status, actor identity, methodology version and evidence references.

**RBE-ES-ORC-007** Reports with unknown evidence references SHALL be rejected.

**RBE-ES-ORC-008** A completed assignment SHALL become read-only except through a superseding report workflow.

**RBE-ES-ORC-009** The engine SHALL distinguish reviewer recommendation from board verdict; recommendation SHALL never be treated as a vote.

**RBE-ES-ORC-010** Free-text report content SHALL be preserved verbatim in the immutable source report while normalized fields are stored separately.

### 6.3 Missing, late or invalid reviews

- Missing mandatory report: session remains in the current phase.

- Invalid report: report is rejected and the assignment remains open.

- Reviewer withdrawal: assignment is cancelled with reason and replaced if required.

- Procedural waiver: allowed only when explicitly supported by methodology and recorded as a signed audit event.

- Timeout: v1 records overdue status but does not autonomously waive or replace a reviewer.

**RBE-ES-ORC-011** The orchestrator SHALL fail closed when a required report is absent.

**RBE-ES-ORC-012** The orchestrator SHALL expose a deterministic readiness assessment listing every unmet prerequisite.


## 7. Deterministic Decision Engine

### 7.1 Inputs

- Frozen methodology profile identifier, version, status, and checksum.
- Versioned decision rule set compatible with that profile.
- Completed mandatory assignments and accepted reports.
- Accepted, non-superseded findings and explicit severity mappings.
- Challenge dispositions, governance incidents, and integrity results.
- Frozen evidence, assessment, finding, and policy identifiers.

### 7.2 Evaluation Result

Decision evaluation returns two independent fields:

| Field | Values | Meaning |
|---|---|---|
| `process_status` | `READY`, `PROCEDURALLY_INCOMPLETE`, `BLOCKED`, `VOID` | Whether a substantive verdict may exist |
| `outcome` | `PASS`, `PASS_WITH_FINDINGS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, `DEFER_FOR_FURTHER_RESEARCH`, or null | Substantive conclusion under the active profile |

When `process_status` is not `READY`, `outcome` SHALL be null and no `BoardDecision` may be
ratified. Process status must never be disguised as `FAIL`.

### 7.3 Methodology Profile Contract

A methodology profile declares required roles, quorum, severity codes and mappings, outcome
subset, precedence, thresholds, reason-code templates, and evidence-sufficiency rules. RBE core
does not hardcode profile-specific SEV mappings. An ACTIVE profile's outcome subset must include
`INSUFFICIENT_EVIDENCE`. RBM-001's current three-outcome taxonomy is non-conforming until this
floor is added and the corrected profile receives named human approval.

**RBE-ES-DEC-001** Decision evaluation SHALL use a frozen, canonically serialized and hashed input
snapshot.

**RBE-ES-DEC-002** The engine SHALL reject an inactive, unknown, checksum-invalid, incomplete, or
architecture-incompatible methodology profile.

**RBE-ES-DEC-003** A profile rule set SHALL define total deterministic precedence for every valid
normalized input combination in its declared scope.

**RBE-ES-DEC-004** The core SHALL NOT infer severity effects, evidence sufficiency, quorum, or an
outcome absent from the active profile.

**RBE-ES-DEC-005** Every evaluation SHALL record rules applied, findings considered, counter-evidence,
reason codes, profile version, engine version, and snapshot hash.

**RBE-ES-DEC-006** Reviewer recommendations, votes, averages, commercial preference, timestamps,
and database row order SHALL NOT determine the outcome.

**RBE-ES-DEC-007** Explanation text SHALL be generated from versioned deterministic templates and
shall not claim greater scope or certainty than the frozen record supports.

### 7.4 Algorithm

```python
def evaluate_decision(snapshot, profile, rule_set):
    normalized = normalize(snapshot)
    validate_active_profile(profile, rule_set, normalized)
    process_status = evaluate_process_integrity(normalized, profile)
    if process_status != "READY":
        return evaluation(process_status=process_status, outcome=None)

    outcome, reasons = rule_set.evaluate(normalized)
    validate_outcome_is_permitted(profile, outcome)
    return evaluation(
        process_status="READY",
        outcome=outcome,
        reason_codes=reasons,
        snapshot_hash=canonical_hash(normalized),
    )
```

### 7.5 Ratification and Publication

Evaluation is machine-computed but non-authoritative until governance validation and accountable
human ratification succeed. Publication is a separate idempotent command and cannot alter the
ratified outcome.

**RBE-ES-DEC-008** Re-evaluation of a published decision SHALL require a governed successor review;
historical decisions remain immutable.

## 8. Persistence and Audit

### 8.1 SQLite schema


| Table | Purpose |
| --- | --- |
| review_sessions | Session identity, target, versions and status |
| review_packages | Package manifest and root checksum |
| review_package_items | Individual file or evidence entries |
| review_assignments | Role assignments and lifecycle |
| review_reports | Immutable report versions |
| findings | Immutable or versioned findings |
| finding_links | Duplicate, supersedes and related-finding relationships |
| evidence_references | Registered evidence locators and checksums |
| board_decisions | Signed and published deterministic decisions |
| remediation_plans | Corrective action records |
| audit_log | Hash-chained append-only events |
| idempotency_keys | Command replay protection |
| schema_migrations | Database migration state |


### 8.2 Transaction boundaries

**RBE-ES-PER-001** SQLite foreign key enforcement SHALL be enabled on every connection.

**RBE-ES-PER-002** State transition and corresponding audit entry SHALL commit in the same transaction.

**RBE-ES-PER-003** Decision record, input snapshot hash, generated artifact manifest and decision audit event SHALL commit atomically.

**RBE-ES-PER-004** Database migrations SHALL be ordered, checksum-verified and reversible where practical.

**RBE-ES-PER-005** The system SHALL refuse startup when the database schema is newer than the running engine supports.

### 8.3 Append-only and hash chaining

The audit log provides tamper evidence rather than a claim of absolute immutability. Each session has a monotonically increasing sequence. Each entry hash is computed from canonical event data and the previous entry hash.

    entry_hash = SHA256(

    canonical_json({

    "session_id": session_id,

    "sequence": sequence,

    "event_type": event_type,

    "actor": actor,

    "occurred_at": occurred_at,

    "payload": payload,

    "previous_hash": previous_hash

    })

    )

**RBE-ES-AUD-001** Audit entries SHALL never be updated or deleted through normal application interfaces.

**RBE-ES-AUD-002** The engine SHALL provide an audit verification command that recomputes and validates every hash link.

**RBE-ES-AUD-003** Administrative database repair SHALL be out of band, documented and detectable through subsequent verification.

**RBE-ES-AUD-004** Sensitive values that must not be logged SHALL be represented by stable redacted placeholders or hashes.


## 9. Machine-Readable Contracts

### 9.1 General schema rules

**RBE-ES-SCH-001** Every exported object SHALL include schema_id and schema_version.

**RBE-ES-SCH-002** Schemas SHALL set additionalProperties to false for normative objects unless extensibility is explicitly defined.

**RBE-ES-SCH-003** Enumerations SHALL be closed and versioned.

**RBE-ES-SCH-004** Canonical JSON serialization SHALL use UTF-8, sorted object keys, no insignificant whitespace and normalized numeric representation.

**RBE-ES-SCH-005** Artifact file names SHALL be deterministic and safe for cross-platform file systems.

### 9.2 Required artifact set


| Artifact | Format | Purpose |
| --- | --- | --- |
| session.json | JSON | Session metadata and status |
| package-manifest.json | JSON | Registered inputs and checksums |
| assignments.json | JSON | Review role and completion record |
| reports.json | JSON | Accepted report versions |
| findings.json | JSON | Normalized finding snapshot |
| decision.json | JSON | Deterministic decision certificate |
| audit.jsonl | JSON Lines | Ordered audit event stream |
| review-report.md | Markdown | Human-readable complete report |


### 9.3 Canonical bundle manifest

    {

    "schema_id": "rbe.review-bundle-manifest",

    "schema_version": "1.0.0",

    "session_id": "RB-01J...",

    "engine_version": "1.0.0",

    "methodology": {"id": "EXAMPLE-CONFORMING-PROFILE", "version": "1.0.0"},

    "process_status": "READY",
    "outcome": "PASS_WITH_FINDINGS",

    "artifacts": [

    {"path": "decision.json", "sha256": "...", "media_type": "application/json"},

    {"path": "review-report.md", "sha256": "...", "media_type": "text/markdown"}

    ],

    "bundle_root_hash": "..."

    }

**RBE-ES-SCH-006** The exported bundle SHALL include a manifest containing SHA-256 for every artifact.

**RBE-ES-SCH-007** The bundle root hash SHALL be computed over the canonical ordered artifact manifest.

**RBE-ES-SCH-008** An import validator SHALL validate schemas, checksums, versions and identifier consistency without modifying the source bundle.


## 10. Human-Readable Artifacts

### 10.1 Review report structure

1. Document identity and control information.

1. Target under review and package version.

1. Methodology, engine and rule-set versions.

1. Executive decision summary.

1. Procedural completeness statement.

1. Reviewer assignments and report status.

1. Findings grouped by severity and category.

1. Decision rationale and deterministic reason codes.

1. Required remediation and re-review conditions.

1. Evidence index.

1. Audit verification summary.

1. Machine-readable bundle manifest reference.

**RBE-ES-HUM-001** The Markdown report SHALL be generated from the same frozen decision snapshot used by the decision engine.

**RBE-ES-HUM-002** The report SHALL not contain facts that are absent from the structured records.

**RBE-ES-HUM-003** Finding order SHALL be deterministic: severity, category, stable finding identifier.

**RBE-ES-HUM-004** The report SHALL clearly distinguish reviewer recommendations from the final board decision.

**RBE-ES-HUM-005** The report SHALL identify unresolved findings and their remediation status.

### 10.2 Decision certificate

The decision certificate is a concise human and machine-verifiable summary. It includes session identity, target, verdict, methodology version, engine version, rule set, decision reason codes, snapshot hash, artifact manifest hash and publication actor. It is not a cryptographic signature unless an approved signing adapter is configured.


## 11. Application Programming Interface

### 11.1 API conventions

- Base path: /api/v1.

- Content type: application/json.

- Errors use a stable code, message, requirement reference and optional details.

- Create and transition operations support Idempotency-Key.

- ETag or record version is used for optimistic concurrency on mutable operational resources.

### 11.2 Required endpoints


| Method | Path | Purpose |
| --- | --- | --- |
| POST | /sessions | Create a review session |
| GET | /sessions/{session_id} | Read session |
| POST | /sessions/{session_id}/validate | Validate package and configuration |
| POST | /sessions/{session_id}/assignments | Create or register assignments |
| POST | /assignments/{assignment_id}/accept | Accept assignment |
| POST | /assignments/{assignment_id}/reports | Submit reviewer report |
| GET | /sessions/{session_id}/readiness | List unmet decision prerequisites |
| POST | /sessions/{session_id}/decision | Compute and publish deterministic decision |
| GET | /sessions/{session_id}/findings | List findings |
| POST | /findings/{finding_id}/remediation-plans | Create remediation plan |
| GET | /sessions/{session_id}/audit | Read ordered audit stream |
| POST | /sessions/{session_id}/export | Generate canonical artifact bundle |
| POST | /bundles/validate | Validate an exported bundle |


### 11.3 Error model

    {

    "error": {

    "code": "RBE_INVALID_TRANSITION",

    "message": "DECIDED is not reachable from INDEPENDENT_REVIEW",

    "requirement": "RBE-ES-LIF-004",

    "details": {

    "current_state": "INDEPENDENT_REVIEW",

    "requested_state": "DECIDED",

    "unmet_prerequisites": ["CHALLENGE", "CONSOLIDATION", "GOVERNANCE_VALIDATION"]

    },

    "correlation_id": "..."

    }

    }

**RBE-ES-API-001** The API SHALL never return raw stack traces, secrets or database paths.

**RBE-ES-API-002** Validation errors SHALL identify the rejected field or prerequisite.

**RBE-ES-API-003** Decision publication SHALL require an explicit command; reading a session SHALL never trigger decision calculation.

**RBE-ES-API-004** The OpenAPI document SHALL be generated or validated in CI.


## 12. User Interface Requirements

The v1 interface is an operator console, not an analytics dashboard. Its purpose is to run and inspect controlled reviews without hiding underlying records.


| View | Required content |
| --- | --- |
| Session list | Target, status, methodology version, created date, verdict, outstanding prerequisites |
| Session workspace | Package, lifecycle timeline, assignments, findings, decision and export actions |
| Assignment view | Role, reviewer, status, instructions, report submission and validation errors |
| Finding explorer | Severity, source report, evidence links, status, remediation and lineage |
| Decision view | Verdict, reason codes, finding counts, snapshot hash and publication metadata |
| Audit timeline | Ordered events, actor, timestamp, payload summary and chain verification |
| Artifact export | Bundle contents, hashes, validation result and download |


**RBE-ES-UI-001** The interface SHALL display the current session state and unmet prerequisites prominently.

**RBE-ES-UI-002** The interface SHALL not present reviewer recommendations as votes or aggregate approval percentages.

**RBE-ES-UI-003** Destructive-looking actions SHALL state their actual append-only behavior.

**RBE-ES-UI-004** The interface SHALL provide keyboard-accessible navigation and semantic labels for controls.

**RBE-ES-UI-005** The decision action SHALL present a deterministic preview of the input counts and blockers before publication.

**RBE-ES-UI-006** The interface SHALL not allow direct editing of published reports, findings, decisions or audit entries.


## 13. Security, Integrity and Privacy

### 13.1 Trust boundaries

- Review packages are untrusted input until validated.

- Reviewer identity assertions are trusted only through the configured local identity adapter.

- Stored Markdown and free text are untrusted display content and must be escaped in web views.

- Artifact bundles are untrusted on import until schema and checksum verification succeeds.

**RBE-ES-SEC-001** The engine SHALL validate file paths and SHALL prevent path traversal during package import and bundle export.

**RBE-ES-SEC-002** The engine SHALL enforce configurable maximum sizes for files, JSON bodies, reports and artifact bundles.

**RBE-ES-SEC-003** Rendered Markdown SHALL be sanitized; embedded scripts and unsafe HTML SHALL be disabled.

**RBE-ES-SEC-004** Checksums SHALL be recomputed by the engine and SHALL not be trusted solely because they were supplied by a client.

**RBE-ES-SEC-005** Secrets SHALL be supplied through environment or approved secret storage and SHALL not be committed to the repository.

**RBE-ES-SEC-006** Database backups and exported bundles MAY contain sensitive review material and SHALL be protected accordingly.

**RBE-ES-SEC-007** The application SHALL apply least-privilege authorization for operator, reviewer, publisher and auditor actions.

**RBE-ES-SEC-008** Publication of a decision SHALL require an authenticated accountable actor even though the verdict itself is machine-computed.

### 13.2 Privacy

**RBE-ES-PRI-001** The engine SHALL store only reviewer identity information necessary for accountability.

**RBE-ES-PRI-002** Audit payloads SHALL avoid duplicating full sensitive report bodies where stable identifiers and hashes are sufficient.

**RBE-ES-PRI-003** Retention and deletion policy SHALL operate at the controlled archive or system level and SHALL not silently remove individual material records from a surviving session.


## 14. Reliability and Non-Functional Requirements

**RBE-ES-NFR-001** For a session containing up to 1,000 findings and 50 reports, deterministic decision calculation SHOULD complete in under one second on a typical developer workstation.

**RBE-ES-NFR-002** Core unit tests SHALL run without network access.

**RBE-ES-NFR-003** The application SHALL start, migrate an empty database and execute a complete golden review on Linux in CI.

**RBE-ES-NFR-004** All logs SHALL include correlation_id and session_id when applicable.

**RBE-ES-NFR-005** Log messages SHALL use structured JSON in production mode and readable text in development mode.

**RBE-ES-NFR-006** The application SHALL expose health, readiness and version information.

**RBE-ES-NFR-007** The engine SHALL use UTC internally and SHALL not derive decision behavior from local time zone.

**RBE-ES-NFR-008** The implementation SHALL be formatted, linted, type-checked and tested in CI.

**RBE-ES-NFR-009** A clean checkout SHALL be buildable using documented commands without hidden local dependencies.

**RBE-ES-NFR-010** Generated files, caches, virtual environments, build output and local databases SHALL be excluded from source control.

### 14.1 Observability

- Session creation count and failures.

- Report validation failures by error code.

- State transition attempts and rejections.

- Decision calculation count and latency.

- Artifact generation and bundle validation failures.

- Audit chain verification status.

**RBE-ES-OBS-001** Metrics and logs SHALL not alter deterministic domain outputs.

**RBE-ES-OBS-002** Every failed command SHALL produce a correlation identifier suitable for tracing the request through logs and audit events.


## 15. Testing and Acceptance

### 15.1 Test Layers

| Layer | Required coverage |
|---|---|
| Unit | Rules, state transitions, canonical serialization, hashes, and invariants |
| Contract | Methodology profiles, JSON Schemas, OpenAPI, event envelopes, and errors |
| Integration | API, persistence, transactions, audit, outbox, and artifact generation |
| Golden | Byte-stable canonical JSON and Markdown outputs |
| Replay | Repeated runs and fresh databases produce compatible canonical results |
| Property | Order invariance, idempotency, monotonic audit sequence, and stable hashing |
| Security | Authorization, traversal, unsafe content, oversized inputs, and role conflicts |
| Migration | Every supported schema and requirement-ID migration path |

### 15.2 Mandatory Golden Scenarios

| ID | Scenario | Expected result |
|---|---|---|
| G-001 | Complete valid review, no findings | `READY` plus profile-permitted outcome |
| G-002 | Non-blocking findings | `READY` plus `PASS_WITH_FINDINGS` where permitted |
| G-003 | Profile-defined critical defect | `READY` plus `FAIL` |
| G-004 | Evidence below a profile's substantive threshold | `INSUFFICIENT_EVIDENCE` |
| G-005 | Bounded research action can close the gap | `DEFER_FOR_FURTHER_RESEARCH` where permitted; otherwise `INSUFFICIENT_EVIDENCE` |
| G-006 | Missing required report or quorum | `PROCEDURALLY_INCOMPLETE`, outcome null |
| G-007 | Integrity or disqualifying governance defect | `BLOCKED` or `VOID`, outcome null |
| G-008 | Duplicate command, same payload | Original result returned |
| G-009 | Same idempotency key, different payload | Conflict error and audit event |
| G-010 | Superseded report or finding | Only active versions considered |
| G-011 | Interrupted publication | No partial publication and no decision recalculation |
| G-012 | Audit entry tampered | Verification fails at the exact sequence |
| G-013 | Inactive methodology profile | Live evaluation rejected before review begins |
| G-014 | Unsupported profile outcome | Configuration rejected, no fallback outcome invented |

### 15.3 Acceptance Gates

**RBE-ES-TST-001** All mandatory golden, negative authorization, migration, package-integrity, and
deterministic replay scenarios SHALL pass.

**RBE-ES-TST-002** Decision and state-machine branch coverage SHALL be 100 percent.

**RBE-ES-TST-003** A replay suite SHALL compare canonical artifact hashes across at least 100 runs.

**RBE-ES-TST-004** The requirement register SHALL link every mandatory architecture and engineering
requirement to an implemented test or an explicit non-conformance record.

**RBE-ES-TST-005** No high or critical dependency vulnerability may remain without a named,
time-bounded approved exception.

**RBE-ES-TST-006** A clean migration and complete non-live foundation workflow SHALL run on Linux
in CI without network access.

## 16. Versioning and Compatibility

### 16.1 Independent version axes


| Versioned item | Example | Meaning |
| --- | --- | --- |
| Methodology | EXAMPLE-CONFORMING-PROFILE v1.0.0 | Governance authority |
| Engine | RBE v1.0.0 | Software implementation |
| Rule set | example-profile-decision v1.0.0 | Executable deterministic mapping |
| Artifact schema | rbe.decision v1.0.0 | Machine contract |


**RBE-ES-VER-001** The engine SHALL declare every methodology version and rule-set version it supports.

**RBE-ES-VER-002** Unsupported methodology versions SHALL fail validation before review begins.

**RBE-ES-VER-003** A breaking schema change SHALL increment the major version.

**RBE-ES-VER-004** Artifact bundles SHALL remain self-describing and independently validatable.

**RBE-ES-VER-005** The engine SHALL preserve the original engine, methodology and schema versions on imported sessions.

**RBE-ES-VER-006** Upgrading the software SHALL not rewrite historical decision artifacts.


## 17. Deployment and Operations

### 17.1 v1 deployment profile

This is the non-production Foundation profile. It proves deterministic domain behavior, persistence, artifacts, and audit controls. It SHALL NOT claim production conformance or issue binding live decisions.

- Single-process application.

- Local or controlled server deployment.

- One SQLite database file.

- Filesystem artifact store under a configured root.

- No mandatory external network services.

- Scheduled encrypted backup of database and artifact root.

**RBE-ES-OPS-001** The application SHALL validate configuration and writable storage before accepting commands.

**RBE-ES-OPS-002** Startup SHALL verify database migration state and audit-chain health for active sessions.

**RBE-ES-OPS-003** Shutdown SHALL stop accepting new commands and complete or roll back active transactions.

**RBE-ES-OPS-004** Backup documentation SHALL include database and artifact consistency requirements.

**RBE-ES-OPS-005** The repository SHALL include an operator runbook covering startup, migration, backup, restore, export validation and incident recovery.

### 17.2 Repository quality

- Source code, tests, schemas and documentation only.

- No committed local databases, build caches, compiled outputs or dependency directories.

- README with quick start and architecture summary.

- CHANGELOG and versioned migration notes.

- LICENSE or internal-use notice as appropriate.

- CI workflow for lint, type check, tests, schema validation and golden artifacts.

**RBE-ES-OPS-006** Codex SHALL implement on a dedicated feature branch and SHALL not merge without review.

**RBE-ES-OPS-007** The pull request SHALL contain a requirement-to-test summary and SHALL call out any non-conformance explicitly.


## 18. Explicit Non-Goals and Future Extensions

### 18.1 Non-goals for v1

- Autonomous AI reviewers or AI-authored final findings.

- Real-time multi-user collaborative editing.

- Enterprise SSO, SCIM or complex organization tenancy.

- Digital signature infrastructure or public transparency ledger.

- Distributed task queues and horizontal scaling.

- Automatic notifications, email workflows or external ticketing integrations.

- Analytics intended to rank reviewers or optimize approval rates.

- Automatic remediation approval.

### 18.2 Future-compatible extension points

- Pluggable reviewer-assistance adapters with explicit provenance.

- Cryptographic signing of decision certificates and bundles.

- PostgreSQL storage adapter.

- External object storage adapter.

- Organization and board tenancy.

- Notification and workflow adapters.

- Formal policy-as-data registry for multiple methodologies.

- Read-only public verification portal for selected decision certificates.

**RBE-ES-FUT-001** Extension points SHALL preserve the deterministic core and SHALL not permit adapters to override a computed verdict.

**RBE-ES-FUT-002** Any future AI-assisted function SHALL record model, prompt, version, source inputs and accountable reviewer acceptance.


## Appendix A. Canonical State Transition Table

This table is generated from and subordinate to `registers/state_machine.json`.

| From | To | Minimum prerequisite |
|---|---|---|
| `DRAFT` | `SUBMITTED` | Submission contract valid and immutable version sealed |
| `SUBMITTED` | `INTAKE_VALIDATION` | Submission digest verified |
| `INTAKE_VALIDATION` | `ACCEPTED` | All admissibility checks pass |
| `INTAKE_VALIDATION` | `RETURNED` | Remediable intake defect recorded |
| `RETURNED` | `SUBMITTED` | Successor submission sealed |
| `RETURNED` | `WITHDRAWN` | Authorized withdrawal confirmed |
| `ACCEPTED` | `EVIDENCE_LOCKED` | Evidence and policy baseline pinned |
| `EVIDENCE_LOCKED` | `ASSIGNMENT` | Required review functions known |
| `ASSIGNMENT` | `INDEPENDENT_REVIEW` | Eligibility, conflicts, and acceptance complete |
| `INDEPENDENT_REVIEW` | `CHALLENGE` | Required assessments sealed |
| `CHALLENGE` | `CLARIFICATION` | Bounded clarification approved |
| `CLARIFICATION` | `INDEPENDENT_REVIEW` | Material answer requires reassessment |
| `CLARIFICATION` | `CHALLENGE` | Challenge response supplied |
| `CHALLENGE` | `CONSOLIDATION` | Challenge obligations complete |
| `CONSOLIDATION` | `GOVERNANCE_VALIDATION` | Rule evaluation and package assembly complete |
| `GOVERNANCE_VALIDATION` | `BLOCKED` | Blocking process or integrity condition exists |
| `BLOCKED` | `GOVERNANCE_VALIDATION` | Condition resolved without invalidation |
| `BLOCKED` | `VOID` | Condition invalidates the session |
| `GOVERNANCE_VALIDATION` | `DECIDED` | Quorum, integrity, ratification, and signatures pass |
| `DECIDED` | `PUBLISHED` | Controlled publication package validates |
| `PUBLISHED` | `APPEALED` | Timely eligible appeal accepted |
| `PUBLISHED` | `FINAL` | Appeal window expires |
| `APPEALED` | `APPEAL_REVIEW` | Independent appeal panel valid |
| `APPEAL_REVIEW` | `UPHELD` | Appeal dismissed with rationale |
| `APPEAL_REVIEW` | `SUPERSEDED` | Successor decision issued |
| `APPEAL_REVIEW` | `REMANDED` | Further governed work specified |
| `REMANDED` | `ASSIGNMENT` | Linked successor session, remand scope, evidence lock, and assignment prerequisites valid |
| `UPHELD` | `FINAL` | Appeal report finalized |
| `SUPERSEDED` | `FINAL` | Successor decision published |
| `FINAL` | `ARCHIVED` | Retention and archive integrity checks pass |

## Appendix B. Decision and Process Tables

### B.1 Process Eligibility

| Condition | Process status | Substantive outcome |
|---|---|---|
| Session or integrity invalidated | `VOID` | null |
| Mandatory process incomplete | `PROCEDURALLY_INCOMPLETE` | null |
| Blocking governance condition | `BLOCKED` | null |
| Every process gate satisfied | `READY` | Evaluate active profile |

### B.2 Substantive Outcome Precedence

The active methodology profile defines deterministic precedence inside the canonical set. The core
engine validates that the mapping is total and cannot be influenced by user preference. It does not
hardcode SEV-to-outcome rules.

### B.3 RBM-001 Profile Boundary

RBM-001 currently declares only `PASS`, `PASS_WITH_FINDINGS`, and `FAIL`; it therefore fails the
mandatory `INSUFFICIENT_EVIDENCE` outcome floor. It cannot govern binding decisions until the
taxonomy is corrected, the profile is revalidated, and a named human authority approves and tags
the corrected release `ACTIVE`.

## Appendix C. Canonical JSON Examples

### C.1 Decision

    {

    "schema_id": "rbe.board-decision",

    "schema_version": "1.0.0",

    "decision_id": "RBD-01J...",

    "session_id": "RB-01J...",

    "status": "PUBLISHED",

    "process_status": "READY",
    "outcome": "PASS_WITH_FINDINGS",

    "methodology": {"id": "EXAMPLE-CONFORMING-PROFILE", "version": "1.0.0"},

    "engine_version": "1.0.0",

    "rule_set": {"id": "example-profile-decision", "version": "1.0.0"},

    "finding_summary": {"SEV-1": 0, "SEV-2": 0, "SEV-3": 2, "SEV-4": 1},

    "reason_codes": ["MATERIAL_FINDINGS"],

    "finding_snapshot_hash": "sha256:...",

    "explanation": "The review is procedurally complete. Two unresolved SEV-3 findings require tracked remediation.",

    "computed_at": "2026-07-18T20:00:00Z",

    "signed_at": "2026-07-18T20:01:00Z",

    "published_at": "2026-07-18T20:02:00Z",

    "published_by": {"actor_id": "actor:...", "display_name": "Accountable Publisher"}

    }

### C.2 Finding

    {

    "schema_id": "rbe.finding",

    "schema_version": "1.0.0",

    "finding_id": "RBF-01J...",

    "session_id": "RB-01J...",

    "source_report_id": "RBR-01J...",

    "severity": "SEV-3",

    "category": "traceability",

    "title": "Decision input lacks stable source linkage",

    "description": "A material decision claim cannot be traced to a registered evidence reference.",

    "evidence_reference_ids": ["RBEV-01J..."],

    "status": "OPEN",

    "remediation_required": true,

    "created_at": "2026-07-18T19:30:00Z"

    }

## Appendix D. Traceability Matrix


| Governance objective | Engineering requirements | Verification |
| --- | --- | --- |
| Methodology supremacy | RBE-ES-PUR-001, RBE-ES-DES-003 | Methodology compatibility tests |
| Deterministic decision | RBE-ES-PUR-002, RBE-ES-DEC-001..006 | Golden and replay tests |
| Human accountability | RBE-ES-DES-002, RBE-ES-SEC-008 | Authorization and provenance tests |
| Append-only records | RBE-ES-DOM-004..005, RBE-ES-AUD-001 | Mutation rejection tests |
| Evidence traceability | RBE-ES-DOM-002, RBE-ES-ORC-007 | Unknown reference rejection |
| Procedural completeness | RBE-ES-ORC-011..012, D-001 | Golden G-007 |
| Machine artifacts | RBE-ES-SCH-001..008 | Schema and bundle validation |
| Audit integrity | RBE-ES-AUD-001..004 | Tamper test G-012 |


## Appendix E. Codex Implementation Brief


| Instruction to Codex: Implement RBE-001 faithfully. Do not invent governance, alter severity semantics or replace deterministic rules with model inference. Raise specification ambiguities as explicit issues before coding around them. |
| --- |



### Required delivery

1. Create a dedicated feature branch named feat/rb-engine-v1 or equivalent.

1. Implement the domain model, state machine, orchestrator, deterministic decision engine, SQLite persistence, API, minimal operator UI and artifact exporter.

1. Add JSON Schemas and OpenAPI documentation.

1. Implement every mandatory golden scenario and deterministic replay test.

1. Add migration, runbook, README and requirement-to-test mapping.

1. Exclude generated artifacts, local databases, caches and dependency directories from the pull request.

1. Open a draft pull request. Do not merge.

1. Report every deviation or ambiguity against the exact RBE requirement identifier.

### Definition of done

- All mandatory RBE requirements implemented or explicitly declared non-conforming.

- All CI checks green.

- Golden artifacts stable across repeated runs.

- Fresh install and migration documented and verified.

- No AI or probabilistic logic in verdict computation.

- Review bundle validates independently.

- Pull request is focused and contains no generated clutter.



| End of controlled specification: Changes to this document after implementation begins must be versioned, reviewed and traceable. Implementation shall not silently redefine the specification. |
| --- |
