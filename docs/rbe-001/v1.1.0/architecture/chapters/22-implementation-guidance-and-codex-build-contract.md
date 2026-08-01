---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 22
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 22. Implementation Guidance and Codex Build Contract

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 142 -->

## 22.1 Purpose
This chapter converts the reference architecture into explicit implementation constraints for human
engineers and coding agents. Its purpose is to minimize architectural invention during build,
prevent convenience-driven erosion of governance, and provide Codex with a bounded contract:
implement the approved architecture, expose ambiguity, and never manufacture substantive policy.
**RBE-IMP-001** Implementation SHALL conform to the frozen architecture and SHALL NOT infer new
decision authority, governance policy or evidence standards from UI requirements or example data.
**RBE-IMP-002** Codex and other coding agents SHALL stop and surface ambiguity when a requested
implementation could change substantive review meaning or violate a constitutional principle.
## 22.2 Order of Authority
44. Constitutional principles.
45. Frozen Review Board Methodology and governance rules.
46. Frozen RBE-001 Reference Architecture requirements.
47. Approved architecture decision records and schemas.
48. Approved implementation plan and acceptance criteria.
49. Code, tests and operational documentation.
A lower-ranked artefact cannot override a higher-ranked artefact. Example data, screenshots,
prototypes and convenience functions are non-authoritative unless explicitly incorporated into a
governed specification.
**RBE-IMP-010** When implementation artefacts conflict, the higher-order authority SHALL prevail and
the inconsistency SHALL be recorded for correction.
## 22.3 Repository and Module Structure
The repository should make architectural boundaries visible. Exact language and framework
choices may vary, but dependency direction and authority boundaries are normative.
Recommended top-level structure:
/apps
/api
/reviewer-web
/admin-web
/workers
/reporting
/integration
/automation
/domain
/cases
/reviews
/decisions
/evidence

<!-- Controlled source page 143 -->

/audit
/application
/commands
/queries
/policies
/contracts
/api
/events
/reports
/infrastructure
/persistence
/messaging
/identity
/observability
/tests
/unit
/component
/integration
/acceptance
/architecture
/docs
/adr
/runbooks
/schemas
**RBE-IMP-020** Domain modules SHALL NOT depend on UI frameworks, transport protocols, persistence
implementations, message brokers, AI SDKs or deployment tooling.
**RBE-IMP-021** Only designated infrastructure adapters SHALL access authoritative databases, object
stores, message brokers, key services or external integrations.
## 22.4 Domain Modeling Rules
- Use explicit domain types for case IDs, evidence IDs, reviewer IDs, methodology versions,
decision classes and hashes.
- Enforce invariants within aggregate or domain-service boundaries, not solely in controllers or UI
validation.
- Represent decisions and findings as immutable versioned records after finalization.
- Represent amendments, appeals and re-reviews as new governed records linked to history.
- Avoid generic status strings when a closed, versioned enumeration is required.
- Do not embed presentation labels as decision logic.
- Make actor, authority, causation and correlation explicit in substantive commands.
**RBE-IMP-030** A domain object SHALL NOT expose a mutation that can place it in a state prohibited by
the Chapter 8 state machine.

<!-- Controlled source page 144 -->

## 22.5 Command and Query Implementation
Commands express intent to change authoritative state and must be validated, authorized, executed
atomically and audited. Queries retrieve information and must apply classification and access policy
without producing side effects.
**RBE-IMP-040** Every substantive command handler SHALL perform schema validation, authentication
context validation, authorization, state/precondition validation, domain execution, durable
persistence and audit/outbox recording in a controlled transaction boundary.
**RBE-IMP-041** Command handlers SHALL be idempotent where client or infrastructure retry is possible.
**RBE-IMP-042** Queries SHALL NOT silently repair, finalize or otherwise mutate authoritative state.
## 22.6 Persistence Rules
- Use migrations; never mutate production schema manually as ordinary practice.
- Preserve immutable historical rows or version records for finalized governance data.
- Use optimistic concurrency or equivalent protection for competing substantive updates.
- Store evidence binaries outside ordinary relational rows while retaining authoritative metadata
and hashes.
- Publish events from a transactional outbox or equivalent atomic mechanism.
- Do not use caches as authoritative stores.
- Do not cascade-delete records required for provenance or reconstruction.
**RBE-IMP-050** Persistence code SHALL preserve the audit and provenance semantics defined in Chapters
10 and 14 even when the underlying technology changes.
## 22.7 API Rules
- Use versioned, explicit request and response schemas.
- Use stable identifiers rather than display names as references.
- Return a controlled error taxonomy.
- Propagate correlation and causation identifiers.
- Never trust client-supplied role, outcome, reviewer eligibility or audit metadata.
- Use pagination and bounded export for large collections.
- Generate API documentation from normative schemas where possible.
- Protect substantive endpoints with contextual authorization, not route-level role checks alone.
**RBE-IMP-060** The API SHALL NOT expose an endpoint whose purpose is to force a decision, rewrite final
history, bypass quorum or suppress required findings.
## 22.8 Event and Orchestration Rules
Events describe facts that have occurred. Commands request change. The two shall not be confused.
Orchestrators coordinate approved processes but may not invent substantive findings or decisions.
- Events are immutable, versioned and attributable.
- Consumers are idempotent and tolerate duplicate delivery.
- Ordering assumptions are explicit and limited to documented scopes.
- Poison messages enter controlled dead-letter handling with replay evidence.
- Orchestration state is observable and recoverable.
- External integration failure cannot corrupt authoritative case state.

