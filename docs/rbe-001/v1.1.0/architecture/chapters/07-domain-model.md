---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 7
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 7. Domain Model

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 43 -->

## 7.1 Domain Modeling Principles
The domain model represents governance concepts directly. It avoids generic workflow objects that
erase the distinction between evidence, assessments, findings, decisions and audit events. Each
aggregate owns a narrow invariant and communicates through explicit identifiers and domain
events.
**RBE-DOM-001** Domain entities SHALL preserve the constitutional separation between source material,
reviewer judgment, normalized findings and board decision.
**RBE-DOM-002** Sealed or published substantive records SHALL be immutable; correction SHALL occur
through versioning and supersession.
**RBE-DOM-003** Every externally visible identifier SHALL be stable, opaque and unique within its entity
type.
## 7.2 Aggregate Overview
Aggregate Root entity Primary invariant
Review Case ReviewCase One authoritative case identity
and lifecycle state.
Submission SubmissionVersion Every submitted package is
immutable and lineaged.
Evidence Package EvidencePackage Manifest and artifact digests
remain stable after lock.
Board Session BoardSession Methodology, rule set and
mandatory role configuration
are pinned.
Assignment ReviewerAssignment Only eligible reviewers
receive role-scoped access.
Assessment AssessmentReport Signed independent reports
are immutable after sealing.
Finding NormalizedFinding Normalization preserves all
source lineage and dissent.
Decision BoardDecision Outcome is deterministic from
authorized inputs and rule
version.
Appeal AppealCase Original decision remains
immutable during appeal.
Governance Incident GovernanceIncident Every material governance

<!-- Controlled source page 44 -->

Aggregate Root entity Primary invariant
event has a disposition.
Audit Ledger AuditEvent Events are append-only,
ordered and attributable.
## 7.3 ReviewCase
ReviewCase is the top-level business identity for one submitted conclusion under review. It
coordinates lifecycle state but does not own evidence bytes, reviewer report content or decision-rule
implementation.
Attribute Meaning
case_id Stable opaque identifier.
case_type Golden Study, Solution Validation or other
approved review class.
title Human-readable case label.
scope Structured population, jurisdiction, period and
subject boundaries.
submission_owner_id Accountable submitting party.
current_state Authoritative lifecycle state.
confidentiality_class Access and handling classification.
created_at / closed_at Lifecycle timestamps.
current_submission_version_id Active immutable submission baseline.
current_board_session_id Active governed review session.
**RBE-DOM-010** A ReviewCase SHALL not directly store mutable “final verdict” text; authoritative
decisions belong to BoardDecision.
## 7.4 SubmissionVersion
Attribute Meaning
submission_version_id Immutable version identifier.
case_id Parent case.
version_number Monotonic case-local number.
declared_conclusion Exact proposition submitted for review.
methodology_id / version Claimed governing method.
package_schema_version Submission contract version.

<!-- Controlled source page 45 -->

Attribute Meaning
manifest_digest Digest of listed artifacts.
submitted_by / submitted_at Attribution and time.
predecessor_id Prior submission version where applicable.
change_summary Reason for correction or amendment.
**RBE-DOM-020** SubmissionVersion SHALL be immutable after submission.
## 7.5 EvidencePackage and EvidenceItem
Entity Key fields Invariant
EvidencePackage package_id,
submission_version_id, status,
digest, locked_at
A locked package cannot
change.
EvidenceItem item_id, package_id,
source_type, locator,
captured_content_ref,
content_hash
Content identity is verifiable.
EvidenceSource source_id, publisher/author,
jurisdiction, date,
independence metadata
Source identity and
provenance are explicit.
EvidenceClaimLink claim_id, item_id, locator,
excerpt_hash, relation
Every material claim can be
traced.
EvidenceExclusion exclusion_id, expected_class,
reason, materiality
Known gaps are recorded, not
hidden.
**RBE-DOM-030** Mutable external URLs SHALL not be treated as sufficient long-term evidence identity
without captured representation or verifiable archival reference.
**RBE-DOM-031** Evidence independence metadata SHALL distinguish distinct URLs from genuinely
independent underlying sources.
## 7.6 BoardSession
Attribute Meaning
board_session_id Identifier for one governed review execution.
case_id Parent case.
submission_version_id Exact submission reviewed.
methodology_version_id Pinned methodology.
rule_set_version_id Pinned deterministic rules.

