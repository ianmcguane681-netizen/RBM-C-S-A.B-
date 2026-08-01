---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 4
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 4. Governance Framework

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 22 -->

## 4.1 Purpose and Constitutional Status
The governance framework defines who may participate in a Review Board, what authority each
function possesses, how independence is preserved, and which actions are prohibited even when
expedient. It is not an administrative appendix. It is the control system that prevents an otherwise
capable review engine from becoming an approval mechanism, rejection mechanism or vehicle for
institutional preference.
**RBE-GOV-001** The governance framework SHALL be binding on every review case, reviewer,
administrator, methodology owner, sponsor and system operator.
**RBE-GOV-002** No project urgency, commercial opportunity, executive preference or engineering
investment SHALL suspend the constitutional principles.
**RBE-GOV-003** Where governance rules conflict with convenience or throughput, governance rules
SHALL prevail.
## 4.2 Board Charter
The Review Board charter is the formal mandate under which a case is examined. The charter
grants authority to assess justification; it does not grant authority to decide business strategy,
authorize development, amend research evidence or create missing methodology rules during a live
case.
Charter element Normative interpretation
Mandate Determine whether the submitted conclusion
is justified by the evidence, reasoning and
applicable methodology.
Jurisdiction Completed review packages submitted through
an authorized Provena workflow.
Authority Issue findings, procedural rulings and a board
decision within the configured decision
taxonomy.
No authority Direct product strategy, select vendors,
approve budgets, invent evidence, rewrite
methodology, or compel a PASS.
Accountability Methodology conformance, traceability,
independence, completeness and
reproducibility.
Success condition A defensible decision, including FAIL or
INSUFFICIENT EVIDENCE, produced without
outcome preference.

<!-- Controlled source page 23 -->

## 4.3 Functional Separation
The board is composed of separate review functions rather than one undifferentiated reviewer pool.
Each function asks a narrow question, receives only the information necessary to answer it, and
produces an independent signed assessment before any controlled consolidation occurs.
Function Primary question Prohibited substitution
Intake and procedural
validation
Is the case reviewable under
the declared methodology and
package contract?
Cannot decide substantive
merit.
Methodology review Was the approved method
followed correctly and
completely?
Cannot cure missing evidence
or score commercial value.
Evidence review Does the registered evidence
support the asserted facts and
findings?
Cannot invent unregistered
facts or infer desirability.
Reasoning review Do the conclusions logically
follow from the accepted
evidence and assumptions?
Cannot replace weak logic
with commercial intuition.
Challenge review What contradictions,
alternatives, assumptions or
failure modes could invalidate
the conclusion?
Cannot reject merely for being
skeptical; challenges require
articulated basis.
Commercial relevance review Assuming upstream validity, is
the verified problem
commercially material under
the approved criteria?
Cannot rescue failed
methodology, evidence or
reasoning.
Governance review Is the process complete,
independent, auditable and
ready for finalization?
Cannot rewrite substantive
assessments.
Decision consolidation What outcome is produced by
the approved rule set from
signed assessments and
findings?
Cannot negotiate a preferred
result.
**RBE-GOV-010** A reviewer SHALL NOT hold incompatible assignments in the same case unless an
explicitly versioned methodology rule permits it and the exception is recorded before review begins.
**RBE-GOV-011** Commercial review SHALL occur only after methodology, evidence and reasoning inputs
required by the rule set are complete.
**RBE-GOV-012** Decision consolidation SHALL consume signed structured outputs; it SHALL NOT
privately reinterpret reviewer intent.

<!-- Controlled source page 24 -->

## 4.4 Independence and Information Barriers
Independence is implemented through assignment controls, staged disclosure and immutable
timestamps. Reviewers must not be anchored by downstream verdicts, sponsor preferences or other
reviewers’ conclusions before their independent assessment is committed.
- Reviewer assignments are fixed and disclosed before access is granted.
- Independent reports are sealed until the applicable disclosure gate.
- Commercial reviewers cannot see desired build decisions, budget commitments or executive
sponsorship unless the methodology declares that information relevant.
- Challenge reviewers receive the conclusion and supporting chain but not a target verdict.
- Reviewer edits after sealing create a new version and preserve the prior version.
- System administrators can operate infrastructure but cannot alter substantive reports or
decisions.
**RBE-GOV-020** The system SHALL record exactly which artifacts were visible to each reviewer at the
time of assessment.
**RBE-GOV-021** The system SHALL NOT reveal another reviewer’s outcome before independent
submission unless the methodology explicitly defines a controlled joint stage.
**RBE-GOV-022** Any unauthorized disclosure or communication capable of influencing a reviewer SHALL
be logged as a governance incident and evaluated before finalization.
## 4.5 Reviewer Eligibility
Eligibility dimension Minimum control
Competence Demonstrated competence appropriate to the
assigned function and domain complexity.
Independence No disqualifying personal, financial,
operational or authorship conflict.
Methodology familiarity Current acknowledgment of the applicable
RBM and role obligations.
Confidentiality Accepted confidentiality and data-handling
duties.
Availability Sufficient time to complete the assignment
without delegation or rushed review.
Identity assurance Verified identity and attributable signed
submissions.
Tool literacy Able to inspect evidence, trace references and
submit schema-valid findings.
**RBE-GOV-030** Eligibility SHALL be evaluated per assignment, not assumed permanently from prior
participation.
**RBE-GOV-031** A reviewer who authored, materially directed or materially benefited from the submitted
conclusion SHALL NOT review that conclusion in an independent function.

<!-- Controlled source page 25 -->

