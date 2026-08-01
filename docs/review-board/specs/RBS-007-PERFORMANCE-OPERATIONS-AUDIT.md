# Reviewer Specification: Performance and Operations Audit

**Document ID:** RBS-007
**Version:** 2.2.0
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval before first operational use
**Applicability:** Provena Foundry Review Board only. Not applicable to GS-P001.
**Governing Methodology:** RBM-001 v2.2.0
**Reviewer Role:** Performance and Operations Auditor (POA)
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

The Performance and Operations Auditor (POA) is responsible for assessing whether the artefact under review meets its performance obligations, whether it is operationally ready for deployment, and whether the change introduces performance regressions or operational risks.

Performance assessment is evidence-based. The POA does not estimate or model performance unless no measured evidence exists, and in that case, the absence of measured evidence is itself a finding. The POA works from benchmarks, profiling output, load test results, and operational metrics — not from code reading alone.

Operational readiness encompasses the system's ability to be monitored, diagnosed, deployed, and recovered under real-world conditions.

---

## 2. Scope

### 2.1 Performance Scope

- Latency: response time for user-facing and API operations, relative to baselines and SLAs.
- Throughput: transactions per second under load, relative to baselines and capacity requirements.
- Resource utilisation: CPU, memory, disk, and network consumption at expected load.
- Scalability: behaviour under increasing load; identification of scaling limits.
- Database query performance: query execution time, use of indexes, lock contention.
- External dependency latency: latency added by third-party services and its impact on system performance.
- Performance regression: whether the change has degraded performance relative to the prior version.

### 2.2 Operations Scope

- Observability: are logs, metrics, and traces sufficient to diagnose issues in production?
- Alerting: are alerts configured for critical system conditions?
- Deployment: is the deployment process safe, repeatable, and rollback-capable?
- Health checks: are health check endpoints present and meaningful?
- Startup and shutdown: does the service start and stop cleanly?
- Configuration management: can the service be configured without code changes?
- Dependency availability: what happens if dependencies are unavailable at startup or during operation?
- Data migration: if schema or data changes are required, are they safe and reversible?

### 2.3 Out of Scope

- Security controls (Security and Privacy Auditor).
- Test methodology (QA and Reliability Auditor).
- Business logic correctness (Business and Commercial Auditor).
- GS-P001 systems.

---

## 3. Responsibilities

| Responsibility | Timing |
|---------------|--------|
| Assess the performance implications of the change scope | Start of review |
| Review performance benchmark results against baselines and SLAs | During review |
| Identify performance regressions from before/after comparison | During review |
| Assess database query performance for new or modified queries | During review |
| Assess operational readiness: observability, alerting, deployment | During review |
| Produce the POA Report | End of review |

---

## 4. Independence Rules

The POA must not have:
- Produced the performance benchmarks in the Input Package.
- Designed the performance architecture of the components under review.
- Set the SLAs or performance targets being assessed against.

Where the POA has prior knowledge of performance characteristics from previous work on the system, they must declare this and apply extra rigour to avoid anchoring on prior expectations rather than current evidence.

---

## 5. Required Inputs

| Input | Source | Required Condition |
|-------|--------|--------------------|
| Performance benchmark results | Input Package | If performance implications declared in scope |
| Baseline performance results (prior version) | Input Package or performance archive | If regression assessment required |
| SLA document or performance targets | Commercial agreement or specification | If SLA is in scope |
| Database query execution plans | Input Package or tool output | If database changes are in scope |
| Load test results | Input Package | If throughput/scalability changes are in scope |
| Profiling output | Input Package | If resource utilisation changes are in scope |
| Monitoring/alerting configuration | Authoring team | For operational readiness assessment |
| Deployment runbook | Authoring team | For deployment assessment |
| Previous POA findings | Previous Review Record | Re-reviews only |

---

## 6. Audit Procedure

### Step 1 — Performance Scope Identification

Determine whether the change has performance implications:

- Does it modify a code path executed on every or most requests?
- Does it add, modify, or remove database queries?
- Does it add a new external dependency call in a critical path?
- Does it change caching behaviour?
- Does it change resource allocation (thread pools, connection pools, memory limits)?
- Does it claim to improve performance?

If none of these apply, the performance assessment scope is limited. Document this explicitly.

### Step 2 — Benchmark Authenticity Confirmation

Confirm that benchmarks:

- Were run against the artefact version under review (commit SHA confirmed).
- Were run in a consistent environment comparable to prior benchmark runs.
- Were run with a representative load profile (not a synthetic minimum that flatters the results).
- Have a sufficient number of iterations to be statistically meaningful (warmup period, multiple runs).

Benchmarks that cannot be confirmed as authentic are an Evidence Gap (coordinate with DEA).

### Step 3 — Performance Regression Assessment

Compare benchmark results against the baseline:

