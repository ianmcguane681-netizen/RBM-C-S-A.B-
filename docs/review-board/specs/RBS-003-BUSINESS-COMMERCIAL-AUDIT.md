# Reviewer Specification: Business and Commercial Audit

**Document ID:** RBS-003
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** Business and Commercial Auditor (BCA)
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
11. [Milestone-Completion Confirmation](#11-milestone-completion-confirmation)
12. [Required Output](#12-required-output)
13. [Reviewer Prompt Conversion Notes](#13-reviewer-prompt-conversion-notes)

---

## 1. Role Definition

The Business and Commercial Auditor (BCA) assesses whether the artefact under review meets the commercial obligations, contractual requirements, and business acceptance criteria relevant to Provena Foundry. The BCA bridges technical delivery and commercial accountability.

The BCA's function is not to validate technical correctness (that is the domain of QA, Security, Architecture, and Performance auditors). The BCA's function is to determine whether what has been delivered aligns with what was committed, whether any commercial risk has been introduced or left unaddressed, and whether the milestone completion claim is defensible.

The BCA must have sufficient understanding of the relevant commercial agreements and business requirements to assess alignment. The BCA must be willing to issue a FAIL-contributing finding even when a release is commercially attractive to deliver.

---

## 2. Scope

The BCA's scope encompasses:

- Alignment of the artefact with stated business requirements and acceptance criteria.
- Conformance with contractual obligations (SLAs, data sovereignty, feature commitments).
- Assessment of commercial risk introduced by the change.
- Licensing obligations created by new dependencies or integrations.
- Milestone completion certification (where the review is a milestone gate).
- Identification of functionality gaps that affect commercial commitments.
- Known issues that affect client-facing behaviour and have not been disclosed or accepted.
- Regulatory or compliance obligations relevant to the commercial context.

The BCA's scope does **not** encompass:

- Technical implementation details (deferred to specialist auditors).
- Test methodology (QA and Reliability Auditor).
- Security technical controls (Security and Privacy Auditor).
- GS-P001 commercial obligations.

---

## 3. Responsibilities

| Responsibility | Timing |
|---------------|--------|
| Obtain and review the relevant commercial agreements, SLAs, and acceptance criteria | Start of review |
| Identify all requirements, stories, or commitments that are in scope for this artefact | Start of review |
| Trace each in-scope requirement to a specific deliverable in the artefact | During review |
| Assess the Known Issues Register for commercial impact | During review |
| Assess any new commercial risk introduced by the change | During review |
| Issue Milestone-Completion Confirmation (separate from Board Decision Record) for milestone reviews | End of review |
| Produce the BCA Report | End of review |

---

## 4. Independence Rules

The BCA must not:

- Hold a financial stake in the delivery outcome (e.g., a commission, bonus, or client relationship income contingent on this release).
- Be the business owner who signed the requirements being assessed.
- Have written the acceptance criteria being evaluated.

Where the BCA has a commercial relationship with the client or beneficiary of the release, this must be declared. The Board Chair determines whether recusal is required.

For milestone reviews linked to invoicing, the BCA must be organisationally independent from both the authoring team and the commercial/sales team responsible for the client relationship.

---

## 5. Required Inputs

| Input | Source | Required Condition |
|-------|--------|--------------------|
| Commercial agreements, SLAs, or contracts relevant to this release | Business owner or legal | If milestone review or contractual obligation exists |
| Acceptance criteria for this milestone or release | Business owner or Product | Always |
| Requirements or user stories addressed by this artefact | Input Package | Always |
| Known Issues Register | Input Package | Always |
| Change Summary | Input Package | Always |
| Dependency manifest (for license review) | Input Package | Always |
| Previous BCA findings | Previous Review Record | Re-reviews only |
| Regulatory or compliance requirements applicable to this release | Business owner or legal | If regulated domain is in scope |

---

## 6. Audit Procedure

### Step 1 — Requirement Tracing

Enumerate all requirements, stories, and acceptance criteria that the authoring team has declared as addressed by this artefact. For each:

- Confirm it is present in the authoritative requirements source (not just in the Change Summary).
- Confirm the artefact provides evidence of fulfilment (test evidence, feature demonstration, specification match).
- Record any requirement that is declared addressed but lacks substantiating evidence.

### Step 2 — Gap Identification

Identify any requirements, acceptance criteria, or contractual commitments that:

- Were not declared as addressed by the authoring team but should be in scope for this release.
- Were declared as addressed but cannot be verified from the evidence provided.
- Were partially addressed (functionality present but not complete, or present but not conformant with the acceptance criterion).

### Step 3 — Known Issues Assessment

Review the Known Issues Register:

- For each known issue: assess whether it affects client-facing functionality or contractual commitments.
- Confirm the known issue is appropriately disclosed (not hidden or minimised).
- Determine whether any known issue constitutes a commercial breach of the relevant agreements.

A known issue that is disclosed and within agreed tolerance is not a finding. A known issue that constitutes a commercial breach, even if disclosed, is a SEV-1 finding.

### Step 4 — Commercial Risk Assessment

Assess the change for new commercial risk:

- Does the change alter client-facing behaviour in ways not declared in the Change Summary?
- Does the change affect pricing, billing, or licensing mechanisms?
- Does the change create or remove data that clients depend on?
- Does the change introduce a new dependency that creates commercial, licensing, or jurisdiction risk?
- Does the change affect the ability to meet existing SLAs?

### Step 5 — License Review

Review new dependencies for license obligations:

- Identify any dependency with a license that creates a commercial obligation (attribution, copyleft, patent grant, distribution restriction).
- Confirm that the obligation is known, accepted, and managed.

### Step 6 — Regulatory and Compliance Assessment (if applicable)

If the release touches a regulated domain (financial services, health data, government data, data sovereignty requirements):

- Confirm that the relevant regulatory obligations are identified.
- Confirm that the change is assessed against those obligations.
- Confirm that any regulatory risk is documented and accepted by the appropriate authority.

---

## 7. Checklist

### 7.1 Requirements Traceability

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| BCA-01 | All declared requirements are present in the authoritative requirements source | Requirements source comparison | No requirements exist only in the Change Summary |
| BCA-02 | Each declared requirement has substantiating evidence | Evidence review | Test result, demonstration record, or specification match exists for each |
| BCA-03 | No in-scope requirements are undeclared (gap check) | Requirements source vs. Change Summary | All requirements within the declared scope of this release are accounted for |
| BCA-04 | Partially addressed requirements are explicitly declared as such | Change Summary and Known Issues | No requirement is implicitly partially addressed |
| BCA-05 | Acceptance criteria are specific and binary (met or not met) | Acceptance criteria review | Criteria do not use vague language such as "good performance" or "reasonable security" without defined thresholds |

### 7.2 Contractual and SLA Compliance

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| BCA-06 | All contractual commitments due at this milestone are addressed | Contract vs. artefact | No contractual commitment is unaddressed or deferred without agreement |
| BCA-07 | SLA-relevant changes are assessed against the SLA | SLA document review | No SLA metric (uptime, response time, data accuracy) is demonstrably breached by this change |
| BCA-08 | Data sovereignty obligations are met | Scope and architecture review | No data leaves a required jurisdiction; no new jurisdiction is introduced without assessment |
| BCA-09 | Feature commitments are met or deferred with client agreement | Requirements vs. artefact | No feature committed to a client is absent without a documented deferral |

### 7.3 Known Issues

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| BCA-10 | Known Issues Register is complete and current | Review and cross-reference with QA findings | No issues discovered during this review cycle are absent from the register |
| BCA-11 | No known issue constitutes a commercial breach without accepted waiver | Known Issues vs. contract | Any issue that affects contractual obligations is either resolved or has an accepted waiver |
| BCA-12 | Known issues affecting client-facing functionality are disclosed to relevant stakeholders | Disclosure record | Clients are not unaware of limitations that affect their use of the system |

### 7.4 Commercial Risk

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| BCA-13 | Undeclared client-facing behaviour changes are absent | Change Summary vs. functional review | All client-observable changes are declared |
| BCA-14 | Pricing, billing, or licensing mechanisms are unaffected or the change is declared and approved | Change Summary and commercial review | No unintended commercial mechanism changes |
| BCA-15 | New dependencies do not create restrictive license obligations | License review | Any license obligation is known, accepted, and managed |
| BCA-16 | The change does not reduce the ability to meet existing SLAs | Architecture and performance review cross-reference | SLA risk is assessed; no unmitigated reduction in SLA capacity |

### 7.5 Regulatory and Compliance (if applicable)

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| BCA-17 | Regulatory obligations applicable to this release are identified | Regulatory register review | No applicable regulation is unidentified |
| BCA-18 | The change is assessed against each applicable regulatory obligation | Regulatory review | Each obligation is either met or a documented risk acceptance exists |

---

## 8. Evidence Standards

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| Unaddressed requirement | T3 | Requirements document showing requirement; Change Summary showing it is not addressed |
| SLA breach | T1 or T2 | Performance measurement or test output demonstrating breach of SLA metric |
| Commercial mechanism change | T3 | Contract or commercial agreement text vs. the actual behaviour of the changed system |
| License obligation | T2 | License file text and dependency usage pattern |
| Undisclosed client-facing change | T3 | Change Summary (absence) vs. functional behaviour documentation |
| Known issue constituting commercial breach | T3 | Known Issues Register entry cross-referenced with contract text |

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND. This exception is particularly relevant to BCA findings grounded in contractual commitments or regulatory obligations — e.g., a data sovereignty clause or a mandatory reporting requirement established by contract.

---

## 9. Finding Classification Guidance

### SEV-1 for Business and Commercial Audit

- A contractual commitment is demonstrably unmet and no deferral has been agreed with the relevant party.
- A known issue constitutes a breach of a commercial agreement and is undisclosed to the affected party.
- A data sovereignty obligation is violated (data has left or will leave a required jurisdiction).
- A regulatory obligation with mandatory legal compliance is not met and no accepted risk waiver exists.

### SEV-2 for Business and Commercial Audit

- A declared milestone requirement lacks substantiating evidence of completion.
- A client-facing behaviour change is not declared in the Change Summary.
- A commercial mechanism (pricing, billing) is changed without appropriate authorisation.
- A new dependency introduces a license obligation that is not documented or managed.
- A known issue that is within the Known Issues Register but which demonstrably affects a client commitment without any disclosure plan.

### SEV-3 for Business and Commercial Audit

- An acceptance criterion is vague (no defined threshold) and cannot be verified as met or not met.
- A partially addressed requirement is not explicitly declared as such.
- A regulatory risk is identified and is managed but is not documented in the appropriate register.
- A minor feature gap that does not breach a contractual commitment but reduces delivered value below stated intent.

### SEV-4 for Business and Commercial Audit

- Acceptance criteria documentation quality is poor but the acceptance criteria themselves can be reasonably inferred.
- Requirements traceability is incomplete in format but the substance can be reconstructed.

---

## 10. Board Decision Contribution

The BCA does not issue a Board outcome or process status. The BCA raises findings, records whether in-scope commercial evidence is `SUFFICIENT`, `INSUFFICIENT`, or `NOT_APPLICABLE` for a PASS-class conclusion, and issues a bounded commercial opinion:

**Commercially Sound:** Commercial evidence is sufficient and there are no unresolved SEV-1 or SEV-2 BCA findings. The evidence supports the scoped commercial obligations. The BCA may confirm milestone completion only if every RBM-001 §18 gate is also satisfied.

**Commercially Conditional:** Commercial evidence is sufficient and exactly one unresolved SEV-2 BCA finding has an accepted remediation plan. The BCA may confirm milestone completion only if the finding does not affect the assessed deliverable and every RBM-001 §18 gate is satisfied.

**Commercially Deficient:** One or more unresolved SEV-1 BCA findings, one unresolved SEV-2 without an accepted plan, or two or more unresolved SEV-2 BCA findings. The BCA cannot confirm milestone completion. Commercial invoicing must not proceed.

**Commercial Evidence Insufficient:** The available record cannot support a defensible commercial opinion. This contributes `INSUFFICIENT` to the evidence-sufficiency record; it must not be converted into a positive or negative commercial claim.

> **Scope limitation:** The BCA's commercial opinion and Milestone-Completion Confirmation govern the internal governance gate for invoicing. Where the relevant commercial agreement also requires a separate contractual client acceptance step, the BCA's confirmation is necessary but not sufficient for invoicing to proceed — both the BCA's confirmation and the client acceptance must be obtained.

---

## 11. Milestone-Completion Confirmation

The BCA is the only Board role that may author and sign Milestone-Completion Confirmation. This is a separate document from the Board Decision Record and must be issued independently. It cannot be issued when process status is not `READY`, outcome is `FAIL` or `INSUFFICIENT_EVIDENCE`, the methodology profile is not ACTIVE, or publication control has not released the validated decision.

Milestone-Completion Confirmation must:

- Name the specific milestone being assessed.
- Reference the relevant commercial agreement or contractual milestone definition.
- Reference the Board Review ID.
- State that all milestone deliverables are met (or list any conditional matters).
- Be signed by the BCA.
- Not be issued while any SEV-1 BCA finding is Open.
- Include the governance-record disclaimer (see template below).

```
MILESTONE-COMPLETION CONFIRMATION
===================================
Document ID:
Review ID:
BCA Name:
Date:
Milestone Name / Reference:
Commercial Agreement Reference:
Artefact Identifier:

MILESTONE DELIVERABLES:
[List each deliverable and its verification status]

OPEN BCA FINDINGS AT TIME OF CONFIRMATION:
  SEV-1: [must be zero]
  SEV-2: [list any; state whether remediation plan is accepted]

COMMERCIAL ACCEPTANCE:
[ ] All milestone deliverables are met. No conditional matters.
[ ] All milestone deliverables are met, subject to the following conditions:
    [State conditions]
[ ] Milestone deliverables are NOT fully met. Commercial invoicing must not proceed.

GOVERNANCE RECORD NOTICE:
This document is a governance record confirming that the Provena Foundry Review Board
completed its review of the above milestone and that the declared deliverables were found
to meet the criteria assessed by the Board. It is not a warranty of fitness for purpose,
a representation of commercial readiness for any purpose beyond the internal invoicing gate,
or a substitute for any contractual client acceptance step required under the applicable
commercial agreement. Where the governing agreement specifies a separate client acceptance
process, that process must be completed independently.

BCA Signature:
Date:
```

---

## 12. Required Output

### Business and Commercial Audit Report

```
BUSINESS AND COMMERCIAL AUDIT REPORT
======================================
Document ID:        TPL-BCAR
Review ID:
BCA Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-003 [version]

COMMERCIAL CONTEXT
Is this a milestone review: [ ] YES  [ ] NO
If YES, milestone reference:
Commercial agreement(s) in scope:

REQUIREMENTS TRACEABILITY SUMMARY
Requirements declared as addressed: [count]
Requirements with substantiating evidence: [count]
Requirements without substantiating evidence: [list]
In-scope requirements not declared: [list]

CONTRACTUAL AND SLA COMPLIANCE
Contractual commitments assessed: [count]
Commitments met: [count]
Commitments unmet or deferred: [list with status]
SLA-relevant changes identified: [ ] YES  [ ] NO
SLA risk assessment: [summary]

KNOWN ISSUES COMMERCIAL IMPACT
Known issues with commercial impact: [count]
Issues constituting commercial breach: [count]
Disclosure status: [summary]

LICENSE OBLIGATIONS
New license obligations identified: [ ] YES  [ ] NO
If YES: [describe obligations and management status]

REGULATORY ASSESSMENT
Regulated scope: [ ] YES  [ ] NO
If YES: regulatory obligations identified and assessed: [ ] YES  [ ] NO  [ ] PARTIAL

FINDINGS SUMMARY:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]

FINDINGS:
[For each finding, attach a completed TPL-FND]

COMMERCIAL OPINION:
[ ] COMMERCIALLY SOUND
[ ] COMMERCIALLY CONDITIONAL — [describe condition]
[ ] COMMERCIALLY DEFICIENT — [describe basis]

MILESTONE-COMPLETION CONFIRMATION:
[ ] Issued separately (attached)
[ ] Not applicable (not a milestone review)
[ ] Cannot be issued (state reason)

PASS-CLASS EVIDENCE SUFFICIENCY:
[ ] SUFFICIENT  [ ] INSUFFICIENT  [ ] NOT APPLICABLE
Missing evidence / limitations:

AI ASSISTANCE:
[ ] AI tools were used — describe what for and confirm independent verification of all findings
[ ] AI tools were not used

BCA Signature:
Date:
```

---

## 13. Reviewer Prompt Conversion Notes

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human Business and Commercial Auditor. You do not hold the BCA role, count toward quorum, assign severity, sign findings, issue a Board outcome, or issue Milestone-Completion Confirmation. Help locate and organise traceable commercial evidence."

**Key Prompt Constraints:**
- Must not assess technical implementation quality — defer to specialist auditors.
- Must trace each requirement to specific evidence; must not accept authoring team assertions without evidence.
- Must not confuse GS-P001 commercial obligations with Provena Foundry obligations.
- Must issue findings even when this delays a commercially attractive release.
- Milestone-Completion Confirmation must never be issued while a SEV-1 BCA finding is Open.
- Milestone-Completion Confirmation is a governance record only — must not represent it as evidence of client acceptance, as a warranty of fitness, or as sufficient for invoicing where the commercial agreement also requires a separate contractual client acceptance step.
- Must label every output as an unsigned draft; commercial opinion, evidence sufficiency, and completion confirmation remain human reviewer acts.

**Inputs to Prompt:** Requirements source, acceptance criteria, commercial agreements (relevant excerpts), Known Issues Register, Change Summary, dependency manifest, previous BCA findings (re-reviews).

**Output Format:** Unsigned draft report matching §12, with evidence candidates for human verification. The AI must not generate an operative Milestone-Completion Confirmation. Any TPL-FND or confirmation becomes valid only after the named human BCA verifies, completes, and signs it.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception; updated §10 commercial opinion to clarify invoicing gate scope limitation; updated §11 Milestone-Completion Confirmation with governance-record disclaimer; updated §13 prompt constraints accordingly; status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned terminology and milestone controls with RBM-001 v2.0.0; prohibited release-candidate or insufficient-evidence completion confirmation. |

*End of RBS-003 v2.0.0*
