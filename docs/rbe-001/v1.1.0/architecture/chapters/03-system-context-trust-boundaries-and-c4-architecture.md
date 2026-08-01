---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 3
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 3. System Context, Trust Boundaries and C4 Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 13 -->

## 3.1 System Context
RBE sits downstream of a reviewable artifact and upstream of any claim that the artifact or
conclusion has passed formal governance. It can review outputs from GS-P001, future Golden
Studies, Solution Validation, specifications, methodologies or other controlled packages, provided a
compatible review profile exists.
Logical context flow
Reviewable Package Producer
|
v
Package Registration + Validation
|
v
Independent Board Functions
| Methodology | Evidence | Reasoning | Challenge | Commercial | Governance |
|
v
Finding Normalization + Conflict Handling
|
v
Deterministic Decision Assembly
|
v
Decision Record + Review Report + Audit/Replay Bundle
|
v
Approved downstream consumer or rework/research loop
**RBE-CTX-001** RBE SHALL treat every upstream artifact as untrusted until package validation completes.
**RBE-CTX-002** RBE SHALL publish an outcome only after all mandatory board functions and decision
prerequisites are satisfied.
**RBE-CTX-003** Downstream systems SHALL consume signed or checksummed decision artifacts, not infer
approval from session status or user-interface text.
## 3.2 External Actors and Systems
Actor or system Relationship to RBE
Package producer Submits a complete, versioned review package
and responds to formal requests for correction
or additional evidence.
Board reviewer Accepts one eligible assignment, declares
conflicts and submits a structured independent
report.
Governance officer Manages procedural readiness and finalization
authority without changing reviewer findings.
Methodology registry Provides immutable methodology and rule-set

<!-- Controlled source page 14 -->

Actor or system Relationship to RBE
versions.
Evidence repository Provides registered evidence objects or
immutable references.
Identity provider / actor registry Supplies actor identity and eligibility data;
optional adapter in v1.
Artifact consumer Reads board decisions, reports and replay
bundles.
Auditor Reconstructs state transitions, inputs, findings
and decision calculation.
Codex / engineering automation Builds and tests the engine but has no live
governance authority.
## 3.3 C4 Level 1 — System Boundary
The RBE system boundary contains all logic and records required to validate a package, orchestrate
independent reviews, normalize findings, calculate an outcome, generate artifacts and preserve
auditability. Research collection, product prioritization and component engineering remain outside
the boundary.
Inside RBE boundary Outside RBE boundary
Review session lifecycle Golden Study evidence discovery
Role assignment and conflict checks Solution ideation and product design
Reviewer report intake Client relationship management
Finding and challenge management Commercial approval to fund a build
Deterministic decision assembly Source scraping and market research
Decision artifact publication General project management
Audit and replay export Production deployment of approved
components
## 3.4 C4 Level 2 — Containers
Container Responsibility
Operator / Reviewer Web UI Neutral presentation of assignments, package
materials, reports, findings and decision
artifacts.
REST API Authenticated command and query interface;
validation, idempotency and authorization

<!-- Controlled source page 15 -->

Container Responsibility
boundary.
Application Service Layer Use-case orchestration for registration,
assignment, submission, challenge, readiness
and finalization.
Domain Core Pure entities, invariants, state machine,
independence rules and deterministic decision
functions.
Persistence Adapter Transactional storage, migrations, append-only
versioning and query projection.
Artifact Generator Canonical JSON, Markdown and export bundle
creation.
Audit Ledger Hash-linked event records and integrity
verification.
CLI / Replay Tool Headless execution, conformance tests and
deterministic replay.
Configuration Registry Versioned board profiles, role constraints,
schemas and rule sets.
**RBE-ARC-001** The domain core SHALL have no dependency on web frameworks, database drivers, UI
libraries, network clients or AI services.
**RBE-ARC-002** All state-changing operations SHALL pass through application services and a single
validated domain transition path.
**RBE-ARC-003** Artifact generation SHALL operate from a frozen decision snapshot, not from mutable
live queries.
**RBE-ARC-004** The CLI replay path and API finalization path SHALL invoke the same decision functions.
## 3.5 C4 Level 3 — Core Components
Component Key responsibilities
Package Registry Manifest validation, file hashes, schema
compatibility, completeness and version
locking.
Conflict and Eligibility Service Authorship/sponsorship checks, role
incompatibilities, declarations and recusal
state.
Assignment Orchestrator Seat creation, staged disclosure, phase
readiness and replacement handling.
Report Validator Schema validation, actor authority, evidence

<!-- Controlled source page 16 -->

Component Key responsibilities
reference validity and report immutability.
Finding Registry Finding creation, severity lineage,
deduplication suggestions, supersession and
resolution state.
Challenge Manager Contrary evidence, alternative explanations,
assumptions and decision-change conditions.
Readiness Evaluator Deterministic list of unmet prerequisites and
blockers.
Decision Engine Pure normalization and rule-set evaluation
producing outcome and reasons.
Artifact Builder Canonical decision JSON, review report and
audit/replay bundle.
Audit Service Append-only events, actor attribution, hashes
and integrity verification.
## 3.6 Trust Boundaries
Boundary Required control
External package  RBE→ Content hash, schema validation, malware-safe
handling, manifest completeness and version
lock.
Reviewer  API→ Authenticated actor, assignment authorization,
conflict-cleared state, request validation and
idempotency.
Application  Domain core→ Typed commands only; no direct state
mutation.
Domain core  Persistence→ Transactional append/version operations
preserving invariants.
Decision snapshot  Artifact builder→ Frozen canonical snapshot and rule-set
checksum.
RBE  Downstream consumer→ Signed or checksummed artifact, stable
identifiers and explicit outcome status.
AI service  Reviewer workflow→ Untrusted suggestion channel; no direct
mutation or decision authority.

