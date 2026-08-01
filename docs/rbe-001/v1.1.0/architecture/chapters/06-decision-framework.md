---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 6
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 6. Decision Framework

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 37 -->

## 6.1 Decision Philosophy
The decision framework converts signed assessments and governed findings into a conclusion
without importing preference. The engine does not ask which outcome is advantageous. It asks
which outcome is required by the locked methodology and the accepted review record.
Decision neutrality
PASS is not success. FAIL is not failure. INSUFFICIENT EVIDENCE is not indecision. Each is
a legitimate governance result when produced by the applicable rules.
**RBE-DEC-001** Decision logic SHALL be versioned, deterministic, inspectable and replayable.
**RBE-DEC-002** No statistical model, language model or opaque score SHALL issue the binding board
verdict.
**RBE-DEC-003** Every outcome SHALL include a machine-readable basis identifying the exact rules and
findings that produced it.
## 6.2 Decision Inputs
Input class Examples Integrity condition
Methodology status Complete, partial, non-
conforming.
Signed methodology
assessment.
Evidence sufficiency Coverage, independence,
quality, contradiction.
Traceable evidence
assessment.
Reasoning validity Supported inference, scope
alignment, assumptions.
Signed reasoning assessment.
Challenge status Resolved, accepted,
unresolved material
challenge.
Challenge record complete.
Commercial relevance Materiality under approved
criteria.
Only considered after
upstream validity.
Governance status Quorum, conflicts, incidents,
integrity.
Governance validation passed.
Findings Severity, blocking status,
disposition.
Normalized with immutable
lineage.
Conditions Required corrective action or
monitoring.
Explicit, bounded and testable.

<!-- Controlled source page 38 -->

## 6.3 Finding Severity and Effect
Severity Definition Typical decision effect
OBSERVATION Context that does not indicate
non-conformance.
No direct effect.
MINOR Limited defect that does not
undermine the central
conclusion.
May support PASS WITH
FINDINGS.
MAJOR Material defect that weakens
justification or requires
corrective action.
May block PASS or require
DEFER.
CRITICAL Defect that invalidates
justification, independence,
integrity or procedural
legitimacy.
FAIL, BLOCKED or VOID
according to type.
UNRESOLVED Severity cannot yet be
determined because required
information is missing.
INSUFFICIENT EVIDENCE or
DEFER.
**RBE-DEC-010** Severity SHALL be assigned by explicit methodology criteria and SHALL NOT be increased
or decreased to obtain a desired verdict.
**RBE-DEC-011** Governance-critical findings SHALL not be offset by high commercial relevance or large
evidence volume.
## 6.4 Outcome Taxonomy
### 6.4.1 PASS
PASS means the submitted conclusion is justified under the applicable methodology, all mandatory
governance conditions are satisfied, and no blocking finding remains. PASS does not authorize
implementation, investment or product development; it certifies the reviewed conclusion only.
- Methodology compliance satisfies the required threshold.
- Evidence is sufficient and appropriately independent for the stated scope.
- Reasoning follows from accepted evidence without material unsupported assumptions.
- Challenge phase identifies no unresolved blocking contradiction.
- Commercial relevance meets the required threshold where applicable.
- Governance validation and deterministic replay pass.
**RBE-DEC-020** PASS SHALL NOT be issued merely because the conclusion is plausible or commercially
attractive.

<!-- Controlled source page 39 -->

