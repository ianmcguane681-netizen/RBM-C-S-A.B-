# RBE-001 v1.1.0 Architecture Normalisation Candidate

This candidate proposes to supersede RBE-001 v1.0.0 for future implementation. Effective
supersession requires named human Principal Architect approval. The v1.0.0 controlled artifacts
remain immutable historical evidence.

## Status

- Codex technical architecture verdict: `READY`.
- Named human Principal Architect approval: required.
- Effective supersession of v1.0.0: pending that approval.
- RBM-001 operational status: not ACTIVE.
- Binding live Review Board decisions: prohibited until an ACTIVE methodology profile is loaded.

## What Changed

1. Release identity is consistently v1.1.0 across the normalized package.
2. Substantive outcomes are separated from process statuses.
3. Reference Architecture Chapter 8 is the only authoritative state machine.
4. Engineering requirements use `RBE-ES-*`; architecture requirements retain `RBE-*`.
5. Architecture, engineering profile, and methodology authority are explicitly separated.
6. Individual Markdown files are committed directly and the ZIP is generated deterministically.

## Reading Order

1. `registers/NORMALISATION_DECISIONS.md`
2. `registers/AUTHORITY_AND_CONFORMANCE.md`
3. `registers/VERDICT_TAXONOMY.md`
4. `registers/STATE_MACHINE.md`
5. `architecture/RBE-001_Reference_Architecture_v1.1.0.md`
6. `engineering/RBE-001_Engineering_Specification_v1.1.0.md`
7. `review/RBE-001_Architecture_Normalisation_Review_v1.1.0.md`

## Verification

From the repository root:

```powershell
python scripts/build_rbe001_v1_1_package.py --check
python -m pytest tests/test_rbe001_package.py
```

The ZIP is a derivative artifact. The searchable Markdown and machine-readable registers are the
review source. A checksum match alone is insufficient unless archive entries also match the
manifest and repository files byte for byte.
