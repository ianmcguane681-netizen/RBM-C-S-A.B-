# RBE-001 - Review Board Engine

This directory contains the controlled Review Board Engine architecture history and the current
normalization candidate for technical and human review.

## Current Review Baseline

The current baseline is [`v1.1.0/`](v1.1.0/README.md).

- Status: normalization release candidate.
- Codex principal technical verdict: pending completion of the PR #3 review record.
- Named human Principal Architect approval: required.
- Operational methodology activation: prohibited until a conforming methodology profile is
  approved and tagged `ACTIVE`.

Validate the candidate from the repository root:

```powershell
python scripts/build_rbe001_v1_1_package.py --check
python -m pytest tests/test_rbe001_package.py
```

The searchable Markdown and machine-readable registers in `v1.1.0/` are the review source. The
ZIP is a deterministic derivative, not a separate authority.

## Historical v1.0.0 Material

The root-level v1.0.0 manifest, ZIP, and Markdown are retained as historical evidence. The
repository copy of `RBE-001_AI_Reader_Package_v1.0.0.zip` does not match its recorded checksum and
does not form a valid review archive. It MUST NOT be used for implementation or current review.

Historical approval language does not transfer to v1.1.0. Effective supersession requires the
named human approval recorded by the v1.1.0 release gate.

## Constitutional Principles

- The Review Board has no interest in whether a proposal succeeds or fails.
- The burden of justification rests with the conclusion, not with its critics.
- Every decision must be traceable and reproducible.
- AI may assist review but cannot provide human approval or binding Board authority.
