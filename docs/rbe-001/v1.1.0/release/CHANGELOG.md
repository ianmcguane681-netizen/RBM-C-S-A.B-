# RBE-001 Change Log

## 1.1.0 Release Candidate - 2026-07-19

### Changed

- Normalized architecture release metadata.
- Made outcome and process-status types mutually exclusive.
- Made Chapter 8 the sole state authority.
- Namespaced Engineering Specification requirements as `RBE-ES-*`.
- Replaced hardcoded SEV-to-verdict logic with active-profile evaluation.
- Separated evaluation, ratification, and publication authority.
- Defined Foundation and production conformance boundaries.

### Added

- Verdict and state machine JSON registers.
- Requirement register and v1.0.0-to-v1.1.0 migration CSV.
- Deterministic manifest, ZIP builder, checksum, and validation tests.
- Explicit technical-review, human-approval, and operational-activation statuses.
- Principal-review corrections for requirement statement completeness, remand reachability,
  authority order, evidence-outcome floors, conditional publication metadata, and cross-platform
  byte stability.
- Repository-level review entrypoint directing readers away from the invalid historical ZIP.

### Preserved

- All controlled v1.0.0 artifacts and source checksums.
- Constitutional neutrality, human accountability, evidence traceability, append-only history,
  separation of duties, deterministic replay, and AI advisory boundaries.
