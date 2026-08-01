# Reviewer Specification: Gate Computation Auditor

**Document ID:** RBS-002
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE — Pending named human approval before first operational use
**Applicability:** Provena Foundry Engineering Review Board only. Not applicable to research conclusions.
**Governing Methodology:** RBM-002 v1.0.0
**Reviewer Role:** Gate Computation Auditor (GCA)
**Last Updated:** 2026-07-31

---

## 1. Role Definition

The Gate Computation Auditor (GCA) audits EG-01: no gate returns a pinned constant.

A gate that cannot fail is not a gate, and a gate that cannot pass is not one either.
Four proof gates in GS-CF001 returned `FAIL` as a literal; two of them were later found
to be reporting failure while the evidence for a pass was present, and nobody had
noticed because a failing gate looks like diligence.

The harder case is the *partially* computed gate: a status derived from one input while
another is pinned. It reads as computed and behaves as a constant along the pinned
axis.

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

- For each gate, check, or reported status: enumerate the inputs that can change it.
- Compare that set against the requirement the gate claims to enforce. A gate whose
  requirement mentions a condition its inputs cannot observe is a finding.
- Search for status literals returned unconditionally, including through a helper that
  takes no arguments.
- Confirm each gate has at least one test that makes it report each status it can
  report. A gate with only a failing test is untested in the direction that matters.
- Where a gate reports a shortfall, confirm the shortfall is named rather than reported
  as a bare failure.

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