### 6.4.2 PASS WITH FINDINGS
PASS WITH FINDINGS means the central conclusion is justified, but material non-blocking findings,
limitations or conditions remain. The decision must make clear what passed, what did not, and
whether conditions affect downstream use.
**RBE-DEC-030** Each condition attached to PASS WITH FINDINGS SHALL be specific, measurable,
attributable and bounded in time or event.
**RBE-DEC-031** A condition SHALL NOT conceal a defect that should have produced FAIL, DEFER or
INSUFFICIENT EVIDENCE.
### 6.4.3 FAIL
FAIL means the submitted conclusion is not justified under the locked methodology or a critical
defect invalidates the review. FAIL is a conclusion about the present submission and evidence chain,
not a permanent claim that the underlying opportunity or proposition can never be valid.
- Critical methodology non-conformance.
- Evidence materially contradicts the conclusion.
- Evidence is selectively used or materially non-independent.
- Reasoning contains an unsupported leap essential to the conclusion.
- A critical governance defect invalidates legitimacy.
- Blocking finding remains unresolved.
**RBE-DEC-040** FAIL rationale SHALL identify the minimum decisive defects and SHALL not add
persuasive or punitive language.
### 6.4.4 INSUFFICIENT EVIDENCE
INSUFFICIENT EVIDENCE means the board cannot determine whether the conclusion is justified
because the evidence base does not support a defensible substantive decision. It is appropriate when
uncertainty is evidentiary rather than merely procedural.
- Source coverage below the required threshold.
- Material claims lack traceable support.
- Independence cannot be established.
- Contradictory evidence cannot be resolved from the package.
- Relevant population, geography or time period is underrepresented.
- Unavailable primary material prevents verification.
**RBE-DEC-050** INSUFFICIENT EVIDENCE SHALL state what evidence class is missing and why it is
material, without prescribing a desired eventual outcome.
### 6.4.5 DEFER FOR FURTHER RESEARCH
DEFER means a bounded research or clarification action is necessary and reasonably capable of
resolving the decision gap. It differs from INSUFFICIENT EVIDENCE by identifying a defined next
step rather than a generally inadequate evidence base.
**RBE-DEC-060** A DEFER decision SHALL define the research question, required artifact or verification
action, responsible role, and re-entry condition.
**RBE-DEC-061** DEFER SHALL NOT be used to avoid issuing an otherwise required FAIL.
**RBE-DEC-062** Every ACTIVE methodology profile SHALL permit `INSUFFICIENT_EVIDENCE`; if it omits
`DEFER_FOR_FURTHER_RESEARCH`, every bounded research gap SHALL map to `INSUFFICIENT_EVIDENCE` and
SHALL NOT map to PASS, PASS WITH FINDINGS or FAIL.

<!-- Controlled source page 40 -->

### 6.4.6 Non-outcome Process Statuses
`PROCEDURALLY_INCOMPLETE`, `BLOCKED`, and `VOID` are process statuses, not outcomes. They indicate
that a legitimate substantive decision cannot be issued because mandatory process, authority, or
integrity conditions are unmet. They are distinct from evidentiary insufficiency, and the
substantive outcome must remain null.
- Missing mandatory reviewer function.
- Unresolved disqualifying conflict.
- Broken evidence integrity chain.
- Invalid rule-set version.
- Unauthorized disclosure affecting independence.
- Decision replay failure.
## 6.5 Deterministic Precedence
Outcome precedence prevents commercial or evidentiary strength from masking procedural
invalidity and prevents positive factors from offsetting critical defects.
Priority Condition Decision result
1 Session invalidated by
integrity or governance rule.
Process status: VOID / BLOCKED; outcome: null.
2 Mandatory process
incomplete.
Process status: PROCEDURALLY INCOMPLETE / BLOCKED;
outcome: null.
3 Critical methodology, evidence
or reasoning defect.
Outcome: FAIL.
4 Evidence cannot support a
substantive judgment.
Outcome: INSUFFICIENT EVIDENCE.
5 Defined further research can
resolve a bounded gap.
Outcome: DEFER FOR FURTHER RESEARCH.
6 Conclusion justified with
material non-blocking
findings.
Outcome: PASS WITH FINDINGS.
7 Conclusion justified with no
blocking or material residual
findings.
Outcome: PASS.
**RBE-DEC-070** Decision precedence SHALL be encoded in the rule set and covered by automated tests.
## 6.6 Decision Rationale Contract
Rationale field Requirement
Decision statement One neutral sentence defining the outcome.
Scope Exact conclusion, population, geography, time
and package version reviewed.
Decisive basis Rules and findings sufficient to produce the

<!-- Controlled source page 41 -->

