---
document_id: RBE-001
title: Review Board Engine Reference Architecture
release_version: 1.1.0
status: normalization-release-candidate
publication_date: 2026-07-19
proposed_supersedes: RBE-001-v1.0.0
supersession_effective_on: named-human-principal-architect-approval
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# RBE-001 Review Board Engine Reference Architecture

## Document Control

| Field | Value |
|---|---|
| Document identifier | RBE-001 |
| Version | 1.1.0 |
| Status | Normalization release candidate - ready for human approval |
| Coverage | Chapters 1-23 |
| Historical source | RBE-001 v1.0.0 controlled PDF, checksum recorded above |
| Implementation consumer | Codex and engineering teams |
| Methodology relationship | Methodology-neutral core; live use requires an ACTIVE profile |
| Owner | Project Exchange / Provena |

## Normalization Authority

This candidate retains the normative v1.0.0 architectural substance while resolving release
metadata, outcome semantics, state ownership, requirement namespaces, and the relationship
between constitutional architecture, implementation profiles, and active methodologies. The
normalization registers are normative where they explicitly resolve a v1.0.0 conflict.

# 1. Executive Summary and Architecture Mandate

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 4 -->

## 1.1 Purpose
The Review Board Engine (RBE) is the governed execution layer that turns a completed review
package and independent reviewer reports into a reproducible, inspectable and durable board
decision. The engine does not discover pain, invent solutions, conduct market research or determine
what Project Exchange wants to build. It evaluates whether a submitted conclusion is justified under
the approved methodology.
**RBE-MAN-001** The engine SHALL exist to execute an approved Review Board Methodology, not to
create, amend or reinterpret that methodology during a live review.
**RBE-MAN-002** The engine SHALL preserve a strict distinction between evidence, reviewer analysis,
findings, recommendations and the final board decision.
**RBE-MAN-003** The engine SHALL prevent any desired business, commercial or engineering outcome
from becoming an input to the decision calculation.
Foundational rule
The Review Board has no interest in whether a proposal succeeds or fails. Its sole
responsibility is to determine whether the conclusion presented is justified by the
evidence, reasoning, and methodology.
## 1.2 Problem Being Solved
Without a governed review layer, a Golden Study or Solution Validation may be well researched yet
still remain vulnerable to confirmation bias, inconsistent standards, hidden assumptions,
undocumented overrides, selective evidence use and commercial pressure. RBE addresses that
governance gap by enforcing structural independence, role separation, complete traceability and
deterministic decision rules.
Governance risk Architectural response
Confirmation bias Independent reviewer functions, blinded
inputs where practical, mandatory challenge
phase.
Outcome pressure No approval target, no rejection target, no
commercial success metric inside the board.
Single-reviewer dominance Separated review functions and constrained
aggregation rules.
Untraceable reasoning Every material finding and decision reason
linked to evidence or procedural basis.
Silent corrections Append-only records with supersession and
lineage.
Inconsistent decisions Versioned rule sets and deterministic replay.

<!-- Controlled source page 5 -->

Governance risk Architectural response
AI overreach AI may assist formatting or analysis but cannot
set binding findings, severities or verdicts.
## 1.3 Scope
RBE v1 covers the complete governance execution path after a reviewable package has been
prepared and before any conclusion is represented as board-approved.
- Registering and validating review packages.
- Creating review sessions against fixed methodology and rule-set versions.
- Assigning structurally separate board functions.
- Collecting independent, schema-valid reviewer reports.
- Recording conflicts of interest and eligibility decisions.
- Normalizing and tracking findings without erasing original reviewer language.
- Running challenge and contradiction checks.
- Computing a deterministic board outcome.
- Publishing machine-readable and human-readable decision artifacts.
- Retaining a complete immutable audit trail and replay bundle.
## 1.4 Explicit Non-Goals
- Finding market pain or conducting the Golden Study.
- Generating solution ideas or ranking product concepts.
- Deciding whether Project Exchange should build a component.
- Replacing accountable human review with autonomous AI.
- Optimizing for approval rates, speed-to-build or commercial enthusiasm.
- Re-running the underlying research as though the board were the research team.
- Allowing a sponsor, researcher, engineer or client to override the board outcome without a new
governed review.
**RBE-NON-001** A conforming implementation SHALL NOT expose an “approve anyway” control or
equivalent bypass.
**RBE-NON-002** A disputed outcome SHALL be addressed through correction, appeal, new evidence or re-
review, never through mutation of the historical decision.
## 1.5 Intended Audiences
Audience Use of this architecture
Codex / implementation agent Build services, schemas, rules, tests and
artifacts exactly as constrained.
Principal engineer Assess implementation completeness and
boundary correctness.
Methodology owner Confirm software faithfully executes RBM-001.
Reviewers Understand role separation, permitted inputs

<!-- Controlled source page 6 -->

Audience Use of this architecture
and report obligations.
Auditors Reconstruct decisions and confirm rule-set
conformance.
Project Exchange leadership Understand what the board can and cannot
legitimately certify.
## 1.6 Board Outcomes
The board must be equally able to produce any authorized outcome. No result is treated as
institutional success or failure.
Outcome Meaning
PASS The submitted conclusion is justified under the
applicable methodology and no blocking
findings remain.
PASS WITH FINDINGS The conclusion is justified, but material non-
blocking findings or conditions remain.
FAIL The conclusion is not justified or a blocking
defect exists.
INSUFFICIENT EVIDENCE The board cannot reach a defensible
substantive conclusion from the submitted
evidence.
DEFER FOR FURTHER RESEARCH A defined additional research action is
required before re-review.
PROCEDURALLY INCOMPLETE The review cannot be finalized because
required process, role or package conditions
are unmet.
**RBE-OUT-001** Outcome labels and their decision conditions SHALL be defined by a versioned
methodology rule set and SHALL NOT be invented by application code.
**RBE-OUT-002** The user interface SHALL present all outcomes neutrally and SHALL NOT visually
celebrate PASS or stigmatize FAIL.
## 1.7 Conformance and Authority
**RBE-CON-001** An implementation conforms only when all mandatory requirements, schema
validations, deterministic replay tests and audit-integrity tests pass.
**RBE-CON-002** Any exception SHALL identify the affected requirement, risk, approving authority, expiry
date and remediation plan.
**RBE-CON-003** A non-conforming engine SHALL NOT label its output “Review Board Decision”.

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

# 3. System Context, Trust Boundaries and C4 Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 13 -->

## 3.1 System Context
RBE sits downstream of a reviewable artifact and upstream of any claim that the artifact or
conclusion has passed formal governance. It can review outputs from GS-P001, future Golden
Studies, Solution Validation, specifications, methodologies or other controlled packages, provided a
compatible review profile exists.
Logical context flow
Reviewable Package Producer
|
v
Package Registration + Validation
|
v
Independent Board Functions
| Methodology | Evidence | Reasoning | Challenge | Commercial | Governance |
|
v
Finding Normalization + Conflict Handling
|
v
Deterministic Decision Assembly
|
v
Decision Record + Review Report + Audit/Replay Bundle
|
v
Approved downstream consumer or rework/research loop
**RBE-CTX-001** RBE SHALL treat every upstream artifact as untrusted until package validation completes.
**RBE-CTX-002** RBE SHALL publish an outcome only after all mandatory board functions and decision
prerequisites are satisfied.
**RBE-CTX-003** Downstream systems SHALL consume signed or checksummed decision artifacts, not infer
approval from session status or user-interface text.
## 3.2 External Actors and Systems
Actor or system Relationship to RBE
Package producer Submits a complete, versioned review package
and responds to formal requests for correction
or additional evidence.
Board reviewer Accepts one eligible assignment, declares
conflicts and submits a structured independent
report.
Governance officer Manages procedural readiness and finalization
authority without changing reviewer findings.
Methodology registry Provides immutable methodology and rule-set

<!-- Controlled source page 14 -->

Actor or system Relationship to RBE
versions.
Evidence repository Provides registered evidence objects or
immutable references.
Identity provider / actor registry Supplies actor identity and eligibility data;
optional adapter in v1.
Artifact consumer Reads board decisions, reports and replay
bundles.
Auditor Reconstructs state transitions, inputs, findings
and decision calculation.
Codex / engineering automation Builds and tests the engine but has no live
governance authority.
## 3.3 C4 Level 1 — System Boundary
The RBE system boundary contains all logic and records required to validate a package, orchestrate
independent reviews, normalize findings, calculate an outcome, generate artifacts and preserve
auditability. Research collection, product prioritization and component engineering remain outside
the boundary.
Inside RBE boundary Outside RBE boundary
Review session lifecycle Golden Study evidence discovery
Role assignment and conflict checks Solution ideation and product design
Reviewer report intake Client relationship management
Finding and challenge management Commercial approval to fund a build
Deterministic decision assembly Source scraping and market research
Decision artifact publication General project management
Audit and replay export Production deployment of approved
components
## 3.4 C4 Level 2 — Containers
Container Responsibility
Operator / Reviewer Web UI Neutral presentation of assignments, package
materials, reports, findings and decision
artifacts.
REST API Authenticated command and query interface;
validation, idempotency and authorization

<!-- Controlled source page 15 -->

Container Responsibility
boundary.
Application Service Layer Use-case orchestration for registration,
assignment, submission, challenge, readiness
and finalization.
Domain Core Pure entities, invariants, state machine,
independence rules and deterministic decision
functions.
Persistence Adapter Transactional storage, migrations, append-only
versioning and query projection.
Artifact Generator Canonical JSON, Markdown and export bundle
creation.
Audit Ledger Hash-linked event records and integrity
verification.
CLI / Replay Tool Headless execution, conformance tests and
deterministic replay.
Configuration Registry Versioned board profiles, role constraints,
schemas and rule sets.
**RBE-ARC-001** The domain core SHALL have no dependency on web frameworks, database drivers, UI
libraries, network clients or AI services.
**RBE-ARC-002** All state-changing operations SHALL pass through application services and a single
validated domain transition path.
**RBE-ARC-003** Artifact generation SHALL operate from a frozen decision snapshot, not from mutable
live queries.
**RBE-ARC-004** The CLI replay path and API finalization path SHALL invoke the same decision functions.
## 3.5 C4 Level 3 — Core Components
Component Key responsibilities
Package Registry Manifest validation, file hashes, schema
compatibility, completeness and version
locking.
Conflict and Eligibility Service Authorship/sponsorship checks, role
incompatibilities, declarations and recusal
state.
Assignment Orchestrator Seat creation, staged disclosure, phase
readiness and replacement handling.
Report Validator Schema validation, actor authority, evidence

<!-- Controlled source page 16 -->

Component Key responsibilities
reference validity and report immutability.
Finding Registry Finding creation, severity lineage,
deduplication suggestions, supersession and
resolution state.
Challenge Manager Contrary evidence, alternative explanations,
assumptions and decision-change conditions.
Readiness Evaluator Deterministic list of unmet prerequisites and
blockers.
Decision Engine Pure normalization and rule-set evaluation
producing outcome and reasons.
Artifact Builder Canonical decision JSON, review report and
audit/replay bundle.
Audit Service Append-only events, actor attribution, hashes
and integrity verification.
## 3.6 Trust Boundaries
Boundary Required control
External package  RBE→ Content hash, schema validation, malware-safe
handling, manifest completeness and version
lock.
Reviewer  API→ Authenticated actor, assignment authorization,
conflict-cleared state, request validation and
idempotency.
Application  Domain core→ Typed commands only; no direct state
mutation.
Domain core  Persistence→ Transactional append/version operations
preserving invariants.
Decision snapshot  Artifact builder→ Frozen canonical snapshot and rule-set
checksum.
RBE  Downstream consumer→ Signed or checksummed artifact, stable
identifiers and explicit outcome status.
AI service  Reviewer workflow→ Untrusted suggestion channel; no direct
mutation or decision authority.

<!-- Controlled source page 17 -->

## 3.7 Primary Data Flows
### 3.7.1 Package registration
4. Submit manifest and referenced files.
5. Validate required types and checksums.
6. Resolve methodology, profile and schema versions.
7. Create immutable package version and review session.
### 3.7.2 Independent review
8. Evaluate eligibility and conflict declaration.
9. Release only stage-appropriate information.
10. Accept structured report and evidence links.
11. Lock report version and create normalized findings.
### 3.7.3 Challenge
12. Collect contradictions, alternatives and assumptions.
13. Link each challenge to evidence or reasoning claim.
14. Require disposition without deleting disagreement.
### 3.7.4 Decision finalization
15. Freeze accepted inputs.
16. Evaluate procedural blockers.
17. Run deterministic rule set.
18. Persist decision, reasons and snapshot atomically.
19. Generate artifacts and integrity hashes.
### 3.7.5 Re-review
20. Register corrected or expanded package.
21. Create a new linked session.
22. Preserve prior reports and outcome.
23. Run the full applicable review profile again.
## 3.8 Reference Technology Profile
Concern Reference choice
Language Python 3.12+ unless repository constraints
require an approved alternative.
API FastAPI or equivalent OpenAPI-first
framework.
Persistence SQLite for v1 with foreign keys, WAL mode
where appropriate and migration-managed
schema.
Schemas JSON Schema draft 2020-12.
Artifacts Canonical UTF-8 JSON and Markdown; optional
PDF generated from the canonical report.

<!-- Controlled source page 18 -->

Concern Reference choice
Testing Unit, property, integration, state-transition,
golden artifact, replay and corruption tests.
Packaging Single-process local deployment initially;
network-independent decision capability.
Time UTC RFC 3339 timestamps; time never
influences verdict except where a rule
explicitly governs deadlines.
Identifiers UUIDv7 or approved stable alternative;
identifiers never affect decision output.
Integrity SHA-256 or stronger approved hash over
package files, rule sets, snapshots and artifacts.
**RBE-TEC-001** The engine SHALL operate without external network access after all required package
content, schemas and rule sets are registered locally.
**RBE-TEC-002** External identity, notification, storage or AI services SHALL be optional adapters and
SHALL NOT be necessary for decision calculation or replay.
**RBE-TEC-003** Database-generated ordering SHALL NOT be used where canonical artifact ordering is
required; explicit deterministic sort keys SHALL be defined.
## 3.9 Recommended Repository Structure
rbe/
pyproject.toml
src/rbe/
domain/
entities.py
value_objects.py
invariants.py
state_machine.py
decision_engine.py
independence.py
application/
commands/
queries/
services/
dto/
adapters/
persistence/
identity/
notifications/
ai_assistance/
api/
routes/
dependencies/
errors.py
artifacts/

<!-- Controlled source page 19 -->

canonical_json.py
markdown_report.py
replay_bundle.py
schemas/
migrations/
cli/
tests/
unit/
integration/
conformance/
golden/
replay/
docs/
architecture/
adr/
api/
**RBE-REP-001** Dependency direction SHALL point inward: presentation and adapters may depend on
application and domain code; domain code SHALL NOT depend on outer layers.
**RBE-REP-002** Decision rules, board profiles and schemas SHALL be versioned resources with
checksums, not hard-coded conditionals scattered through handlers.
## 3.10 Architecture Review Findings for Sections 1–3
Review lens Result
Methodology alignment PASS — engine authority is subordinate to
RBM-001 and gaps fail closed.
Bias resistance PASS WITH ACTION — structural separation
and information barriers specified; final
incompatibility matrix must be locked in
RBM-001.
Codex implementability PASS — boundaries, containers, components
and dependency rules are explicit.
Determinism PASS — pure decision core and frozen
snapshot defined.
Auditability PASS — append-only, lineage and replay
requirements established.
Scope discipline PASS — research, solution generation and
build approval remain outside RBE.
Terminology ACTION — outcome vocabulary must be
synchronized with final RBM-001 before
release freeze.

<!-- Controlled source page 20 -->

Section freeze decision
Sections 1–3 are architecture-ready. They may be used by Codex to establish repository
boundaries, core principles, board-function separation and system context. Codex SHALL
NOT yet finalize database schema, API resources or decision tables until Sections 4–7 and
the RBM-001 terminology lock are complete.

<!-- Controlled source page 21 -->

Integration rule
These chapters are drafted as a controlled section release. After section review and
terminology lock, they SHALL be merged into the single authoritative RBE-001 Reference
Architecture without changing requirement identifiers or semantic meaning.

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

