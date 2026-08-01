---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 15
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 15. Event, Integration and Orchestration Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 98 -->

## 15.1 Purpose
This chapter defines how authoritative domain changes become durable events, how work is
coordinated without weakening transaction boundaries, and how external systems receive only
controlled, versioned information. Events communicate facts; they do not grant authority to bypass
the domain.
**RBE-EVT-001** Only committed authoritative changes SHALL produce integration events.
**RBE-EVT-002** An event consumer SHALL NOT infer permission to mutate governed state outside an
authorized command.
## 15.2 Domain Events and Integration Events
Type Audience Example Guarantee
Domain event Inside authoritative
application boundary EvidencePackageLocked Occurs within command
transaction
Integration event External modules or
systems DecisionPublished v1 Published through outbox
Workflow signal Coordinator and task
workers
ReviewDeadlineApproachi
ng Non-substantive scheduling
Audit event Governance ledger AssessmentSubmitted Immutable accountability
record
A single business action may create all four records, but each has a distinct purpose and retention
model.
## 15.3 Event Envelope
Field Meaning
event_id Globally unique immutable identifier
event_type Stable name plus version
occurred_at Trusted authoritative time
recorded_at Persistence time
aggregate_type / aggregate_id Source aggregate
aggregate_version Version after event
case_id / session_id Governance context
actor_id Responsible principal or system identity
correlation_id End-to-end operation
causation_id Command or prior event
classification Payload handling class
schema_version Contract version
payload Minimum necessary event data
integrity Optional signature or digest metadata
**RBE-EVT-010** Event payloads SHALL contain the minimum information required by declared consumers
and SHALL prefer references over duplicating restricted content.

<!-- Controlled source page 99 -->

## 15.4 Canonical Event Catalogue
Event Trigger Typical consumers
CaseRegistered Case created Workflow, analytics
SubmissionVersionSubmitted Submission frozen Intake queue
EvidenceItemVerified Upload finalized Evidence inventory
EvidencePackageLocked Evidence lock completed Review assignment
ReviewerAssigned Assignment accepted Work queue, notification
ConflictDeclared Reviewer declaration Chair, governance incident workflow
AssessmentSubmitted Reviewer submission Completion projection
ChallengeOpened Challenge recorded Relevant reviewer task queue
FindingsConsolidated Normalization complete Decision evaluation
DecisionEvaluated Rules executed Governance validation
DecisionRatified Board authority completes Report generation
DecisionPublished Approved output released Public/authorized downstream
systems
AppealLodged Valid appeal received Appeal workflow
ReReviewOpened Successor session created Lineage and assignment workflows
## 15.5 Transactional Outbox
Integration publication uses a transactional outbox. The domain transaction writes aggregate
changes, audit event and outbox record atomically. A publisher leases pending records, publishes
them, records broker acknowledgment and supports safe retry.
**RBE-EVT-020** Direct broker publication inside the authoritative database transaction SHALL NOT be
relied on for atomic delivery.
**RBE-EVT-021** Outbox consumers SHALL tolerate duplicate delivery and preserve event order where the
contract declares ordering significant.
## 15.6 Delivery Semantics
Concern Architectural rule
Delivery At least once
Deduplication Consumer stores processed event_id or equivalent
Ordering Per aggregate where required, not global unless justified
Retry Exponential backoff with bounded jitter
Poison messages Quarantine/dead-letter with operator workflow
Replay Controlled from retained event source or export
Acknowledgment Only after durable consumer effect
Schema incompatibility Quarantine and alert; never discard silently
## 15.7 Workflow Orchestration
The workflow coordinator manages tasks, deadlines, reminders, escalation notices and retries. It
does not decide outcomes or modify substantive findings. Every substantive transition is requested
through a domain command and revalidates current state and authorization.

<!-- Controlled source page 100 -->

