# Arbitrage Review Board Methodology (RBM-005)

**Document ID:** RBM-005
**Version:** 1.0.0
**Status:** RELEASE-CANDIDATE — Pending named human approval before first operational use
**Architecture Authority:** RBE-001 v1.1.0
**Applicability:** Claimed arbitrage positions across betting markets. Not applicable to research conclusions (RBM-001), engineering artefacts (RBM-002), on-chain assets (RBM-003) or listed equities (RBM-004).
**Last Updated:** 2026-08-02

---
## Table of Contents

### 6B. Canonical RBE Lifecycle Mapping

RBM-005 maps onto the RBE-001 canonical lifecycle without modification, identically to
RBM-001 through RBM-004. The lifecycle belongs to the architecture. A profile that could
rewrite it could invent a state in which its own findings did not have to be answered.

### 16.2 Activation Gate

This profile is a RELEASE CANDIDATE. It is non-binding, carries no human approval record,
and cannot authorise action. Every decision produced under it is advisory and recorded as
such until every item in `activation_requirements` is met, including two named human
approvals.

---

## 1. Why This Profile Exists

Arbitrage is the only one of these three domains where the arithmetic genuinely
guarantees a return -- and it is the one where people lose money fastest, because the
guarantee is conditional on things the arithmetic never sees.

Two books offering what looks like the same bet can settle differently. A headline price
can be available for five pounds. An account can be restricted without notice. A leg can
be voided, leaving the other side naked. Every one of these turns a locked position into
an ordinary bet, and none of them appears in the margin calculation.

This profile reviews the conditions, not the maths. The maths is a line of code.

## 2. Scope

In scope: prices offered, the sizes at which they are offered, the rules under which each
leg settles, the exposure if a leg voids, and whether the account can actually place the
required stake.

Out of scope: whether an outcome will occur, what odds are 'fair', value betting, model
prices, and anything requiring a view on the event itself. This board reviews whether a
claimed lock is a lock.

**Decision Finalisation and Publication Separation** applies unchanged from RBE-001: the
actor who assembles a decision may not publish it, and neither may be the sceptical seat.

## 3. The Artefact Is a Priced Instant

A review is pinned to a set of quotes, each carrying its source, market, and the instant it
was observed. Prices move continuously, so a review under this profile describes an instant
and expires in seconds rather than days.

That is not a weakness to work around; it is the subject. An arb assembled from prices read
minutes apart existed at neither of them, and the timestamp is what makes the difference
visible.

## 4. Board Composition

Six specialist seats -- PQA MIA EXA ALA CPA RPA -- plus a Board Chair, a Methodology
Auditor and a Sceptical Reviewer. The pool, the tiers and the quorum are declared in
`PROFILE.json` and enforced by the runtime rather than by this document.

## 5. The Six Market Gates

### AG-01 — Price observability

**Reviewer seat:** PQA

**Requirement.** Every price must carry its source, its market, and the instant it was observed. A price without a timestamp is not evidence, because the whole claim depends on both legs being available at once.

**Failure mode.** An arb is computed from prices read minutes apart. It existed for neither of them together.

### AG-02 — Market identity and settlement

**Reviewer seat:** MIA

**Requirement.** Both legs must be shown to settle under identical rules, quoted verbatim from each operator. Rules are never normalised, paraphrased, or assumed equivalent because the market names match.

**Failure mode.** Two books offer 'Team A to win'. One voids on abandonment and the other pays; one settles at 90 minutes and the other includes extra time. Both legs priced correctly and the lock is a coin flip.

### AG-03 — Executability at size

**Reviewer seat:** EXA

**Requirement.** The stated odds must be shown available at the stake the arb requires. Exchange sizes are observed from the book; bookmaker limits are an upper bound applied per account and must be labelled as such.

**Failure mode.** A headline price is available for five pounds. The arb is real and worth nothing.

### AG-04 — Account and limit reality

**Reviewer seat:** ALA

**Requirement.** Account status, stake restrictions and prior limitations must be recorded. An arb requiring a stake the account cannot place is UNFILLABLE, never profit.

**Failure mode.** The account has been restricted to a fraction of the advertised maximum, and every calculation assumed the advertised one.

### AG-05 — Counterparty and void exposure

**Reviewer seat:** CPA

**Requirement.** The loss if one leg voids and the other loses must be computed and reported beside the guaranteed return. Palpable-error and void policies must be quoted from each operator.

**Failure mode.** A twenty-nine pound guaranteed return carries two hundred and fifty pounds of one-sided exposure, and only the twenty-nine appears on the screen.

### AG-06 — Reproducibility

**Reviewer seat:** RPA

**Requirement.** Every quoted price must be recorded with enough detail that a third party can state what was offered, where, and when. Commission treatment must be shown in the arithmetic rather than assumed.

**Failure mode.** A margin is reported gross of commission. At five per cent of net winnings a one per cent margin was never a margin.

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

It produces three lists: what is established at this artefact, what is alleged and
unverified, and what could not be checked at all. Anyone converting that into a
position is making a decision the board did not make and does not endorse.

A review under this profile can never, by itself, authorise a transaction.
Authorisation requires a ratified mandate under a binding profile, which this is not.
