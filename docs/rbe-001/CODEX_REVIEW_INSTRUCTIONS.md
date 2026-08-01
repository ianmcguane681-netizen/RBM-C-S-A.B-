# Codex Review Instructions - RBE-001

## Current Source

Review the RBE-001 v1.1.0 normalization candidate under:

`docs/rbe-001/v1.1.0/`

Do not extract or review from the root-level v1.0.0 ZIP. That repository artifact fails its
recorded checksum and archive validation and is retained only as historical evidence.

## Required First Step

From the repository root, run:

```powershell
python scripts/build_rbe001_v1_1_package.py --check
```

Stop if validation fails. Then read, in order:

1. `v1.1.0/registers/NORMALISATION_DECISIONS.md`
2. `v1.1.0/registers/AUTHORITY_AND_CONFORMANCE.md`
3. `v1.1.0/registers/VERDICT_TAXONOMY.md`
4. `v1.1.0/registers/STATE_MACHINE.md`
5. all 23 chapter files and the complete architecture
6. the v1.1.0 Engineering Specification
7. the principal technical review and release material

## Review Rules

Findings must cite exact files, sections, and requirement IDs. Codex must not invent architecture,
weaken a `SHALL`, infer an outcome mapping, or treat process status as a verdict. AI technical
review cannot supply named human Principal Architect approval or activate a methodology profile.

Use one technical verdict: `READY`, `READY WITH FINDINGS`, or `NOT READY`. State human approval,
effective supersession, methodology activation, and production authorization as separate gates.
