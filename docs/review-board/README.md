# Provena Foundry Review Board — Methodology Profile Package

**Package Version:** 2.0.0
**Status:** RELEASE-CANDIDATE — Pending named human Principal Architect and Methodology Owner approval
**Applicability:** Provena Foundry only. Not applicable to GS-P001.
**Architecture Authority:** RBE-001 v1.1.0 or a later approved compatible release
**Profile:** [`PROFILE.json`](PROFILE.json)
**Manifest:** [`MANIFEST.json`](MANIFEST.json)
**Human Approval Record:** Not issued
**Last Updated:** 2026-07-19

> **Note:** This package is a release-candidate methodology profile subordinate to RBE-001. It cannot govern binding Board decisions until the applicable RBE release and this exact checksummed profile receive named human approval, `PROFILE.json` becomes `ACTIVE`, and the package is tagged. A merge or AI review is not activation.

---

## Overview

This directory contains the RBM-001 methodology profile and its reviewer specifications for the Provena Foundry Review Board. RBE-001 remains the higher constitutional and architectural authority. The package is designed to:

1. **Be committed to GitHub** as a versioned, checksummed methodology profile beneath RBE-001.
2. **Be converted into individual reviewer prompts** — each specification includes a `Reviewer Prompt Conversion Notes` section with the identity, constraints, inputs, and output format required to instantiate that reviewer as an AI-assisted or human-guided review agent.
3. **Be compiled into an orchestration build specification** — the sequencing rules, input/output dependencies, tier routing, and schema references provide the contract for an orchestration layer that manages review workflow.

---

## Document Map

### Governing Methodology

| File | ID | Version | Description |
|------|----|---------|-------------|
| [`REVIEW-BOARD-METHODOLOGY.md`](REVIEW-BOARD-METHODOLOGY.md) | RBM-001 | 2.0.0 | Methodology profile. Reviewer specifications are subordinate to it; the profile is subordinate to RBE-001. |

### Control Artifacts

| File | Purpose |
|---|---|
| [`PROFILE.json`](PROFILE.json) | Machine-readable profile identity, outcomes, process statuses, role policy, quorum, lifecycle mapping, activation requirements, and checksum |
| [`MANIFEST.json`](MANIFEST.json) | Checksums and sizes for every controlled package file plus deterministic root hash |
| [`schemas/`](schemas/) | Versioned machine-readable record contracts |
| [`RBM-001_PRINCIPAL_REVIEW_v2.0.0.md`](RBM-001_PRINCIPAL_REVIEW_v2.0.0.md) | Findings, resolutions, validation, and non-activation boundary |

### Reviewer Specifications

| File | ID | Version | Role | Abbrev |
|------|----|---------|------|--------|
| [`specs/RBS-001-METHODOLOGY-AUDIT.md`](specs/RBS-001-METHODOLOGY-AUDIT.md) | RBS-001 | 2.0.0 | Methodology Auditor | MA |
| [`specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md`](specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md) | RBS-002 | 2.0.0 | Software Architecture Auditor | SAA |
| [`specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md`](specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md) | RBS-003 | 2.0.0 | Business and Commercial Auditor | BCA |
| [`specs/RBS-004-DATA-EVIDENCE-AUDIT.md`](specs/RBS-004-DATA-EVIDENCE-AUDIT.md) | RBS-004 | 2.0.0 | Data and Evidence Auditor | DEA |
| [`specs/RBS-005-QA-RELIABILITY-AUDIT.md`](specs/RBS-005-QA-RELIABILITY-AUDIT.md) | RBS-005 | 2.0.0 | QA and Reliability Auditor | QRA |
| [`specs/RBS-006-SECURITY-PRIVACY-AUDIT.md`](specs/RBS-006-SECURITY-PRIVACY-AUDIT.md) | RBS-006 | 2.0.0 | Security and Privacy Auditor | SPA |
| [`specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md`](specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md) | RBS-007 | 2.0.0 | Performance and Operations Auditor | POA |
| [`specs/RBS-008-SCEPTICAL-REVIEW.md`](specs/RBS-008-SCEPTICAL-REVIEW.md) | RBS-008 | 2.0.0 | Sceptical Reviewer | SR |

---

## Review Execution Sequence

