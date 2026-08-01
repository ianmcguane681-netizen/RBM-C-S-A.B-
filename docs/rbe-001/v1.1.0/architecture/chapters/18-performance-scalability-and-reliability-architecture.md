---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 18
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 18. Performance, Scalability and Reliability Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 115 -->

## 18.1 Purpose
This chapter defines non-functional behaviour for the Review Board Engine. Performance and scale
are important, but they are subordinate to integrity, auditability and governance. The system may
delay a command when dependencies are unavailable; it may not acknowledge a substantive state
change that was not durably committed and audited.
**RBE-NFR-001** Performance optimization SHALL NOT bypass authorization, validation, audit
persistence, integrity verification or separation-of-duties controls.
## 18.2 Service-Level Objectives
Capability Baseline objective Measurement boundary
Interactive read operations 95% under 2 seconds; 99%
under 5 seconds
Trusted edge to complete
response, excluding user
network
Substantive command
acknowledgement
95% under 3 seconds when
dependencies healthy
Receipt through durable
authoritative commit
Evidence metadata search 95% under 3 seconds Query request to result page
Report generation 95% under 60 seconds for
standard case
Queued job start to signed
artefact ready
Audit timeline query 95% under 5 seconds for
standard case
Request to complete ordered
response
Platform availability
99.9% monthly for core read
and governed command
surfaces
Externally observed service,
excluding approved
maintenance
Targets shall be calibrated with production evidence. The baseline values above are architecture
objectives, not permission to weaken controls.
## 18.3 Workload Model
- Low-to-moderate numbers of high-value review cases.
- Bursty evidence ingestion and report generation.
- Read-heavy navigation and audit queries.
- Write operations constrained by governance sequencing.
- Large immutable evidence objects stored outside the transactional database.
- Background jobs for indexing, rendering, notifications and integrity validation.
**RBE-NFR-010** Capacity models SHALL distinguish transactional metadata, evidence object storage,
search indexing, audit events and generated artefacts.

<!-- Controlled source page 116 -->

## 18.4 Scalability Strategy
The baseline modular-monolith architecture shall scale vertically first and horizontally at stateless
tiers. Scale-out of authoritative writes must preserve aggregate consistency and ordered governance
events. Service extraction is justified only when measured constraints exceed the safe capacity of the
modular design.
- Stateless API nodes behind a load balancer.
- Independent background worker pools by workload class.
- Read replicas and projections for non-authoritative queries.
- Partitioning of audit and event tables by time or tenant when required.
- Object storage for evidence and generated reports.
- Search indexes rebuilt from authoritative data.
- Back-pressure on ingestion and report queues.
**RBE-NFR-020** Horizontal scaling SHALL preserve idempotency, optimistic concurrency and single
authoritative transition semantics.
**RBE-NFR-021** No cached or replicated value SHALL be treated as authoritative for a substantive
decision command.
## 18.5 Concurrency and Consistency
Governed aggregates require strong consistency at the point of mutation. Reviewer work may occur
in parallel, but incompatible updates must be detected rather than silently overwritten.
- Optimistic concurrency tokens on governed aggregates.
- Idempotency keys for externally retried commands.
- Transactional outbox for event publication.
- Ordered processing within the relevant case or aggregate boundary.
- Explicit merge or re-review flow for conflicting human edits.
- No last-write-wins behaviour for findings, decisions or final reports.
**RBE-NFR-030** A stale command SHALL fail with a resolvable concurrency response and SHALL NOT
overwrite newer governed state.
## 18.6 Availability and Degraded Operation
Dependency failure Permitted degraded
behaviour Prohibited behaviour
Search index unavailable Use direct case navigation or
queue reindex
Treat missing search result as
missing evidence
Notification provider
unavailable Queue and retry notification Roll back valid decision
AI provider unavailable Disable assistance and
continue human workflow
Block core review or fabricate
AI result
Report renderer unavailable Queue regeneration from
immutable data
Publish incomplete or
unsigned report
Audit store unavailable Allow read-only operations Accept substantive mutation

<!-- Controlled source page 117 -->

