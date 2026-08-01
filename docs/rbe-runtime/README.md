# RBE Runtime v0.1 Developer Guide

## Status

RBE runtime v0.1 is a local, single-node Foundation implementation of:

- RBE-001 Reference Architecture and Engineering Specification v1.1.0.
- RBM-001 Review Board Methodology v2.0.0.
- GitHub Issue #5, "Implement RBE runtime v0.1 incrementally."

It is deliberately non-production. RBM-001 is `RELEASE_CANDIDATE`, so every
execution is an `ADVISORY_DRY_RUN`; outputs are non-binding and cannot permit a
merge.

## Authority Boundary

The runtime loads and validates the controlled packages on startup. It does not
copy their lifecycle or outcome tables into a second configuration:

- Shared package integrity rules live in `controlled_authority/`; the runtime
  and the two CLI scripts consume that library, and runtime code never imports
  from `scripts/`.
- Lifecycle states and transitions come from
  `docs/rbe-001/v1.1.0/registers/state_machine.json`.
- Process and outcome taxonomy comes from
  `docs/rbe-001/v1.1.0/registers/verdict_taxonomy.json`.
- Roles, quorum, role separation, unresolved statuses, and decision precedence
  come from `docs/review-board/PROFILE.json`.
- RBM records are validated against the closed schemas in
  `docs/review-board/schemas/`.
- Role-to-spec eligibility is read from the eight controlled RBS documents.

The two specifications are not modified by this runtime.

## Runtime Modules

| Module | Responsibility |
|---|---|
| `authority.py` | Validate and load controlled RBE/RBM packages |
| `schemas.py` | Draft 2020-12 validation for closed RBM records |
| `profile.py` | Profile-driven role, spec, quorum, and separation policy |
| `state_machine.py` | Canonical lifecycle guard |
| `validation.py` | Initiation, report, finding, evidence, and remediation cross-record checks |
| `decision.py` | Pure safe interpretation of RBM decision precedence |
| `storage.py` | Backend-neutral `ReviewStore` persistence contract and adapter factory |
| `repository.py` | Foundation SQLite adapter: migrations, idempotency, append-only audit |
| `service.py` | Lifecycle prerequisites, review orchestration, ratification, publication |
| `artifacts.py` | Deterministic JSON/Markdown export and checksum validation |
| `cli.py` | Headless authority, audit, export, and bundle commands |

The deterministic decision core has no database, network, UI, or AI dependency.

## Lifecycle

The runtime enforces the canonical RBE state machine and transition
prerequisites. Important controls include:

- Review initiation must match the loaded profile checksum and manifest.
- Returned packages are immutable; resubmission appends a successor package.
- Evidence content and provenance are preserved before `EVIDENCE_LOCKED`.
- Each board role is held by a distinct named human.
- Signed independence/conflict declarations precede independent review.
- Specialists report before the Sceptical Reviewer; the Methodology Auditor
  closes the report phase.
- Findings must link to their source report and registered evidence.
- Accepted remediation must come from a schema-valid TPL-RMP record.
- Decision inputs freeze before machine evaluation.
- A machine candidate is separate from human ratification.
- Publication is explicit and performed by an actor separate from Chair and MA.
- Appeal/remand/final/archive transitions require traceable control metadata.

## Decision Behavior

RBM expressions are parsed with a restricted AST evaluator. Arbitrary Python,
function calls, attributes, and imports are rejected. Startup validates rule
priority uniqueness, permitted outcomes, and finite boundary coverage.

The engine records:

- Process status.
- Outcome, or `null` for a non-READY process.
- Rules evaluated and selected reason code.
- Findings and counter-evidence considered.
- Process blockers.
- Profile/engine versions and profile checksum.
- Canonical frozen-snapshot hash.
- Deterministic explanation text.

Recommendations, timestamps, row order, votes, and commercial preference do
not influence the outcome.

## Persistence

Review orchestration and artifact export depend on the structural `ReviewStore`
protocol in `storage.py`. They do not depend on SQLite types. `open_sqlite_store`
selects the local Foundation adapter when `RBERuntime` receives a database path.
A future durable backend must implement the same record, atomicity, idempotency,
immutability, and audit-verification contract, then can be injected without
changing business logic:

```python
runtime = RBERuntime(repository=review_store_adapter)
```

Supplying both `database_path` and `repository` is rejected so backend ownership
is unambiguous. This is an implementation boundary, not permission to weaken any
RBE/RBM persistence or audit requirement.

SQLite foreign keys are enabled on every runtime connection. Migrations are
ordered and checksum-verified. Startup refuses a newer or checksum-mismatched
schema and verifies every existing session audit chain.

Material source records are append-only. State transitions and their audit
events commit atomically. Commands require idempotency keys; replaying the same
key and payload returns the original result, while a changed payload is rejected
and audited.

Evidence bytes are stored in SQLite for this Foundation build. Protect runtime
databases and exports because they may contain sensitive review material.

## Python Entry Point

```python
from rbe_runtime.models import ExecutionMode
from rbe_runtime.service import RBERuntime

runtime = RBERuntime("review.sqlite3")
runtime.initiate_review(
    initiation_record,
    actor=initiation_record["board_chair"],
    idempotency_key="initiate-001",
    execution_mode=ExecutionMode.ADVISORY_DRY_RUN,
)
```

All write methods require an accountable actor and idempotency key. See
`tests/test_rbe_runtime_service.py` for complete governed scenarios.

Implementation choices and their authority basis are recorded in
`ARCHITECTURE_DECISION_LOG.md`. That log is non-normative and does not amend the
controlled RBE or RBM packages.

## Headless Commands

```powershell
python -m rbe_runtime version
python -m rbe_runtime validate-authority
python -m rbe_runtime verify-audit --database review.sqlite3 --session REV-001
python -m rbe_runtime export --database review.sqlite3 --session REV-001 --output rbe-bundles/REV-001
python -m rbe_runtime verify-bundle --bundle rbe-bundles/REV-001
```

CLI failures return stable JSON errors without stack traces, secrets, or
database paths.

## Export Contract

An exported bundle contains at least:

- `session.json`
- `package-manifest.json`
- `assignments.json`
- `evidence.json` and preserved `evidence/*.bin`
- `reports.json`
- `findings.json`
- `remediation-plans.json`
- `decision.json`
- `audit.jsonl`
- `review-report.md`
- `bundle-manifest.json`

All JSON is canonical UTF-8. The bundle manifest records every artifact's
SHA-256 and size plus a canonical bundle root hash. Re-exporting an unchanged
session is byte-stable.

## Test Commands

Focused runtime suite:

```powershell
python -m pytest -p no:cacheprovider tests/test_rbe_runtime_authority.py tests/test_rbe_runtime_validation.py tests/test_rbe_runtime_repository.py tests/test_rbe_runtime_decision.py tests/test_rbe_runtime_service.py tests/test_rbe_runtime_artifacts.py tests/test_rbe_runtime_cli.py
```

Full repository:

```powershell
python -m pytest -p no:cacheprovider
```

## Deliberate Non-Goals

- No Streamlit or other UI.
- No distributed service or OpenAPI deployment.
- No autonomous or authoritative AI reviewer.
- No cryptographic signature infrastructure; v0.1 preserves accountable
  signature references.
- No live profile activation or binding decision.
- No external identity, notification, queue, or object-storage system.
- No production authentication or authorization adapter.

These exclusions preserve Issue #5's Foundation boundary and do not weaken the
controls implemented inside that boundary.
