# Reviewer Specification: Sceptical Review

**Document ID:** RBS-008
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** Sceptical Reviewer (SR)
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

The Sceptical Reviewer (SR) is the adversarial voice of the Review Board. The SR's function is not to conduct a specialist technical review — that is the domain of the eight specialist auditors. The SR's function is to examine the review as a whole, challenge the assumptions made by the authoring team and the specialist reviewers, probe for systemic risks that fall between specialist domains, and ask the questions that optimistic participants are inclined to skip.

The SR is institutionally positioned to find what others missed, question what others accepted, and represent the interests of future users, operators, and clients who were not present during development.

The SR must be the most independently minded member of the Board. The SR's value is entirely in their willingness to be uncomfortable and to make others uncomfortable. A Sceptical Reviewer who consistently finds no concerns of note is not performing the role.

---

## 2. Scope

The SR's scope is not bounded by specialist domain. The SR may raise findings in any area — but the SR must not duplicate findings already raised by specialist reviewers. The SR's distinctive contribution is:

- **Cross-domain risks:** Issues that arise at the intersection of two or more specialist domains (e.g., a security control that creates a performance cliff; a data transformation that is architecturally correct but commercially wrong).
- **Assumption challenges:** Assumptions made by the authoring team in the Change Summary, requirements, or design that are unvalidated or rely on conditions that may not hold.
- **Systemic risks:** Risks that arise from the accumulation of small, individually acceptable decisions that together create a larger risk.
- **Optimism bias assessment:** Are the findings and conclusions of specialist reviewers reasonable, or do they reflect an overall pattern of leniency or confirmation bias?
- **Unknown unknowns:** What would need to be true for this artefact to fail in production in a way that the specialist reviews have not anticipated?
- **Coverage gaps:** What reviewer role, if any, has not been represented in this review, and what risks does that gap create?
- **Red team perspective:** If a user, client, or adversary were trying to break, misuse, or misunderstand this system, what would they find?

The SR's scope does **not** include:

- Re-conducting specialist reviews that have already been performed.
- Making Board decisions or overriding specialist findings.
- GS-P001 systems.

---

## 3. Responsibilities

| Responsibility | Timing |
|---------------|--------|
| Read all specialist reviewer reports | After specialist reports are submitted |
| Identify cross-domain risks not captured by any specialist | After specialist reports |
| Challenge assumptions in the authoring team's Change Summary | After specialist reports |
| Assess the overall pattern of specialist findings for bias indicators | After specialist reports |
| Probe for systemic and accumulation risks | After specialist reports |
| Apply red team perspective | After specialist reports |
| Issue SR Challenge Questions to the Board before the decision is finalised | Before Board Decision |
| Produce the SR Report | After SR Challenge Questions are addressed |

---

## 4. Independence Rules

For major milestone reviews, the SR must be organisationally independent from the authoring team (RBM-001 §5.4). This is non-negotiable for milestone-completion reviews.

For routine maintenance reviews, the SR must be a senior reviewer who was not involved in the specific change and has no confirmation interest in the outcome.

The SR must not:
- Have been involved in any decision that resulted in the architectural, design, or commercial choices under review.
- Have a prior relationship with the authoring team that would create social pressure to moderate findings.
- Have previously served as a specialist reviewer on this same artefact version (the SR reviews the review, not the artefact directly).

---

## 5. Required Inputs

| Input | Source | Required Condition |
|-------|--------|--------------------|
| All specialist reviewer reports | Each specialist reviewer | Always — SR reviews after specialists |
| All Finding Records from all reviewers | Review system | Always |
| Change Summary | Input Package | Always |
| Input Package (full) | Authoring team | Always |
| Scope Statement | Review Initiation Record | Always |
| Board Chair's preliminary finding set summary | Board Chair | Before SR challenge questions |
| Previous SR findings | Previous Review Record | Re-reviews only |

**Timing note:** The SR must not begin their review until all specialist reports are submitted. The SR's inputs are the specialist reports, not the artefact directly. The SR may request access to specific artefact components if a cross-domain risk requires direct verification, but this is exceptional, not routine.

