---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 10
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 10. Audit, Traceability and Provenance

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 70 -->

## 10.1 Objective
The audit architecture must make every material decision reconstructable without relying on
memory, trust in a single operator or mutable application state. Traceability connects the final
decision to the exact evidence, methodology, rules, reviewers, findings, challenges and signatures
that produced it.
**RBE-AUD-001** Every material action SHALL produce an immutable, attributable audit event.
**RBE-AUD-002** The system SHALL support independent reconstruction of any published decision from
retained artefacts and versioned rules.
**RBE-AUD-003** Audit data SHALL be designed as evidence, not as diagnostic logging.
## 10.2 Audit Event Model
Field Description
event_id Globally unique immutable identifier.
event_type Versioned enumerated event name.
occurred_at Trusted UTC timestamp.
recorded_at Persistence timestamp, separately retained.
actor_id Human or service principal.
actor_role Effective role at action time.
case_id / session_id Scope of action.
state_before / state_after Lifecycle context where applicable.
object_type / object_id Affected domain object.
action Created, viewed, sealed, transitioned, signed,
exported, etc.
reason_code Structured reason or policy basis.
policy_version Authorization and governance policy version.
payload_digest Hash of canonical event payload.
previous_event_digest Link to prior event in chain or partition.
correlation_id Groups related workflow events.
source_context Client, service, region and request metadata.
signature / attestation Optional cryptographic or organizational
attestation.

<!-- Controlled source page 71 -->

## 10.3 Event Taxonomy
Family Examples
Identity and access login, MFA challenge, role grant, access denial,
break-glass use
Case lifecycle submission sealed, evidence locked, state
transitioned, case voided
Evidence artifact added, hash verified, disclosure,
amendment proposed
Assignment assigned, conflict declared, assignment
accepted, reviewer removed
Assessment draft created, finding added, assessment
sealed, signature verified
Challenge challenge issued, answer submitted,
disposition recorded
Decision rules executed, candidate generated, validation
passed, decision signed
Publication report rendered, package verified, recipient
release, correction notice
Appeal appeal filed, eligibility determined, panel
constituted, outcome issued
Administration policy changed, key rotated, retention action,
restore test
Integrity digest mismatch, replay failure, unauthorized
mutation attempt
**RBE-AUD-020** Event types SHALL be versioned and backward-readable.
**RBE-AUD-021** Free-text operational logs SHALL NOT substitute for required audit events.
## 10.4 Evidence Provenance and Chain of Custody
Provenance element Required record
Origin Source, issuer, retrieval method and date.
Authenticity Signature, certificate, authoritative URL or
verification method where available.
Independence Relationship between source and affected
parties.
Transformation Every extraction, normalization, redaction or
format conversion.

<!-- Controlled source page 72 -->

Provenance element Required record
Custody Who or what handled the artefact and when.
Integrity Original and transformed content digests.
Scope use Claims, findings and assessments that cite the
artefact.
Exclusion Why evidence was rejected, superseded or
deemed out of scope.
**RBE-AUD-030** The original artefact SHALL be retained whenever legally and technically permissible.
**RBE-AUD-031** A transformed artefact SHALL retain a verifiable link to its source artefact and
transformation procedure.
## 10.5 Decision Provenance Graph
Decision provenance is represented as a directed graph, not a single narrative paragraph. The graph
makes each decision element traceable through intermediate findings and assessments to
underlying evidence and governing rules.
Node type Must link to
Decision Decision rule execution, governance
validation, signatures and report package.
Decision basis Accepted findings, blocking findings,
uncertainty and rule clauses.
Finding Assessment, evidence references, methodology
clauses and challenge dispositions.
Assessment Reviewer identity, assignment, scope, artefact
set and attestation.
Challenge disposition Challenge, response, evidence and reviewer
ruling.
Evidence item Source provenance, content digest and
evidence package.
Methodology clause Pinned methodology version and exact clause
identifier.
Rule execution Ruleset version, inputs, outputs and
deterministic trace.
**RBE-AUD-040** No published decision basis SHALL exist without at least one trace path to a governing
rule and supporting assessment or evidence record.

<!-- Controlled source page 73 -->

