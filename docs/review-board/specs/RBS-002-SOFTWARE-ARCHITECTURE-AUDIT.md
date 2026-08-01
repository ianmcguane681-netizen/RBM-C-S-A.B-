# Reviewer Specification: Software Architecture Audit

**Document ID:** RBS-002
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** Software Architecture Auditor (SAA)
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

The Software Architecture Auditor (SAA) assesses whether the artefact under review is structurally sound, internally consistent, and aligned with the architectural decisions and constraints that govern Provena Foundry. The SAA's focus is structure, not behaviour — the SAA does not re-run tests or re-assess business logic, but examines whether the code is organised, coupled, and extended in ways that are sustainable, comprehensible, and safe.

The SAA must be a practitioner with direct software engineering and architectural design experience. The role requires the ability to read code, evaluate dependency graphs, assess API design, and identify structural anti-patterns.

---

## 2. Scope

The SAA's scope encompasses:

- Conformance with documented architectural decisions and patterns for Provena Foundry.
- Structural quality of new or modified modules, services, and components.
- Dependency management: direction of dependencies, coupling, and dependency version hygiene.
- API design quality and backward compatibility for any API changes.
- Data model changes and their structural implications.
- Separation of concerns and appropriate layering.
- Error handling architecture.
- Configuration and environment variable management.
- Build and packaging structure.
- Code removed from the artefact (dead code, orphaned dependencies).

The SAA's scope does **not** encompass:

- Performance measurement (Performance and Operations Auditor).
- Security control implementation (Security and Privacy Auditor).
- Test coverage (QA and Reliability Auditor).
- Business logic correctness (Business and Commercial Auditor assesses commercial alignment; QA assesses correctness through tests).
- GS-P001 code, even if shared libraries are in scope.

---

## 3. Responsibilities

| Responsibility | Timing |
|---------------|--------|
| Review the Change Summary and Scope Statement to determine architectural review scope | Start of review |
| Examine the architectural decision record (if present) for decisions applicable to this change | Start of review |
| Review all files in the change set that constitute structural changes | During review |
| Assess dependency manifest against known architectural constraints | During review |
| Raise findings per §7 checklist | During review |
| Produce the SAA Report | End of review |

---

## 4. Independence Rules

The SAA must not have:
- Designed the architectural approach implemented in the artefact under review.
- Co-authored more than 20% of the changed files by line count.

Where the SAA has contributed to architectural decisions that are being implemented (not designed for the first time), they must declare this in their Independence Declaration and limit their finding scope to areas where they have no authorial stake.

---

## 5. Required Inputs

| Input | Source | Required Condition |
|-------|--------|--------------------|
| Artefact version (commit SHA or equivalent) | Review Initiation Record | Always |
| Complete diff of changed files | Authoring team or VCS | Always |
| Architectural decision record (ADR) or equivalent | Authoring team | If exists |
| Dependency manifest | Input Package | Always |
| API specification (current and prior version) | Input Package | If API changes are in scope |
| Database schema (current and prior version) | Input Package | If schema changes are in scope |
| System architecture diagram (current) | Input Package | If available |
| Previous SAA review findings | Previous Review Record | Re-reviews only |

---

## 6. Audit Procedure

### Step 1 — Change Characterisation

Read the Change Summary and Scope Statement. Categorise the change:

- **Structural change:** New module, service, component, or layer introduced.
- **Dependency change:** New dependencies added, existing dependencies upgraded or removed.
- **API change:** Public or internal API interface added, modified, or removed.
- **Data model change:** Schema or data structure added, modified, or removed.
- **Refactor:** Internal reorganisation without interface change.
- **Configuration change:** Environment variable, feature flag, or build configuration change.

Each category has specific checklist sections. Identify which apply.

### Step 2 — Architectural Conformance

Compare the change against the documented architectural decisions (ADR) for Provena Foundry. For each applicable ADR:
- Is the change consistent with the decision?
- If not, is there a documented rationale for deviation?

A deviation without documented rationale is a finding. A deviation with documented rationale is an observation at minimum; assess whether the rationale is sound.

### Step 3 — Structural Analysis

Examine the changed code structurally:
- Dependency direction: do dependencies flow in the correct direction per the architecture?
- Layer violations: does any lower-layer component depend on a higher-layer component?
- Coupling: has the change increased coupling between components that should be decoupled?
- Cohesion: are new modules focused on a single responsibility?
- Error propagation: are errors handled at the appropriate layer?

### Step 4 — Dependency Analysis

Review the dependency manifest against the prior version:
- New dependencies: are they justified, actively maintained, and compatible with the Provena Foundry license model?
- Upgraded dependencies: are there known breaking changes?
- Removed dependencies: have all usages been cleaned up?
- Transitive dependencies: does any change introduce a transitive dependency conflict?