<!-- Controlled source page 46 -->

Attribute Meaning
required_function_set Mandatory review functions.
evidence_package_digest Locked baseline digest.
status Session lifecycle status.
started_at / finalized_at Execution boundaries.
predecessor_session_id Lineage for re-review or appeal.
**RBE-DOM-040** A BoardSession SHALL reference exactly one locked submission version and one locked
evidence package baseline.
## 7.7 Reviewer and ReviewerAssignment
Entity Key fields
Reviewer reviewer_id, verified_identity_ref, capability
profile, active status.
ReviewerCredential credential_id, function, domain, issuer,
valid_from, valid_to.
ConflictDeclaration declaration_id, reviewer_id, session_id,
disclosed_facts, signed_at.
ConflictRuling ruling_id, declaration_id, decision, basis,
adjudicator, decided_at.
ReviewerAssignment assignment_id, session_id, reviewer_id,
function, scope, access_policy, status.
AssignmentAccessEvent event_id, assignment_id, artifact_id, action,
timestamp.
**RBE-DOM-050** ReviewerAssignment SHALL be the sole source of substantive artifact access authority
for a reviewer.
**RBE-DOM-051** Removal from assignment SHALL not delete prior access or activity records.
## 7.8 AssessmentReport
Attribute Meaning
assessment_id Stable identifier.
assignment_id Owning reviewer assignment.
assessment_type Methodology, evidence, reasoning, challenge,
commercial or governance.
version_number Monotonic report version.

<!-- Controlled source page 47 -->

Attribute Meaning
status Draft, sealed, superseded.
scope_acknowledgment Exact question and artifact set reviewed.
summary_conclusion Role-specific conclusion, not board verdict.
uncertainty_statement Known limits and confidence constraints.
signed_by / signed_at Attribution.
content_digest Integrity digest.
predecessor_id Prior version if amended.
**RBE-DOM-060** A sealed AssessmentReport SHALL be immutable and SHALL retain its exact visible
artifact set.
## 7.9 SourceFinding and NormalizedFinding
Entity Purpose
SourceFinding Reviewer-authored finding inside one sealed
assessment.
FindingBasis Evidence, rule, calculation or procedural basis
for a finding.
FindingTrace Link to precise artifact, claim, rule or event.
NormalizedFinding Board-level grouping of one or more source
findings.
FindingRelationship Agrees with, conflicts with, duplicates, narrows
or supersedes.
FindingDisposition Accepted, rejected, resolved, unresolved,
waived under rule.
FindingCondition Required action linked to a decision condition.
**RBE-DOM-070** Normalization SHALL NOT overwrite the source finding text, author, severity
recommendation or rationale.
**RBE-DOM-071** A disposition that rejects or downgrades a finding SHALL state the governing basis and
accountable actor or rule.
## 7.10 DecisionRuleSet and DecisionEvaluation
Entity Purpose
DecisionRuleSet Immutable versioned collection of executable
decision rules.

<!-- Controlled source page 48 -->

