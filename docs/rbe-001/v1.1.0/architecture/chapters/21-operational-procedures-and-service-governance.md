---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 21
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 21. Operational Procedures and Service Governance

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 135 -->

## 21.1 Purpose
This chapter defines how the Review Board Engine is operated after deployment. Operational
convenience shall never become an informal route around governance. Procedures must preserve
evidence integrity, reviewer independence, reproducibility and the distinction between technical
administration and substantive review authority.
**RBE-OPS-001** Operational procedures SHALL preserve the constitutional principles during normal,
degraded, emergency and recovery conditions.
**RBE-OPS-002** No operational role SHALL gain authority to create, alter or suppress a substantive Board
outcome merely because it maintains the platform.
## 21.2 Operating Model
Operational function Accountability
Service ownership Availability, lifecycle, risk and operating
readiness
Platform operations Infrastructure, deployment, monitoring and
recovery
Application operations Queues, integrations, configuration and service
health
Security operations Detection, response, access review and
vulnerability management
Governance operations Reviewer rosters, methodology versions, case
controls and procedural compliance
Data stewardship Retention, classification, quality and
authorized disposal
Audit and assurance Independent review of logs, controls, incidents
and exceptions
These functions may be performed by a small team during early implementation, but their
authorities and actions must remain logically separated and independently attributable.
## 21.3 Service Catalogue and Ownership
Every production service, datastore, integration and scheduled process shall have a named owner,
technical maintainer, data classification, recovery objective, dependency record and escalation path.
Ownership is a duty, not unrestricted privilege.
**RBE-OPS-010** A production component without a named accountable owner and documented support
path SHALL be considered non-operational and SHALL NOT be relied upon for authoritative review
processing.

<!-- Controlled source page 136 -->

## 21.4 Standard Operating Procedures
- Service start, stop and health validation.
- Deployment and rollback.
- Configuration promotion and emergency correction.
- Identity onboarding, role change and offboarding.
- Reviewer assignment support and conflict-control escalation.
- Evidence-ingestion exception handling.
- Queue backlog and integration failure handling.
- Report generation, signing and publication recovery.
- Backup validation and restoration.
- Incident declaration, communications and closure.
- Retention execution and legal hold.
- Methodology and template version activation.
**RBE-OPS-020** Every procedure that can affect authoritative records SHALL specify prerequisites,
authorized roles, validation checks, audit evidence, rollback or recovery, and post-action review.
## 21.5 Monitoring and Observability
Observability shall distinguish service health from governance health. A technically available
system may still be operationally unsafe if audit events are not persisting, evidence hashes fail,
reviewer conflicts are unresolved or report signatures cannot be verified.
Signal domain Examples
Availability Request success, latency, dependency
reachability
Processing Queue depth, command failures, workflow age,
stalled cases
Integrity Hash mismatch, audit discontinuity, signing
failure, replay mismatch
Security Authentication anomaly, privilege elevation,
export spike, policy denials
Governance Quorum failure, conflict backlog, overdue
challenge, unauthorized transition attempts
Capacity Storage growth, object count, broker lag,
database saturation
**RBE-OPS-030** Monitoring SHALL alert on integrity and governance failures even when conventional
availability metrics remain healthy.
**RBE-OPS-031** Operational telemetry SHALL avoid recording protected evidence content, secrets or
unnecessary personal data.

<!-- Controlled source page 137 -->

