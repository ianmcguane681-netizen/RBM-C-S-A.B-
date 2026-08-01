# Crypto Review Board Methodology (RBM-003)

**Document ID:** RBM-003
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE — Pending named human approval before first operational use
**Architecture Authority:** RBE-001 v1.1.0
**Applicability:** On-chain assets, protocols and the claims made about them. Not applicable to research conclusions (RBM-001) or engineering artefacts (RBM-002).
**Last Updated:** 2026-08-01

---

## Table of Contents

1. [Why This Profile Exists](#1-why-this-profile-exists)
2. [Scope](#2-scope)
3. [The Artefact Is a Block Height](#3-the-artefact-is-a-block-height)
4. [Board Composition](#4-board-composition)
5. [The Six Chain Gates](#5-the-six-chain-gates)
6. [Evidence Standards](#6-evidence-standards)
7. [Severity Classification](#7-severity-classification)
8. [Review Tiers](#8-review-tiers)
9. [Agent Seats](#9-agent-seats)
10. [Process Status and Decision Framework](#10-process-status-and-decision-framework)
11. [What This Board Will Not Produce](#11-what-this-board-will-not-produce)

### 6B. Canonical RBE Lifecycle Mapping

RBM-003 maps onto the RBE-001 canonical lifecycle without modification, identically to
RBM-001 and RBM-002. The lifecycle belongs to the architecture. A profile that could
rewrite it could invent a state in which its own findings did not have to be answered.

### 16.2 Activation Gate

This profile is a RELEASE CANDIDATE. It is non-binding, carries no human approval record,
and cannot authorise action. Every decision produced under it is advisory and recorded as
such until every item in `activation_requirements` is met, including two named human
approvals.

---

## 1. Why This Profile Exists

A crypto claim and its verification sit unusually close together. The chain is immutable,
hash-addressed, independently retrievable and free to query, so for most quantitative
claims the distance between *asserted* and *established* is a single query.

That is a better evidentiary position than either sibling profile enjoys. RBM-001's
research evidence is curated by strangers and mostly absent; RBM-002's engineering
evidence is excellent but private to a repository. Chain state is excellent *and* public.

So the default here is strict: **an unreproduced quantitative claim stays ALLEGED.** Not
because the claimant is presumed dishonest, but because when verification costs one query,
declining to run it is a choice.

The gates target the ways a checkable claim still misleads once you start checking:
counting one entity as many, reading supply from a website rather than a contract, and
reporting headline liquidity that would not survive an exit.

## 2. Scope

In scope: deployed contracts, chain state, token supply and distribution, liquidity and
exit cost, privileged authority, and any published quantitative claim about them.

Out of scope: price direction, timing, and whether an asset is a good purchase. This board
answers *what is true at this block*, not *what happens next*.

**Decision Finalisation and Publication Separation** applies unchanged from RBE-001: the
actor who assembles a decision may not publish it, and neither may be the sceptical seat.

## 3. The Artefact Is a Block Height

A review names a chain and a block height, and that is its artefact version — the exact
analogue of RBM-002's commit hash. It is immutable, independently retrievable, and pins
every figure in the review to one point in chain history.

A review that cannot name its block height is `PROCEDURALLY_INCOMPLETE`. A figure recorded
without one is not reproducible, and an unreproducible figure is a claim.

## 4. Board Composition

| Role | Code | Function |
|---|---|---|
| Board Chair | BC | Accountable human. Convenes, ratifies, publishes. Never an agent. |
| Methodology Auditor | MA | Audits that this methodology was followed. |
| Chain Verification Auditor | CVA | CG-01 |
| Address Distinctness Auditor | ADA | CG-02 |
| Tokenomics Auditor | TKA | CG-03 |
| Contract Authority Auditor | CAA | CG-04 |
| Liquidity Auditor | LQA | CG-05 |
| Reproducibility Auditor | RPA | CG-06 |
| Sceptical Reviewer | SR | Adversarial cross-domain review. Blind to the proposed outcome. |

Separation of duties is inherited from RBE-001 and is not relaxed.

## 5. The Six Chain Gates

### CG-01 — Chain-observable verification

> Every quantitative claim must be reproducible from chain state at a stated block height,
> by a query recorded in the finding.

*Fails when:* a project dashboard is cited as though it were chain state. Dashboards apply
undisclosed filters. A figure nobody else can regenerate is not a measurement.

### CG-02 — Address distinctness

> Counts of users, holders or actives must exclude self-transfers, cyclic flows, and
> clusters funded from a common source. An address is not a person.

*Fails when:* ten thousand addresses funded sequentially from one wallet are reported as
ten thousand users. This is the sentinel defect in another costume — identifiers that look
distinct and are not — and it is the most common route from a true number to a false claim.

### CG-03 — Supply and lock verification

> Circulating supply, vesting schedules and locks must be read from contract state, never
> from a website or a spreadsheet.

*Fails when:* published tokenomics and deployed contract disagree, and the published
version is the one everyone models. An unlock schedule is code, and code is retrievable.

### CG-04 — Contract authority

> Identify every address that can mint, pause, upgrade, blacklist or withdraw, and the
> threshold required.

*Fails when:* "ownership renounced" is stated while an upgradeable proxy retains an admin
who can replace the implementation, and with it every other guarantee.

### CG-05 — Liquidity reality

> Liquidity must be assessed as exit cost at a stated size, not as headline TVL.

*Fails when:* TVL is reported as though it were depth. The question a holder actually faces
is what it costs to leave, and that is a different number — often by an order of magnitude.

### CG-06 — Provenance and reproducibility

> Every figure records chain, block height, contract address and the exact query, and
> reproduces on a clean run against an archive node.

*Fails when:* a figure is correct when taken and unreproducible a week later, because the
block height was never recorded.

## 6. Evidence Standards

| Tier | Meaning |
|---|---|
| T1 | A query against chain state at a recorded block height, with its result |
| T2 | Deployed contract source or bytecode, read at a recorded address |
| T3 | An artefact the system produced, with recorded provenance |
| T4 | Assertion without a retrievable referent |

**A project's own dashboard is T4, not T1.** It is a claim about chain state, not chain
state. This distinction does more work than any other rule in this document.

A T4 finding may be raised but cannot alone carry SEV-1. Agent-produced output is never
evidence; an agent seat citing its own reasoning has cited T4.

## 7. Severity Classification

| Severity | Meaning |
|---|---|
| SEV-1 | The defect makes a reported figure wrong, and a holder would rely on it |
| SEV-2 | The defect can make a figure wrong under conditions that occur |
| SEV-3 | The defect degrades clarity, traceability, or reproducibility |
| SEV-4 | Observation; no defect asserted |

The vocabulary is shared with RBM-001 and RBM-002 deliberately, so a decision means the
same thing under any of the three.

## 8. Review Tiers

| Tier | Applies to | Specialists |
|---|---|---|
| 1 | A single contract, or a bounded re-review at a new block height | 2, from CVA/ADA/RPA |
| 2 | A protocol with multiple contracts, or any position being taken | 4 |
| 3 | Anything with an upgradeable proxy, a bridge, or a custodial dependency | 6 |

Upgradeability is Tier 3 by construction. A contract that can be replaced has no
guarantees that survive a review of its current implementation.

## 9. Agent Seats

Permitted for MA, the six specialists, and SR. Never for BC.

Independence is not assumed from separate invocations. It requires distinct instruction
versions per seat, recorded model and instruction version, and a sceptical seat blind to
the proposed outcome. Seats sharing a model are recorded as sharing one, because two seats
on one model are correlated reviewers.

## 10. Process Status and Decision Framework

Process status and outcome are separate axes, as in RBE-001:

- `READY` — procedurally complete; an outcome may be computed
- `PROCEDURALLY_INCOMPLETE` — quorum, evidence lock, or block height missing
- `BLOCKED` — an external dependency prevents completion
- `VOID` — withdrawn

Only `READY` produces `PASS`, `PASS_WITH_FINDINGS`, `FAIL` or `INSUFFICIENT_EVIDENCE`. The
precedence rules are RBE-001's, unchanged and unchangeable by this profile:

| Priority | Rule | Condition | Outcome |
|---|---|---|---|
| 1 | RBM-DEC-001 | `unresolved_sev1 >= 1` | FAIL |
| 2 | RBM-DEC-002 | `unresolved_sev2 >= 2` | FAIL |
| 3 | RBM-DEC-003 | `unresolved_sev2 == 1 and accepted_sev2_remediation == 0` | FAIL |
| 4 | RBM-DEC-004 | `substantive_evidence_sufficient == false` | INSUFFICIENT_EVIDENCE |
| 5 | RBM-DEC-005 | `unresolved_sev2 == 1 and accepted_sev2_remediation == 1` | PASS_WITH_FINDINGS |
| 6 | RBM-DEC-006 | no unresolved SEV-1 or SEV-2, evidence sufficient | PASS |

`INSUFFICIENT_EVIDENCE` is expected to be a common outcome here and is not a failure of the
review. Where a project's claims cannot be reproduced from chain state, that *is* the
finding.

## 11. What This Board Will Not Produce

No price target, no rating, no buy or sell signal, no score.

It produces three lists: what is established at this block, what is alleged and
unverified, and what could not be checked at all. Anyone converting that into a position
is making a decision the board did not make and does not endorse.

A review under this profile can never, by itself, authorise a transaction. Authorisation
requires a ratified mandate under a binding profile, which this is not.
