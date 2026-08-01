# Reviewer Specification: Security and Privacy Audit

**Document ID:** RBS-006
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** Security and Privacy Auditor (SPA)
**Last Updated:** 2026-07-19

---

## Table of Contents

1. [Role Definition](#1-role-definition)
2. [Scope](#2-scope)
3. [Responsibilities](#3-responsibilities)
4. [Independence Rules](#4-independence-rules)
5. [Required Inputs](#5-required-inputs)
6. [Audit Procedure](#6-audit-procedure)
7. [Checklist](#7-checklist)
8. [Evidence Standards](#8-evidence-standards)
9. [Finding Classification Guidance](#9-finding-classification-guidance)
10. [Board Decision Contribution](#10-board-decision-contribution)
11. [Required Output](#11-required-output)
12. [Reviewer Prompt Conversion Notes](#12-reviewer-prompt-conversion-notes)

---

## 1. Role Definition

The Security and Privacy Auditor (SPA) is responsible for assessing the security controls, threat exposure, and privacy obligations of the artefact under review. The SPA's function is to identify security vulnerabilities, assess the adequacy of access controls and data protection mechanisms, and confirm that privacy obligations are understood and implemented.

The SPA must have direct security engineering experience. The SPA must be willing to raise Critical findings even when doing so delays a release. Security findings are non-negotiable: they cannot be waived by commercial pressure.

The SPA's approach must be threat-driven, not checklist-driven. A checklist confirms that known controls are present; the SPA must also ask what controls are absent and what threats are unmitigated.

---

## 2. Scope

### 2.1 Security Scope

- Authentication and authorisation controls: correctness, completeness, and bypass resistance.
- Input validation and injection attack resistance.
- Secrets management: absence of hardcoded secrets, secure storage and transmission.
- Cryptographic implementations: algorithm choice, key management, and correct usage.
- Dependency vulnerabilities: known CVEs in the dependency manifest.
- Session management: token lifetime, revocation, and fixation resistance.
- Error handling: absence of sensitive data in error responses.
- Logging: security-relevant events are logged without logging sensitive data.
- API security: rate limiting, authentication enforcement, authorisation scoping.
- Infrastructure configuration: where in scope, network exposure, permission boundaries.

### 2.2 Privacy Scope

- Personal data identification: which personal data does this change handle?
- Lawful basis for processing: is there a declared lawful basis for each personal data type?
- Data minimisation: is only the minimum necessary personal data collected and processed?
- Retention compliance: is personal data retained only for the declared retention period?
- Access control for personal data: is access to personal data restricted to authorised principals?
- Data subject rights: does the change affect the system's ability to fulfil data subject rights (access, deletion, portability)?
- Cross-border transfer: is personal data transferred across jurisdictional boundaries, and if so, is this permitted?

### 2.3 Out of Scope

- Business logic correctness (unless it has a direct security implication).
- Performance (Performance and Operations Auditor).
- Test methodology (QA and Reliability Auditor).
- GS-P001 security controls.

---

## 3. Responsibilities

| Responsibility | Timing |
|---------------|--------|
| Review security scan results (SAST, DAST, dependency vulnerability scan) | Start of review |
| Identify which security and privacy concerns are in scope for this change | Start of review |
| Conduct threat model analysis for new or materially changed attack surfaces | During review |
| Assess authentication and authorisation correctness | During review |
| Assess input validation and injection resistance | During review |
| Assess secrets management | During review |
| Assess privacy implications of the change | During review |
| Flag any Critical findings to the Board Chair immediately, without waiting for the end of review | On discovery |
| Produce the SPA Report | End of review |

**Critical finding immediacy rule:** If the SPA discovers a SEV-1 finding during review, the Board Chair must be notified immediately. The SPA may continue reviewing but must not withhold a SEV-1 finding until the report is complete.

---

## 4. Independence Rules

The SPA must not have:
- Designed or implemented the security controls under assessment.
- Authored the security scan configuration or selected the scanning tool for this artefact.
- Had prior knowledge of the specific vulnerability (i.e., been told about it and asked to "confirm" it — the SPA must discover findings independently).

For artefacts touching production authentication or authorisation systems, the SPA must be independent of the team that implemented those systems, regardless of whether those systems are directly in the change scope.

---

## 5. Required Inputs

| Input | Source | Required Condition |
|-------|--------|--------------------|
| SAST scan results | Input Package (conditional, see RBM-001 §7.2) | If any security changes declared in scope |
| Dependency vulnerability scan results | Input Package | Always |
| DAST scan results | Input Package (conditional) | If the change modifies externally accessible endpoints |
| Privacy impact assessment | Input Package (conditional) | If personal data handling is in scope |
| Changed source files | Diff | Always |
| API specification (current and prior) | Input Package | If API changes are in scope |
| Authentication/authorisation configuration | Authoring team | If auth changes are in scope |
| Previous SPA findings | Previous Review Record | Re-reviews only |

---

## 6. Audit Procedure

### Step 1 — Attack Surface Analysis

Identify the attack surface of the change:

- What new inputs does the system accept from external or untrusted sources?
- What new endpoints, entry points, or data flows are introduced?
- What trust boundaries are crossed by the change?
- What new principals (users, services, systems) are granted access?

An attack surface analysis is the starting point. All subsequent security assessment is directed at the attack surface.

### Step 2 — Scan Result Assessment

Review security scan results:

- SAST: for each finding, determine if it represents a genuine vulnerability in the context of this artefact (not all SAST findings are exploitable; the SPA must assess applicability, not just list findings).
- Dependency vulnerability scan: for each CVE, determine severity (using the CVE's CVSS score adjusted for the usage context) and whether it is exploitable in the Provena Foundry deployment context.
- DAST: for each finding, confirm it is reproduced against the artefact under review (not a prior version).

SAST and DAST findings are T1 evidence for security issues. The SPA must still assess whether each finding is applicable — a tool finding in dead code or in a protected context has different severity than the same finding in an active, exposed path.

### Step 3 — Authentication and Authorisation Review

For any change that touches auth:

- Are all endpoints that require authentication protected? Is there any path to access protected data without valid authentication?
- Are authorisation checks applied at the correct layer (not only in the UI)?
- Is there a risk of privilege escalation (a lower-privilege principal accessing higher-privilege data or operations)?
- Are authorisation failures audited?
- Is token/session lifetime appropriate?
- Is token revocation implemented and tested?

### Step 4 — Input Validation and Injection Review

For all inputs accepted from untrusted sources:

- Is the input validated against an expected type, length, and format?
- Is the input sanitised before use in SQL, shell, HTML, or other injection contexts?
- Is parameterised query / prepared statement usage confirmed for all database interactions with user-supplied data?
- Is file upload handled securely (type validation, storage location, execution prevention)?

### Step 5 — Secrets and Cryptography Review

- Are there hardcoded secrets, API keys, or passwords in the changed files? (Coordinate with SAA if SAA already identified this.)
- Are secrets loaded from environment variables or a secrets manager, not configuration files in the repository?
- Are cryptographic algorithms appropriate (no MD5, SHA1, DES for security purposes; RSA keys ≥ 2048 bits; AES-128 minimum)?
- Are cryptographic keys managed with appropriate access controls?
- Is TLS enforced for all external communications?

### Step 6 — Error Handling and Logging Review

- Do error responses return internal stack traces, database errors, or other sensitive information to clients?
- Are security-relevant events (authentication failures, authorisation failures, privilege escalations) logged?
- Are logs free of sensitive data (passwords, tokens, personal data)?
- Is log injection prevented (user input in log statements is sanitised or structured)?

### Step 7 — Privacy Assessment (if personal data is in scope)

- Enumerate the personal data fields introduced or modified by this change.
- For each: confirm the lawful basis for processing is documented.
- Confirm only the minimum necessary data is collected (data minimisation principle).
- Confirm retention policy is enforced or planned.
- Confirm access is restricted to authorised principals.
- Confirm cross-border transfer restrictions are met.

---

## 7. Checklist

### 7.1 Security Scan Baseline

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SPA-01 | SAST scan completed on changed files | Scan result review | Scan report present, run against artefact version under review |
| SPA-02 | Dependency vulnerability scan completed | Scan result review | Scan report present for all runtime dependencies |
| SPA-03 | DAST scan completed (if externally accessible endpoints changed) | Scan result review | Scan report present, run against the deployed artefact version |
| SPA-04 | All SAST Critical/High findings assessed for applicability | SPA review of scan output | Each Critical/High SAST finding has an applicability assessment from SPA |
| SPA-05 | All CVEs with CVSS ≥ 7.0 in dependency scan assessed for exploitability | SPA review | Each high/critical CVE has an exploitability assessment for the Provena Foundry context |

### 7.2 Authentication and Authorisation

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SPA-06 | All endpoints requiring authentication are protected | Code and API spec review | No endpoint that handles sensitive data or operations is accessible without valid authentication |
| SPA-07 | Authorisation is enforced server-side | Code review | Authorisation checks are in server-side code, not only in client-side UI |
| SPA-08 | No privilege escalation path is present | Threat analysis | No combination of valid operations allows a lower-privilege principal to access higher-privilege data |
| SPA-09 | Authorisation failures are logged | Code review | Auth failure events are written to the security log |
| SPA-10 | Token/session lifetime is appropriate | Configuration review | Token expiry is within a defensible time window for the use case |
| SPA-11 | Token revocation is implemented | Code review | Tokens can be invalidated before expiry |

### 7.3 Input Validation and Injection

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SPA-12 | All untrusted inputs are type- and length-validated | Code review | No unvalidated external input is processed |
| SPA-13 | SQL interactions use parameterised queries | Code review | No string concatenation for SQL construction |
| SPA-14 | No shell injection risk | Code review | No user-controlled input used in shell command construction |
| SPA-15 | HTML output is escaped | Code review | User-supplied content rendered in HTML is escaped or uses a safe templating library |
| SPA-16 | File upload is validated and sandboxed | Code review | File type, size, and storage location are validated; files are not executable from upload location |

### 7.4 Secrets and Cryptography

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SPA-17 | No hardcoded secrets | Code review and SAST | No API keys, passwords, tokens, or certificates in source files |
| SPA-18 | Secrets are loaded from environment or secrets manager | Code review | Secret sources are external to the codebase |
| SPA-19 | Cryptographic algorithms are current | Code review | No MD5, SHA1 for security purposes; no DES or 3DES; RSA ≥ 2048 |
| SPA-20 | TLS is enforced for external communications | Code and configuration review | No plain HTTP for external calls; TLS certificate validation is not disabled |
| SPA-21 | Cryptographic keys are access-controlled | Configuration and code review | Key access is restricted to the minimum necessary principals |

### 7.5 Error Handling and Logging

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SPA-22 | Error responses do not expose internal details | Code review | Stack traces, SQL errors, and internal paths are not returned to clients |
| SPA-23 | Security events are logged | Code review | Auth failures, auth successes (for sensitive operations), and authorisation failures are logged |
| SPA-24 | Logs do not contain sensitive data | Code review | No passwords, tokens, or personal data in log output |
| SPA-25 | Log injection is prevented | Code review | User input in log messages is sanitised or uses structured logging |

### 7.6 Privacy (if personal data in scope)

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| SPA-26 | Personal data fields introduced or modified are enumerated | Code and data model review | All personal data in scope is identified |
| SPA-27 | Lawful basis for processing is documented | Privacy impact assessment | Each personal data type has a documented lawful basis |
| SPA-28 | Data minimisation is applied | Code and data model review | Only necessary personal data is collected |
| SPA-29 | Retention policy is enforced | Code review | Data deletion or archival is implemented per policy |
| SPA-30 | Personal data access is restricted | Code and authorisation review | Access is limited to authorised principals with a business need |
| SPA-31 | Cross-border transfer restrictions are met | Architecture review | No personal data transfer to a prohibited jurisdiction |

---

## 8. Evidence Standards

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| Authentication bypass | T2 | Demonstrated request path that accesses protected data without authentication |
| SQL injection | T1 (SAST) or T2 | SAST finding with code location; or constructed payload demonstrating injection |
| Hardcoded secret | T2 | Specific file path and line number containing the secret |
| CVE in dependency | T1 | CVE ID, CVSS score, and usage context demonstrating exploitability |
| Privacy data exposure | T2 or T3 | Code showing personal data in log or error output; or API response containing personal data |
| Missing input validation | T2 | Code path showing unvalidated input reaching a sensitive operation |

**Note:** For authentication and authorisation findings, T2 evidence requires a documented walkthrough of the specific request path that demonstrates the vulnerability. Assertions that "auth could be bypassed" without a specific path are not admissible.

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND. This exception is directly relevant to SPA findings grounded in privacy law obligations (e.g., mandatory data localisation requirements, statutory retention limits, or data subject rights under applicable legislation) and security obligations imposed by contractual or regulatory instruments.

---

## 9. Finding Classification Guidance

### SEV-1 for Security and Privacy Audit

- Unauthenticated access to protected data or operations is possible via a demonstrated request path.
- SQL injection, command injection, or path traversal vulnerability in an exposed endpoint.
- A hardcoded secret, API key, or private key is present in source code.
- A critical CVE (CVSS ≥ 9.0) in a runtime dependency is confirmed exploitable in the Provena Foundry context.
- Personal data is transferred to a prohibited jurisdiction without authorisation.
- A cryptographic algorithm that provides no meaningful security (e.g., MD5 for password hashing) is used.

### SEV-2 for Security and Privacy Audit

- Authorisation check is present but at the wrong layer (client-side only), creating a bypass risk.
- An error response returns internal system details (stack trace, database schema) to external clients.
- A high-severity CVE (CVSS 7.0–8.9) in a runtime dependency that is likely exploitable in context.
- Security-relevant events are not logged.
- Personal data is collected without a documented lawful basis.
- Sensitive data appears in application logs.
- Input validation is absent for a category of untrusted input.

### SEV-3 for Security and Privacy Audit

- A moderate CVE (CVSS 4.0–6.9) in a dependency with limited exploitability in context.
- Log injection risk that is low-severity in the specific context.
- Data minimisation is not applied but no personal data is collected without a lawful basis.
- Token lifetime is longer than recommended but not egregiously so.
- SAST findings in non-critical, non-exposed paths.

### SEV-4 for Security and Privacy Audit

- Security header recommendations not implemented (X-Frame-Options, CSP, etc.) where these have low practical impact in the deployment context.
- Dependency with an informational advisory (not a CVE).

---

## 10. Board Decision Contribution

The SPA does not issue a Board outcome or process status. The SPA raises findings and records whether in-scope security and privacy evidence is `SUFFICIENT`, `INSUFFICIENT`, or `NOT_APPLICABLE` for a PASS-class conclusion, with missing evidence listed. Per RBM-001 §3 (P6 — Honest Rejection), security findings must never be moderated downward to avoid a `FAIL` outcome.

An unresolved SEV-1 security finding is a hard merge block with no waiver permitted. The SPA must not accept schedule pressure, commercial urgency, or team assurances as grounds for reclassifying a confirmed SEV-1 finding.

---

## 11. Required Output

### Security and Privacy Audit Report

```
SECURITY AND PRIVACY AUDIT REPORT
===================================
Document ID:        TPL-SPAR
Review ID:
SPA Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-006 [version]

ATTACK SURFACE ANALYSIS
New external inputs: [describe]
New endpoints or entry points: [describe]
New trust boundaries crossed: [describe]
New principals granted access: [describe]

SECURITY SCAN SUMMARY
SAST scan present: [ ] YES  [ ] NO  [ ] NOT APPLICABLE
SAST Critical/High findings assessed: [count assessed] / [count in scan]
Dependency vulnerability scan present: [ ] YES  [ ] NO
CVEs CVSS ≥ 7.0 assessed: [count assessed] / [count in scan]
DAST scan present: [ ] YES  [ ] NO  [ ] NOT APPLICABLE

SCOPE
Auth/authorisation in scope: [ ] YES  [ ] NO
Input validation in scope: [ ] YES  [ ] NO
Secrets/cryptography in scope: [ ] YES  [ ] NO
Error handling/logging in scope: [ ] YES  [ ] NO
Privacy (personal data) in scope: [ ] YES  [ ] NO

IMMEDIATE ESCALATIONS
[ ] No SEV-1 findings discovered during review
[ ] SEV-1 finding(s) escalated to Board Chair immediately during review
  Escalation timestamp:
  Finding(s):

FINDINGS SUMMARY:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]

FINDINGS:
[For each finding, attach a completed TPL-FND]

UNMITIGATED THREAT ASSESSMENT:
[List any threats to the attack surface that are identified but for which no finding was raised,
with rationale for why no finding was raised. This section may be empty if all threats are mitigated.]

PASS-CLASS EVIDENCE SUFFICIENCY:
[ ] SUFFICIENT  [ ] INSUFFICIENT  [ ] NOT APPLICABLE
Missing evidence / limitations:

AI ASSISTANCE:
[ ] AI tools were used — describe what for and confirm independent verification of all findings
[ ] AI tools were not used

SPA Signature:
Date:
```

---

## 12. Reviewer Prompt Conversion Notes

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human Security and Privacy Auditor. You do not hold the SPA role, count toward quorum, assign severity, sign findings, or issue an outcome. Surface candidate security and privacy evidence promptly to the named human SPA."

**Key Prompt Constraints:**
- Must assess scan results for applicability — not all tool findings are exploitable in context.
- Must raise findings based on specific, demonstrated vulnerabilities — not "this could potentially be a problem."
- Must never reclassify a confirmed Critical finding to a lower severity due to schedule or commercial pressure.
- Must not assess business logic unless it has a direct security implication.
- Must not assess GS-P001 security controls.
- All security evidence must include specific file paths, line numbers, or request paths.
- Must label every output as an unsigned draft; exploitability, severity, and evidence sufficiency remain human reviewer acts.

**Inputs to Prompt:** SAST results, dependency vulnerability scan, DAST results (if applicable), privacy impact assessment (if applicable), changed source files, API specification, auth configuration.

**Output Format:** Unsigned draft report matching §11, with evidence candidates for human verification. TPL-FND records become valid only after the named human SPA verifies evidence, supplies severity, and signs.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception to §8 with SPA-specific guidance for regulatory and privacy law obligations; status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned terminology and decision contribution with RBM-001 v2.0.0; corrected conditional-input reference. |

*End of RBS-006 v2.0.0*
