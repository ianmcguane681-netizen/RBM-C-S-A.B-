# RBE-001 v1.1.0 Principal Technical Review

Review date: 19 July 2026

Reviewer type: Codex principal technical architecture review. This record is not named human
Principal Architect approval and cannot activate a methodology profile.

## Executive Determination

- Technical verdict: `READY`
- Pull-request recommendation: `APPROVE FOR MERGE AS RELEASE CANDIDATE`
- Human approval status: `REQUIRED`
- Effective supersession status: `PENDING HUMAN APPROVAL`
- RBM-001 operational status: `NOT ACTIVE`

The reviewed candidate is internally implementable without inventing verdicts, persisted states,
requirement ownership, remand behavior, or authority precedence. All principal technical findings
identified during PR #3 review were corrected on the same branch and converted into automated
regression controls where practical.

## Principal Finding Dispositions

| ID | Severity | Finding | Exact authority | Disposition |
|---|---|---|---|---|
| PR3-001 | High | Candidate language made v1.0.0 supersession effective before human approval | `README.md` Status; Reference Architecture front matter; Chapter 23.20 | Closed: supersession is proposed and becomes effective only on named human approval |
| PR3-002 | High | ACTIVE methodology was ordered above the architecture it must obey | `registers/AUTHORITY_AND_CONFORMANCE.md`, Order of Authority | Closed: constitution and approved architecture now precede every methodology profile |
| PR3-003 | High | `PROCEDURALLY_INCOMPLETE` and `BLOCKED` remained described as an outcome | Chapter 6.4.6 and 6.5; `registers/verdict_taxonomy.json` | Closed: process status and substantive outcome are separate fields and non-ready outcomes are null |
| PR3-004 | High | A profile subset could omit or remap evidentiary insufficiency | Chapter 6 requirement `RBE-DEC-062`; Engineering Specification 7.3 and Appendix B.3 | Closed: every ACTIVE profile must permit `INSUFFICIENT_EVIDENCE`; DEFER omission maps only to it |
| PR3-005 | High | `REMANDED` was a reachable non-terminal dead end | Chapter 8.3, 8.5, and `RBE-STM-061`; `registers/state_machine.json`; Engineering Appendix A | Closed: governed re-entry is `REMANDED -> ASSIGNMENT` through a linked successor session |
| PR3-006 | High | The requirement register truncated 367 line-wrapped statements | `scripts/build_rbe001_v1_1_package.py`, `collect_requirements`; `registers/requirement_register.json` | Closed: complete statements and exact source line ranges are generated and validated |
| PR3-007 | Medium | Checkout line-ending conversion could invalidate the deterministic archive on Windows | repository `.gitattributes`; package build/check contract | Closed: controlled text is LF and ZIP content is binary |
| PR3-008 | Medium | The repository entrypoint directed reviewers to the corrupt v1.0.0 ZIP | `docs/rbe-001/README.md`; `docs/rbe-001/CODEX_REVIEW_INSTRUCTIONS.md` | Closed: both now identify v1.1.0 and prohibit use of the invalid historical archive |
| PR3-009 | Medium | `BoardDecision.published_by` was required before publication | Engineering Specification 5.6 and Appendix C.1 | Closed: signed and published lifecycle fields are explicit and publication fields are conditional |
| PR3-010 | Medium | Historical source pages 157-159 had no explicit v1.1.0 disposition | Chapter 23.16 | Closed: v1.0.0 open items, certification, and limitations are retained by checksum and do not transfer approval |

## Original Normalisation Scope

| ID | v1.0.0 issue | v1.1.0 disposition |
|---|---|---|
| NR-001 | Conflicting draft/final and release metadata | One v1.1.0 release-candidate identity and explicit approval gate |
| NR-002 | Five architecture outcomes versus three engineering verdicts | Canonical outcome register plus conforming profile contract |
| NR-003 | Two incompatible state machines | Chapter 8 and `state_machine.json` are the sole state authority |
| NR-004 | Colliding requirement identifiers | `RBE-ES-*` namespace, five architecture collision fixes, and source-qualified migration |
| NR-005 | Unclear architecture/specification/methodology authority | Explicit authority order and conformance profile boundaries |
| NR-006 | Corrupt, non-reproducible AI package | Searchable Markdown, deterministic builder, manifest, ZIP, checksum, and tests |

## Verification Gate

The merge gate requires all of the following to pass on the final branch head:

- `python scripts/build_rbe001_v1_1_package.py --check`
- `python -m pytest tests/test_rbe001_package.py -q`
- `python -m pytest -q`
- `git diff --check main...HEAD`
- remote head SHA equality before merge

## Remaining Controlled Gates

These are not unresolved PR #3 architecture defects, but they prohibit operational activation:

- named human Principal Architect approval of v1.1.0;
- a conforming methodology profile that includes `INSUFFICIENT_EVIDENCE`;
- named human methodology-owner approval and an immutable `ACTIVE` release tag;
- production ADRs for identity, cryptography, retention, privacy, publication audiences,
  SLO/RPO/RTO, backup, recovery, and operational ownership;
- implementation and acceptance evidence linking requirements to tests or explicit
  non-conformance records.

## Approval Boundary

This review approves the technical merge of PR #3 as a release candidate. It does not provide the
human approval required for effective supersession, production authorization, methodology
activation, or binding live Review Board decisions.
