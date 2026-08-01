# Provena Foundry Review Board — Governing Methodology

**Document ID:** RBM-001
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending named human Principal Architect and Methodology Owner approval before first operational use
**Applicability:** Provena Foundry releases only. This document does not govern GS-P001 or any other Provena product line.
**Architecture Authority:** RBE-001 v1.1.0 or a later approved compatible release
**Profile Definition:** `PROFILE.json`
**Package Manifest:** `MANIFEST.json`
**Human Approval Record:** Not issued
**Last Updated:** 2026-07-19
**Owner:** Provena Foundry Governance

> **Note:** This document is a methodology profile subordinate to the Provena Foundry Review Board Engine (RBE-001) constitution and approved architecture. It is a release candidate. It must not be used for a binding live review until the applicable RBE release is approved, a named human Principal Architect and Methodology Owner approve this exact checksummed package, `PROFILE.json` is updated to `ACTIVE`, and the approved package is tagged. Any release-candidate review is advisory only, must record `binding=false`, and cannot authorise merge, publication, deployment, milestone completion, or invoicing.

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Relationship to GS-P001](#2-relationship-to-gs-p001)
3. [Governing Principles](#3-governing-principles)
4. [Review Board Composition](#4-review-board-composition)
5. [Independence Rules](#5-independence-rules)
6. [Review Trigger Conditions](#6-review-trigger-conditions)
6A. [Review Risk Tiers](#6a-review-risk-tiers)
7. [Input Package Requirements](#7-input-package-requirements)
8. [Evidence Standards](#8-evidence-standards)
9. [Severity Classification](#9-severity-classification)
10. [Process Status and Decision Framework](#10-process-status-and-decision-framework)
11. [Merge-Blocking Rules](#11-merge-blocking-rules)
12. [Disagreement Handling](#12-disagreement-handling)
13. [Finding Lifecycle](#13-finding-lifecycle)
14. [Remediation and Re-Review Process](#14-remediation-and-re-review-process)
15. [Audit Trail Requirements](#15-audit-trail-requirements)
16. [Versioning and Reproducibility](#16-versioning-and-reproducibility)
17. [Required Output Templates and Machine-Readable Schemas](#17-required-output-templates-and-machine-readable-schemas)
18. [Milestone-Completion Criteria](#18-milestone-completion-criteria)
18A. [Appeal and Correction Mechanism](#18a-appeal-and-correction-mechanism)
19. [Reviewer Specification Index](#19-reviewer-specification-index)
20. [Document History](#20-document-history)

---

## 1. Purpose and Scope

### 1.1 Purpose

The Provena Foundry Review Board (the Board) is a governed review function that applies this methodology profile within RBE-001. Once this profile is ACTIVE, it may determine whether a scoped build increment meets the profile threshold before merge, publication, deployment, or milestone completion. While this profile is RELEASE-CANDIDATE, it may be used only for non-binding validation and rehearsal.

The Board exists because:

- Software quality assertions made by the team that produces the software are structurally compromised by confirmation bias, time pressure, and familiarity blindness.
- Commercial commitments depend on accurate, defensible quality signals. A missed defect discovered by a client costs substantially more than the cost of a thorough review.
- Reproducibility and traceability are non-negotiable properties of professional software. Reviews must themselves be traceable and reproducible.
- Honest rejection is more valuable than optimistic approval. A FAIL verdict that prompts correction is a net positive; a PASS verdict that masks a defect is a liability.

### 1.2 Scope

This methodology applies to:

- All pull requests and merge requests targeting protected branches of Provena Foundry repositories.
- All milestone-completion declarations for Provena Foundry.
- All production deployments of Provena Foundry.
- Any change to Provena Foundry that touches security controls, data contracts, public APIs, or commercial commitments.

This methodology explicitly does **not** apply to:

- GS-P001 or any product governed by a separate methodology.
- Internal development branches that have not yet entered formal review.
- Documentation-only changes that carry no functional impact (subject to a Tier 1 lightweight review, not full Board review — see §6A).

### 1.3 Authority and Conformance

The order of authority is:

1. RBE constitutional principles.
2. An approved RBE-001 Reference Architecture release and its normative registers.
3. This methodology profile, but only when its status is `ACTIVE` and its checksum and human approval record validate.
4. Reviewer specifications, templates, schemas, automation, and operational documentation subordinate to this profile.

A lower authority cannot weaken or reinterpret a higher one. If this profile conflicts with RBE-001 in a way that can affect process legitimacy or a substantive outcome, the review is `BLOCKED`, no outcome may be issued, and the conflict must be resolved through a new version. The machine-readable identity, outcome subset, process statuses, role rules, lifecycle mapping, and checksum are declared in `PROFILE.json`.

### 1.4 What the Board Is Not

The Board is not:

- A rubber-stamp process. A review without findings on a non-trivial change is suspicious and must be justified.
- A code review substitute. Developer peer review is a prerequisite, not a replacement.
- An AI opinion oracle. AI tools may assist reviewers in locating evidence but may not substitute for human judgement or generate findings unsupported by verifiable evidence.
- A commercial readiness certification. A Board decision is a governance record, not a warranty of fitness or client acceptance (see §18).

---

## 2. Relationship to GS-P001

GS-P001 is a separate Provena product line with its own governance, methodology, and review processes. This document, all reviewer specifications derived from it, and all Board decisions, finding records, and audit logs produced under it are scoped exclusively to Provena Foundry.

Where Provena Foundry shares infrastructure, libraries, or data pipelines with GS-P001, the reviewer must identify the shared component, note which governance regime owns it, and limit findings to the Provena Foundry usage of that component. Findings must not be raised against GS-P001 assets under this methodology.

If a shared component is found to be defective and that defect originates in GS-P001–governed code, the finding is recorded as an **External Dependency Risk** and escalated through the appropriate GS-P001 channel. The Provena Foundry FAIL/PASS determination must account for the risk but must not conflate the two governance regimes.

---

## 3. Governing Principles

The following principles are non-negotiable and take precedence over convenience, schedule, or reviewer preference.

### P1 — Evidence Quality

Every finding must be supported by specific, verifiable evidence. Evidence must be:

- **Concrete:** A specific file path, line number, log entry, test output, metric value, or document reference.
- **Reproducible:** Any reviewer given the same artefact package and the same evidence pointer must be able to independently verify the finding.
- **Current:** Evidence must refer to the artefact under review, not a previous version or a similar project.

Assertions of the form "this probably has issues" or "this feels wrong" are not findings. They may prompt a reviewer to search for evidence, but they do not become findings until evidence is located.

### P2 — Traceability

Every finding, every decision, and every remediation must be traceable to:

- The specific artefact version under review (commit SHA, build hash, or equivalent immutable identifier).
- The reviewer who raised it.
- The evidence that supports it.
- The resolution applied (if any).

Traceability records are permanent. They must not be deleted, even if a finding is later superseded.

### P3 — Repeatability

A review conducted twice on the same artefact by different reviewers following the same specification must produce materially equivalent results. Where results diverge, the divergence itself must be recorded and resolved through the Disagreement Handling process (§12), not suppressed.

Reviewers must document their method sufficiently that another reviewer can reproduce their conclusions without access to the original reviewer.

### P4 — Commercial Relevance

Findings must be assessed in terms of commercial impact, not merely technical correctness. A technically sub-optimal implementation that carries no commercial risk may be a Minor finding. A technically conformant implementation that creates a commercial liability is at minimum a Major finding.

Commercial relevance includes: client-facing data accuracy, contractual SLA compliance, licensing obligations, data sovereignty, and reputational exposure.

### P5 — Deterministic Decisions

When process status is `READY`, Board decisions must be deterministic given the sealed finding set and evidence-sufficiency record. The decision rules in §10 must produce exactly one permitted substantive outcome. When process status is not `READY`, the outcome must be null. Reviewers and the Board must not override these rules based on schedule pressure, optimism, or qualitative judgement outside the defined framework.

If the decision rules produce an outcome that appears wrong, the correct action is to review the evidence and findings, not to adjust the outcome. If the rules themselves are inadequate, the rules must be amended through the versioning process (§16) before the next review cycle.

Board decisions are not votes. The Board Chair assembles the decision candidate produced by the rules, the Methodology Auditor independently validates governance, and the Board Chair signs the validated result. Neither actor can override a deterministic outcome.

### P6 — Honest Rejection

A FAIL verdict is not a failure of the review process. It is the review process working correctly. Reviewers who consistently find no issues on non-trivial artefacts will be asked to justify their methodology. Reviewers must not moderate finding severity downward to avoid a FAIL verdict.

### P7 — No Fabricated Evidence

Reviewers must not generate, infer, or construct evidence. A missing mandatory Input Package item produces `PROCEDURALLY_INCOMPLETE` before substantive review. An evidentiary gap discovered inside an otherwise procedurally complete package is recorded as an **Evidence Gap** with supporting evidence of the gap. If the sealed record cannot support a defensible substantive conclusion and no confirmed defect independently controls the result, the outcome is `INSUFFICIENT_EVIDENCE`; the gap must never silently fall through to PASS or FAIL.

### P8 — No Opaque AI Judgement

AI tools may be used to assist search (e.g., locate all usages of a deprecated function, identify patterns in test output). AI tools must not:

- Generate finding text that the reviewer cannot independently verify.
- Make or influence severity determinations.
- Produce summary conclusions that substitute for reviewer analysis.
- Generate evidence (e.g., synthesised test results, inferred metrics).

Where a reviewer uses AI assistance, they must disclose this in their review report and confirm that every finding produced with AI assistance has been independently verified by them against the actual artefact.

---

## 4. Review Board Composition

### 4.1 Roles

| Role | Abbrev | Responsibility |
|------|--------|----------------|
| Board Chair | BC | Convenes reviews, enforces process, confirms and records deterministic decisions |
| Methodology Auditor | MA | Reviews specification conformance and process integrity |
| Software Architecture Auditor | SAA | Reviews structural and architectural correctness |
| Business and Commercial Auditor | BCA | Reviews commercial impact and contractual alignment |
| Data and Evidence Auditor | DEA | Reviews data quality, evidence integrity, and traceability |
| QA and Reliability Auditor | QRA | Reviews test coverage, defect management, and reliability |
| Security and Privacy Auditor | SPA | Reviews security controls and privacy obligations |
| Performance and Operations Auditor | POA | Reviews performance, scalability, and operational readiness |
| Sceptical Reviewer | SR | Challenges assumptions, probes for hidden risks, devil's advocate |

There are nine Board roles in total. The six **specialist auditors** are SAA, BCA, DEA, QRA, SPA, and POA. MA and SR are separate cross-cutting roles. BC is the convening and decision-assembly authority. A separate publication control, operated by protected-branch automation or a named Publication Authority, releases a validated decision; it is not a tenth reviewer role.

### 4.2 Quorum

Quorum requirements vary by review tier (see §6A). At minimum, for a Tier 2 Standard Review:

- Board Chair (or designated deputy).
- Methodology Auditor.
- At least four of the six specialist auditors (SAA, BCA, DEA, QRA, SPA, POA), selected based on the nature of the artefact under review.
- The Sceptical Reviewer.

For a Tier 3 Full Board Review, all nine roles must be filled with no substitution of scope.

If a required auditor is unavailable, the Board Chair must document the absence and assign a qualified substitute before substantive review begins. A review that lacks quorum is `PROCEDURALLY_INCOMPLETE`. A review knowingly conducted without quorum is `VOID` and cannot produce a substantive outcome.

### 4.3 Assignment

The Board Chair is responsible for assigning reviewers to each review cycle. Assignment must respect independence rules (§5). Assignments are documented in the Review Initiation Record before any reviewer begins work.

One named human may hold only one logical Board role in a review session. Roles must not be merged at any tier. A designated deputy assumes the BC role for the entire session and is subject to the same restrictions. An AI assistant or automated service does not fill a Board role and does not count toward quorum.

### 4.4 Human Reviewers and AI Execution Boundaries

All Board roles must be filled by named, accountable human reviewers. This rule has the following operational meaning:

**What AI agents and automated tools may do:**
- Execute search queries against the artefact (grep, static analysis, dependency graph traversal).
- Locate evidence candidates for a human reviewer to evaluate.
- Format report templates and populate structured fields from reviewer-supplied content.
- Run automated scanning tools whose outputs become T1 evidence.
- Draft a report structure that the named human reviewer then reviews, verifies, and signs.

**What AI agents and automated tools must not do:**
- Hold a Board role in their own name.
- Sign, countersign, or formally submit any review document without an identified human reviewer accepting accountability for its content.
- Classify finding severity.
- Determine whether evidence is admissible under §8.2.
- Close a finding.
- Issue a Board Decision Record.
- Issue a Milestone-Completion Confirmation.
- Issue an Independence Declaration.

**Mandatory human sign-off boundaries:** The following acts require a named human reviewer's explicit signature or equivalent recorded acknowledgement before the record is accepted into the audit trail:

| Act | Required Sign-off |
|----|------------------|
| Independence Declaration | The named reviewer for each role |
| Finding raised at SEV-1 or SEV-2 | The named specialist reviewer who raises it |
| Finding closure (SEV-1 or SEV-2) | The named closure reviewer (must differ from finding raiser) |
| Board Decision Record | Board Chair |
| Milestone-Completion Confirmation | Business and Commercial Auditor |
| Methodology Audit Report (process integrity phase) | Methodology Auditor |
| Correction Record | Panel Chair of the appeal panel |

An AI-generated draft report becomes a valid reviewer report only when the named human reviewer has read it, confirmed all findings against the actual artefact, corrected any errors, and signed it. The human reviewer accepts full accountability for the signed document regardless of how it was drafted.

### 4.5 Decision Finalisation and Publication Separation

The Board Chair may assemble the unsigned decision candidate but may not be its sole governance validator or publication authority. The Methodology Auditor validates the candidate against the sealed finding set, process status, profile version, and checksum. After that validation, the Board Chair may sign the decision. Publication then requires either:

- protected-branch automation that independently validates the signed decision and machine-readable indicator; or
- a named Publication Authority who did not serve as Board Chair or Methodology Auditor in the same session.

The publication control may release a validated record but may not alter its process status, outcome, reasoning, or merge authorisation.

---

## 5. Independence Rules

### 5.1 Conflict of Interest

A reviewer must not review artefacts they authored, co-authored, or substantially specified. If a reviewer contributed to any component within scope, they must declare this in the Review Initiation Record and must be recused from reviewing that component.

### 5.2 Commercial Independence

A reviewer must not hold a commercial stake in the outcome of the review (e.g., a bonus tied to release, a client relationship that depends on approval). Where a potential commercial conflict exists, the reviewer must declare it. The Methodology Auditor validates whether recusal is required and the Board Chair assigns any replacement. If the Board Chair has the conflict, the Methodology Auditor and Methodology Owner appoint a deputy; the conflicted Chair must not adjudicate their own conflict or participate further in that session.

### 5.3 Organisational Independence

For milestone reviews that determine commercial invoicing or contractual commitments, at least one reviewer per specialist discipline must be organisationally independent from the team that produced the artefact. "Organisationally independent" means not managed by the same direct line manager and not a member of the same development team.

### 5.4 Independence for Sceptical Reviewer

The Sceptical Reviewer must always be independent of the authoring team for Tier 3 and all milestone reviews. For Tier 1 and Tier 2 routine reviews, a senior reviewer who was not involved in the specific change may serve.

### 5.5 Declaration Requirement

Every reviewer must sign an Independence Declaration at the start of each review, confirming they have no disqualifying conflicts. This declaration is retained in the audit trail. AI agents may not sign Independence Declarations; only the named human reviewer may do so.

No reviewer may validate their own independence, assignment exception, finding closure, governance decision, or appeal. An unresolved conflict produces process status `BLOCKED`; a material undisclosed conflict discovered after substantive review may make the session `VOID`.

---

## 6. Review Trigger Conditions

A Board review is mandatory when any of the following conditions are met. The Minimum Tier column indicates the lowest permissible review tier; the actual tier may be escalated by the MA or Board Chair.

| Trigger | Threshold | Minimum Tier |
|---------|-----------|-------------|
| Milestone completion | Any milestone with commercial or contractual significance | Tier 3 |
| Protected branch merge | Any PR targeting `main`, `release/*`, or equivalent; low-risk changes may use Tier 1 only when every Tier 1 criterion is met | Tier 1 |
| Functional code change to protected branch | Any executable production-code change not otherwise requiring Tier 3 | Tier 2 |
| Production deployment | Any deployment to a production environment | Tier 3 |
| Security change | Any change to authentication, authorisation, encryption, or access control | Tier 3 |
| Data contract change | Any change to public API schemas, database schemas affecting external clients | Tier 3 |
| Governance or methodology change | Any change to this document or any reviewer specification | Tier 3 |
| Performance boundary change | Any change expected to alter throughput, latency, or resource consumption by >10% | Tier 2 |
| Dependency upgrade — major version | Major version upgrade of a critical dependency | Tier 2 |
| Dependency upgrade — patch/minor | Patch or minor version upgrade with no known security advisory | Tier 1 |
| Post-incident change | Any change implementing a post-incident action item | Tier 2 |
| Low-risk documentation or configuration | Documentation or safe configuration with no executable, security, data, API, contractual, or deployment effect | Tier 1 |

Routine development merges to non-protected branches do not require a Board review but should undergo standard developer peer review.

---

## 6A. Review Risk Tiers

Review risk tiers provide a deterministic, proportionate path through the review process. Tier classification is not discretionary: the authoring team proposes a tier; the MA validates against the criteria below; the Board Chair confirms before any reviewer begins work.

A tier may be **escalated** (e.g., from Tier 1 to Tier 2) by the MA or Board Chair at any point. A tier may **not be de-escalated** below the minimum mandated by any applicable trigger condition in §6.

### Tier 1 — Lightweight Review

**Applies to:** Changes that carry low risk of defect propagation, commercial harm, or security exposure and do not meet a Tier 2 or Tier 3 trigger. Characteristic changes:
- Documentation corrections with no executable, API-contract, security, data, contractual, or deployment effect.
- Test-suite-only changes with no production code modification.
- Dependency patch-version upgrades with no known CVE or breaking change.
- Configuration-only changes that do not touch security parameters, data routing, or access control.

**Required reviewers:** BC + MA (gate + process integrity) + any two of {SAA, QRA, POA} whose discipline is most relevant to the change + SR. Each role is held by a distinct named human.

**Not required (unless scope triggers conditional inputs):** BCA, DEA, SPA. If the change summary indicates any commercial, data quality, or security angle, the relevant specialist must be added.

**Decision rules:** §10 applies unchanged. The smaller reviewer set does not relax finding thresholds.

### Tier 2 — Standard Review

**Applies to:** Code changes, API changes, data model changes, new integrations, major or minor dependency version upgrades, operational configuration changes, and any change that does not meet Tier 1 criteria and does not require Tier 3.

**Required reviewers:** Full minimum quorum per §4.2 (BC + MA + four of six specialists + SR), with each role held by a distinct named human.

**Decision rules:** §10 applies unchanged.

### Tier 3 — Full Board Review

**Applies to:** Any change that meets any of the following criteria:
- Touches security controls, cryptographic implementations, access control, or authentication.
- Modifies a data contract affecting external clients or personal data handling.
- Is a milestone completion, release gate, or production deployment.
- Modifies this methodology or any reviewer specification.
- Is classified as High-risk by the authoring team or escalated to Tier 3 by MA or Board Chair.
- Is a post-incident change implementing an action item for a SEV-1 production incident.

**Required reviewers:** All nine roles (BC + MA + all six specialists + SR), held by nine distinct named humans. No role may be omitted or merged. The SR report must explicitly address the Tier 3 characterisation.

**Decision rules:** §10 applies unchanged. The SR must include a Tier 3 Risk Characterisation section in their report.

### Tier Classification Record

The assigned tier must be recorded in the Review Initiation Record (TPL-RIR) along with the trigger conditions and classification rationale. Any escalation after initial classification must be documented with the reason.

### 6B. Canonical RBE Lifecycle Mapping

This profile does not define a competing review-session state machine. Its phases map to the RBE-001 canonical states as follows:

| RBM activity | Canonical RBE state(s) |
|---|---|
| Assemble and seal Input Package | `DRAFT` → `SUBMITTED` |
| Validate admissibility | `INTAKE_VALIDATION` → `RETURNED` or `ACCEPTED` |
| Pin package, profile, rules, and checksums | `EVIDENCE_LOCKED` |
| Assign distinct, conflict-cleared reviewers | `ASSIGNMENT` |
| Specialist audits | `INDEPENDENT_REVIEW` |
| Sceptical challenge and bounded answers | `CHALLENGE` ↔ `CLARIFICATION` |
| Normalize findings and compute candidate outcome | `CONSOLIDATION` |
| MA process and decision-candidate validation | `GOVERNANCE_VALIDATION` |
| Board Chair signs validated result | `DECIDED` |
| Independent publication control releases record | `PUBLISHED` |
| Appeal and correction | `APPEALED` → `APPEAL_REVIEW` → `UPHELD`, `SUPERSEDED`, or `REMANDED` |
| Ordinary close and retention | `FINAL` → `ARCHIVED` |

`BLOCKED`, `VOID`, `WITHDRAWN`, and `RETURNED` retain their RBE meanings. A remand creates a linked successor session that resumes at `ASSIGNMENT`; it does not mutate the original session. Finding lifecycle labels in §13 are states of an individual finding, not aliases for review-session states or process statuses.

---

## 7. Input Package Requirements

### 7.1 Mandatory Inputs

No review may begin without a complete Input Package. The following items are mandatory for all reviews:

| Item | Description |
|------|-------------|
| Artefact Identifier | Immutable identifier: commit SHA, build hash, or tagged release identifier |
| Review Risk Tier | Proposed tier (Tier 1 / 2 / 3) with classification rationale |
| Scope Statement | Explicit statement of what is in and out of scope for this review |
| Change Summary | Author-provided description of what changed and why |
| Linked Requirements | References to the requirements, specifications, or stories addressed by this change |
| Test Evidence Package | All test results (unit, integration, end-to-end) produced by the CI pipeline for this artefact version |
| Dependency Manifest | Complete list of runtime dependencies with versions |
| Known Issues Register | Documented list of known defects and limitations as of the artefact version |
| Previous Review Record | If a re-review: the prior Board decision and the remediation evidence |

### 7.2 Conditional Inputs

| Condition | Additional Required Input |
|-----------|--------------------------|
| Contains security changes | Security scan results (SAST, DAST, dependency vulnerability scan) |
| Handles personal data | Privacy impact assessment |
| Has performance implications | Performance benchmark results with baseline comparison |
| Modifies data contracts | Schema migration plan and backward-compatibility analysis |
| Is a milestone completion | Commercial acceptance criteria statement from the business owner (see §18 for scope limitations) |

### 7.3 Input Package Validation

The Methodology Auditor validates the Input Package before any specialist review begins. If mandatory items are absent, process status is `PROCEDURALLY_INCOMPLETE`, the session moves to `RETURNED`, and no substantive outcome is produced. The deficiency and required completion action are recorded in the audit trail.

The completion clock starts when the Input Package is deemed incomplete. If the package is not completed within five business days, the Board Chair must escalate. Resubmission creates a sealed successor package version; it does not overwrite the incomplete package.

---

## 8. Evidence Standards

### 8.1 Evidence Quality Tiers

All evidence submitted in support of a finding or a remediation must be classified by the reviewer into one of the following tiers:

| Tier | Name | Description |
|------|------|-------------|
| T1 | Direct Instrument | Artefact produced directly by an automated tool against the specific artefact under review (e.g., CI test log, static analysis report, benchmark output) |
| T2 | Direct Observation | Reviewer-executed procedure applied to the specific artefact under review, with documented steps and output |
| T3 | Documentary Reference | A written specification, contract, legal instrument, regulatory instrument, or authoritative technical standard that the artefact can be compared against |
| T4 | Reasoned Inference | A conclusion derived from T1–T3 evidence using explicitly stated reasoning |
| T5 | Assertion | A claim without supporting T1–T4 evidence |

### 8.2 Evidence Admissibility

| Context | Minimum Tier Required |
|---------|----------------------|
| Raising a Critical (SEV-1) finding | T1 or T2 — see exception below |
| Raising a Major (SEV-2) finding | T1, T2, or T3 |
| Raising a Minor (SEV-3) finding | T1, T2, T3, or T4 |
| Raising an Observation (SEV-4) | T1–T4 |
| Closing a Critical finding | T1 or T2 demonstrating resolution |
| Closing a Major finding | T1, T2, or T3 demonstrating resolution |
| Closing a Minor finding | T1–T4 demonstrating resolution |

**Exception — Authoritative External Reference for Critical Findings:**
T3 evidence is admissible to support a SEV-1 finding when all of the following conditions are satisfied:

1. The T3 reference is an authoritative legal statute, regulatory instrument, contractual obligation, or recognised technical specification (e.g., an applicable data protection regulation, a signed client contract clause, an IETF RFC, or a governing industry standard).
2. The reviewer explicitly identifies the specific clause, section, provision, or requirement number within the referenced document.
3. The reviewer documents a direct chain of applicability — a single logical step from the referenced requirement to the specific artefact behaviour under review, without inference chains spanning more than one step.
4. The reviewer confirms the referenced document is currently in force, applies to this jurisdiction and context, and has not been superseded.

A finding supported only by T3 under this exception must be marked with the flag `T3-AUTHORITATIVE-EXTERNAL` in the Finding Record. The MA will verify that all four conditions are satisfied during the process integrity audit. If any condition is not met, the MA will reclassify the finding's evidence to inadmissible and require the reviewer to locate T1 or T2 evidence or withdraw the SEV-1 classification.

T5 evidence (assertion) is not admissible for any finding under any circumstances.

### 8.3 Evidence Capture Requirements

Evidence must be captured in a form that:

- Can be reproduced by a third party following documented steps.
- References the specific artefact version (commit SHA or equivalent).
- Is timestamped at the point of capture.
- Is retained in the audit trail and not overwritten by subsequent evidence.

---

## 9. Severity Classification

All findings are classified using the following severity scale. Severity is assigned by the reviewer who raises the finding and may be challenged through the Disagreement Handling process (§12).

### SEV-1 — Critical

A defect, gap, or non-conformance that:

- Creates a material risk of data loss, data corruption, or unauthorised data access.
- Violates a contractual, legal, or regulatory obligation (established by T1, T2, or T3-AUTHORITATIVE-EXTERNAL evidence per §8.2).
- Prevents core functionality from operating correctly.
- Would cause the system to produce incorrect outputs in normal operating conditions.
- Represents a security vulnerability that could be exploited without insider access.

**Board Decision Impact:** A single unresolved SEV-1 finding produces `FAIL` when process status is `READY`. No exception or waiver applies.

### SEV-2 — Major

A defect, gap, or non-conformance that:

- Significantly degrades system reliability, performance, or data accuracy under foreseeable conditions.
- Violates a stated requirement or design specification without a recorded waiver.
- Creates a commercial risk that is not mitigated by the known issues register.
- Would require a non-trivial remediation effort and cannot be deferred without accumulating technical debt that is not disclosed.

**Board Decision Impact:** Two or more unresolved SEV-2 findings produce `FAIL`. Exactly one unresolved SEV-2 with an accepted remediation plan may produce `PASS_WITH_FINDINGS` if evidence is otherwise sufficient. One unresolved SEV-2 without an accepted remediation plan produces `FAIL`. Zero unresolved SEV-2 findings may produce `PASS` if all other conditions are met.

### SEV-3 — Minor

A defect, gap, or non-conformance that:

- Reduces system quality, maintainability, or observability below desired standards.
- Represents a deviation from best practice that carries low but non-zero risk.
- Is bounded in impact and can be remediated in a subsequent release without commercial risk.

**Board Decision Impact:** Minor findings do not block merge but must be entered into the tracking register with target remediation dates.

### SEV-4 — Observation

A note, recommendation, or improvement opportunity that:

- Does not represent a defect or non-conformance.
- Is provided for the team's benefit to improve future work.

**Board Decision Impact:** Observations do not affect the Board decision. They are recorded for reference.

---

## 10. Process Status and Decision Framework

### 10.1 Process Status

Process status is evaluated before any substantive outcome. Exactly one canonical status applies:

| Status | Profile rule | Substantive outcome |
|---|---|---|
| `READY` | Inputs are sealed and complete; profile is ACTIVE for binding use (or explicitly advisory for a dry run); distinct-role quorum, conflicts, required reports, challenge disposition, audit integrity, and governance validation all pass | Exactly one outcome required |
| `PROCEDURALLY_INCOMPLETE` | A mandatory input, assignment, quorum member, report, signature, or validation step is missing before decision | Must be null |
| `BLOCKED` | A material but potentially resolvable conflict, dispute, integrity concern, architecture conflict, or governance condition prevents a legitimate decision | Must be null |
| `VOID` | The session is invalid, including a changed artefact, knowingly bypassed quorum, material undisclosed conflict, checksum failure, or use of an unauthorised profile | Must be null |

Process defects never map to `FAIL`. They must be repaired in the current state where allowed or handled through a traceable successor session.

### 10.2 Finding Snapshot and Evidence Sufficiency

The decision candidate is computed from a sealed finding snapshot. For outcome calculation, **unresolved** means a finding in `OPEN`, `CONTESTED`, or `UNDER_REVIEW`. `CLOSED`, `WITHDRAWN`, and valid SEV-3/SEV-4 `WAIVED` findings are not unresolved. A contested finding retains its asserted severity until the dispute is resolved.

The consolidation record derives whether the procedurally complete evidence is sufficient for a defensible PASS-class conclusion from the required specialist reports and recorded evidence gaps; the MA validates that derivation rather than supplying technical judgement. `substantive_evidence_sufficient=false` does not erase confirmed defects. It controls only when no FAIL rule already establishes that the scoped conclusion is not justified.

### 10.3 Deterministic Outcome Rules

When process status is `READY`, evaluate the following rules in order and stop at the first match:

| Priority | Condition | Outcome |
|---|---|---|
| 1 | One or more unresolved SEV-1 findings | `FAIL` |
| 2 | Two or more unresolved SEV-2 findings | `FAIL` |
| 3 | Exactly one unresolved SEV-2 without an accepted remediation plan and committed timeline | `FAIL` |
| 4 | The sealed record is not substantively sufficient for a defensible PASS-class conclusion | `INSUFFICIENT_EVIDENCE` |
| 5 | Exactly one unresolved SEV-2 with an accepted remediation plan and committed timeline | `PASS_WITH_FINDINGS` |
| 6 | Zero unresolved SEV-1 and SEV-2 findings, with sufficient evidence | `PASS` |

The profile permits `PASS`, `PASS_WITH_FINDINGS`, `FAIL`, and `INSUFFICIENT_EVIDENCE`. It omits `DEFER_FOR_FURTHER_RESEARCH`; every bounded evidence or research gap therefore maps to `INSUFFICIENT_EVIDENCE` with a recorded next-evidence action. The outcome rules are total and mutually exclusive for every `READY` input.

`FAIL` requires remediation and a governed successor review (§14). `PASS_WITH_FINDINGS` permits conditional merge only under §11 and requires tracked remediation. `INSUFFICIENT_EVIDENCE` does not assert that the artefact passes or fails and cannot authorise merge, deployment, publication, milestone completion, or invoicing. `PASS` is not a declaration of perfection; it means the evidence supports the scoped conclusion at this profile's threshold.

### 10.4 Decision Authority and Four-Eyes Control

The outcome is not a vote. The Board Chair assembles an unsigned candidate from the sealed snapshot and §10.3. The Methodology Auditor independently validates process status, snapshot counts, evidence sufficiency, rule application, profile checksum, and activation status. Only then may the Board Chair sign the record. Publication follows §4.5.

If any reviewer disputes a finding record, the dispute must be resolved or the process remains `BLOCKED`; it must not be converted into an outcome. Disputes about an already signed outcome are handled through §18A.

### 10.5 Abstentions

A reviewer may not abstain from raising a finding they have identified. If a reviewer is uncertain whether a finding warrants raising, they must raise it at the severity they believe is most defensible and note their uncertainty. Findings may be challenged and re-classified but must not be suppressed.

---

## 11. Merge-Blocking Rules

### 11.1 Hard Blocks

The following conditions constitute hard merge blocks. No merge to a protected branch may proceed while any hard block is active.

| Block Condition |
|----------------|
| Process status is not `READY` |
| Outcome is `FAIL` or `INSUFFICIENT_EVIDENCE` |
| One or more SEV-1 findings are unresolved |
| One SEV-2 finding is unresolved without an accepted remediation plan, or two or more SEV-2 findings are unresolved |
| The artefact identifier has changed since the review was conducted |
| The Board Decision Record has not been signed by the Board Chair |
| MA governance validation is absent or failed |
| Profile status is not `ACTIVE`, profile checksum is invalid, or the human approval record is absent |
| Independent publication control has not validated the decision artifact |

### 11.2 Conditional Merge

`PASS_WITH_FINDINGS` is the only conditional merge path. It requires exactly one unresolved SEV-2, an accepted remediation plan with a committed timeline, `READY` process status, valid quorum, an ACTIVE profile, completed four-eyes validation, and successful independent publication control. No Board Chair waiver may replace any of those conditions. Missing specialist scope is acceptable only where the tier's declared minimum quorum and conditional-role rules were satisfied before review began.

### 11.3 Branch Protection Integration

For repositories using automated branch protection, the Board decision must be recorded in the machine-readable indicator format (TPL-MRI, defined in §17.6 and schema §17.9) that can be consumed by branch protection rules. The merge-blocking mechanism must not rely solely on manual process. A RELEASE-CANDIDATE profile always emits `binding=false` and `merge_permitted=false`, regardless of its advisory outcome.

---

## 12. Disagreement Handling

### 12.1 Types of Disagreement

| Type | Description |
|------|-------------|
| Finding Dispute | A reviewer disagrees with a finding raised by another reviewer (existence, severity, or evidence) |
| Decision Dispute | A reviewer disputes the Board decision as not following from the finding set |
| Process Dispute | A reviewer disputes the conduct of the review (independence violation, evidence fabrication, etc.) |

### 12.2 Finding Dispute Resolution

**Step 1 — Peer Resolution (24 hours)**
The disputing reviewer contacts the finding owner directly. Both reviewers attempt to agree on finding disposition. If agreed: the finding record is updated with the agreed disposition and the rationale, as an appended correction (not an overwrite).

**Step 2 — Board Panel (48 hours from Step 1 failure)**
If peer resolution fails, the Board Chair convenes a panel of three reviewers (excluding the disputing parties). The panel reviews the evidence and makes a binding determination. The determination is recorded as an appended entry.

**Step 3 — Independent Escalation**
If the panel cannot reach a unanimous determination within 48 hours, the finding remains `CONTESTED`, process status becomes `BLOCKED`, and the Board Chair appoints an independent qualified adjudicator who did not participate in the original review or panel. The adjudicator resolves only the finding dispute against the admissibility and severity rules and records the evidence basis. The Board Chair must not resolve evidentiary truth or finding severity by applying outcome rules.

At no stage may a finding be suppressed during an active dispute. The finding remains Open and Contested until resolution. A Contested SEV-1 finding blocks merge.

### 12.3 Decision Dispute Resolution

A Decision Dispute can only be raised on the grounds that the decision does not follow from the finding set per §10. Schedule pressure, commercial impact, or team workload are not valid grounds.

The MA reviews the process status, sealed finding snapshot, evidence-sufficiency record, and outcome and confirms whether §§10.1–10.3 were applied correctly. If a misapplication is confirmed, the Board Chair records a corrected decision per the Correction Mechanism (§18A). The original decision is preserved; the correction is a separate appended record. If the decision correctly follows from the rules, the dispute is closed with a written explanation.

### 12.4 Process Dispute Resolution

Process disputes (independence violations, evidence fabrication, deliberate suppression) are elevated to Provena Foundry governance leadership immediately. The affected review becomes `BLOCKED` pending investigation. If integrity can no longer be established, it becomes `VOID`. All findings from the affected reviewer are placed under review; no substantive outcome may be issued while the dispute is active.

---

## 13. Finding Lifecycle

All findings follow this lifecycle. State transitions are permanent and append-only in the audit trail.

For §10 calculations, `OPEN`, `CONTESTED`, and `UNDER_REVIEW` are unresolved. Moving a finding to `UNDER_REVIEW` does not reduce its decision impact.

```
[OPEN]
   │
   ├── Contested (dispute raised) ──► [OPEN] (dispute resolved, finding confirmed)
   │                                ──► [WITHDRAWN] (dispute resolved, finding invalid)
   │
   ├── Remediation submitted ──► [UNDER REVIEW]
   │                                │
   │                                ├── Evidence accepted ──► [CLOSED]
   │                                └── Evidence rejected ──► [OPEN]
   │
   └── Board decision: not applicable to this review ──► [WAIVED] (SEV-3/4 only, requires justification)
```

### 13.1 Finding Record Fields

Each finding must be recorded with:

| Field | Description |
|-------|-------------|
| Finding ID | Unique identifier: `[Review ID]-[Reviewer Abbrev]-[Sequence]` |
| Review ID | Identifier of the review cycle |
| Reviewer | Name and role of the reviewer who raised the finding |
| Artefact Version | Immutable identifier of the artefact under review |
| Severity | SEV-1 through SEV-4 |
| Reviewer Spec Reference | Section of the reviewer specification that identifies this finding type |
| Finding Title | Concise description (≤ 80 characters) |
| Finding Detail | Full description with evidence references |
| Evidence Tier | T1–T5 per §8.1; flag `T3-AUTHORITATIVE-EXTERNAL` if applicable |
| Evidence Reference | Specific pointers to evidence (file path, line number, log entry, document section, clause/provision) |
| Status | OPEN / CONTESTED / UNDER REVIEW / CLOSED / WITHDRAWN / WAIVED |
| Remediation Requirement | What must be demonstrated to close this finding |
| Target Resolution Date | Required for SEV-1 and SEV-2 |
| Closure Evidence | Evidence submitted to close the finding |
| Closure Reviewer | Who reviewed and accepted closure (must differ from finding raiser for SEV-1/SEV-2) |
| Closure Date | When the finding was closed |

---

## 14. Remediation and Re-Review Process

### 14.1 Remediation Plan Requirements

For SEV-1 and SEV-2 findings, the authoring team must submit a Remediation Plan within two business days of a `FAIL` or `PASS_WITH_FINDINGS` outcome. The plan must include:

- Root cause analysis for each finding.
- Specific changes to be made.
- Who is responsible for each change.
- Target completion date.
- How resolution will be evidenced (what T1/T2 evidence will be produced).

The Methodology Auditor reviews and accepts or rejects the Remediation Plan. A rejected plan must be resubmitted within one business day.

### 14.2 Re-Review Scope

A re-review is scoped to:

- Verification that each remediated finding has been resolved per its closure requirements.
- Assessment of whether the remediation introduced new defects within the scope of the original review.
- Confirmation that the artefact version identifier has changed since the original review.

A re-review is **not** a fresh full review unless the Board Chair determines that the remediation was so extensive that the original review is no longer applicable.

### 14.3 Re-Review Decision

A re-review is a linked successor session and uses the same process-status and outcome framework as the original review against a newly sealed artefact and finding snapshot. It may produce any permitted outcome in §10.3. Closed findings remain linked as historical records; unresolved or newly introduced findings retain their normal decision impact.

### 14.4 Remediation Timeout

If a SEV-1 finding has not been remediated within ten business days of the FAIL decision, the Board Chair must escalate to Provena Foundry governance leadership. The release associated with the failing artefact must be placed on hold until the finding is closed.

---

## 15. Audit Trail Requirements

### 15.1 Mandatory Records

The following records must be retained for every review:

| Record | Retention Period |
|--------|-----------------|
| Review Initiation Record (artefact ID, reviewers, trigger, tier) | Permanent |
| Independence Declarations (all reviewers) | Permanent |
| Input Package validation record | Permanent |
| All Finding Records (including Withdrawn) | Permanent |
| All Reviewer Reports | Permanent |
| Disagreement records | Permanent |
| Remediation Plans | Permanent |
| Re-review records | Permanent |
| Board Decision Record | Permanent |
| Correction Records (if any) | Permanent |
| Branch protection integration record | 7 years |
| Methodology profile, checksum, manifest, and human approval record | Permanent |
| Governance validation and publication records | Permanent |

### 15.2 Immutability

Audit trail records are append-only. No record may be deleted, overwritten, or altered. Corrections must be made by adding a superseding Correction Record (TPL-COR, §17.8) that references the original by its unique identifier. The original record is preserved in full.

### 15.3 Storage Requirements

Audit records must be stored in a location that:

- Is access-controlled and auditable.
- Is backed up with a tested restore process.
- Is retained independent of the code repository (to survive repository deletion or migration).
- Is readable without proprietary software.

For Provena Foundry, audit records are maintained in the designated review archive (location defined in the operational runbook, separate from this document).

### 15.4 Audit Log Format

Each audit log entry must be structured with:

- Timestamp (ISO 8601, UTC).
- Actor (human reviewer name and role; `system` if automated tool).
- Event type (finding raised, finding updated, decision recorded, etc.).
- Payload (the record content or a reference to the full record).
- Previous record reference (for updates and supersessions; `null` for initial entries).
- Methodology profile ID, version, status, and checksum for decision-affecting events.

---

## 16. Versioning and Reproducibility

### 16.1 Document Versioning

This methodology and all reviewer specifications are versioned using semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR:** Changes that alter decision outcomes for the same finding set (e.g., changing severity rules, changing decision criteria, adding new hard-block conditions).
- **MINOR:** Changes that add new sections, new guidance, new tiers, or new templates without altering how existing findings are evaluated.
- **PATCH:** Typographic corrections, cross-reference fixes, or formatting changes.

Every approved version is retained in version control with an immutable tag. The exact profile checksum, package manifest root hash, architecture authority, and human approval reference used for a review are recorded in the Review Initiation Record and determine which rules apply.

### 16.2 Activation Gate

A release candidate becomes ACTIVE only when all of the following are true:

1. The referenced RBE architecture release has named human approval.
2. The package validator passes against the exact commit.
3. The Principal Architect and Methodology Owner approve the exact profile checksum in a recorded human approval artifact.
4. `PROFILE.json` status is changed to `ACTIVE` and contains that approval reference.
5. The package is rebuilt, revalidated, committed, and tagged immutably.

Codex, another AI tool, a test result, a merged pull request, or a checksum cannot supply the human approval record. Activation is a separate governed change and must not be bundled silently into this release candidate.

### 16.3 Review Reproducibility

A review is reproducible if, given:

- The artefact version (immutable identifier).
- The version of this methodology.
- The version of each applicable reviewer specification.
- The Input Package.

A different reviewer following the same process would reach materially equivalent conclusions. Reviews must be conducted and documented to this standard.

### 16.4 Artefact Versioning

The artefact under review must be identified by an immutable version identifier before the review begins. Reviews conducted against a moving target are void unless the commit SHA is captured at the time of review initiation and does not change during the review.

If the artefact changes during a review, the review must be restarted against the new artefact version. The previous partial review is recorded as void.

---

## 17. Required Output Templates and Machine-Readable Schemas

### 17.1 Template Index

| Template ID | Name | Owner | Used By | Schema |
|-------------|------|-------|---------|--------|
| TPL-RIR | Review Initiation Record | Board Chair | All reviews | `schemas/tpl-rir.schema.json` |
| TPL-IND | Independence Declaration | Each reviewer | All reviews | — |
| TPL-IPV | Input Package Validation | Methodology Auditor | All reviews | — |
| TPL-FND | Finding Record | Each reviewer | Per finding | `schemas/tpl-fnd.schema.json` |
| TPL-RRR | Reviewer Report | Each reviewer | All reviews | `schemas/tpl-rrr.schema.json` |
| TPL-BDR | Board Decision Record | Board Chair | All reviews | `schemas/tpl-bdr.schema.json` |
| TPL-RMP | Remediation Plan | Authoring team | `FAIL` / `PASS_WITH_FINDINGS` | `schemas/tpl-rmp.schema.json` |
| TPL-RVR | Re-Review Record | Board Chair | Re-reviews | — |
| TPL-MRI | Machine-Readable Indicator | Publication control | Branch protection | `schemas/tpl-mri.schema.json` |
| TPL-COR | Correction Record | Panel Chair | Appeals/corrections | `schemas/tpl-cor.schema.json` |

### 17.2 Template: Review Initiation Record (TPL-RIR)

```
REVIEW INITIATION RECORD
=========================
Review ID:
Review Date:
Trigger Condition (§6):
Review Risk Tier (§6A): [ ] Tier 1  [ ] Tier 2  [ ] Tier 3
Tier Classification Rationale:
Artefact Identifier (commit SHA or equivalent):
Repository:
Branch / Target:
Methodology Version:
Methodology Profile ID:
Methodology Profile Status:
Methodology Profile Checksum:
Package Manifest Root Hash:
Architecture Authority:
Human Approval Record:
Reviewer Spec Versions (list each):

Assigned Reviewers:
  Board Chair:
  Methodology Auditor:
  Software Architecture Auditor:
  Business and Commercial Auditor:
  Data and Evidence Auditor:
  QA and Reliability Auditor:
  Security and Privacy Auditor:
  Performance and Operations Auditor:
  Sceptical Reviewer:

Omitted Specialist Roles (with justification; not permitted for Tier 3):

Input Package Location:
Input Package Process Status: [READY / PROCEDURALLY_INCOMPLETE]
Input Package Validator:
Input Package Validation Date:
```

### 17.3 Template: Independence Declaration (TPL-IND)

```
INDEPENDENCE DECLARATION
=========================
Review ID:
Reviewer Name:
Reviewer Role:
Date:

I confirm that:
[ ] I did not author or co-author any component within the scope of this review.
[ ] I do not hold a commercial stake in the outcome of this review.
[ ] I am not managed by the same direct line manager as the authoring team
    (required for Tier 3 and milestone reviews; mark N/A for Tier 1 routine reviews).
[ ] I have no other conflict of interest that would impair my independence.
[ ] I understand that I am personally accountable for the content of any report
    I sign, regardless of whether AI tools assisted in its preparation.

If any item above is unchecked, describe the conflict and state the
Methodology Auditor disposition and any replacement assignment:

[Conflict description if applicable]
[MA conflict disposition reference]

Signature:
```

### 17.4 Template: Finding Record (TPL-FND)

```
FINDING RECORD
==============
Finding ID:
Review ID:
Reviewer:
Reviewer Role:
Artefact Version:
Date Raised:

Severity: [ ] SEV-1  [ ] SEV-2  [ ] SEV-3  [ ] SEV-4
Reviewer Spec Reference:
Finding Title (≤ 80 chars):

Finding Detail:
[Full description]

Evidence:
  Evidence Tier: [ ] T1  [ ] T2  [ ] T3  [ ] T3-AUTHORITATIVE-EXTERNAL  [ ] T4  [ ] T5
  If T3-AUTHORITATIVE-EXTERNAL:
    Document name and version:
    Specific clause/section/provision:
    Applicability chain (single logical step):
    Confirmation document is currently in force: [ ] YES
  Evidence Reference:
  [Specific file path / line / log entry / document section]

AI Assistance Used: [ ] Yes  [ ] No
If yes, describe what AI was used for and confirm independent verification:

Status: [ ] OPEN  [ ] CONTESTED  [ ] UNDER REVIEW  [ ] CLOSED  [ ] WITHDRAWN  [ ] WAIVED

Remediation Requirement:
[What must be demonstrated to close this finding]

Target Resolution Date:
[Required for SEV-1 and SEV-2]

--- Closure ---
Closure Evidence:
Closure Reviewer (must differ from finding raiser for SEV-1/SEV-2):
Closure Date:
Closure Decision: [ ] ACCEPTED  [ ] REJECTED
Rejection Reason (if rejected):
```

### 17.5 Template: Board Decision Record (TPL-BDR)

```
BOARD DECISION RECORD
=====================
Review ID:
Artefact Identifier:
Review Risk Tier:
Decision Date:
Board Chair:

Summary of Finding Set:
  SEV-1 Unresolved:                      [count]
  SEV-2 Unresolved:                      [count]
  SEV-2 Remediation Plans Accepted:      [count]
  SEV-3 Open:                            [count]
  SEV-4 Open:                            [count]
  Contested Findings:                    [count]

Process Status (§10.1):
  [ ] READY  [ ] PROCEDURALLY INCOMPLETE  [ ] BLOCKED  [ ] VOID

Substantive Evidence Sufficient for a PASS-class conclusion: [ ] YES  [ ] NO

Outcome (§10.3; exactly one only when Process Status is READY):
  [ ] FAIL
  [ ] INSUFFICIENT EVIDENCE
  [ ] PASS WITH FINDINGS
  [ ] PASS
  [ ] NONE — Process Status is not READY

Decision rules applied deterministically; this is not a vote.

Unresolved Findings at Time of Decision (list Finding IDs):

Conditions on PASS WITH FINDINGS (if applicable):
  Unresolved Finding ID:
  Remediation Plan accepted: [ ] YES
  Remediation deadline:

Binding Decision: [ ] YES  [ ] NO — advisory release-candidate review

Merge Authorisation:
  [ ] Merge permitted
  [ ] Merge blocked — hard block condition:

MA Governance Validator:
MA Governance Validation Reference:
Board Chair Signature:
Date:
```

### 17.6 Template: Machine-Readable Indicator (TPL-MRI)

The TPL-MRI is governed by the versioned JSON schema at §17.9.4. Human-readable template:

```json
{
  "schema_version": "2.0.0",
  "review_id": "",
  "artefact_sha": "",
  "review_risk_tier": 2,
  "methodology_profile_id": "RBM-001",
  "methodology_version": "2.0.0",
  "methodology_status": "RELEASE_CANDIDATE",
  "methodology_checksum": "sha256:...",
  "binding": false,
  "process_status": "READY",
  "outcome": "PASS",
  "merge_permitted": false,
  "decision_date": "",
  "board_chair": "",
  "governance_validator": "",
  "publication_authority": "",
  "unresolved_sev1_count": 0,
  "unresolved_sev2_count": 0,
  "unresolved_sev2_remediation_plan_accepted": 0,
  "contested_findings": 0,
  "expires_at": "",
  "correction_ref": null
}
```

The `expires_at` field is set to 72 hours after `decision_date` for artefacts under active development. If the artefact SHA changes, the indicator is void regardless of expiry. If a Correction Record has been issued, `correction_ref` is set to the TPL-COR identifier; the most recent valid indicator supersedes prior ones.

### 17.7 Template: Remediation Plan (TPL-RMP)

```
REMEDIATION PLAN
================
Document ID:
Review ID:
Authoring Team Contact:
Date Submitted:

For each unresolved SEV-1 or SEV-2 Finding:

Finding ID:
  Root Cause Analysis:
  Specific Changes to be Made:
  Responsible Person:
  Target Completion Date:
  Resolution Evidence Planned (T1/T2):

Methodology Auditor Review:
  [ ] ACCEPTED — Review may proceed to remediation
  [ ] REJECTED — Reason:
  MA Signature:
  Date:
```

### 17.8 Template: Correction Record (TPL-COR)

```
CORRECTION RECORD
=================
Correction ID:
Original Record ID (the record being corrected):
Original Record Type: [TPL-RIR / TPL-FND / TPL-BDR / TPL-MRI / other]
Date of Correction:
Panel Chair (or Board Chair for Decision Dispute corrections):

Reason for Correction:
  [ ] Procedural error in original review
  [ ] New material evidence not available at time of original review
  [ ] Demonstrable misapplication of decision rules

Description of Error in Original Record:
[Specific description — reference rule or section misapplied]

Corrected Content:
[Full corrected text for the affected field(s) only]

Original Record Status: PRESERVED — this correction does not delete or modify the original
Lineage Reference: [Original Record ID] → [This Correction ID]

Effect on Board Decision (if correction is to TPL-BDR):
  Original process status: [READY / PROCEDURALLY INCOMPLETE / BLOCKED / VOID]
  Corrected process status: [READY / PROCEDURALLY INCOMPLETE / BLOCKED / VOID]
  Original outcome: [PASS / PASS WITH FINDINGS / FAIL / INSUFFICIENT EVIDENCE / NONE]
  Corrected outcome: [PASS / PASS WITH FINDINGS / FAIL / INSUFFICIENT EVIDENCE / NONE]
  Revised TPL-MRI issued: [ ] YES — ID:  [ ] NO

Panel Chair Signature:
Date:
```

### 17.9 Versioned Machine-Readable Schemas

The normative Draft 2020-12 schemas are version-controlled files under `schemas/`:

- `tpl-rir.schema.json` — Review Initiation Record.
- `tpl-fnd.schema.json` — Finding Record.
- `tpl-rrr.schema.json` — Reviewer Report.
- `tpl-bdr.schema.json` — Board Decision Record.
- `tpl-rmp.schema.json` — Remediation Plan.
- `tpl-mri.schema.json` — Machine-Readable Indicator.
- `tpl-cor.schema.json` — Correction Record.

Schema version `2.0.0` matches this profile. The package validator parses every schema, validates profile and manifest identity, and enforces cross-record invariants that JSON Schema alone cannot safely express. In particular: non-`READY` process status requires a null outcome; `FAIL` and `INSUFFICIENT_EVIDENCE` cannot permit merge; RELEASE-CANDIDATE records are non-binding; reviewer identities must satisfy distinct-role quorum; and a decision requires separate Board Chair, governance validator, and publication-control identities where applicable.

---

## 18. Milestone-Completion Criteria

### 18.1 Definition

A milestone is complete when and only when:

1. All deliverables defined in the milestone specification have been produced.
2. A Board review has been completed for the artefact representing the milestone output.
3. Process status is `READY` under an ACTIVE, checksum-valid, human-approved profile.
4. The Board outcome is `PASS` or `PASS_WITH_FINDINGS`.
5. The Business and Commercial Auditor has issued a Milestone-Completion Confirmation.
6. All SEV-1 findings are resolved.
7. A Remediation Plan with accepted timeline is in place for the single unresolved SEV-2 permitted by `PASS_WITH_FINDINGS`, if present.
8. The Board Decision Record has been validated by the MA, signed by the Board Chair, and released by independent publication control.

### 18.2 Commercial Invoicing Gate

Where milestone completion is linked to a commercial invoice, the invoice must not be raised until conditions 1–8 above are satisfied.

**Important scope limitation:** The Board Decision Record and the Milestone-Completion Confirmation are governance records. They confirm that:

- The review process was completed per this methodology.
- The process status and outcome met the threshold criteria defined in §§10.1–10.3.
- The BCA assessed that the declared acceptance criteria were addressed.

They are **not** representations of present commercial readiness, fitness for purpose, warranty of quality, or evidence of client acceptance. They do **not** supersede or substitute for:

- Any contractual acceptance process agreed with the client.
- Any client sign-off, UAT, or acceptance testing required by the commercial agreement.
- Any legal or regulatory approval required before the product is used in a regulated context.

Commercial invoicing remains subject to the separately negotiated acceptance gate defined in the relevant commercial agreement. The BCA's Milestone-Completion Confirmation is a necessary but not sufficient condition for invoicing where a contractual client acceptance step also applies.

### 18.3 Partial Milestone Completion

A milestone is binary: complete or not complete. There is no partial completion for commercial invoicing purposes. Where a milestone contains multiple components and one component fails review, the entire milestone is incomplete until all components have received a PASS or PASS WITH FINDINGS decision.

---

## 18A. Appeal and Correction Mechanism

### 18A.1 Purpose

The Appeal and Correction Mechanism provides a structured, evidence-based path to correct errors in Board decisions and review records. It preserves the integrity and immutability of the original audit trail while permitting legitimate corrections. It is not a mechanism for relitigating decisions on commercial or schedule grounds.

### 18A.2 Grounds for Appeal

An appeal may be raised only on one of the following grounds:

| Ground | Description |
|--------|-------------|
| Procedural Error | A material breach of this methodology occurred during the review that affected the finding set or decision (e.g., independence violation not caught by MA, quorum not met without authorisation) |
| New Material Evidence | Evidence that was not available at the time of the review and would materially affect a finding's admissibility or severity |
| Decision Rule Misapplication | The Board Decision Record does not follow from the process status, sealed finding set, evidence-sufficiency record, and rules in §§10.1–10.3 |

The following are **not** valid grounds for appeal:

- Schedule pressure or commercial urgency.
- Disagreement with a finding's technical merit that was already disputed and resolved during the review.
- New opinions about the severity of an existing finding without new evidence.

### 18A.3 Appeal Process

**Step 1 — Submission (within 5 business days of Board Decision)**
Any named reviewer, the Board Chair, or the authoring team may submit an appeal. The submission must:
- State the ground (Procedural Error / New Material Evidence / Decision Rule Misapplication).
- Reference the specific record or finding being challenged.
- Provide the evidence supporting the appeal ground (T1–T3; T5 assertions are not admissible in an appeal).

**Step 2 — Admissibility Review (within 2 business days of submission)**
The Methodology Auditor assesses whether the appeal meets the grounds criteria. If the appeal does not meet the criteria, it is rejected with a written explanation. The original decision stands.

**Step 3 — Appeal Panel (within 5 business days of admissibility confirmation)**
If admissible, the Board Chair convenes a panel of three reviewers, none of whom participated in the original review and none of whom holds a conflicting role or commercial interest. The Board Chair does not sit on the panel. The panel:
- Reviews the original records and the appeal evidence.
- Makes a binding determination: Upheld (error confirmed) or Dismissed (original record correct).

**Step 4 — Correction Record (if Upheld)**
If the appeal is upheld, the Panel Chair issues a Correction Record (TPL-COR, §17.8) appended to the audit trail. The original record is preserved unchanged. If the original Board Decision is corrected, a revised TPL-MRI is issued, referencing the correction.

### 18A.4 Lineage Preservation

All corrections are additive. The original record is never modified or removed. The correction chain is recorded in the `correction_ref` field of the TPL-MRI and in the `lineage` field of the TPL-COR. Any consumer of the audit trail must follow the correction chain to determine the current operative record.

---

## 19. Reviewer Specification Index

The following specifications define the scope, inputs, evidence requirements, checklists, and output templates for each Board reviewer role. Each specification is a standalone document that must be read alongside this governing methodology.

| Spec ID | Title | File | Version |
|---------|-------|------|---------|
| RBS-001 | Methodology Audit | `specs/RBS-001-METHODOLOGY-AUDIT.md` | 2.0.0 |
| RBS-002 | Software Architecture Audit | `specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md` | 2.0.0 |
| RBS-003 | Business and Commercial Audit | `specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md` | 2.0.0 |
| RBS-004 | Data and Evidence Audit | `specs/RBS-004-DATA-EVIDENCE-AUDIT.md` | 2.0.0 |
| RBS-005 | QA and Reliability Audit | `specs/RBS-005-QA-RELIABILITY-AUDIT.md` | 2.0.0 |
| RBS-006 | Security and Privacy Audit | `specs/RBS-006-SECURITY-PRIVACY-AUDIT.md` | 2.0.0 |
| RBS-007 | Performance and Operations Audit | `specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md` | 2.0.0 |
| RBS-008 | Sceptical Review | `specs/RBS-008-SCEPTICAL-REVIEW.md` | 2.0.0 |

---

## 20. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-18 | Provena Foundry Governance | Initial release |
| 1.1.0 | 2026-07-18 | Provena Foundry Governance | Principal Architect review: (1) Status set to RELEASE-CANDIDATE; (2) Decision outcomes made mutually exclusive with explicit evaluation order; (3) Quorum role count corrected to six specialist auditors; (4) Board Chair role description corrected — decisions are deterministic, not voted; (5) AI execution boundaries and mandatory human sign-off table added (§4.4); (6) Review Risk Tiers introduced (§6A) with Tier 1 lightweight, Tier 2 standard, Tier 3 full-board paths; (7) T3-AUTHORITATIVE-EXTERNAL evidence exception for SEV-1 findings added (§8.2); (8) Milestone-completion gate scope limitation added — Board decision is not warranty of commercial readiness (§18.2); (9) Versioned machine-readable JSON schemas added for TPL-RIR, TPL-FND, TPL-BDR, TPL-MRI, TPL-COR (§17.9); (10) Appeal and Correction Mechanism added (§18A) with append-only lineage and TPL-COR template |
| 2.0.0 | 2026-07-19 | Provena Foundry Governance | RBE-001 conformance correction: separated process status from substantive outcome; added mandatory `INSUFFICIENT_EVIDENCE`; closed unresolved-finding decision gaps; added architecture authority, canonical lifecycle mapping, activation gate, profile checksum/manifest, distinct-role and four-eyes controls, independent publication, corrected tier precedence and evidence rules, external schemas, validation tests, and principal review record. Status remains RELEASE-CANDIDATE pending named human approval. |
| 2.1.0 | 2026-07-26 | Provena Foundry Governance | Agent-held reviewer seats. v2.0.0 required a distinct accountable human in every board seat, so the board could not be seated by an organisation with fewer humans than seats and was never convened. Designated reviewer seats (MA, SR, and the specialist pool) may now be held by governed agents. The Board Chair seat remains human because accountability cannot be delegated. Ratification and publication authority remain human. Any review using an agent-held seat is advisory and cannot be binding, and the seat's model and instruction version are recorded. Independence requirements prevent correlated agent seats. Status remains RELEASE-CANDIDATE pending named human approval. |

## 21. Agent-Held Reviewer Seats

A reviewer seat may be held by a governed agent. This section states what that
does and does not change.

**Permitted seats.** Methodology Audit, Sceptical Review, and every specialist
seat may be agent-held. The Board Chair seat may not. The Chair is accountable
for the review, and accountability cannot be delegated to an agent.

**Authority is unchanged.** Ratification and publication authority remain human.
An agent produces a report; it does not sign a decision.

**Advisory only.** A review in which any seat was agent-held is advisory and
cannot be binding, regardless of profile status.

**Verification.** Every agent-held seat requires a named human verifier, recorded
against the report. This is the existing `ai_assistance.human_verified` control.

**Independence.** Agent seats fail as a board when they share reasoning. The
following are required and recorded:

- a distinct instruction version per seat;
- the sceptical seat is blind to the proposed outcome, receiving evidence and the
  question "what does this evidence fail to establish?";
- the model and instruction version of each seat;
- where seats share a model, that fact is recorded rather than obscured.

**Interpretation.** A board of agents that never dissents is not providing
assurance. Dissent rate is a health signal for the board, not a defect in it.
| 2.2.0 | 2026-07-26 | Provena Foundry Governance | Single-authority advisory ratification. v2.1.0 permitted agent-held reviewer seats but kept ratification human, and ratification requires two separated humans, so a one-human organisation could complete a review and never sign the result. A single named human Board Chair may now ratify while the profile is non-binding, recorded permanently as single_authority so it is never mistaken for a two-signature decision. Refused once the profile is ACTIVE. The deterministic gates still compute the outcome, so the signatory attests to the process rather than choosing the result. Supersedable by a two-signature decision. Status remains RELEASE-CANDIDATE pending named human approval. |

## 22. Single-Authority Advisory Ratification

Ratification requires two separated humans. An organisation with one human can
therefore conduct a complete review and never sign the result, leaving governed
decisions permanently unratified. This section permits a single named human to
ratify, and states exactly what is given up by doing so.

**Permitted only while non-binding.** Single-authority ratification is available
only while the profile is not ACTIVE. It is refused the moment the methodology
becomes binding, so it can never become a route to a binding decision signed by
one person.

**The authority is the Board Chair, and must be human.** No agent may ratify,
under any configuration.

**Publication is covered by the same allowance.** Publication normally requires an
authority separate from those who decided. A single-authority decision was signed
by one human because no second human exists, so that separation cannot be met
either. The Board Chair may publish their own single-authority decision, and the
decision remains marked single-authority in the published indicator.

**Recorded permanently.** The decision carries `single_authority: true` through
the decision record, the published indicator, and the exported bundle. No reader
can mistake it for a two-signature decision.

**The outcome is still not the signatory's to choose.** The deterministic gates
compute the outcome from the frozen findings. A single authority attests that the
process ran and accepts the recorded result; it cannot alter it. This is what
makes single-authority ratification defensible rather than a rubber stamp.

**What is genuinely given up.** The four-eyes control exists so that nobody
approves their own work. A single authority attests to a review it commissioned.
The residual risk is not a falsified outcome, which the gates prevent, but a
favourably framed question: the choice of evidence admitted and seats staffed. No
signature scheme addresses that. Only a second human does.

**Upgrade path.** A two-signature decision supersedes a single-authority one
through the ordinary appeal and supersession process. The original remains in the
history, marked superseded, beside the stronger decision that replaced it.

---

*End of Governing Methodology — RBM-001 v2.2.0*
