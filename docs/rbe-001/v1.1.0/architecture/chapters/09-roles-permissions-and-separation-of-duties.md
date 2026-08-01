---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 9
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 9. Roles, Permissions and Separation of Duties

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 63 -->

## 9.1 Security and Governance Objective
Access control exists to protect independence, evidence integrity and procedural legitimacy. It is not
merely a confidentiality feature. The architecture combines role-based permissions, case-scoped
attributes, information barriers and explicit separation-of-duties rules.
**RBE-IAM-001** Every protected action SHALL be authorized against identity, role, case scope, lifecycle
state, conflict status and artefact classification.
**RBE-IAM-002** No role SHALL receive authority solely because it is organizationally senior.
**RBE-IAM-003** Permissions SHALL default to deny.
## 9.2 Principal Types
Principal type Examples Authentication expectation
Human reviewer Methodology, evidence,
reasoning, challenge,
commercial or governance
reviewer.
Strong authenticated identity;
MFA required.
Process coordinator Intake officer, board
coordinator, appeal registrar.
Strong authenticated identity;
scoped operational role.
Administrative operator Identity, infrastructure or
retention administrator.
Privileged account; just-in-
time elevation and session
logging.
Submitter / sponsor Research owner or authorized
case sponsor.
Authenticated external or
internal identity with case
scope.
Observer / auditor Read-only inspection under
explicit grant.
Authenticated, purpose-bound
and time-limited.
Service principal Workflow engine, hashing
service, report renderer,
notification service.
Workload identity, key
rotation and least privilege.
AI assistant Non-authoritative support
service.
Dedicated service identity
with restricted data and no
decision authority.
## 9.3 Role Catalogue
Role Permitted scope Key prohibition
Submitter Create drafts, submit
packages, answer bounded
clarifications, initiate eligible
Cannot assign reviewers or
edit locked evidence.

<!-- Controlled source page 64 -->

Role Permitted scope Key prohibition
appeal.
Intake Officer Validate submission contract
and admissibility.
Cannot perform substantive
review on same case.
Board Coordinator Manage assignments,
schedules and completeness.
Cannot decide merits or force
transition.
Methodology Reviewer Assess methodology
compliance.
No evidence or commercial
substitution.
Evidence Reviewer Assess source sufficiency,
independence and
traceability.
Cannot rewrite findings to
reach preferred result.
Reasoning Reviewer Assess inferential validity and
assumptions.
Cannot introduce unregistered
evidence.
Challenge Reviewer Test contradictions and
alternative explanations.
Cannot reject without
reasoned basis.
Commercial Reviewer Assess materiality only after
upstream validity.
Cannot rescue invalid
methodology or evidence.
Governance Reviewer Validate quorum, conflicts,
process and reproducibility.
Cannot change substantive
findings.
Decision Assembler Apply deterministic rule set
and compile decision
candidate.
No discretionary verdict
selection.
Publication Authority Release validated outputs. Cannot change decision
content.
Appeal Registrar Validate appeal eligibility and
grounds.
Cannot adjudicate appeal
merits.
Appeal Reviewer Review eligible appeal
grounds.
Must satisfy independence
from challenged decision.
Auditor Inspect retained records and
replay decisions.
Read-only; no workflow
commands.
System Administrator Operate identity,
infrastructure and
configuration.
No substantive artefact
mutation.
Retention Administrator Execute archival and legal
retention actions.
No content editing.
AI Assistant Summarize, classify or
retrieve within approved
No scoring, signing, transition
or final decision authority.

<!-- Controlled source page 65 -->

Role Permitted scope Key prohibition
bounds.
## 9.4 Permission Model
Permission family Representative actions
Case create, view metadata, submit, withdraw,
initiate appeal
Evidence upload draft, lock, view, verify digest, request
amendment
Assignment propose, accept, decline, remove, adjudicate
conflict
Assessment create, edit own draft, seal, view permitted
peer output
Challenge issue, answer, disposition, escalate
Decision assemble, validate, sign, publish, replay
Governance declare conflict, pause, block, void, record
incident
Audit query, export, verify chain, run replay
Administration manage roles, keys, policies, retention
schedules
**RBE-IAM-020** Permissions SHALL be action-specific; broad “edit case” or “admin all” grants SHALL NOT
authorize substantive mutations.
**RBE-IAM-021** Every permission grant SHALL be case-scoped unless the action is explicitly platform-
scoped.
## 9.5 Separation-of-Duties Rules
Control pair Mandatory rule
Submission vs intake Submitter cannot validate own submission.
Intake vs substantive review Intake officer cannot fill a required review
function on same case.
Evidence custody vs evidence assessment Person who materially prepared or curated
evidence cannot be sole evidence reviewer.
Independent review vs governance validation A reviewer cannot be the only governance
validator of their own work.
Decision assembly vs publication Assembler cannot be sole publication

<!-- Controlled source page 66 -->

