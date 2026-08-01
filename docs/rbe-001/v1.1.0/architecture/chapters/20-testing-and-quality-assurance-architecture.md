---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 20
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 20. Testing and Quality Assurance Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 128 -->

## 20.1 Purpose
This chapter defines the verification system required to establish that the Review Board Engine
behaves as specified, preserves impartiality, and produces decisions that are traceable, reproducible
and resistant to unauthorized influence. Testing is not limited to software correctness. It must also
demonstrate governance correctness: the engine must reject actions that would violate
methodology, evidence integrity, reviewer independence or decision authority.
**RBE-TST-001** The release process SHALL provide objective evidence that functional, security,
governance, traceability and operational requirements have been verified before production
promotion.
**RBE-TST-002** A test result SHALL NOT be considered sufficient when it proves only that a user interface
path works while the authoritative domain rule remains unverified.
## 20.2 Quality Objectives
- Correctness: authorized actions produce the specified state and unauthorized actions are
rejected.
- Determinism: repeated evaluation of the same governed inputs produces compatible machine
decisions and explainable variation where human judgement is permitted.
- Traceability: every requirement can be linked to one or more tests and every release can be
linked to its executed evidence.
- Isolation: failures in integrations, automation or presentation do not silently alter authoritative
case state.
- Reproducibility: a historical release and its test environment can be reconstructed sufficiently to
reproduce critical decisions and defects.
- Usability without persuasion: interfaces present evidence and findings neutrally without
nudging reviewers toward a desired outcome.
- Resilience: degraded conditions preserve integrity and fail safely rather than bypassing controls.
## 20.3 Verification Layers
Layer Primary purpose Required evidence
Static verification Detect defects before
execution
Lint, type checks, schema
checks, dependency policy,
architecture tests
Unit verification Prove local domain rules
Deterministic unit tests,
mutation score where
valuable, boundary cases
Component verification
Prove service behavior with
real adapters or faithful
substitutes
Contract tests, persistence
tests, authorization tests
Integration verification Prove interactions across
services and infrastructure
Broker, database, object store,
identity and signing

<!-- Controlled source page 129 -->

Layer Primary purpose Required evidence
integration tests
End-to-end verification Prove governed user journeys
Recorded scenarios from
intake through report
publication and appeal
Operational verification Prove recovery and support
procedures
Backup restore, failover,
rollback, incident and access-
revocation exercises
Governance verification Prove constitutional and
methodological constraints
Negative tests for bias,
override, conflicts, quorum
and evidence substitution
## 20.4 Requirements Traceability
The quality system shall maintain a bidirectional traceability model. Every normative requirement
must reference its verification method, and every automated or manual test must identify the
requirement or risk it verifies. Orphan requirements and orphan tests are release defects.
**RBE-TST-010** Every SHALL requirement in the frozen architecture SHALL have a verification status of
automated, manually verified, deferred with approved rationale, or not applicable with approved
rationale.
**RBE-TST-011** The release candidate SHALL include a machine-readable requirements traceability
matrix identifying requirement ID, test ID, test type, execution result, environment, build identifier
and evidence location.
**RBE-TST-012** A failed constitutional, evidence-integrity, authorization, audit or separation-of-duties test
SHALL block release regardless of aggregate pass rate.
## 20.5 Domain and State-Machine Testing
The state machine defined in Chapter 8 is authoritative. Tests must prove both allowed transitions
and prohibited transitions. Property-based and model-based techniques should be used for
transition sequences that are difficult to enumerate manually.
- Every state has verified entry and exit invariants.
- Every transition is tested for correct authority, preconditions, side effects and audit events.
- Invalid transitions fail atomically and leave no partial authoritative change.
- Retries and duplicate commands do not create duplicate assignments, findings, decisions or
reports.
- Appeal and re-review create new governed records rather than rewriting historical decisions.
- Concurrency tests cover competing reviewer submissions, evidence locking and decision
finalization.
**RBE-TST-020** The test suite SHALL prove that no command can move a case directly to a final outcome
while bypassing mandatory review or challenge stages.

<!-- Controlled source page 130 -->

