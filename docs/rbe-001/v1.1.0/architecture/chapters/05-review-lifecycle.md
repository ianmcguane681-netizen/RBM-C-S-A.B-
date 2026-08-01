---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 5
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 5. Review Lifecycle

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 29 -->

## 5.1 Lifecycle Objective
The lifecycle converts a submitted package into a final, replayable board decision through controlled
states. Each state has defined entry conditions, permitted actors, required outputs and failure paths.
Movement is event-driven and recorded; no state may be skipped simply because a reviewer or
sponsor believes the answer is obvious.
**RBE-LIF-001** Every case SHALL exist in exactly one authoritative lifecycle state at a time.
**RBE-LIF-002** Every transition SHALL identify the triggering actor or rule, prior state, new state,
timestamp and supporting reason.
**RBE-LIF-003** Invalid transitions SHALL be rejected by the domain layer and recorded as security-
relevant events where appropriate.
## 5.2 Authoritative State Model
State Purpose Normal exit
DRAFT Assemble submission
metadata and candidate
package.
SUBMITTED
SUBMITTED Create immutable submission
version and begin intake.
INTAKE_VALIDATION
INTAKE_VALIDATION Check package, methodology
and procedural completeness.
ACCEPTED or RETURNED
RETURNED Submission requires
correction before review.
SUBMITTED or WITHDRAWN
ACCEPTED Case is reviewable and ready
for evidence lock.
EVIDENCE_LOCKED
EVIDENCE_LOCKED Freeze the evidence and
methodology baseline.
ASSIGNMENT
ASSIGNMENT Select eligible reviewers and
adjudicate conflicts.
INDEPENDENT_REVIEW
INDEPENDENT_REVIEW Collect sealed function-specific
assessments.
CHALLENGE
CHALLENGE Test contradictions,
assumptions and alternative
explanations.
CLARIFICATION or
CONSOLIDATION
CLARIFICATION Receive bounded answers or
governed amendments.
INDEPENDENT_REVIEW,
CHALLENGE or
CONSOLIDATION
CONSOLIDATION Normalize findings and GOVERNANCE_VALIDATION

<!-- Controlled source page 30 -->

State Purpose Normal exit
execute decision rules.
GOVERNANCE_VALIDATION Confirm quorum, integrity,
completeness and replay.
DECIDED or BLOCKED
BLOCKED A governance or procedural
issue prevents decision.
GOVERNANCE_VALIDATION
or VOID
DECIDED A signed board outcome exists. PUBLISHED
PUBLISHED Final artifacts issued and
appeal window open.
FINAL or APPEALED
APPEALED Authorized appeal under
defined grounds.
APPEAL_REVIEW
APPEAL_REVIEW Assess appeal without
mutating original decision.
UPHELD, SUPERSEDED or
REMANDED
FINAL Decision is closed and
retained.
ARCHIVED
ARCHIVED Long-term immutable
retention.
No normal exit
VOID Session invalidated; no
substantive board decision.
New case/session only
WITHDRAWN Submitter ended the case
before decision.
No normal exit
## 5.3 Submission and Intake Validation
- Case identity and scope
- Submission owner and authority
- Methodology identifier and version
- Rule-set identifier and version
- Declared conclusion under review
- Evidence manifest and artifact hashes
- Required study outputs
- Known limitations and assumptions
- Conflict-relevant parties
- Requested confidentiality classification
**RBE-LIF-010** Submission SHALL create an immutable submission version; later corrections SHALL
create a successor version.
**RBE-LIF-011** Intake validation SHALL assess reviewability, not substantive merit.
**RBE-LIF-012** A returned submission SHALL state each missing or invalid requirement without
suggesting a preferred substantive conclusion.

<!-- Controlled source page 31 -->