The execution sequence depends on the assigned review risk tier (§6A of RBM-001). Steps within the same phase may execute in parallel. Steps in a later phase must not begin until all prior-phase steps are complete.

### Tier 1 — Lightweight

```
PHASE 0 — Pre-Review
  Board Chair:    Issue Review Initiation Record (TPL-RIR) with Tier 1 classification
  MA:             Validate Input Package (TPL-IPV)
  Reviewers:      Submit Independence Declarations (TPL-IND)
  [GATE: READY continues; PROCEDURALLY_INCOMPLETE returns the package]

PHASE 1 — Specialist Reviews (parallel)
  Two of {SAA, QRA, POA} — selected by Board Chair for the specific change scope
  [SEV-1 findings escalated immediately regardless of tier]

PHASE 2 — Challenge
  SR:  Sceptical Review + SR Challenge Questions
  Board Chair:  Obtain traceable answers; unresolved challenge means BLOCKED

PHASE 3 — Consolidation, Governance Validation, Decision, Publication
  Board Chair:  Assemble unsigned decision candidate under §10.3
  MA:           Process Integrity Audit + independent candidate validation
  Board Chair:  Sign validated TPL-BDR
  Independent publication control: validate and publish TPL-MRI
```

### Tier 2 — Standard

```
PHASE 0 — Pre-Review
  Board Chair:    Issue TPL-RIR with Tier 2 classification
  MA:             Validate Input Package (TPL-IPV)
  All reviewers:  Submit Independence Declarations (TPL-IND)
  [GATE: READY continues; PROCEDURALLY_INCOMPLETE returns the package]

PHASE 1 — Specialist Reviews (parallel)
  SAA:  Software Architecture Audit
  BCA:  Business and Commercial Audit
  DEA:  Data and Evidence Audit
  QRA:  QA and Reliability Audit
  SPA:  Security and Privacy Audit   [SEV-1 findings escalated immediately]
  POA:  Performance and Operations Audit
  [Minimum four of six; all six preferred]

PHASE 2 — Challenge
  SR:  Sceptical Review (reviews Phase 1 reports)
  SR:  Issues SR Challenge Questions
  Board Chair:  Obtain traceable answers; unresolved challenge means BLOCKED

PHASE 3 — Consolidation, Governance Validation, Decision, Publication
  Board Chair:  Assemble unsigned decision candidate under §10.3
  MA:           Process Integrity Audit + independent candidate validation
  Board Chair:  Sign validated TPL-BDR
  Independent publication control: validate and publish TPL-MRI
  BCA:          Issues Milestone-Completion Confirmation (if applicable)
```

### Tier 3 — Full Board

```
Same sequence as Tier 2, with:
  — All nine roles mandatory; no omissions permitted
  — Nine distinct named humans; roles cannot be merged
  — SR report must include explicit Tier 3 Risk Characterisation section
  — BCA must confirm commercial invoicing gate scope limitation (§18.2)
  — No process, quorum, finding, or publication waiver is available
```

---

## Review Risk Tiers — Quick Reference

Full definitions in RBM-001 §6A. Tier is proposed by authoring team, validated by MA, confirmed by Board Chair.

| Tier | Label | Typical Changes | Required Reviewers |
|------|-------|-----------------|-------------------|
| 1 | Lightweight | Non-functional doc corrections, test-only, patch upgrades, safe config | BC + MA + 2 of {SAA, QRA, POA} + SR |
| 2 | Standard | Code changes, API changes, data model, major/minor upgrades | BC + MA + ≥4 specialists + SR |
| 3 | Full Board | Security, data contracts, milestones, methodology changes, post-incident | All 9 roles, no omissions |

Any trigger condition in RBM-001 §6 mandating Tier 3 overrides a lower tier proposal. Tiers can be escalated, never de-escalated.

---

## Key Decision Rules (Summary)

Full rules are in RBM-001 §10. Process status is evaluated first. A non-`READY` process has no substantive outcome. For `READY` inputs, evaluate the outcome rules in order.

| Check | Outcome |
|-------|---------|
| Process incomplete, blocked, or void | No outcome; merge blocked |
| Any unresolved SEV-1 | `FAIL` |
| Two or more unresolved SEV-2 | `FAIL` |
| One unresolved SEV-2 without accepted remediation | `FAIL` |
| Evidence insufficient for a defensible PASS-class conclusion | `INSUFFICIENT_EVIDENCE` |
| One unresolved SEV-2 with accepted remediation | `PASS_WITH_FINDINGS` |
| No unresolved SEV-1/2 and evidence sufficient | `PASS` |