<!-- Controlled source page 17 -->

## 3.7 Primary Data Flows
### 3.7.1 Package registration
4. Submit manifest and referenced files.
5. Validate required types and checksums.
6. Resolve methodology, profile and schema versions.
7. Create immutable package version and review session.
### 3.7.2 Independent review
8. Evaluate eligibility and conflict declaration.
9. Release only stage-appropriate information.
10. Accept structured report and evidence links.
11. Lock report version and create normalized findings.
### 3.7.3 Challenge
12. Collect contradictions, alternatives and assumptions.
13. Link each challenge to evidence or reasoning claim.
14. Require disposition without deleting disagreement.
### 3.7.4 Decision finalization
15. Freeze accepted inputs.
16. Evaluate procedural blockers.
17. Run deterministic rule set.
18. Persist decision, reasons and snapshot atomically.
19. Generate artifacts and integrity hashes.
### 3.7.5 Re-review
20. Register corrected or expanded package.
21. Create a new linked session.
22. Preserve prior reports and outcome.
23. Run the full applicable review profile again.
## 3.8 Reference Technology Profile
Concern Reference choice
Language Python 3.12+ unless repository constraints
require an approved alternative.
API FastAPI or equivalent OpenAPI-first
framework.
Persistence SQLite for v1 with foreign keys, WAL mode
where appropriate and migration-managed
schema.
Schemas JSON Schema draft 2020-12.
Artifacts Canonical UTF-8 JSON and Markdown; optional
PDF generated from the canonical report.

<!-- Controlled source page 18 -->

Concern Reference choice
Testing Unit, property, integration, state-transition,
golden artifact, replay and corruption tests.
Packaging Single-process local deployment initially;
network-independent decision capability.
Time UTC RFC 3339 timestamps; time never
influences verdict except where a rule
explicitly governs deadlines.
Identifiers UUIDv7 or approved stable alternative;
identifiers never affect decision output.
Integrity SHA-256 or stronger approved hash over
package files, rule sets, snapshots and artifacts.
**RBE-TEC-001** The engine SHALL operate without external network access after all required package
content, schemas and rule sets are registered locally.
**RBE-TEC-002** External identity, notification, storage or AI services SHALL be optional adapters and
SHALL NOT be necessary for decision calculation or replay.
**RBE-TEC-003** Database-generated ordering SHALL NOT be used where canonical artifact ordering is
required; explicit deterministic sort keys SHALL be defined.
## 3.9 Recommended Repository Structure
rbe/
pyproject.toml
src/rbe/
domain/
entities.py
value_objects.py
invariants.py
state_machine.py
decision_engine.py
independence.py
application/
commands/
queries/
services/
dto/
adapters/
persistence/
identity/
notifications/
ai_assistance/
api/
routes/
dependencies/
errors.py
artifacts/

<!-- Controlled source page 19 -->

canonical_json.py
markdown_report.py
replay_bundle.py
schemas/
migrations/
cli/
tests/
unit/
integration/
conformance/
golden/
replay/
docs/
architecture/
adr/
api/
**RBE-REP-001** Dependency direction SHALL point inward: presentation and adapters may depend on
application and domain code; domain code SHALL NOT depend on outer layers.
**RBE-REP-002** Decision rules, board profiles and schemas SHALL be versioned resources with
checksums, not hard-coded conditionals scattered through handlers.
## 3.10 Architecture Review Findings for Sections 1–3
Review lens Result
Methodology alignment PASS — engine authority is subordinate to
RBM-001 and gaps fail closed.
Bias resistance PASS WITH ACTION — structural separation
and information barriers specified; final
incompatibility matrix must be locked in
RBM-001.
Codex implementability PASS — boundaries, containers, components
and dependency rules are explicit.
Determinism PASS — pure decision core and frozen
snapshot defined.
Auditability PASS — append-only, lineage and replay
requirements established.
Scope discipline PASS — research, solution generation and
build approval remain outside RBE.
Terminology ACTION — outcome vocabulary must be
synchronized with final RBM-001 before
release freeze.

<!-- Controlled source page 20 -->

Section freeze decision
Sections 1–3 are architecture-ready. They may be used by Codex to establish repository
boundaries, core principles, board-function separation and system context. Codex SHALL
NOT yet finalize database schema, API resources or decision tables until Sections 4–7 and
the RBM-001 terminology lock are complete.

<!-- Controlled source page 21 -->

Integration rule
These chapters are drafted as a controlled section release. After section review and
terminology lock, they SHALL be merged into the single authoritative RBE-001 Reference
Architecture without changing requirement identifiers or semantic meaning.
