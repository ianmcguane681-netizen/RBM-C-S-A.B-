---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 12
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 12. System and Service Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 85 -->

## 12.1 Purpose
This chapter converts the governance, lifecycle, state, authorization and provenance requirements
established in Chapters 4–11 into an implementable system structure. The architecture must make
impartial review the path of least resistance and prohibited shortcuts technically difficult or
impossible.
**RBE-SYS-001** The system architecture SHALL enforce governance rules in domain services rather than
relying on user-interface convention.
**RBE-SYS-002** No infrastructure or application component SHALL possess an undocumented capability
to force a substantive decision outcome.
**RBE-SYS-003** Every service boundary SHALL preserve case identity, session identity, methodology
version, actor identity and correlation identifiers.
## 12.2 Architectural Style
RBE-001 shall begin as a modular monolith with explicit bounded modules, transactional
consistency inside the authoritative domain, and asynchronous integration at external boundaries.
This balances evidential integrity and implementation simplicity while retaining a migration path to
independently deployed services if scale or organizational boundaries later justify it.
- Modular monolith for the authoritative write model.
- Hexagonal architecture around domain modules.
- Command/query separation without premature infrastructure duplication.
- Outbox-driven publication for reliable external events.
- Stateless application nodes behind a trusted edge.
- Immutable object storage for evidence and signed report artefacts.
**RBE-SYS-010** Deployment topology SHALL NOT weaken module boundaries defined by this architecture.
**RBE-SYS-011** Service extraction SHALL require an architecture decision record demonstrating
preserved atomicity, traceability and separation of duties.
## 12.3 Logical Components
Component Primary responsibility Authoritative data
Trusted Edge
Authentication termination, request
validation, rate limiting and
correlation
No substantive case data
Identity and Access Module Role, case scope, conflict status and
policy evaluation
Assignments, roles and policy
decisions
Case Management Module Case registration, submissions,
lifecycle and ownership ReviewCase and SubmissionVersion
Evidence Module Evidence ingestion, locking,
classification, integrity and lineage
EvidencePackage, EvidenceItem and
hashes
Review Module Independent assessments, findings
and challenge responses AssessmentReport and findings
Decision Module Rule evaluation, consolidation and
decision assembly
DecisionEvaluation and
BoardDecision

<!-- Controlled source page 86 -->

Component Primary responsibility Authoritative data
Appeal Module Appeal grounds, admissibility and
successor sessions AppealCase and lineage
Audit and Provenance Module Append-only audit events and replay
bundles AuditEvent and provenance graph
Reporting Module Human and machine-readable
governed outputs ReviewReport and DecisionPackage
Workflow Coordinator Deadline tracking, notifications and
non-substantive orchestration Workflow timers and task projections
## 12.4 Trust Boundaries
The architecture recognizes distinct trust zones. Crossing a trust boundary requires identity
propagation, authorization, validation, classification handling and an audit event appropriate to the
action.
Boundary Inside Outside Required control
Public/Trusted Edge Authenticated application Browser, CLI and external
client
Strong authentication,
request size limits and
schema validation
Application/Authoritative
Domain Domain command handlers Edge and background
workers
Policy decision,
idempotency and
transaction boundary
Domain/Object Store Evidence metadata Binary evidence and
reports
Hash verification, signed
retrieval and malware
scanning
Domain/Integration Authoritative state Notification and
downstream systems
Outbox, allowlisted payload
and delivery audit
Human/AI Assistance Human-governed decision AI-generated suggestions
Attribution, non-
authoritative status and
human acceptance
**RBE-SYS-020** A trust-boundary crossing SHALL be observable through correlated logs and, where
governance-relevant, an immutable audit event.
**RBE-SYS-021** External systems SHALL receive only the minimum data required for their declared
purpose.
## 12.5 Deployment Topology
The baseline production topology consists of a web/API tier, background worker tier, relational
database, immutable object store, message broker or durable queue, key management service,
centralized observability stack and isolated administrative access plane.
Tier Characteristics Failure posture
Web/API Stateless, horizontally scalable, no
local authoritative state
Reject safely; clients may retry
idempotently
Worker Leased jobs, retry policies, poison
queue handling No duplicate substantive effect
Relational database Primary authoritative transactional
store Fail closed for writes

<!-- Controlled source page 87 -->

