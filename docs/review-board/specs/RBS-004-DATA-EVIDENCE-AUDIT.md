# Reviewer Specification: Data and Evidence Audit

**Document ID:** RBS-004
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** Data and Evidence Auditor (DEA)
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

The Data and Evidence Auditor (DEA) is responsible for two distinct but related concerns:

**Data Quality Audit:** Assessing the quality, integrity, accuracy, and traceability of data that Provena Foundry produces, processes, stores, or exposes. The DEA determines whether the system handles data in a manner that is correct, consistent, and defensible.

**Evidence Quality Audit:** Assessing the quality of the evidence submitted in the Input Package by the authoring team. This includes test results, benchmarks, prior audit artefacts, and any other evidence used to support claims about the artefact's quality.

The DEA sits at the intersection of data engineering rigour and scientific evidence standards. The DEA must be able to assess both: "Is this data pipeline correct?" and "Is this test result genuine, reproducible, and applicable to the artefact under review?"

---

## 2. Scope

### 2.1 Data Quality Scope

- Data ingestion: correctness, completeness, and failure handling for data entering the system.
- Data transformation: accuracy and reversibility of transformations; absence of silent data loss.
- Data storage: schema correctness, constraint enforcement, and data integrity mechanisms.
- Data output: accuracy, completeness, and format correctness of data produced by the system.
- Data lineage: whether the system can trace data from source to output.
- Data consistency: whether the system maintains consistency under concurrent access and failure conditions.
- Data retention and deletion: whether data lifecycle policies are implemented correctly.

### 2.2 Evidence Quality Scope

- Test result authenticity: confirming test results were produced by the artefact version under review, not a prior version or a different environment.
- Test result completeness: confirming the test results cover the scope declared in the Change Summary.
- Benchmark applicability: confirming performance benchmarks use conditions representative of production.
- Known Issues Register completeness: confirming the register reflects actual system state.
- Evidence chain integrity: confirming that every claim in the authoring team's submissions is supported by traceable evidence.

### 2.3 Out of Scope

- Security controls for data (Security and Privacy Auditor).
- Business rules governing data use (Business and Commercial Auditor).
- Performance implications of data volume (Performance and Operations Auditor).
- GS-P001 data systems.

---

## 3. Responsibilities

| Responsibility | Timing |
|---------------|--------|
| Assess all data-handling changes for quality, integrity, and traceability | During review |
| Assess Input Package evidence for authenticity and applicability | During review |
| Identify Evidence Gaps (required evidence absent from Input Package) | During review |
| Cross-reference Known Issues Register against actual findings | During review |
| Produce the DEA Report | End of review |

---

## 4. Independence Rules

The DEA must not have:
- Produced the test results, benchmarks, or other evidence in the Input Package.
- Designed the data model or data pipeline under review.
- Authored the Known Issues Register for this artefact.

The DEA's independence from the evidence they are assessing is critical. A DEA who produced the evidence they are auditing cannot perform an independent assessment.

---

## 5. Required Inputs

| Input | Source | Required Condition |
|-------|--------|--------------------|
| Test Evidence Package | Input Package | Always |
| Known Issues Register | Input Package | Always |
| Data model / schema documentation | Input Package or codebase | If data changes are in scope |
| Data pipeline specifications or diagrams | Authoring team | If data pipeline changes are in scope |
| Changed source files for data-handling components | Diff | Always |
| CI/CD pipeline configuration | Authoring team | For test authenticity assessment |
| Previous DEA findings | Previous Review Record | Re-reviews only |

---

## 6. Audit Procedure

### Step 1 — Evidence Authenticity Check

Before assessing the content of the evidence, assess its provenance:

- Confirm test results include a timestamp and reference the specific artefact version (commit SHA or build hash).
- Confirm the CI/CD pipeline configuration confirms the test was run against the declared version (not a prior version).
- Confirm that the test environment is documented (runtime version, OS, configuration) and is representative.
- Flag any test result that lacks a version reference, a timestamp, or an environment description.

