# Reviewer Specification: Methodology Auditor

**Document ID:** RBS-001
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE — Pending named human approval before first operational use
**Applicability:** Provena Foundry Engineering Review Board only. Not applicable to research conclusions.
**Governing Methodology:** RBM-002 v1.0.0
**Reviewer Role:** Methodology Auditor (MA)
**Last Updated:** 2026-07-31

---

## 1. Role Definition

The Methodology Auditor (MA) audits whether this review followed RBM-002.

The MA does not audit the code. The MA audits the *review* — whether quorum was met,
whether evidence was locked before independent review began, whether each specialist
worked from the reviewer specification their seat requires, and whether the findings
raised are traceable to the gate they claim.

The distinctive MA question is: **if this review had missed something, would this
process have caught it?** A board that met quorum, followed sequence, and asked no
question capable of failing has conducted a ceremony.

---

## 2. Scope

In scope: the artefact at the commit named in the review initiation record, and the
documentation that travels with it.

Out of scope: other seats' domains, except where a defect arises at the boundary
between them. A duplicate finding is a finding this seat should have left to the seat
that owns it.

---

## 3. Independence Rules

This seat forms its assessment before reading other seats' reports. Where the seat is
held by an agent, its instruction version is distinct from every other seat's, and both
the model and the instruction version are recorded. Where seats share a model, the
record says so, because two seats on one model are correlated reviewers.

This seat is a **non-authoritative AI assistant** when held by an agent. Its output is
an **unsigned draft**: advisory, never evidence, and never a ratification.

---

## 4. Audit Procedure

- Confirm the review initiation record names a commit hash, and that the commit exists.
- Confirm evidence was locked before the first independent review was submitted.
- Confirm each specialist seat cites the reviewer specification for its role.
- Confirm each finding cites a gate (EG-01..EG-06) and an evidence tier.
- Confirm no seat holds two roles, and no agent seat holds BC.
- Confirm the sceptical seat received a brief with the proposed outcome stripped.
- Confirm that where seats share a model, the record says so.

---

## 5. Evidence Standards

Findings cite evidence by tier:

- **T1** a reproducible command and its recorded output at the named commit
- **T2** source read at the named commit, cited by file and line
- **T3** an artefact the system produced, with recorded provenance
- **T4** assertion without a retrievable referent

A T4 finding cannot alone carry SEV-1. In engineering, T1 evidence is cheap.

---

## 6. Finding Classification Guidance

- **SEV-1** the defect makes a reported result wrong, and the result is relied upon
- **SEV-2** the defect can make a reported result wrong under conditions that occur
- **SEV-3** the defect degrades clarity, maintainability, or diagnostics
- **SEV-4** observation; no defect asserted

Each finding names the gate it arises under and, where the defect is live, the input
that demonstrates it.

---

## 10. Board Decision Contribution

This seat contributes findings and a recommended process status. It does not compute
the outcome: the outcome follows from the decision precedence rules in RBM-002 §10, and
no seat may reach past them.

Where this seat is held by an agent, its contribution is advisory and requires a named
human verifier before it enters the decision record.

---

## 11. Required Output

One reviewer report record (TPL-RRR) citing this specification and its version, plus
zero or more finding records (TPL-FND). A report with no findings must state what was
examined and what would have constituted a finding, so that a silent seat is
distinguishable from an absent one.