## 4.6 Conflict-of-Interest Framework
Conflict management is preventive, not reputational. A declaration does not imply wrongdoing. Its
purpose is to identify circumstances that could reasonably affect, or appear to affect, impartial
judgment.
Conflict class Examples Default disposition
Direct financial Equity, fees, bonus,
commission or funding linked
to case outcome.
Disqualify.
Authorship or ownership Authored the study,
conclusion, scoring or solution
hypothesis under review.
Disqualify from independent
functions.
Operational dependency Responsible for a team,
roadmap or target that
benefits from PASS or FAIL.
Disqualify or restrict.
Personal relationship Close relationship with
submitter, sponsor or
materially affected party.
Independent governance
determination.
Prior advocacy Publicly or internally
committed to a specific
outcome.
Presume conflict; require
documented ruling.
Domain familiarity only Professional knowledge
without outcome dependency.
Not a conflict by itself; disclose
where relevant.
Institutional affiliation Shared employer or
organization without direct
dependency.
Assess case by case.
**RBE-GOV-040** Conflict declarations SHALL be completed before substantive artifact access.
**RBE-GOV-041** Conflict rulings SHALL identify the declared facts, governing rule, decision, decision-
maker and timestamp.
**RBE-GOV-042** A conflicted reviewer SHALL lose access to sealed case materials when removed from an
assignment, subject to audit retention.
## 4.7 Quorum and Decision Authority
Quorum is not merely headcount. A valid board requires all mandatory functions, sufficient eligible
reviewers, complete signed assessments and no unresolved disqualifying governance incident.
Condition Required status for decision
Mandatory functions All present or formally waived by a rule that
permits waiver.
Reviewer eligibility Confirmed for every active assignment.

<!-- Controlled source page 26 -->

Condition Required status for decision
Conflict declarations Complete and adjudicated.
Independent submissions Sealed before cross-review where required.
Blocking findings Resolved, accepted or deterministically
mapped to outcome.
Challenge phase Completed where required.
Governance incidents Closed or explicitly blocking.
Rule-set version Locked and valid for the full decision
calculation.
**RBE-GOV-050** The system SHALL calculate quorum from role coverage and governance state, not from a
simple reviewer count.
**RBE-GOV-051** No user SHALL manually set quorum to satisfied without an authorized, rule-based
waiver record.
## 4.8 Authority and Prohibited Overrides
Actor Permitted authority Explicit prohibition
Submitter Submit package, answer
clarification requests, provide
new evidence through
governed amendment.
Cannot edit reviewer reports
or final outcome.
Reviewer Assess assigned scope, raise
findings, request clarification,
sign report.
Cannot alter evidence or
another reviewer’s report.
Board chair / coordinator Manage process, schedule
gates, verify completeness.
Cannot coerce substantive
findings or choose verdict.
Methodology owner Publish future methodology
versions and clarifications
outside the live case.
Cannot retroactively change
the locked rules to obtain a
desired outcome.
System administrator Operate platform, permissions
and recovery procedures.
Cannot mutate sealed
substantive records.
Executive or sponsor Receive final artifacts and
initiate appeal or new
submission.
Cannot override, suppress or
relabel the decision.
**RBE-GOV-060** The engine SHALL have no “executive override”, “manual approval”, “force pass” or
equivalent capability.

<!-- Controlled source page 27 -->

**RBE-GOV-061** A decision may be superseded only by a new governed decision that preserves lineage to
the prior decision.
## 4.9 Escalation and Governance Incidents
- Unresolved conflict of interest.
- Unauthorized artifact disclosure.
- Evidence tampering or source substitution.
- Reviewer coercion or outcome pressure.
- Loss of rule-set integrity.
- Material system failure affecting traceability.
- Identity compromise or unauthorized signing.
- Attempted alteration of a sealed assessment or decision.
Severity Effect
Advisory Recorded; review may continue with
documented observation.
Material Review pauses until governance ruling.
Blocking Decision cannot be finalized.
Invalidating Current session is void; a new governed
session is required.
**RBE-GOV-070** Every governance incident SHALL produce an immutable incident record and disposition.
**RBE-GOV-071** A blocking incident SHALL prevent decision publication at the state-machine level, not
merely through user guidance.
## 4.10 Governance Metrics and Anti-Metrics
Permitted metric Purpose
Median review duration Capacity and process planning.
Clarification frequency Identify package-quality problems.
Appeal rate and appeal grounds Improve methodology clarity and process
quality.
Decision replay success Verify determinism.
Conflict declaration rate Monitor governance participation, not
reviewer quality.
Finding traceability coverage Measure audit completeness.
Prohibited or dangerous metric Reason
PASS rate target Creates approval pressure.
FAIL rate target Creates skepticism pressure.

<!-- Controlled source page 28 -->

Prohibited or dangerous metric Reason
Reviewer approval tendency ranking Encourages conformity and outcome gaming.
Commercial value attributed to reviewer Compromises independence.
Speed leaderboard Rewards rushed review.
Executive satisfaction with verdict Makes preference a success criterion.
**RBE-GOV-080** The platform SHALL NOT optimize reviewer performance against outcome distribution.
## 4.11 Governance Compliance Checklist
- Applicable methodology and rule set locked.
- Board functions complete and independently assigned.
- Eligibility and conflicts adjudicated.
- Information barriers enforced and logged.
- No prohibited override path exists.
- All substantive artifacts signed and versioned.
- Quorum calculated from rule-based conditions.
- Governance incidents resolved.
- Decision reproducible from retained inputs.
- Final report states uncertainty and limitations without persuasion.