- For each measured metric (p50, p95, p99 latency; throughput; CPU; memory): has the metric worsened relative to the baseline?
- Is the degradation within the acceptable tolerance declared in the SLA or performance targets?
- Is there an explanation for any degradation?

A regression is a finding even if the absolute performance is within SLA, if it represents unexplained deterioration.

### Step 4 — SLA Compliance Assessment

For each performance SLA metric:

- Does the benchmark result meet the SLA threshold?
- Under what load conditions was the benchmark run? Are those conditions representative of the expected production load?
- Are p99 and worst-case latencies within acceptable bounds, not only median values?

Do not accept median-only metrics for SLA compliance. Systems frequently meet their median targets while failing clients in the tail.

### Step 5 — Database Query Assessment

For each new or modified database query:

- Is an execution plan available?
- Does the query use indexes appropriately (no full table scans on large tables without justification)?
- Is there a risk of lock contention from this query under concurrent load?
- Are N+1 query patterns present?

### Step 6 — External Dependency Latency Assessment

For each new or modified external service call in a request path:

- What is the expected latency of the external call?
- Is the call on the critical path (blocking the response to the client)?
- Is there a timeout? (Coordinate with QRA.)
- Is the external call's latency contribution within the SLA budget?

### Step 7 — Operational Readiness Assessment

**Observability:**
- Are structured logs emitted for significant operations? Do logs include request IDs for distributed tracing?
- Are application-level metrics exported (request count, error rate, latency histograms)?
- Are distributed traces available for cross-service request paths?

**Alerting:**
- Are alerts configured for: error rate spikes, latency degradation, resource saturation, and service unavailability?
- Are alert thresholds calibrated (not so sensitive as to generate noise, not so loose as to miss real issues)?

**Deployment:**
- Is the deployment process documented in a runbook?
- Is rollback possible? Is the rollback process documented and tested?
- Are database migrations reversible? If not, is a compensating migration available?

**Health Checks:**
- Is a health check endpoint present?
- Does the health check reflect actual service readiness (database connectivity, dependency availability) rather than only process liveness?

**Startup and Shutdown:**
- Does the service drain in-flight requests on shutdown?
- Does the service fail fast on startup if required configuration is absent?

---

## 7. Checklist

### 7.1 Performance Benchmark Validity

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-01 | Benchmarks run against correct artefact version | Benchmark metadata | SHA or build hash matches Review Initiation Record |
| POA-02 | Benchmark environment is documented | Benchmark report | Hardware, OS, and runtime are stated |
| POA-03 | Benchmark load profile is representative | Benchmark report | Load profile matches expected production load profile |
| POA-04 | Sufficient iterations for statistical validity | Benchmark report | Warmup excluded; multiple runs averaged; variance is reported |
| POA-05 | Baseline benchmarks are present for comparison | Input Package | Prior-version benchmark results are included |

### 7.2 Performance Regression

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-06 | p50 latency has not worsened beyond tolerance | Benchmark comparison | p50 delta is within declared tolerance |
| POA-07 | p99 latency has not worsened beyond tolerance | Benchmark comparison | p99 delta is within declared tolerance |
| POA-08 | Throughput has not degraded beyond tolerance | Benchmark comparison | TPS delta is within declared tolerance |
| POA-09 | CPU utilisation at target load is unchanged or improved | Benchmark comparison | CPU delta is within declared tolerance |
| POA-10 | Memory utilisation at target load is unchanged or improved | Benchmark comparison | Memory delta is within declared tolerance |
| POA-11 | Any regressions have explanations | Change Summary | Author has explained regressions; explanation is plausible |

### 7.3 SLA Compliance

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-12 | p99 latency meets SLA threshold at target load | Benchmark vs. SLA | p99 ≤ SLA target at expected concurrent load |
| POA-13 | Throughput meets SLA threshold at target load | Load test vs. SLA | TPS ≥ SLA target at expected concurrent load |
| POA-14 | Assessment is based on p99, not median only | Benchmark report | p99 metrics are present and assessed |

### 7.4 Database Queries

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-15 | Execution plans exist for new/modified queries | Input Package | EXPLAIN ANALYZE or equivalent present |
| POA-16 | No full table scans on tables expected to grow large | Execution plan | No Seq Scan on tables without a documented size bound |
| POA-17 | N+1 query patterns are absent | Code and query review | No loop generating individual queries that could be batched |
| POA-18 | Lock contention risk is assessed for write-heavy queries | Query and concurrency review | High-concurrency write paths are identified and mitigation is documented |

### 7.5 External Dependencies

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-19 | External calls on critical paths have latency budgets | Architecture review | Expected latency is within the request latency budget |
| POA-20 | External call latency is measured in benchmarks | Benchmark report | External dependency latency is included in end-to-end benchmark measurement |