Entity Purpose
DecisionRule Single ordered rule with condition, effect and
explanation template.
RuleInputSnapshot Canonical snapshot of authorized inputs used
for evaluation.
RuleEvaluation Per-rule result, input references and execution
order.
DecisionCandidate Pre-publication calculated result.
ReplayResult Verification that the same inputs and version
reproduce the same output.
**RBE-DOM-080** DecisionRuleSet SHALL be content-addressed or cryptographically digested and
immutable once used by a session.
**RBE-DOM-081** Rule evaluation SHALL be pure with respect to substantive outcome: no network calls,
mutable external state or hidden model output.
## 7.11 BoardDecision
Attribute Meaning
decision_id Stable decision identifier.
board_session_id Session that produced the decision.
outcome_code Authorized taxonomy value.
decision_statement Neutral human-readable statement.
decisive_rule_ids Rules sufficient to determine outcome.
decisive_finding_ids Findings sufficient to determine outcome.
confidence_profile Separate multi-dimensional confidence record.
limitations Bounded uncertainty and scope limits.
conditions Structured required actions where applicable.
status Draft candidate, signed, published, superseded.
signed_at Finalization timestamp.
content_digest Integrity identifier.
predecessor_decision_id Lineage if superseding.
**RBE-DOM-090** BoardDecision SHALL not contain editable fields after signing.
**RBE-DOM-091** Published narrative and machine-readable decision SHALL share the same decision
identifier and digest linkage.

<!-- Controlled source page 49 -->

## 7.12 AppealCase
Attribute Meaning
appeal_id Stable identifier.
decision_id Original immutable decision.
appellant_id Authorized appellant.
ground_code Permitted appeal basis.
statement Claimed defect and requested remedy.
supporting_artifact_refs Registered appeal evidence.
status Submitted, accepted, rejected, under review,
decided.
appeal_session_id Independent appeal review session.
outcome UPHELD, REMANDED or SUPERSEDED.
successor_decision_id New decision where applicable.
**RBE-DOM-100** AppealCase SHALL reference, never modify, the original BoardDecision.
## 7.13 GovernanceIncident
Attribute Meaning
incident_id Stable incident identifier.
session_id Affected session.
incident_type Conflict, disclosure, coercion, tampering,
identity, system integrity or other.
severity Advisory, material, blocking or invalidating.
reported_by / detected_by Attribution.
facts Objective incident record.
affected_artifact_ids Potentially compromised objects.
status Open, investigating, mitigated, closed.
disposition Continue, pause, reassign, re-review, block or
void.
decided_by / decided_at Governance authority and time.
**RBE-DOM-110** GovernanceIncident facts and disposition SHALL be separated from speculation and
narrative commentary.

<!-- Controlled source page 50 -->

## 7.14 AuditEvent
Attribute Meaning
audit_event_id Globally unique event identifier.
aggregate_type / id Affected domain object.
event_type Named domain or security event.
actor_type / actor_id Human, service or rule identity.
occurred_at Authoritative timestamp.
correlation_id Request or workflow correlation.
causation_id Prior event that caused this event.
before_digest / after_digest Integrity references where applicable.
payload Schema-versioned event data.
signature / chain_hash Tamper-evidence metadata.
**RBE-DOM-120** Audit events SHALL be append-only and SHALL not contain secrets or unnecessary
personal data.
**RBE-DOM-121** The audit ledger SHALL support chronological reconstruction and causal reconstruction
of every decision.
## 7.15 ReviewReport and ReplayBundle
Artifact Contents
ReviewReport Decision, rationale, scope, board functions,
findings, dissent, uncertainty, conditions,
appeal rights and integrity references.
DecisionRecord JSON Canonical machine-readable decision and trace
map.
ReplayBundle Pinned rule set, canonical input snapshot,
evidence manifest and digests, assessment
digests, rule evaluations and expected output.
AuditExport Filtered but complete event chain appropriate
to authorized auditors.
EvidenceIndex Human and machine-readable source and
claim index.
**RBE-DOM-130** ReplayBundle SHALL be sufficient to verify decision determinism without relying on
mutable application database state.

<!-- Controlled source page 51 -->

