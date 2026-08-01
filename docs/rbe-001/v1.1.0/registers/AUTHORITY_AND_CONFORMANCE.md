# RBE-001 Authority and Conformance

## Order of Authority

1. RBE constitutional principles.
2. An approved RBE-001 Reference Architecture release and its normative registers.
3. An approved and ACTIVE methodology profile for a live case, operating within the architecture.
4. Approved architecture decisions and exceptions that do not weaken items 1-3.
5. RBE-001 Engineering Specification v1.1.0 for the selected conformance profile.
6. Approved schemas, implementation plans, and acceptance criteria.
7. Code, tests, user interfaces, and operational documentation.

A lower authority cannot weaken or reinterpret a higher one. Ambiguity capable of changing a
substantive outcome is a blocking architecture question.

RBE-001 v1.1.0 remains a release candidate until named human Principal Architect approval. Before
that approval it may be reviewed and used for non-binding technical validation, but it does not
effectively supersede v1.0.0 or authorize binding implementation decisions.

## Architecture and Methodology

RBE-001 defines how a governed review is represented, executed, audited, and reproduced. It does
not define case-specific evidence thresholds, quorum, severity effects, or commercial criteria.
Those values belong to a versioned methodology profile.

A profile must declare:

- profile ID, version, status, checksum, owner, and human approval record;
- review functions, eligibility, conflicts, quorum, and separation-of-duties rules;
- severity vocabulary and canonical mappings;
- its permitted subset of RBE substantive outcomes, which must include `INSUFFICIENT_EVIDENCE`;
- deterministic precedence and complete rule coverage;
- evidence sufficiency and challenge requirements;
- report templates and schema versions.

Only an `ACTIVE` profile may govern a binding live decision. Release-candidate profiles may be
used only for non-binding fixtures and advisory dry runs that are clearly labelled.

An ACTIVE profile may omit `DEFER_FOR_FURTHER_RESEARCH` only if every bounded research gap maps
to `INSUFFICIENT_EVIDENCE`. It must never map evidentiary insufficiency to `PASS`,
`PASS_WITH_FINDINGS`, or `FAIL`.

## Foundation Profile

The v1.1.0 Engineering Specification describes a local, single-process, SQLite-backed Foundation
profile. It may prove:

- domain invariants and canonical state transitions;
- deterministic profile evaluation;
- immutable lineage, audit hashing, and replay;
- schema validation and reproducible artifacts;
- authorization and separation-of-duties policy behavior.

It cannot claim production conformance, high availability, regulated retention compliance,
cryptographic publication authority, or binding live Board operation.

## Production Gate

Production use additionally requires approved deployment ADRs for identity, cryptography,
retention, privacy jurisdiction, publication audiences, SLOs, RPO/RTO, object storage, backup,
recovery, and operational ownership. These decisions cannot alter canonical verdicts, states,
traceability, or human authority.