**RBE-TST-021** State-machine tests SHALL include randomized valid and invalid command sequences and
SHALL verify invariants after every operation.
## 20.6 Decision and Reasoning Verification
Decision tests must verify the decision framework rather than merely assert status labels. Test
fixtures shall include evidence packages that justify each permitted outcome and adversarial
packages that appear commercially attractive but fail methodological or evidential requirements.
- PASS cannot be produced when a mandatory methodological control fails.
- Commercial value cannot compensate for insufficient evidence.
- INSUFFICIENT EVIDENCE is available without penalty or artificial escalation pressure.
- FAIL requires explicit, traceable reasoning rather than a bare status.
- PASS WITH FINDINGS preserves unresolved findings and follow-up obligations.
- DEFER records the unresolved question and the evidence or action required to continue.
- Decision assembly never invents a finding absent from authoritative reviewer assessments.
**RBE-TST-030** Golden decision fixtures SHALL be reviewed by governance owners and SHALL represent
all decision classes, material boundary conditions and known anti-patterns.
**RBE-TST-031** Changes to decision rules SHALL require regression execution against all golden fixtures
and explicit review of every changed result.
## 20.7 Authorization and Separation-of-Duties Testing
Authorization tests shall operate at the authoritative command boundary. They must test actor
identity, role, assignment, conflict status, case state, object classification and contextual restrictions
in combination.
Scenario Expected behavior
Unassigned reviewer submits assessment Reject and audit denial
Conflicted reviewer accesses restricted case Reject; record conflict control event
Administrator attempts substantive decision Reject regardless of technical privilege
Reviewer attempts to approve own assignment
change Reject under separation of duties
Chair finalizes without quorum Reject and preserve pending state
AI service attempts to issue decision Reject; AI has no substantive authority
Expired elevated privilege performs export Reject and require new authorization
**RBE-TST-040** Authorization regression tests SHALL execute against every mutating command and every
protected read path.
**RBE-TST-041** The quality gate SHALL include explicit tests proving that generic administrative access
cannot override substantive governance rules.
## 20.8 Evidence Integrity and Provenance Testing
- Hash verification on ingestion, retrieval, export and archival restore.

<!-- Controlled source page 131 -->

- Chain-of-custody preservation through transformations, redactions and derived artefacts.
- Immutability of evidence versions used by finalized reviews.
- Failure on missing, substituted or mismatched evidence identifiers.
- Reconstruction of a decision report from authoritative records and versioned templates.
- Independent validation of signed reports and provenance manifests.
- Detection of tampered audit segments or altered report packages.
**RBE-TST-050** The test suite SHALL prove that changing an evidence object after evidence lock cannot
silently change the evidence set associated with a review.
**RBE-TST-051** A full provenance replay test SHALL reconstruct at least one representative case from
audit events, governed records and immutable artefacts in every release candidate environment.
## 20.9 API, Contract and Schema Testing
Interfaces defined in Chapter 13 and event contracts defined in Chapter 15 shall be versioned and
tested independently of implementation language. Consumer-driven contract tests may supplement
but shall not replace provider conformance tests against the normative schemas.
- Backward-compatible schema evolution for supported versions.
- Rejection of unknown or invalid substantive fields where permissive parsing would be unsafe.
- Idempotency-key behavior and duplicate-request replay.
- Correlation, causation and actor metadata propagation.
- Consistent error taxonomy without disclosure of protected content.
- Event ordering and outbox publication guarantees.
- Compatibility tests for report manifests and machine-readable decision outputs.
**RBE-TST-060** Breaking contract changes SHALL require a new version, migration plan and coexistence
period or explicit coordinated cutover approval.
## 20.10 Security Testing
Security testing shall implement the assurance requirements of Chapter 16 and include automated
and human-led techniques. Passing scanners alone is insufficient.
- Static application security testing and secret detection.
- Dependency, container and infrastructure vulnerability scanning.
- Dynamic and API security testing in an isolated environment.
- Penetration testing before initial production and after material boundary changes.
- Abuse-case testing for privileged access, evidence export, report signing and break-glass use.
- Supply-chain verification from source commit to deployed artefact.
- Remediation verification and regression tests for security defects.
**RBE-TST-070** Critical security findings affecting evidence integrity, decision authority, authentication,
authorization or signing SHALL block production release until remediated or formally accepted by
designated security and governance authorities.
## 20.11 AI and Automation Testing
AI-assisted capabilities are non-authoritative. Testing must demonstrate that model output is
bounded, attributable and incapable of becoming a decision without the required human and
domain controls.

<!-- Controlled source page 132 -->

