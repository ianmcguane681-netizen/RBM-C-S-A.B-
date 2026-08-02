# Reviewer Specification: Methodology Auditor

**Document ID:** RBS-001
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE - Pending named human approval before first operational use
**Applicability:** Provena Foundry Stocks Review Board only.
**Governing Methodology:** RBM-004 v1.0.0
**Reviewer Role:** Methodology Auditor (MA)
**Last Updated:** 2026-08-02

---

## 1. Role Definition

This seat reviews the review: whether the tier matches the subject, whether the
declared quorum was met or waived, whether every gate was answered or recorded as
not assessed, and whether all evidence sits at one artefact.

---

## 2. Scope

The conduct of the review against RBM-004. Not the subject, and not any other seat's
judgement about it.

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

Reports LAST, after every other seat including the Sceptical Reviewer. A methodology
audit filed before the reports it audits has audited nothing, and the runtime
refuses it.

---

## 5. Evidence Standards

The review's own records: the initiation, the evidence register, the seat reports
and their citations.

---

## 6. Finding Classification Guidance

A review conducted below the tier its subject requires is SEV-2, because every
conclusion drawn from it claims more coverage than it had. Evidence split across
artefacts under one declared version is SEV-3.

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