### 7.6 Observability

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-21 | Structured logs are emitted for significant operations | Code review | Key operations produce structured log entries with request IDs |
| POA-22 | Application metrics are exported | Configuration and code review | Error rate, latency, and request count metrics are available |
| POA-23 | Distributed tracing is implemented for cross-service paths | Code review | Trace context is propagated across service boundaries |

### 7.7 Alerting

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-24 | Alerts exist for error rate spikes | Alert configuration review | Alert fires when error rate exceeds defined threshold |
| POA-25 | Alerts exist for latency degradation | Alert configuration review | Alert fires when p99 latency exceeds defined threshold |
| POA-26 | Alerts exist for resource saturation | Alert configuration review | Alert fires when CPU or memory exceeds defined threshold |

### 7.8 Deployment and Recovery

| # | Item | Method | Pass Condition |
|---|------|--------|----------------|
| POA-27 | Deployment runbook exists and is current | Documentation review | Runbook covers this artefact version |
| POA-28 | Rollback procedure is documented | Runbook review | Rollback steps are specific and have been tested |
| POA-29 | Database migrations are reversible or a compensating migration exists | Migration plan review | No irreversible migration step without a documented rollforward-only plan |
| POA-30 | Health check reflects actual service readiness | Code review | Health check tests database connectivity and key dependency availability |
| POA-31 | Service drains in-flight requests on shutdown | Code review | SIGTERM handling includes graceful drain |
| POA-32 | Service fails fast on missing required configuration | Code review | Missing required env vars cause immediate startup failure with a clear error |

---

## 8. Evidence Standards

| Finding Type | Minimum Evidence Tier | Example Evidence |
|-------------|----------------------|-----------------|
| SLA breach | T1 | Benchmark output showing p99 above SLA threshold |
| Performance regression | T1 | Before/after benchmark comparison showing metric degradation |
| Full table scan | T1 | EXPLAIN ANALYZE output showing Seq Scan |
| N+1 query | T2 | Code walkthrough showing loop with per-iteration query |
| Missing alert | T2 | Alert configuration showing absence of required alert |
| Missing health check | T2 | Code review showing health endpoint not checking dependency |

A claim that performance is acceptable without benchmark evidence is not admissible. The absence of benchmarks where performance implications are declared is an Evidence Gap.

> **T3-AUTHORITATIVE-EXTERNAL exception (RBM-001 §8.2):** For SEV-1 findings grounded in a legal, regulatory, contractual, or technical specification obligation, T3 evidence is admissible where all four conditions are met: (1) the source is authoritative for Provena Foundry's context; (2) the specific clause or section is named; (3) applicability in a single logical step is demonstrated; and (4) the source is confirmed in force at the time of the review. Such findings must be flagged `T3-AUTHORITATIVE-EXTERNAL` in the TPL-FND. This exception is relevant to POA findings grounded in SLA obligations that are contractually mandated.

---

## 9. Finding Classification Guidance

### SEV-1 for Performance and Operations Audit

- A benchmark demonstrates that a declared SLA metric is breached at expected production load.
- A performance regression of >50% on a critical path metric (p99 latency or throughput) with no explanation or mitigation.
- A deployment is not rollback-capable and contains a schema migration that cannot be reversed.

### SEV-2 for Performance and Operations Audit

- Performance benchmarks are absent where performance implications are declared in scope (Evidence Gap with commercial impact).
- A full table scan exists on a table expected to grow to production scale.
- An N+1 query pattern in a critical path.
- No health check is present or the health check is liveness-only (does not check dependencies).
- No alerting is configured for error rate or latency.
- A graceful shutdown is not implemented for a service that handles long-lived requests.

### SEV-3 for Performance and Operations Audit

- Benchmark load profile is not fully representative (partially applicable results).
- p99 metrics are absent from benchmarks (only median reported).
- Distributed tracing is absent in a multi-service path.
- Alert thresholds are present but poorly calibrated (known to produce excessive noise or known to be too loose).
- Deployment runbook is present but not current for this artefact version.

### SEV-4 for Performance and Operations Audit

- Benchmark environment documentation is incomplete but the environment is known to be consistent.
- Structured logging is present but lacks request IDs in some paths.

---

## 10. Board Decision Contribution

The POA does not issue a Board outcome or process status. The POA raises findings and records whether in-scope performance and operations evidence is `SUFFICIENT`, `INSUFFICIENT`, or `NOT_APPLICABLE` for a PASS-class conclusion, with missing evidence listed.

The POA must state whether the evidence supports operational readiness for deployment. This evidence-sufficiency contribution is traceable, not a Board vote or outcome.

---

## 11. Required Output

### Performance and Operations Audit Report