## 7.16 Conceptual Relationship Model
The conceptual relationship model is expressed below in implementation-neutral form:
- ReviewCase 1 — N SubmissionVersion
- SubmissionVersion 1 — 1 EvidencePackage
- EvidencePackage 1 — N EvidenceItem
- ReviewCase 1 — N BoardSession
- BoardSession 1 — N ReviewerAssignment
- ReviewerAssignment 1 — N AssessmentReport versions
- AssessmentReport 1 — N SourceFinding
- NormalizedFinding N — M SourceFinding through FindingRelationship
- BoardSession 1 — 1 active DecisionRuleSet version
- BoardSession 1 — N DecisionEvaluation records
- BoardSession 1 — 0..N BoardDecision versions, only one current published authority
- BoardDecision 1 — 0..N AppealCase
- BoardSession 1 — 0..N GovernanceIncident
- Every aggregate 1 — N AuditEvent
## 7.17 Aggregate Invariants
Invariant ID Invariant
INV-001 A published decision cannot exist without a
valid board session, locked evidence package
and locked rule set.
INV-002 A reviewer cannot seal an assessment outside
an active eligible assignment.
INV-003 A locked evidence package cannot lose or
replace an item.
INV-004 A normalized finding cannot exist without at
least one source finding.
INV-005 A decision cannot reference an unsigned or
superseded assessment as current input.
INV-006 A PASS cannot coexist with an unresolved
blocking finding under the same rule set.
INV-007 An appeal cannot mutate the appealed
decision.
INV-008 A void session cannot publish a substantive
board decision.
INV-009 Every material decision reason must trace to a
rule and accepted input.
INV-010 No actor can both alter a sealed substantive
record and erase the audit evidence of that

<!-- Controlled source page 52 -->

Invariant ID Invariant
action.
## 7.18 Domain Events
- CaseCreated
- SubmissionVersionSubmitted
- IntakeReturned
- SubmissionAccepted
- EvidencePackageLocked
- ReviewerAssigned
- ConflictDeclared
- ConflictRuled
- AssessmentSealed
- ChallengeRaised
- ClarificationRequested
- EvidenceAmended
- FindingNormalized
- GovernanceIncidentOpened
- DecisionCalculated
- ReplayVerified
- DecisionSigned
- DecisionPublished
- AppealSubmitted
- AppealAccepted
- DecisionUpheld
- DecisionSuperseded
- CaseFinalized
- CaseArchived
**RBE-DOM-140** Domain event names and payload schemas SHALL be versioned and stable enough for
audit, integration and replay consumers.
## 7.19 Codex Implementation Boundaries for Chapters 4–7
- Implement domain rules before UI flows.
- Use explicit enums and state transition guards; do not encode lifecycle meaning in free text.
- Keep decision rules in versioned declarative or deterministic code modules with tests.
- Keep original assessments and source findings immutable after sealing.
- Use append-only audit records and content digests for all sealed artifacts.
- Do not permit administrators to edit signed substantive content through back-office screens.
- Expose role-scoped APIs that return only artifacts permitted by the information barrier.
- Generate final reports from authoritative domain records, not manually editable templates.
- Provide test fixtures for PASS, PASS WITH FINDINGS, FAIL, INSUFFICIENT EVIDENCE, DEFER,
BLOCKED and VOID.

<!-- Controlled source page 53 -->

- Provide deterministic replay tests and negative tests for every prohibited transition and
override.
**RBE-DOM-150** Codex SHALL treat the two constitutional principles as acceptance criteria for every
implementation decision made from these chapters.
## 7.20 Section Review and Freeze Criteria
Review gate Acceptance condition
Principal Engineer Entities, invariants, transitions and rule inputs
are implementable without guessing.
Principal Architect Governance separation and constitutional
principles are preserved across chapters.
Methodology Owner Terms and outcome meanings align with
RBM-001 or are explicitly marked pending
terminology lock.
Security Review No role or administrative path can bypass
sealing, access barriers or audit.
Data Review Versioning, immutability, lineage and
retention are internally consistent.
Codex Readiness Implementation contract is precise enough to
produce tests before UI work.
Freeze Requirement IDs stable; cross-references
verified; no unresolved blocking review
comments.
End of Sections 4–7

Sections 4–7 are incorporated into the normalized v1.1.0 master. Their requirements retain
architecture ownership and are read together with the canonical outcome, state, authority, and
requirement registers. Any later semantic change requires a versioned architecture decision and
cannot be introduced through implementation convenience.