# 9. Roles, Permissions and Separation of Duties

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 63 -->

## 9.1 Security and Governance Objective
Access control exists to protect independence, evidence integrity and procedural legitimacy. It is not
merely a confidentiality feature. The architecture combines role-based permissions, case-scoped
attributes, information barriers and explicit separation-of-duties rules.
**RBE-IAM-001** Every protected action SHALL be authorized against identity, role, case scope, lifecycle
state, conflict status and artefact classification.
**RBE-IAM-002** No role SHALL receive authority solely because it is organizationally senior.
**RBE-IAM-003** Permissions SHALL default to deny.
## 9.2 Principal Types
Principal type Examples Authentication expectation
Human reviewer Methodology, evidence,
reasoning, challenge,
commercial or governance
reviewer.
Strong authenticated identity;
MFA required.
Process coordinator Intake officer, board
coordinator, appeal registrar.
Strong authenticated identity;
scoped operational role.
Administrative operator Identity, infrastructure or
retention administrator.
Privileged account; just-in-
time elevation and session
logging.
Submitter / sponsor Research owner or authorized
case sponsor.
Authenticated external or
internal identity with case
scope.
Observer / auditor Read-only inspection under
explicit grant.
Authenticated, purpose-bound
and time-limited.
Service principal Workflow engine, hashing
service, report renderer,
notification service.
Workload identity, key
rotation and least privilege.
AI assistant Non-authoritative support
service.
Dedicated service identity
with restricted data and no
decision authority.
## 9.3 Role Catalogue
Role Permitted scope Key prohibition
Submitter Create drafts, submit
packages, answer bounded
clarifications, initiate eligible
Cannot assign reviewers or
edit locked evidence.

<!-- Controlled source page 64 -->

Role Permitted scope Key prohibition
appeal.
Intake Officer Validate submission contract
and admissibility.
Cannot perform substantive
review on same case.
Board Coordinator Manage assignments,
schedules and completeness.
Cannot decide merits or force
transition.
Methodology Reviewer Assess methodology
compliance.
No evidence or commercial
substitution.
Evidence Reviewer Assess source sufficiency,
independence and
traceability.
Cannot rewrite findings to
reach preferred result.
Reasoning Reviewer Assess inferential validity and
assumptions.
Cannot introduce unregistered
evidence.
Challenge Reviewer Test contradictions and
alternative explanations.
Cannot reject without
reasoned basis.
Commercial Reviewer Assess materiality only after
upstream validity.
Cannot rescue invalid
methodology or evidence.
Governance Reviewer Validate quorum, conflicts,
process and reproducibility.
Cannot change substantive
findings.
Decision Assembler Apply deterministic rule set
and compile decision
candidate.
No discretionary verdict
selection.
Publication Authority Release validated outputs. Cannot change decision
content.
Appeal Registrar Validate appeal eligibility and
grounds.
Cannot adjudicate appeal
merits.
Appeal Reviewer Review eligible appeal
grounds.
Must satisfy independence
from challenged decision.
Auditor Inspect retained records and
replay decisions.
Read-only; no workflow
commands.
System Administrator Operate identity,
infrastructure and
configuration.
No substantive artefact
mutation.
Retention Administrator Execute archival and legal
retention actions.
No content editing.
AI Assistant Summarize, classify or
retrieve within approved
No scoring, signing, transition
or final decision authority.

<!-- Controlled source page 65 -->

Role Permitted scope Key prohibition
bounds.
## 9.4 Permission Model
Permission family Representative actions
Case create, view metadata, submit, withdraw,
initiate appeal
Evidence upload draft, lock, view, verify digest, request
amendment
Assignment propose, accept, decline, remove, adjudicate
conflict
Assessment create, edit own draft, seal, view permitted
peer output
Challenge issue, answer, disposition, escalate
Decision assemble, validate, sign, publish, replay
Governance declare conflict, pause, block, void, record
incident
Audit query, export, verify chain, run replay
Administration manage roles, keys, policies, retention
schedules
**RBE-IAM-020** Permissions SHALL be action-specific; broad “edit case” or “admin all” grants SHALL NOT
authorize substantive mutations.
**RBE-IAM-021** Every permission grant SHALL be case-scoped unless the action is explicitly platform-
scoped.
## 9.5 Separation-of-Duties Rules
Control pair Mandatory rule
Submission vs intake Submitter cannot validate own submission.
Intake vs substantive review Intake officer cannot fill a required review
function on same case.
Evidence custody vs evidence assessment Person who materially prepared or curated
evidence cannot be sole evidence reviewer.
Independent review vs governance validation A reviewer cannot be the only governance
validator of their own work.
Decision assembly vs publication Assembler cannot be sole publication

<!-- Controlled source page 66 -->

Control pair Mandatory rule
authority.
Administration vs substantive decision System administrator cannot create or alter
findings or verdicts.
Original panel vs appeal panel Appeal panel must exclude reviewers whose
work is directly challenged, except as non-
voting respondents.
Methodology ownership vs live adjudication Methodology owner cannot amend rules for
active case and then adjudicate under the
amendment.
AI assistance vs human attestation AI-generated material requires accountable
human review and cannot self-attest.
**RBE-IAM-030** The authorization engine SHALL evaluate incompatible-role combinations before
assignment and again before every sensitive action.
**RBE-IAM-031** Separation-of-duties violations SHALL be blocking governance incidents.
## 9.6 Four-Eyes and Multi-Review Controls
Action Minimum control
Evidence lock One initiator plus one independent verifier, or
deterministic system verifier with human
approval.
Material assignment override Coordinator plus governance approval.
Decision finalization Decision assembler plus governance validator.
Publication Validated decision plus independent
publication authority.
Appeal eligibility exception Appeal registrar plus governance authority.
Void declaration Governance authority plus recorded second
approval.
Privileged access to sealed assessment Break-glass initiator plus independent
approver and auditor notification.
## 9.7 Information Barriers
Information visibility is governed by function and state. Isolation protects independence; disclosure
occurs only when the lifecycle requires it.
Stage Visible to reviewer Hidden until authorized
Before assignment acceptance Case metadata needed for Substantive evidence and peer

<!-- Controlled source page 67 -->

Stage Visible to reviewer Hidden until authorized
conflict declaration. identities where unnecessary.
Independent review Role-relevant evidence and
methodology.
Peer conclusions, target
outcome, executive
preference.
Challenge Sealed assessments and
scoped supporting material.
Unrelated confidential data.
Consolidation Normalized findings and
signed assessments.
Administrative notes without
decision relevance.
Appeal Original decision, appeal
grounds and required record.
New material outside allowed
appeal scope.
**RBE-IAM-050** The system SHALL log every disclosure of sealed or restricted artefacts.
**RBE-IAM-051** Outcome labels and commercial desirability signals SHALL be withheld where they are
not required for the reviewer’s function.
## 9.8 Conflict-of-Interest Controls
- Financial interest in the outcome
- Operational ownership of the submitted work
- Prior authorship of material under review
- Reporting-line pressure or executive sponsorship
- Personal or professional relationship creating reasonable doubt
- Prior public commitment to a specific outcome
- Recent paid work for a materially affected party
- Access to non-record evidence that cannot be disclosed
**RBE-IAM-060** Conflict declarations SHALL occur before substantive access and be renewed when
material circumstances change.
**RBE-IAM-061** The conflicted individual SHALL NOT adjudicate their own conflict.
**RBE-IAM-062** Conflict disposition SHALL be immutable, reasoned and visible to governance reviewers
and auditors.
## 9.9 Privileged Administration and Break-Glass
Control Requirement
Just-in-time elevation Privileged role granted for a bounded duration
and purpose.
Named ticket or incident Every elevation references a governance or
operations record.
Session recording Commands and affected resources are logged.
No content authority Elevation does not confer substantive review

<!-- Controlled source page 68 -->

Control Requirement
permissions.
Break-glass approval Independent approval unless immediate
preservation requires emergency use.
Post-event review Mandatory governance and security review.
Credential hygiene Separate admin identities; no shared accounts.
**RBE-IAM-070** Break-glass access SHALL never permit alteration of sealed or decided substantive
artefacts.
## 9.10 AI Permission Boundary
AI may AI may not
Retrieve approved artefacts within caller
scope.
Choose or influence final decision outcome.
Draft summaries with source references. Sign assessments or decisions.
Check structural completeness. Create evidence or conceal uncertainty.
Suggest potential contradictions for human
review.
Transition cases or adjudicate conflicts.
Generate report prose from locked structured
data.
Override rule engine or governance controls.
Assist with deterministic classification where
policy allows.
Receive broader data access than the
accountable user.
**RBE-IAM-080** Every AI-produced substantive draft SHALL be labeled as machine-assisted and attributed
to the accountable human approver.
**RBE-IAM-081** AI service identities SHALL have no permission to finalize, sign, publish, appeal, void or
supersede a decision.
## 9.11 Access Review and Revocation
- Periodic role recertification
- Per-case assignment review at major lifecycle gates
- Immediate revocation on conflict, departure or credential compromise
- Automatic expiry of temporary access
- Verification that revoked users cannot retrieve cached protected content
- Audit comparison between granted permissions and actions taken
**RBE-IAM-090** Revocation SHALL affect future access immediately while preserving attributable
historical records.

<!-- Controlled source page 69 -->

## 9.12 Codex Implementation Contract
- Separate identity, authorization and business-rule evaluation.
- Implement policy-as-code with versioned rules.
- Authorize server-side on every action; never trust UI state.
- Include lifecycle state and conflict status in authorization decisions.
- Avoid superuser paths in application logic.
- Create test fixtures for every incompatible-role pair.
- Test confused-deputy and privilege-escalation scenarios.
- Use workload identities for services and rotate credentials.
- Make AI permissions an explicit deny-heavy policy set.

# 10. Audit, Traceability and Provenance

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 70 -->

## 10.1 Objective
The audit architecture must make every material decision reconstructable without relying on
memory, trust in a single operator or mutable application state. Traceability connects the final
decision to the exact evidence, methodology, rules, reviewers, findings, challenges and signatures
that produced it.
**RBE-AUD-001** Every material action SHALL produce an immutable, attributable audit event.
**RBE-AUD-002** The system SHALL support independent reconstruction of any published decision from
retained artefacts and versioned rules.
**RBE-AUD-003** Audit data SHALL be designed as evidence, not as diagnostic logging.
## 10.2 Audit Event Model
Field Description
event_id Globally unique immutable identifier.
event_type Versioned enumerated event name.
occurred_at Trusted UTC timestamp.
recorded_at Persistence timestamp, separately retained.
actor_id Human or service principal.
actor_role Effective role at action time.
case_id / session_id Scope of action.
state_before / state_after Lifecycle context where applicable.
object_type / object_id Affected domain object.
action Created, viewed, sealed, transitioned, signed,
exported, etc.
reason_code Structured reason or policy basis.
policy_version Authorization and governance policy version.
payload_digest Hash of canonical event payload.
previous_event_digest Link to prior event in chain or partition.
correlation_id Groups related workflow events.
source_context Client, service, region and request metadata.
signature / attestation Optional cryptographic or organizational
attestation.

<!-- Controlled source page 71 -->

## 10.3 Event Taxonomy
Family Examples
Identity and access login, MFA challenge, role grant, access denial,
break-glass use
Case lifecycle submission sealed, evidence locked, state
transitioned, case voided
Evidence artifact added, hash verified, disclosure,
amendment proposed
Assignment assigned, conflict declared, assignment
accepted, reviewer removed
Assessment draft created, finding added, assessment
sealed, signature verified
Challenge challenge issued, answer submitted,
disposition recorded
Decision rules executed, candidate generated, validation
passed, decision signed
Publication report rendered, package verified, recipient
release, correction notice
Appeal appeal filed, eligibility determined, panel
constituted, outcome issued
Administration policy changed, key rotated, retention action,
restore test
Integrity digest mismatch, replay failure, unauthorized
mutation attempt
**RBE-AUD-020** Event types SHALL be versioned and backward-readable.
**RBE-AUD-021** Free-text operational logs SHALL NOT substitute for required audit events.
## 10.4 Evidence Provenance and Chain of Custody
Provenance element Required record
Origin Source, issuer, retrieval method and date.
Authenticity Signature, certificate, authoritative URL or
verification method where available.
Independence Relationship between source and affected
parties.
Transformation Every extraction, normalization, redaction or
format conversion.

<!-- Controlled source page 72 -->

Provenance element Required record
Custody Who or what handled the artefact and when.
Integrity Original and transformed content digests.
Scope use Claims, findings and assessments that cite the
artefact.
Exclusion Why evidence was rejected, superseded or
deemed out of scope.
**RBE-AUD-030** The original artefact SHALL be retained whenever legally and technically permissible.
**RBE-AUD-031** A transformed artefact SHALL retain a verifiable link to its source artefact and
transformation procedure.
## 10.5 Decision Provenance Graph
Decision provenance is represented as a directed graph, not a single narrative paragraph. The graph
makes each decision element traceable through intermediate findings and assessments to
underlying evidence and governing rules.
Node type Must link to
Decision Decision rule execution, governance
validation, signatures and report package.
Decision basis Accepted findings, blocking findings,
uncertainty and rule clauses.
Finding Assessment, evidence references, methodology
clauses and challenge dispositions.
Assessment Reviewer identity, assignment, scope, artefact
set and attestation.
Challenge disposition Challenge, response, evidence and reviewer
ruling.
Evidence item Source provenance, content digest and
evidence package.
Methodology clause Pinned methodology version and exact clause
identifier.
Rule execution Ruleset version, inputs, outputs and
deterministic trace.
**RBE-AUD-040** No published decision basis SHALL exist without at least one trace path to a governing
rule and supporting assessment or evidence record.

<!-- Controlled source page 73 -->

## 10.6 Cryptographic Integrity Strategy
Control Architecture requirement
Content hashing Use approved collision-resistant digest over
canonical bytes.
Canonicalization Structured objects serialized deterministically
before hashing.
Package digest Merkle-style or manifest digest covering all
decision artefacts.
Event chaining Each audit event links to prior digest within an
ordered partition.
Digital signatures Signed decisions and sealed assessments bind
identity, content digest and timestamp.
Key management Central managed keys, rotation, revocation and
audit.
Timestamping Trusted server time; external timestamp
authority considered for high-assurance
releases.
Verification tooling Independent command or service validates
package without production database
mutation.
**RBE-AUD-050** Cryptographic controls SHALL detect alteration; they SHALL NOT be represented as
proving truth of the underlying content.
**RBE-AUD-051** Algorithm identifiers and key versions SHALL be stored with each signature or digest
record.
## 10.7 Immutability and Corrections
Immutability does not mean errors can never be addressed. It means corrections are additive,
explicit and lineage-preserving.
Scenario Required treatment
Typographical report defect Issue corrected report version linked to same
decision; preserve prior output.
Material decision defect Use appeal, superseding decision or void
process as applicable.
Incorrect metadata Append correction event and successor
metadata record.
Compromised signature key Revoke key, record incident, re-attest only
through governed process.

<!-- Controlled source page 74 -->

Scenario Required treatment
Evidence corruption Block use, restore verified immutable copy and
record recovery.
Policy bug Version policy, replay affected cases and
initiate governed remediation.
**RBE-AUD-060** No correction process SHALL erase the existence of the original record.
## 10.8 Reproducibility and Decision Replay
Replay input Requirement
Evidence package Exact locked manifest and verified digests.
Submission assertions Exact version reviewed.
Methodology Pinned identifier, version and digest.
Ruleset Pinned executable or declarative version and
digest.
Assessments Sealed structured assessments and signatures.
Challenge record Complete challenge and disposition set.
Configuration Relevant policy and taxonomy versions.
Replay engine Compatible deterministic implementation.
Expected output Decision class, finding set references and
decision digest.
**RBE-AUD-070** Decision replay SHALL be executable without editing historical records.
**RBE-AUD-071** A replay mismatch SHALL create a blocking integrity incident.
**RBE-AUD-072** The platform SHALL distinguish deterministic decision replay from human re-review.
## 10.9 Time and Ordering
- Use UTC for authoritative timestamps.
- Retain local display timezone separately where useful.
- Record occurred_at and recorded_at to detect delayed ingestion.
- Use monotonic sequence numbers within event partitions.
- Synchronize infrastructure clocks and alert on drift.
- Do not infer legal or workflow ordering solely from client-supplied time.
## 10.10 Retention, Archive and Legal Hold
Record class Minimum architectural treatment
Published decision package Long-term immutable retention.