### Step 5 — API Review (if applicable)

Compare current and prior API specifications:
- Are breaking changes present?
- Are breaking changes declared and managed (versioning, deprecation notices, migration guidance)?
- Does the API design follow established Provena Foundry conventions?
- Are new endpoints consistent with existing naming, versioning, and contract patterns?

### Step 6 — Data Model Review (if applicable)

Compare current and prior schema or data structures:
- Are destructive changes present (column drops, type changes, constraint tightening)?
- Is a migration plan in place for destructive changes?
- Are new fields nullable where appropriate?
- Do naming conventions follow Provena Foundry standards?

### Step 7 — Configuration and Environment

Review any changes to configuration, environment variables, or feature flags:
- Are new environment variables documented?
- Are default values appropriate?
- Are sensitive configuration values handled correctly (not hardcoded)?
- Is the configuration change backward-compatible with existing deployments?

---

## 7. Checklist

### 7.1 Structural Integrity

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SAA-01 | Dependency direction conforms to architectural layering | Code review | No lower layer imports from a higher layer |
| SAA-02 | New modules have a single, clearly stated responsibility | Code review | Module scope is bounded and documented |
| SAA-03 | No circular dependencies introduced | Dependency analysis tool or manual trace | No cycles in the import graph |
| SAA-04 | Error handling is at the architecturally correct layer | Code review | Errors are not swallowed silently at lower layers |
| SAA-05 | Cross-cutting concerns (logging, auth, instrumentation) are not duplicated | Code review | Shared infrastructure is used; new implementations are justified |
| SAA-06 | Abstractions are not leaky | Code review | Implementation details of one component are not required knowledge for another |
| SAA-07 | Dead code is not introduced | Code review | No unreachable functions, disabled code paths, or commented-out logic committed |

### 7.2 Dependency Management

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SAA-08 | New dependencies are justified | Change Summary review | Rationale for new dependency is stated |
| SAA-09 | New dependencies are actively maintained | Dependency audit | Last release within 12 months; no archived status |
| SAA-10 | New dependencies are compatible with Provena Foundry license model | License check | No GPL or restrictive copyleft where commercial distribution is required |
| SAA-11 | Major version upgrades of dependencies are assessed for breaking changes | Changelog review | Breaking changes are documented and addressed |
| SAA-12 | Removed dependencies have all usages cleaned up | Code search | No remaining imports of removed packages |
| SAA-13 | No dependency conflicts introduced | Dependency resolution output | Lock file resolves cleanly without conflict warnings |

### 7.3 API Design (if applicable)

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SAA-14 | Breaking changes are identified and declared | API diff | All breaking changes are listed in the Change Summary |
| SAA-15 | Breaking changes have a migration path | Change Summary and API spec | Deprecation notice or versioning strategy is in place |
| SAA-16 | New endpoints follow Provena Foundry naming conventions | API spec review | Names, HTTP methods, and status codes are consistent with existing endpoints |
| SAA-17 | Response contracts are complete (all fields documented, types specified) | API spec review | No undocumented fields; types are explicit |
| SAA-18 | Error responses are consistent with the existing error contract | API spec review | Error shapes match the established error response model |

### 7.4 Data Model (if applicable)

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SAA-19 | Destructive schema changes are declared | Schema diff | All column drops, type changes, and constraint changes are listed in Change Summary |
| SAA-20 | Migration plan covers all destructive changes | Migration plan review | Each destructive change has a corresponding migration step |
| SAA-21 | New fields use appropriate nullability | Schema review | Required fields are NOT NULL; optional fields are nullable where appropriate |
| SAA-22 | Naming conventions are consistent | Schema review | New names follow established Provena Foundry conventions |
| SAA-23 | Indexes are appropriate for query patterns | Schema review | New tables/columns with expected query patterns have appropriate indexes |

### 7.5 Configuration and Environment

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SAA-24 | New environment variables are documented | Configuration documentation review | All new env vars are listed in the deployment documentation |
| SAA-25 | Sensitive values are not hardcoded | Code search | No secrets, tokens, or credentials in source files |
| SAA-26 | Configuration changes are backward-compatible | Review | Existing deployments can operate without supplying new required env vars (or rollout strategy is documented) |

### 7.6 Architectural Conformance

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SAA-27 | Change conforms to documented architectural decisions | ADR review | No undocumented ADR deviations |
| SAA-28 | Deviations from ADR have documented rationale | ADR and Change Summary review | Any deviation includes a written justification |
| SAA-29 | The architectural impact of this change is assessed | Change Summary review | Author has stated architectural implications; if none, this is explicit |

---

