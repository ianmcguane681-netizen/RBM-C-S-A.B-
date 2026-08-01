---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 11
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 11. Review Reports and Decision Outputs

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 77 -->

## 11.1 Purpose
Reports are controlled projections of the governed record. They explain what the Board concluded,
why it concluded it, what evidence and rules were relied upon, what uncertainty remains and what
follows. They are not marketing collateral and must not persuade the reader toward an
organizational preference.
**RBE-OUT-010** Every published output SHALL be generated from the same sealed decision record and
share one decision digest.
**RBE-OUT-011** Reports SHALL distinguish fact, finding, inference, limitation, recommendation and
decision.
**RBE-OUT-003** PASS and FAIL outputs SHALL use neutral presentation and equivalent evidentiary rigor.
## 11.2 Output Catalogue
Output Audience Purpose
Decision Notice Submitter, governance
stakeholders
Authoritative outcome and
immediate implications.
Full Review Report Reviewers, architects, auditors Complete rationale, findings,
evidence and governance
record.
Executive Summary Authorized leadership Condensed explanation
without suppressing
uncertainty.
Methodology Compliance
Report
Methodology owners and
auditors
Clause-by-clause compliance
and deviations.
Evidence Assessment Report Research and assurance teams Evidence sufficiency,
independence and
traceability.
Reasoning Assessment Report Architects and reviewers Inference chain, assumptions
and logical defects.
Challenge Register Board and auditors Challenges, responses and
dispositions.
Commercial Relevance Report Commercial governance Materiality assessment
conditional on upstream
validity.
Governance Validation Report Board and auditors Quorum, conflicts, signatures,
integrity and replay status.
Findings Register All authorized consumers Structured findings with
severity, status and trace links.

<!-- Controlled source page 78 -->

Output Audience Purpose
Appeal Decision Report Appeal parties and auditors Grounds, scope, analysis and
appeal outcome.
Machine-readable Decision
Package
Systems and verification tools Canonical structured
representation for automation
and replay.
Audit Export Auditors and compliance Event timeline and
provenance evidence.
## 11.3 Decision Notice Specification
- Document identifier and version
- Case and review-session identifiers
- Decision class and effective date
- Exact conclusion reviewed
- Plain-language decision rationale
- Material findings and unresolved limitations
- Applicable methodology and ruleset versions
- Appeal eligibility and deadline
- Decision digest and verification identifier
- Authorized signatures and publication status
**RBE-OUT-020** The Decision Notice SHALL NOT omit a material limitation merely to make the outcome
easier to communicate.
## 11.4 Full Review Report Structure
Section Required content
1. Control page Identifiers, versions, classification, status and
signatures.
2. Executive summary Outcome, central rationale, key findings and
uncertainty.
3. Scope and question Exact proposition reviewed and exclusions.
4. Constitutional basis Review Board principles and burden of
justification.
5. Methodology baseline Pinned methodology, rules and deviations.
6. Evidence package Manifest summary, source quality and
limitations.
7. Functional assessments Methodology, evidence, reasoning, challenge,
commercial and governance conclusions.
8. Findings register Structured decisive and non-decisive findings.

<!-- Controlled source page 79 -->

Section Required content
9. Challenge analysis Contradictions, alternatives and dispositions.
10. Decision derivation Rule execution trace and outcome mapping.
11. Limitations and uncertainty Known unknowns and confidence boundaries.
12. Recommendations Permitted actions clearly separated from
decision.
13. Appeal and re-review Available pathways and conditions.
14. Provenance and verification Digests, signatures, audit references and replay
result.
Appendices Evidence index, glossary, rule trace and
detailed tables.
## 11.5 Findings Register
Field Requirement
finding_id Stable unique identifier.
function Originating review function.
type Compliance, evidence, reasoning, challenge,
commercial or governance.
severity Defined taxonomy; never inferred from prose.
statement Specific, falsifiable and neutral wording.
basis Evidence, methodology or rule references.
impact How the finding affects justification or process.
status Open, resolved, accepted limitation,
superseded or non-decisive.
decision_effect Blocking, contributory, informational or none.
owner Accountable function, not a preferred outcome
owner.
provenance Assessment, reviewer and signature
references.
**RBE-OUT-030** A finding SHALL NOT be included in a decision basis unless its provenance and supporting
references validate.

<!-- Controlled source page 80 -->

## 11.6 Decision Taxonomy Presentation
Decision Required plain-language
meaning Required caution
PASS The submitted conclusion is
justified under the locked
evidence, reasoning and
methodology.
Does not guarantee
implementation success or
eliminate all uncertainty.
PASS WITH FINDINGS The conclusion is justified, but
material findings require
explicit treatment or
monitoring.
Findings are not decorative;
obligations must be stated.
FAIL The conclusion is not justified
under the reviewed record.
Does not mean the underlying
opportunity is impossible; it
means this conclusion failed
justification.
INSUFFICIENT EVIDENCE The record cannot support a
defensible determination.
Must not be reframed as likely
PASS or likely FAIL.
DEFER A defined dependency
prevents a current
determination.
Must state the dependency
and conditions for
resumption.
**RBE-OUT-040** Outcome wording SHALL describe justification status, not organizational enthusiasm or
disappointment.
## 11.7 Recommendations
Recommendations are downstream guidance, not hidden decision criteria. They must be linked to
findings and remain clearly distinguishable from the verdict.
Recommendation type Allowed use
Corrective Resolve a defined methodological, evidentiary
or governance defect.
Research Collect specified evidence needed for a future
determination.
Control Mitigate a governance or operational risk.
Monitoring Track a verified uncertainty or condition.
No-build / stop Permitted where the decision and governance
mandate justify halting further work.
Proceed to next gate Permitted only when PASS conditions and
external governance allow it.

