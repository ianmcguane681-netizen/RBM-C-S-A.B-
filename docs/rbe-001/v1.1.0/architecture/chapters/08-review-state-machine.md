---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 8
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 8. Review State Machine

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 55 -->

## 8.1 Purpose
The Review State Machine is the authoritative representation of case progression. It converts
lifecycle policy into enforceable domain behaviour. The state machine prevents skipped controls,
unrecorded transitions, post hoc alteration and the use of informal status labels that have no
governance meaning.
**RBE-STM-001** Every review case SHALL have one and only one authoritative state.
**RBE-STM-002** State SHALL be derived from accepted transition events, not editable free text.
**RBE-STM-003** A transition SHALL execute only when its preconditions, actor authority, required
artefacts and invariants all pass.
## 8.2 State Categories
Category States Architectural meaning
Preparation DRAFT, SUBMITTED Submission assembly and
immutable handoff.
Admissibility INTAKE_VALIDATION,
RETURNED, ACCEPTED
Procedural reviewability, not
substantive merit.
Control establishment EVIDENCE_LOCKED,
ASSIGNMENT
Pin inputs and establish
eligible independent
reviewers.
Substantive review INDEPENDENT_REVIEW,
CHALLENGE, CLARIFICATION
Function-specific assessment
and adversarial testing.
Decision construction CONSOLIDATION,
GOVERNANCE_VALIDATION
Normalize findings, execute
rules and validate governance.
Decision and publication DECIDED, PUBLISHED Create signed outcome and
release controlled outputs.
Post-decision APPEALED, APPEAL_REVIEW,
UPHELD, SUPERSEDED,
REMANDED
Governed challenge without
mutating history.
Terminal FINAL, ARCHIVED, VOID,
WITHDRAWN
Closed, retained or invalidated
sessions.
## 8.3 Canonical State Definitions
State Definition Core invariant Normal exit
DRAFT Submission exists but
is mutable and not
reviewable.
Owner edits only; no
substantive reviewer
access.
Valid submission
contract.

<!-- Controlled source page 56 -->

State Definition Core invariant Normal exit
SUBMITTED A submission version
has been sealed.
No mutation; intake
metadata only.
INTAKE_VALIDATION
initiated.
INTAKE_VALIDATION Procedural
completeness and
eligibility are checked.
No substantive
judgement.
ACCEPTED or
RETURNED.
RETURNED Defects prevent
review.
Submitter may create
successor version.
Resubmission or
withdrawal.
ACCEPTED Case is procedurally
admissible.
Inputs still not
available to reviewers
until lock.
Evidence lock
complete.
EVIDENCE_LOCKED Evidence,
methodology and
ruleset are pinned.
Only governed
amendments; no
replacement.
Assignments valid.
ASSIGNMENT Reviewer eligibility,
conflicts and role
boundaries are
established.
No reviewer sees
content before
clearance.
Required assignments
accepted.
INDEPENDENT_REVIE
W
Reviewers produce
sealed assessments.
Assessments isolated
and signed.
All required
assessments sealed.
CHALLENGE Contradictions and
assumption failures
are tested.
Challenges must be
reasoned and
traceable.
Consolidation or
bounded clarification.
CLARIFICATION Defined questions are
answered without
reopening the entire
submission.
Scope-limited; all
changes lineage-
preserving.
Return to named prior
stage.
CONSOLIDATION Findings are
normalized and
decision rules
executed.
No new evidence or
hidden judgement.
Governance package
assembled.
GOVERNANCE_VALID
ATION
Quorum, integrity and
reproducibility are
verified.
No policy override. DECIDED or
BLOCKED.
BLOCKED A material
governance condition
prevents decision.
Substantive result
cannot be published.
Issue resolved or
session voided.
DECIDED A signed outcome
exists.
Immutable
substantive decision.
Publication.

<!-- Controlled source page 57 -->