<!-- Controlled source page 75 -->

Record class Minimum architectural treatment
Evidence package Retain according to methodology, law and
source rights.
Audit events At least as long as related decision artefacts.
Identity and access events Security retention aligned to investigation
needs.
Draft content Retain only where governance or recovery
requires.
Secrets and credentials Never embed in retained case artefacts.
Legal hold Suspends deletion without altering original
retention metadata.
Archive package Self-describing manifest, checksums, schemas
and verification instructions.
**RBE-AUD-090** Retention deletion SHALL be a governed, logged and independently authorized action.
**RBE-AUD-091** An archive SHALL remain verifiable without dependence on the live application UI.
## 10.11 Audit Query and Export
- Chronological case timeline
- All access to a named artefact
- Decision-to-evidence trace report
- Reviewer actions and role state at action time
- Policy and methodology versions used
- All failed or denied transition attempts
- All privileged and break-glass events
- Replay result and integrity status
- Appeal lineage and supersession graph
**RBE-AUD-100** Audit export SHALL preserve identifiers, timestamps, digests and schema version.
**RBE-AUD-101** Exports SHALL be access-controlled and themselves audited.
## 10.12 Privacy and Data Minimization
Auditability does not justify indiscriminate retention of personal or sensitive data. Events should
identify actors and actions while avoiding unnecessary payload duplication.
**RBE-AUD-110** Audit records SHALL reference protected content by identifier and digest rather than
duplicating full sensitive payloads unless required.
**RBE-AUD-111** Redaction or pseudonymization SHALL preserve evidentiary integrity and lineage.
## 10.13 Codex Implementation Contract
- Model audit events as append-only domain records.
- Use canonical serialization before hashing.

<!-- Controlled source page 76 -->

- Create verification libraries independent of UI.
- Separate operational telemetry from governance audit records.
- Test event-chain tampering and replay mismatch detection.
- Make all exports schema-versioned and machine-readable.
- Provide decision provenance graph traversal.
- Preserve old schemas and migration readers.
- Never expose secret values in audit payloads.

# 11. Review Reports and Decision Outputs

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 77 -->

## 11.1 Purpose
Reports are controlled projections of the governed record. They explain what the Board concluded,
why it concluded it, what evidence and rules were relied upon, what uncertainty remains and what
follows. They are not marketing collateral and must not persuade the reader toward an
organizational preference.
**RBE-OUT-010** Every published output SHALL be generated from the same sealed decision record and
share one decision digest.
**RBE-OUT-011** Reports SHALL distinguish fact, finding, inference, limitation, recommendation and
decision.
**RBE-OUT-003** PASS and FAIL outputs SHALL use neutral presentation and equivalent evidentiary rigor.
## 11.2 Output Catalogue
Output Audience Purpose
Decision Notice Submitter, governance
stakeholders
Authoritative outcome and
immediate implications.
Full Review Report Reviewers, architects, auditors Complete rationale, findings,
evidence and governance
record.
Executive Summary Authorized leadership Condensed explanation
without suppressing
uncertainty.
Methodology Compliance
Report
Methodology owners and
auditors
Clause-by-clause compliance
and deviations.
Evidence Assessment Report Research and assurance teams Evidence sufficiency,
independence and
traceability.
Reasoning Assessment Report Architects and reviewers Inference chain, assumptions
and logical defects.
Challenge Register Board and auditors Challenges, responses and
dispositions.
Commercial Relevance Report Commercial governance Materiality assessment
conditional on upstream
validity.
Governance Validation Report Board and auditors Quorum, conflicts, signatures,
integrity and replay status.
Findings Register All authorized consumers Structured findings with
severity, status and trace links.

<!-- Controlled source page 78 -->

Output Audience Purpose
Appeal Decision Report Appeal parties and auditors Grounds, scope, analysis and
appeal outcome.
Machine-readable Decision
Package
Systems and verification tools Canonical structured
representation for automation
and replay.
Audit Export Auditors and compliance Event timeline and
provenance evidence.
## 11.3 Decision Notice Specification
- Document identifier and version
- Case and review-session identifiers
- Decision class and effective date
- Exact conclusion reviewed
- Plain-language decision rationale
- Material findings and unresolved limitations
- Applicable methodology and ruleset versions
- Appeal eligibility and deadline
- Decision digest and verification identifier
- Authorized signatures and publication status
**RBE-OUT-020** The Decision Notice SHALL NOT omit a material limitation merely to make the outcome
easier to communicate.
## 11.4 Full Review Report Structure
Section Required content
1. Control page Identifiers, versions, classification, status and
signatures.
2. Executive summary Outcome, central rationale, key findings and
uncertainty.
3. Scope and question Exact proposition reviewed and exclusions.
4. Constitutional basis Review Board principles and burden of
justification.
5. Methodology baseline Pinned methodology, rules and deviations.
6. Evidence package Manifest summary, source quality and
limitations.
7. Functional assessments Methodology, evidence, reasoning, challenge,
commercial and governance conclusions.
8. Findings register Structured decisive and non-decisive findings.

<!-- Controlled source page 79 -->

Section Required content
9. Challenge analysis Contradictions, alternatives and dispositions.
10. Decision derivation Rule execution trace and outcome mapping.
11. Limitations and uncertainty Known unknowns and confidence boundaries.
12. Recommendations Permitted actions clearly separated from
decision.
13. Appeal and re-review Available pathways and conditions.
14. Provenance and verification Digests, signatures, audit references and replay
result.
Appendices Evidence index, glossary, rule trace and
detailed tables.
## 11.5 Findings Register
Field Requirement
finding_id Stable unique identifier.
function Originating review function.
type Compliance, evidence, reasoning, challenge,
commercial or governance.
severity Defined taxonomy; never inferred from prose.
statement Specific, falsifiable and neutral wording.
basis Evidence, methodology or rule references.
impact How the finding affects justification or process.
status Open, resolved, accepted limitation,
superseded or non-decisive.
decision_effect Blocking, contributory, informational or none.
owner Accountable function, not a preferred outcome
owner.
provenance Assessment, reviewer and signature
references.
**RBE-OUT-030** A finding SHALL NOT be included in a decision basis unless its provenance and supporting
references validate.

<!-- Controlled source page 80 -->

## 11.6 Decision Taxonomy Presentation
Decision Required plain-language
meaning Required caution
PASS The submitted conclusion is
justified under the locked
evidence, reasoning and
methodology.
Does not guarantee
implementation success or
eliminate all uncertainty.
PASS WITH FINDINGS The conclusion is justified, but
material findings require
explicit treatment or
monitoring.
Findings are not decorative;
obligations must be stated.
FAIL The conclusion is not justified
under the reviewed record.
Does not mean the underlying
opportunity is impossible; it
means this conclusion failed
justification.
INSUFFICIENT EVIDENCE The record cannot support a
defensible determination.
Must not be reframed as likely
PASS or likely FAIL.
DEFER A defined dependency
prevents a current
determination.
Must state the dependency
and conditions for
resumption.
**RBE-OUT-040** Outcome wording SHALL describe justification status, not organizational enthusiasm or
disappointment.
## 11.7 Recommendations
Recommendations are downstream guidance, not hidden decision criteria. They must be linked to
findings and remain clearly distinguishable from the verdict.
Recommendation type Allowed use
Corrective Resolve a defined methodological, evidentiary
or governance defect.
Research Collect specified evidence needed for a future
determination.
Control Mitigate a governance or operational risk.
Monitoring Track a verified uncertainty or condition.
No-build / stop Permitted where the decision and governance
mandate justify halting further work.
Proceed to next gate Permitted only when PASS conditions and
external governance allow it.

<!-- Controlled source page 81 -->

**RBE-OUT-050** A recommendation SHALL cite the finding or decision rule that justifies it.
**RBE-OUT-051** Commercial attractiveness SHALL NOT be used to soften or contradict the recorded
decision.
## 11.8 Executive Summary Rules
- State the exact decision in the first section.
- Include the central reason, not only the outcome.
- Name material limitations and blocking findings.
- Avoid promotional adjectives and persuasive framing.
- Do not collapse INSUFFICIENT EVIDENCE into “promising”.
- Retain identifiers needed to find the full report.
- Use equivalent prominence for adverse and favourable findings.
## 11.9 Machine-Readable Decision Package
Object Minimum fields
package schema_version, package_id, generated_at,
decision_digest
case case_id, session_id, submission_version, state
decision class, rationale_code, effective_at, supersedes
methodology id, version, digest
ruleset id, version, digest, execution_trace
evidence manifest_id, package_digest, item references
assessments assessment ids, function, signer, digest
findings structured findings and decision effects
challenges challenge, response and disposition references
governance quorum, conflict status, validation and replay
result
signatures signer, role, algorithm, key version, timestamp
reports human-readable output ids and digests
lineage prior decisions, appeals, remands and
successors
**RBE-OUT-070** The machine-readable package SHALL be the canonical structured source for all human-
readable reports.
**RBE-OUT-071** Schema evolution SHALL be versioned and backward-readable.

<!-- Controlled source page 82 -->

## 11.10 Report Generation and Rendering
Stage Control
Data selection Only sealed, authorized decision-package
objects.
Template selection Versioned report template.
Generation Deterministic rendering from canonical
structured data.
Validation Required-section, cross-reference and digest
checks.
Accessibility Tagged headings, readable tables, descriptive
links and accessible language.
Signing Bind signer to final file digest.
Publication Release only the validated signed version.
Correction Issue successor report; preserve prior file and
digest.
**RBE-OUT-080** Manual edits after rendering SHALL invalidate the report signature and require
regeneration or governed re-signing.
## 11.11 Publication and Audience Controls
Classification Audience rule
Internal controlled Named organizational roles only.
Board confidential Reviewers, governance and authorized
auditors.
Submitter restricted Submitter and named case stakeholders.
Public summary Approved redacted summary derived from
sealed report.
Regulatory / legal Released under specific authority and logged.
Machine integration Authenticated service consumers with schema
contract.
**RBE-OUT-090** Redaction SHALL not change the substantive meaning of the decision.
**RBE-OUT-091** Every publication event SHALL record recipient class, artefact digest and authorization
basis.
## 11.12 Appeal Outputs
- Original decision and digest

<!-- Controlled source page 83 -->

- Appeal identifier, filer and accepted grounds
- Scope of appeal review
- Appeal panel composition and conflict status
- Evidence and rules considered
- Ground-by-ground analysis
- Outcome: upheld, superseded or remanded
- Any successor decision identifier
- Updated lineage graph
- Signatures and publication status
## 11.13 Quality Gates
Gate Failure effect
Completeness Block publication.
Traceability Block publication.
Decision-package digest match Block publication.
Required signatures Block publication.
Neutral language check Return for correction without changing
decision.
Accessibility validation Return for correction.
Cross-reference validation Return for correction.
Replay verification Block publication.
Classification and audience authorization Block release.
## 11.14 Output Anti-Patterns
- A one-page PASS notice with no reasoning
- A FAIL report that omits contrary evidence
- Marketing language in the executive summary
- Manual spreadsheet as the only findings register
- Different verdict wording across PDF, UI and API
- Hidden caveats placed only in appendices
- Replacing a report file without preserving its prior digest
- An AI-generated narrative with no accountable human approval
- A recommendation that contradicts the decision
- Treating “insufficient evidence” as an informal positive signal
## 11.15 Codex Implementation Contract
- Generate all outputs from one canonical decision package.
- Version schemas and templates independently.
- Calculate and store digests for every published artefact.
- Create deterministic report-generation tests.

<!-- Controlled source page 84 -->

- Validate required sections and trace references automatically.
- Keep report prose neutral and template-controlled.
- Expose verification metadata to authorized consumers.
- Implement correction as successor artefact creation, never overwrite.
- Ensure AI-assisted text is reviewable, attributable and non-authoritative.
- Provide golden-file tests for PASS, PASS WITH FINDINGS, FAIL, INSUFFICIENT EVIDENCE and
DEFER outputs.
## 11.16 Sections 8–11 Architecture Freeze Checklist
- State taxonomy and transition matrix reconciled with Chapter 5 lifecycle.
- Every sensitive action mapped to a role and separation-of-duties rule.
- Audit events cover all state transitions, disclosures, signatures and publications.
- Decision provenance graph links outputs to rules, assessments and evidence.
- Replay requirements are implementable from retained data.
- Human and machine-readable reports share one canonical decision package.
- Appeal and re-review preserve prior decisions and lineage.
- AI boundaries prohibit autonomous governance or decision authority.
- All constitutional principles are reflected in system controls, not only prose.
- Requirement identifiers remain stable for later merge into the master document.
Architecture completion statement
Sections 8–11 complete the operational control layer of RBE-001. Codex may use these
chapters to implement state enforcement, authorization, audit provenance and report
generation only after the Review Board Methodology and preceding architecture chapters
are frozen. Any unresolved ambiguity SHALL be raised as an architecture question rather
than silently resolved in code.

# 12. System and Service Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 85 -->

## 12.1 Purpose
This chapter converts the governance, lifecycle, state, authorization and provenance requirements
established in Chapters 4–11 into an implementable system structure. The architecture must make
impartial review the path of least resistance and prohibited shortcuts technically difficult or
impossible.
**RBE-SYS-001** The system architecture SHALL enforce governance rules in domain services rather than
relying on user-interface convention.
**RBE-SYS-002** No infrastructure or application component SHALL possess an undocumented capability
to force a substantive decision outcome.
**RBE-SYS-003** Every service boundary SHALL preserve case identity, session identity, methodology
version, actor identity and correlation identifiers.
## 12.2 Architectural Style
RBE-001 shall begin as a modular monolith with explicit bounded modules, transactional
consistency inside the authoritative domain, and asynchronous integration at external boundaries.
This balances evidential integrity and implementation simplicity while retaining a migration path to
independently deployed services if scale or organizational boundaries later justify it.
- Modular monolith for the authoritative write model.
- Hexagonal architecture around domain modules.
- Command/query separation without premature infrastructure duplication.
- Outbox-driven publication for reliable external events.
- Stateless application nodes behind a trusted edge.
- Immutable object storage for evidence and signed report artefacts.
**RBE-SYS-010** Deployment topology SHALL NOT weaken module boundaries defined by this architecture.
**RBE-SYS-011** Service extraction SHALL require an architecture decision record demonstrating
preserved atomicity, traceability and separation of duties.
## 12.3 Logical Components
Component Primary responsibility Authoritative data
Trusted Edge
Authentication termination, request
validation, rate limiting and
correlation
No substantive case data
Identity and Access Module Role, case scope, conflict status and
policy evaluation
Assignments, roles and policy
decisions
Case Management Module Case registration, submissions,
lifecycle and ownership ReviewCase and SubmissionVersion
Evidence Module Evidence ingestion, locking,
classification, integrity and lineage
EvidencePackage, EvidenceItem and
hashes
Review Module Independent assessments, findings
and challenge responses AssessmentReport and findings
Decision Module Rule evaluation, consolidation and
decision assembly
DecisionEvaluation and
BoardDecision

<!-- Controlled source page 86 -->

Component Primary responsibility Authoritative data
Appeal Module Appeal grounds, admissibility and
successor sessions AppealCase and lineage
Audit and Provenance Module Append-only audit events and replay
bundles AuditEvent and provenance graph
Reporting Module Human and machine-readable
governed outputs ReviewReport and DecisionPackage
Workflow Coordinator Deadline tracking, notifications and
non-substantive orchestration Workflow timers and task projections
## 12.4 Trust Boundaries
The architecture recognizes distinct trust zones. Crossing a trust boundary requires identity
propagation, authorization, validation, classification handling and an audit event appropriate to the
action.
Boundary Inside Outside Required control
Public/Trusted Edge Authenticated application Browser, CLI and external
client
Strong authentication,
request size limits and
schema validation
Application/Authoritative
Domain Domain command handlers Edge and background
workers
Policy decision,
idempotency and
transaction boundary
Domain/Object Store Evidence metadata Binary evidence and
reports
Hash verification, signed
retrieval and malware
scanning
Domain/Integration Authoritative state Notification and
downstream systems
Outbox, allowlisted payload
and delivery audit
Human/AI Assistance Human-governed decision AI-generated suggestions
Attribution, non-
authoritative status and
human acceptance
**RBE-SYS-020** A trust-boundary crossing SHALL be observable through correlated logs and, where
governance-relevant, an immutable audit event.
**RBE-SYS-021** External systems SHALL receive only the minimum data required for their declared
purpose.
## 12.5 Deployment Topology
The baseline production topology consists of a web/API tier, background worker tier, relational
database, immutable object store, message broker or durable queue, key management service,
centralized observability stack and isolated administrative access plane.
Tier Characteristics Failure posture
Web/API Stateless, horizontally scalable, no
local authoritative state
Reject safely; clients may retry
idempotently
Worker Leased jobs, retry policies, poison
queue handling No duplicate substantive effect
Relational database Primary authoritative transactional
store Fail closed for writes

