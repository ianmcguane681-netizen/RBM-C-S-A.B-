# RBE-001 Canonical State Machine

The machine-readable authority is `state_machine.json`. Reference Architecture Chapter 8 supplies
the normative meaning and invariants.

The initial state is `DRAFT`. Every non-terminal state has at least one explicit outbound
transition, and every state is reachable from the initial state.

## Remand Re-entry

`APPEAL_REVIEW -> REMANDED -> ASSIGNMENT` is the only canonical remand path. The transition from
`REMANDED` requires an immutable remand scope, a linked successor review session, a locked evidence
baseline, and valid assignment prerequisites. Routing through `ASSIGNMENT` prevents a remand from
bypassing independence, conflict, or role controls.

## Ownership Rule

Only canonical states may be persisted as authoritative case state. Review-role phases, tasks,
deadlines, and UI labels are projections. They cannot authorize transitions or reconstruct truth.

## Legacy Engineering-State Mapping

| v1.0.0 engineering state | v1.1.0 treatment |
|---|---|
| `CREATED` | `DRAFT` |
| `INPUT_VALIDATION` | `INTAKE_VALIDATION` |
| `READY_FOR_ASSIGNMENT` | `ACCEPTED` until evidence lock; otherwise `EVIDENCE_LOCKED` |
| `SPECIALIST_REVIEW` | `INDEPENDENT_REVIEW`, with specialist phase stored as a projection |
| `METHOD_REVIEW` | `INDEPENDENT_REVIEW`, with methodology phase stored as a projection |
| `SCEPTICAL_REVIEW` | `CHALLENGE` when adversarial review is open; otherwise `INDEPENDENT_REVIEW` |
| `DECISION_PENDING` | `CONSOLIDATION` or `GOVERNANCE_VALIDATION`, selected from immutable artifacts |
| `DECISION_COMPLETE` | `DECIDED` before controlled release; `PUBLISHED` after release |
| `REMEDIATION_REQUIRED` | Not a case state; represent as findings and linked remediation obligations |
| `RE_REVIEW_PENDING` | Not a direct state; create a governed successor session or use `REMANDED` after appeal |
| `ARCHIVED` | `ARCHIVED` |
| `CANCELLED` | `WITHDRAWN` for authorized withdrawal; `VOID` for invalidation |

Conditional mappings require explicit migration evidence. No migration may guess from a label
alone. If authoritative artifacts cannot determine the destination, migration stops and reports the
record for human review.