State Definition Core invariant Normal exit
PUBLISHED Controlled reports are
released and appeal
window begins.
Only publication
metadata may
advance.
FINAL or APPEALED.
APPEALED A valid appeal has
been accepted.
Original decision
remains intact.
APPEAL_REVIEW.
APPEAL_REVIEW Appeal grounds are
evaluated by eligible
reviewers.
No de novo rewrite
unless remanded.
UPHELD,
SUPERSEDED or
REMANDED.
UPHELD Original decision
remains authoritative.
Appeal report
appended.
FINAL.
SUPERSEDED A new decision
replaces effect, not
history.
Both decisions
retained and linked.
FINAL.
REMANDED Case returns for
specified governed
work.
Scope of remand is
explicit.
ASSIGNMENT through a
linked successor session.
FINAL No ordinary workflow
remains.
Read-only except
retention operations.
ARCHIVED.
ARCHIVED Long-term immutable
retention.
No normal transition. None.
VOID Session is invalid due
to blocking defect.
No substantive verdict
may be inferred.
New session only.
WITHDRAWN Submitter ended case
before decision.
History retained. None.
## 8.4 Transition Contract
Transition field Requirement
Transition identifier Globally unique and immutable.
Case identifier Links to exactly one review case.
Prior state Must match current authoritative state.
Target state Must be permitted by transition matrix.
Trigger Human command, rule event, timeout or
system recovery event.
Actor Authenticated principal or named
deterministic service.

<!-- Controlled source page 58 -->

Transition field Requirement
Authority basis Role, scope and policy rule authorizing
transition.
Precondition result Machine-evaluated pass/fail with evidence.
Reason code Enumerated, non-empty and reportable.
Timestamp Trusted server time in UTC.
Artefact references Required supporting records and digests.
Audit event Append-only event committed atomically with
state change.
**RBE-STM-020** State change and transition audit event SHALL commit atomically.
**RBE-STM-021** A failed transition SHALL leave the case state unchanged and SHALL return the exact
failed precondition.
**RBE-STM-022** Retrying a transition with the same idempotency key SHALL NOT create duplicate state
changes.
## 8.5 Transition Matrix
From To Authority Minimum
precondition
DRAFT SUBMITTED Submitter Submission contract
valid; version seal
created.
SUBMITTED INTAKE_VALIDATION System Submission digest
verified.
INTAKE_VALIDATION ACCEPTED Intake officer All admissibility
checks pass.
INTAKE_VALIDATION RETURNED Intake officer At least one
remediable intake
defect.
RETURNED SUBMITTED Submitter Successor submission
version sealed.
RETURNED WITHDRAWN Submitter Withdrawal
confirmed.
ACCEPTED EVIDENCE_LOCKED System / intake officer Evidence manifest
and policy baseline
pinned.

<!-- Controlled source page 59 -->

From To Authority Minimum
precondition
EVIDENCE_LOCKED ASSIGNMENT Board coordinator Required review
functions known.
ASSIGNMENT INDEPENDENT_REVIE
W
System Eligibility, conflicts
and acceptance
complete.
INDEPENDENT_REVIE
W
CHALLENGE System All required
assessments sealed.
CHALLENGE CLARIFICATION Board coordinator Bounded clarification
request approved.
CLARIFICATION INDEPENDENT_REVIE
W
System Material answer
requires reviewer
reassessment.
CLARIFICATION CHALLENGE System Challenge response
supplied.
CHALLENGE CONSOLIDATION System Challenge obligations
complete.
CONSOLIDATION GOVERNANCE_VALID
ATION
Decision assembler Rule execution and
package assembly
complete.
GOVERNANCE_VALID
ATION
BLOCKED Governance reviewer Blocking defect exists.
BLOCKED GOVERNANCE_VALID
ATION
Governance reviewer Defect resolved
without invalidating
session.
BLOCKED VOID Governance authority Defect invalidates
session.
GOVERNANCE_VALID
ATION
DECIDED System All governance gates
pass; signatures valid.
DECIDED PUBLISHED Publication authority Publication package
validated.
PUBLISHED APPEALED Appeal registrar Appeal is timely and
eligible.
PUBLISHED FINAL System Appeal window
expired.
APPEALED APPEAL_REVIEW System Appeal panel valid.

<!-- Controlled source page 60 -->

