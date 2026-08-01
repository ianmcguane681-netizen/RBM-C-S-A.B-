# Reviewer Specification: Liquidity Auditor

**Document ID:** RBS-006
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE - Pending named human approval before first operational use
**Applicability:** Provena Foundry Crypto Review Board only.
**Governing Methodology:** RBM-003 v1.0.0
**Reviewer Role:** Liquidity Auditor (LQA)
**Last Updated:** 2026-08-01

---

## 1. Role Definition

The Liquidity Auditor (LQA) audits CG-05: what would it cost to leave.

TVL is not depth. The question a holder faces is the cost of exiting at a given size, and
that is a different number -- often by an order of magnitude.

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

- Compute slippage to exit at several stated sizes, not a single headline figure.
- Separate liquidity that is locked, incentivised, or owned by the project itself.
- Identify concentration: how much depth sits with one provider, and what happens if it
  leaves.
- Check whether liquidity is real or circular -- a pool funded by the token's own treasury
  is not external demand.
- State the venue and block height. Depth is not a constant.

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
