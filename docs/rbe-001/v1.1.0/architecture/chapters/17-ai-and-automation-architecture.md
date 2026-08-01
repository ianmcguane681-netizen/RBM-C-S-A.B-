---
document_id: RBE-001
release_version: 1.1.0
status: normalization-release-candidate
chapter: 17
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# 17. AI and Automation Architecture

> Normalized AI-readable edition. RBE-001 v1.0.0 remains immutable historical
> evidence; the v1.1.0 registers control any explicitly identified conflict.


<!-- Controlled source page 109 -->

## 17.1 Purpose
This chapter defines how artificial intelligence and deterministic automation may assist the Review
Board without becoming a decision-maker, hidden methodology or source of outcome pressure. AI is
an internal capability. It may reduce clerical effort, surface inconsistencies and improve navigation,
but it cannot own judgment, satisfy quorum or substitute for evidence.
**RBE-AI-001** The complete governed review process SHALL remain operational when all AI assistance is
disabled.
**RBE-AI-002** AI output SHALL be treated as untrusted proposed content until explicitly reviewed and
adopted by an authorized human.
**RBE-AI-003** No model, agent or automated workflow SHALL possess authority to approve, reject or
finalize a substantive Review Board outcome.
## 17.2 Permitted Uses
Use case Permitted role Required control
Evidence extraction Assistant Source citation and human
verification
Deduplication and clustering Assistant No deletion; reviewer
confirms relationship
Summarization Assistant Traceable to source passages
and labeled as generated
Contradiction surfacing Assistant Present both supporting and
opposing material
Draft finding language Assistant Human reviewer owns final
wording and rationale
Schema validation Deterministic automation Versioned rules and testable
output
Deadline and workflow
reminders Deterministic automation No substantive state override
Anomaly detection Assistant Explain signal basis and
permit dismissal
## 17.3 Prohibited Uses
- Casting or simulating a Board vote.
- Choosing a final decision class without human decision authority.
- Generating unsupported evidence or citations.
- Changing evidence, methodology, findings or decisions without a governed command.
- Suppressing contradictory evidence because it weakens a preferred outcome.

<!-- Controlled source page 110 -->

- Optimizing prompts or ranking toward approval, rejection or commercial desirability.
- Inferring sensitive personal attributes unless explicitly authorized and methodologically
necessary.
- Using confidential case data to train external models without approved contractual and technical
safeguards.
- Auto-publishing reports or recommendations.
**RBE-AI-010** The system SHALL technically prevent AI identities from invoking decision-finalization,
report-signing, appeal-resolution and privilege-management commands.
## 17.4 Human Accountability
A human may use AI-generated material only by adopting it through an attributable action.
Adoption means the reviewer has examined the underlying sources, accepts responsibility for
accuracy and understands that the generated text does not reduce their duty of independent
judgment.
**RBE-AI-020** Every AI-assisted final artefact SHALL identify the responsible human adopter and retain
provenance to the model invocation and cited source material.
**RBE-AI-021** A reviewer SHALL be able to edit, reject or ignore AI output without penalty or workflow
obstruction.
## 17.5 Model and Provider Governance
Control area Architecture requirement
Approved models Use only models recorded in the active model
registry
Provider terms Verify data-use, retention, residency and
confidentiality commitments
Model version Pin production use to a recorded model or
deployment version
Capability assessment Evaluate context length, tool use, structured
output and known limitations
Risk tier Classify use case by data sensitivity and
decision proximity
Change control Re-evaluate prompts and tests before model or
provider change
Fallback Provide deterministic or human-only path
**RBE-AI-030** Each production model deployment SHALL have an owner, approved use cases, data
classification limit, evaluation record and retirement procedure.
**RBE-AI-031** Model upgrades SHALL NOT be treated as transparent infrastructure changes where they
can alter substantive output.

<!-- Controlled source page 111 -->

## 17.6 Prompt and Instruction Governance
Prompts that influence substantive review assistance are governed artefacts. System instructions,
templates, retrieval policies, output schemas and tool permissions shall be versioned, reviewed and
testable. User-entered case content must never be allowed to override protected system instructions
or tool restrictions.
- Versioned prompt identifiers and effective dates.
- Change approval for decision-adjacent prompts.
- Explicit source-grounding and uncertainty instructions.
- Output schemas that separate facts, inference, uncertainty and recommendations.
- Prompt-injection resistance and content isolation.
- No hidden instructions that promote a preferred outcome.
**RBE-AI-040** Every model invocation SHALL record prompt version, model version, parameters, tools,
source references, actor, case, timestamp and output hash.
**RBE-AI-041** Case evidence SHALL be treated as data, not as trusted instructions to the model or agent.
## 17.7 Retrieval and Grounding
Retrieval-augmented assistance must preserve source identity, version and exact evidence location.
The model may synthesize across retrieved material but may not present an uncited assertion as
established evidence.
**RBE-AI-050** AI-generated factual claims used in review artefacts SHALL resolve to authoritative
evidence references accessible to the adopting reviewer.
**RBE-AI-051** The retrieval layer SHALL enforce the same case access, classification and conflict
restrictions as direct evidence access.
## 17.8 Output Structure and Uncertainty
- Separate extracted facts from interpretation.
- Distinguish direct evidence from model inference.
- Express uncertainty and missing context.
- Identify contradictory or unavailable evidence.
- Avoid persuasive or outcome-seeking language.
- Provide machine-verifiable references where possible.
**RBE-AI-060** AI output SHALL NOT be represented to users as a Board decision, reviewer opinion or
verified fact until the relevant human action occurs.
## 17.9 Evaluation Framework
Evaluation dimension Illustrative measures
Grounding Citation precision, unsupported-claim rate,
evidence coverage
Neutrality Outcome skew, loaded-language rate, balanced
contradiction handling
Accuracy Extraction correctness, classification accuracy,

