# Reviewer Specification: Sceptical Reviewer

**Document ID:** RBS-008
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE - Pending named human approval before first operational use
**Applicability:** Provena Foundry Crypto Review Board only.
**Governing Methodology:** RBM-003 v1.0.0
**Reviewer Role:** Sceptical Reviewer (SR)
**Last Updated:** 2026-08-01

---

## 1. Role Definition

The Sceptical Reviewer (SR) audits the review as a whole.

The SR examines the review, not the chain. What would have to be true for this project to
be misrepresented in a way every seat above would have passed?

The SR is blind to the proposed outcome. A sceptical seat that knows the board is minded to
pass is being asked to ratify, not to challenge.

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

- Identify what the six gates together cannot see. Name it.
- Ask whether the seats verified the claims the project makes, or the claims that were easy
  to verify.
- Look at gate boundaries: supply can be correct, liquidity real, addresses distinct, and the
  combination still misleading.
- Ask what off-chain dependency the whole thing rests on -- a bridge, a custodian, an oracle,
  a jurisdiction -- and whether any seat examined it.
- Ask whether the reviewed block height was chosen or merely convenient.

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