---

## 6. Audit Procedure

### Step 1 — Specialist Report Survey

Read all specialist reports. For each report, note:

- The overall finding count and severity distribution.
- Any section of the specialist's checklist that was marked out of scope, with the justification.
- Any finding that the specialist flagged as uncertain in severity.
- Any area where specialist coverage appears thin relative to the declared scope.

### Step 2 — Cross-Domain Risk Identification

For each finding raised by any specialist, ask: does this finding have implications for another specialist domain that were not explored?

Examples of cross-domain risks:
- A security control that relies on a rate limit: does that rate limit work correctly at the load levels the POA assessed?
- A data transformation that is architecturally sound: does it handle the data quality edge cases the DEA would have examined?
- A new dependency that is commercially licensed appropriately: does it introduce a security CVE?
- A performance optimisation: does it compromise the reliability mechanisms the QRA assessed?

Cross-domain risks that are not covered by any specialist finding are SR findings.

### Step 3 — Assumption Challenge

Review the Change Summary and the authoring team's claims. For each significant claim:

- What assumption is this claim based on?
- Is that assumption explicitly validated by evidence in the Input Package?
- What happens if the assumption is false?

Assumptions to challenge:
- "The existing behaviour was correct" — was it? Is there evidence?
- "This change is backward-compatible" — for all clients? Under all conditions?
- "Performance will be acceptable" — at what load? Validated how?
- "This is a low-risk change" — by what assessment? Based on what evidence?
- "The existing test suite covers this" — has anyone verified this specifically for the changed path?

An unvalidated assumption that, if false, would create a material risk is an SR finding.

### Step 4 — Optimism Bias Assessment

Assess the overall pattern of specialist reviews:

- Is the finding count and severity distribution plausible for the scope of this change? A non-trivial change with zero findings across all specialist domains is suspicious.
- Are any specialist findings clustered in a way that suggests reviewers stopped looking after finding one issue?
- Are there areas where multiple reviewers accepted "this looks fine" with thin evidence?
- Are severity classifications consistently in the lower range without justification?

If the SR identifies a pattern suggesting optimism bias (not individual finding quality — the MA handles that), this is an SR finding.

### Step 5 — Systemic Risk Assessment

Look for risks that emerge from the combination of individually acceptable decisions:

- Is technical debt accumulating in a specific area at a rate that creates near-term risk?
- Is there a pattern of deferred items (Minor findings, known issues, "next sprint" items) that together represent a significant unacknowledged risk?
- Does the change, combined with prior changes, create a structural risk that no individual change would reveal?

### Step 6 — Red Team Perspective

Adopt the perspective of someone who wants to break or misuse this system:

- **As a client:** How could I be surprised or harmed by this release in a way that is not disclosed?
- **As a bad actor:** Is there anything in the specialist reports that was found but whose exploitability was understated?
- **As an operator:** If something goes wrong in production after this release, what is the first thing I would not be able to diagnose because observability is inadequate?
- **As a regulator or auditor:** If I examined this release for compliance, where would I find gaps that were not caught by the specialist reviews?

### Step 7 — Coverage Gap Assessment

Identify any area that should have been in scope for a specialist review but was not covered, either because:

- A specialist role was absent from the quorum and their scope was not covered by a substitute.
- A specialist marked an area as out of scope with justification that the SR considers inadequate.
- An area falls between specialist domains and was not picked up by either.

Coverage gaps are SR findings.

### Step 8 — SR Challenge Questions

Before the Board finalises its decision, the SR issues SR Challenge Questions — a set of specific questions directed at the Board, the authoring team, or specific specialist reviewers. Challenge questions are not findings; they are requests for clarification or additional evidence that the SR believes are necessary before the Board can make a sound decision.

Challenge questions must be:
- Specific (not "are we confident in the quality?" — that is not a question).
- Answerable by evidence (not by reassurance).
- Resolved before the Board decision is finalised (or elevated to findings if they cannot be resolved).

---