<!-- Controlled source page 145 -->

- No workflow engine configuration may bypass domain validation.
**RBE-IMP-070** Every event representing a substantive state change SHALL originate from an
authoritative domain transaction and carry sufficient identifiers for provenance reconstruction.
## 22.9 Security Implementation Rules
- Deny by default.
- Use managed identity and short-lived credentials.
- Keep secrets outside code, images and ordinary configuration repositories.
- Validate issuer, audience, expiry and revocation of identity assertions.
- Apply authorization at the domain/application boundary.
- Record privileged actions and policy decisions without leaking protected content.
- Use approved cryptography and centralized key management.
- Quarantine and validate evidence files before authoritative ingestion.
**RBE-IMP-080** No code path, test helper or administrative utility SHALL introduce a permanent
universal bypass of authorization or governance policy.
## 22.10 AI and Automation Implementation Rules
AI modules are advisory adapters. They may summarize, classify, extract, suggest challenges or
identify possible inconsistencies, but their output is untrusted until validated and accepted by an
authorized human or deterministic control.
- Isolate AI SDKs and prompt logic from authoritative domain modules.
- Version model, provider, prompt, tool configuration and safety policy.
- Minimize and classify data sent to models.
- Treat evidence content as untrusted input capable of prompt injection.
- Require schema-constrained output where structured output is needed.
- Capture citations or source references for factual suggestions.
- Provide deterministic fallback and graceful unavailability.
- Never auto-convert a model suggestion into a finding, score or decision.
**RBE-IMP-090** AI output SHALL be stored as attributed advisory material distinct from reviewer-
authored and Board-authoritative records.
**RBE-IMP-091** An AI component SHALL NOT possess credentials capable of finalizing decisions, signing
reports, changing methodology or altering immutable evidence.
## 22.11 User Interface Implementation Rules
The UI shall support clarity, completeness and neutral review. It must not communicate that one
outcome is preferred or reward reviewers for approval or rejection volume.
- Present decision options with equivalent visual weight.
- Show evidence provenance and methodology version near substantive assessments.
- Require explicit reasoning and references before submission.
- Show unresolved conflicts, missing evidence and policy denials clearly.
- Prevent hidden defaults from selecting a substantive outcome.
- Distinguish saved draft, submitted assessment and finalized Board decision.
- Expose AI-generated material as AI-generated and unaccepted.

<!-- Controlled source page 146 -->

