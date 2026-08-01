---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 16
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 16. Security Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 103 -->

## 16.1 Purpose
This chapter defines the security architecture required to preserve the integrity, confidentiality,
availability and independence of the Review Board Engine. Security is not treated as a perimeter
concern. It is part of the governance model because any unauthorized change to evidence, reviewer
assignments, findings, methodology versions, decision rules or reports can invalidate the legitimacy
of the Board itself.
**RBE-SEC-001** Security controls SHALL protect evidential integrity, reviewer independence, decision
provenance and reproducibility as first-class protection objectives.
**RBE-SEC-002** No security exception SHALL create a capability to force, suppress or rewrite a
substantive review outcome.
## 16.2 Security Objectives
- Prevent unauthorized access to cases, evidence and review material.
- Prevent unauthorized or untraceable modification of governed records.
- Preserve the separation of duties established in Chapter 9.
- Ensure that privileged access is attributable, time-bounded and independently reviewable.
- Ensure that compromise of a non-authoritative component cannot silently alter authoritative
state.
- Maintain the ability to reconstruct security-relevant events during an investigation.
- Preserve availability without bypassing governance controls during degraded operation.
## 16.3 Threat Model
The baseline threat model includes malicious insiders, compromised reviewer accounts,
compromised administrator accounts, supply-chain compromise, external attackers, accidental data
leakage, privilege escalation, evidence tampering, report substitution, malicious automation and
unauthorized model-generated content. The architecture assumes that any single identity, client
device, application node or integration may fail or become compromised.
Threat Primary control family Governance consequence if
uncontrolled
Reviewer account takeover
Phishing-resistant MFA,
conditional access, session
controls
Fraudulent findings,
disclosure of protected
evidence or manipulation of
reviewer work
Administrator misuse
Just-in-time privilege, dual
authorization, immutable
audit
Circumvention of assignment,
state or retention controls
Evidence tampering Content hashing, immutable
storage, chain of custody
Invalid decision basis and loss
of reproducibility
Report substitution Digital signing, artefact hash Public or internal reliance on

<!-- Controlled source page 104 -->

Threat Primary control family Governance consequence if
uncontrolled
binding, trusted publication a false decision artefact
API abuse
Strong authentication,
authorization, rate limits,
command validation
Unauthorized transitions or
denial of service
Supply-chain compromise
Pinned dependencies, SBOM,
signed builds, provenance
verification
Malicious code inside trusted
deployment path
AI prompt or data attack Content isolation, validation,
model boundary controls
Manipulated summaries,
disclosure or unsafe
recommendations
## 16.4 Identity and Authentication
Human and workload identities shall be centrally governed. Authentication proves identity; it does
not confer permission. Authorization remains contextual to role, case assignment, conflict status,
review stage and action type.
- Phishing-resistant multi-factor authentication for privileged and substantive reviewer roles.
- Short-lived access tokens with explicit audience, issuer and scope validation.
- Workload identity for services; no long-lived embedded service passwords.
- Device and session risk evaluation for privileged operations.
- Step-up authentication for report signing, role elevation, evidence export and emergency actions.
- Immediate revocation on separation, role withdrawal or confirmed compromise.
**RBE-SEC-010** The system SHALL reject authentication assertions that cannot be validated against a
trusted issuer, intended audience and current revocation state.
**RBE-SEC-011** Privileged human access SHALL require phishing-resistant multi-factor authentication
and SHALL be re-authenticated for high-impact operations.
**RBE-SEC-012** Service-to-service authentication SHALL use managed workload identity or equivalently
short-lived credentials.
## 16.5 Authorization and Policy Enforcement
Authorization shall be evaluated at the domain boundary using deny-by-default policy. UI
concealment is not authorization. Every command must be checked against actor identity, role, case
assignment, conflict declarations, current state, object classification and separation-of-duties
constraints.
Authorization input Example Required effect
Actor identity Reviewer, chair, auditor,
workload
Establish accountable
principal
Role and capability Evidence reviewer, report Limit permitted command