## 7. Checklist

The SR does not follow a fixed checklist in the way that specialist auditors do. The SR's value is in generative inquiry, not item-checking. However, the following prompts are provided to ensure the SR does not omit key dimensions:

### 7.1 Cross-Domain Risks

| Prompt | Question |
|--------|----------|
| CR-01 | Security + Performance: do any security controls assume load conditions that the system may exceed? |
| CR-02 | Data + Architecture: does the data model support the query and transformation patterns the architecture requires? |
| CR-03 | Reliability + Operations: are reliability mechanisms visible to the monitoring and alerting stack? |
| CR-04 | Business + Data: does the data the system produces match the commercial claims made for it? |
| CR-05 | Security + QA: do the tests cover the security-relevant paths, or are security tests limited to the security scan tools? |
| CR-06 | Architecture + Operations: is the deployment architecture consistent with the deployment runbook? |

### 7.2 Assumption Challenges

| Prompt | Question |
|--------|----------|
| AC-01 | What is the highest-stakes assumption the authoring team made, and is it validated by T1 or T2 evidence? |
| AC-02 | Is backward compatibility assumed rather than proven? What would a client see if the assumption is wrong? |
| AC-03 | Is "low risk" a classification applied to this change, and if so, on what basis? |
| AC-04 | Are any performance targets based on estimates rather than measurements? |
| AC-05 | What behaviour was preserved from the prior version, and how was preservation verified? |

### 7.3 Optimism Bias Indicators

| Prompt | Question |
|--------|----------|
| OB-01 | Is the finding count for this change scope plausible, or is it suspiciously low? |
| OB-02 | Are findings clustered in obvious areas, suggesting reviewers stopped looking after finding the first issue? |
| OB-03 | Are severity classifications consistently low across all specialist domains without clear justification? |
| OB-04 | Did any specialist mark a significant scope area as out of scope with thin justification? |

### 7.4 Systemic Risks

| Prompt | Question |
|--------|----------|
| SR-01 | Is there a specific area of the codebase accumulating deferred findings across multiple reviews? |
| SR-02 | Do the combined open known issues, Minor findings, and deferred items represent a larger risk than they appear individually? |
| SR-03 | Does this change, in the context of recent prior changes, create a pattern risk not visible from this change alone? |

### 7.5 Red Team Perspective

| Prompt | Question |
|--------|----------|
| RT-01 | What is the most likely way this release will cause a production incident, and is it mitigated? |
| RT-02 | What client-visible behaviour has changed that a client has not been told about? |
| RT-03 | If this system were audited by an external regulator, what would they find that the specialist reviews did not? |
| RT-04 | If an adversary read the specialist reviews to find out what was not tested, what would they target? |

### 7.6 Coverage Gaps

| Prompt | Question |
|--------|----------|
| CG-01 | Is any specialist role absent from the review, and was their scope covered by a substitute or left uncovered? |
| CG-02 | Are there areas marked out of scope across multiple specialist reviews that together constitute a significant uncovered domain? |
| CG-03 | Is there a new type of risk introduced by this change that none of the existing specialist roles is well-positioned to assess? |

### 7.7 Tier 3 Risk Characterisation (Tier 3 reviews only)

For Tier 3 (Full Board) reviews, the SR must include an explicit Tier 3 Risk Characterisation in the SR Report (§11.2). The following prompts are mandatory:

| Prompt | Question |
|--------|----------|
| T3-01 | What is the highest-consequence failure mode for this artefact in production, and is it adequately mitigated across the specialist findings? |
| T3-02 | Are there systemic risks that individually fall below specialist finding thresholds but together represent a material residual risk the Board should accept on record? |
| T3-03 | Does the combined specialist finding set, including all PASS WITH FINDINGS conditions, leave the Board in a position to make a fully informed deployment decision? If not, what is outstanding? |
| T3-04 | Does this review involve any `T3-AUTHORITATIVE-EXTERNAL` findings, and are all four admissibility conditions verifiable from the record? |

---

## 8. Evidence Standards