Tier Characteristics Failure posture
Object store Versioned or write-once retention for
governed artefacts Hash mismatch blocks use
Message transport At-least-once delivery with
deduplication
Delayed delivery does not alter
decisions
Observability Separate from authoritative audit Monitoring loss alerts but does not
create hidden state
## 12.6 Availability and Degraded Modes
Availability goals must never create a path around governance. Degraded operation may delay
intake, review, publication or notification; it may not fabricate approvals, bypass evidence lock, or
suppress audit.
- Read-only access may continue from verified replicas when writes are unavailable.
- New substantive commands are rejected if audit persistence cannot commit atomically.
- Notifications may queue while the authoritative decision remains final and visible.
- Report rendering may be retried from immutable decision data.
- Evidence retrieval failures place the affected review task into a blocked state.
**RBE-SYS-030** The system SHALL fail closed for any operation that would change governance state
without a durable audit record.
**RBE-SYS-031** Degraded-mode banners and machine-readable health responses SHALL distinguish
unavailable, read-only and partially degraded states.
## 12.7 Configuration and Methodology Control
Configuration capable of changing decision behaviour is governed content. Decision rules,
methodology versions, severity mappings, quorum thresholds and report schemas must be
versioned and activated through controlled release procedures.
**RBE-SYS-040** Decision-affecting configuration SHALL be immutable after activation and SHALL carry
effective-from metadata and an approval record.
**RBE-SYS-041** Ordinary operational administrators SHALL NOT modify active decision rules directly in
production.
**RBE-SYS-042** Every case SHALL resolve decision-affecting configuration by explicit version identifier,
never by “latest” at replay time.
## 12.8 AI Assistance Boundary
AI may assist with extraction, summarization, duplication detection, drafting and anomaly
surfacing. It remains outside the authoritative decision boundary. All AI outputs are suggestions
with provenance, model identification where available, prompt/context references, confidence
limitations and human acceptance status.
- AI cannot cast a vote or satisfy quorum.
- AI cannot create a final finding without human adoption.
- AI cannot alter evidence or methodology records.
- AI cannot approve its own suggestion.
- AI-generated text in a final report must be attributable to the accepting human reviewer.

<!-- Controlled source page 88 -->

**RBE-SYS-050** Disabling all AI assistance SHALL leave the complete governed review process
operational.
**RBE-SYS-051** AI failure SHALL degrade convenience only, not substantive governance capability.
## 12.9 Observability Architecture
Operational telemetry and governance audit are complementary but distinct. Logs, metrics and
traces diagnose system behaviour; audit events establish durable accountability. Neither may
silently substitute for the other.
Signal Purpose Examples
Metrics Health, capacity and service
objectives
Latency, queue age, error rate, lock
contention
Traces Cross-component request
reconstruction
Correlation ID, span hierarchy and
dependency time
Application logs Technical diagnostics Validation failure, retry and
dependency status
Audit events Governance accountability
Assignment, evidence lock,
assessment submission and decision
publication
**RBE-SYS-060** Sensitive evidence content SHALL NOT be copied into ordinary application logs.
**RBE-SYS-061** Observability identifiers SHALL permit correlation to an audit event without exposing
protected content.
## 12.10 Security Architecture Baseline
- Strong user authentication with phishing-resistant options for privileged roles.
- Short-lived service credentials and workload identity.
- Encryption in transit and at rest.
- Central key management with rotation and access logging.
- Network segmentation for data, application and administrative planes.
- Dependency and container vulnerability management.
- Secrets excluded from source control, logs and report artefacts.
- Backups tested through governed restoration exercises.
**RBE-SYS-070** Security controls SHALL preserve evidential integrity and reviewer independence as
explicit protection objectives.
## 12.11 Codex Implementation Contract
- Create modules that correspond to the bounded responsibilities in Section 12.3.
- Keep domain rules independent of web frameworks, database clients and queue libraries.
- Use dependency inversion for storage, time, identity, cryptographic and notification services.
- Do not introduce a generic super-admin route that bypasses domain commands.
- Emit correlation, causation, case and session identifiers on all substantive operations.
- Implement health checks that reveal dependency degradation without exposing secrets.
- Provide architecture tests that prevent prohibited module dependencies.
- Document every new cross-boundary data flow in an architecture decision record.
