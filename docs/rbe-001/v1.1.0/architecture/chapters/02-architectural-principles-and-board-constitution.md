---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 2
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 2. Architectural Principles and Board Constitution

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 8 -->

This section is the engineering constitution of the Review Board. Later design choices are valid only
when they preserve these principles.
## 2.1 Structural Impartiality
Impartiality must be created by system structure, not merely requested from reviewers. The
architecture separates functions, constrains information flows, records conflicts and prevents a
single actor from controlling incompatible parts of a review.
## 2.2 No Desired Outcome
The board has no approval quota, rejection quota, commercial objective, engineering preference or
reputational incentive attached to any verdict.
## 2.3 Methodology Supremacy
The approved methodology governs the board. Software cannot fill gaps by guessing; ambiguity
becomes a methodology issue or procedural blocker.
## 2.4 Evidence Traceability
Every material conclusion must be traceable to registered evidence, explicit reasoning or a defined
procedural rule.
## 2.5 Independent Reasoning
Each reviewer function produces its own analysis before aggregation and cannot see downstream
conclusions that could anchor its reasoning.
## 2.6 Explain, Never Persuade
Board artifacts explain what was concluded and why. They do not advocate for adoption,
investment, rejection or commercial action.
## 2.7 Challenge Before Finalization
A conclusion cannot be finalized until contrary evidence, alternative explanations, unsupported
assumptions and change-of-decision conditions have been examined.
## 2.8 Determinism
Identical normalized inputs, methodology version and rule-set version produce the same computed
outcome and canonical artifact content.
## 2.9 Append-Only Governance
Material records are immutable after acceptance. Corrections create superseding records with
lineage.
## 2.10 Human Accountability
Named accountable actors remain visible. AI assistance never becomes an anonymous decision-
maker.

<!-- Controlled source page 9 -->

## 2.11 Fail Closed
Missing inputs, invalid schemas, conflicts, unknown rule sets or unmet independence conditions
prevent finalization.
## 2.12 Reproducibility
An auditor can replay a session using the exported bundle and reproduce the computed decision.
## 2.13 Neutral Presentation
Language, ordering, color, defaults and dashboards must not nudge reviewers toward PASS, FAIL or
any commercial conclusion.
## 2.14 Least Necessary Knowledge
Each board function receives only the information needed for its assigned question, reducing
anchoring and cross-contamination.
## 2.15 Re-review, Not Rewrite
New evidence or corrected analysis creates a new linked review session; historical outcomes remain
intact.
## 2.16 Board Functional Separation
The Review Board is not a single reviewer persona. It is a set of independent functions with narrow
mandates. Implementations may use different human staffing models, but the logical functions and
incompatibility rules remain mandatory.
Board function Exclusive question
Methodology Review Was the required methodology followed
correctly and completely?
Evidence Review Is the evidence valid, independent, sufficient,
traceable and appropriately characterized?
Reasoning Review Do the findings and conclusion logically follow
from the evidence without unsupported
assumptions?
Challenge Review What contradicts the conclusion, what
alternatives exist, and what would change the
decision?
Commercial Relevance Review Assuming the conclusion is valid, is the verified
pain or capability commercially meaningful?
Governance Review Is the review complete, auditable, conflict-
cleared and ready for finalization?
Decision Assembly What outcome follows from accepted findings
under the fixed rule set?

<!-- Controlled source page 10 -->

