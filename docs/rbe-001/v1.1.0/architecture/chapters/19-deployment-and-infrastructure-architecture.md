---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 19
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 19. Deployment and Infrastructure Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 120 -->

## 19.1 Purpose
This chapter defines the environments, delivery pipeline, infrastructure controls and operational
topology used to deploy the Review Board Engine. Deployment must preserve the same governance
constraints as application design. Infrastructure administrators and release automation may move
approved software between environments; they may not alter review outcomes or decision rules
outside governed change paths.
**RBE-INF-001** Deployment architecture SHALL preserve the security, audit, separation-of-duties and
reproducibility requirements defined in Chapters 8–18.
## 19.2 Environment Model
Environment Purpose Data policy
Local development Developer implementation
and unit testing
Synthetic or approved
anonymized data only
Continuous integration Automated build, test and
security validation Ephemeral synthetic fixtures
Development integration Shared component integration Synthetic data; no production
secrets
Staging / pre-production Production-like acceptance
and operational rehearsal
Synthetic or formally
approved masked data
Production Authoritative governed
operation
Approved live data under
classification controls
Disaster-recovery
environment
Recovery readiness and
failover
Protected replicated
production data under
equivalent controls
**RBE-INF-010** Production data and secrets SHALL NOT be copied into lower environments except
through formally approved, controlled and auditable masking processes.
## 19.3 Baseline Production Topology
- Trusted web application and API ingress.
- Stateless application nodes.
- Background worker nodes separated by workload class.
- Authoritative relational database.
- Immutable evidence and report object storage.
- Durable queue or message broker.
- Central identity, secrets and key-management services.
- Observability pipeline and security monitoring.
- Controlled administrative access plane.
- Backup and disaster-recovery services.

<!-- Controlled source page 121 -->

**RBE-INF-020** All production components SHALL be deployed from versioned infrastructure definitions
and approved release artefacts.
## 19.4 Infrastructure as Code
Infrastructure definitions are controlled software artefacts. Networks, identities, policies, databases,
storage, queues, monitoring and deployment settings shall be declared, reviewed and reproducible.
Manual production changes are exceptional and must be reconciled back into code.
- Peer review and automated validation.
- Policy-as-code for mandatory security and resilience controls.
- Environment-specific values separated from reusable modules.
- No secrets embedded in infrastructure code or state outputs.
- Drift detection and operator-visible alerts.
- Immutable or replaceable infrastructure where practical.
**RBE-INF-030** Unreviewed manual infrastructure drift SHALL be treated as a configuration incident and
either reverted or codified through normal change control.
## 19.5 Build and Release Pipeline
Stage Required evidence
Source validation Branch protection, review approval and signed
commit or equivalent provenance
Build Reproducible build output and dependency
lock verification
Test Unit, integration, architecture, security and
migration tests
Scan Source, dependency, container and
infrastructure vulnerability results
Package Signed image or artefact with SBOM and
provenance attestation
Deploy to staging Automated deployment and smoke test
evidence
Approval Authorized production release approval with
linked change record
Production deployment Verified artefact digest and deployment audit
record
Post-deployment Health, migration and conformance checks
**RBE-INF-040** The pipeline SHALL promote the same signed artefact digest from staging to production;
production SHALL NOT rebuild source independently.
**RBE-INF-041** A deployment SHALL fail if provenance, signature or policy validation cannot be
completed.

<!-- Controlled source page 122 -->

## 19.6 Release Strategies
Deployments should minimize interruption and permit rapid recovery. Blue/green, rolling or canary
strategies may be used when they preserve schema compatibility, audit ordering and a single
authoritative write path.
- Backward-compatible application changes before destructive schema changes.
- Feature flags for non-substantive capabilities.
- Explicit migration sequencing.
- Automated smoke and conformance checks.
- Fast rollback of application artefacts.
- Forward-recovery plans where database changes cannot be safely rolled back.
**RBE-INF-050** Feature flags SHALL NOT be used to bypass constitutional, decision, audit or separation-of-
duties requirements.
## 19.7 Database Migration Architecture
Database migrations are governed release artefacts. Migrations must preserve historical data,
immutable provenance and compatibility with in-flight reviews. Destructive changes require staged
migration, verified backup and explicit archival or transformation rules.
**RBE-INF-060** Every production migration SHALL be versioned, repeatable, tested against representative
data and linked to a release record.
**RBE-INF-061** A migration SHALL NOT rewrite finalized decisions, audit events or evidence hashes
except through an explicitly approved corrective procedure that preserves the original record.
## 19.8 Configuration Management
Configuration class Control
Operational configuration Versioned, reviewed and environment-scoped
Decision-affecting configuration Immutable after activation and approved
through governance
Secrets Runtime injection from approved secret
manager
Feature flags Owned, time-bounded and reviewed for
removal
External endpoints Allowlisted, TLS-validated and environment-
specific
Logging levels Controlled to avoid sensitive-data exposure
**RBE-INF-070** The application SHALL resolve decision-affecting configuration by explicit version
identifier, not mutable environment default.
## 19.9 Container and Runtime Controls
- Minimal signed base images.

<!-- Controlled source page 123 -->

