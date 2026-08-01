---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 13
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 13. API and Command Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 90 -->

## 13.1 Purpose
The API is a governed command surface, not a thin database façade. It must express domain intent,
reject ambiguous mutation, preserve idempotency, expose failed preconditions clearly and avoid
endpoints that permit clients to assemble invalid states.
**RBE-API-001** Every mutating endpoint SHALL map to a named domain command with defined actor,
target, preconditions and audit effect.
**RBE-API-002** The API SHALL NOT expose unrestricted create, update or delete operations for governed
aggregates.
## 13.2 API Styles
Style Use Constraint
REST/JSON External and user-facing synchronous
commands and queries
Resource-oriented URLs with intent-
specific commands
Internal command bus Application-to-domain invocation Typed command and result contracts
Event subscription Asynchronous downstream
integration
Versioned event envelopes and at-
least-once semantics
Bulk export Audit, replay and governed reporting Asynchronous job with signed
manifest
## 13.3 Command Envelope
Every command shall carry a standard envelope sufficient for authorization, concurrency, replay
protection and audit correlation.
Field Required Meaning
command_id Yes Globally unique idempotency
identifier
command_type Yes Stable command name and version
actor_id Yes Authenticated principal or workload
identity
case_id Contextual Target review case
session_id Contextual Target board session
expected_version For aggregate mutation Optimistic concurrency token
correlation_id Yes End-to-end operation identifier
causation_id When derived Prior command or event identifier
requested_at Yes Client timestamp treated as
informational
reason_code For governed actions Controlled vocabulary rationale
payload Yes Command-specific validated data
**RBE-API-010** The server SHALL derive authorization identity from trusted authentication context, not
from a caller-supplied actor_id alone.

<!-- Controlled source page 91 -->

**RBE-API-011** Idempotency records SHALL bind command identity to actor, target and normalized
payload hash.
## 13.4 Core Command Catalogue
Command Authorized actor Key preconditions Primary result
RegisterCase Intake Officer Valid submission metadata DRAFT case
SubmitVersion Submitter/Intake Case accepts submission Immutable
SubmissionVersion
AcceptIntake Intake Officer Validation complete ACCEPTED state
LockEvidence Evidence Custodian Package complete and
verified EVIDENCE_LOCKED
AssignReviewer Board Chair/Assignment
Service Eligibility and SoD pass ReviewerAssignment
DeclareConflict Any assigned reviewer Active assignment Conflict declaration
SubmitAssessment Assigned reviewer Correct function and state Immutable
AssessmentReport
SubmitChallenge Eligible challenger Challenge window open Challenge record
RecordClarification Authorized party Clarification request open Linked clarification
ConsolidateFindings Decision Assembly role Required assessments
complete Normalized findings
EvaluateDecision Decision service Frozen rule set and inputs DecisionEvaluation
RatifyDecision Governance authority Quorum and validation
pass BoardDecision
PublishDecision Publication authority Signed outputs complete PUBLISHED state
LodgeAppeal Eligible appellant Ground and time
requirements AppealCase
OpenReReview Governance authority Permitted trigger Successor session
## 13.5 Query Model
Queries may use denormalized projections optimized for navigation and reporting, but every
substantive displayed value must retain a pointer to its authoritative source and version.
- Case summary projection.
- Reviewer work queue projection.
- Evidence inventory and integrity status projection.
- Decision provenance projection.
- Audit timeline projection.
- Public or audience-filtered decision projection.
**RBE-API-020** Query projections SHALL be rebuildable from authoritative records and events.
**RBE-API-021** A stale projection SHALL never be used to authorize a command or determine a
substantive outcome.
## 13.6 Error Contract
Category HTTP indication Required response content
Validation failure 400 Field path, code and safe explanation
Authentication required 401 No protected detail

<!-- Controlled source page 92 -->

Category HTTP indication Required response content
Authorization denied 403 Policy code without leaking restricted
content
Not found or hidden 404 Opaque response where disclosure is
restricted
Concurrency conflict 409 Current aggregate version and retry
guidance
Failed precondition 422 Exact governance precondition codes
Rate or capacity limit 429 Retry guidance
Dependency unavailable 503 Degraded-mode identifier and
correlation ID
**RBE-API-030** Error responses SHALL be deterministic, machine-readable and safe for the caller’s
authorization scope.
**RBE-API-031** The API SHALL distinguish business rejection from technical failure.
## 13.7 Idempotency and Concurrency
Clients and workers may retry. The architecture therefore treats duplicate delivery as normal.
Commands that could create substantive effects require idempotency keys, payload-hash
comparison and optimistic concurrency against the aggregate version.
**RBE-API-040** A repeated accepted command with the same idempotency key SHALL return the original
result.
**RBE-API-041** Reusing an idempotency key with a different normalized payload SHALL be rejected and
audited as a protocol violation.
**RBE-API-042** Lost-update prevention SHALL apply to all aggregate mutations.
## 13.8 Versioning and Compatibility
- Version external contracts independently from internal class names.
- Use additive changes where possible.
- Retain semantic meaning of existing fields.
- Publish deprecation windows and migration guidance.
- Keep event consumers tolerant of unknown additive fields.
- Never reinterpret a historical outcome code in place.
**RBE-API-050** Breaking contract changes SHALL require a new major version and a documented
migration path.
## 13.9 File and Evidence Transfer
Binary evidence shall be transferred using short-lived signed upload/download grants. Metadata
registration and finalization remain governed commands. A file is not evidence until malware
checks, hash computation, classification and metadata validation complete.
Step Command or operation Control
1 RequestUploadGrant Authorization, size and media policy
2 Direct upload to quarantine No case evidence status yet
3 FinalizeEvidenceItem Server hash and scan result required

<!-- Controlled source page 93 -->

Step Command or operation Control
4 AttachToEvidencePackage Package ownership and classification
check
5 LockEvidencePackage Completeness and chain-of-custody
validation
**RBE-API-060** Client-provided hashes SHALL be treated as claims and verified server-side.
**RBE-API-061** Download grants SHALL be audience-scoped, short-lived and logged.
## 13.10 API Security and Abuse Controls
- Schema and content-type validation.
- Request body and file size limits.
- Per-actor and per-client throttling.
- Replay protection for privileged commands.
- CSRF protection for browser sessions.
- Outbound URL allowlisting for any retrieval feature.
- Safe pagination limits and export quotas.
- No direct exposure of internal storage keys.
## 13.11 Example Decision Command Contract
Attribute Example
Command RatifyDecision v1
Target BoardSession
Required roles Governance Reviewer plus authorized Chair
Preconditions Assessments complete; challenge resolved; quorum valid;
no unresolved conflicts; evaluation frozen
Atomic writes BoardDecision, state transition, audit event, outbox event
Idempotency Required
Failure behavior No partial decision or transition
Output Decision identifier, outcome, rationale hash, aggregate
version and report-generation status
## 13.12 Codex Implementation Contract
- Generate OpenAPI schemas from reviewed contract definitions, not from database entities.
- Implement command handlers as thin adapters over domain services.
- Use explicit DTOs and reject unknown mutation fields where safety requires.
- Apply authorization before loading or returning protected content.
- Return stable error codes suitable for tests and clients.
- Write contract tests for idempotency, concurrency, forbidden transitions and audience filtering.
- Never add a generic PATCH endpoint for governed aggregates.
- Keep public decision APIs read-only and audience-filtered.