<!-- Controlled source page 112 -->

Evaluation dimension Illustrative measures
numerical fidelity
Safety Data leakage, prompt-injection resistance,
prohibited-command resistance
Reliability Schema conformance, timeout rate, retry
behaviour, determinism where required
Human utility Acceptance with edits, reviewer time saved,
false-positive burden
**RBE-AI-070** Decision-adjacent AI features SHALL pass documented evaluations before release and after
material model, prompt or retrieval changes.
**RBE-AI-071** Evaluation datasets SHALL include adversarial, contradictory, incomplete and outcome-
tempting cases.
## 17.10 Bias and Outcome Neutrality Controls
Bias control is not satisfied by asking a model to be unbiased. The system must constrain inputs,
prompts, outputs and user experience so that AI has no incentive or authority to advance a desired
result.
- Balanced retrieval across supporting and contradictory evidence.
- Neutral labels and ordering for decision classes.
- No success metric based on approval rate or commercial conversion.
- Periodic outcome-distribution review to detect unexplained drift.
- Blind or masked evaluation where practical.
- Independent review of high-impact prompt changes.
**RBE-AI-080** AI feature performance SHALL NOT be optimized against approval, rejection, pass-rate or
commercial-conversion targets.
## 17.11 Agents and Tool Use
Agentic workflows increase risk because a model may select and sequence actions. Agents may be
used only within narrow, pre-authorized task envelopes. Every tool call must be policy-checked,
schema-validated, attributable and reversible where feasible.
Agent capability Permitted? Constraint
Search authorized evidence Yes Case-scoped access and
complete retrieval logging
Create draft note Yes Draft namespace only; human
adoption required
Assign reviewer No
Governed human or
deterministic workflow
command

<!-- Controlled source page 113 -->

Agent capability Permitted? Constraint
Change case state No Only explicit authorized
domain command
Send reminder Yes Template-bound and non-
substantive
Publish report No Human authorization and
signing required
Delete evidence No Retention-governed human
process only
**RBE-AI-090** Agent tools SHALL expose the minimum capability necessary and SHALL NOT provide
generic database, shell or unrestricted network access in production.
## 17.12 Data Protection and Model Isolation
- Classify data before model submission.
- Redact or tokenize unnecessary personal and sensitive data.
- Use private or enterprise model endpoints for protected cases.
- Disable provider training and unnecessary retention where contractually and technically
supported.
- Separate case context between sessions and tenants.
- Prevent generated content from leaking into unrelated cases.
**RBE-AI-100** Restricted evidence SHALL NOT be sent to a model or provider not approved for that
classification.
## 17.13 Failure, Fallback and Kill Switch
AI failure must degrade convenience rather than governance. Timeouts, malformed responses,
model unavailability or evaluation failures shall return the task to a human or deterministic path
without silently changing substantive state.
**RBE-AI-110** The platform SHALL provide a centrally controlled kill switch capable of disabling AI
invocations without disabling core Review Board operations.
**RBE-AI-111** AI retries SHALL preserve idempotency and SHALL NOT duplicate adopted notes,
notifications or audit events.
## 17.14 Audit and Explainability
Explainability means the system can show what model was used, what information it received, what
instructions governed it, what tools it invoked, what it returned and who accepted or rejected the
result. It does not require exposing private model reasoning.
**RBE-AI-120** AI provenance SHALL be sufficient to reproduce the invocation context to the extent
permitted by provider capability and retention policy.
## 17.15 Codex Implementation Contract
- Put AI behind explicit interfaces separate from authoritative domain services.

<!-- Controlled source page 114 -->

- Assign AI identities no substantive decision permissions.
- Persist invocation provenance and output hashes.
- Label generated content clearly in the UI and data model.
- Require human adoption before generated content enters governed artefacts.
- Provide deterministic fallbacks and feature flags.
- Validate all structured model output before use.
- Treat retrieved evidence as untrusted data and enforce case-scoped access.
- Add adversarial tests for prompt injection, data leakage and prohibited tool use.