<!-- Controlled source page 105 -->

Authorization input Example Required effect
publisher family
Case relationship Assigned, unassigned, recused Enforce case-scoped authority
State and stage Evidence review open,
decision final
Prevent invalid timing of
action
Conflict status Declared conflict, pending
determination
Suspend or prohibit
substantive action
Resource classification Restricted evidence, internal
report
Apply access and export
controls
Separation-of-duties rule Author cannot approve own
report Require independent actor
**RBE-SEC-020** Every mutating command SHALL be authorized within the authoritative application or
domain boundary immediately before state change.
**RBE-SEC-021** Authorization decisions SHALL be logged with actor, policy version, target, result and
correlation identifiers without exposing protected content.
**RBE-SEC-022** No generic administrator role SHALL bypass case-state, conflict, quorum or separation-of-
duties controls.
## 16.6 Privileged Access Management
Privileged access must be exceptional rather than ambient. Standing production privileges increase
the likelihood of invisible governance failure. Administrative access therefore requires time-bound
elevation, reason capture, approval where appropriate and enhanced monitoring.
- Just-in-time elevation with automatic expiry.
- Dual authorization for destructive, retention-affecting or cryptographic-key operations.
- Break-glass accounts held outside normal identity paths and tested under controlled conditions.
- Privileged session recording or equivalent command-level evidence for high-risk administration.
- Quarterly access recertification and immediate review after organizational change.
- No shared administrative credentials.
**RBE-SEC-030** Emergency access SHALL NOT permit alteration of finalized decisions, signed reports or
immutable audit history.
**RBE-SEC-031** Use of break-glass access SHALL trigger an independent post-event review and security
incident record.
## 16.7 Data Classification and Handling
Classification Examples Minimum handling
Public Published decision notice Integrity protection and
publication provenance
Internal Operational dashboards, non- Authenticated access and

<!-- Controlled source page 106 -->

Classification Examples Minimum handling
sensitive metadata ordinary logging controls
Confidential Reviewer notes, internal
findings, commercial analysis
Need-to-know access,
encryption and controlled
export
Restricted
Personal data, legally sensitive
evidence, protected source
material
Case-scoped access, enhanced
monitoring, explicit retention
and export approval
**RBE-SEC-040** Every evidence object and report artefact SHALL carry an explicit classification and
handling policy.
**RBE-SEC-041** Data classification SHALL propagate to derived artefacts, exports, search indexes and AI-
processing requests.
## 16.8 Encryption and Key Management
- Encryption in transit using current approved protocols.
- Encryption at rest for databases, object stores, queues, backups and search indexes.
- Application-level envelope encryption for the most sensitive evidence classes where required.
- Centralized key management with role separation between data operators and key
administrators.
- Rotation, revocation and recovery procedures tested before production use.
- Key usage logging bound to workload identity and purpose.
**RBE-SEC-050** Cryptographic keys SHALL be managed outside application source code, container images
and ordinary configuration repositories.
**RBE-SEC-051** Evidence and signed report artefacts SHALL retain verifiable content hashes independent
of the storage provider.
## 16.9 Secrets Management
Secrets include API credentials, signing material, database credentials, integration tokens and
recovery material. They shall be injected at runtime from an approved secrets manager and never
stored in source control, build logs, test fixtures or report artefacts.
**RBE-SEC-060** Secret access SHALL be least-privilege, attributable, short-lived where supported and
auditable.
**RBE-SEC-061** Production secrets SHALL NOT be copied into lower environments.
## 16.10 Application and API Security
- Input validation against explicit command schemas.
- Output encoding and safe content rendering.
- Protection against injection, path traversal, unsafe deserialization and server-side request
forgery.
- Idempotency and replay protection for substantive commands.
- Rate limiting appropriate to actor, endpoint and sensitivity.

<!-- Controlled source page 107 -->

