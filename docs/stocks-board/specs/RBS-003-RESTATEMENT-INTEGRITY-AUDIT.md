# Reviewer Specification: Restatement Integrity Analyst

**Document ID:** RBS-003
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE - Pending named human approval before first operational use
**Applicability:** Provena Foundry Stocks Review Board only.
**Governing Methodology:** RBM-004 v1.0.0
**Reviewer Role:** Restatement Integrity Analyst (RIA)
**Last Updated:** 2026-08-02

---

## 1. Role Definition

This seat answers SG-02 — Restatement and revision integrity — and nothing else. Its findings cite
`RBS-003 section 7 (SG-02)`, so a reader moves from a finding to the seat that
raised it and to the gate that required it.

---

## 2. Scope

Where a period has been filed more than once at different values, every version must be reported with the filing that produced it. No version may be selected silently, and an as-restated figure may never be compared against an as-originally-filed one.

---

## 3. Independence Rules

This seat forms its assessment before reading other seats' reports. Where held by an agent,
its instruction version is distinct from every other seat's, and both model and instruction
version are recorded. Where seats share a model, the record says so, because two seats on
one model are correlated reviewers.

Where held by an agent this seat is a **non-authoritative AI assistant** and its output is an
**unsigned draft**: advisory, never evidence, never a ratification.

---

## 4. Audit Procedure

Gather the evidence the gate names, at the review's stated artefact. Record what
was searched as well as what was found: a gate answered over evidence that was
never gathered looks exactly like coverage and is worse than an absent gate.

Where the evidence cannot be obtained, record the gate as NOT ASSESSED with
`evidence_sufficiency: INSUFFICIENT` and state what was attempted.

---

## 5. Evidence Standards

Every figure carries the source that produced it and is retrievable by a third
party from that citation alone. A figure that cannot be regenerated is ALLEGED.

---

## 6. Finding Classification Guidance

**The failure mode this seat exists for.** A ratio is computed from an original 10-K and compared to a later year that was restated, so the trend is an artefact of the correction rather than of the business.

A defect that makes a reported figure wrong, and that a reader would rely on, is
SEV-1. One that can make a figure wrong under conditions that occur is SEV-2.
One that degrades clarity, traceability or reproducibility is SEV-3. An
observation asserting no defect is SEV-4.

---

## 10. Board Decision Contribution

This seat contributes findings and a recommended process status. It does not compute the
outcome: that follows from the decision precedence rules in RBM-004 section 10, and no seat
may reach past them.

Where held by an agent, this seat's contribution is advisory and requires a named human
verifier before it enters the decision record.

---

## 11. Required Output

One reviewer report record (TPL-RRR) citing this specification and its version, plus zero or
more finding records (TPL-FND). A report with no findings must state what was examined and
what would have constituted a finding, so a silent seat is distinguishable from an absent one.