- Provide accessible navigation, labels and keyboard operation.
**RBE-IMP-100** The UI SHALL NOT preselect PASS, FAIL or any substantive outcome.
**RBE-IMP-101** Neutral presentation requirements SHALL be covered by acceptance and usability testing.
## 22.12 Coding Standards
- Use the project language formatter and static analysis in CI.
- Prefer explicit, readable code over clever abstraction.
- Keep functions and modules cohesive and bounded.
- Use structured logging with stable event names.
- Handle errors deliberately; do not swallow failures affecting integrity.
- Use typed schemas at external and domain boundaries.
- Document non-obvious governance rules with requirement IDs.
- No TODO may defer a mandatory control without a tracked issue and approved release decision.
**RBE-IMP-110** Code implementing substantive governance rules SHALL reference the relevant
requirement or approved decision record in tests or documentation.
## 22.13 Logging and Error Handling
Logs support operations and security but are not substitutes for the immutable audit model. Errors
must be observable and safe, with internal detail available to authorized operators and neutral
messages presented to users.
**RBE-IMP-120** The application SHALL NOT log raw secrets, unrestricted evidence content, authentication
tokens or unnecessary personal data.
**RBE-IMP-121** Failures after a substantive command is accepted SHALL resolve to a known durable state
and SHALL be recoverable without double application.
## 22.14 Migration and Compatibility Rules
- Database changes use forward-reviewed migrations and tested rollback or roll-forward strategy.
- Contract changes identify compatibility impact and supported versions.
- Historical records retain original methodology, policy, schema and template references.
- Data backfills are idempotent, attributable and verified.
- Migrations affecting hashes, signatures or provenance require independent validation.
- Production migration scripts are immutable release artefacts.
**RBE-IMP-130** A migration SHALL NOT reinterpret historical substantive data under a new methodology
or decision rule unless a governed re-review explicitly requires it.
## 22.15 Feature Delivery Sequence
50. Foundation: identifiers, identity context, policy enforcement and audit primitives.
51. Case intake and immutable evidence package handling.
52. Reviewer eligibility, conflicts and assignment.
53. Independent assessments and challenge workflow.
54. Decision assembly and finalization.
55. Report generation, signing and publication.
56. Appeal and re-review.

<!-- Controlled source page 147 -->

57. Integrations and advisory AI capabilities.
58. Advanced reporting, analytics and operational optimization.
This sequence prioritizes trustworthy governance over dashboards, demonstrations or artificial data
volume.
## 22.16 Pull Request and Review Requirements
- Linked issue, requirement and architecture context.
- Description of domain and data impact.
- Tests proving positive and negative behavior.
- Security and privacy considerations.
- Migration and rollback considerations.
- UI screenshots only as supplementary evidence, never as proof of domain correctness.
- Independent review for governance-significant changes.
- No self-approval for changes to authorization, decision, evidence or audit controls.
**RBE-IMP-140** Changes affecting constitutional controls, decision authority, evidence integrity or audit
semantics SHALL require review by both engineering and designated governance or architecture
authority.
## 22.17 Codex Task Packet
Every Codex task should contain enough context to prevent architectural invention. The minimum
task packet is:
- Task objective and non-goals.
- Applicable requirement IDs.
- Authoritative domain entities and states.
- Permitted modules to change.
- Forbidden changes and invariants.
- Input/output or contract schema.
- Acceptance tests, including negative cases.
- Data and security classification.
- Migration or compatibility expectations.
- Expected documentation and audit updates.
**RBE-IMP-150** Codex SHALL NOT be instructed with outcome-only prompts such as “make the test pass”
or “add an approve button” without the governing requirements and constraints.
## 22.18 Codex Prohibited Inferences
Codex must not infer Required response
That PASS is the preferred outcome Maintain neutral outcome model
That missing evidence may be replaced by
plausible synthetic evidence Stop and report insufficient source material
That administrators may override governance Reject and request architecture clarification
That AI output is authoritative Store as advisory only

<!-- Controlled source page 148 -->

Codex must not infer Required response
That a prototype screenshot defines policy Use frozen requirements and schemas
That historical records may be rewritten for
simplicity Implement versioned amendment or re-review
That a failed integrity test may be disabled Treat as a blocking defect
## 22.19 Definition of Done
- Implementation satisfies stated requirements and acceptance criteria.
- Positive, negative, authorization and failure tests pass.
- Architecture conformance tests pass.
- Contracts, schemas and migrations are versioned.
- Observability and audit events are present and validated.
- Security and privacy review is complete where applicable.
- Runbooks and operational impacts are updated.
- No unresolved blocker or critical defect remains.
- Generated artefacts are reproducible from source.
- Principal engineer and required governance reviewers approve the change.
## 22.20 Architecture Exception Process
An implementation may not silently diverge from the architecture. A proposed exception must
identify the requirement, reason, alternatives, risk, duration, compensating controls, owner and
closure date. Constitutional principles are not eligible for ordinary exception.
**RBE-IMP-160** Architecture exceptions SHALL be explicit, time-bounded, versioned and approved before
release; undocumented divergence is a defect.
## 22.21 Section Freeze Conditions
- Repository and dependency boundaries are approved.
- Command, persistence, event and AI implementation rules align with Chapters 12–17.
- Codex task packet and prohibited-inference rules are accepted.
- Definition of done and review authorities are named.
- Architecture-exception process is operational.
- No implementation instruction contradicts the constitutional principles.