- Non-root runtime users.
- Read-only filesystem where compatible.
- Dropped Linux capabilities and restrictive security profiles.
- Resource requests and limits.
- No shell or package manager in production images unless formally justified.
- Runtime admission policies for signatures, provenance and vulnerability thresholds.
**RBE-INF-080** Production workloads SHALL run with the minimum operating-system and platform
privileges required for their declared function.
## 19.10 Network, DNS and Certificate Management
- Private data-plane connectivity.
- Controlled public ingress through managed edge protection.
- Service-to-service encryption and identity.
- Automated certificate issuance and rotation.
- DNS change governance and monitoring.
- Egress controls for external providers and AI services.
- No direct developer workstation access to production data services.
**RBE-INF-090** All documented production network flows SHALL have an owner, purpose, source,
destination, protocol and security control.
## 19.11 Observability Infrastructure
Logs, metrics and traces shall be collected centrally with environment, service, release and
correlation identifiers. Governance audit events remain authoritative in their dedicated store.
Observability infrastructure must be access-controlled and must not become a secondary repository
for protected evidence.
**RBE-INF-100** Production logs SHALL be structured, time-synchronized, tamper-resistant within the
retention period and protected from unauthorized deletion.
**RBE-INF-101** Release identifiers SHALL be included in telemetry so incidents can be correlated to
deployed code and configuration.
## 19.12 Backup and Recovery Infrastructure
- Automated encrypted backups.
- Separate administrative and cryptographic control.
- Cross-zone or cross-region protection appropriate to recovery objectives.
- Regular restore tests into isolated environments.
- Integrity validation after restore.
- Documented dependency order for full-platform recovery.
**RBE-INF-110** A backup SHALL not be considered successful until restoration and integrity verification
have been demonstrated on the approved schedule.
## 19.13 Change and Release Governance
Change class Approval expectation
Low-risk operational patch Automated tests and authorized release owner

<!-- Controlled source page 124 -->

Change class Approval expectation
Security-sensitive change Security review and release approval
Schema or migration change Database review, backup validation and
rollback/forward plan
Decision-rule or methodology change Governance approval and new immutable
version
Emergency change Time-bounded emergency approval and
mandatory retrospective review
AI model or prompt change AI evaluation and owner approval
proportional to risk
**RBE-INF-120** Emergency deployment authority SHALL NOT include authority to alter review outcomes,
finalized reports or immutable governance history.
## 19.14 Rollback and Recovery
Rollback must return the platform to a known good technical state without creating ambiguity about
governed records created during the failed release. Where data changes cannot be reversed safely,
the system shall use forward recovery and preserve a complete incident and migration history.
**RBE-INF-130** Rollback procedures SHALL preserve all valid audit events and shall not silently discard
acknowledged substantive commands.
## 19.15 Multi-Tenancy and Environment Isolation
Where multiple studies, boards or organizational tenants share the platform, isolation shall be
explicit at identity, authorization, data, storage, search, queue and observability layers. Shared
infrastructure does not imply shared access.
**RBE-INF-140** Tenant or study identifiers SHALL be propagated and enforced on every governed data
path.
## 19.16 Infrastructure Acceptance Criteria
- Reproducible environment creation from code.
- Verified identity, network and secret boundaries.
- Policy checks passing before deployment.
- Signed artefact promotion from staging.
- Restore and failover rehearsal completed.
- No unresolved critical vulnerabilities.
- Observability, alerting and runbooks operational.
- Architecture conformance checks passing.
**RBE-INF-150** Production readiness SHALL be evidenced by completed acceptance records, not verbal
assurance or unrecorded manual checks.

<!-- Controlled source page 125 -->

## 19.17 Codex Implementation Contract
- Provide infrastructure definitions in a dedicated, reviewed repository path.
- Generate no production secret values in source-controlled files.
- Use signed, pinned images and immutable artefact references.
- Create environment parity without copying production data into lower environments.
- Implement deployment health, migration and conformance gates.
- Preserve one authoritative write path during rolling or canary deployment.
- Add rollback or forward-recovery procedures for every release-affecting change.
- Emit release and configuration identifiers into application telemetry and audit context.
- Document every manual production action and reconcile resulting drift.

<!-- Controlled source page 126 -->

Cross-Chapter Conformance Checklist
Area Required evidence before freeze
Security Threat model, access-control tests, privileged-
access design and incident-impact process
AI Model registry, prompt governance, evaluation
suite, provenance and kill switch
Reliability SLOs, capacity model, fail-closed behaviour,
backup and recovery evidence
Deployment Signed pipeline, IaC, migration controls,
environment isolation and rollback plan
Constitutional alignment
No mechanism creates outcome preference,
unsupported approval or non-reproducible
decision
Codex readiness Implementation contracts are testable and
leave no authority to invent governance rules
Section Freeze Conditions
Sections 16–19 may be marked frozen only after Principal Architect, Principal Software Engineer
and security review confirm that the controls are internally consistent with Chapters 1–15 and that
the implementation contracts are sufficiently precise for Codex. Freezing these chapters does not
authorize implementation of unresolved governance or methodology rules.
**RBE-FRZ-001** Any conflict between these chapters and the constitutional principles SHALL be resolved
in favour of the constitutional principles.
**RBE-FRZ-002** Any implementation ambiguity capable of changing substantive review outcomes SHALL
be returned for architecture clarification rather than inferred by Codex.

## 19.18 Normalized Release Status

Sections 16-19 are incorporated into the v1.1.0 normalized master.
Deployment choices remain gated by approved ADRs and do not authorize
Codex to invent decision-affecting behavior.

**RBE-DOC-200** Sections 20–23 SHALL be interpreted together with the preceding architecture sections
and SHALL NOT override earlier constitutional, governance, security, evidence-integrity or
separation-of-duties requirements.

<!-- Controlled source page 127 -->

**RBE-DOC-201** Where an implementation instruction conflicts with a constitutional principle, the
constitutional principle SHALL prevail and the conflict SHALL be escalated as an architecture
defect.