<!-- Controlled source page 87 -->

Tier Characteristics Failure posture
Object store Versioned or write-once retention for
governed artefacts Hash mismatch blocks use
Message transport At-least-once delivery with
deduplication
Delayed delivery does not alter
decisions
Observability Separate from authoritative audit Monitoring loss alerts but does not
create hidden state
## 12.6 Availability and Degraded Modes
Availability goals must never create a path around governance. Degraded operation may delay
intake, review, publication or notification; it may not fabricate approvals, bypass evidence lock, or
suppress audit.
- Read-only access may continue from verified replicas when writes are unavailable.
- New substantive commands are rejected if audit persistence cannot commit atomically.
- Notifications may queue while the authoritative decision remains final and visible.
- Report rendering may be retried from immutable decision data.
- Evidence retrieval failures place the affected review task into a blocked state.
**RBE-SYS-030** The system SHALL fail closed for any operation that would change governance state
without a durable audit record.
**RBE-SYS-031** Degraded-mode banners and machine-readable health responses SHALL distinguish
unavailable, read-only and partially degraded states.
## 12.7 Configuration and Methodology Control
Configuration capable of changing decision behaviour is governed content. Decision rules,
methodology versions, severity mappings, quorum thresholds and report schemas must be
versioned and activated through controlled release procedures.
**RBE-SYS-040** Decision-affecting configuration SHALL be immutable after activation and SHALL carry
effective-from metadata and an approval record.
**RBE-SYS-041** Ordinary operational administrators SHALL NOT modify active decision rules directly in
production.
**RBE-SYS-042** Every case SHALL resolve decision-affecting configuration by explicit version identifier,
never by “latest” at replay time.
## 12.8 AI Assistance Boundary
AI may assist with extraction, summarization, duplication detection, drafting and anomaly
surfacing. It remains outside the authoritative decision boundary. All AI outputs are suggestions
with provenance, model identification where available, prompt/context references, confidence
limitations and human acceptance status.
- AI cannot cast a vote or satisfy quorum.
- AI cannot create a final finding without human adoption.
- AI cannot alter evidence or methodology records.
- AI cannot approve its own suggestion.
- AI-generated text in a final report must be attributable to the accepting human reviewer.

<!-- Controlled source page 88 -->

**RBE-SYS-050** Disabling all AI assistance SHALL leave the complete governed review process
operational.
**RBE-SYS-051** AI failure SHALL degrade convenience only, not substantive governance capability.
## 12.9 Observability Architecture
Operational telemetry and governance audit are complementary but distinct. Logs, metrics and
traces diagnose system behaviour; audit events establish durable accountability. Neither may
silently substitute for the other.
Signal Purpose Examples
Metrics Health, capacity and service
objectives
Latency, queue age, error rate, lock
contention
Traces Cross-component request
reconstruction
Correlation ID, span hierarchy and
dependency time
Application logs Technical diagnostics Validation failure, retry and
dependency status
Audit events Governance accountability
Assignment, evidence lock,
assessment submission and decision
publication
**RBE-SYS-060** Sensitive evidence content SHALL NOT be copied into ordinary application logs.
**RBE-SYS-061** Observability identifiers SHALL permit correlation to an audit event without exposing
protected content.
## 12.10 Security Architecture Baseline
- Strong user authentication with phishing-resistant options for privileged roles.
- Short-lived service credentials and workload identity.
- Encryption in transit and at rest.
- Central key management with rotation and access logging.
- Network segmentation for data, application and administrative planes.
- Dependency and container vulnerability management.
- Secrets excluded from source control, logs and report artefacts.
- Backups tested through governed restoration exercises.
**RBE-SYS-070** Security controls SHALL preserve evidential integrity and reviewer independence as
explicit protection objectives.
## 12.11 Codex Implementation Contract
- Create modules that correspond to the bounded responsibilities in Section 12.3.
- Keep domain rules independent of web frameworks, database clients and queue libraries.
- Use dependency inversion for storage, time, identity, cryptographic and notification services.
- Do not introduce a generic super-admin route that bypasses domain commands.
- Emit correlation, causation, case and session identifiers on all substantive operations.
- Implement health checks that reveal dependency degradation without exposing secrets.
- Provide architecture tests that prevent prohibited module dependencies.
- Document every new cross-boundary data flow in an architecture decision record.

# 13. API and Command Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 90 -->

## 13.1 Purpose
The API is a governed command surface, not a thin database façade. It must express domain intent,
reject ambiguous mutation, preserve idempotency, expose failed preconditions clearly and avoid
endpoints that permit clients to assemble invalid states.
**RBE-API-001** Every mutating endpoint SHALL map to a named domain command with defined actor,
target, preconditions and audit effect.
**RBE-API-002** The API SHALL NOT expose unrestricted create, update or delete operations for governed
aggregates.
## 13.2 API Styles
Style Use Constraint
REST/JSON External and user-facing synchronous
commands and queries
Resource-oriented URLs with intent-
specific commands
Internal command bus Application-to-domain invocation Typed command and result contracts
Event subscription Asynchronous downstream
integration
Versioned event envelopes and at-
least-once semantics
Bulk export Audit, replay and governed reporting Asynchronous job with signed
manifest
## 13.3 Command Envelope
Every command shall carry a standard envelope sufficient for authorization, concurrency, replay
protection and audit correlation.
Field Required Meaning
command_id Yes Globally unique idempotency
identifier
command_type Yes Stable command name and version
actor_id Yes Authenticated principal or workload
identity
case_id Contextual Target review case
session_id Contextual Target board session
expected_version For aggregate mutation Optimistic concurrency token
correlation_id Yes End-to-end operation identifier
causation_id When derived Prior command or event identifier
requested_at Yes Client timestamp treated as
informational
reason_code For governed actions Controlled vocabulary rationale
payload Yes Command-specific validated data
**RBE-API-010** The server SHALL derive authorization identity from trusted authentication context, not
from a caller-supplied actor_id alone.

<!-- Controlled source page 91 -->

**RBE-API-011** Idempotency records SHALL bind command identity to actor, target and normalized
payload hash.
## 13.4 Core Command Catalogue
Command Authorized actor Key preconditions Primary result
RegisterCase Intake Officer Valid submission metadata DRAFT case
SubmitVersion Submitter/Intake Case accepts submission Immutable
SubmissionVersion
AcceptIntake Intake Officer Validation complete ACCEPTED state
LockEvidence Evidence Custodian Package complete and
verified EVIDENCE_LOCKED
AssignReviewer Board Chair/Assignment
Service Eligibility and SoD pass ReviewerAssignment
DeclareConflict Any assigned reviewer Active assignment Conflict declaration
SubmitAssessment Assigned reviewer Correct function and state Immutable
AssessmentReport
SubmitChallenge Eligible challenger Challenge window open Challenge record
RecordClarification Authorized party Clarification request open Linked clarification
ConsolidateFindings Decision Assembly role Required assessments
complete Normalized findings
EvaluateDecision Decision service Frozen rule set and inputs DecisionEvaluation
RatifyDecision Governance authority Quorum and validation
pass BoardDecision
PublishDecision Publication authority Signed outputs complete PUBLISHED state
LodgeAppeal Eligible appellant Ground and time
requirements AppealCase
OpenReReview Governance authority Permitted trigger Successor session
## 13.5 Query Model
Queries may use denormalized projections optimized for navigation and reporting, but every
substantive displayed value must retain a pointer to its authoritative source and version.
- Case summary projection.
- Reviewer work queue projection.
- Evidence inventory and integrity status projection.
- Decision provenance projection.
- Audit timeline projection.
- Public or audience-filtered decision projection.
**RBE-API-020** Query projections SHALL be rebuildable from authoritative records and events.
**RBE-API-021** A stale projection SHALL never be used to authorize a command or determine a
substantive outcome.
## 13.6 Error Contract
Category HTTP indication Required response content
Validation failure 400 Field path, code and safe explanation
Authentication required 401 No protected detail

<!-- Controlled source page 92 -->

Category HTTP indication Required response content
Authorization denied 403 Policy code without leaking restricted
content
Not found or hidden 404 Opaque response where disclosure is
restricted
Concurrency conflict 409 Current aggregate version and retry
guidance
Failed precondition 422 Exact governance precondition codes
Rate or capacity limit 429 Retry guidance
Dependency unavailable 503 Degraded-mode identifier and
correlation ID
**RBE-API-030** Error responses SHALL be deterministic, machine-readable and safe for the caller’s
authorization scope.
**RBE-API-031** The API SHALL distinguish business rejection from technical failure.
## 13.7 Idempotency and Concurrency
Clients and workers may retry. The architecture therefore treats duplicate delivery as normal.
Commands that could create substantive effects require idempotency keys, payload-hash
comparison and optimistic concurrency against the aggregate version.
**RBE-API-040** A repeated accepted command with the same idempotency key SHALL return the original
result.
**RBE-API-041** Reusing an idempotency key with a different normalized payload SHALL be rejected and
audited as a protocol violation.
**RBE-API-042** Lost-update prevention SHALL apply to all aggregate mutations.
## 13.8 Versioning and Compatibility
- Version external contracts independently from internal class names.
- Use additive changes where possible.
- Retain semantic meaning of existing fields.
- Publish deprecation windows and migration guidance.
- Keep event consumers tolerant of unknown additive fields.
- Never reinterpret a historical outcome code in place.
**RBE-API-050** Breaking contract changes SHALL require a new major version and a documented
migration path.
## 13.9 File and Evidence Transfer
Binary evidence shall be transferred using short-lived signed upload/download grants. Metadata
registration and finalization remain governed commands. A file is not evidence until malware
checks, hash computation, classification and metadata validation complete.
Step Command or operation Control
1 RequestUploadGrant Authorization, size and media policy
2 Direct upload to quarantine No case evidence status yet
3 FinalizeEvidenceItem Server hash and scan result required

<!-- Controlled source page 93 -->

Step Command or operation Control
4 AttachToEvidencePackage Package ownership and classification
check
5 LockEvidencePackage Completeness and chain-of-custody
validation
**RBE-API-060** Client-provided hashes SHALL be treated as claims and verified server-side.
**RBE-API-061** Download grants SHALL be audience-scoped, short-lived and logged.
## 13.10 API Security and Abuse Controls
- Schema and content-type validation.
- Request body and file size limits.
- Per-actor and per-client throttling.
- Replay protection for privileged commands.
- CSRF protection for browser sessions.
- Outbound URL allowlisting for any retrieval feature.
- Safe pagination limits and export quotas.
- No direct exposure of internal storage keys.
## 13.11 Example Decision Command Contract
Attribute Example
Command RatifyDecision v1
Target BoardSession
Required roles Governance Reviewer plus authorized Chair
Preconditions Assessments complete; challenge resolved; quorum valid;
no unresolved conflicts; evaluation frozen
Atomic writes BoardDecision, state transition, audit event, outbox event
Idempotency Required
Failure behavior No partial decision or transition
Output Decision identifier, outcome, rationale hash, aggregate
version and report-generation status
## 13.12 Codex Implementation Contract
- Generate OpenAPI schemas from reviewed contract definitions, not from database entities.
- Implement command handlers as thin adapters over domain services.
- Use explicit DTOs and reject unknown mutation fields where safety requires.
- Apply authorization before loading or returning protected content.
- Return stable error codes suitable for tests and clients.
- Write contract tests for idempotency, concurrency, forbidden transitions and audience filtering.
- Never add a generic PATCH endpoint for governed aggregates.
- Keep public decision APIs read-only and audience-filtered.

# 14. Persistence and Data Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 94 -->

## 14.1 Purpose
The persistence architecture protects the integrity, lineage and reproducibility of governed
decisions. It distinguishes authoritative transactional records, immutable artefacts, derived
projections, operational telemetry and temporary processing data.
**RBE-DAT-001** Each data item SHALL have a declared system of record, owner, classification, retention
rule and mutability rule.
**RBE-DAT-002** Derived data SHALL never silently replace or overwrite its authoritative source.
## 14.2 Storage Classes
Storage class Technology baseline Contents Mutability
Transactional store Relational database
Cases, assignments,
assessments, decisions and
audit metadata
Controlled by domain
commands
Immutable object store Versioned/WORM-capable
object storage
Evidence binaries, report
renderings and replay
bundles
Append-only/versioned
Projection store Relational read models or
search index
Queues, timelines and
search views Rebuildable
Message transport Durable broker/queue Integration events and
work items
Transient with durable
acknowledgment
Telemetry store Logs, metrics and traces Operational diagnostics Retention-limited
Quarantine store Isolated object storage Unverified uploads Temporary and restricted
## 14.3 Relational Aggregate Model
Aggregate root Key child records Consistency boundary
ReviewCase SubmissionVersion, case metadata
and lifecycle version
Case registration and high-level
lifecycle
EvidencePackage EvidenceItem, source metadata and
integrity records Evidence composition and lock
BoardSession
ReviewerAssignment,
AssessmentReport, Challenge and
clarification
Single governed review session
BoardDecision DecisionEvaluation, normalized
findings and rationale references Final decision assembly
AppealCase Grounds, admissibility result and
successor-session reference Appeal processing
ReviewReport Output variants, signatures and
publication records Report generation and release
## 14.4 Identifier Strategy
Identifiers must be opaque, globally unique and stable. Human-readable case references may
coexist with immutable internal identifiers but shall not encode sensitive meaning.

<!-- Controlled source page 95 -->

- UUIDv7 or equivalent sortable opaque identifiers for primary entities.
- Separate display reference such as RBE-2026-000123.
- No reuse of deleted, voided or abandoned identifiers.
- Explicit lineage identifiers for supersession and remand.
**RBE-DAT-010** Foreign-system identifiers SHALL be stored as namespaced external references, not used
as internal primary keys.
## 14.5 Immutability and Versioning
Published decisions, submitted assessments, locked evidence metadata, activated rule sets and audit
events are immutable. Corrections occur through successor records linked to the original. Mutable
workflow metadata uses optimistic version columns and complete audit coverage.
Record Mutation rule
SubmissionVersion Never edited after submission; successor version only
EvidenceItem after lock Binary and core metadata immutable; annotation through
linked record
AssessmentReport after submit Immutable; withdrawal or superseding assessment only
BoardDecision Immutable after ratification; successor decision through
governed session
AuditEvent Append-only; correction event references prior event
Projection Freely rebuildable from authoritative records
**RBE-DAT-020** Hard deletion of governed records SHALL be prohibited in normal application operation.
**RBE-DAT-021** Privacy-driven erasure or redaction SHALL preserve a verifiable tombstone and legal
basis without retaining prohibited content.
## 14.6 Evidence Integrity and Object Storage
Metadata Requirement
content_hash Strong approved digest over exact bytes
size_bytes Verified server-side
media_type Detected and declared values retained
storage_version Immutable object version identifier
classification Access and handling category
source_reference Origin and acquisition context
ingested_at Trusted server time
malware_status Scanner result and signature version
custody_events Ordered acquisition, transfer, lock and access events
**RBE-DAT-030** Every evidence read used in review SHALL verify object identity against authoritative
metadata.
**RBE-DAT-031** Replacement of an evidence object SHALL create a new EvidenceItem and shall never
preserve the prior identifier.

<!-- Controlled source page 96 -->