The Board Chair assembles the candidate, the MA validates it independently, the Board Chair signs it, and independent publication control releases it. There is no vote or discretionary override.

---

## Human Sign-off Boundaries

AI agents may assist in locating evidence, formatting reports, and running automated tools. The following acts require a named human reviewer's explicit signature before the record is accepted into the audit trail:

| Act | Required Signatory |
|----|-------------------|
| Independence Declaration | The named reviewer |
| Finding raised at SEV-1 or SEV-2 | The named specialist reviewer |
| Finding closure (SEV-1/SEV-2) | Closure reviewer (different person from finder) |
| Board Decision Record | Board Chair |
| Governance validation | Methodology Auditor |
| Decision publication | Independent publication control |
| Milestone-Completion Confirmation | Business and Commercial Auditor |
| MA Report (process integrity phase) | Methodology Auditor |
| Correction Record | Panel Chair |

---

## Evidence Tier Quick Reference

| Tier | Name | Admissible for SEV-1? | Admissible for SEV-2? |
|------|----|----------------------|----------------------|
| T1 | Direct Instrument (automated tool output) | Yes | Yes |
| T2 | Direct Observation (reviewer procedure) | Yes | Yes |
| T3 | Documentary Reference (spec/contract/regulation) | With T3-AUTHORITATIVE-EXTERNAL conditions (see §8.2) | Yes |
| T4 | Reasoned Inference | No | No |
| T5 | Assertion | No — never admissible | No — never admissible |

**T3-AUTHORITATIVE-EXTERNAL exception:** T3 is admissible for SEV-1 when: (1) the reference is an authoritative legal/regulatory/contractual/technical standard; (2) the specific clause is named; (3) direct applicability is shown in one logical step; (4) the document is confirmed currently in force. All four conditions required.

---

## Severity Reference

| Severity | Merge Impact | Example |
|----------|-------------|---------|
| SEV-1 — Critical | Hard block, no waiver | Authentication bypass; data corruption; hardcoded secret; confirmed regulatory violation |
| SEV-2 — Major | Block unless single finding with accepted remediation plan | Missing test coverage on critical path; SLA breach; unlicensed dependency |
| SEV-3 — Minor | No block; tracked in register | Naming convention violation; missing index; incomplete documentation |
| SEV-4 — Observation | No impact; recorded for reference | Style suggestions; minor improvements |

---

## Template and Schema Reference

All templates are defined in RBM-001 §17. Normative JSON Schemas are versioned under `schemas/` and indexed in §17.9.

| Template ID | Name | Owner | Schema |
|-------------|------|-------|--------|
| TPL-RIR | Review Initiation Record | Board Chair | `schemas/tpl-rir.schema.json` |
| TPL-IND | Independence Declaration | Each reviewer | — |
| TPL-IPV | Input Package Validation | MA | — |
| TPL-FND | Finding Record | Each reviewer | `schemas/tpl-fnd.schema.json` |
| TPL-RRR | Reviewer Report | Each reviewer | `schemas/tpl-rrr.schema.json` |
| TPL-BDR | Board Decision Record | Board Chair | `schemas/tpl-bdr.schema.json` |
| TPL-RMP | Remediation Plan | Authoring team | `schemas/tpl-rmp.schema.json` |
| TPL-RVR | Re-Review Record | Board Chair | — |
| TPL-MRI | Machine-Readable Indicator | Publication control | `schemas/tpl-mri.schema.json` |
| TPL-COR | Correction Record | Panel Chair | `schemas/tpl-cor.schema.json` |

Reviewer-specific report templates: TPL-MAR (MA), TPL-SAAR (SAA), TPL-BCAR (BCA), TPL-DEAR (DEA), TPL-QRAR (QRA), TPL-SPAR (SPA), TPL-POAR (POA), TPL-SRR (SR).

---

## Orchestration Build Specification — Contracts

Input/output contract for each reviewer role, for use by an orchestration build specification. Tier column shows the minimum tier at which the role is engaged.