SR findings must meet the same evidence standards as specialist findings (RBM-001 §8). The SR may not raise findings based on general scepticism without evidence. The SR's adversarial posture is a frame for finding evidence, not a substitute for it.

The SR has one additional evidence tool: the compilation of specialist reports is itself evidence. A pattern of thin evidence across multiple specialist reports is evidence of an optimism bias risk. The SR must document this as a finding with specific references to the relevant report sections.

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| Cross-domain risk | T3 or T4 | Specialist report A finding cross-referenced with specialist report B scope assessment |
| Unvalidated assumption | T3 | Change Summary claim; Input Package showing absence of supporting evidence |
| Optimism bias pattern | T3 | Multiple specialist reports showing thin evidence; cross-reference to finding count expectations |
| Coverage gap | T3 | Review Initiation Record showing missing role; Scope Statement showing the area as in scope |
| Systemic deferred risk | T3 | Known Issues Register; prior review records; Minor finding accumulation |

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND.

---

## 9. Finding Classification Guidance

### SEV-1 for Sceptical Review

- A cross-domain risk that, when traced through both domains, reveals a confirmed data loss, security bypass, or contractual breach that no specialist raised.
- A coverage gap that left a High-risk area (per QRA risk profile standards) completely unreviewed.
- An unvalidated assumption that, if false, produces a condition that would be a SEV-1 finding for any specialist auditor.

### SEV-2 for Sceptical Review

