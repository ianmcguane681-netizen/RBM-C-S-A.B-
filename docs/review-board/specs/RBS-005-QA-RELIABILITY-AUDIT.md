# Reviewer Specification: QA and Reliability Audit

**Document ID:** RBS-005
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** QA and Reliability Auditor (QRA)
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

The QA and Reliability Auditor (QRA) is responsible for assessing the adequacy of the testing strategy, the quality of the test implementation, the trustworthiness of test results, and the system's demonstrated reliability. The QRA determines whether the artefact has been tested in a manner that is thorough, honest, and meaningful — and whether the test results justify confidence in the system's correctness.

The QRA operates at the level of testing methodology, not individual test implementation. The QRA assesses whether the right things are being tested, in the right way, with results that are genuine. The QRA does not re-run tests (that is the DEA's authenticity check); the QRA assesses the adequacy of what was run.

Reliability assessment extends beyond testing to encompass error handling, failure modes, recovery mechanisms, and the system's demonstrated behaviour under adverse conditions.

---

## 2. Scope

The QRA's scope encompasses:

- Test strategy: is there a coherent strategy that covers unit, integration, and end-to-end layers appropriately?
- Test coverage: is the coverage adequate for the risk profile of the changed code?
- Test quality: are tests meaningful (do they fail when they should fail)?
- Test isolation: are tests independent, repeatable, and not dependent on external state?
- Failure mode coverage: are error paths, boundary conditions, and failure scenarios tested?
- Defect management: are known defects tracked and triaged correctly?
- Reliability mechanisms: are circuit breakers, retries, timeouts, and fallbacks implemented correctly?
- Regression: does the test suite protect against regression of previously fixed issues?
- Flakiness: are tests reliable enough to be trusted?

The QRA's scope does **not** encompass:

- Test result authenticity (Data and Evidence Auditor).
- Performance benchmarking (Performance and Operations Auditor).
- Security testing methodology (Security and Privacy Auditor reviews security-specific testing).
- GS-P001 test suites.

---

## 3. Responsibilities

| Responsibility | Timing |
|---------------|--------|
| Review the test strategy (or absence of one) | Start of review |
| Assess test coverage relative to the change scope and risk profile | During review |
| Assess test quality by examining a representative sample of test implementations | During review |
| Assess failure mode coverage for new and modified components | During review |
| Review defect management (known issues, triage, severity) | During review |
| Assess reliability mechanisms in new or modified code | During review |
| Produce the QRA Report | End of review |

---

## 4. Independence Rules

The QRA must not have:
- Written the test suite being assessed.
- Defined the test strategy being assessed.
- Triaged the defects in the Known Issues Register.

Where the QRA contributed to the test strategy but not the implementation, they must declare this and limit their scope to areas where they have no authorial stake.

---

## 5. Required Inputs

| Input | Source | Required Condition |
|-------|--------|--------------------|
| Test Evidence Package (all results) | Input Package | Always |
| Test source code (or access to test files) | Codebase | Always |
| Coverage report (if generated) | CI/CD output | If available |
| Known Issues Register | Input Package | Always |
| Change Summary with risk assessment | Input Package | Always |
| CI/CD pipeline definition | Authoring team | For test isolation assessment |
| Previous QRA findings | Previous Review Record | Re-reviews only |

---

## 6. Audit Procedure

### Step 1 — Risk Profile Assessment

Before assessing coverage, establish the risk profile of the change:

- **High risk:** Changes to core data processing, authentication, billing, external integrations, or any path executed for every request.
- **Medium risk:** Changes to secondary features, configuration-driven behaviour, or internal utilities with bounded impact.
- **Low risk:** Documentation, UI copy, minor UI adjustments, or changes backed by a well-established suite.

Coverage expectations scale with risk profile. A High-risk change with 40% coverage is a different finding from a Low-risk change with 40% coverage.

### Step 2 — Test Strategy Assessment

Determine whether a coherent test strategy exists:

- Is there a documented test strategy? If not, can one be inferred from the test structure?
- Does the strategy distinguish between unit, integration, and end-to-end tests?
- Are the layers of the testing pyramid appropriately balanced for the system type?
- Are there system tests that validate end-to-end behaviour?

### Step 3 — Coverage Assessment

Map the change scope to the test suite:

- For each changed functional area: what tests exist that exercise it?
- Are critical paths (happy path, primary error path) tested at least at integration level?
- Are boundary conditions tested?
- Are untested changed areas identified and their risk justified?

Note: coverage percentage alone is insufficient. A 90% coverage metric built from trivial or tautological tests is worse than 60% coverage from meaningful tests. The QRA assesses whether the coverage is meaningful, not only whether a number exists.

### Step 4 — Test Quality Assessment

Examine a representative sample of tests (at minimum: 10 tests or 25% of new/changed tests, whichever is larger):

- **Meaningful assertion:** Does the test assert the actual expected behaviour, or does it assert that something ran without error (tautological)?
- **Failure detection:** Would this test fail if the code under test returned incorrect data?
- **Isolation:** Does the test depend on execution order, shared mutable state, or external services?
- **Determinism:** Is the test outcome deterministic across runs?
- **Clarity:** Is the test purpose clear from the test name and structure?

A test that cannot fail meaningfully provides no quality signal and should not count as coverage.

### Step 5 — Failure Mode Coverage

For each new or significantly modified component:

- What happens when upstream dependencies are unavailable?
- What happens when inputs are at or beyond boundary values?
- What happens when storage operations fail?
- What happens when concurrent requests arrive simultaneously?

Are the answers to these questions tested? If not, are they documented as known limitations?

### Step 6 — Reliability Mechanism Assessment

Review reliability mechanisms in the changed code:

- **Timeouts:** Are external calls bounded by timeouts? Are timeouts configured at appropriate values?
- **Retries:** Is retry logic present where transient failures are foreseeable? Is it bounded (not infinite)?
- **Circuit breakers:** Is there protection against cascading failure from a repeatedly failing dependency?
- **Fallbacks:** Is there graceful degradation when a non-critical dependency fails?
- **Idempotency:** Are operations that may be retried designed to be idempotent?

### Step 7 — Defect Triage Assessment

Review the Known Issues Register:

- Are all open defects triaged with severity and priority?
- Are any open defects high-severity (from the QRA's assessment) that are not classified as such?
- Are resolution timelines assigned to high-severity defects?
- Are there defects that should block this release that are currently open?

---

## 7. Checklist

### 7.1 Test Strategy

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| QRA-01 | A test strategy is documented or can be clearly inferred | Documentation and test structure review | A coherent approach to test layers is evident |
| QRA-02 | The strategy distinguishes unit, integration, and end-to-end tests | Test structure review | Tests at multiple levels exist in the test suite |
| QRA-03 | The strategy is appropriate for the system type | Strategy and system review | Not exclusively unit tests for a systems-integration-heavy product; not exclusively e2e for a pure computation module |

### 7.2 Test Coverage

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| QRA-04 | All High-risk changed areas have integration-level test coverage | Coverage map | No High-risk changed area is tested only at unit level or not at all |
| QRA-05 | Happy path is tested for all new functionality | Test review | At least one test confirms the primary success path for each new feature |
| QRA-06 | Primary error path is tested for all new functionality | Test review | At least one test confirms the primary failure path |
| QRA-07 | Boundary conditions are tested where applicable | Test review | Inputs at and beyond defined boundaries are tested |
| QRA-08 | Coverage gaps are documented and risk-assessed | Known Issues or Change Summary | Untested areas are known, documented, and the risk is accepted |

### 7.3 Test Quality

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| QRA-09 | Tests assert specific expected values, not merely absence of error | Test code review (sample) | No tautological tests (assert-no-exception-was-thrown as the only assertion) |
| QRA-10 | Tests are isolated from each other | Test code review | No shared mutable state between tests; no order dependency |
| QRA-11 | Tests are isolated from external services | Test code review | External calls are mocked or stubbed in unit tests |
| QRA-12 | Tests are deterministic | Test code review and CI history | No time-dependent, random, or environment-sensitive assertions |
| QRA-13 | Test names describe expected behaviour | Test code review | Names are of the form "should [behaviour] when [condition]" or equivalent |
| QRA-14 | Flaky tests are not present in the suite | CI history | No tests with an intermittent failure history are in the passing test suite |

### 7.4 Failure Mode Coverage

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| QRA-15 | Unavailable upstream dependency is handled and tested | Code and test review | Failure of each external dependency has a defined handling path and a test |
| QRA-16 | Storage operation failure is handled and tested | Code and test review | Storage errors produce a defined response, not an unhandled exception |
| QRA-17 | Concurrent access is assessed and tested where applicable | Code and test review | Race conditions are identified and either mitigated or accepted with documentation |

### 7.5 Reliability Mechanisms

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| QRA-18 | External calls have timeouts | Code review | No unbounded external calls |
| QRA-19 | Retry logic is bounded | Code review | Retry loops have a maximum attempt count and back-off |
| QRA-20 | Idempotency is implemented where retries are possible | Code review | Operations that may be retried are idempotent or retry safety is documented |
| QRA-21 | Graceful degradation is implemented for non-critical dependencies | Code review | Failure of optional features does not prevent core functionality |

### 7.6 Defect Management

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| QRA-22 | All open defects are triaged with severity | Known Issues Register review | No untriaged defects |
| QRA-23 | No high-severity open defect is misclassified at a lower severity | Register review with QRA's assessment | QRA's independent severity assessment aligns with register classification |
| QRA-24 | High-severity defects have resolution timelines | Register review | All high-severity open defects have target dates |
| QRA-25 | No open defect should block this release per the test policy | Register and test policy review | No release-blocking defects are present and open |

---

## 8. Evidence Standards

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| Tautological test | T2 | Test code showing assertion that only verifies no exception was thrown |
| Missing coverage | T2 | Code path in diff with no corresponding test in test suite |
| Flaky test | T1 | CI history showing intermittent failure for a specific test |
| Missing timeout | T2 | Code showing external call without timeout parameter |
| Defect misclassification | T4 (with T3 support) | Known Issues entry; QRA's reasoned assessment of correct severity with reference to severity classification rules |

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND.

---

## 9. Finding Classification Guidance

### SEV-1 for QA and Reliability Audit

- A High-risk path (data integrity, authentication, billing) has zero test coverage at integration or end-to-end level.
- A test suite has been manipulated to produce passing results for failing tests (coordinate with DEA).
- An open release-blocking defect is present and has been misclassified to avoid blocking the release.
- There is no test evidence whatsoever for a materially significant functional area.

### SEV-2 for QA and Reliability Audit

- Multiple tautological tests in critical paths that provide false quality confidence.
- A High-risk changed area lacks primary error path tests.
- External calls in the critical path have no timeout.
- Retry logic is unbounded (potential infinite loop under failure conditions).
- A high-severity defect is open without a resolution timeline.
- Known flaky tests are in the passing test suite, providing unreliable quality signal.

### SEV-3 for QA and Reliability Audit

- Medium-risk areas lack boundary condition tests.
- Minor tautological tests in non-critical paths.
- Retry logic is bounded but back-off is not implemented.
- Open defects are triaged but resolution timelines are missing for medium-severity issues.
- Test names do not describe behaviour, reducing maintainability.

### SEV-4 for QA and Reliability Audit

- Test structure or naming conventions are inconsistent but not misleading.
- Coverage gaps in low-risk areas with no foreseeable user impact.

---

## 10. Board Decision Contribution

The QRA does not issue a Board outcome or process status. The QRA raises findings and records whether in-scope test and reliability evidence is `SUFFICIENT`, `INSUFFICIENT`, or `NOT_APPLICABLE` for a PASS-class conclusion, with missing evidence listed.

The QRA must state whether the test suite provides trustworthy quality assurance for the artefact under review. This evidence-sufficiency contribution is traceable, not a Board vote or outcome.

---

## 11. Required Output

### QA and Reliability Audit Report

```
QA AND RELIABILITY AUDIT REPORT
=================================
Document ID:        TPL-QRAR
Review ID:
QRA Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-005 [version]

RISK PROFILE ASSESSMENT
Change risk profile: [ ] HIGH  [ ] MEDIUM  [ ] LOW
Basis for risk profile:

TEST STRATEGY ASSESSMENT
Strategy documented: [ ] YES  [ ] NO  [ ] IMPLIED
Test layers present: [ ] Unit  [ ] Integration  [ ] End-to-End  [ ] System
Strategy assessment: [ ] ADEQUATE  [ ] PARTIAL  [ ] ABSENT

COVERAGE ASSESSMENT
High-risk changed areas: [count]
High-risk areas with integration/e2e coverage: [count]
High-risk coverage gaps: [list]

TEST QUALITY ASSESSMENT
Sample size examined: [count tests]
Tautological tests found in sample: [count]
Isolated tests: [ ] ALL  [ ] MOST  [ ] SOME  [ ] NONE
Deterministic tests: [ ] ALL  [ ] MOST  [ ] SOME  [ ] NONE
Flaky tests identified: [count]

FAILURE MODE COVERAGE
External dependency failure coverage: [ ] PRESENT  [ ] PARTIAL  [ ] ABSENT
Storage failure coverage: [ ] PRESENT  [ ] PARTIAL  [ ] ABSENT
Concurrent access assessment: [ ] PRESENT  [ ] PARTIAL  [ ] ABSENT  [ ] NOT APPLICABLE

RELIABILITY MECHANISMS
External call timeouts: [ ] ALL BOUNDED  [ ] SOME UNBOUNDED  [ ] NOT APPLICABLE
Retry logic: [ ] BOUNDED  [ ] UNBOUNDED  [ ] ABSENT  [ ] NOT APPLICABLE
Graceful degradation: [ ] PRESENT  [ ] PARTIAL  [ ] ABSENT  [ ] NOT APPLICABLE

DEFECT MANAGEMENT
All defects triaged: [ ] YES  [ ] NO
Misclassified high-severity defects: [count]
High-severity defects without timelines: [count]
Release-blocking defects open: [ ] YES — [list]  [ ] NO

FINDINGS SUMMARY:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]

FINDINGS:
[For each finding, attach a completed TPL-FND]

TEST SUITE TRUSTWORTHINESS ASSESSMENT:
[ ] The test suite provides trustworthy quality assurance for this artefact.
[ ] The test suite provides partial quality assurance — material gaps noted above.
[ ] The test suite does not provide adequate quality assurance for this artefact.

Basis for assessment:

PASS-CLASS EVIDENCE SUFFICIENCY:
[ ] SUFFICIENT  [ ] INSUFFICIENT  [ ] NOT APPLICABLE
Missing evidence / limitations:

AI ASSISTANCE:
[ ] AI tools were used — describe what for and confirm independent verification of all findings
[ ] AI tools were not used

QRA Signature:
Date:
```

---

## 12. Reviewer Prompt Conversion Notes

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human QA and Reliability Auditor. You do not hold the QRA role, count toward quorum, assign severity, sign findings, or issue an outcome. Help inspect whether the right things are tested in the right way."

**Key Prompt Constraints:**
- Must assess test quality from the test implementation, not just from coverage numbers.
- Must distinguish meaningful coverage from coverage that provides false confidence.
- Must assess reliability mechanisms independently of performance (defer performance questions to POA).
- Must not accept test coverage claims without examining actual test code.
- Must not raise findings about GS-P001 test suites.
- Must label every output as an unsigned draft; trustworthiness and evidence sufficiency remain human reviewer acts.

**Inputs to Prompt:** Test Evidence Package, test source files, coverage report (if available), Known Issues Register, Change Summary with risk characterisation, CI pipeline definition.

**Output Format:** Unsigned draft report matching §11, with evidence candidates for human verification. TPL-FND records become valid only after the named human QRA verifies evidence, supplies severity, and signs.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception note to §8; status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned terminology and evidence-sufficiency contribution with RBM-001 v2.0.0. |

*End of RBS-005 v2.0.0*