## 5.4 Evidence Lock
Evidence lock establishes the exact artifact universe against which independent review begins. It
prevents post hoc substitution, silent deletion and moving evidentiary targets.
Locked element Control
Artifact bytes Content hash and storage reference.
Manifest Immutable ordered list of evidence items and
metadata.
Methodology version Pinned identifier and digest.
Decision rule set Pinned identifier and digest.
Submission assertions Versioned claim and conclusion set.
Known exclusions Explicitly recorded missing, inaccessible or
out-of-scope material.
Access policy Role-based visibility map effective at lock time.
**RBE-LIF-020** No evidence item SHALL be replaced after lock. New material SHALL be introduced
through a governed amendment with lineage.
**RBE-LIF-021** The system SHALL compute and verify an evidence package digest before every decision
replay.
## 5.5 Assignment and Conflict Adjudication
Assignment is a governance operation, not a scheduling convenience. The engine evaluates role
requirements, reviewer eligibility, conflicts, availability and incompatible-role rules before any
substantive access is granted.
**RBE-LIF-030** A reviewer SHALL receive no substantive package access until assignment acceptance and
conflict declaration are complete.
**RBE-LIF-031** Assignment changes after access SHALL preserve the original assignment, access history
and removal reason.
## 5.6 Independent Review Stage
Assessment component Required content
Scope acknowledgment The exact question and artifacts reviewed.
Findings Structured issue records with severity, basis
and trace links.
Observations Non-decisive context kept distinct from
findings.
Reasoning Explicit chain from evidence or rule to
conclusion.
Uncertainty Known limitations, ambiguity and confidence

<!-- Controlled source page 32 -->

Assessment component Required content
constraints.
Requests Clarification or additional evidence requests
within role authority.
Attestation Identity, timestamp, methodology version and
independence declaration.
**RBE-LIF-040** Independent assessments SHALL be sealed before other reviewer conclusions are
disclosed.
**RBE-LIF-041** An assessment SHALL NOT be accepted unless all material findings contain a traceable
basis.
**RBE-LIF-042** A reviewer may conclude that no finding exists, but SHALL still provide scope
acknowledgment and reasoning sufficiency attestation.
## 5.7 Challenge Phase
The challenge phase is an adversarial quality control stage, not a ritual objection quota. It tests
whether the submitted conclusion survives credible contradiction, alternative explanations, omitted
evidence, assumption failure and boundary cases.
- Identify evidence that contradicts or materially weakens the conclusion.
- Identify plausible alternative explanations for the same evidence.
- Test whether claims exceed the population, jurisdiction, time period or scope supported.
- Test whether source dependence creates false independence.
- Identify hidden assumptions and evaluate sensitivity to their failure.
- Identify what additional evidence would change the conclusion.
- Distinguish absence of evidence from evidence of absence.
**RBE-LIF-050** Challenge findings SHALL be evaluated on articulated basis, not accepted merely because
they are skeptical.
**RBE-LIF-051** The board SHALL NOT require every challenge to be resolved in favor of the submission;
unresolved material challenges SHALL affect the deterministic outcome.
## 5.8 Clarification and Amendment
Mechanism Permitted use Not permitted
Clarification Explain an existing artifact,
term or calculation without
changing the evidence
baseline.
Introduce new evidence
disguised as explanation.
Correction Fix clerical or manifest error
with full lineage.
Erase the original error or
alter a sealed assessment.
Evidence amendment Add new evidence through a
new package version and
Silently add only favorable
sources.

<!-- Controlled source page 33 -->

Mechanism Permitted use Not permitted
defined re-review scope.
Methodology clarification Resolve prospective ambiguity
through authorized
governance.
Change locked rules for the
current case to obtain a result.
**RBE-LIF-060** Material amendments SHALL trigger re-evaluation of every assessment materially affected
by the change.
**RBE-LIF-061** The engine SHALL record which prior findings were invalidated, retained or superseded by
an amendment.
## 5.9 Consolidation
Consolidation groups related findings, preserves dissent, resolves duplicates and prepares
structured inputs for the decision rules. It does not flatten legitimate disagreement into artificial
consensus.
- Preserve original reviewer language and signed report version.
- Create normalized finding records with lineage to all source findings.
- Record whether findings agree, conflict or address different questions.
- Apply severity only under the configured methodology rules.
- Keep dissenting reasoning visible in the final artifact.
- Prohibit deletion of inconvenient findings.
**RBE-LIF-070** A normalized finding SHALL retain links to every contributing and dissenting source
finding.
**RBE-LIF-071** Consensus SHALL NOT be manufactured by majority vote unless the methodology
explicitly uses voting for the relevant question.
## 5.10 Governance Validation and Decision
Validation Failure effect
Rule-set and methodology digests valid Block.
All mandatory assessments signed Block.
Quorum satisfied Block.
Conflicts adjudicated Block.
Blocking incidents resolved Block.
Evidence digest valid Block.
Decision replay deterministic Block.
Final rationale trace coverage complete Block or methodology-defined defect.