- Prompt-injection and hostile-evidence tests.
- Hallucination and unsupported-citation detection.
- Data-minimization and prohibited-data leakage tests.
- Model and prompt version traceability.
- Deterministic fallback when the model is unavailable or output fails validation.
- Human-review enforcement for AI-produced summaries, suggested challenges and
classifications.
- Bias evaluation focused on whether presentation or ranking changes reviewer treatment of
equivalent evidence.
**RBE-TST-080** No AI test fixture SHALL be accepted as proving decision correctness unless the
authoritative non-AI decision rules and human approvals are also verified.
**RBE-TST-081** The system SHALL test that AI output cannot directly mutate evidence, findings, reviewer
assessments, decisions or signed reports.
## 20.12 Performance, Reliability and Recovery Testing
Performance tests shall use representative case sizes, evidence volumes, concurrent reviewers and
report-generation workloads. Reliability tests must verify safe behavior under partial failure.
Test class Minimum concern
Load Expected concurrent review and evidence-
access demand
Stress Behavior beyond planned capacity and
controlled rejection
Soak Resource leakage and queue accumulation
over extended operation
Chaos/fault injection Database, broker, object store, identity and
network failure
Recovery Restore, point-in-time recovery and
provenance validation
Deployment Rolling or blue-green promotion without
governance inconsistency
**RBE-TST-090** Recovery testing SHALL verify not only service availability but also consistency of case
state, evidence references, audit history and signed outputs.
## 20.13 Test Data Governance
Test data shall be synthetic by default. Production evidence or personal data may be used only
under explicit approval, minimization, isolation and destruction controls. Synthetic fixtures must
still preserve realistic structural complexity.
**RBE-TST-100** Production secrets and unrestricted production evidence SHALL NOT be copied into test
environments.

<!-- Controlled source page 133 -->

**RBE-TST-101** Test fixtures used as normative golden cases SHALL be version-controlled, reviewed and
immutable within a released test baseline.
## 20.14 Environments and Test Independence
- Unit and component tests must run without dependence on shared mutable environments.
- Integration environments shall be reproducible from infrastructure and configuration
definitions.
- Acceptance tests shall execute against the same build artefact intended for promotion.
- Environment-specific configuration shall be injected and separately validated.
- Test execution identities shall have no unrecorded production privilege.
- Clock, randomness and external dependencies shall be controllable where determinism is
required.
**RBE-TST-110** A release SHALL NOT be certified using a build artefact different from the artefact
promoted to production.
## 20.15 Defect Classification and Release Gates
Severity Definition Release effect
Blocker
Constitutional breach,
decision corruption, evidence
loss, audit compromise or
unauthorized substantive
action
Release prohibited
Critical
Material security, availability
or data-integrity failure with
no acceptable control
Release prohibited
Major
Significant function fails or
governance assurance
incomplete
Requires remediation or
approved deferral
Minor
Limited impact with safe
workaround and no
governance compromise
May proceed with tracked
remediation
Observation
Improvement or risk not
presently causing non-
conformance
Record and prioritize
**RBE-TST-120** Release approval SHALL be evidence-based and SHALL identify all open defects, risk
acceptances, deferred tests and accountable owners.
## 20.16 Quality Evidence Package
- Build and source identifiers.
- Software bill of materials and attestations.
- Requirements traceability matrix.

<!-- Controlled source page 134 -->

- Automated test results and coverage summaries.
- Manual test records and reviewer approvals.
- Security assessment and vulnerability status.
- Performance and recovery results.
- Known defects, exceptions and risk acceptances.
- Architecture-conformance report.
- Final release recommendation with independent sign-off.
**RBE-TST-130** Quality evidence SHALL be retained as a versioned release artefact and SHALL remain
independently verifiable after the release is superseded.
## 20.17 Architecture Conformance Tests
Architecture rules that can be expressed mechanically should be enforced mechanically. Examples
include dependency direction, forbidden module imports, access to authoritative persistence, event
publication through the outbox, use of approved identity libraries and prohibition of AI modules
from decision command handlers.
**RBE-TST-140** The CI pipeline SHALL fail when code violates mechanically enforceable architecture
boundaries.
**RBE-TST-141** Architecture tests SHALL be maintained as production code and reviewed whenever
module boundaries or service responsibilities change.
## 20.18 Chapter 20 Codex Build Contract
- Codex may generate tests, fixtures and quality tooling only within frozen architectural
boundaries.
- Codex shall not weaken assertions merely to make a pipeline pass.
- Codex shall not replace negative governance tests with mocked success paths.
- Codex shall preserve requirement IDs in test names or metadata.
- Codex shall surface ambiguous requirements rather than infer an outcome-favouring
interpretation.
- Codex-generated test data shall contain no real secrets or personal data.
- Any proposed removal of a test protecting a constitutional principle requires explicit human
architecture approval.
**RBE-TST-150** Automated coding agents SHALL treat failing governance and integrity tests as evidence of
a defect, not as obstacles to be bypassed.
## 20.19 Section Freeze Conditions
- The requirements traceability model is approved.
- All decision classes and state transitions have normative verification coverage.
- Separation-of-duties and AI-boundary negative tests are defined.
- Release blockers and risk-acceptance authorities are named.
- Recovery and provenance replay tests are specified.
- The Codex build contract is accepted by architecture and engineering owners.
