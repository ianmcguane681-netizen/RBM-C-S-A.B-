# RBE Runtime v0.1 Traceability

## Issue #5 Scope

| Issue requirement | Primary implementation | Acceptance coverage |
|---|---|---|
| 1. Validate review initiation | `authority.py`, `schemas.py`, `profile.py`, `validation.py`, `service.py` | `test_rbe_runtime_authority.py`, `test_rbe_runtime_validation.py` |
| 2. Enforce canonical lifecycle | `state_machine.py`, `service.py`, atomic `repository.py` transition | Every registered/prohibited transition tests; service stage and successor-package tests |
| 3. Load RBM profile/specifications | `AuthorityBundle`, `ProfilePolicy`, `DecisionEngine` | Package identity, compatibility, role/spec, unsafe-rule, and total-coverage tests |
| 4. Preserve evidence/provenance | `EvidenceReference`, SQLite evidence BLOB/provenance, bundle evidence files | Hash mismatch, round-trip, evidence-lock, unknown-reference, export tests |
| 5. Accept structured reports/findings | Closed RBM schema validation plus immutable RBE normalization envelope | Report/finding identity, schema, evidence lineage, AI verification, append-only tests |
| 6. Validate roles/quorum/conflicts/cross-records | Profile-driven role plan, signed conflict declarations, publication separation | Quorum, duplicate actor, material conflict, actor mismatch, decision bundle tests |
| 7. Apply deterministic rules | Restricted AST evaluator over `PROFILE.json` precedence | All outcomes, precedence, non-READY null outcome, unsafe syntax, 100-run replay |
| 8. Produce decision and final report | Candidate, ratification, publication, JSON/Markdown artifact exporter | Five Golden scenarios, RC ceiling, deterministic export, bundle tamper tests |
| 9. Maintain append-only audit | Hash-chained SQLite events and startup/CLI verification | Sequence, rollback, idempotency, immutability trigger, out-of-band tamper tests |

## Authoritative Engineering Controls

| Control family | Requirements represented | Runtime evidence |
|---|---|---|
| Purpose and boundaries | RBE-ES-PUR-001..004, DES-001..004 | Pure decision module, versioned records, JSON and Markdown outputs |
| Lifecycle | RBE-ES-LIF-001..010 | Canonical register loader, prerequisite service, atomic transition, idempotency |
| Domain lineage | RBE-ES-DOM-001..006 | Assignment-report-finding FKs, supersession fields, canonical UTC output |
| Orchestration | RBE-ES-ORC-001..012 | Profile checksum, role plan, conflict declarations, phase and readiness guards |
| Decisions | RBE-ES-DEC-001..008 | Frozen hashes, safe profile rules, candidate/ratification split, immutable history |
| Persistence | RBE-ES-PER-001..005 | FK connections, transaction boundaries, migration checks, newer-schema refusal |
| Audit | RBE-ES-AUD-001..004 | Append-only triggers, canonical hash chain, verifier, hashed sensitive rationale in audit |
| Schemas/artifacts | RBE-ES-SCH-001..008 | Closed RBM schemas, canonical JSON, safe paths, manifests and import verification |
| Human report | RBE-ES-HUM-001..005 | Frozen decision report, deterministic finding order, recommendation/verdict separation |
| Security | RBE-ES-SEC-001, 004, 005, 008 | Path containment, recomputed checksums, no secrets, accountable publication actor |
| Foundation operations | RBE-ES-NFR-002..003, OPS-001..003, OPS-006..007 | Offline core tests, clean migration/golden flow, startup audit check, dedicated branch/PR |

## Required Scenario Fixtures

The closed scenario catalog is under `tests/fixtures/rbe_runtime/`:

- `pass.json`
- `pass_with_findings.json`
- `fail.json`
- `insufficient_evidence.json`
- `blocked.json`

The scenarios are executed end to end by `test_rbe_runtime_service.py`; the
fixture catalog and expected outcome set are validated by
`test_rbe_runtime_cli.py`.