## 14.7 Audit Persistence
Audit events are persisted in an append-only logical ledger in the same transaction as the governed
change. A hash chain or signed batch manifest provides tamper evidence. Audit storage may be
replicated into a separate retention domain, but the transactional record remains the publication
source for event identity and ordering.
**RBE-DAT-040** The governed write and its primary audit event SHALL commit or roll back together.
**RBE-DAT-041** Audit sequence allocation SHALL be deterministic within an aggregate or ledger partition.
## 14.8 Data Classification
Class Examples Baseline handling
Public Published decision notice approved
for public release Read-only public access
Internal Operational status and non-sensitive
metadata Authenticated workforce access
Restricted Reviewer identities, assessments and
commercial analysis Case-scoped need-to-know
Highly Restricted Personal data, privileged evidence
and security material
Explicit grant, enhanced logging and
export control
System Secret Credentials, signing keys and
recovery material
Dedicated secret/key management;
never in database fields or reports
## 14.9 Retention, Archival and Legal Hold
Retention is policy-driven by artefact class, jurisdiction, contractual obligations and evidential value.
Expiration jobs create auditable disposition records. Legal hold overrides normal deletion and must
itself be authorized, scoped and reviewed.
Data family Default architectural posture
Final decisions and provenance Long-term or permanent retention subject to policy
Evidence Retention aligned with case, appeal and legal obligations
Draft working data Shorter retention after closure
Authentication and security telemetry Time-bound security retention
Quarantine uploads Rapid disposal after rejection or expiry
Backups Encrypted, rotation-based and disposition-aware
**RBE-DAT-050** Retention configuration SHALL be versioned and applied by record classification and
effective policy version.
**RBE-DAT-051** Archive retrieval SHALL preserve integrity verification and access authorization.
## 14.10 Backup, Restore and Disaster Recovery
- Point-in-time recovery for the transactional store.
- Cross-zone and, where required, cross-region replication.
- Versioned immutable evidence objects.
- Encrypted backups with independently controlled keys.
- Documented recovery point and recovery time objectives.

<!-- Controlled source page 97 -->

- Regular restoration tests that include audit-chain and object-hash verification.
- Recovery procedures that prevent duplicate event publication.
**RBE-DAT-060** A restoration SHALL not be declared successful until authoritative data, evidence
integrity and audit continuity are verified together.
## 14.11 Migrations and Schema Evolution
Schema migrations are reviewed, ordered, repeatable and reversible where technically safe.
Destructive changes use expand-migrate-contract sequencing and verified backups. Historical
semantics are preserved through explicit version fields and translation layers.
**RBE-DAT-070** Production migrations SHALL be automated, checksum-verified and recorded as
deployment evidence.
**RBE-DAT-071** A migration SHALL NOT rewrite historical decision meaning to conform to a newer
taxonomy.
## 14.12 Data Quality Controls
Control Example
Referential integrity Every decision references an existing session and rule set
Check constraints Outcome and terminal state combinations
Unique constraints One active assignment per reviewer/function/session
Completeness rules Published report has required signatures and hashes
Reconciliation Object inventory against evidence metadata
Replay validation Decision inputs reproduce stored evaluation result
## 14.13 Codex Implementation Contract
- Use database constraints to reinforce, not replace, domain invariants.
- Keep migrations in source control and test them against realistic copies.
- Store timestamps in UTC with clear precision and trusted server generation.
- Use explicit transaction boundaries for governed commands.
- Implement an outbox table in the same database transaction as aggregate changes.
- Never cascade-delete governed records.
- Create reconciliation jobs for database/object-store consistency.
- Provide deterministic fixtures and migration tests for historical versions.

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

# 16. Security Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 103 -->

## 16.1 Purpose
This chapter defines the security architecture required to preserve the integrity, confidentiality,
availability and independence of the Review Board Engine. Security is not treated as a perimeter
concern. It is part of the governance model because any unauthorized change to evidence, reviewer
assignments, findings, methodology versions, decision rules or reports can invalidate the legitimacy
of the Board itself.
**RBE-SEC-001** Security controls SHALL protect evidential integrity, reviewer independence, decision
provenance and reproducibility as first-class protection objectives.
**RBE-SEC-002** No security exception SHALL create a capability to force, suppress or rewrite a
substantive review outcome.
## 16.2 Security Objectives
- Prevent unauthorized access to cases, evidence and review material.
- Prevent unauthorized or untraceable modification of governed records.
- Preserve the separation of duties established in Chapter 9.
- Ensure that privileged access is attributable, time-bounded and independently reviewable.
- Ensure that compromise of a non-authoritative component cannot silently alter authoritative
state.
- Maintain the ability to reconstruct security-relevant events during an investigation.
- Preserve availability without bypassing governance controls during degraded operation.
## 16.3 Threat Model
The baseline threat model includes malicious insiders, compromised reviewer accounts,
compromised administrator accounts, supply-chain compromise, external attackers, accidental data
leakage, privilege escalation, evidence tampering, report substitution, malicious automation and
unauthorized model-generated content. The architecture assumes that any single identity, client
device, application node or integration may fail or become compromised.
Threat Primary control family Governance consequence if
uncontrolled
Reviewer account takeover
Phishing-resistant MFA,
conditional access, session
controls
Fraudulent findings,
disclosure of protected
evidence or manipulation of
reviewer work
Administrator misuse
Just-in-time privilege, dual
authorization, immutable
audit
Circumvention of assignment,
state or retention controls
Evidence tampering Content hashing, immutable
storage, chain of custody
Invalid decision basis and loss
of reproducibility
Report substitution Digital signing, artefact hash Public or internal reliance on

<!-- Controlled source page 104 -->

Threat Primary control family Governance consequence if
uncontrolled
binding, trusted publication a false decision artefact
API abuse
Strong authentication,
authorization, rate limits,
command validation
Unauthorized transitions or
denial of service
Supply-chain compromise
Pinned dependencies, SBOM,
signed builds, provenance
verification
Malicious code inside trusted
deployment path
AI prompt or data attack Content isolation, validation,
model boundary controls
Manipulated summaries,
disclosure or unsafe
recommendations
## 16.4 Identity and Authentication
Human and workload identities shall be centrally governed. Authentication proves identity; it does
not confer permission. Authorization remains contextual to role, case assignment, conflict status,
review stage and action type.
- Phishing-resistant multi-factor authentication for privileged and substantive reviewer roles.
- Short-lived access tokens with explicit audience, issuer and scope validation.
- Workload identity for services; no long-lived embedded service passwords.
- Device and session risk evaluation for privileged operations.
- Step-up authentication for report signing, role elevation, evidence export and emergency actions.
- Immediate revocation on separation, role withdrawal or confirmed compromise.
**RBE-SEC-010** The system SHALL reject authentication assertions that cannot be validated against a
trusted issuer, intended audience and current revocation state.
**RBE-SEC-011** Privileged human access SHALL require phishing-resistant multi-factor authentication
and SHALL be re-authenticated for high-impact operations.
**RBE-SEC-012** Service-to-service authentication SHALL use managed workload identity or equivalently
short-lived credentials.
## 16.5 Authorization and Policy Enforcement
Authorization shall be evaluated at the domain boundary using deny-by-default policy. UI
concealment is not authorization. Every command must be checked against actor identity, role, case
assignment, conflict declarations, current state, object classification and separation-of-duties
constraints.
Authorization input Example Required effect
Actor identity Reviewer, chair, auditor,
workload
Establish accountable
principal
Role and capability Evidence reviewer, report Limit permitted command

<!-- Controlled source page 105 -->

Authorization input Example Required effect
publisher family
Case relationship Assigned, unassigned, recused Enforce case-scoped authority
State and stage Evidence review open,
decision final
Prevent invalid timing of
action
Conflict status Declared conflict, pending
determination
Suspend or prohibit
substantive action
Resource classification Restricted evidence, internal
report
Apply access and export
controls
Separation-of-duties rule Author cannot approve own
report Require independent actor
**RBE-SEC-020** Every mutating command SHALL be authorized within the authoritative application or
domain boundary immediately before state change.
**RBE-SEC-021** Authorization decisions SHALL be logged with actor, policy version, target, result and
correlation identifiers without exposing protected content.
**RBE-SEC-022** No generic administrator role SHALL bypass case-state, conflict, quorum or separation-of-
duties controls.
## 16.6 Privileged Access Management
Privileged access must be exceptional rather than ambient. Standing production privileges increase
the likelihood of invisible governance failure. Administrative access therefore requires time-bound
elevation, reason capture, approval where appropriate and enhanced monitoring.
- Just-in-time elevation with automatic expiry.
- Dual authorization for destructive, retention-affecting or cryptographic-key operations.
- Break-glass accounts held outside normal identity paths and tested under controlled conditions.
- Privileged session recording or equivalent command-level evidence for high-risk administration.
- Quarterly access recertification and immediate review after organizational change.
- No shared administrative credentials.
**RBE-SEC-030** Emergency access SHALL NOT permit alteration of finalized decisions, signed reports or
immutable audit history.
**RBE-SEC-031** Use of break-glass access SHALL trigger an independent post-event review and security
incident record.
## 16.7 Data Classification and Handling
Classification Examples Minimum handling
Public Published decision notice Integrity protection and
publication provenance
Internal Operational dashboards, non- Authenticated access and

<!-- Controlled source page 106 -->

Classification Examples Minimum handling
sensitive metadata ordinary logging controls
Confidential Reviewer notes, internal
findings, commercial analysis
Need-to-know access,
encryption and controlled
export
Restricted
Personal data, legally sensitive
evidence, protected source
material
Case-scoped access, enhanced
monitoring, explicit retention
and export approval
**RBE-SEC-040** Every evidence object and report artefact SHALL carry an explicit classification and
handling policy.
**RBE-SEC-041** Data classification SHALL propagate to derived artefacts, exports, search indexes and AI-
processing requests.
## 16.8 Encryption and Key Management
- Encryption in transit using current approved protocols.
- Encryption at rest for databases, object stores, queues, backups and search indexes.
- Application-level envelope encryption for the most sensitive evidence classes where required.
- Centralized key management with role separation between data operators and key
administrators.
- Rotation, revocation and recovery procedures tested before production use.
- Key usage logging bound to workload identity and purpose.
**RBE-SEC-050** Cryptographic keys SHALL be managed outside application source code, container images
and ordinary configuration repositories.
**RBE-SEC-051** Evidence and signed report artefacts SHALL retain verifiable content hashes independent
of the storage provider.
## 16.9 Secrets Management
Secrets include API credentials, signing material, database credentials, integration tokens and
recovery material. They shall be injected at runtime from an approved secrets manager and never
stored in source control, build logs, test fixtures or report artefacts.
**RBE-SEC-060** Secret access SHALL be least-privilege, attributable, short-lived where supported and
auditable.
**RBE-SEC-061** Production secrets SHALL NOT be copied into lower environments.
## 16.10 Application and API Security
- Input validation against explicit command schemas.
- Output encoding and safe content rendering.
- Protection against injection, path traversal, unsafe deserialization and server-side request
forgery.
- Idempotency and replay protection for substantive commands.
- Rate limiting appropriate to actor, endpoint and sensitivity.

<!-- Controlled source page 107 -->

- File-type, size, malware and content-disarm controls for evidence ingestion.
- Secure error handling that does not disclose secrets, internal topology or protected evidence.
**RBE-SEC-070** Evidence files SHALL be quarantined until validation, integrity hashing and malware
scanning complete successfully.
**RBE-SEC-071** Security validation failure SHALL prevent authoritative ingestion and SHALL create a
traceable rejection record.
## 16.11 Network and Infrastructure Security
The system shall separate public ingress, application, data, administrative and build planes. Direct
access to authoritative data services from user networks is prohibited. Administrative access shall
occur through controlled, strongly authenticated paths.
**RBE-SEC-080** Authoritative databases, object stores and brokers SHALL NOT be directly exposed to the
public internet.
**RBE-SEC-081** Network policy SHALL restrict service communication to documented flows defined by the
architecture.
## 16.12 Software Supply-Chain Security
- Maintain a software bill of materials for each release.
- Pin and verify dependency versions.
- Scan source, dependencies, containers and infrastructure definitions.
- Sign build artefacts and verify signatures before deployment.
- Use isolated build workers with minimal credentials.
- Preserve build provenance from source commit to deployed image.
- Require review for changes to security-sensitive dependencies and build workflows.
**RBE-SEC-090** Production deployments SHALL consume only artefacts produced by the approved,
attestable build pipeline.
**RBE-SEC-091** A critical unresolved supply-chain vulnerability SHALL block release unless a formally
approved, time-bounded risk exception exists.
## 16.13 Security Logging, Detection and Response
Security telemetry shall complement, not replace, the immutable governance audit trail. Detection
must cover authentication anomalies, privilege elevation, evidence access, export activity, policy
denial spikes, integrity failures, signing failures and unusual administrative behaviour.
Security event Minimum response
Repeated failed privileged authentication Risk escalation, possible session block and alert
Unexpected evidence hash mismatch Immediate quarantine, case block and incident
declaration
Unauthorized export attempt Deny, audit and alert
Break-glass use Immediate notification and mandatory
retrospective review
Signing-key anomaly Suspend publication and invoke key incident

<!-- Controlled source page 108 -->

Security event Minimum response
procedure
Audit-chain validation failure Fail closed for substantive mutation and
initiate incident response
**RBE-SEC-100** The incident response process SHALL preserve evidence required to determine whether
governance outcomes were affected.
**RBE-SEC-101** A security incident with possible decision impact SHALL trigger case-impact assessment
and, where necessary, re-review.
## 16.14 Privacy and Data Minimization
The engine shall process only data necessary for review and governance. Personal or sensitive data
should be isolated, redacted or tokenized where reviewers do not require direct access. Privacy
controls must not destroy traceability; redactions must preserve a verifiable relationship to the
protected original.
**RBE-SEC-110** Exports and AI-processing requests SHALL contain the minimum data necessary for the
declared purpose.
**RBE-SEC-111** Retention and deletion SHALL follow approved schedules while preserving legally or
methodologically required provenance.
## 16.15 Security Assurance and Acceptance
- Threat-model review before major architecture change.
- Secure code review and automated security tests in CI.
- Penetration testing before production and after material boundary changes.
- Access-control and separation-of-duties test suites.
- Backup, key-recovery and incident-response exercises.
- Architecture conformance review for every production release.
**RBE-SEC-120** Security acceptance SHALL include evidence that governance controls remain effective
under attack, failure and privileged misuse scenarios.
## 16.16 Codex Implementation Contract
- Implement deny-by-default authorization in domain command handlers.
- Never create hidden maintenance routes capable of rewriting governed state.
- Keep secrets out of repository, fixtures, logs and generated artefacts.
- Use parameterized data access and validated command schemas.
- Preserve evidence and report hashes through every storage and transport layer.
- Add automated tests for privilege escalation, conflict enforcement and separation of duties.
- Document every new trust-boundary crossing and required security control.
- Fail closed when authorization, audit persistence or integrity verification is unavailable.

# 17. AI and Automation Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 109 -->

## 17.1 Purpose
This chapter defines how artificial intelligence and deterministic automation may assist the Review
Board without becoming a decision-maker, hidden methodology or source of outcome pressure. AI is
an internal capability. It may reduce clerical effort, surface inconsistencies and improve navigation,
but it cannot own judgment, satisfy quorum or substitute for evidence.
**RBE-AI-001** The complete governed review process SHALL remain operational when all AI assistance is
disabled.
**RBE-AI-002** AI output SHALL be treated as untrusted proposed content until explicitly reviewed and
adopted by an authorized human.
**RBE-AI-003** No model, agent or automated workflow SHALL possess authority to approve, reject or
finalize a substantive Review Board outcome.
## 17.2 Permitted Uses
Use case Permitted role Required control
Evidence extraction Assistant Source citation and human
verification
Deduplication and clustering Assistant No deletion; reviewer
confirms relationship
Summarization Assistant Traceable to source passages
and labeled as generated
Contradiction surfacing Assistant Present both supporting and
opposing material
Draft finding language Assistant Human reviewer owns final
wording and rationale
Schema validation Deterministic automation Versioned rules and testable
output
Deadline and workflow
reminders Deterministic automation No substantive state override
Anomaly detection Assistant Explain signal basis and
permit dismissal
## 17.3 Prohibited Uses
- Casting or simulating a Board vote.
- Choosing a final decision class without human decision authority.
- Generating unsupported evidence or citations.
- Changing evidence, methodology, findings or decisions without a governed command.
- Suppressing contradictory evidence because it weakens a preferred outcome.

