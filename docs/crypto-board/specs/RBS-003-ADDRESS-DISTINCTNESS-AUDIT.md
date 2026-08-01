# Reviewer Specification: Address Distinctness Auditor

**Document ID:** RBS-003
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE - Pending named human approval before first operational use
**Applicability:** Provena Foundry Crypto Review Board only.
**Governing Methodology:** RBM-003 v1.0.0
**Reviewer Role:** Address Distinctness Auditor (ADA)
**Last Updated:** 2026-08-01

---

## 1. Role Definition

The Address Distinctness Auditor (ADA) audits CG-02: distinct addresses are not distinct entities.

An address is not a person. Counting addresses and reporting users is the single most
common way a true number becomes a false claim.

This is the sentinel defect wearing another costume: identifiers that look distinct and are
not. Ten thousand wallets funded sequentially from one source are one entity with a script.

---

## 2. Scope

In scope: the contracts, chain state, and published claims named in the review initiation
record, at the block height it states.

Out of scope: price prediction, investment recommendation, and other seats' domains except
where a defect arises at the boundary between them.

This board does not produce valuations or recommendations. It reports what is established,
what is alleged, and what could not be verified.

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

- Cluster addresses by common funding source, and report the count before and after.
- Identify self-transfers and cyclic flows; exclude them from volume and activity counts.
- Check first-funding timing: a cohort created within minutes of each other is one actor.
- Where a count is reported as "users", "holders" or "actives", state which of the three the
  data can actually support.
- Report the clustering method used. An unstated heuristic is not reproducible.

---

## 5. Evidence Standards

- **T1** a query against chain state at a recorded block height, with its result
- **T2** deployed contract source or bytecode, read at a recorded address
- **T3** an artefact the system produced, with recorded provenance
- **T4** assertion without a retrievable referent, including any project-published figure

A T4 finding cannot alone carry SEV-1. A project's own dashboard is T4, not T1: it is a
claim about chain state, not chain state.

---

## 6. Finding Classification Guidance

- **SEV-1** the defect makes a reported figure wrong, and a holder would rely on it
- **SEV-2** the defect can make a figure wrong under conditions that occur
- **SEV-3** the defect degrades clarity, traceability, or reproducibility
- **SEV-4** observation; no defect asserted

Every finding names its gate and the block height at which it was observed.

---

## 10. Board Decision Contribution

This seat contributes findings and a recommended process status. It does not compute the
outcome: that follows from the decision precedence rules in RBM-003 section 10, and no seat
may reach past them.

Where held by an agent, this seat's contribution is advisory and requires a named human
verifier before it enters the decision record.

---

## 11. Required Output

One reviewer report record (TPL-RRR) citing this specification and its version, plus zero or
more finding records (TPL-FND). A report with no findings must state what was examined and
what would have constituted a finding, so a silent seat is distinguishable from an absent one.
