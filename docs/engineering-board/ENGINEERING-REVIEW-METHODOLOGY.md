# Engineering Review Board Methodology (RBM-002)

**Document ID:** RBM-002
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE — Pending named human approval before first operational use
**Architecture Authority:** RBE-001 v1.1.0
**Applicability:** Provena Foundry engineering artefacts. Not applicable to research conclusions, which are governed by RBM-001.
**Last Updated:** 2026-07-31

---

## Table of Contents

1. [Why a Second Profile Exists](#1-why-a-second-profile-exists)
2. [Scope](#2-scope)
3. [What This Board Reviews](#3-what-this-board-reviews)
4. [Board Composition](#4-board-composition)
5. [The Six Engineering Gates](#5-the-six-engineering-gates)
6. [Evidence Standards](#6-evidence-standards)
7. [Severity Classification](#7-severity-classification)
8. [Review Tiers](#8-review-tiers)
9. [Agent Seats](#9-agent-seats)
10. [Process Status and Decision Framework](#10-process-status-and-decision-framework)
11. [Relationship to RBM-001](#11-relationship-to-rbm-001)

### 6B. Canonical RBE Lifecycle Mapping

RBM-002 maps onto the RBE-001 canonical lifecycle without modification. The mapping is
declared in `PROFILE.json` under `canonical_lifecycle_mapping` and is identical to
RBM-001's, because the lifecycle belongs to the architecture and not to the
methodology. A profile that could rewrite the lifecycle could invent a state in which
its own findings did not have to be answered.

### 16.2 Activation Gate

This profile is a RELEASE CANDIDATE. It is non-binding, carries no human approval
record, and cannot permit a merge. Activation requires every item in
`activation_requirements`, including two named human approvals. Until then every
decision produced under RBM-002 is advisory, and is recorded as such.

---

## 1. Why a Second Profile Exists

RBM-001 governs research conclusions. Its hardest problem is that the evidence is
curated by somebody else: a federal court archive holds a complaint for roughly one
case in sixty-seven, and no amount of diligence changes that. RBM-001's gates are
therefore mostly about *restraint* — refusing to claim more than the evidence carries.

Engineering review has the opposite problem. The evidence is excellent. A test passes
or it fails. A commit hash is a fact. A build reproduces or it does not. Nothing in
the record depends on a stranger's upload decision.

Better evidence permits sharper gates, and a profile whose gates were written for
scarce evidence would waste that. RBM-002 exists to use it.

## 2. Scope

In scope: source code, tests, schemas, data-processing tools, connectors, command-line
interfaces, and the artefacts they produce, at a named commit.

Out of scope: whether a research conclusion is supported by its evidence. That is
RBM-001's question, and an engineering board that answered it would be substituting a
review of the *machinery* for a review of the *finding*.

**Decision Finalisation and Publication Separation** applies unchanged from RBE-001:
the actor who assembles a decision may not be the actor who publishes it, and neither
may be the sceptical seat.

## 3. What This Board Reviews

The review target is a `GIT_COMMIT`. This is worth stating because it is the point at
which engineering review is *easier* than research review rather than harder: the
artefact under review is exactly identified, immutable, and independently retrievable
by anyone with the repository.

A review that cannot name the commit it reviewed is `PROCEDURALLY_INCOMPLETE`.

## 4. Board Composition

| Role | Code | Function |
|---|---|---|
| Board Chair | BC | Accountable human. Convenes, ratifies, publishes. Never an agent. |
| Methodology Auditor | MA | Audits that this methodology was followed. |
| Gate Computation Auditor | GCA | EG-01 |
| Measurement Completeness Auditor | MCA | EG-02 |
| Enforcement Fidelity Auditor | EFA | EG-03 |
| Attestation Integrity Auditor | ATA | EG-04 |
| Sentinel and Vocabulary Auditor | SVA | EG-05 |
| Reproducibility Auditor | RPA | EG-06 |
| Sceptical Reviewer | SR | Adversarial cross-domain review. Blind to the proposed outcome. |

Separation of duties is inherited from RBE-001 and is not relaxed: distinct actors per
seat, chair distinct from governance validator, assembler distinct from publisher.

## 5. The Six Engineering Gates

Each gate is a defect class **observed in this system's own code**, not a category
drawn from a checklist. That provenance is the reason to trust the list: every one of
them shipped, and every one of them read as correct until something forced a second
look.

### EG-01 — Gate computation

> No gate, check, or status may return a pinned constant. Every reported status must be
> computed from inputs that can change it.

*Observed:* four proof gates in GS-CF001 returned `FAIL` as a hardcoded literal. They
were not failing; they were incapable of anything else. Two of them were later found to
be reporting failure while the evidence for a pass was present.

The subtle case is a gate that is *partly* computed — a status derived from one input
while a second is pinned. The auditor's question is not "is this computed?" but "which
inputs can change this result, and does that set match the requirement?"

### EG-02 — Measurement completeness

> No summary, rate, or aggregate may be written over a denominator that was not
> enumerated, or a numerator with unattempted members.

*Observed twice:* a coverage census wrote a summary after pagination failed and zero
records were retrieved — the file read as a finished measurement resting on nothing.
The guard added for that case then failed to cover a second: rate-limited records were
written down as absences, so a busy API silently understated archive coverage.

The pattern is a **partial state presenting as a complete one**. It is this system's
most frequent defect class by a wide margin.

### EG-03 — Enforcement fidelity

> Every stated requirement must name the constant, test, or code path that enforces it.
> A requirement that exists only as prose is not a requirement.

*Observed:* a review board accepted a remediation requiring corroboration across three
federal districts. The requirement was written into the README and enforced nowhere,
so a single district would have satisfied the code while contradicting the commitment.

An auditor raising an EG-03 finding must cite both the prose and the absence.

### EG-04 — Attestation integrity

> No attestation may be recorded by the process that produced the value it attests to,
> and no actor may sign as another.

*Observed:* a pricing ledger required a human to read a page and transcribe the figure
against a recorded hash. A demonstration run recorded a named human as the transcriber
for a figure the automation itself had read, and committed it. The guard and the
violation were written five minutes apart, by the same author.

This gate is why agent seats are advisory: an agent may review, and may never ratify or
publish.

### EG-05 — Sentinel handling

> Values meaning unknown, unset, or not yet determined must never be equality-matched,
> compared, or counted as results.

*Observed:* two records that both failed to classify fell to the same fallback value,
matched each other on equality, and produced a corroboration `PASS` from two records
that had corroborated nothing. Related: an FJC judgment code of `4` means *unknown*,
and reading it as a decision would convert "not yet judged" into a judgement.

### EG-06 — Reproducibility

> The reviewed commit hash and the observed test result must be recorded, and the
> result must reproduce from a clean checkout.

*Observed:* test counts quoted between sessions from memory rather than from a recorded
run. A count that cannot be reproduced is a claim, not a measurement — which makes it
an EG-02 finding wearing an engineering hat.

## 6. Evidence Standards

Engineering evidence tiers, strongest first:

| Tier | Meaning |
|---|---|
| T1 | A reproducible command and its recorded output at a named commit |
| T2 | Source read directly at a named commit, cited by file and line |
| T3 | An artefact the system produced, with its provenance recorded |
| T4 | Assertion by a reviewer without a retrievable referent |

A T4 finding may be raised but cannot alone carry SEV-1. The asymmetry is deliberate:
in engineering, T1 evidence is cheap, so a reviewer who did not produce it usually
chose not to.

Agent-produced output is never evidence. An agent seat citing its own reasoning has
cited T4.

## 7. Severity Classification

| Severity | Meaning |
|---|---|
| SEV-1 | The defect makes a reported result wrong, and the result is relied upon |
| SEV-2 | The defect can make a reported result wrong under conditions that occur |
| SEV-3 | The defect degrades clarity, maintainability, or diagnostic quality |
| SEV-4 | Observation; no defect asserted |

The severity vocabulary is shared with RBM-001 deliberately, so a decision assembled
under either profile means the same thing. `INSUFFICIENT_EVIDENCE` and
`PROCEDURALLY_INCOMPLETE` likewise retain their RBE-001 meanings.

Note that **all six gates describe SEV-1-capable defects**. Each one, in its observed
instance, produced a result that was reported as true and was not.

## 8. Review Tiers

| Tier | Applies to | Specialists required |
|---|---|---|
| 1 | A bounded change to a single module | 2, from GCA/MCA/RPA |
| 2 | A change crossing modules, or touching a gate, guard, or published artefact | 4 |
| 3 | A change to the review machinery itself, or to how evidence is admitted | 6 |

A change to the engineering board's own gates is Tier 3 by construction. A board that
could revise its own gates at Tier 1 has no gates.

## 9. Agent Seats

Permitted for MA, the six specialists, and SR. Never for BC.

Independence between agent seats is not assumed from separate invocations. It requires
distinct instruction versions per seat, recorded model and instruction version, and a
sceptical seat blind to the proposed outcome. Where seats share a model, that fact is
recorded — two seats on one model are correlated reviewers, and a board that did not
say so would be reporting more independence than it had.

## 10. Process Status and Decision Framework

Process status and outcome are separate axes, exactly as in RBE-001:

- `READY` — the review was procedurally complete and an outcome may be computed
- `PROCEDURALLY_INCOMPLETE` — quorum, evidence lock, or record integrity failed
- `BLOCKED` — an external dependency prevents completion
- `VOID` — the review is withdrawn

Only a `READY` process produces one of `PASS`, `PASS_WITH_FINDINGS`, `FAIL`, or
`INSUFFICIENT_EVIDENCE`. The precedence rules are RBE-001's, unchanged and unchangeable
by this profile:

| Priority | Rule | Condition | Outcome |
|---|---|---|---|
| 1 | RBM-DEC-001 | `unresolved_sev1 >= 1` | FAIL |
| 2 | RBM-DEC-002 | `unresolved_sev2 >= 2` | FAIL |
| 3 | RBM-DEC-003 | `unresolved_sev2 == 1 and accepted_sev2_remediation == 0` | FAIL |
| 4 | RBM-DEC-004 | `substantive_evidence_sufficient == false` | INSUFFICIENT_EVIDENCE |
| 5 | RBM-DEC-005 | `unresolved_sev2 == 1 and accepted_sev2_remediation == 1` | PASS_WITH_FINDINGS |
| 6 | RBM-DEC-006 | no unresolved SEV-1 or SEV-2, evidence sufficient | PASS |

`DEFER_FOR_FURTHER_RESEARCH` is not a permitted outcome and maps to
`INSUFFICIENT_EVIDENCE`. An engineering board that could defer indefinitely would never
have to say a thing was wrong.

## 11. Relationship to RBM-001

The two profiles are siblings, not layers. Neither reviews the other's decisions.

They share: the RBE-001 architecture, the lifecycle, the outcome vocabulary, the
decision precedence, the severity scale, the separation-of-duties rules, and the agent
seat policy. They differ in what the specialists audit and what evidence is available
to them.

A single artefact may be reviewed under both — a commit that changes how a study
computes its proof gates is an engineering artefact and a methodology artefact at once.
Those are two reviews, recorded separately, and either may fail without the other.