<!-- Controlled source page 110 -->

- Optimizing prompts or ranking toward approval, rejection or commercial desirability.
- Inferring sensitive personal attributes unless explicitly authorized and methodologically
necessary.
- Using confidential case data to train external models without approved contractual and technical
safeguards.
- Auto-publishing reports or recommendations.
**RBE-AI-010** The system SHALL technically prevent AI identities from invoking decision-finalization,
report-signing, appeal-resolution and privilege-management commands.
## 17.4 Human Accountability
A human may use AI-generated material only by adopting it through an attributable action.
Adoption means the reviewer has examined the underlying sources, accepts responsibility for
accuracy and understands that the generated text does not reduce their duty of independent
judgment.
**RBE-AI-020** Every AI-assisted final artefact SHALL identify the responsible human adopter and retain
provenance to the model invocation and cited source material.
**RBE-AI-021** A reviewer SHALL be able to edit, reject or ignore AI output without penalty or workflow
obstruction.
## 17.5 Model and Provider Governance
Control area Architecture requirement
Approved models Use only models recorded in the active model
registry
Provider terms Verify data-use, retention, residency and
confidentiality commitments
Model version Pin production use to a recorded model or
deployment version
Capability assessment Evaluate context length, tool use, structured
output and known limitations
Risk tier Classify use case by data sensitivity and
decision proximity
Change control Re-evaluate prompts and tests before model or
provider change
Fallback Provide deterministic or human-only path
**RBE-AI-030** Each production model deployment SHALL have an owner, approved use cases, data
classification limit, evaluation record and retirement procedure.
**RBE-AI-031** Model upgrades SHALL NOT be treated as transparent infrastructure changes where they
can alter substantive output.

<!-- Controlled source page 111 -->

## 17.6 Prompt and Instruction Governance
Prompts that influence substantive review assistance are governed artefacts. System instructions,
templates, retrieval policies, output schemas and tool permissions shall be versioned, reviewed and
testable. User-entered case content must never be allowed to override protected system instructions
or tool restrictions.
- Versioned prompt identifiers and effective dates.
- Change approval for decision-adjacent prompts.
- Explicit source-grounding and uncertainty instructions.
- Output schemas that separate facts, inference, uncertainty and recommendations.
- Prompt-injection resistance and content isolation.
- No hidden instructions that promote a preferred outcome.
**RBE-AI-040** Every model invocation SHALL record prompt version, model version, parameters, tools,
source references, actor, case, timestamp and output hash.
**RBE-AI-041** Case evidence SHALL be treated as data, not as trusted instructions to the model or agent.
## 17.7 Retrieval and Grounding
Retrieval-augmented assistance must preserve source identity, version and exact evidence location.
The model may synthesize across retrieved material but may not present an uncited assertion as
established evidence.
**RBE-AI-050** AI-generated factual claims used in review artefacts SHALL resolve to authoritative
evidence references accessible to the adopting reviewer.
**RBE-AI-051** The retrieval layer SHALL enforce the same case access, classification and conflict
restrictions as direct evidence access.
## 17.8 Output Structure and Uncertainty
- Separate extracted facts from interpretation.
- Distinguish direct evidence from model inference.
- Express uncertainty and missing context.
- Identify contradictory or unavailable evidence.
- Avoid persuasive or outcome-seeking language.
- Provide machine-verifiable references where possible.
**RBE-AI-060** AI output SHALL NOT be represented to users as a Board decision, reviewer opinion or
verified fact until the relevant human action occurs.
## 17.9 Evaluation Framework
Evaluation dimension Illustrative measures
Grounding Citation precision, unsupported-claim rate,
evidence coverage
Neutrality Outcome skew, loaded-language rate, balanced
contradiction handling
Accuracy Extraction correctness, classification accuracy,

<!-- Controlled source page 112 -->

Evaluation dimension Illustrative measures
numerical fidelity
Safety Data leakage, prompt-injection resistance,
prohibited-command resistance
Reliability Schema conformance, timeout rate, retry
behaviour, determinism where required
Human utility Acceptance with edits, reviewer time saved,
false-positive burden
**RBE-AI-070** Decision-adjacent AI features SHALL pass documented evaluations before release and after
material model, prompt or retrieval changes.
**RBE-AI-071** Evaluation datasets SHALL include adversarial, contradictory, incomplete and outcome-
tempting cases.
## 17.10 Bias and Outcome Neutrality Controls
Bias control is not satisfied by asking a model to be unbiased. The system must constrain inputs,
prompts, outputs and user experience so that AI has no incentive or authority to advance a desired
result.
- Balanced retrieval across supporting and contradictory evidence.
- Neutral labels and ordering for decision classes.
- No success metric based on approval rate or commercial conversion.
- Periodic outcome-distribution review to detect unexplained drift.
- Blind or masked evaluation where practical.
- Independent review of high-impact prompt changes.
**RBE-AI-080** AI feature performance SHALL NOT be optimized against approval, rejection, pass-rate or
commercial-conversion targets.
## 17.11 Agents and Tool Use
Agentic workflows increase risk because a model may select and sequence actions. Agents may be
used only within narrow, pre-authorized task envelopes. Every tool call must be policy-checked,
schema-validated, attributable and reversible where feasible.
Agent capability Permitted? Constraint
Search authorized evidence Yes Case-scoped access and
complete retrieval logging
Create draft note Yes Draft namespace only; human
adoption required
Assign reviewer No
Governed human or
deterministic workflow
command

<!-- Controlled source page 113 -->

Agent capability Permitted? Constraint
Change case state No Only explicit authorized
domain command
Send reminder Yes Template-bound and non-
substantive
Publish report No Human authorization and
signing required
Delete evidence No Retention-governed human
process only
**RBE-AI-090** Agent tools SHALL expose the minimum capability necessary and SHALL NOT provide
generic database, shell or unrestricted network access in production.
## 17.12 Data Protection and Model Isolation
- Classify data before model submission.
- Redact or tokenize unnecessary personal and sensitive data.
- Use private or enterprise model endpoints for protected cases.
- Disable provider training and unnecessary retention where contractually and technically
supported.
- Separate case context between sessions and tenants.
- Prevent generated content from leaking into unrelated cases.
**RBE-AI-100** Restricted evidence SHALL NOT be sent to a model or provider not approved for that
classification.
## 17.13 Failure, Fallback and Kill Switch
AI failure must degrade convenience rather than governance. Timeouts, malformed responses,
model unavailability or evaluation failures shall return the task to a human or deterministic path
without silently changing substantive state.
**RBE-AI-110** The platform SHALL provide a centrally controlled kill switch capable of disabling AI
invocations without disabling core Review Board operations.
**RBE-AI-111** AI retries SHALL preserve idempotency and SHALL NOT duplicate adopted notes,
notifications or audit events.
## 17.14 Audit and Explainability
Explainability means the system can show what model was used, what information it received, what
instructions governed it, what tools it invoked, what it returned and who accepted or rejected the
result. It does not require exposing private model reasoning.
**RBE-AI-120** AI provenance SHALL be sufficient to reproduce the invocation context to the extent
permitted by provider capability and retention policy.
## 17.15 Codex Implementation Contract
- Put AI behind explicit interfaces separate from authoritative domain services.

<!-- Controlled source page 114 -->

- Assign AI identities no substantive decision permissions.
- Persist invocation provenance and output hashes.
- Label generated content clearly in the UI and data model.
- Require human adoption before generated content enters governed artefacts.
- Provide deterministic fallbacks and feature flags.
- Validate all structured model output before use.
- Treat retrieved evidence as untrusted data and enforce case-scoped access.
- Add adversarial tests for prompt injection, data leakage and prohibited tool use.

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

# 20. Testing and Quality Assurance Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 128 -->

## 20.1 Purpose
This chapter defines the verification system required to establish that the Review Board Engine
behaves as specified, preserves impartiality, and produces decisions that are traceable, reproducible
and resistant to unauthorized influence. Testing is not limited to software correctness. It must also
demonstrate governance correctness: the engine must reject actions that would violate
methodology, evidence integrity, reviewer independence or decision authority.
**RBE-TST-001** The release process SHALL provide objective evidence that functional, security,
governance, traceability and operational requirements have been verified before production
promotion.
**RBE-TST-002** A test result SHALL NOT be considered sufficient when it proves only that a user interface
path works while the authoritative domain rule remains unverified.
## 20.2 Quality Objectives
- Correctness: authorized actions produce the specified state and unauthorized actions are
rejected.
- Determinism: repeated evaluation of the same governed inputs produces compatible machine
decisions and explainable variation where human judgement is permitted.
- Traceability: every requirement can be linked to one or more tests and every release can be
linked to its executed evidence.
- Isolation: failures in integrations, automation or presentation do not silently alter authoritative
case state.
- Reproducibility: a historical release and its test environment can be reconstructed sufficiently to
reproduce critical decisions and defects.
- Usability without persuasion: interfaces present evidence and findings neutrally without
nudging reviewers toward a desired outcome.
- Resilience: degraded conditions preserve integrity and fail safely rather than bypassing controls.
## 20.3 Verification Layers
Layer Primary purpose Required evidence
Static verification Detect defects before
execution
Lint, type checks, schema
checks, dependency policy,
architecture tests
Unit verification Prove local domain rules
Deterministic unit tests,
mutation score where
valuable, boundary cases
Component verification
Prove service behavior with
real adapters or faithful
substitutes
Contract tests, persistence
tests, authorization tests
Integration verification Prove interactions across
services and infrastructure
Broker, database, object store,
identity and signing

<!-- Controlled source page 129 -->

Layer Primary purpose Required evidence
integration tests
End-to-end verification Prove governed user journeys
Recorded scenarios from
intake through report
publication and appeal
Operational verification Prove recovery and support
procedures
Backup restore, failover,
rollback, incident and access-
revocation exercises
Governance verification Prove constitutional and
methodological constraints
Negative tests for bias,
override, conflicts, quorum
and evidence substitution
## 20.4 Requirements Traceability
The quality system shall maintain a bidirectional traceability model. Every normative requirement
must reference its verification method, and every automated or manual test must identify the
requirement or risk it verifies. Orphan requirements and orphan tests are release defects.
**RBE-TST-010** Every SHALL requirement in the frozen architecture SHALL have a verification status of
automated, manually verified, deferred with approved rationale, or not applicable with approved
rationale.
**RBE-TST-011** The release candidate SHALL include a machine-readable requirements traceability
matrix identifying requirement ID, test ID, test type, execution result, environment, build identifier
and evidence location.
**RBE-TST-012** A failed constitutional, evidence-integrity, authorization, audit or separation-of-duties test
SHALL block release regardless of aggregate pass rate.
## 20.5 Domain and State-Machine Testing
The state machine defined in Chapter 8 is authoritative. Tests must prove both allowed transitions
and prohibited transitions. Property-based and model-based techniques should be used for
transition sequences that are difficult to enumerate manually.
- Every state has verified entry and exit invariants.
- Every transition is tested for correct authority, preconditions, side effects and audit events.
- Invalid transitions fail atomically and leave no partial authoritative change.
- Retries and duplicate commands do not create duplicate assignments, findings, decisions or
reports.
- Appeal and re-review create new governed records rather than rewriting historical decisions.
- Concurrency tests cover competing reviewer submissions, evidence locking and decision
finalization.
**RBE-TST-020** The test suite SHALL prove that no command can move a case directly to a final outcome
while bypassing mandatory review or challenge stages.

<!-- Controlled source page 130 -->

**RBE-TST-021** State-machine tests SHALL include randomized valid and invalid command sequences and
SHALL verify invariants after every operation.
## 20.6 Decision and Reasoning Verification
Decision tests must verify the decision framework rather than merely assert status labels. Test
fixtures shall include evidence packages that justify each permitted outcome and adversarial
packages that appear commercially attractive but fail methodological or evidential requirements.
- PASS cannot be produced when a mandatory methodological control fails.
- Commercial value cannot compensate for insufficient evidence.
- INSUFFICIENT EVIDENCE is available without penalty or artificial escalation pressure.
- FAIL requires explicit, traceable reasoning rather than a bare status.
- PASS WITH FINDINGS preserves unresolved findings and follow-up obligations.
- DEFER records the unresolved question and the evidence or action required to continue.
- Decision assembly never invents a finding absent from authoritative reviewer assessments.
**RBE-TST-030** Golden decision fixtures SHALL be reviewed by governance owners and SHALL represent
all decision classes, material boundary conditions and known anti-patterns.
**RBE-TST-031** Changes to decision rules SHALL require regression execution against all golden fixtures
and explicit review of every changed result.
## 20.7 Authorization and Separation-of-Duties Testing
Authorization tests shall operate at the authoritative command boundary. They must test actor
identity, role, assignment, conflict status, case state, object classification and contextual restrictions
in combination.
Scenario Expected behavior
Unassigned reviewer submits assessment Reject and audit denial
Conflicted reviewer accesses restricted case Reject; record conflict control event
Administrator attempts substantive decision Reject regardless of technical privilege
Reviewer attempts to approve own assignment
change Reject under separation of duties
Chair finalizes without quorum Reject and preserve pending state
AI service attempts to issue decision Reject; AI has no substantive authority
Expired elevated privilege performs export Reject and require new authorization
**RBE-TST-040** Authorization regression tests SHALL execute against every mutating command and every
protected read path.
**RBE-TST-041** The quality gate SHALL include explicit tests proving that generic administrative access
cannot override substantive governance rules.
## 20.8 Evidence Integrity and Provenance Testing
- Hash verification on ingestion, retrieval, export and archival restore.

<!-- Controlled source page 131 -->

- Chain-of-custody preservation through transformations, redactions and derived artefacts.
- Immutability of evidence versions used by finalized reviews.
- Failure on missing, substituted or mismatched evidence identifiers.
- Reconstruction of a decision report from authoritative records and versioned templates.
- Independent validation of signed reports and provenance manifests.
- Detection of tampered audit segments or altered report packages.
**RBE-TST-050** The test suite SHALL prove that changing an evidence object after evidence lock cannot
silently change the evidence set associated with a review.
**RBE-TST-051** A full provenance replay test SHALL reconstruct at least one representative case from
audit events, governed records and immutable artefacts in every release candidate environment.
## 20.9 API, Contract and Schema Testing
Interfaces defined in Chapter 13 and event contracts defined in Chapter 15 shall be versioned and
tested independently of implementation language. Consumer-driven contract tests may supplement
but shall not replace provider conformance tests against the normative schemas.
- Backward-compatible schema evolution for supported versions.
- Rejection of unknown or invalid substantive fields where permissive parsing would be unsafe.
- Idempotency-key behavior and duplicate-request replay.
- Correlation, causation and actor metadata propagation.
- Consistent error taxonomy without disclosure of protected content.
- Event ordering and outbox publication guarantees.
- Compatibility tests for report manifests and machine-readable decision outputs.
**RBE-TST-060** Breaking contract changes SHALL require a new version, migration plan and coexistence
period or explicit coordinated cutover approval.
## 20.10 Security Testing
Security testing shall implement the assurance requirements of Chapter 16 and include automated
and human-led techniques. Passing scanners alone is insufficient.
- Static application security testing and secret detection.
- Dependency, container and infrastructure vulnerability scanning.
- Dynamic and API security testing in an isolated environment.
- Penetration testing before initial production and after material boundary changes.
- Abuse-case testing for privileged access, evidence export, report signing and break-glass use.
- Supply-chain verification from source commit to deployed artefact.
- Remediation verification and regression tests for security defects.
**RBE-TST-070** Critical security findings affecting evidence integrity, decision authority, authentication,
authorization or signing SHALL block production release until remediated or formally accepted by
designated security and governance authorities.
## 20.11 AI and Automation Testing
AI-assisted capabilities are non-authoritative. Testing must demonstrate that model output is
bounded, attributable and incapable of becoming a decision without the required human and
domain controls.

<!-- Controlled source page 132 -->

