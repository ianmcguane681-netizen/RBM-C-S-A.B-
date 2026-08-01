# RBE-001 Canonical Verdict Taxonomy

The machine-readable authority is `verdict_taxonomy.json`.

## Substantive Outcomes

| Outcome | Meaning |
|---|---|
| `PASS` | The scoped conclusion is justified and no blocking or material residual finding remains. |
| `PASS_WITH_FINDINGS` | The scoped conclusion is justified, with explicit non-blocking findings or conditions. |
| `FAIL` | The scoped conclusion is not justified or a critical substantive defect controls. |
| `INSUFFICIENT_EVIDENCE` | The record cannot support a defensible substantive conclusion. |
| `DEFER_FOR_FURTHER_RESEARCH` | A bounded research or clarification action can resolve the defined gap. |

## Process Statuses

| Status | Meaning | Outcome allowed? |
|---|---|---|
| `READY` | Every process, integrity, authority, and profile gate passes. | Yes, exactly one |
| `PROCEDURALLY_INCOMPLETE` | A mandatory process input, role, report, or gate is missing. | No |
| `BLOCKED` | A material governance or integrity condition prevents a legitimate decision. | No |
| `VOID` | The session is invalid and cannot yield a substantive decision. | No |

## Profile Rule

An ACTIVE methodology profile may use a subset of the five substantive outcomes, but that subset
must include `INSUFFICIENT_EVIDENCE` and provide a deterministic result for every valid input in
scope. It cannot reinterpret process status as `FAIL`, silently fall back to a preferred outcome,
or suppress evidentiary insufficiency.

`DEFER_FOR_FURTHER_RESEARCH` may be omitted only when the profile maps a bounded research gap to
`INSUFFICIENT_EVIDENCE`. Evidentiary insufficiency must never map to `PASS`,
`PASS_WITH_FINDINGS`, or `FAIL`.

RBM-001 currently defines `PASS`, `PASS_WITH_FINDINGS`, and `FAIL`. It is therefore not yet
conformant with the ACTIVE-profile outcome floor. RBM-001 remains non-binding until corrected,
reviewed, approved by a named human authority, and activated.