| Role | Min Tier | Phase | Inputs Required | Primary Output | Secondary Outputs |
|------|---------|-------|----------------|----------------|-------------------|
| MA (gate) | 1 | 0 | Input Package, TPL-RIR | TPL-IPV (`READY` or `PROCEDURALLY_INCOMPLETE`) | Tier validation |
| SAA | 1* | 1 | Diff, dependency manifest, API spec, schema, ADR | TPL-SAAR + TPL-FND[] | — |
| BCA | 2 | 1 | Requirements, acceptance criteria, contracts, Known Issues | TPL-BCAR + TPL-FND[] | Milestone-Completion Confirmation (conditional) |
| DEA | 2 | 1 | Test results, Known Issues, data model, CI config | TPL-DEAR + TPL-FND[] | Evidence fabrication flag |
| QRA | 1* | 1 | Test results, test source, Known Issues, CI config | TPL-QRAR + TPL-FND[] | Trust assessment |
| SPA | 3** | 1 | SAST, dep scan, DAST, privacy assessment, diff | TPL-SPAR + TPL-FND[] | Immediate SEV-1 escalation |
| POA | 1* | 1 | Benchmarks, baseline, SLA, exec plans, monitoring config | TPL-POAR + TPL-FND[] | Operational readiness opinion |
| MA (governance) | 1 | 3 | All reports, sealed finding snapshot, evidence-sufficiency record, unsigned TPL-BDR | Signed TPL-MAR + governance validation | Canonical process status |
| SR | 1 | 2 | All Phase-1 reports, all TPL-FND, Input Package | TPL-SRCQ + TPL-SRR + TPL-FND[] | Re-open recommendation |
| Board Chair | 1 | 3 | All reports, sealed snapshot, SR challenge answers | Unsigned candidate then signed TPL-BDR after MA validation | TPL-COR (if correction) |
| Publication control | 1 | 3 | Signed TPL-BDR, MA validation, profile and manifest | Published TPL-MRI | Branch-protection result |

\* Tier 1 engages two of {SAA, QRA, POA} — Board Chair selects the most relevant for the change.
\*\* SPA is required at Tier 3 and whenever any security trigger condition in §6 applies.

---

## Appeal and Correction — Summary

Full process in RBM-001 §18A.

- **Window:** 5 business days from Board Decision.
- **Valid grounds:** Procedural error, new material evidence, decision rule misapplication.
- **Invalid grounds:** Schedule pressure, commercial urgency, disagreement with technical merit without new evidence.
- **Outcome:** Correction Record (TPL-COR) appended — original records preserved unchanged. Revised TPL-MRI issued if decision is corrected.
- **Lineage:** `correction_ref` in TPL-MRI chains to TPL-COR; most recent operative record governs.

---

## GS-P001 Boundary

This entire package is scoped to Provena Foundry. GS-P001 is governed by a separate methodology. Where Provena Foundry shares infrastructure or libraries with GS-P001, findings must be scoped to the Provena Foundry usage of that component. Findings must not be raised against GS-P001–governed assets under this methodology.

---

## Versioning

This package follows semantic versioning per RBM-001 §16.1. Changes require updating:

1. The document version and status.
2. The `Document History` table in the changed document.
3. The `Reviewer Specification Index` in RBM-001 if a spec version changes.
4. This README's package version.
5. `PROFILE.json`, schemas, package manifest, and validator fixtures.

## Controlled Validation

Run `python scripts/validate_rbm001_package.py --write` after changing controlled files; it normalizes controlled text to LF before rebuilding checksums. Then run `python scripts/validate_rbm001_package.py --check` before review or publication. The validator verifies canonical line endings, the profile checksum, controlled-file manifest, complete RBE lifecycle mapping, decision precedence, schema set, and release-candidate activation boundary. Its `validate_decision_bundle()` contract additionally checks TPL-RIR, TPL-BDR, and TPL-MRI identity, quorum, role separation, deterministic outcome, and merge-authorisation invariants.

## Activation Boundary

This package remains non-binding. Activation requires the exact sequence in RBM-001 §16.2, including named human Principal Architect and Methodology Owner approval of the exact profile checksum and a new immutable tagged commit. The current pull request may establish technical readiness; it cannot itself activate the methodology.

---

*End of README — Provena Foundry Review Board Methodology Profile Package v2.0.0*