- Prompt-injection and hostile-evidence tests.
- Hallucination and unsupported-citation detection.
- Data-minimization and prohibited-data leakage tests.
- Model and prompt version traceability.
- Deterministic fallback when the model is unavailable or output fails validation.
- Human-review enforcement for AI-produced summaries, suggested challenges and
classifications.
- Bias evaluation focused on whether presentation or ranking changes reviewer treatment of
equivalent evidence.
**RBE-TST-080** No AI test fixture SHALL be accepted as proving decision correctness unless the
authoritative non-AI decision rules and human approvals are also verified.
**RBE-TST-081** The system SHALL test that AI output cannot directly mutate evidence, findings, reviewer
assessments, decisions or signed reports.
## 20.12 Performance, Reliability and Recovery Testing
Performance tests shall use representative case sizes, evidence volumes, concurrent reviewers and
report-generation workloads. Reliability tests must verify safe behavior under partial failure.
Test class Minimum concern
Load Expected concurrent review and evidence-
access demand
Stress Behavior beyond planned capacity and
controlled rejection
Soak Resource leakage and queue accumulation
over extended operation
Chaos/fault injection Database, broker, object store, identity and
network failure
Recovery Restore, point-in-time recovery and
provenance validation
Deployment Rolling or blue-green promotion without
governance inconsistency
**RBE-TST-090** Recovery testing SHALL verify not only service availability but also consistency of case
state, evidence references, audit history and signed outputs.
## 20.13 Test Data Governance
Test data shall be synthetic by default. Production evidence or personal data may be used only
under explicit approval, minimization, isolation and destruction controls. Synthetic fixtures must
still preserve realistic structural complexity.
**RBE-TST-100** Production secrets and unrestricted production evidence SHALL NOT be copied into test
environments.

<!-- Controlled source page 133 -->

**RBE-TST-101** Test fixtures used as normative golden cases SHALL be version-controlled, reviewed and
immutable within a released test baseline.
## 20.14 Environments and Test Independence
- Unit and component tests must run without dependence on shared mutable environments.
- Integration environments shall be reproducible from infrastructure and configuration
definitions.
- Acceptance tests shall execute against the same build artefact intended for promotion.
- Environment-specific configuration shall be injected and separately validated.
- Test execution identities shall have no unrecorded production privilege.
- Clock, randomness and external dependencies shall be controllable where determinism is
required.
**RBE-TST-110** A release SHALL NOT be certified using a build artefact different from the artefact
promoted to production.
## 20.15 Defect Classification and Release Gates
Severity Definition Release effect
Blocker
Constitutional breach,
decision corruption, evidence
loss, audit compromise or
unauthorized substantive
action
Release prohibited
Critical
Material security, availability
or data-integrity failure with
no acceptable control
Release prohibited
Major
Significant function fails or
governance assurance
incomplete
Requires remediation or
approved deferral
Minor
Limited impact with safe
workaround and no
governance compromise
May proceed with tracked
remediation
Observation
Improvement or risk not
presently causing non-
conformance
Record and prioritize
**RBE-TST-120** Release approval SHALL be evidence-based and SHALL identify all open defects, risk
acceptances, deferred tests and accountable owners.
## 20.16 Quality Evidence Package
- Build and source identifiers.
- Software bill of materials and attestations.
- Requirements traceability matrix.

<!-- Controlled source page 134 -->

- Automated test results and coverage summaries.
- Manual test records and reviewer approvals.
- Security assessment and vulnerability status.
- Performance and recovery results.
- Known defects, exceptions and risk acceptances.
- Architecture-conformance report.
- Final release recommendation with independent sign-off.
**RBE-TST-130** Quality evidence SHALL be retained as a versioned release artefact and SHALL remain
independently verifiable after the release is superseded.
## 20.17 Architecture Conformance Tests
Architecture rules that can be expressed mechanically should be enforced mechanically. Examples
include dependency direction, forbidden module imports, access to authoritative persistence, event
publication through the outbox, use of approved identity libraries and prohibition of AI modules
from decision command handlers.
**RBE-TST-140** The CI pipeline SHALL fail when code violates mechanically enforceable architecture
boundaries.
**RBE-TST-141** Architecture tests SHALL be maintained as production code and reviewed whenever
module boundaries or service responsibilities change.
## 20.18 Chapter 20 Codex Build Contract
- Codex may generate tests, fixtures and quality tooling only within frozen architectural
boundaries.
- Codex shall not weaken assertions merely to make a pipeline pass.
- Codex shall not replace negative governance tests with mocked success paths.
- Codex shall preserve requirement IDs in test names or metadata.
- Codex shall surface ambiguous requirements rather than infer an outcome-favouring
interpretation.
- Codex-generated test data shall contain no real secrets or personal data.
- Any proposed removal of a test protecting a constitutional principle requires explicit human
architecture approval.
**RBE-TST-150** Automated coding agents SHALL treat failing governance and integrity tests as evidence of
a defect, not as obstacles to be bypassed.
## 20.19 Section Freeze Conditions
- The requirements traceability model is approved.
- All decision classes and state transitions have normative verification coverage.
- Separation-of-duties and AI-boundary negative tests are defined.
- Release blockers and risk-acceptance authorities are named.
- Recovery and provenance replay tests are specified.
- The Codex build contract is accepted by architecture and engineering owners.

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

# 22. Implementation Guidance and Codex Build Contract

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 142 -->

## 22.1 Purpose
This chapter converts the reference architecture into explicit implementation constraints for human
engineers and coding agents. Its purpose is to minimize architectural invention during build,
prevent convenience-driven erosion of governance, and provide Codex with a bounded contract:
implement the approved architecture, expose ambiguity, and never manufacture substantive policy.
**RBE-IMP-001** Implementation SHALL conform to the frozen architecture and SHALL NOT infer new
decision authority, governance policy or evidence standards from UI requirements or example data.
**RBE-IMP-002** Codex and other coding agents SHALL stop and surface ambiguity when a requested
implementation could change substantive review meaning or violate a constitutional principle.
## 22.2 Order of Authority
44. Constitutional principles.
45. Frozen Review Board Methodology and governance rules.
46. Frozen RBE-001 Reference Architecture requirements.
47. Approved architecture decision records and schemas.
48. Approved implementation plan and acceptance criteria.
49. Code, tests and operational documentation.
A lower-ranked artefact cannot override a higher-ranked artefact. Example data, screenshots,
prototypes and convenience functions are non-authoritative unless explicitly incorporated into a
governed specification.
**RBE-IMP-010** When implementation artefacts conflict, the higher-order authority SHALL prevail and
the inconsistency SHALL be recorded for correction.
## 22.3 Repository and Module Structure
The repository should make architectural boundaries visible. Exact language and framework
choices may vary, but dependency direction and authority boundaries are normative.
Recommended top-level structure:
/apps
/api
/reviewer-web
/admin-web
/workers
/reporting
/integration
/automation
/domain
/cases
/reviews
/decisions
/evidence

<!-- Controlled source page 143 -->

/audit
/application
/commands
/queries
/policies
/contracts
/api
/events
/reports
/infrastructure
/persistence
/messaging
/identity
/observability
/tests
/unit
/component
/integration
/acceptance
/architecture
/docs
/adr
/runbooks
/schemas
**RBE-IMP-020** Domain modules SHALL NOT depend on UI frameworks, transport protocols, persistence
implementations, message brokers, AI SDKs or deployment tooling.
**RBE-IMP-021** Only designated infrastructure adapters SHALL access authoritative databases, object
stores, message brokers, key services or external integrations.
## 22.4 Domain Modeling Rules
- Use explicit domain types for case IDs, evidence IDs, reviewer IDs, methodology versions,
decision classes and hashes.
- Enforce invariants within aggregate or domain-service boundaries, not solely in controllers or UI
validation.
- Represent decisions and findings as immutable versioned records after finalization.
- Represent amendments, appeals and re-reviews as new governed records linked to history.
- Avoid generic status strings when a closed, versioned enumeration is required.
- Do not embed presentation labels as decision logic.
- Make actor, authority, causation and correlation explicit in substantive commands.
**RBE-IMP-030** A domain object SHALL NOT expose a mutation that can place it in a state prohibited by
the Chapter 8 state machine.

<!-- Controlled source page 144 -->

## 22.5 Command and Query Implementation
Commands express intent to change authoritative state and must be validated, authorized, executed
atomically and audited. Queries retrieve information and must apply classification and access policy
without producing side effects.
**RBE-IMP-040** Every substantive command handler SHALL perform schema validation, authentication
context validation, authorization, state/precondition validation, domain execution, durable
persistence and audit/outbox recording in a controlled transaction boundary.
**RBE-IMP-041** Command handlers SHALL be idempotent where client or infrastructure retry is possible.
**RBE-IMP-042** Queries SHALL NOT silently repair, finalize or otherwise mutate authoritative state.
## 22.6 Persistence Rules
- Use migrations; never mutate production schema manually as ordinary practice.
- Preserve immutable historical rows or version records for finalized governance data.
- Use optimistic concurrency or equivalent protection for competing substantive updates.
- Store evidence binaries outside ordinary relational rows while retaining authoritative metadata
and hashes.
- Publish events from a transactional outbox or equivalent atomic mechanism.
- Do not use caches as authoritative stores.
- Do not cascade-delete records required for provenance or reconstruction.
**RBE-IMP-050** Persistence code SHALL preserve the audit and provenance semantics defined in Chapters
10 and 14 even when the underlying technology changes.
## 22.7 API Rules
- Use versioned, explicit request and response schemas.
- Use stable identifiers rather than display names as references.
- Return a controlled error taxonomy.
- Propagate correlation and causation identifiers.
- Never trust client-supplied role, outcome, reviewer eligibility or audit metadata.
- Use pagination and bounded export for large collections.
- Generate API documentation from normative schemas where possible.
- Protect substantive endpoints with contextual authorization, not route-level role checks alone.
**RBE-IMP-060** The API SHALL NOT expose an endpoint whose purpose is to force a decision, rewrite final
history, bypass quorum or suppress required findings.
## 22.8 Event and Orchestration Rules
Events describe facts that have occurred. Commands request change. The two shall not be confused.
Orchestrators coordinate approved processes but may not invent substantive findings or decisions.
- Events are immutable, versioned and attributable.
- Consumers are idempotent and tolerate duplicate delivery.
- Ordering assumptions are explicit and limited to documented scopes.
- Poison messages enter controlled dead-letter handling with replay evidence.
- Orchestration state is observable and recoverable.
- External integration failure cannot corrupt authoritative case state.

<!-- Controlled source page 145 -->

- No workflow engine configuration may bypass domain validation.
**RBE-IMP-070** Every event representing a substantive state change SHALL originate from an
authoritative domain transaction and carry sufficient identifiers for provenance reconstruction.
## 22.9 Security Implementation Rules
- Deny by default.
- Use managed identity and short-lived credentials.
- Keep secrets outside code, images and ordinary configuration repositories.
- Validate issuer, audience, expiry and revocation of identity assertions.
- Apply authorization at the domain/application boundary.
- Record privileged actions and policy decisions without leaking protected content.
- Use approved cryptography and centralized key management.
- Quarantine and validate evidence files before authoritative ingestion.
**RBE-IMP-080** No code path, test helper or administrative utility SHALL introduce a permanent
universal bypass of authorization or governance policy.
## 22.10 AI and Automation Implementation Rules
AI modules are advisory adapters. They may summarize, classify, extract, suggest challenges or
identify possible inconsistencies, but their output is untrusted until validated and accepted by an
authorized human or deterministic control.
- Isolate AI SDKs and prompt logic from authoritative domain modules.
- Version model, provider, prompt, tool configuration and safety policy.
- Minimize and classify data sent to models.
- Treat evidence content as untrusted input capable of prompt injection.
- Require schema-constrained output where structured output is needed.
- Capture citations or source references for factual suggestions.
- Provide deterministic fallback and graceful unavailability.
- Never auto-convert a model suggestion into a finding, score or decision.
**RBE-IMP-090** AI output SHALL be stored as attributed advisory material distinct from reviewer-
authored and Board-authoritative records.
**RBE-IMP-091** An AI component SHALL NOT possess credentials capable of finalizing decisions, signing
reports, changing methodology or altering immutable evidence.
## 22.11 User Interface Implementation Rules
The UI shall support clarity, completeness and neutral review. It must not communicate that one
outcome is preferred or reward reviewers for approval or rejection volume.
- Present decision options with equivalent visual weight.
- Show evidence provenance and methodology version near substantive assessments.
- Require explicit reasoning and references before submission.
- Show unresolved conflicts, missing evidence and policy denials clearly.
- Prevent hidden defaults from selecting a substantive outcome.
- Distinguish saved draft, submitted assessment and finalized Board decision.
- Expose AI-generated material as AI-generated and unaccepted.

<!-- Controlled source page 146 -->

- Provide accessible navigation, labels and keyboard operation.
**RBE-IMP-100** The UI SHALL NOT preselect PASS, FAIL or any substantive outcome.
**RBE-IMP-101** Neutral presentation requirements SHALL be covered by acceptance and usability testing.
## 22.12 Coding Standards
- Use the project language formatter and static analysis in CI.
- Prefer explicit, readable code over clever abstraction.
- Keep functions and modules cohesive and bounded.
- Use structured logging with stable event names.
- Handle errors deliberately; do not swallow failures affecting integrity.
- Use typed schemas at external and domain boundaries.
- Document non-obvious governance rules with requirement IDs.
- No TODO may defer a mandatory control without a tracked issue and approved release decision.
**RBE-IMP-110** Code implementing substantive governance rules SHALL reference the relevant
requirement or approved decision record in tests or documentation.
## 22.13 Logging and Error Handling
Logs support operations and security but are not substitutes for the immutable audit model. Errors
must be observable and safe, with internal detail available to authorized operators and neutral
messages presented to users.
**RBE-IMP-120** The application SHALL NOT log raw secrets, unrestricted evidence content, authentication
tokens or unnecessary personal data.
**RBE-IMP-121** Failures after a substantive command is accepted SHALL resolve to a known durable state
and SHALL be recoverable without double application.
## 22.14 Migration and Compatibility Rules
- Database changes use forward-reviewed migrations and tested rollback or roll-forward strategy.
- Contract changes identify compatibility impact and supported versions.
- Historical records retain original methodology, policy, schema and template references.
- Data backfills are idempotent, attributable and verified.
- Migrations affecting hashes, signatures or provenance require independent validation.
- Production migration scripts are immutable release artefacts.
**RBE-IMP-130** A migration SHALL NOT reinterpret historical substantive data under a new methodology
or decision rule unless a governed re-review explicitly requires it.
## 22.15 Feature Delivery Sequence
50. Foundation: identifiers, identity context, policy enforcement and audit primitives.
51. Case intake and immutable evidence package handling.
52. Reviewer eligibility, conflicts and assignment.
53. Independent assessments and challenge workflow.
54. Decision assembly and finalization.
55. Report generation, signing and publication.
56. Appeal and re-review.

<!-- Controlled source page 147 -->

57. Integrations and advisory AI capabilities.
58. Advanced reporting, analytics and operational optimization.
This sequence prioritizes trustworthy governance over dashboards, demonstrations or artificial data
volume.
## 22.16 Pull Request and Review Requirements
- Linked issue, requirement and architecture context.
- Description of domain and data impact.
- Tests proving positive and negative behavior.
- Security and privacy considerations.
- Migration and rollback considerations.
- UI screenshots only as supplementary evidence, never as proof of domain correctness.
- Independent review for governance-significant changes.
- No self-approval for changes to authorization, decision, evidence or audit controls.
**RBE-IMP-140** Changes affecting constitutional controls, decision authority, evidence integrity or audit
semantics SHALL require review by both engineering and designated governance or architecture
authority.
## 22.17 Codex Task Packet
Every Codex task should contain enough context to prevent architectural invention. The minimum
task packet is:
- Task objective and non-goals.
- Applicable requirement IDs.
- Authoritative domain entities and states.
- Permitted modules to change.
- Forbidden changes and invariants.
- Input/output or contract schema.
- Acceptance tests, including negative cases.
- Data and security classification.
- Migration or compatibility expectations.
- Expected documentation and audit updates.
**RBE-IMP-150** Codex SHALL NOT be instructed with outcome-only prompts such as “make the test pass”
or “add an approve button” without the governing requirements and constraints.
## 22.18 Codex Prohibited Inferences
Codex must not infer Required response
That PASS is the preferred outcome Maintain neutral outcome model
That missing evidence may be replaced by
plausible synthetic evidence Stop and report insufficient source material
That administrators may override governance Reject and request architecture clarification
That AI output is authoritative Store as advisory only