- File-type, size, malware and content-disarm controls for evidence ingestion.
- Secure error handling that does not disclose secrets, internal topology or protected evidence.
**RBE-SEC-070** Evidence files SHALL be quarantined until validation, integrity hashing and malware
scanning complete successfully.
**RBE-SEC-071** Security validation failure SHALL prevent authoritative ingestion and SHALL create a
traceable rejection record.
## 16.11 Network and Infrastructure Security
The system shall separate public ingress, application, data, administrative and build planes. Direct
access to authoritative data services from user networks is prohibited. Administrative access shall
occur through controlled, strongly authenticated paths.
**RBE-SEC-080** Authoritative databases, object stores and brokers SHALL NOT be directly exposed to the
public internet.
**RBE-SEC-081** Network policy SHALL restrict service communication to documented flows defined by the
architecture.
## 16.12 Software Supply-Chain Security
- Maintain a software bill of materials for each release.
- Pin and verify dependency versions.
- Scan source, dependencies, containers and infrastructure definitions.
- Sign build artefacts and verify signatures before deployment.
- Use isolated build workers with minimal credentials.
- Preserve build provenance from source commit to deployed image.
- Require review for changes to security-sensitive dependencies and build workflows.
**RBE-SEC-090** Production deployments SHALL consume only artefacts produced by the approved,
attestable build pipeline.
**RBE-SEC-091** A critical unresolved supply-chain vulnerability SHALL block release unless a formally
approved, time-bounded risk exception exists.
## 16.13 Security Logging, Detection and Response
Security telemetry shall complement, not replace, the immutable governance audit trail. Detection
must cover authentication anomalies, privilege elevation, evidence access, export activity, policy
denial spikes, integrity failures, signing failures and unusual administrative behaviour.
Security event Minimum response
Repeated failed privileged authentication Risk escalation, possible session block and alert
Unexpected evidence hash mismatch Immediate quarantine, case block and incident
declaration
Unauthorized export attempt Deny, audit and alert
Break-glass use Immediate notification and mandatory
retrospective review
Signing-key anomaly Suspend publication and invoke key incident

<!-- Controlled source page 108 -->

Security event Minimum response
procedure
Audit-chain validation failure Fail closed for substantive mutation and
initiate incident response
**RBE-SEC-100** The incident response process SHALL preserve evidence required to determine whether
governance outcomes were affected.
**RBE-SEC-101** A security incident with possible decision impact SHALL trigger case-impact assessment
and, where necessary, re-review.
## 16.14 Privacy and Data Minimization
The engine shall process only data necessary for review and governance. Personal or sensitive data
should be isolated, redacted or tokenized where reviewers do not require direct access. Privacy
controls must not destroy traceability; redactions must preserve a verifiable relationship to the
protected original.
**RBE-SEC-110** Exports and AI-processing requests SHALL contain the minimum data necessary for the
declared purpose.
**RBE-SEC-111** Retention and deletion SHALL follow approved schedules while preserving legally or
methodologically required provenance.
## 16.15 Security Assurance and Acceptance
- Threat-model review before major architecture change.
- Secure code review and automated security tests in CI.
- Penetration testing before production and after material boundary changes.
- Access-control and separation-of-duties test suites.
- Backup, key-recovery and incident-response exercises.
- Architecture conformance review for every production release.
**RBE-SEC-120** Security acceptance SHALL include evidence that governance controls remain effective
under attack, failure and privileged misuse scenarios.
## 16.16 Codex Implementation Contract
- Implement deny-by-default authorization in domain command handlers.
- Never create hidden maintenance routes capable of rewriting governed state.
- Keep secrets out of repository, fixtures, logs and generated artefacts.
- Use parameterized data access and validated command schemas.
- Preserve evidence and report hashes through every storage and transport layer.
- Add automated tests for privilege escalation, conflict enforcement and separation of duties.
- Document every new trust-boundary crossing and required security control.
- Fail closed when authorization, audit persistence or integrity verification is unavailable.