From To Authority Minimum
precondition
APPEAL_REVIEW UPHELD Appeal panel Appeal denied with
rationale.
APPEAL_REVIEW SUPERSEDED Appeal panel New decision issued.
APPEAL_REVIEW REMANDED Appeal panel Specified further
review required.
REMANDED ASSIGNMENT Appeal registrar Linked successor session,
immutable remand scope,
locked evidence baseline and
assignment prerequisites valid.
UPHELD FINAL System Appeal report
finalized.
SUPERSEDED FINAL System Successor decision
published.
FINAL ARCHIVED Retention service Archival package and
retention checks
complete.
## 8.6 Forbidden Transitions
- DRAFT directly to INDEPENDENT_REVIEW
- RETURNED directly to ACCEPTED without successor submission
- EVIDENCE_LOCKED back to mutable DRAFT
- INDEPENDENT_REVIEW directly to DECIDED
- CHALLENGE bypassed because all reviewers agree
- BLOCKED directly to PUBLISHED
- DECIDED back to CONSOLIDATION
- PUBLISHED decision mutated in place
- FINAL reopened without appeal, remand or new session
- ARCHIVED changed by ordinary application commands
**RBE-STM-040** Forbidden transitions SHALL be impossible through both user interface and API.
**RBE-STM-041** Administrative privilege SHALL NOT bypass the transition matrix.
## 8.7 State Invariants
Invariant Applies from Rule
Input immutability EVIDENCE_LOCKED Evidence, methodology and
ruleset digests remain
unchanged.
Reviewer isolation INDEPENDENT_REVIEW No unsealed peer assessment
is visible.
Assessment completeness CHALLENGE Every required assessment is
signed and traceable.
Challenge completion CONSOLIDATION All mandatory challenge

<!-- Controlled source page 61 -->

Invariant Applies from Rule
questions have dispositions.
Decision determinism GOVERNANCE_VALIDATION Same pinned inputs and rule
version reproduce the
decision.
Publication consistency PUBLISHED Human and machine-readable
outputs share one decision
digest.
Historical immutability DECIDED onward No prior substantive artefact
can be overwritten.
Appeal non-destruction APPEALED onward Original decision remains
retrievable and verifiable.
Archive integrity ARCHIVED Package digest, retention
metadata and signatures
verify.
## 8.8 Timeouts, Stalls and Recovery
Condition Permitted response Not permitted
Reviewer overdue Reminder, reassignment after
governance check, or pause.
Automatic adverse finding.
Clarification overdue Return to challenge with
unanswered status, or defer
under rules.
Assume favourable answer.
System outage Resume from last committed
event and verify digests.
Reconstruct state from UI
labels.
Signature service unavailable Enter BLOCKED or wait. Publish unsigned decision.
Partial transaction Rollback uncommitted change
and log recovery event.
Manually edit state.
Corrupt artefact Block, verify source and
restore immutable copy.
Replace silently.
**RBE-STM-050** Timeouts SHALL affect workflow management only unless the methodology explicitly
assigns substantive meaning.
**RBE-STM-051** Recovery SHALL be event-replayable and shall not rely on undocumented operator
judgement.

<!-- Controlled source page 62 -->

## 8.9 Appeal and Re-review Semantics
An appeal contests a governed decision on defined grounds. A re-review is a new governed session
prompted by new evidence, a new methodology version, a remand or an invalidated prior session.
Neither mechanism edits historical records.
Mechanism Same case? Same evidence
baseline?
Original
decision
mutated?
Result
Appeal Yes Normally yes No Upheld,
superseded or
remanded.
New evidence re-
review
Linked successor
session
No No New
independent
decision.
Methodology-
version re-
review
Linked successor
session
May be same
evidence
No Decision under
new rules.
Void-session
restart
New session
linked to void
record
As governed No First valid
decision for
restarted work.
**RBE-STM-060** Every successor session SHALL declare why it exists and identify the prior session it
supersedes, remands or re-examines.
**RBE-STM-061** A remanded case SHALL re-enter through ASSIGNMENT in a linked successor session and
SHALL NOT bypass role eligibility, conflict, independence, evidence-lock, or assignment controls.
## 8.10 Codex Implementation Contract
- Implement transitions in the domain layer, not only route handlers.
- Use enumerated states and reason codes.
- Require optimistic concurrency or version checks on every transition.
- Persist transition and audit event in one transaction.
- Provide idempotency for external commands.
- Make forbidden transitions unrepresentable where practical.
- Expose a transition-explain endpoint returning failed preconditions without leaking protected
content.
- Write property-based tests for invariant preservation and invalid transition rejection.
- Do not implement manual database procedures as normal workflow operations.