<!-- Controlled source page 34 -->

**RBE-LIF-080** The decision SHALL be calculated only from authorized signed inputs and the locked rule
set.
**RBE-LIF-081** A human-readable rationale may explain the calculated outcome but SHALL NOT
contradict or replace the machine-readable decision basis.
## 5.11 Publication
- Final decision and definition
- Applicable methodology and rule-set versions
- Board composition by function
- Conflict and waiver summary
- Material findings and unresolved dissent
- Evidence and reasoning trace references
- Limitations and uncertainty
- Required follow-up or conditions
- Appeal rights and deadline
- Integrity identifiers and replay bundle reference
**RBE-LIF-090** Publication SHALL freeze a signed decision artifact and a machine-readable decision
record with matching integrity identifiers.
**RBE-LIF-091** The presentation layer SHALL use neutral visual treatment for every outcome.
## 5.12 Appeal and Re-review
Appeal is not a second opportunity to argue preference. It is a governed challenge to process, rule
application, evidence integrity or material error. The original decision remains immutable.
Appeal ground Example
Procedural defect Required function omitted or information
barrier breached.
Rule misapplication Decision engine applied the wrong threshold
or version.
Material factual error A finding relied on an incorrect registered fact.
Evidence integrity failure Artifact hash mismatch or source substitution.
Undisclosed conflict A disqualifying conflict existed during review.
New evidence Handled as a new evidence version and scoped
re-review, not retroactive mutation.
Disagreement with judgment alone Insufficient unless tied to an authorized
ground.
**RBE-LIF-100** Appeal reviewers SHALL be independent of the original decision to the extent defined by
methodology and availability rules.
**RBE-LIF-101** An appeal outcome SHALL be UPHELD, REMANDED or SUPERSEDED; it SHALL NOT edit the
original record.

<!-- Controlled source page 35 -->

## 5.13 Closure, Retention and Replay
**RBE-LIF-110** A final case SHALL retain every submission version, evidence manifest, access record,
assessment version, finding, incident, decision input, rule-set digest, decision output and appeal
artifact.
**RBE-LIF-111** The engine SHALL support deterministic replay without network access to mutable third-
party content, using retained evidence representations and hashes.
## 5.14 Transition Matrix
From To Trigger Primary guard
DRAFT SUBMITTED Submitter action Package schema valid.
SUBMITTED INTAKE_VALIDATION System event Submission version
sealed.
INTAKE_VALIDATION RETURNED Intake finding Correctable
procedural defects.
INTAKE_VALIDATION ACCEPTED Intake approval All mandatory
package conditions
met.
ACCEPTED EVIDENCE_LOCKED Lock command Manifest and hashes
valid.
EVIDENCE_LOCKED ASSIGNMENT System event Rule set and access
policy pinned.
ASSIGNMENT INDEPENDENT_REVIE
W
Coordinator action All mandatory roles
eligible and accepted.
INDEPENDENT_REVIE
W
CHALLENGE System event Required independent
reports sealed.
CHALLENGE CLARIFICATION Authorized request Bounded clarification
required.
CHALLENGE CONSOLIDATION System event Challenge
requirements
complete.
CONSOLIDATION GOVERNANCE_VALID
ATION
System event Decision inputs
normalized.
GOVERNANCE_VALID
ATION
DECIDED Decision engine All validation gates
pass.
GOVERNANCE_VALID
ATION
BLOCKED Governance rule Blocking defect exists.
DECIDED PUBLISHED Authorized
publication
Artifacts signed and
matched.

<!-- Controlled source page 36 -->

From To Trigger Primary guard
PUBLISHED APPEALED Valid appeal Within appeal
window and ground
valid.
PUBLISHED FINAL Appeal window
expiry
No valid appeal.
FINAL ARCHIVED Retention workflow Archive package
verified.