An evidence package that cannot be confirmed as authentic for the specific artefact under review is an Evidence Gap, regardless of its content.

### Step 2 — Test Coverage Scope Mapping

Map the test results to the Change Summary:

- Identify every functional area changed.
- Confirm that the test results include coverage of each changed area.
- Identify any changed area with no test coverage in the submitted results.

A gap between changed areas and test coverage is an Evidence Gap. The DEA does not assess whether the coverage is sufficient (that is the QA Auditor's role); the DEA assesses whether the evidence for coverage exists and is authentic.

### Step 3 — Data Quality Assessment

For each data-handling change in the artefact:

**Ingestion:**
- Is invalid input rejected or handled explicitly? Is the rejection or handling code present and tested?
- Is there a risk of silent data loss on error conditions?

**Transformation:**
- Is the transformation deterministic? Given the same input, does it produce the same output?
- Are edge cases (null, empty, boundary values) handled explicitly?
- Is there a risk of precision loss (e.g., floating point, date/time conversions)?

**Storage:**
- Are database constraints (NOT NULL, UNIQUE, FOREIGN KEY) appropriate and enforced at the database level, not only in application code?
- Is data that must be consistent across tables managed with transactions?
- Is there a risk of orphaned records from concurrent operations?

**Output:**
- Are output formats validated against a schema or contract?
- Are output values that are derived from input values traceable through the transformation chain?

**Data Lineage:**
- Can any output value be traced to its source inputs through the system's logs or data structures?
- If lineage is required for this data type (e.g., for audit or regulatory purposes), is it implemented?

**Retention and Deletion:**
- If data has a defined retention policy, is it enforced?
- If data deletion is in scope, does deletion cascade correctly to all related data?

### Step 4 — Known Issues Register Completeness

Cross-reference the Known Issues Register against:

- All QA findings from the test results that were not fixed.
- All DEA findings raised during this review that the authoring team is aware of before remediation.
- Any issues raised in previous review cycles that are still open.

A known issue that exists in reality but is absent from the Register is a finding.

### Step 5 — Evidence Chain Assessment

For any claim in the Change Summary or authoring team submission:

- Identify the evidence that supports the claim.
- Confirm the evidence is traceable to the specific artefact version.
- Confirm the evidence is not circular (the claim is not substantiated solely by restatement of the claim).

Particular attention to:
- Claims that a bug has been fixed: is there a test that would have caught the bug before and now passes?
- Claims that performance has improved: is there a before/after benchmark?
- Claims that a security issue has been resolved: is there a test or scan result showing resolution?

---

## 7. Checklist

### 7.1 Evidence Authenticity

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-01 | Test results include artefact version reference | Inspect test output metadata | SHA or build hash matches the artefact identifier in the Review Initiation Record |
| DEA-02 | Test results include timestamp | Inspect test output metadata | Timestamp is present and consistent with the review timeline |
| DEA-03 | Test environment is documented | Inspect test output or CI configuration | Runtime version, OS, and key environment variables are stated |
| DEA-04 | Test environment is representative of production | Compare test environment to production configuration | No material differences that would invalidate the test results |
| DEA-05 | CI/CD pipeline confirms tests ran against declared version | CI configuration and pipeline logs | No evidence of test result reuse from a prior run |

### 7.2 Test Coverage Scope

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-06 | All functionally changed areas have corresponding test evidence | Change Summary vs. test results | No changed area has zero test evidence in the submitted package |
| DEA-07 | New data-handling paths have explicit test evidence | Code diff vs. test results | New ingestion, transformation, storage, and output paths have tests |
| DEA-08 | Error paths in data-handling have test evidence | Code diff vs. test results | Error handling code paths are covered by tests |

### 7.3 Data Quality — Ingestion

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-09 | Invalid input is rejected or handled explicitly | Code review | No silent acceptance of malformed data |
| DEA-10 | No silent data loss on ingestion error | Code review | Errors produce a failure signal, not silent discard |
| DEA-11 | Ingestion is idempotent where required | Code review and specification | Re-submission of the same input does not duplicate records where uniqueness is required |

### 7.4 Data Quality — Transformation

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-12 | Transformations are deterministic | Code review | Same input always produces same output; no dependency on external state without documentation |
| DEA-13 | Edge cases are handled (null, empty, boundary) | Code review and test review | Explicit handling for null, empty, and boundary values is present |
| DEA-14 | Precision loss risks are identified and managed | Code review | Floating point, date/time, and currency transformations are assessed for precision |
| DEA-15 | Transformation chain is traceable | Code review | It is possible to identify which inputs contributed to which outputs |

### 7.5 Data Quality — Storage

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-16 | Database constraints are enforced at the database level | Schema review | Constraints are in schema, not only in application code |
| DEA-17 | Transactional operations are wrapped in transactions | Code review | Multi-step writes that must be atomic are within a transaction |
| DEA-18 | Concurrent write risks are identified and mitigated | Code review | Optimistic or pessimistic locking is used where concurrent writes could corrupt data |
| DEA-19 | Orphaned record risk from cascade operations is assessed | Schema and code review | FK constraints or explicit cleanup handles related record deletion |

### 7.6 Data Quality — Output

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-20 | Output values are validated against a contract or schema | Code review | Output serialisation is schema-validated |
| DEA-21 | Derived output values are traceable to source inputs | Code review | The transformation chain from input to output can be followed |

### 7.7 Known Issues Register

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-22 | Known Issues Register includes all unfixed issues identified in test results | Test results vs. Register | No issue evident in test output is absent from Register |
| DEA-23 | Previous open known issues are still present in the Register (or closed with evidence) | Prior review vs. current Register | Issues from prior reviews are either closed with evidence or still listed |
| DEA-24 | Register is not empty without explicit confirmation | Inspect Register | Either issues are listed or an explicit statement confirms zero known issues |

### 7.8 Evidence Chain

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| DEA-25 | Bug-fix claims have regression tests | Code diff and test review | A test exists that would fail before the fix and passes after |
| DEA-26 | Performance improvement claims have before/after benchmarks | Input Package | Baseline and post-change benchmarks are present and comparable |
| DEA-27 | Security resolution claims have scan or test evidence | Input Package | A scan result or test output confirms resolution |
| DEA-28 | No claim in the submission is supported only by restatement | Input Package review | Claims are supported by T1–T4 evidence |

---

## 8. Evidence Standards

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| Evidence Gap | T1 (absence is direct) | Log showing test suite did not run against the specific artefact version |
| Silent data loss risk | T2 | Code walkthrough demonstrating the execution path where data is discarded without signal |
| Missing constraint | T2 | Schema file showing absence of a constraint that should be present |
| Non-deterministic transformation | T2 | Code review showing dependency on external state or random component |
| Known Issues Register gap | T2 or T3 | Test output showing an issue; Register showing it is absent |

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND.

---

## 9. Finding Classification Guidance

### SEV-1 for Data and Evidence Audit

- Evidence in the Input Package is demonstrably fabricated or produced against a different artefact version and presented as applicable to this review.
- Silent data loss is confirmed in the data ingestion or transformation pipeline.
- A transactional integrity failure that would cause data corruption under foreseeable conditions.
- A known issue constituting data corruption or data loss is absent from the Known Issues Register with no disclosure.

### SEV-2 for Data and Evidence Audit

- Test results cannot be confirmed as authentic for the specific artefact version under review (Evidence Authenticity failure).
- A material changed area has no test evidence in the submitted package.
- Database constraints are absent for fields that require data integrity enforcement.
- A deterministic transformation is implemented non-deterministically.
- The Known Issues Register is materially incomplete (multiple missing issues).

### SEV-3 for Data and Evidence Audit

- Edge case handling is absent for a specific class of input (low risk but not zero).
- Test environment differs from production in a minor but potentially relevant way.
- The Known Issues Register is missing one minor issue.
- Output schema validation is present but incomplete.

### SEV-4 for Data and Evidence Audit

- Test result formatting or metadata is incomplete but content is authentic and applicable.
- Known Issues Register entries are present but poorly described.

---

## 10. Board Decision Contribution

The DEA does not issue a Board outcome or process status. The DEA raises findings and records whether in-scope data and evidence are `SUFFICIENT`, `INSUFFICIENT`, or `NOT_APPLICABLE` for a PASS-class conclusion, with missing evidence listed. A DEA SEV-1 finding regarding evidence fabrication is escalated immediately under RBM-001 §12.4; the review is `BLOCKED` or `VOID` until integrity is resolved.

---

## 11. Required Output

### Data and Evidence Audit Report

```
DATA AND EVIDENCE AUDIT REPORT
================================
Document ID:        TPL-DEAR
Review ID:
DEA Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-004 [version]

EVIDENCE AUTHENTICITY ASSESSMENT
Test results authenticated (artefact version confirmed): [ ] YES  [ ] NO  [ ] PARTIAL
Timestamp confirmed: [ ] YES  [ ] NO
Environment documented: [ ] YES  [ ] NO
Environment representative of production: [ ] YES  [ ] NO  [ ] UNCERTAIN
Notes:

TEST COVERAGE SCOPE MAPPING
Changed functional areas: [count]
Changed areas with test evidence: [count]
Changed areas without test evidence: [list]

DATA QUALITY ASSESSMENT SCOPE
Data-handling changes in scope: [ ] YES  [ ] NO
If YES, categories assessed:
  [ ] Ingestion  [ ] Transformation  [ ] Storage  [ ] Output  [ ] Lineage  [ ] Retention/Deletion

KNOWN ISSUES REGISTER
Register present and current: [ ] YES  [ ] NO
Issues in test output not present in Register: [count — list if >0]

EVIDENCE CHAIN ASSESSMENT
Claims assessed: [count]
Claims without adequate T1–T4 support: [list]

FINDINGS SUMMARY:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]

FINDINGS:
[For each finding, attach a completed TPL-FND]

EVIDENCE FABRICATION FLAG:
[ ] No evidence of fabrication or misrepresentation
[ ] SUSPECTED FABRICATION — escalating under RBM-001 §12.4

PASS-CLASS EVIDENCE SUFFICIENCY:
[ ] SUFFICIENT  [ ] INSUFFICIENT  [ ] NOT APPLICABLE
Missing evidence / limitations:

AI ASSISTANCE:
[ ] AI tools were used — describe what for and confirm independent verification of all findings
[ ] AI tools were not used

DEA Signature:
Date:
```

---

## 12. Reviewer Prompt Conversion Notes

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human Data and Evidence Auditor. You do not hold the DEA role, count toward quorum, authenticate evidence, assign severity, sign findings, or issue an outcome. Help locate candidate evidence about data and evidence integrity."

**Key Prompt Constraints:**
- Must confirm evidence authenticity before assessing evidence content.
- Must not assess security controls — raise data-adjacent security concerns as cross-references to the Security and Privacy Auditor.
- Must not assess business rules or commercial impact — those belong to the BCA.
- Evidence fabrication must be escalated immediately, not just recorded as a finding.
- Must be explicit about which checklist items are in scope vs. not applicable for a given artefact.
- Must label every output as an unsigned draft; authenticity and evidence sufficiency remain human reviewer acts.

**Inputs to Prompt:** Test Evidence Package, CI/CD pipeline configuration, Known Issues Register, changed data-handling source files, data model documentation, Change Summary.

**Output Format:** Unsigned draft report matching §11, with evidence candidates for human verification. TPL-FND records become valid only after the named human DEA verifies evidence, supplies severity, and signs.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception note to §8; status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned terminology and evidence-sufficiency contribution with RBM-001 v2.0.0. |

*End of RBS-004 v2.0.0*