## 21.6 Alerting and Escalation
- Alerts are actionable, owned and severity-classified.
- Repeated non-actionable alerts are defects and must be corrected.
- Integrity and unauthorized-decision signals receive immediate escalation.
- Governance incidents are routed to governance authority, not only technical support.
- Escalation paths include out-of-hours ownership where service commitments require it.
- Every critical alert has a runbook and an auditable acknowledgement path.
**RBE-OPS-040** An alert suggesting possible alteration of evidence, audit history, decision authority or
signed reports SHALL be treated as a potential governance incident until disproved.
## 21.7 Incident Management
Incidents shall be classified by both technical severity and governance impact. The incident
commander coordinates restoration but cannot unilaterally decide whether affected reviews remain
valid.
Phase Required activities
Detect and declare Identify scope, severity, systems and potential
case impact
Contain Limit access or processing without destroying
evidence
Preserve Secure logs, snapshots, hashes, identity records
and affected artefacts
Restore Recover service through approved, tested
procedures
Assess governance impact Determine whether cases, evidence or
decisions require suspension or re-review
Communicate Provide accurate, role-appropriate status and
obligations
Review Root cause, control failure, corrective actions
and closure approval
**RBE-OPS-050** Incident response SHALL preserve forensic and governance evidence even where
preservation delays convenience-oriented restoration steps.
**RBE-OPS-051** A technically resolved incident SHALL remain open until potential impact on evidence,
reviews, decisions and reports has been assessed and documented.
## 21.8 Degraded Mode and Safe Failure
The platform may continue limited read-only or non-substantive functions during dependency
failures only when integrity can be proven. It shall not accept substantive actions that cannot be
durably audited, authorized and reconciled.
- Read-only access may be permitted when data freshness and integrity are explicit.

<!-- Controlled source page 138 -->

- New evidence ingestion stops when hashing, object storage or audit persistence is unavailable.
- Decision finalization stops when signing, quorum validation or immutable audit persistence is
unavailable.
- Queued commands retain actor and causation context and are revalidated before execution.
- Manual offline decisions are not silently imported as if created by the engine.
- Operators receive explicit degraded-mode indicators and prohibited-action explanations.
**RBE-OPS-060** The engine SHALL fail closed for substantive actions when authorization, audit durability,
evidence integrity or decision validation cannot be established.
## 21.9 Change and Release Management
Changes shall be categorized by risk and reviewed accordingly. Changes to methodology, decision
rules, state transitions, authorization policy, report meaning, audit semantics or evidence handling
are governance-significant even if the code change is small.
- Change record with purpose, scope, owner and risk.
- Linked architecture and requirement changes.
- Test and migration evidence.
- Security and governance review where applicable.
- Approval appropriate to risk.
- Deployment plan, observation window and rollback.
- Post-deployment validation and closure.
**RBE-OPS-070** Emergency changes SHALL be time-bounded, fully audited and retrospectively reviewed;
emergency status SHALL NOT remove constitutional or evidence-integrity controls.
## 21.10 Configuration and Feature-Flag Governance
Configuration is executable policy and shall be governed like code. Feature flags affecting
substantive workflows must not create alternate unreviewed decision paths.
**RBE-OPS-080** Production configuration SHALL be versioned, reviewed, promoted through controlled
automation and attributable to an approved change.
**RBE-OPS-081** A feature flag SHALL NOT disable mandatory review, challenge, quorum, audit, signing or
separation-of-duties controls.
## 21.11 Identity Lifecycle and Access Reviews
- Access granted from approved role and business need.
- Case assignments separately controlled from platform role.
- Conflict declarations evaluated before assignment and on material change.
- Role changes propagate promptly across identity, application and data layers.
- Offboarding revokes active sessions, tokens, keys and standing privileges.
- Periodic recertification covers human, service and emergency identities.
- Orphaned identities and inactive privileged access are removed.
**RBE-OPS-090** Access recertification SHALL verify both technical permission and continued eligibility
under independence and conflict-of-interest rules.

<!-- Controlled source page 139 -->