Rationale field Requirement
outcome.
Supporting basis Additional evidence and reasoning that
strengthens but does not independently
determine outcome.
Dissent Material contrary assessments and their
disposition.
Uncertainty Known limitations and what remains
unknown.
Conditions Any required action, owner and completion
test.
Non-implication What the decision does not authorize or prove.
Trace map Machine-readable links to findings, evidence,
rules and assessment versions.
**RBE-DEC-080** The rationale SHALL explain rather than persuade and SHALL avoid promotional,
celebratory, adversarial or punitive language.
**RBE-DEC-081** A published rationale SHALL not claim greater certainty or scope than the accepted
evidence supports.
## 6.7 Confidence and Uncertainty
Confidence describes robustness within the reviewed scope; it is not a substitute for decision rules. A
high-confidence FAIL and a high-confidence PASS are equally valid. Confidence must not be used to
turn an otherwise failing case into a pass.
Confidence dimension Question
Evidence coverage How completely does the package cover
material claim classes?
Source independence How likely are sources to represent genuinely
independent observations?
Verification strength How directly were source claims and artifacts
verified?
Reasoning robustness How sensitive is the conclusion to plausible
alternative assumptions?
Temporal relevance How well does the evidence represent the
relevant period?
Scope fit How closely does the evidence match the
asserted population and jurisdiction?

<!-- Controlled source page 42 -->

**RBE-DEC-090** Confidence SHALL be reported separately from outcome and SHALL not override blocking
rules.
## 6.8 Recommendations
Recommendations are subordinate to the decision. They may identify corrective actions, research
needs or downstream cautions, but they may not convert the Review Board into a product strategy
committee.
- Correct a specified methodological defect.
- Collect a defined missing evidence class.
- Narrow the conclusion to the supported scope.
- Re-run a defined validation step.
- Retain a limitation in all downstream use.
- Initiate a separate solution-validation or build-decision process after PASS.
**RBE-DEC-100** Recommendations SHALL be clearly labeled non-binding unless a methodology rule
makes a condition mandatory for the stated decision.
**RBE-DEC-101** The Review Board SHALL NOT recommend a specific product, vendor or implementation
unless that subject was explicitly within the approved review scope.
## 6.9 Appeals and Decision Lineage
**RBE-DEC-110** Every decision SHALL have a stable identifier, content digest, predecessor reference
where applicable and status indicating current or superseded authority.
**RBE-DEC-111** A superseding decision SHALL explain the appeal or new evidence basis and preserve the
full prior rationale.
## 6.10 Decision Test Matrix
Scenario Required outcome
Strong commercial case, weak evidence INSUFFICIENT EVIDENCE or FAIL; never PASS.
Strong evidence, invalid methodology
execution
FAIL or BLOCKED.
Valid evidence and reasoning, minor
documentation defect
PASS WITH FINDINGS if non-blocking.
Critical conflict of interest discovered before
publication
BLOCKED or VOID according to impact.
Contradictory sources with no defensible
resolution
INSUFFICIENT EVIDENCE.
Bounded missing verification can be obtained DEFER.
All thresholds met, no blocking findings PASS.
Executive demands approval despite
deterministic FAIL
FAIL remains; demand logged as governance
incident if coercive.
## 6.11 Normalized Outcome and Process-Status Contract

RBE-001 v1.1.0 separates a substantive `DecisionOutcome` from workflow and integrity
status. The canonical substantive outcomes are `PASS`, `PASS_WITH_FINDINGS`, `FAIL`,
`INSUFFICIENT_EVIDENCE`, and `DEFER_FOR_FURTHER_RESEARCH`. The values
`PROCEDURALLY_INCOMPLETE`, `BLOCKED`, and `VOID` are process statuses and SHALL NOT
be stored or presented as substantive verdicts.

A methodology profile MAY authorize only a subset of the substantive outcomes. The active
profile SHALL declare that subset and its deterministic mapping. When a process status blocks
evaluation, no substantive BoardDecision is created.

**RBE-DEC-120** The decision engine SHALL return process status separately from substantive
outcome and SHALL reject a profile that does not define a total deterministic mapping for its
permitted outcomes.
