# Reviewer Specification: Methodology Audit

**Document ID:** RBS-001
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** Methodology Auditor (MA)
**Last Updated:** 2026-07-19

---

## Table of Contents

1. [Role Definition](#1-role-definition)
2. [Scope](#2-scope)
3. [Responsibilities](#3-responsibilities)
4. [Independence Rules](#4-independence-rules)
5. [Required Inputs](#5-required-inputs)
6. [Audit Procedure](#6-audit-procedure)
7. [Checklist](#7-checklist)
8. [Evidence Standards](#8-evidence-standards)
9. [Finding Classification Guidance](#9-finding-classification-guidance)
10. [Board Decision Contribution](#10-board-decision-contribution)
11. [Required Output](#11-required-output)
12. [Reviewer Prompt Conversion Notes](#12-reviewer-prompt-conversion-notes)

---

## 1. Role Definition

The Methodology Auditor (MA) is the first reviewer to act on every review cycle and the last to close it. The MA's function is to ensure the review process itself is conducted correctly, completely, and in accordance with RBM-001.

The MA is not a specialist in the technical content under review. The MA is a specialist in the review process. The MA reviews the reviewers.

The MA holds a unique dual function:

1. **Gate function:** Validate the Input Package before any specialist review begins. Block the review if mandatory inputs are absent.
2. **Process integrity function:** After all specialist reviews are complete, audit the review process itself — confirming that each reviewer followed their specification, raised admissible findings, and did not suppress, fabricate, or inadequately evidence their findings.

The MA does not assess the technical merit of specialist findings. The MA assesses whether findings were raised and evidenced in compliance with this specification and RBM-001.

---

## 2. Scope

The MA's scope encompasses:

- The completeness and validity of the Input Package (RBM-001 §7).
- Compliance of each reviewer's conduct with their respective reviewer specification.
- Compliance of findings with the evidence standards of RBM-001 §8.
- Compliance of the finding lifecycle with RBM-001 §13.
- Validity of process status and outcome relative to the sealed finding snapshot, evidence-sufficiency record, profile identity, and RBM-001 §10.
- Completeness and integrity of the audit trail (RBM-001 §15).
- Version consistency: the architecture authority, methodology profile version/checksum/status, package manifest, human approval record, and reviewer specification versions in the Review Initiation Record must match the documents actually applied.

The MA's scope does **not** encompass:

- The technical correctness of the artefact under review.
- The technical merit of specialist findings (e.g., whether an architecture finding is a valid architectural concern).
- GS-P001 processes, documents, or governance.

---

## 3. Responsibilities

### 3.1 Pre-Review (Gate Function)

| Responsibility | Timing |
|---------------|--------|
| Receive the Input Package from the authoring team | Before review initiation |
| Validate each mandatory input per RBM-001 §7.1 | Before any specialist review begins |
| Validate conditional inputs per RBM-001 §7.2 based on declared scope | Before any specialist review begins |
| Issue Input Package Validation record (TPL-IPV) | Before any specialist review begins |
| Return the package with `PROCEDURALLY_INCOMPLETE` status if incomplete | Immediately on discovery |
| Confirm artefact identifier is immutable and recorded | Before any specialist review begins |

### 3.2 During Review

| Responsibility | Timing |
|---------------|--------|
| Monitor for mid-review artefact version changes | Continuous |
| Record any artefact version change as a process defect | On discovery |
| Receive Independence Declarations from all reviewers | Before any reviewer begins their review |
| Flag missing or conflicted Independence Declarations | On discovery |

### 3.3 Post-Review (Process Integrity Function)

| Responsibility | Timing |
|---------------|--------|
| Review each reviewer's report for specification compliance | After all specialist reports are submitted |
| Assess each finding for evidence admissibility per RBM-001 §8 | After all specialist reports are submitted |
| Identify findings that rely on T5 evidence (assertion) | After all specialist reports are submitted |
| Validate process status and candidate outcome under RBM-001 §10 | After the unsigned Board Decision Record is drafted |
| Validate distinct-role quorum and four-eyes separation | Before the Board Chair signs |
| Validate profile checksum, manifest, activation, and human approval record | Before the Board Chair signs |
| Confirm the audit trail is complete per RBM-001 §15 | Before the review is closed |
| Issue the MA Report | After all post-review checks are complete |

---

## 4. Independence Rules

The MA must not:

- Have authored or co-authored any component within the scope of the artefact under review.
- Have served as a specialist reviewer in the same review cycle (the MA role is separate from specialist roles).
- Have written or approved the Input Package.

The MA must be sufficiently independent from the review process itself to assess it objectively. The MA may not review their own previous MA decisions without a second independent MA co-signing.

For milestone reviews, the MA must be organisationally independent from the authoring team per RBM-001 §5.3.

---

## 5. Required Inputs

### 5.1 Inputs for Gate Function

| Input | Source | Required Condition |
|-------|--------|--------------------|
| Draft Input Package | Authoring team | Always |
| Review Initiation Record (TPL-RIR) | Board Chair | Always |
| `PROFILE.json` and `MANIFEST.json` | Controlled package | Always |
| Scope Statement | Authoring team or Board Chair | Always |
| Previous Review Record | Board Chair | Re-reviews only |

### 5.2 Inputs for Process Integrity Function

| Input | Source | Required Condition |
|-------|--------|--------------------|
| All Independence Declarations (TPL-IND) | Each reviewer | Always |
| All Specialist Reviewer Reports | Each reviewer | After specialist reviews complete |
| All Finding Records (TPL-FND) | Each reviewer | After specialist reviews complete |
| Draft Board Decision Record (TPL-BDR) | Board Chair | After specialist reviews complete |
| Audit trail as assembled to date | Board Chair or designated archivist | Before MA closes review |

---

## 6. Audit Procedure

### Step 1 — Input Package Validation

Review each mandatory input item against the checklist in §7. For each item:
- Confirm it is present.
- Confirm it refers to the correct artefact version (matching the immutable identifier in the Review Initiation Record).
- Confirm it is not a template placeholder (e.g., a test results document that contains no actual test results).
- Confirm it is not materially stale (produced against a prior version of the artefact).

If any mandatory item fails, record `PROCEDURALLY_INCOMPLETE`, return the package, and stop. Do not proceed to Step 2 until a sealed successor package is complete.

### Step 2 — Independence Declaration Collection

Collect a signed Independence Declaration from every assigned reviewer before they begin their review. Confirm each Board role is held by a distinct named human. Flag any reviewer who begins work without a signed declaration. The MA adjudicates disclosed reviewer conflicts; if the Board Chair is conflicted, the MA and Methodology Owner appoint a deputy.

### Step 3 — Version Consistency Check

Confirm that the architecture authority, methodology profile ID/version/status/checksum, package manifest root hash, human approval reference, and each reviewer specification version in the Review Initiation Record match the controlled package. If any identity or checksum differs, stop with `VOID`. A RELEASE-CANDIDATE profile may continue only as an explicitly non-binding dry run.

### Step 4 — Post-Review Report Audit

For each specialist reviewer's report:

**4a — Specification Compliance:** Confirm the reviewer addressed all mandatory checklist items in their specification. Note any sections that were not addressed. Determine if the omission is justified (out of scope for this review) or a gap (in scope but not addressed).

**4b — Finding Admissibility:** For each finding raised:
- Confirm the evidence tier declared by the reviewer.
- Confirm the evidence tier is sufficient for the finding severity per RBM-001 §8.2.
- Confirm the evidence reference is specific (file path, line number, log entry, document section). Vague references ("see the test results") are not admissible.
- Flag any finding that relies on T5 evidence.

**4c — AI Assistance Disclosure:** Confirm that any reviewer who used AI assistance declared it and confirmed independent verification.

**4d — Severity Compliance:** Confirm that finding severity classifications are internally consistent across reviewers (e.g., the same class of defect is not SEV-1 for one reviewer and SEV-3 for another without justification).

### Step 5 — Decision Validation

Confirm that the unsigned Board Decision Record correctly applies RBM-001 §10:
- Validate the canonical process status first; a non-`READY` status requires a null outcome.
- Count unresolved (`OPEN`, `CONTESTED`, or `UNDER_REVIEW`) SEV-1 and SEV-2 findings.
- Validate the specialist-derived evidence-sufficiency record without substituting MA technical judgement.
- Verify the unique outcome among `PASS`, `PASS_WITH_FINDINGS`, `FAIL`, and `INSUFFICIENT_EVIDENCE` per §10.3.
- Verify RELEASE-CANDIDATE runs are non-binding with merge prohibited.
- Verify the Board Chair and MA are distinct and publication control is independent.

If the decision does not follow from the rules, this is a process defect — raise it as a Critical process finding before the decision is finalised.

### Step 6 — Audit Trail Completeness

Confirm that all required records per RBM-001 §15.1 exist, are correctly structured, and are stored in the designated archive location.

---

## 7. Checklist

### 7.1 Input Package Validation Checklist

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| IPV-01 | Artefact Identifier present | Inspect TPL-RIR | A specific, immutable identifier (commit SHA or equivalent) is recorded |
| IPV-02 | Scope Statement present and specific | Inspect Input Package | Scope explicitly states what is in and out of scope; is not generic |
| IPV-03 | Change Summary present | Inspect Input Package | Describes what changed and why; not a copy of a generic commit message template |
| IPV-04 | Linked Requirements present | Inspect Input Package | At least one requirement, story, or specification reference is provided |
| IPV-05 | Test Evidence Package present | Inspect Input Package | Contains actual test results for the specific artefact version; not a prior run |
| IPV-06 | Dependency Manifest present | Inspect Input Package | Lists runtime dependencies with version numbers |
| IPV-07 | Known Issues Register present | Inspect Input Package | Exists and is current (not empty unless explicitly confirmed to be zero known issues) |
| IPV-08 | Previous Review Record present (re-reviews) | Inspect Input Package | Prior Board Decision Record and remediation evidence are included |
| IPV-09 | Security scan results present (conditional) | Inspect Scope Statement | Required if any security changes declared in scope |
| IPV-10 | Privacy impact assessment present (conditional) | Inspect Scope Statement | Required if personal data handling declared in scope |
| IPV-11 | Performance benchmarks present (conditional) | Inspect Scope Statement | Required if performance implications declared in scope |
| IPV-12 | Schema migration plan present (conditional) | Inspect Scope Statement | Required if data contract changes declared in scope |
| IPV-13 | Commercial acceptance criteria confirmation present (conditional) | Inspect Scope Statement | Required for milestone completion reviews |
| IPV-14 | All documents reference the correct artefact version | Cross-reference | All documents cite the same immutable identifier |

### 7.2 Process Integrity Checklist

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| PIC-01 | Independence Declarations received from all reviewers | Inspect declarations | All assigned reviewers have submitted a signed declaration before beginning work |
| PIC-02 | No undeclared conflicts identified | Cross-reference declarations with authorship records | All potential conflicts are declared |
| PIC-03 | Profile identity and package integrity match TPL-RIR | Validate `PROFILE.json`, checksum, `MANIFEST.json`, architecture authority, status, and human approval reference | Exact match; binding use requires ACTIVE and named human approval |
| PIC-04 | Reviewer specification versions match TPL-RIR | Compare RIR to each reviewer report header | Same version numbers for each role |
| PIC-05 | Artefact version did not change during review | Review timeline and version records | SHA or equivalent is identical at start and end of review |
| PIC-06 | Each specialist report addresses mandatory checklist items | Review each report against its specification | All in-scope checklist items addressed or justified absence |
| PIC-07 | All findings have admissible evidence | Review each TPL-FND | SEV-1 uses T1/T2 or valid `T3-AUTHORITATIVE-EXTERNAL`; SEV-2 may use T1/T2/T3; SEV-3/4 may use T1–T4; no finding relies on T5 |
| PIC-08 | All evidence references are specific | Review each TPL-FND evidence reference | All references include specific file path, line, log entry, or document section |
| PIC-09 | AI assistance declared where used | Review each TPL-FND | Any AI-assisted finding includes declaration and independent verification confirmation |
| PIC-10 | Severity classifications are internally consistent | Cross-review comparison | Same class of defect is not assigned materially different severities across reviewers without documented justification |
| PIC-11 | Process status and outcome correctly apply §10 | Re-apply rules to process record, sealed snapshot, and evidence sufficiency | Non-READY has null outcome; READY has the unique correct outcome |
| PIC-12 | All required audit trail records exist | Inspect archive | All records per RBM-001 §15.1 are present, complete, and correctly stored |
| PIC-13 | Unresolved findings counted consistently | Verify decision record | OPEN, CONTESTED, and UNDER_REVIEW findings retain severity impact |
| PIC-14 | Machine-readable indicator issued | Inspect TPL-MRI | TPL-MRI is present, valid, and consistent with Board Decision |
| PIC-15 | Review risk tier correctly classified and recorded | TPL-RIR and RBM-001 §6A criteria | The assigned tier matches all applicable trigger conditions; no de-escalation below the mandated minimum; tier classification is recorded in the TPL-RIR |
| PIC-16 | Mandatory human sign-off boundaries observed | Review all signed records | Each act requiring human sign-off per RBM-001 §4.4 (finding confirmation, finding closure, Board Decision Record, Milestone-Completion Confirmation, Correction Records) is signed by a named human; no act is signed solely by an AI-generated identifier |
| PIC-17 | Four-eyes and publication separation observed | Compare identities and records | Board Chair, MA governance validator, and human Publication Authority are distinct where publication is human; automation cannot be bypassed |
| PIC-18 | Outcome evidence floor preserved | Inspect evidence-sufficiency record and candidate | Evidentiary insufficiency maps to `INSUFFICIENT_EVIDENCE`, never PASS/PASS_WITH_FINDINGS/FAIL |

---

## 8. Evidence Standards

For process findings raised by the MA, the following evidence standards apply:

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| Missing Input Package item | T1 (absence is direct) | Screenshot or log showing item not present in package |
| T5 evidence used by specialist | T3 | The specialist's finding record showing the evidence field; comparison to RBM-001 §8.2 |
| Decision rule misapplication | T3 | The finding record count and the decision rule text showing the discrepancy |
| Artefact version change during review | T1 | Git log or equivalent showing SHA change between review start and review end |
| Independence violation | T2 | Authorship record and independence declaration showing undeclared conflict |
| Missing specification coverage | T3 | Reviewer report showing uncovered checklist item with no justification |

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND. The MA must verify all four conditions are recorded when auditing any such finding.

The MA must not raise process findings on the basis of assertion (T5). If the MA cannot evidence a process concern, it must be recorded as an Observation pending further investigation, not a finding.

---

## 9. Finding Classification Guidance

### SEV-1 for Methodology Audit

- The Input Package was represented as complete when mandatory items were absent, and the review proceeded on false premises.
- A reviewer with a direct conflict of interest reviewed their own work; no Chair or MA waiver can cure authorship conflict.
- The Board Decision does not follow from the finding set and was recorded anyway (potential integrity violation).
- Evidence fabrication: a reviewer recorded evidence that demonstrably does not exist in the artefact.

### SEV-2 for Methodology Audit

- A mandatory Input Package item is absent and the review proceeded without MA deferral.
- An Independence Declaration was not collected before a reviewer began work.
- A SEV-1 finding relies on T3 without satisfying all `T3-AUTHORITATIVE-EXTERNAL` conditions, or relies on T4/T5.
- The artefact version changed during the review and this was not documented or acted upon.
- A reviewer's report does not address mandatory checklist sections that are in scope, with no documented justification.

### SEV-3 for Methodology Audit

- A conditional Input Package item is absent and the omission was not flagged.
- Evidence references are vague (lacking file paths or line numbers) but T-tier is otherwise appropriate.
- AI assistance was used but not declared.
- Severity classifications are inconsistent across reviewers for the same finding type without documented justification.

### SEV-4 for Methodology Audit

- Minor formatting or completeness gaps in finding records that do not affect substance.
- An audit trail record exists but is not in the correct format.

---

## 10. Board Decision Contribution

The MA does not issue the substantive outcome. The MA records exactly one canonical process status and validates the unsigned decision candidate:

- `READY`: every required process, identity, integrity, role, challenge, and validation control passes. A candidate outcome is required.
- `PROCEDURALLY_INCOMPLETE`: a mandatory input, assignment, quorum member, report, signature, or validation step is absent. Outcome must be null.
- `BLOCKED`: a material conflict, dispute, architecture conflict, or remediable integrity concern prevents finalisation. Outcome must be null.
- `VOID`: the session is invalid and cannot yield an outcome. A linked successor session is required.

The Board Chair cannot override the MA's documented failed control. A disagreement follows RBM-001 §§12 or 18A and remains traceable.

---

## 11. Required Output

### 11.1 Input Package Validation Record (TPL-IPV)

```
INPUT PACKAGE VALIDATION RECORD
================================
Review ID:
MA Name:
Validation Date:
Artefact Identifier under review:

MANDATORY ITEMS:
[For each IPV-01 through IPV-08, record: PRESENT / ABSENT]
[For absent items: state the specific gap]

CONDITIONAL ITEMS:
[Identify which conditions apply based on Scope Statement]
[For each applicable conditional item: PRESENT / ABSENT / NOT APPLICABLE]

OVERALL PROCESS STATUS:
[ ] READY — Review may proceed
[ ] PROCEDURALLY INCOMPLETE — Package returned pending: [list missing items]

Notes:

MA Signature:
Date:
```

### 11.2 Methodology Audit Report

```
METHODOLOGY AUDIT REPORT
=========================
Document ID:        TPL-MAR
Review ID:
MA Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-001 [version]

SECTION 1 — GATE FUNCTION
Input Package Process Status: [ ] READY  [ ] PROCEDURALLY INCOMPLETE
Reference to TPL-IPV:

SECTION 2 — INDEPENDENCE CHECK
Independence Declarations received from all reviewers: [ ] YES  [ ] NO
Any undeclared conflicts identified: [ ] YES  [ ] NO
Details if NO or YES respectively:

SECTION 3 — VERSION CONSISTENCY
Architecture authority consistent: [ ] YES  [ ] NO
Profile ID/version/status/checksum consistent: [ ] YES  [ ] NO
Manifest root hash valid: [ ] YES  [ ] NO
Human approval record valid for binding use: [ ] YES  [ ] NO  [ ] ADVISORY ONLY
Reviewer spec versions consistent: [ ] YES  [ ] NO
Details if NO:

SECTION 4 — SPECIALIST REPORT AUDIT
[For each specialist reviewer:]
Reviewer Name / Role:
  Report received: [ ] YES  [ ] NO
  Mandatory checklist sections addressed: [ ] ALL  [ ] PARTIAL  [ ] NONE
  Gaps (if PARTIAL):
  Findings with inadmissible evidence: [count and list Finding IDs]
  AI assistance declared where used: [ ] YES  [ ] NO  [ ] N/A
  Notes:

SECTION 5 — DECISION VALIDATION
Process Status:
Finding snapshot summary:
  SEV-1 Unresolved:
  SEV-2 Unresolved:
  SEV-2 Remediation Plans Accepted:
Substantive Evidence Sufficient: [ ] YES  [ ] NO
Candidate Outcome:
Outcome correctly applies §10 rules: [ ] YES  [ ] NO  [ ] N/A — process not READY
Board Chair and MA identities distinct: [ ] YES  [ ] NO
Publication control independent: [ ] YES  [ ] NO  [ ] NOT YET PUBLISHED
If NO, state discrepancy:

SECTION 6 — AUDIT TRAIL COMPLETENESS
All required records present: [ ] YES  [ ] NO  [ ] PARTIAL
Missing records (if any):

SECTION 7 — PROCESS FINDINGS RAISED
[List all Finding Records (TPL-FND) raised by the MA]
[Include Finding ID, Severity, Title, and Status]

SECTION 8 — OVERALL PROCESS OPINION
[ ] READY
[ ] PROCEDURALLY INCOMPLETE — [state missing controls]
[ ] BLOCKED — [state blocking controls and remediation]
[ ] VOID — [state invalidating condition and successor-session requirement]

MA Signature:
Date:
```

---

## 12. Reviewer Prompt Conversion Notes

*This section is for the orchestration layer that converts this specification into individual reviewer prompts.*

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human Methodology Auditor. You do not hold the MA role, count toward quorum, sign records, adjudicate conflicts, or determine process status. Assist with two phases: (1) candidate checks for Input Package validation, and (2) candidate checks for process and decision integrity."

**Phase Separation:** The MA prompt must be invoked twice — once before specialist reviews begin (gate function) and once after all specialist reports are submitted (process integrity function). These are distinct prompt invocations with different inputs.

**Inputs to Phase 1 Prompt:** Input Package, Review Initiation Record, Scope Statement.

**Inputs to Phase 2 Prompt:** All specialist reviewer reports, all Finding Records, sealed finding snapshot, evidence-sufficiency record, unsigned Board Decision Record, `PROFILE.json`, `MANIFEST.json`, audit trail records, and Independence Declarations.

**Prohibited Behaviours for Prompt:** The MA prompt must not assess technical merit of specialist findings, supply evidence sufficiency from its own judgement, sign a record, or choose an outcome. It must not generate findings about the artefact's technical content. It must not use the word "probably" or "likely" as a finding basis — only documented evidence. Any AI output remains an unsigned draft until the named human MA verifies and signs it.

**Output Format:** Produce an unsigned draft report matching §11.2 and clearly labelled AI-assisted. Potential issues are evidence candidates, not accepted TPL-FND records, until the named human MA verifies the evidence, assigns any severity, corrects the draft, and signs it.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception with MA verification obligation; updated PIC-07 for T3-AUTHORITATIVE-EXTERNAL admissibility; added PIC-15 (tier classification validation) and PIC-16 (mandatory human sign-off boundary check); status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned with RBM-001 v2.0.0: canonical process statuses, `INSUFFICIENT_EVIDENCE`, four-eyes governance validation, profile/manifest checks, unresolved-finding semantics, and corrected evidence admissibility. |

*End of RBS-001 v2.0.0*