```
PERFORMANCE AND OPERATIONS AUDIT REPORT
=========================================
Document ID:        TPL-POAR
Review ID:
POA Name:
Report Date:
Artefact Identifier:
Methodology Version: RBM-001 [version]
This Spec Version:  RBS-007 [version]

PERFORMANCE SCOPE
Change has performance implications: [ ] YES  [ ] NO  [ ] UNCERTAIN
Basis for scope determination:

BENCHMARK VALIDITY
Benchmarks present: [ ] YES  [ ] NO
Version confirmed: [ ] YES  [ ] NO  [ ] N/A
Environment documented: [ ] YES  [ ] NO  [ ] N/A
Baseline benchmarks present: [ ] YES  [ ] NO  [ ] N/A
Assessment: [ ] VALID  [ ] PARTIALLY VALID  [ ] INVALID  [ ] ABSENT

PERFORMANCE RESULTS SUMMARY (if benchmarks present)
                    Baseline    Current    Delta    SLA Target    Status
p50 Latency:
p99 Latency:
Throughput (TPS):
CPU @ target load:
Memory @ target load:

SLA COMPLIANCE
SLA metrics assessed: [list]
SLA breaches identified: [ ] YES  [ ] NO
Details if YES:

DATABASE QUERY ASSESSMENT
New/modified queries in scope: [ ] YES  [ ] NO
Execution plans present: [ ] YES  [ ] NO  [ ] N/A
Full table scan findings: [count]
N+1 query findings: [count]

OPERATIONAL READINESS
Structured logging: [ ] PRESENT  [ ] PARTIAL  [ ] ABSENT
Application metrics: [ ] PRESENT  [ ] PARTIAL  [ ] ABSENT
Distributed tracing: [ ] PRESENT  [ ] PARTIAL  [ ] ABSENT  [ ] N/A
Alerting (error rate): [ ] PRESENT  [ ] ABSENT
Alerting (latency): [ ] PRESENT  [ ] ABSENT
Health check (meaningful): [ ] PRESENT  [ ] LIVENESS ONLY  [ ] ABSENT
Graceful shutdown: [ ] PRESENT  [ ] ABSENT  [ ] N/A
Deployment runbook: [ ] PRESENT AND CURRENT  [ ] PRESENT BUT STALE  [ ] ABSENT
Rollback procedure: [ ] DOCUMENTED AND TESTED  [ ] DOCUMENTED  [ ] ABSENT

FINDINGS SUMMARY:
  SEV-1: [count]
  SEV-2: [count]
  SEV-3: [count]
  SEV-4: [count]

FINDINGS:
[For each finding, attach a completed TPL-FND]

OPERATIONAL READINESS ASSESSMENT:
[ ] The artefact is operationally ready for deployment.
[ ] The artefact is operationally ready with conditions — [describe conditions].
[ ] The artefact is not operationally ready for production deployment.

Basis for assessment:

PASS-CLASS EVIDENCE SUFFICIENCY:
[ ] SUFFICIENT  [ ] INSUFFICIENT  [ ] NOT APPLICABLE
Missing evidence / limitations:

AI ASSISTANCE:
[ ] AI tools were used — describe what for and confirm independent verification of all findings
[ ] AI tools were not used

POA Signature:
Date:
```

---

## 12. Reviewer Prompt Conversion Notes

**Role Prompt Identity:** "You are a non-authoritative AI assistant supporting the named human Performance and Operations Auditor. You do not hold the POA role, count toward quorum, assign severity, sign findings, or issue an outcome. Help locate measured performance and operations evidence."

**Key Prompt Constraints:**
- Must not accept performance claims without benchmark evidence.
- Must assess p99 latency, not only median.
- Must not assess security controls — raise any security-adjacent operational concern as a cross-reference to the SPA.
- Must assess SLA compliance against the actual SLA targets, not implied or assumed targets.
- Must not assess GS-P001 performance or operational configuration.
- Operational readiness finding must be an explicit assessment, not implied.
- Must label every output as an unsigned draft; operational readiness and evidence sufficiency remain human reviewer acts.

**Inputs to Prompt:** Performance benchmark results (current and baseline), SLA document, database execution plans, load test results, monitoring/alerting configuration, deployment runbook, health check implementation, changed source files.

**Output Format:** Unsigned draft report matching §11, with evidence candidates for human verification. TPL-FND records become valid only after the named human POA verifies evidence, supplies severity, and signs.

---

---

## Document History

| Version | Date | Summary of Changes |
|---------|------|--------------------|
| 1.0.0 | 2026-07-18 | Initial release |
| 1.1.0 | 2026-07-18 | Updated to RBM-001 v1.1.0; added T3-AUTHORITATIVE-EXTERNAL evidence exception note to §8 with SLA-obligation relevance; status set to RELEASE-CANDIDATE |
| 2.0.0 | 2026-07-19 | Aligned terminology and evidence-sufficiency contribution with RBM-001 v2.0.0. |

*End of RBS-007 v2.0.0*
