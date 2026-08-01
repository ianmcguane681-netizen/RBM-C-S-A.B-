---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 14
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 14. Persistence and Data Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 94 -->

## 14.1 Purpose
The persistence architecture protects the integrity, lineage and reproducibility of governed
decisions. It distinguishes authoritative transactional records, immutable artefacts, derived
projections, operational telemetry and temporary processing data.
**RBE-DAT-001** Each data item SHALL have a declared system of record, owner, classification, retention
rule and mutability rule.
**RBE-DAT-002** Derived data SHALL never silently replace or overwrite its authoritative source.
## 14.2 Storage Classes
Storage class Technology baseline Contents Mutability
Transactional store Relational database
Cases, assignments,
assessments, decisions and
audit metadata
Controlled by domain
commands
Immutable object store Versioned/WORM-capable
object storage
Evidence binaries, report
renderings and replay
bundles
Append-only/versioned
Projection store Relational read models or
search index
Queues, timelines and
search views Rebuildable
Message transport Durable broker/queue Integration events and
work items
Transient with durable
acknowledgment
Telemetry store Logs, metrics and traces Operational diagnostics Retention-limited
Quarantine store Isolated object storage Unverified uploads Temporary and restricted
## 14.3 Relational Aggregate Model
Aggregate root Key child records Consistency boundary
ReviewCase SubmissionVersion, case metadata
and lifecycle version
Case registration and high-level
lifecycle
EvidencePackage EvidenceItem, source metadata and
integrity records Evidence composition and lock
BoardSession
ReviewerAssignment,
AssessmentReport, Challenge and
clarification
Single governed review session
BoardDecision DecisionEvaluation, normalized
findings and rationale references Final decision assembly
AppealCase Grounds, admissibility result and
successor-session reference Appeal processing
ReviewReport Output variants, signatures and
publication records Report generation and release
## 14.4 Identifier Strategy
Identifiers must be opaque, globally unique and stable. Human-readable case references may
coexist with immutable internal identifiers but shall not encode sensitive meaning.

<!-- Controlled source page 95 -->

- UUIDv7 or equivalent sortable opaque identifiers for primary entities.
- Separate display reference such as RBE-2026-000123.
- No reuse of deleted, voided or abandoned identifiers.
- Explicit lineage identifiers for supersession and remand.
**RBE-DAT-010** Foreign-system identifiers SHALL be stored as namespaced external references, not used
as internal primary keys.
## 14.5 Immutability and Versioning
Published decisions, submitted assessments, locked evidence metadata, activated rule sets and audit
events are immutable. Corrections occur through successor records linked to the original. Mutable
workflow metadata uses optimistic version columns and complete audit coverage.
Record Mutation rule
SubmissionVersion Never edited after submission; successor version only
EvidenceItem after lock Binary and core metadata immutable; annotation through
linked record
AssessmentReport after submit Immutable; withdrawal or superseding assessment only
BoardDecision Immutable after ratification; successor decision through
governed session
AuditEvent Append-only; correction event references prior event
Projection Freely rebuildable from authoritative records
**RBE-DAT-020** Hard deletion of governed records SHALL be prohibited in normal application operation.
**RBE-DAT-021** Privacy-driven erasure or redaction SHALL preserve a verifiable tombstone and legal
basis without retaining prohibited content.
## 14.6 Evidence Integrity and Object Storage
Metadata Requirement
content_hash Strong approved digest over exact bytes
size_bytes Verified server-side
media_type Detected and declared values retained
storage_version Immutable object version identifier
classification Access and handling category
source_reference Origin and acquisition context
ingested_at Trusted server time
malware_status Scanner result and signature version
custody_events Ordered acquisition, transfer, lock and access events
**RBE-DAT-030** Every evidence read used in review SHALL verify object identity against authoritative
metadata.
**RBE-DAT-031** Replacement of an evidence object SHALL create a new EvidenceItem and shall never
preserve the prior identifier.

<!-- Controlled source page 96 -->

## 14.7 Audit Persistence
Audit events are persisted in an append-only logical ledger in the same transaction as the governed
change. A hash chain or signed batch manifest provides tamper evidence. Audit storage may be
replicated into a separate retention domain, but the transactional record remains the publication
source for event identity and ordering.
**RBE-DAT-040** The governed write and its primary audit event SHALL commit or roll back together.
**RBE-DAT-041** Audit sequence allocation SHALL be deterministic within an aggregate or ledger partition.
## 14.8 Data Classification
Class Examples Baseline handling
Public Published decision notice approved
for public release Read-only public access
Internal Operational status and non-sensitive
metadata Authenticated workforce access
Restricted Reviewer identities, assessments and
commercial analysis Case-scoped need-to-know
Highly Restricted Personal data, privileged evidence
and security material
Explicit grant, enhanced logging and
export control
System Secret Credentials, signing keys and
recovery material
Dedicated secret/key management;
never in database fields or reports
## 14.9 Retention, Archival and Legal Hold
Retention is policy-driven by artefact class, jurisdiction, contractual obligations and evidential value.
Expiration jobs create auditable disposition records. Legal hold overrides normal deletion and must
itself be authorized, scoped and reviewed.
Data family Default architectural posture
Final decisions and provenance Long-term or permanent retention subject to policy
Evidence Retention aligned with case, appeal and legal obligations
Draft working data Shorter retention after closure
Authentication and security telemetry Time-bound security retention
Quarantine uploads Rapid disposal after rejection or expiry
Backups Encrypted, rotation-based and disposition-aware
**RBE-DAT-050** Retention configuration SHALL be versioned and applied by record classification and
effective policy version.
**RBE-DAT-051** Archive retrieval SHALL preserve integrity verification and access authorization.
## 14.10 Backup, Restore and Disaster Recovery
- Point-in-time recovery for the transactional store.
- Cross-zone and, where required, cross-region replication.
- Versioned immutable evidence objects.
- Encrypted backups with independently controlled keys.
- Documented recovery point and recovery time objectives.

<!-- Controlled source page 97 -->

- Regular restoration tests that include audit-chain and object-hash verification.
- Recovery procedures that prevent duplicate event publication.
**RBE-DAT-060** A restoration SHALL not be declared successful until authoritative data, evidence
integrity and audit continuity are verified together.
## 14.11 Migrations and Schema Evolution
Schema migrations are reviewed, ordered, repeatable and reversible where technically safe.
Destructive changes use expand-migrate-contract sequencing and verified backups. Historical
semantics are preserved through explicit version fields and translation layers.
**RBE-DAT-070** Production migrations SHALL be automated, checksum-verified and recorded as
deployment evidence.
**RBE-DAT-071** A migration SHALL NOT rewrite historical decision meaning to conform to a newer
taxonomy.
## 14.12 Data Quality Controls
Control Example
Referential integrity Every decision references an existing session and rule set
Check constraints Outcome and terminal state combinations
Unique constraints One active assignment per reviewer/function/session
Completeness rules Published report has required signatures and hashes
Reconciliation Object inventory against evidence metadata
Replay validation Decision inputs reproduce stored evaluation result
## 14.13 Codex Implementation Contract
- Use database constraints to reinforce, not replace, domain invariants.
- Keep migrations in source control and test them against realistic copies.
- Store timestamps in UTC with clear precision and trusted server generation.
- Use explicit transaction boundaries for governed commands.
- Implement an outbox table in the same database transaction as aggregate changes.
- Never cascade-delete governed records.
- Create reconciliation jobs for database/object-store consistency.
- Provide deterministic fixtures and migration tests for historical versions.
