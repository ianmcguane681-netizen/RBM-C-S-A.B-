# RBE Runtime v0.1 Architecture Decision Log

## Control Status

This log records implementation decisions for RBE runtime v0.1. It is
non-normative and cannot amend, reinterpret, activate, or supersede RBE-001
v1.1.0 or RBM-001 v2.0.0. If an entry conflicts with either controlled package,
the controlled package prevails and the implementation must stop for Principal
Architect review.

Entry status `IMPLEMENTED_PENDING_REVIEW` means code exists on the unmerged
feature branch but has not acquired architectural authority.

## Decision Index

| ID | Decision | Status |
|---|---|---|
| ADL-001 | Shared controlled-authority validation boundary | `IMPLEMENTED_PENDING_REVIEW` |
| ADL-002 | Release Candidate execution is advisory only | `IMPLEMENTED_PENDING_REVIEW` |
| ADL-003 | Preserve exact RBM records inside normalized RBE envelopes | `IMPLEMENTED_PENDING_REVIEW` |
| ADL-004 | Business logic depends on the `ReviewStore` persistence port | `IMPLEMENTED_PENDING_REVIEW` |
| ADL-005 | Machine evaluation, human ratification, and publication remain separate | `IMPLEMENTED_PENDING_REVIEW` |

## ADL-001 - Shared Controlled-Authority Validation Boundary

**Context:** Package validation was initially implemented in engineering scripts,
which caused operational runtime modules to import tooling code.

**Decision:** The reusable validation implementation lives in
`controlled_authority/`. Runtime modules and CLI scripts consume that package.
Files in `scripts/` contain command-line adaptation only, and runtime imports
from `scripts/` are prohibited by an AST boundary test.

**Authority basis:** Controlled-package integrity, version compatibility, and
methodology-profile validation are prerequisites to runtime execution; tooling
location is an implementation concern.

**Consequences:** There is one package-validation implementation. Tooling cannot
become an undeclared runtime dependency. Controlled file ordering uses an
explicit canonical POSIX-path key rather than operating-system `Path` ordering,
so package roots remain stable across Windows and Linux runners.

**Verification:** RBE/RBM package validators and
`test_runtime_does_not_import_engineering_scripts`.

## ADL-002 - Release Candidate Execution Is Advisory Only

**Context:** RBM-001 v2.0.0 remains `RELEASE_CANDIDATE`, while Issue #5 requires
Foundation execution and golden outcome scenarios.

**Decision:** RC execution is permitted only as `ADVISORY_DRY_RUN`. It is
non-binding, cannot permit merge, and cannot activate or mutate the methodology.
`BINDING_LIVE` fails closed unless the profile is ACTIVE, binding, and has its
required human approval record.

**Authority basis:** RBE-ES-DEC-002, the RBM profile activation controls, and the
controlled conformance fixtures.

**Consequences:** Foundation behavior can be proven without manufacturing
authority that the profile does not possess.

**Verification:** Authority and service tests for advisory execution, binding
rejection, ratification, and publication.

## ADL-003 - Preserve Exact RBM Records Inside Normalized RBE Envelopes

**Context:** The RBE ReviewerReport model requires normalized summary and
recommendation fields. The closed RBM TPL-RRR schema intentionally forbids those
additional fields.

**Decision:** Preserve the exact schema-valid RBM record as `raw_record`; store
RBE normalization fields in the governed outer submission record. Never modify
the controlled schema or silently discard either contract.

**Authority basis:** RBE ReviewerReport requirements and closed RBM TPL-RRR
validation are both authoritative.

**Consequences:** Exact methodology records remain reproducible while the runtime
retains the normalized fields required by RBE.

**Verification:** Closed-schema, normalization, immutable-record, and bundle
round-trip tests.

## ADL-004 - Business Logic Depends on the ReviewStore Port

**Context:** SQLite is approved for Foundation, but persistence must remain an
implementation detail.

**Decision:** Orchestration and artifact export depend on the structural
`ReviewStore` protocol. SQLite is selected by the default adapter factory.
Alternative durable stores are supplied by constructor injection and must honor
the same atomicity, immutability, idempotency, and audit contract.

**Authority basis:** RBE persistence and audit behavior is mandatory; database
product selection is not business logic.

**Consequences:** A future PostgreSQL adapter does not require changes to the
review workflow or decision engine. No current persistence behavior changes.

**Verification:** `test_runtime_accepts_repository_through_storage_port` plus
the repository, service, artifact, and audit suites.

## ADL-005 - Separate Evaluation, Ratification, and Publication

**Context:** A deterministic machine result is not a signed Board decision, and
a Board decision is not publication.

**Decision:** Persist a frozen decision candidate first, require explicit human
ratification second, and permit publication only through an independent
publication authority. Recommendations remain outside outcome computation.

**Authority basis:** RBE decision authority and publication separation controls,
plus RBM role-separation and decision-precedence rules.

**Consequences:** Automation cannot sign, publish, or upgrade its own result.
Publication cannot alter the computed outcome.

**Verification:** Decision replay, ratification, role-separation, publication,
and tamper-detection tests.
