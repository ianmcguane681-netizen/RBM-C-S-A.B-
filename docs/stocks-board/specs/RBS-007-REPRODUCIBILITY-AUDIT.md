# Reviewer Specification: Reproducibility Auditor

**Document ID:** RBS-007
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE - Pending named human approval before first operational use
**Applicability:** Provena Foundry Stocks Review Board only.
**Governing Methodology:** RBM-004 v1.0.0
**Reviewer Role:** Reproducibility Auditor (RPA)
**Last Updated:** 2026-08-02

---

## 1. Role Definition

This seat answers SG-06 — Reproducibility — and nothing else. Its findings cite
`RBS-007 section 7 (SG-06)`, so a reader moves from a finding to the seat that
raised it and to the gate that required it.

---

## 2. Scope

Every figure must carry the filing, period and retrieval that produced it, and a sample must be re-retrieved and shown to reproduce. A figure that cannot be regenerated is a claim.

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

**The failure mode this seat exists for.** A number is quoted from memory or from an earlier draft, and nobody can tell which filing it came from.

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
