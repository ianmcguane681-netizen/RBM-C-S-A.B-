# RBE-001 v1.1.0 Normalisation Decisions

Status: Normative candidate for the v1.1.0 normalization release.

These decisions resolve contradictions in v1.0.0 without modifying or deleting the controlled
v1.0.0 artifacts. The old release remains historical evidence. Supersession for future
implementation becomes effective only after named human Principal Architect approval.

## NORM-001 - Release Identity

RBE-001 v1.1.0 is the normalized architecture release candidate. It covers Chapters 1-23 and is no
longer a sectional draft. The candidate is technically ready for named human approval. It does not
represent that approval, effectively supersede v1.0.0, or activate a methodology profile.

## NORM-002 - Verdict Taxonomy

RBE has five substantive outcomes:

- `PASS`
- `PASS_WITH_FINDINGS`
- `FAIL`
- `INSUFFICIENT_EVIDENCE`
- `DEFER_FOR_FURTHER_RESEARCH`

`PROCEDURALLY_INCOMPLETE`, `BLOCKED`, and `VOID` are process statuses, not verdicts. A blocked
evaluation has no substantive outcome. Each ACTIVE methodology profile declares a total
deterministic mapping and MUST include `INSUFFICIENT_EVIDENCE` in its permitted outcome set. A
profile may omit `DEFER_FOR_FURTHER_RESEARCH` only by mapping bounded research gaps to
`INSUFFICIENT_EVIDENCE`; it cannot disguise evidentiary insufficiency as `PASS`,
`PASS_WITH_FINDINGS`, or `FAIL`.

## NORM-003 - State Authority

Reference Architecture Chapter 8 and `state_machine.json` define the only authoritative case
state machine. The v1.0.0 Engineering Specification states are retired. Specialist, methodology,
sceptical, commercial, and governance phases are assignment projections inside canonical states,
not competing persisted states.

`REMANDED` re-enters through `ASSIGNMENT` after a governed successor session and explicit remand
scope are recorded. This prevents remand from becoming a dead end or bypassing assignment and
independence controls.

## NORM-004 - Requirement Ownership

Architecture requirements retain `RBE-[DOMAIN]-NNN`. Five source-qualified collisions inside the
v1.0.0 architecture receive new IDs, while the earlier definitions retain their historical IDs.
Engineering requirements use `RBE-ES-[DOMAIN]-NNN`. Historical IDs are never reused or silently
redefined. The migration CSV records every architecture collision and every v1.0.0 engineering ID.

## NORM-005 - Authority and Profiles

The RBE Reference Architecture is methodology-neutral and controls constitutional, domain, and
security semantics. The Engineering Specification defines a non-production Foundation profile.
An ACTIVE methodology profile supplies quorum, required roles, thresholds, evidence sufficiency,
severity effects, and its permitted outcome subset. No methodology profile can override the RBE
constitution.

RBM-001 remains non-operational until a named human authority approves and tags it ACTIVE.

The architecture and its normative registers outrank every methodology profile. An ACTIVE profile
governs case-specific thresholds and rules only within those constitutional and domain bounds.

## NORM-006 - Publication and Reproducibility

Individual Markdown files are the primary AI-readable publication. The ZIP is a deterministic
derivative generated from those files. The manifest, archive, checksum file, chapter count,
requirement namespaces, verdict register, and state register are validated automatically.

Requirement statements are reconstructed across controlled line wraps and carry exact source line
ranges. Repository line-ending attributes keep those bytes stable across supported operating
systems.
