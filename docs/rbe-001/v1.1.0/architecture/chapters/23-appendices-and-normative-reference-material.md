---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 23
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

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