<!-- Controlled source page 81 -->

**RBE-OUT-050** A recommendation SHALL cite the finding or decision rule that justifies it.
**RBE-OUT-051** Commercial attractiveness SHALL NOT be used to soften or contradict the recorded
decision.
## 11.8 Executive Summary Rules
- State the exact decision in the first section.
- Include the central reason, not only the outcome.
- Name material limitations and blocking findings.
- Avoid promotional adjectives and persuasive framing.
- Do not collapse INSUFFICIENT EVIDENCE into “promising”.
- Retain identifiers needed to find the full report.
- Use equivalent prominence for adverse and favourable findings.
## 11.9 Machine-Readable Decision Package
Object Minimum fields
package schema_version, package_id, generated_at,
decision_digest
case case_id, session_id, submission_version, state
decision class, rationale_code, effective_at, supersedes
methodology id, version, digest
ruleset id, version, digest, execution_trace
evidence manifest_id, package_digest, item references
assessments assessment ids, function, signer, digest
findings structured findings and decision effects
challenges challenge, response and disposition references
governance quorum, conflict status, validation and replay
result
signatures signer, role, algorithm, key version, timestamp
reports human-readable output ids and digests
lineage prior decisions, appeals, remands and
successors
**RBE-OUT-070** The machine-readable package SHALL be the canonical structured source for all human-
readable reports.
**RBE-OUT-071** Schema evolution SHALL be versioned and backward-readable.

<!-- Controlled source page 82 -->

## 11.10 Report Generation and Rendering
Stage Control
Data selection Only sealed, authorized decision-package
objects.
Template selection Versioned report template.
Generation Deterministic rendering from canonical
structured data.
Validation Required-section, cross-reference and digest
checks.
Accessibility Tagged headings, readable tables, descriptive
links and accessible language.
Signing Bind signer to final file digest.
Publication Release only the validated signed version.
Correction Issue successor report; preserve prior file and
digest.
**RBE-OUT-080** Manual edits after rendering SHALL invalidate the report signature and require
regeneration or governed re-signing.
## 11.11 Publication and Audience Controls
Classification Audience rule
Internal controlled Named organizational roles only.
Board confidential Reviewers, governance and authorized
auditors.
Submitter restricted Submitter and named case stakeholders.
Public summary Approved redacted summary derived from
sealed report.
Regulatory / legal Released under specific authority and logged.
Machine integration Authenticated service consumers with schema
contract.
**RBE-OUT-090** Redaction SHALL not change the substantive meaning of the decision.
**RBE-OUT-091** Every publication event SHALL record recipient class, artefact digest and authorization
basis.
## 11.12 Appeal Outputs
- Original decision and digest

<!-- Controlled source page 83 -->

- Appeal identifier, filer and accepted grounds
- Scope of appeal review
- Appeal panel composition and conflict status
- Evidence and rules considered
- Ground-by-ground analysis
- Outcome: upheld, superseded or remanded
- Any successor decision identifier
- Updated lineage graph
- Signatures and publication status
## 11.13 Quality Gates
Gate Failure effect
Completeness Block publication.
Traceability Block publication.
Decision-package digest match Block publication.
Required signatures Block publication.
Neutral language check Return for correction without changing
decision.
Accessibility validation Return for correction.
Cross-reference validation Return for correction.
Replay verification Block publication.
Classification and audience authorization Block release.
## 11.14 Output Anti-Patterns
- A one-page PASS notice with no reasoning
- A FAIL report that omits contrary evidence
- Marketing language in the executive summary
- Manual spreadsheet as the only findings register
- Different verdict wording across PDF, UI and API
- Hidden caveats placed only in appendices
- Replacing a report file without preserving its prior digest
- An AI-generated narrative with no accountable human approval
- A recommendation that contradicts the decision
- Treating “insufficient evidence” as an informal positive signal
## 11.15 Codex Implementation Contract
- Generate all outputs from one canonical decision package.
- Version schemas and templates independently.
- Calculate and store digests for every published artefact.
- Create deterministic report-generation tests.

<!-- Controlled source page 84 -->

- Validate required sections and trace references automatically.
- Keep report prose neutral and template-controlled.
- Expose verification metadata to authorized consumers.
- Implement correction as successor artefact creation, never overwrite.
- Ensure AI-assisted text is reviewable, attributable and non-authoritative.
- Provide golden-file tests for PASS, PASS WITH FINDINGS, FAIL, INSUFFICIENT EVIDENCE and
DEFER outputs.
## 11.16 Sections 8–11 Architecture Freeze Checklist
- State taxonomy and transition matrix reconciled with Chapter 5 lifecycle.
- Every sensitive action mapped to a role and separation-of-duties rule.
- Audit events cover all state transitions, disclosures, signatures and publications.
- Decision provenance graph links outputs to rules, assessments and evidence.
- Replay requirements are implementable from retained data.
- Human and machine-readable reports share one canonical decision package.
- Appeal and re-review preserve prior decisions and lineage.
- AI boundaries prohibit autonomous governance or decision authority.
- All constitutional principles are reflected in system controls, not only prose.
- Requirement identifiers remain stable for later merge into the master document.
Architecture completion statement
Sections 8–11 complete the operational control layer of RBE-001. Codex may use these
chapters to implement state enforcement, authorization, audit provenance and report
generation only after the Review Board Methodology and preceding architecture chapters
are frozen. Any unresolved ambiguity SHALL be raised as an architecture question rather
than silently resolved in code.
