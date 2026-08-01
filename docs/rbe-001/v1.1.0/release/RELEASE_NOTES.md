# RBE-001 v1.1.0 Release-Candidate Notes

Release date: 19 July 2026

## Purpose

This normalization candidate resolves publication and implementation contradictions discovered in
the v1.0.0 controlled package. It does not erase or mutate v1.0.0, and supersession is not effective
until named human Principal Architect approval.

## Resolved

- Unified release version, coverage, status, and supersession metadata.
- Separated five substantive outcomes from four process statuses.
- Adopted Chapter 8 as the canonical state machine.
- Retired the alternate Engineering Specification lifecycle.
- Resolved five internal architecture ID collisions and moved all engineering IDs into `RBE-ES-*`,
  with source-qualified migration lineage.
- Defined authority among constitution, active methodology, architecture, profiles, and code.
- Classified SQLite as a non-production Foundation profile.
- Replaced the corrupt AI package process with deterministic generation and validation.
- Preserved complete wrapped requirement statements with exact source line ranges.
- Closed the `REMANDED` lifecycle dead end through governed successor assignment.
- Required `INSUFFICIENT_EVIDENCE` in every ACTIVE methodology profile.
- Corrected architecture-over-methodology authority and publication-field conditionality.
- Added cross-platform line-ending controls and a current repository review entrypoint.

## Operational Limitations

- Human Principal Architect approval is not supplied by this release.
- RBM-001 remains non-operational until approved and tagged ACTIVE.
- Production deployment requires controlled identity, cryptography, retention, privacy, audience,
  SLO, RPO/RTO, backup, and recovery decisions.