- A cross-domain risk that creates a material quality or commercial risk not captured by specialists.
- A pattern of optimism bias that calls into question the reliability of the specialist reviews as a whole (not individual finding quality — that is the MA's domain).
- A systemic deferred risk where the accumulation of Minor findings and known issues represents an unacknowledged Major risk.
- A coverage gap in a Medium-risk area with no compensating coverage.
- An SR Challenge Question that cannot be answered with evidence and represents a material uncertainty.

### SEV-3 for Sceptical Review

- A cross-domain risk with low probability or bounded impact.
- A minor assumption challenge where the assumption is reasonable but unvalidated.
- A coverage gap in a low-risk area.
- An SR Challenge Question answered with adequate evidence that nonetheless reveals a minor concern.

### SEV-4 for Sceptical Review

- An observation or improvement suggestion arising from the cross-domain perspective.
- A red team concern that the team is aware of and has accepted with documentation.

---

## 10. Board Decision Contribution

The SR does not issue a Board outcome or process status. The SR raises findings and records whether challenge coverage is `SUFFICIENT` or `INSUFFICIENT` for a PASS-class conclusion, with unanswered challenges and missing evidence listed.

If the SR identifies an unanswered material challenge, optimism bias, coverage gap, or systemic risk that makes the finding snapshot untrustworthy, process status is `BLOCKED` until the challenge receives a traceable disposition and the MA validates that disposition. The Board Chair may not dismiss a material challenge by assertion or schedule preference.

---

## 11. Required Output

### 11.1 SR Challenge Questions (issued before Board Decision)

```
SR CHALLENGE QUESTIONS
=======================
Review ID:
SR Name:
Issued:

The following questions must be answered with T1–T4 evidence before the Board finalises its decision.
Questions that cannot be answered must be elevated to SR findings.

[For each question:]
Question ID: [Review ID]-SR-Q[N]
Directed at: [Board / authoring team / specific specialist reviewer]
Question: [Specific question]
Evidence required to close: [What constitutes an adequate answer]
Status: [ ] OPEN  [ ] ANSWERED  [ ] ELEVATED TO FINDING
Answer received (if ANSWERED):
Finding raised (if ELEVATED): [Finding ID]
```

### 11.2 Sceptical Review Report

```
SCEPTICAL REVIEW REPORT
========================
Document ID:        TPL-SRR
Review ID:
SR Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-008 [version]

SPECIALIST REPORT SURVEY SUMMARY
Specialist reports received: [count] / [count required]
Overall finding count across all specialists:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]
SR assessment of plausibility: [ ] PLAUSIBLE  [ ] SUSPICIOUSLY LOW  [ ] APPROPRIATE

CROSS-DOMAIN RISKS IDENTIFIED
[List each cross-domain risk assessed, with the result]
[For raised findings, reference the TPL-FND]

ASSUMPTION CHALLENGES
[List each assumption challenged, with the result]

OPTIMISM BIAS ASSESSMENT
Pattern of optimism bias detected: [ ] YES  [ ] NO  [ ] UNCERTAIN
If YES or UNCERTAIN: [describe the pattern and its basis]

SYSTEMIC RISKS
Systemic deferred risk identified: [ ] YES  [ ] NO
If YES: [describe]

RED TEAM ASSESSMENT
Most material uncaptured risk identified: [ ] YES  [ ] NO
If YES: [describe; reference TPL-FND if raised as finding]

COVERAGE GAPS
Missing specialist roles: [list]
Coverage gap assessed: [describe scope of gap and associated risk]

SR CHALLENGE QUESTIONS
Questions issued: [count]
Questions answered: [count]
Questions elevated to findings: [count]
Reference to TPL-SRCQ:

FINDINGS SUMMARY:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]

FINDINGS:
[For each finding, attach a completed TPL-FND]

TIER 3 RISK CHARACTERISATION (complete for Tier 3 reviews only — omit for Tier 1 and Tier 2):
Highest-consequence failure mode and mitigation status:
Residual systemic risks below individual finding thresholds:
Board's ability to make a fully informed deployment decision: [ ] YES  [ ] NO — [describe outstanding matters]
T3-AUTHORITATIVE-EXTERNAL findings present: [ ] YES  [ ] NO
If YES — all four admissibility conditions verified from record: [ ] YES  [ ] NO — [describe gap]

RECOMMENDATION TO RE-OPEN SPECIALIST REVIEW:
[ ] Not recommended — the specialist finding set is a sufficient basis for Board decision.
[ ] BLOCKED pending disposition — [state the material optimism bias, coverage gap, systemic risk, or unanswered challenge]
Traceable challenge disposition and MA validation reference:

PASS-CLASS CHALLENGE SUFFICIENCY:
[ ] SUFFICIENT  [ ] INSUFFICIENT
Missing evidence / unanswered challenges:

AI ASSISTANCE:
[ ] AI tools were used — describe what for and confirm independent verification of all findings
[ ] AI tools were not used

SR Signature:
Date:
```

---

## 12. Reviewer Prompt Conversion Notes

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human Sceptical Reviewer. You do not hold the SR role, count toward quorum, assign severity, sign findings, block a review, or issue an outcome. Help locate candidate contradictions, omissions, and assumptions for human review."

**Key Prompt Constraints:**
- Must wait until all specialist reports are available before beginning the SR review.
- Must not re-conduct specialist reviews — reference specialist reports as evidence.
- Must raise findings with specific evidence, not general scepticism.
- Must issue SR Challenge Questions before the Board decision, not after.
- Must not raise findings about GS-P001 assets.
- If optimism bias is identified, must cite specific patterns in specific specialist reports.
- A Sceptical Review with zero findings on a non-trivial change requires written justification in the report.
- Must label every output as an unsigned draft; challenge materiality and evidence sufficiency remain human reviewer acts.

**Inputs to Prompt:** All specialist reviewer reports, all Finding Records, Change Summary, Input Package, Scope Statement.

**Output Format:** Unsigned draft SR Challenge Questions and report matching §11.2, with evidence candidates for human verification. TPL-SRCQ, TPL-SRR, and TPL-FND become valid only after the named human SR verifies and signs them.

**Sequencing for Orchestration:** This prompt must be invoked after all specialist reviewer prompts have completed and their outputs are available. The SR Challenge Question issuance must trigger a pause before the Board Decision prompt is invoked.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception note to §8; added Tier 3 Risk Characterisation requirement to §7 and §11.2 report template; status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned terminology, challenge blocking, and decision contribution with RBM-001 v2.0.0. |

*End of RBS-008 v2.0.0*
