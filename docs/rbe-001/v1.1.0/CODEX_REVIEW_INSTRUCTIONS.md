# Codex Review Instructions - RBE-001 v1.1.0

## Required First Step

Run:

```powershell
python scripts/build_rbe001_v1_1_package.py --check
```

Stop if validation fails. Do not review or implement from a stale, corrupt, or checksum-mismatched
package.

## Authority

Read `registers/AUTHORITY_AND_CONFORMANCE.md` before interpreting architecture or engineering
requirements. In particular:

- process status is not a substantive verdict;
- Chapter 8 owns authoritative state;
- `RBE-*` and `RBE-ES-*` are separate namespaces;
- release-candidate methodology profiles cannot govern binding decisions;
- AI cannot provide human approval or Board authority.

## Review Scope

Review all 23 chapter files, the complete architecture, engineering specification, normative
registers, migration register, release material, and normalization review. Findings must cite exact
files, sections, and requirement IDs.

## Prohibited Inferences

Codex must not:

- treat PASS as a preferred result;
- convert missing process prerequisites into FAIL;
- invent a state alias, outcome mapping, quorum, severity effect, or profile threshold;
- claim RBM-001 is ACTIVE without a named human approval record and tagged release;
- silently rewrite historical IDs or artifacts;
- treat the deterministic ZIP as a different authority from its Markdown inputs;
- begin a binding operational implementation from an unapproved profile.

## Review Verdict

Use exactly one technical verdict: `READY`, `READY WITH FINDINGS`, or `NOT READY`. State human
approval and operational activation separately so a technical verdict cannot masquerade as formal
governance authority.