- Create reviewer tasks after accepted assignment.
- Track due dates and send reminders.
- Open escalation tasks when service-level thresholds are missed.
- Request report rendering after decision ratification.
- Retry notifications and exports independently of decision state.
- Close obsolete tasks when a case transitions through an authoritative command.
**RBE-EVT-030** Workflow state SHALL be disposable and reconstructable from authoritative case state
and events.
**RBE-EVT-031** A scheduler or worker SHALL NOT force a substantive transition solely because a timer
expired.
## 15.8 Saga and Compensation Rules
Long-running cross-system processes use sagas only where an atomic local transaction is impossible.
Compensation creates new explicit actions; it never erases a historical governed event.
Process Authoritative step Possible compensation
Evidence ingestion Finalize verified EvidenceItem Mark unusable and create
replacement item
Decision publication Publish authoritative decision
Withdraw audience access through
new publication record; preserve
history
External export Create signed export manifest Revoke grant and issue corrected
export
Notification delivery Record notification request Retry or record delivery failure;
decision unchanged
**RBE-EVT-040** Compensation SHALL be auditable, reason-coded and linked to the action it addresses.
## 15.9 External Integration Principles
- Explicit data-processing purpose and owner.
- Allowlisted destination and credentials.
- Audience and classification filtering.
- Contract version and consumer identity.
- Rate limit, timeout and circuit breaker.
- Delivery and failure audit.
- Documented retention expectation at the receiver.
- Ability to disable integration without corrupting authoritative workflow.
**RBE-EVT-050** No external integration SHALL be required to reconstruct the authoritative decision
unless it is itself a governed evidence source whose content is preserved.
## 15.10 Notifications
Notifications are advisory. Email, chat or push messages may announce a task or publication but are
not the authoritative record. Sensitive content is minimized; recipients authenticate to view
governed details.
**RBE-EVT-060** Notification delivery failure SHALL NOT roll back a valid substantive transaction.

<!-- Controlled source page 101 -->

**RBE-EVT-061** Notification templates SHALL be versioned, audience-aware and free from outcome-
promotional language.
## 15.11 Replay and Backfill
Replay supports projection rebuild, controlled consumer recovery and audit investigation. Replayed
events retain their original event identity and timestamps and carry a replay context outside the
immutable payload.
- Authorize replay by scope, consumer and date/event range.
- Dry-run compatibility checks before high-volume replay.
- Throttle to protect production workloads.
- Prevent outward notifications unless explicitly enabled.
- Record replay initiator, purpose and result.
**RBE-EVT-070** Replay SHALL NOT create a second substantive domain effect for an already-applied
event.
## 15.12 Failure Handling and Operational Controls
Failure Required response
Broker unavailable Retain outbox, alert on age threshold and continue local
commits where safe
Consumer unavailable Retry and retain event
Schema invalid Quarantine, alert and preserve payload
Duplicate event Return success after confirming prior application
Out-of-order event Buffer, reject or rebuild according to consumer contract
Object reference unavailable Block dependent task and preserve event
Authorization drift Revalidate at command execution; do not trust stale task
assignment
## 15.13 Event Security and Privacy
- Encrypt transport and authenticate producers and consumers.
- Use topic or subscription authorization by event family and classification.
- Avoid evidence body, free-text rationale and personal data in broad events.
- Rotate credentials without event loss.
- Audit subscription creation and permission changes.
- Protect replay and dead-letter access as privileged operations.
## 15.14 Codex Implementation Contract
- Implement outbox publication with leases, retries and idempotent acknowledgment.
- Create a schema registry or equivalent reviewed event-contract repository.
- Generate consumers that reject unsupported major versions safely.
- Keep workflow coordinator decisions non-substantive.
- Add consumer contract tests for duplicate, delayed, out-of-order and replayed events.
- Expose operational dashboards for outbox age, dead-letter count and consumer lag.
- Never place full evidence content or unrestricted reviewer commentary in integration events.
- Document every consumer, purpose, classification and retention expectation.

<!-- Controlled source page 102 -->

## 15.15 Sections 12–15 Architecture Freeze Checklist
- Constitutional principles remain enforceable across service, API, data and event boundaries.
- Every mutating API maps to an explicit governed command.
- No generic administrative bypass exists.
- Authoritative writes, audit and outbox records commit atomically where required.
- All immutable artefacts have successor-based correction semantics.
- Every stored or transmitted data class has an owner, purpose and retention rule.
- AI remains outside authoritative decision authority.
- Workflow timers cannot determine substantive outcomes.
- External integrations can fail without corrupting the governed decision.
- Codex implementation contracts are testable and contain no unresolved architectural discretion.
## 15.16 Principal Architect and Principal Engineer Review Questions
Review lens Required question
Governance Can any component influence an outcome outside
methodology, evidence and reasoning?
Architecture Are module and trust boundaries explicit and
enforceable?
Engineering Can the design be implemented without inventing
substantive rules?
Security Can privileged access bypass separation of duties or audit?
Data Can every decision be reconstructed from retained
authoritative inputs?
Operations Do degraded modes fail safely without fabricating
progress?
Integration Can duplicate, delayed or failed messages alter
substantive truth?
Codex readiness Are commands, invariants, interfaces and tests sufficiently
explicit?