## 10.6 Cryptographic Integrity Strategy
Control Architecture requirement
Content hashing Use approved collision-resistant digest over
canonical bytes.
Canonicalization Structured objects serialized deterministically
before hashing.
Package digest Merkle-style or manifest digest covering all
decision artefacts.
Event chaining Each audit event links to prior digest within an
ordered partition.
Digital signatures Signed decisions and sealed assessments bind
identity, content digest and timestamp.
Key management Central managed keys, rotation, revocation and
audit.
Timestamping Trusted server time; external timestamp
authority considered for high-assurance
releases.
Verification tooling Independent command or service validates
package without production database
mutation.
**RBE-AUD-050** Cryptographic controls SHALL detect alteration; they SHALL NOT be represented as
proving truth of the underlying content.
**RBE-AUD-051** Algorithm identifiers and key versions SHALL be stored with each signature or digest
record.
## 10.7 Immutability and Corrections
Immutability does not mean errors can never be addressed. It means corrections are additive,
explicit and lineage-preserving.
Scenario Required treatment
Typographical report defect Issue corrected report version linked to same
decision; preserve prior output.
Material decision defect Use appeal, superseding decision or void
process as applicable.
Incorrect metadata Append correction event and successor
metadata record.
Compromised signature key Revoke key, record incident, re-attest only
through governed process.

<!-- Controlled source page 74 -->

Scenario Required treatment
Evidence corruption Block use, restore verified immutable copy and
record recovery.
Policy bug Version policy, replay affected cases and
initiate governed remediation.
**RBE-AUD-060** No correction process SHALL erase the existence of the original record.
## 10.8 Reproducibility and Decision Replay
Replay input Requirement
Evidence package Exact locked manifest and verified digests.
Submission assertions Exact version reviewed.
Methodology Pinned identifier, version and digest.
Ruleset Pinned executable or declarative version and
digest.
Assessments Sealed structured assessments and signatures.
Challenge record Complete challenge and disposition set.
Configuration Relevant policy and taxonomy versions.
Replay engine Compatible deterministic implementation.
Expected output Decision class, finding set references and
decision digest.
**RBE-AUD-070** Decision replay SHALL be executable without editing historical records.
**RBE-AUD-071** A replay mismatch SHALL create a blocking integrity incident.
**RBE-AUD-072** The platform SHALL distinguish deterministic decision replay from human re-review.
## 10.9 Time and Ordering
- Use UTC for authoritative timestamps.
- Retain local display timezone separately where useful.
- Record occurred_at and recorded_at to detect delayed ingestion.
- Use monotonic sequence numbers within event partitions.
- Synchronize infrastructure clocks and alert on drift.
- Do not infer legal or workflow ordering solely from client-supplied time.
## 10.10 Retention, Archive and Legal Hold
Record class Minimum architectural treatment
Published decision package Long-term immutable retention.

<!-- Controlled source page 75 -->

Record class Minimum architectural treatment
Evidence package Retain according to methodology, law and
source rights.
Audit events At least as long as related decision artefacts.
Identity and access events Security retention aligned to investigation
needs.
Draft content Retain only where governance or recovery
requires.
Secrets and credentials Never embed in retained case artefacts.
Legal hold Suspends deletion without altering original
retention metadata.
Archive package Self-describing manifest, checksums, schemas
and verification instructions.
**RBE-AUD-090** Retention deletion SHALL be a governed, logged and independently authorized action.
**RBE-AUD-091** An archive SHALL remain verifiable without dependence on the live application UI.
## 10.11 Audit Query and Export
- Chronological case timeline
- All access to a named artefact
- Decision-to-evidence trace report
- Reviewer actions and role state at action time
- Policy and methodology versions used
- All failed or denied transition attempts
- All privileged and break-glass events
- Replay result and integrity status
- Appeal lineage and supersession graph
**RBE-AUD-100** Audit export SHALL preserve identifiers, timestamps, digests and schema version.
**RBE-AUD-101** Exports SHALL be access-controlled and themselves audited.
## 10.12 Privacy and Data Minimization
Auditability does not justify indiscriminate retention of personal or sensitive data. Events should
identify actors and actions while avoiding unnecessary payload duplication.
**RBE-AUD-110** Audit records SHALL reference protected content by identifier and digest rather than
duplicating full sensitive payloads unless required.
**RBE-AUD-111** Redaction or pseudonymization SHALL preserve evidentiary integrity and lineage.
## 10.13 Codex Implementation Contract
- Model audit events as append-only domain records.
- Use canonical serialization before hashing.

<!-- Controlled source page 76 -->

- Create verification libraries independent of UI.
- Separate operational telemetry from governance audit records.
- Test event-chain tampering and replay mismatch detection.
- Make all exports schema-versioned and machine-readable.
- Provide decision provenance graph traversal.
- Preserve old schemas and migration readers.
- Never expose secret values in audit payloads.