**RBE-SEP-001** A reviewer SHALL be assigned to one logical board function per session unless RBM-001
explicitly permits a non-conflicting combination.
**RBE-SEP-002** The same actor SHALL NOT perform both evidence review and final governance approval
in the same session.
**RBE-SEP-003** The same actor SHALL NOT author the submitted research package and serve as an
independent board reviewer for that package.
**RBE-SEP-004** The same actor SHALL NOT perform reasoning review and decision assembly when the
methodology requires independent aggregation.
**RBE-SEP-005** Commercial review SHALL occur only after evidence and reasoning validity are
established; commercial attractiveness SHALL NOT cure evidentiary or logical defects.
**RBE-SEP-006** No board function SHALL alter another function’s accepted report. Disagreement SHALL
be recorded as a separate finding, challenge or escalation.
## 2.17 Information Barriers
Stage Information available
Methodology review Methodology, package manifest, process
records and required deliverables. Substantive
desired outcome hidden where practical.
Evidence review Evidence set, provenance, extraction records
and claims. Commercial recommendation and
build preference hidden.
Reasoning review Accepted evidence findings and submitted
reasoning chain. Commercial desirability
hidden.
Challenge review Evidence, reasoning and provisional findings;
no final verdict.
Commercial review Validated pain/capability findings and
uncertainty statement; not raw enthusiasm
from sponsors.
Governance review All reports, conflict declarations, rule-set
readiness and audit records.
Decision assembly Normalized accepted findings and procedural
state only.
**RBE-IBR-001** The engine SHOULD implement staged disclosure so that downstream recommendations
cannot anchor upstream independent reviews.
**RBE-INF-002** Any departure from staged disclosure SHALL be recorded with reason and risk
classification.

<!-- Controlled source page 11 -->

## 2.18 Bias and Conflict Controls
- Conflict-of-interest declaration before assignment acceptance.
- Automatic incompatibility checks against authorship, sponsorship and prior decisions.
- Independent report submission before peer reports are visible.
- No outcome-linked compensation or reviewer scoring.
- Neutral ordering and presentation of evidence.
- Mandatory identification of contrary evidence and alternative explanations.
- Explicit uncertainty and confidence statements.
- No reviewer voting by popularity; the rule set consumes findings and procedural state.
- Immutable record of every override request, rejected transition and recusal.
**RBE-BIAS-001** The system SHALL require a conflict declaration for every assignment before review
materials are released.
**RBE-BIAS-002** A declared material conflict SHALL block assignment acceptance unless an explicit
methodology-authorized exception is approved and audited.
**RBE-BIAS-003** The engine SHALL preserve reviewer independence by preventing access to peer
recommendations before initial report submission, unless the methodology explicitly defines a
collaborative phase.
**RBE-BIAS-004** The system SHALL NOT calculate reviewer performance using approval or rejection
frequency.
## 2.19 Decision Reasoning Standard
The board may state its reasoning clearly and directly. Impartiality does not require weak language,
artificial balance or reluctance to identify defects. It requires that the reasoning arise from evidence
and rules rather than preference.
**RBE-REA-001** Decision reasoning SHALL identify the decisive evidence, applicable rule, accepted finding
and logical connection to the outcome.
**RBE-REA-002** Decision reasoning SHALL distinguish facts, interpretations, assumptions, uncertainties
and methodology judgments.
**RBE-REA-003** The board SHALL state material weaknesses plainly even when the overall outcome is
PASS.
**RBE-REA-004** The board SHALL state material strengths plainly even when the overall outcome is FAIL.
**RBE-REA-005** The board SHALL document what additional evidence or correction could change a non-
PASS outcome where this can be specified without prejudging a future review.
## 2.20 AI Assistance Boundary
AI may support clerical and analytical work, but governance authority remains with named
reviewers and deterministic rules.
Permitted assistance Prohibited authority
Schema validation and formatting Setting final severity without accountable
reviewer acceptance
Duplicate detection suggestions Creating evidence that was not submitted

<!-- Controlled source page 12 -->

Permitted assistance Prohibited authority
Trace-link suggestions Closing findings autonomously
Summarization with source links Serving as the sole independent reviewer
Contradiction search assistance Changing rule-set logic during a session
Drafting neutral prose Selecting PASS or FAIL by generative judgment
**RBE-AI-130** Every AI-assisted output incorporated into a report SHALL be attributable, reviewable and
explicitly accepted by an accountable human actor or deterministic validation rule.
**RBE-AI-131** AI model identity, prompt or instruction version, timestamp and accepted output hash
SHOULD be retained when AI assistance materially influences reviewer analysis.