Dependency failure Permitted degraded
behaviour Prohibited behaviour
where safe
Evidence object store
unavailable
Block affected task and
preserve state
Mark evidence verified
without retrieval
**RBE-NFR-040** The system SHALL fail closed for substantive writes when durable audit or authoritative
persistence cannot be confirmed.
## 18.7 Resilience Patterns
- Bounded retries with exponential backoff and jitter.
- Circuit breakers for unstable external dependencies.
- Timeouts appropriate to each call class.
- Bulkheads between interactive, report, indexing and notification workloads.
- Dead-letter handling with operator-visible remediation.
- Idempotent consumers and deduplication.
- Health checks that distinguish liveness, readiness and dependency degradation.
**RBE-NFR-050** Retries SHALL NOT create duplicate state transitions, reports, reviewer assignments or
notifications.
## 18.8 Backup, Recovery and Disaster Recovery
Asset Backup / protection
approach Recovery expectation
Transactional database
Encrypted point-in-time
recovery and tested full
backups
RPO <= 15 minutes; RTO <= 4
hours
Evidence objects
Versioned immutable storage
with cross-zone or cross-
region replication
No accepted evidence loss
after durable
acknowledgement
Audit records Append-only protected copy
and integrity verification
No silent gap; reconstruction
available
Signing keys Managed key service with
governed recovery
Publication resumes only after
key trust restored
Search indexes Rebuild from authoritative
sources
May be unavailable during
rebuild
Configuration and schemas Version-controlled, signed
release artefacts Restore exact active version
**RBE-NFR-060** Recovery exercises SHALL verify both technical restoration and preservation of
governance provenance.

<!-- Controlled source page 118 -->

**RBE-NFR-061** Recovered systems SHALL validate audit-chain and evidence-integrity status before
accepting substantive writes.
## 18.9 Data Integrity and Corruption Handling
Integrity checks must detect storage corruption, incomplete replication and accidental mutation. A
hash mismatch or missing event is a governance incident, not merely an infrastructure defect.
**RBE-NFR-070** Integrity validation failures SHALL quarantine the affected artefact, block dependent
decisions and create an incident record.
## 18.10 Capacity Management
- Forecast database, object, index and audit growth separately.
- Monitor queue depth, oldest-message age and worker saturation.
- Enforce upload-size and case-volume limits appropriate to approved use.
- Load-test report generation and evidence ingestion independently.
- Preserve headroom for incident replay, reindexing and audit export.
- Review capacity assumptions before onboarding materially larger workloads.
**RBE-NFR-080** Capacity alarms SHALL be set early enough to avoid emergency changes that bypass
normal governance.
## 18.11 Performance Testing
Test class Purpose
Baseline load test Validate expected case and user volume
Burst test Validate evidence-ingestion and report-
generation spikes
Soak test Detect leaks, queue growth and gradual
degradation
Failure test Measure behaviour during dependency outage
Recovery test Confirm backlog drains without duplicates or
ordering loss
Large-case test Validate evidence and audit navigation at
upper supported size
Security load test Confirm controls remain effective under abuse
and rate pressure
**RBE-NFR-090** Performance tests SHALL include authorization, audit and integrity controls; synthetic
bypass modes SHALL NOT be used for acceptance results.
## 18.12 Observability and Reliability Indicators
- Latency by command and query type.
- Error and rejection rates separated by business validation, authorization and infrastructure
failure.

<!-- Controlled source page 119 -->

- Queue depth and oldest item age.
- Database lock, deadlock and concurrency-conflict rates.
- Integrity verification failures.
- Report rendering and signing success rates.
- Recovery point age and backup verification status.
- SLO burn rate and error-budget consumption.
**RBE-NFR-100** Operational metrics SHALL not expose protected evidence content or reviewer-
confidential material.
## 18.13 Reliability Governance
Reliability work shall be prioritized by impact on governance capability. Failure modes that can
produce silent inconsistency, lost provenance or false acknowledgement are more severe than those
that cause visible delay.
**RBE-NFR-110** A release SHALL be blocked when known defects can cause untraceable mutation,
incorrect authorization, duplicate finalization or integrity loss.
## 18.14 Codex Implementation Contract
- Use idempotency and concurrency controls on every substantive command.
- Separate background workload pools and apply back-pressure.
- Never serve a cached value as authoritative for mutation preconditions.
- Implement health checks and explicit degraded modes.
- Preserve transactional outbox semantics.
- Provide restore and replay tooling as tested code, not manual assumptions.
- Instrument latency, failures, queue age and integrity checks.
- Add chaos and recovery tests for critical dependencies.