Control pair Mandatory rule
authority.
Administration vs substantive decision System administrator cannot create or alter
findings or verdicts.
Original panel vs appeal panel Appeal panel must exclude reviewers whose
work is directly challenged, except as non-
voting respondents.
Methodology ownership vs live adjudication Methodology owner cannot amend rules for
active case and then adjudicate under the
amendment.
AI assistance vs human attestation AI-generated material requires accountable
human review and cannot self-attest.
**RBE-IAM-030** The authorization engine SHALL evaluate incompatible-role combinations before
assignment and again before every sensitive action.
**RBE-IAM-031** Separation-of-duties violations SHALL be blocking governance incidents.
## 9.6 Four-Eyes and Multi-Review Controls
Action Minimum control
Evidence lock One initiator plus one independent verifier, or
deterministic system verifier with human
approval.
Material assignment override Coordinator plus governance approval.
Decision finalization Decision assembler plus governance validator.
Publication Validated decision plus independent
publication authority.
Appeal eligibility exception Appeal registrar plus governance authority.
Void declaration Governance authority plus recorded second
approval.
Privileged access to sealed assessment Break-glass initiator plus independent
approver and auditor notification.
## 9.7 Information Barriers
Information visibility is governed by function and state. Isolation protects independence; disclosure
occurs only when the lifecycle requires it.
Stage Visible to reviewer Hidden until authorized
Before assignment acceptance Case metadata needed for Substantive evidence and peer

<!-- Controlled source page 67 -->

Stage Visible to reviewer Hidden until authorized
conflict declaration. identities where unnecessary.
Independent review Role-relevant evidence and
methodology.
Peer conclusions, target
outcome, executive
preference.
Challenge Sealed assessments and
scoped supporting material.
Unrelated confidential data.
Consolidation Normalized findings and
signed assessments.
Administrative notes without
decision relevance.
Appeal Original decision, appeal
grounds and required record.
New material outside allowed
appeal scope.
**RBE-IAM-050** The system SHALL log every disclosure of sealed or restricted artefacts.
**RBE-IAM-051** Outcome labels and commercial desirability signals SHALL be withheld where they are
not required for the reviewer’s function.
## 9.8 Conflict-of-Interest Controls
- Financial interest in the outcome
- Operational ownership of the submitted work
- Prior authorship of material under review
- Reporting-line pressure or executive sponsorship
- Personal or professional relationship creating reasonable doubt
- Prior public commitment to a specific outcome
- Recent paid work for a materially affected party
- Access to non-record evidence that cannot be disclosed
**RBE-IAM-060** Conflict declarations SHALL occur before substantive access and be renewed when
material circumstances change.
**RBE-IAM-061** The conflicted individual SHALL NOT adjudicate their own conflict.
**RBE-IAM-062** Conflict disposition SHALL be immutable, reasoned and visible to governance reviewers
and auditors.
## 9.9 Privileged Administration and Break-Glass
Control Requirement
Just-in-time elevation Privileged role granted for a bounded duration
and purpose.
Named ticket or incident Every elevation references a governance or
operations record.
Session recording Commands and affected resources are logged.
No content authority Elevation does not confer substantive review

<!-- Controlled source page 68 -->

Control Requirement
permissions.
Break-glass approval Independent approval unless immediate
preservation requires emergency use.
Post-event review Mandatory governance and security review.
Credential hygiene Separate admin identities; no shared accounts.
**RBE-IAM-070** Break-glass access SHALL never permit alteration of sealed or decided substantive
artefacts.
## 9.10 AI Permission Boundary
AI may AI may not
Retrieve approved artefacts within caller
scope.
Choose or influence final decision outcome.
Draft summaries with source references. Sign assessments or decisions.
Check structural completeness. Create evidence or conceal uncertainty.
Suggest potential contradictions for human
review.
Transition cases or adjudicate conflicts.
Generate report prose from locked structured
data.
Override rule engine or governance controls.
Assist with deterministic classification where
policy allows.
Receive broader data access than the
accountable user.
**RBE-IAM-080** Every AI-produced substantive draft SHALL be labeled as machine-assisted and attributed
to the accountable human approver.
**RBE-IAM-081** AI service identities SHALL have no permission to finalize, sign, publish, appeal, void or
supersede a decision.
## 9.11 Access Review and Revocation
- Periodic role recertification
- Per-case assignment review at major lifecycle gates
- Immediate revocation on conflict, departure or credential compromise
- Automatic expiry of temporary access
- Verification that revoked users cannot retrieve cached protected content
- Audit comparison between granted permissions and actions taken
**RBE-IAM-090** Revocation SHALL affect future access immediately while preserving attributable
historical records.

<!-- Controlled source page 69 -->

## 9.12 Codex Implementation Contract
- Separate identity, authorization and business-rule evaluation.
- Implement policy-as-code with versioned rules.
- Authorize server-side on every action; never trust UI state.
- Include lifecycle state and conflict status in authorization decisions.
- Avoid superuser paths in application logic.
- Create test fixtures for every incompatible-role pair.
- Test confused-deputy and privilege-escalation scenarios.
- Use workload identities for services and rotate credentials.
- Make AI permissions an explicit deny-heavy policy set.