<!-- Controlled source page 148 -->

Codex must not infer Required response
That a prototype screenshot defines policy Use frozen requirements and schemas
That historical records may be rewritten for
simplicity Implement versioned amendment or re-review
That a failed integrity test may be disabled Treat as a blocking defect
## 22.19 Definition of Done
- Implementation satisfies stated requirements and acceptance criteria.
- Positive, negative, authorization and failure tests pass.
- Architecture conformance tests pass.
- Contracts, schemas and migrations are versioned.
- Observability and audit events are present and validated.
- Security and privacy review is complete where applicable.
- Runbooks and operational impacts are updated.
- No unresolved blocker or critical defect remains.
- Generated artefacts are reproducible from source.
- Principal engineer and required governance reviewers approve the change.
## 22.20 Architecture Exception Process
An implementation may not silently diverge from the architecture. A proposed exception must
identify the requirement, reason, alternatives, risk, duration, compensating controls, owner and
closure date. Constitutional principles are not eligible for ordinary exception.
**RBE-IMP-160** Architecture exceptions SHALL be explicit, time-bounded, versioned and approved before
release; undocumented divergence is a defect.
## 22.21 Section Freeze Conditions
- Repository and dependency boundaries are approved.
- Command, persistence, event and AI implementation rules align with Chapters 12–17.
- Codex task packet and prohibited-inference rules are accepted.
- Definition of done and review authorities are named.
- Architecture-exception process is operational.
- No implementation instruction contradicts the constitutional principles.

# 23. Appendices and Normative Reference Material

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 149 -->

## 23.1 Purpose and Status
This chapter consolidates the vocabulary, identifiers, decision references, control matrices and
handoff material required to use the architecture consistently. Unless explicitly marked informative,
the appendices are normative and form part of RBE-001.
**RBE-APP-001** Implementations and operating procedures SHALL use the canonical terms and identifiers
defined in this chapter or provide an approved mapping.
## 23.2 Canonical Glossary
Term Canonical meaning
Appeal
A governed request to review whether a
finalized decision or procedure should be
reconsidered under the permitted appeal
grounds.
Assessment A reviewer-authored, role-bounded evaluation
of a defined review dimension.
Audit event An immutable record of an attributable action,
state change or control decision.
Board decision
The finalized governance outcome produced
after required reviews, challenge and
authority checks.
Case The governed unit submitted to the Review
Board for evaluation.
Challenge
A mandatory attempt to identify contradictory
evidence, invalid assumptions or unsupported
reasoning.
Conflict of interest
A relationship or circumstance that could
reasonably impair or appear to impair
reviewer independence.
Decision class PASS, PASS WITH FINDINGS, FAIL, DEFER or
INSUFFICIENT EVIDENCE.
Evidence package The versioned, integrity-protected set of
evidence available to a review.
Finding A material, evidence-linked conclusion
requiring recognition, response or follow-up.
Golden fixture A reviewed test case used to detect unintended
changes in decision or governance behavior.
Governed record A record subject to immutability, provenance,

<!-- Controlled source page 150 -->

Term Canonical meaning
authorization and retention controls.
Methodology The approved rules that define how evidence is
gathered, assessed and interpreted.
Observation
A relevant note that does not independently
determine the decision or create a mandatory
action.
Recommendation
A proposed action supported by a justified
decision; not an authority to bypass the
decision framework.
Re-review
A new review session linked to a historical
case, using explicitly identified evidence and
methodology versions.
Reviewer An eligible person assigned a bounded review
function.
Substantive action
An action that can affect evidence, findings,
assessments, decisions, reports or governance
validity.
Traceability
The ability to connect a conclusion to evidence,
reasoning, methodology, actors, versions and
actions.
Version
An immutable identified state of a
methodology, policy, schema, template,
evidence object or governed record.
## 23.3 Acronyms and Identifiers
Identifier Meaning
RBE Review Board Engine
RBM Review Board Methodology
SoD Separation of Duties
RBAC Role-Based Access Control
ABAC Attribute-Based Access Control
ADR Architecture Decision Record
API Application Programming Interface
SLO Service-Level Objective
RPO Recovery Point Objective

<!-- Controlled source page 151 -->

Identifier Meaning
RTO Recovery Time Objective
CI/CD Continuous Integration / Continuous Delivery
SBOM Software Bill of Materials
PII Personally Identifiable Information
MFA Multi-Factor Authentication
KMS Key Management Service
IaC Infrastructure as Code
## 23.4 Constitutional Principles — Canonical Text
59. The Review Board has no interest in whether a proposal succeeds or fails. Its sole responsibility
is to determine whether the conclusion presented is justified by the evidence, reasoning, and
methodology.
60. The burden of justification rests with the conclusion, not with its critics. Every recommendation
must earn approval through evidence, reasoning, and methodological compliance. No proposal
is approved because it appears plausible, desirable, or commercially attractive.
61. Every decision shall be reproducible. An independent Review Board, applying the same
approved methodology to the same evidence, should be able to understand how the decision was
reached and, where appropriate, arrive at a compatible conclusion.
**RBE-APP-010** The canonical wording above SHALL be preserved in the master architecture unless
amended through explicit constitutional governance.
## 23.5 Decision-Class Reference
Decision Core meaning What it does not mean
PASS
The presented conclusion is
justified to the required
standard.
The proposal is guaranteed to
succeed or is commercially
mandatory.
PASS WITH FINDINGS
The conclusion is justified, but
material findings or
obligations remain.
Findings may be ignored
because the overall result
passed.
FAIL
The presented conclusion is
not justified or a mandatory
requirement is breached.
The underlying opportunity or
idea can never become valid.
DEFER
A decision cannot responsibly
be finalized until a defined
action, clarification or
dependency is resolved.
The Board is avoiding an
unfavorable outcome.

<!-- Controlled source page 152 -->

Decision Core meaning What it does not mean
INSUFFICIENT EVIDENCE
The available evidence cannot
justify the presented
conclusion.
The conclusion is false; only
that it is not presently
justified.
## 23.6 Review-Function Separation Reference
Function Question answered Prohibited substitution
Methodology Review Was the approved
methodology followed?
Cannot decide commercial
attractiveness.
Evidence Review
Is the evidence sufficient,
independent, relevant and
traceable?
Cannot repair missing
evidence with assumptions.
Reasoning Review Do conclusions logically follow
from evidence?
Cannot change evidence or
methodology.
Challenge Review
What contradicts the
conclusion or would change
it?
Cannot advocate for a
predetermined outcome.
Commercial Review If valid, is the finding
commercially meaningful?
Cannot override weak
evidence or reasoning.
Governance Review
Can Provena defensibly stand
behind the process and
decision?
Cannot rewrite specialist
assessments.
Decision Assembly
What outcome follows from
authoritative assessments and
rules?
Cannot invent findings or
suppress dissent.
## 23.7 High-Level State Reference
State family Representative states Invariant
Intake Registered, validating, rejected No substantive review before
minimum intake validity.
Evidence Evidence open, locked,
amended
Review uses an identified
immutable evidence set.
Assignment Awaiting assignment,
assigned, conflict resolution
Only eligible, conflict-cleared
reviewers participate.
Review Independent reviews active,
challenge active
Required functions remain
separated and attributable.

<!-- Controlled source page 153 -->

State family Representative states Invariant
Decision Assembly, quorum check,
pending finalization
No final outcome before all
mandatory controls pass.
Publication Finalized, report generated,
published
Final history is immutable and
signed where required.
Post-decision Appeal open, re-review,
archived
Historical decision remains
preserved.
## 23.8 Role and Authority Summary
Role Permitted authority Explicit prohibition
Intake Officer
Validate submission
completeness and register
case
Cannot make substantive
findings or decisions
Methodology Reviewer Assess methodology
compliance
Cannot decide evidence
sufficiency outside assigned
scope
Evidence Reviewer Assess evidence quality and
sufficiency
Cannot substitute or
manufacture evidence
Reasoning Reviewer Assess logical support Cannot change methodology
or evidence
Commercial Reviewer Assess commercial relevance
of validated findings
Cannot compensate for invalid
evidence
Governance Reviewer Assess procedural
defensibility
Cannot rewrite specialist
assessments
Board Chair Coordinate quorum and
finalization
Cannot unilaterally force
outcome
Administrator Operate platform and
identities
Cannot perform substantive
Board action by privilege
Auditor Read governed history and
verify controls Cannot mutate case state
AI Service Provide bounded advisory
output
Cannot decide, sign, assign or
mutate authoritative records
## 23.9 Core Traceability Chain
The minimum traceability chain is:

<!-- Controlled source page 154 -->

Decision  Decision rationale  Findings and dissent  Reviewer assessments  Evidence references → → → →
and versions  Evidence provenance and integrity  Methodology and policy versions  Actor and → → →
authority  State transitions and audit events  Signed report and release artefacts→ →
**RBE-APP-020** A finalized decision SHALL be considered non-conformant if any mandatory link in the
traceability chain cannot be resolved and verified.
## 23.10 Requirement Identifier Convention
Requirement identifiers use the format RBE-[DOMAIN]-NNN. Domain prefixes include DOC, GOV,
LIF, DEC, DOM, STM, IAM, AUD, REP, SYS, API, DAT, EVT, SEC, AIA, REL, INF, TST, OPS, IMP and APP.
Identifiers are immutable after publication. Withdrawn requirements remain reserved and are
marked withdrawn rather than reused.
**RBE-APP-030** Requirement identifiers SHALL NOT be renumbered for cosmetic convenience after the
master document is published.
## 23.11 Architecture Decision Record Template
Field Required content
ADR ID and title Stable identifier and concise decision name
Status Proposed, accepted, superseded, rejected or
withdrawn
Context Problem, constraints and applicable
requirements
Decision The chosen architecture and its boundaries
Alternatives Material alternatives considered
Consequences Positive, negative, risks and operational impact
Governance impact Effect on evidence, independence, decisions,
audit or constitutional principles
Migration Adoption, coexistence, rollback and data
implications
Verification Tests and evidence required
Approvals Architecture, engineering, security and
governance authorities as applicable
## 23.12 Architecture Exception Template
Field Required content
Exception ID Stable identifier
Requirement affected Exact requirement or boundary
Reason Why conformance is presently infeasible

<!-- Controlled source page 155 -->

Field Required content
Alternatives assessed Options and reasons rejected
Risk Technical, security and governance risk
Compensating controls Temporary protections
Owner Accountable person
Approval Required authorities
Expiry Mandatory closure or renewal date
Closure evidence Proof of remediation or approved replacement
## 23.13 Codex Task Template
Task field Required content
Objective Specific implementation result
Non-goals What must not be changed
Requirements Applicable RBE/RBM identifiers
Architecture context Modules, services, states and contracts
Permitted files Expected change boundary
Forbidden changes Constitutional and domain invariants
Inputs/outputs Schemas and examples clearly marked non-
authoritative
Acceptance tests Positive, negative, authorization and failure
cases
Security/data Classification and secret handling
Migration Compatibility and rollback
Documentation ADR, schema, runbook and comments
Stop conditions Ambiguities requiring human decision
## 23.14 Master Document Assembly Rules
- Sections 1–23 shall be merged into one authoritative document after sectional review.
- Heading numbering, requirement identifiers and cross-references shall be reconciled.
- Duplicate constitutional text may remain where useful, but canonical wording must not drift.
- Contradictions are resolved before publication, not hidden through editorial smoothing.
- A consolidated contents table, glossary and requirement index shall be generated.
- Diagrams and tables shall carry stable captions or identifiers.
- Sectional release covers shall be removed from the master version.

<!-- Controlled source page 156 -->

- The final document shall be rendered and visually inspected page by page.
- The final master shall receive principal-architect and principal-engineer approval.
**RBE-APP-040** The master document SHALL NOT be declared final while unresolved cross-section
contradictions, broken references or undefined normative terms remain.
## 23.15 Final Architecture Review Checklist
Review area Acceptance question
Constitution Does every chapter preserve outcome
neutrality and burden of justification?
Methodology Can implementation rules be traced to an
approved methodology or governance rule?
Separation Can any individual role or technical privilege
force an outcome?
Evidence Is the exact reviewed evidence set immutable
and reconstructable?
Decision Are all decision classes explicit, justified and
neutrally presented?
Audit
Can an independent party reconstruct who did
what, when, under which authority and
version?
Security Do controls protect evidential and decision
integrity, not merely confidentiality?
AI Is AI advisory, bounded and incapable of
substantive authority?
Operations Do degraded and emergency procedures fail
safely?
Testing Are constitutional and governance controls
proven by negative tests?
Codex Can a coding agent implement without
inventing policy?
Publication Are reports verifiable, versioned and linked to
provenance?
## 23.16 Historical v1.0.0 Source Disposition

Controlled source pages 157-159 contained the v1.0.0 master-review open items, publication
certification, and controlled limitations. They remain historical evidence under source checksum
`0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31` but do not transfer
approval to this candidate.

Their unresolved items are dispositioned as follows:

- reviewer combination and quorum rules remain ACTIVE-methodology responsibilities;
- retention, privacy, SLO, RPO/RTO, identity, cryptography, and publication audiences remain
  production deployment gates;
- requirement-to-test traceability remains an implementation acceptance artifact;
- the cross-chapter entity/event glossary and final diagrams remain controlled publication
  dependencies and must not be invented by implementation code;
- the historical `APPROVED FOR CONTROLLED ENGINEERING USE` statement applies only to v1.0.0 and
  is not a human approval record for v1.1.0.

<!-- Controlled source pages 157-159: historical certification disposition -->

## 23.17 Normalization Resolution Register

The v1.1.0 normalization candidate resolves the master-document assembly questions as follows:

- Chapter 8 is the only authoritative case state machine.
- Chapter 6 is the canonical outcome taxonomy; process statuses are not verdicts.
- Architecture requirement IDs retain `RBE-[DOMAIN]-NNN` ownership.
- Engineering requirements use `RBE-ES-[DOMAIN]-NNN` and are linked through the
  requirement migration register.
- RBE-001 is the methodology-neutral constitutional and execution architecture.
- A methodology profile, including RBM-001, becomes operational only after a named human
  authority approves and activates a versioned release.
- The local SQLite engineering profile is a foundation profile and cannot claim production
  conformance or issue binding live decisions.

Deployment-specific values for retention, SLO, RPO, RTO, cryptographic profiles, identity
providers, publication audiences, and production topology remain controlled deployment ADRs.
They do not alter the canonical domain semantics and must be approved before production use.

## 23.18 Final Codex Constitutional Contract

Codex is an implementation capability, not a member of the Review Board. It has no desired
case outcome and no authority to decide what should be true. It must implement the architecture
faithfully, preserve evidence and traceability, and expose uncertainty rather than disguise it.

**RBE-APP-050** Codex SHALL NOT fabricate evidence, requirements, reviewer assessments,
methodology rules, approvals, or test results.

**RBE-APP-051** Codex SHALL NOT optimize for a preferred Review Board outcome, approval rate,
rejection rate, or commercial conclusion.

**RBE-APP-052** Codex SHALL treat insufficient evidence and architecture clarification required as
valid outputs rather than failures to complete a task.

## 23.19 Release Gates

- Canonical verdict and process-status registers validate.
- Canonical state-machine register validates.
- Architecture and engineering requirement namespaces do not collide.
- Every superseded v1.0.0 engineering ID has an explicit migration entry.
- Individual Markdown sources and the deterministic ZIP contain identical bytes.
- The principal technical review reports no unresolved architecture blocker.
- A named human Principal Architect must approve operational activation.
- A live Board decision additionally requires an ACTIVE methodology profile.

## 23.20 Normalized Architecture Status

RBE-001 v1.1.0 proposes to supersede the contradictory release metadata and implementation
mappings in v1.0.0. Effective supersession begins only after named human Principal Architect
approval. The v1.0.0 controlled files remain immutable historical artifacts. This normalized
Markdown candidate is technically ready for human approval; it is not evidence of that approval
and does not activate RBM-001 or authorize a live Review Board decision.