## 8. Evidence Standards

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| Circular dependency | T1 (tool output) or T2 (documented manual trace) | Dependency graph output showing cycle |
| Layer violation | T2 | Import statement in lower-layer file referencing higher-layer module |
| Breaking API change | T3 | API spec diff showing removed/modified field with no migration path |
| Unlicensed dependency | T1 or T2 | License file of dependency; package registry metadata |
| Hardcoded secret | T2 | Specific file path and line number containing the hardcoded value |
| ADR deviation | T3 | ADR text and the specific code section that deviates from it |

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND.

---

## 9. Finding Classification Guidance

### SEV-1 for Software Architecture Audit

- A secret, credential, or token is hardcoded in source code.
- A breaking API change is deployed without any versioning or migration strategy, creating data loss or client breakage risk.
- A destructive schema change is made without a migration plan, risking data loss.
- A dependency with a known critical vulnerability (CVSS 9.0+) is introduced (coordinate with Security and Privacy Auditor).

### SEV-2 for Software Architecture Audit

- A circular dependency is introduced.
- A significant layer violation that compromises the architectural integrity of a core component.
- A breaking API change without documented migration path (no data loss risk, but client breakage).
- A new mandatory environment variable is undocumented.
- A dependency without a maintainer or with an incompatible license is introduced.
- Dead code committed (more than trivial scope — a full module or significant function).

### SEV-3 for Software Architecture Audit

- Naming convention violations.
- Missing indexes for anticipated query patterns (no immediate impact but foreseeable performance risk).
- A dependency justified but not actively maintained (last release 12–24 months).
- Minor API inconsistencies (e.g., inconsistent HTTP method use for a non-critical endpoint).
- ADR deviation with documented rationale (the deviation is documented but the SAA considers it architecturally questionable).

### SEV-4 for Software Architecture Audit

- Naming style inconsistencies (minor).
- Structural suggestions that are improvements but not defects.
- Documentation gaps in configuration that are present but incomplete.

---

## 10. Board Decision Contribution

The SAA does not issue a Board outcome or process status. The SAA raises findings and records whether the in-scope architecture evidence is `SUFFICIENT`, `INSUFFICIENT`, or `NOT_APPLICABLE` for a PASS-class conclusion, with missing evidence listed. This contribution enters the sealed evidence-sufficiency record used by RBM-001 §10; it is not a vote or verdict.

---

## 11. Required Output

### Software Architecture Audit Report

```
SOFTWARE ARCHITECTURE AUDIT REPORT
====================================
Document ID:        TPL-SAAR
Review ID:
SAA Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-002 [version]

CHANGE CHARACTERISATION
Categories identified (check all that apply):
[ ] Structural change  [ ] Dependency change  [ ] API change
[ ] Data model change  [ ] Refactor  [ ] Configuration change

CHECKLIST SECTIONS IN SCOPE:
[List which checklist sections were assessed and which were out of scope with justification]

FINDINGS SUMMARY:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]

FINDINGS:
[For each finding, attach a completed TPL-FND]

STRUCTURAL RISK ASSESSMENT:
[Brief narrative — is the artefact structurally sound enough for its intended use?
This is not a vote; it is a professional assessment to assist the Board.]

ARCHITECTURAL DECISION CONFORMANCE:
[ ] Conforms to all applicable ADRs
[ ] Deviates from ADRs — deviations listed in findings above

PASS-CLASS EVIDENCE SUFFICIENCY:
[ ] SUFFICIENT  [ ] INSUFFICIENT  [ ] NOT APPLICABLE
Missing evidence / limitations:

AI ASSISTANCE:
[ ] AI tools were used — describe what for and confirm independent verification of all findings
[ ] AI tools were not used

SAA Signature:
Date:
```

---

## 12. Reviewer Prompt Conversion Notes

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human Software Architecture Auditor. You do not hold the SAA role, count toward quorum, assign severity, sign findings, or issue an outcome. Help locate evidence about structural soundness, dependency quality, API design, and architectural conformance."

**Key Prompt Constraints:**
- Must cite specific file paths and line numbers for all findings.
- Must not assess GS-P001 code or raise findings against shared libraries owned by GS-P001.
- Must distinguish between findings (non-conformances) and observations (improvement suggestions).
- Must not use AI-generated analysis as a finding without independent verification.
- Must label every output as an unsigned draft; severity and evidence sufficiency remain human reviewer acts.

**Inputs to Prompt:** Full diff of changed files, dependency manifest, current and prior API spec (if applicable), current and prior schema (if applicable), architectural decision record, Change Summary.

**Output Format:** Unsigned draft report matching §11, with evidence candidates for human verification. TPL-FND records become valid only after the named human SAA verifies evidence, supplies severity, and signs.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception note to §8; status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned terminology and decision contribution with RBM-001 v2.0.0; retained human authority and evidence requirements. |

*End of RBS-002 v2.0.0*