## 21.12 Evidence Operations
Operational handling of evidence shall preserve classification, integrity, chain of custody and the
exact set used by each review. Operators may remediate technical ingestion failures but may not
substitute evidence content or alter reviewer interpretation.
- Quarantine and validation of incoming files.
- Integrity hash generation and verification.
- Metadata correction through governed amendment, not silent overwrite.
- Redaction as a derived, linked artefact.
- Controlled export with purpose, scope and recipient recording.
- Legal hold and retention exceptions.
- Archive validation and periodic readability checks.
**RBE-OPS-100** Operational correction of evidence metadata SHALL create a new attributable version or
amendment record and SHALL preserve the prior state.
## 21.13 Backup, Restore and Disaster Recovery Operations
Backup success is not proof of recoverability. Restores must be exercised and validated across
databases, object stores, event infrastructure, configuration, keys and signed report artefacts.
**RBE-OPS-110** Recovery exercises SHALL validate cross-store consistency and provenance, not merely
successful restoration of individual technologies.
**RBE-OPS-111** After disaster recovery, substantive processing SHALL resume only after integrity,
authorization policy, audit continuity and report-signing capability are validated.
## 21.14 Data Retention, Archival and Disposal
Retention schedules shall distinguish operational logs, immutable governance audit, evidence,
derived artefacts, reports, security telemetry and temporary processing data. Disposal must be
authorized, verifiable and compatible with legal hold and reproducibility requirements.
**RBE-OPS-120** Deletion SHALL create an auditable disposal record identifying authority, scope, rule,
execution result and any retained tombstone or provenance reference.
**RBE-OPS-121** Retention reduction SHALL NOT make a finalized decision materially unreconstructable
while its governing retention obligation remains active.
## 21.15 Methodology and Policy Operations
Methodology versions, decision criteria, report templates and policy bundles shall be activated
through controlled releases. Historical cases retain the versions under which they were governed
unless a formal re-review is initiated.
**RBE-OPS-130** A new methodology or policy version SHALL NOT retroactively alter the meaning or status
of a finalized historical review.
**RBE-OPS-131** Activation records SHALL identify the approved version, effective time, approving
authority, affected case classes and rollback limitations.
## 21.16 Routine Governance Reviews
- Monthly review of stalled and overdue cases.
- Quarterly privileged-access and conflict-control review.

<!-- Controlled source page 140 -->

- Quarterly integrity and audit-chain validation.
- Periodic review of decision distribution for process anomalies, without outcome targets.
- Annual disaster-recovery and incident exercise.
- Annual methodology and report-template review.
- Review of AI use, model changes and unsupported-output incidents.
- Review of exceptions, risk acceptances and repeated manual interventions.
Outcome distribution may be examined for signs of process malfunction or bias, but the Board shall
never establish quotas for PASS, FAIL or any other result.
**RBE-OPS-140** Operational metrics SHALL NOT be converted into approval, rejection or throughput
targets that pressure substantive outcomes.
## 21.17 Service-Level Objectives and Error Budgets
Service-level objectives shall reflect user and governance needs. Availability targets must not
encourage bypassing safe-failure controls. Error budgets may govern release pace but cannot
authorize integrity or constitutional breaches.
**RBE-OPS-150** Integrity, unauthorized-decision and audit-loss events SHALL have a zero-tolerance
objective independent of general availability error budgets.
## 21.18 Documentation and Knowledge Management
- Runbooks are versioned and tested.
- Architecture decisions and operational constraints are linked.
- Known failure modes and recovery validation steps are documented.
- No critical procedure depends solely on undocumented personal knowledge.
- Changes to procedures are reviewed by affected technical and governance owners.
- Obsolete guidance is clearly withdrawn rather than left ambiguously available.
## 21.19 Chapter 21 Codex Build Contract
- Codex may generate runbook scaffolding, dashboards and operational automation from
approved requirements.
- Codex shall not create backdoor maintenance endpoints or unaudited repair scripts.
- Codex shall not implement an operator override that changes substantive outcomes.
- Automated remediation must be idempotent, bounded and fully logged.
- Generated operational tools must use ordinary authorization and workload identity.
- Where a procedure requires judgement about case validity, Codex shall route to the designated
governance authority.
**RBE-OPS-160** Operational automation generated by coding agents SHALL be subject to the same review,
testing, least-privilege and audit requirements as production application code.
## 21.20 Section Freeze Conditions
- Operational roles and escalation authorities are named.
- Critical runbooks and safe-failure rules are approved.
- Incident governance-impact assessment is defined.
- Change, configuration and emergency-access procedures are aligned with Chapters 9 and 16.
- Backup, restore and provenance validation procedures are accepted.

<!-- Controlled source page 141 -->

- Operational metrics are confirmed not to create outcome pressure.
