"""cross_run_analysis.py — Compare multiple pipeline runs for stability and consistency.

Correction 4 (original): count-only comparisons are insufficient. This module
compares runs using complaint-ID overlap, ordering stability, and source mutation.

Mutation analysis fix (Milestone 4): the original implementation hashed entire
raw records including volatile CFPB administrative metadata, causing false-positive
"unstable" verdicts. Records are now split into three named field buckets:

  CLASSIFICATION_INPUT_FIELDS
    Fields the classifier actually reads to assign mechanism, operational status,
    and software_addressable flag. A change here can alter pipeline outputs.
    Flagged as: classification_mutation — CRITICAL if detected across runs.

  STABLE_BUSINESS_FIELDS
    Stable CFPB source fields not used directly in classification. A change here
    is unexpected (CFPB should not alter complaint metadata post-filing) and
    worth noting, but does not affect pipeline outputs.
    Flagged as: business_mutation — WARNING if detected across runs.

  Volatile retrieval metadata (everything else)
    Connector-generated fields (_retrieved_at, _retrieval_url, _access_method)
    and CFPB live-updated fields (company_response, timely, date_sent_to_company,
    company_public_response) that the CFPB updates continuously.
    Flagged as: metadata_differs — INFO, expected for live CFPB pulls; NOT a
    stability issue.

Overall stability is penalised only by classification_mutation. Business mutation
adds a mild penalty. Metadata differences are never penalised.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.run_index import read_run_index

# ---------------------------------------------------------------------------
# Field bucket definitions
# ---------------------------------------------------------------------------

# Fields that feed directly into OPERATIONAL_TERMS, SOFTWARE_ADDRESSABLE_TERMS,
# and MECHANISM_RULES classification. A content change here can produce different
# mechanism assignments, different operational/software_addressable flags, and
# therefore different ODR outcomes. These are the ONLY fields that matter for
# mutation-as-pipeline-impact assessment.
CLASSIFICATION_INPUT_FIELDS: frozenset[str] = frozenset({
    "complaint_what_happened",
    "product",
    "sub_product",
    "issue",
    "sub_issue",
})

# Stable CFPB source fields that are not used in classification. Consumer-filed
# metadata that the CFPB does not modify after initial ingestion.
STABLE_BUSINESS_FIELDS: frozenset[str] = frozenset({
    "complaint_id",
    "company",
    "state",
    "zip_code",
    "tags",
    "submitted_via",
    "has_narrative",
    "date_received",
})

# Everything else is volatile retrieval metadata: fields the CFPB updates live
# (company_response, timely, date_sent_to_company, company_public_response) and
# connector-generated fields (_retrieved_at, _retrieval_url, _access_method,
# _source_name, _cfpb_hit_id, _source_record_id). These are EXPECTED to differ
# between pulls and are never treated as a stability issue.
# (No explicit set needed — anything not in the two sets above is volatile.)


def _field_subset_hash(rec: dict, fields: frozenset[str]) -> str:
    """SHA-256[:16] of a dict containing only the specified fields."""
    subset = {k: rec.get(k) for k in fields}
    blob = json.dumps(subset, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RunSnapshot:
    """Per-run data loaded from artifact files."""
    run_id: str
    timestamp: str
    verdict: str
    evidence_ceiling: str
    source_access_method: str
    # Count-level metrics
    candidate_count: int
    verified_count: int
    finding_count: int
    opportunity_count: int
    mechanisms: list[str]
    companies: list[str]
    gate_statuses: dict[str, str]
    gates_constraining: list[str]
    # Complaint-ID level metrics
    complaint_ids: list[str]                       # ordered as returned by API
    complaint_id_set_hash: str                     # SHA-256 of sorted ID list
    complaint_ordering_hash: str                   # SHA-256 of ordered ID list
    # Three-bucket content hashes (complaint_id → short hash)
    classification_content_by_id: dict[str, str]  # CLASSIFICATION_INPUT_FIELDS
    business_content_by_id: dict[str, str]         # STABLE_BUSINESS_FIELDS
    metadata_content_by_id: dict[str, str]         # volatile fields — informational

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Content maps can be large; omit from serialisation
        d.pop("classification_content_by_id", None)
        d.pop("business_content_by_id", None)
        d.pop("metadata_content_by_id", None)
        return d


@dataclass
class CrossRunComparison:
    """Result of comparing N pipeline runs."""
    run_count: int
    run_ids: list[str]
    timestamps: list[str]

    # Count-level retrieval
    candidate_counts: list[int]
    retrieval_stable: bool
    retrieval_note: str

    # Complaint-ID overlap / equality
    id_set_hashes: list[str]
    complaint_ids_identical: bool
    jaccard_similarity: float
    id_overlap_note: str

    # Ordering stability
    complaint_ordering_hashes: list[str]
    ordering_stable: bool
    ordering_note: str

    # Three-category mutation analysis
    # 1. Classification-input mutation — affects pipeline outputs; CRITICAL
    classification_mutation_detected: bool
    classification_mutation_details: list[str]
    # 2. Business-field mutation — unexpected; does not affect outputs; WARNING
    business_mutation_detected: bool
    business_mutation_details: list[str]
    # 3. Volatile metadata differences — expected for live CFPB pulls; INFO only
    metadata_differs: bool
    metadata_differs_count: int
    metadata_differs_note: str
    # Summary: True if classification OR business mutation (not metadata)
    mutation_detected: bool
    mutation_details: list[str]   # combined classification + business details

    # Verdicts
    verdicts: list[str]
    verdict_consistent: bool
    evidence_ceilings: list[str]
    ceiling_consistent: bool

    # Proof Gates
    gate_status_by_run: list[dict[str, str]]
    inconsistent_gates: list[str]

    # Mechanisms
    mechanisms_per_run: list[list[str]]
    common_mechanisms: list[str]
    any_run_mechanisms: list[str]
    mechanism_stable: bool

    # Findings / Opportunities
    findings_per_run: list[int]
    opportunities_per_run: list[int]

    # Companies
    companies_per_run: list[list[str]]
    common_companies: list[str]

    # Overall
    overall_stability: str
    stability_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _load_json_artifact(path_str: str | None) -> Any:
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _sha256_of(value: Any) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def _load_run_snapshot(entry: dict[str, Any]) -> RunSnapshot:
    paths = entry.get("artifact_paths", {})

    # ---- Candidates --------------------------------------------------------
    candidates_data = _load_json_artifact(paths.get("normalised_candidates")) or []
    candidate_count = len(candidates_data)

    # ---- Findings ----------------------------------------------------------
    findings_data = _load_json_artifact(paths.get("findings")) or []
    finding_count = len(findings_data)
    mechanisms: list[str] = []
    companies: list[str] = []
    for f in findings_data:
        mech = f.get("mechanism")
        if mech and mech not in mechanisms:
            mechanisms.append(mech)
        for company in f.get("companies", []):
            if company and company not in companies:
                companies.append(company)

    # ---- Opportunities -----------------------------------------------------
    opps_data = _load_json_artifact(paths.get("opportunities")) or []
    opportunity_count = len(opps_data)

    # ---- Verified evidence count -------------------------------------------
    processed = _load_json_artifact(paths.get("processed"))
    verified_count = 0
    if processed:
        verified_count = len(processed.get("verified_evidence", []))

    # ---- Proof gates -------------------------------------------------------
    gates_data = _load_json_artifact(paths.get("proof_gate_results")) or []
    gate_statuses: dict[str, str] = {}
    constraining: list[str] = []
    for gate in gates_data:
        gid = gate.get("gate_id", "")
        status = gate.get("status", "UNKNOWN")
        gate_statuses[gid] = status
        if gate.get("constrains_max_verdict"):
            constraining.append(gid)

    # ---- Complaint-ID level metrics ----------------------------------------
    raw_data = _load_json_artifact(paths.get("raw"))
    raw_records: list[dict] = []
    if isinstance(raw_data, dict):
        raw_records = raw_data.get("records", [])
    elif isinstance(raw_data, list):
        raw_records = raw_data

    complaint_ids: list[str] = []
    classification_content_by_id: dict[str, str] = {}
    business_content_by_id: dict[str, str] = {}
    metadata_content_by_id: dict[str, str] = {}

    for rec in raw_records:
        cid = str(
            rec.get("complaint_id")
            or rec.get("_source_record_id")
            or ""
        )
        if not cid:
            continue
        complaint_ids.append(cid)

        # Bucket 1: classification inputs — fields the classifier reads
        classification_content_by_id[cid] = _field_subset_hash(
            rec, CLASSIFICATION_INPUT_FIELDS
        )

        # Bucket 2: stable business fields — not used in classification
        business_content_by_id[cid] = _field_subset_hash(
            rec, STABLE_BUSINESS_FIELDS
        )

        # Bucket 3: volatile metadata — everything else (informational only)
        volatile_keys = frozenset(rec.keys()) - CLASSIFICATION_INPUT_FIELDS - STABLE_BUSINESS_FIELDS
        metadata_content_by_id[cid] = _field_subset_hash(rec, volatile_keys)

    sorted_ids = sorted(complaint_ids)
    complaint_id_set_hash = _sha256_of(sorted_ids)
    complaint_ordering_hash = _sha256_of(complaint_ids)

    return RunSnapshot(
        run_id=entry.get("run_id", ""),
        timestamp=entry.get("timestamp", ""),
        verdict=entry.get("verdict", ""),
        evidence_ceiling=entry.get("evidence_ceiling", ""),
        source_access_method=entry.get("source_access_method", ""),
        candidate_count=candidate_count,
        verified_count=verified_count,
        finding_count=finding_count,
        opportunity_count=opportunity_count,
        mechanisms=sorted(mechanisms),
        companies=sorted(companies),
        gate_statuses=gate_statuses,
        gates_constraining=constraining,
        complaint_ids=complaint_ids,
        complaint_id_set_hash=complaint_id_set_hash,
        complaint_ordering_hash=complaint_ordering_hash,
        classification_content_by_id=classification_content_by_id,
        business_content_by_id=business_content_by_id,
        metadata_content_by_id=metadata_content_by_id,
    )


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _jaccard(sets: list[set]) -> float:
    """Minimum pairwise Jaccard similarity across all pairs in *sets*."""
    if len(sets) <= 1:
        return 1.0
    min_j = 1.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            a, b = sets[i], sets[j]
            union = len(a | b)
            inter = len(a & b)
            pair_j = inter / union if union > 0 else 1.0
            if pair_j < min_j:
                min_j = pair_j
    return round(min_j, 4)


def _detect_content_mutations(
    snapshots: list[RunSnapshot],
    content_attr: str,
    label: str,
) -> list[str]:
    """Return mutation detail strings for the given content-hash attribute."""
    details: list[str] = []
    sample_ids = list(getattr(snapshots[0], content_attr).keys())
    for cid in sample_ids:
        hashes = [
            getattr(s, content_attr).get(cid)
            for s in snapshots
            if cid in getattr(s, content_attr)
        ]
        unique = {h for h in hashes if h is not None}
        if len(unique) > 1:
            details.append(
                f"Complaint {cid}: {label} hash changed across runs — "
                f"{sorted(unique)}."
            )
    return details


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def compare_runs(run_entries: list[dict[str, Any]]) -> CrossRunComparison:
    """Compare N pipeline runs with full complaint-ID and mutation analysis."""
    if not run_entries:
        raise ValueError("compare_runs requires at least one run entry.")

    snapshots = [_load_run_snapshot(e) for e in run_entries]
    n = len(snapshots)
    run_ids = [s.run_id for s in snapshots]
    timestamps = [s.timestamp for s in snapshots]

    # ---- Count-level retrieval stability -----------------------------------
    candidate_counts = [s.candidate_count for s in snapshots]
    retrieval_stable = all(c > 0 for c in candidate_counts)
    if retrieval_stable:
        retrieval_note = (
            f"All {n} run(s) returned candidates (counts: {candidate_counts}). "
            "Note: count equality does not imply record-set equality; see "
            "complaint-ID overlap analysis below."
        )
    else:
        zero_runs = [run_ids[i] for i, c in enumerate(candidate_counts) if c == 0]
        retrieval_note = (
            f"{len(zero_runs)} run(s) returned 0 candidates: {zero_runs}. "
            "CFPB API may have returned an empty result set for that pull."
        )

    # ---- Complaint-ID overlap / equality -----------------------------------
    id_set_hashes = [s.complaint_id_set_hash for s in snapshots]
    complaint_ids_identical = len(set(id_set_hashes)) == 1

    id_sets = [set(s.complaint_ids) for s in snapshots]
    jaccard = _jaccard(id_sets) if all(len(s) > 0 for s in id_sets) else 0.0

    if complaint_ids_identical:
        id_overlap_note = (
            f"All {n} run(s) retrieved the exact same set of complaint IDs "
            f"(set-hash: {id_set_hashes[0][:12]}…). "
            "Record-set identity confirmed."
        )
    else:
        hashes_preview = [h[:12] + "…" for h in id_set_hashes]
        id_overlap_note = (
            f"Complaint ID sets differ across runs "
            f"(set-hashes: {hashes_preview}, Jaccard={jaccard:.4f}). "
            "The CFPB API does not guarantee a deterministic result set for repeated "
            "queries; record-set variation is expected between runs."
        )

    # ---- Ordering stability ------------------------------------------------
    complaint_ordering_hashes = [s.complaint_ordering_hash for s in snapshots]
    ordering_stable = len(set(complaint_ordering_hashes)) == 1
    ordering_note = (
        "Complaint ordering is identical across all runs."
        if ordering_stable else
        "Complaint ordering varies across runs. The CFPB API sort order "
        "is not guaranteed to be deterministic between requests."
    )

    # ---- Three-category mutation analysis ----------------------------------
    # Only meaningful when all runs retrieved the same complaint ID set.
    clf_mut_details: list[str] = []
    biz_mut_details: list[str] = []
    meta_mut_count = 0

    if complaint_ids_identical and n > 1:
        clf_mut_details = _detect_content_mutations(
            snapshots, "classification_content_by_id",
            "classification-input"
        )
        biz_mut_details = _detect_content_mutations(
            snapshots, "business_content_by_id",
            "stable-business-field"
        )
        meta_mut_count = len(_detect_content_mutations(
            snapshots, "metadata_content_by_id",
            "volatile-metadata"
        ))

    classification_mutation_detected = len(clf_mut_details) > 0
    business_mutation_detected = len(biz_mut_details) > 0
    metadata_differs = meta_mut_count > 0

    # Summary mutation (not metadata)
    mutation_details = clf_mut_details + biz_mut_details
    mutation_detected = classification_mutation_detected or business_mutation_detected

    if metadata_differs:
        metadata_differs_note = (
            f"{meta_mut_count} record(s) have volatile-metadata differences "
            f"(company_response, timely, date_sent_to_company, _retrieved_at, etc.). "
            "This is EXPECTED for live CFPB pulls — the CFPB database updates "
            "these administrative fields continuously. "
            "Volatile metadata is NOT included in mutation_detected or stability scoring."
        )
    else:
        metadata_differs_note = (
            "No volatile-metadata differences detected across runs."
        )

    # ---- Verdict / ceiling consistency -------------------------------------
    verdicts = [s.verdict for s in snapshots]
    verdict_consistent = len(set(verdicts)) == 1
    ceilings = [s.evidence_ceiling for s in snapshots]
    ceiling_consistent = len(set(ceilings)) == 1

    # ---- Proof gate consistency --------------------------------------------
    gate_status_by_run = [s.gate_statuses for s in snapshots]
    all_gate_ids = sorted({gid for s in snapshots for gid in s.gate_statuses})
    inconsistent_gates = [
        gid for gid in all_gate_ids
        if len({s.gate_statuses.get(gid, "MISSING") for s in snapshots}) > 1
    ]

    # ---- Mechanism distribution --------------------------------------------
    mechanism_sets = [set(s.mechanisms) for s in snapshots]
    common_mechs = sorted(set.intersection(*mechanism_sets)) if mechanism_sets else []
    any_mechs = sorted(set.union(*mechanism_sets)) if mechanism_sets else []
    mechanism_stable = len(common_mechs) == len(any_mechs) and bool(common_mechs)

    findings_per_run = [s.finding_count for s in snapshots]
    opps_per_run = [s.opportunity_count for s in snapshots]

    company_sets = [set(s.companies) for s in snapshots]
    common_companies = sorted(set.intersection(*company_sets)) if company_sets else []

    # ---- Overall stability -------------------------------------------------
    stability_notes: list[str] = []
    stability_issues = 0

    if not retrieval_stable:
        stability_notes.append("RETRIEVAL UNSTABLE: Some runs returned 0 candidates.")
        stability_issues += 2

    if not complaint_ids_identical:
        stability_notes.append(
            f"RECORD-SET VARIES: Jaccard={jaccard:.4f}. {id_overlap_note}"
        )
        stability_issues += 1

    if not ordering_stable:
        # Ordering variation alone is not a methodology failure; note only
        stability_notes.append(f"ORDERING VARIES: {ordering_note}")

    # Classification mutations ARE a pipeline-impact stability issue
    if classification_mutation_detected:
        stability_notes.append(
            f"CLASSIFICATION-INPUT MUTATION: {len(clf_mut_details)} record(s) have "
            "changed classification-input fields (complaint_what_happened, product, "
            "issue, sub_product, sub_issue) between runs. "
            "Pipeline outputs MAY differ if reprocessed from these records."
        )
        stability_issues += 3

    # Business mutations are unexpected but not pipeline-impacting
    if business_mutation_detected:
        stability_notes.append(
            f"BUSINESS-FIELD MUTATION: {len(biz_mut_details)} record(s) have "
            "changed stable-business fields (company, state, zip_code, etc.) "
            "between runs. Unexpected but does not affect classification outputs."
        )
        stability_issues += 1

    # Metadata differences are purely informational — NOT a stability issue
    if metadata_differs:
        stability_notes.append(
            f"METADATA DIFFERENCES (INFO — not a stability issue): "
            f"{meta_mut_count} record(s) have volatile-metadata changes "
            "(company_response, timely, date_sent_to_company, _retrieved_at). "
            "Expected for live CFPB pulls. Does not affect pipeline outputs."
        )

    if not verdict_consistent:
        stability_notes.append(
            f"VERDICT VARIES: {set(verdicts)}. "
            "Expected if some runs returned 0 candidates (→ REJECT)."
        )
        stability_issues += 1

    if not ceiling_consistent:
        stability_notes.append(
            f"CEILING INCONSISTENCY: {set(ceilings)}. "
            "Evidence ceiling must always be CONTINUE RESEARCH for CFPB-only data."
        )
        stability_issues += 3

    if inconsistent_gates:
        stability_notes.append(
            f"GATE STATUS VARIATION: {inconsistent_gates}. "
            "Data-dependent gates may vary if different records are retrieved."
        )
        stability_issues += 1

    if not mechanism_stable and any_mechs:
        stability_notes.append(
            f"MECHANISM VARIATION: common={common_mechs}, any={any_mechs}."
        )
        stability_issues += 1

    if ceiling_consistent and all(c == "CONTINUE RESEARCH" for c in ceilings):
        stability_notes.append(
            "CEILING ENFORCED: CONTINUE RESEARCH in all runs — correct for "
            "single source family."
        )

    if not stability_notes:
        stability_notes.append("All key metrics are consistent across all runs.")

    if stability_issues == 0:
        overall_stability = "stable"
    elif stability_issues <= 2:
        overall_stability = "partially_stable"
    else:
        overall_stability = "unstable"

    return CrossRunComparison(
        run_count=n,
        run_ids=run_ids,
        timestamps=timestamps,
        candidate_counts=candidate_counts,
        retrieval_stable=retrieval_stable,
        retrieval_note=retrieval_note,
        id_set_hashes=id_set_hashes,
        complaint_ids_identical=complaint_ids_identical,
        jaccard_similarity=jaccard,
        id_overlap_note=id_overlap_note,
        complaint_ordering_hashes=complaint_ordering_hashes,
        ordering_stable=ordering_stable,
        ordering_note=ordering_note,
        classification_mutation_detected=classification_mutation_detected,
        classification_mutation_details=clf_mut_details,
        business_mutation_detected=business_mutation_detected,
        business_mutation_details=biz_mut_details,
        metadata_differs=metadata_differs,
        metadata_differs_count=meta_mut_count,
        metadata_differs_note=metadata_differs_note,
        mutation_detected=mutation_detected,
        mutation_details=mutation_details,
        verdicts=verdicts,
        verdict_consistent=verdict_consistent,
        evidence_ceilings=ceilings,
        ceiling_consistent=ceiling_consistent,
        gate_status_by_run=gate_status_by_run,
        inconsistent_gates=inconsistent_gates,
        mechanisms_per_run=[s.mechanisms for s in snapshots],
        common_mechanisms=common_mechs,
        any_run_mechanisms=any_mechs,
        mechanism_stable=mechanism_stable,
        findings_per_run=findings_per_run,
        opportunities_per_run=opps_per_run,
        companies_per_run=[s.companies for s in snapshots],
        common_companies=common_companies,
        overall_stability=overall_stability,
        stability_notes=stability_notes,
    )


def load_and_compare_last_n_runs(
    n: int,
    run_index_path: str | Path = "data/exports/run_index.json",
) -> CrossRunComparison:
    all_entries = read_run_index(run_index_path)
    if not all_entries:
        raise ValueError(f"Run index is empty: {run_index_path}")
    entries = all_entries[-n:] if len(all_entries) >= n else all_entries
    return compare_runs(entries)


def write_cross_run_report(comparison: CrossRunComparison, path: str | Path) -> str:
    lines: list[str] = []
    lines.append("# Cross-Run Comparison Report")
    lines.append("")
    lines.append(f"**Runs compared:** {comparison.run_count}  ")
    lines.append(f"**Overall stability:** **{comparison.overall_stability}**  ")
    lines.append("")

    lines.append("## Run IDs and timestamps")
    lines.append("")
    lines.append("| # | Run ID | Timestamp | Verdict | Ceiling |")
    lines.append("|---|---|---|---|---|")
    for i, (rid, ts, v, c) in enumerate(zip(
        comparison.run_ids, comparison.timestamps,
        comparison.verdicts, comparison.evidence_ceilings,
    ), 1):
        lines.append(f"| {i} | `{rid}` | `{ts}` | {v} | {c} |")
    lines.append("")

    lines.append("## Retrieval — count level")
    lines.append("")
    lines.append("| Run # | Candidates |")
    lines.append("|---|---|")
    for i, c in enumerate(comparison.candidate_counts, 1):
        lines.append(f"| {i} | {c} |")
    lines.append("")
    lines.append(f"**Retrieval stable (all > 0):** {comparison.retrieval_stable}  ")
    lines.append(f"> {comparison.retrieval_note}")
    lines.append("")

    lines.append("## Complaint-ID overlap and equality")
    lines.append("")
    lines.append("| Run # | ID-set hash (first 12) | Ordering hash (first 12) |")
    lines.append("|---|---|---|")
    for i, (sh, oh) in enumerate(zip(
        comparison.id_set_hashes, comparison.complaint_ordering_hashes
    ), 1):
        lines.append(f"| {i} | `{sh[:12]}…` | `{oh[:12]}…` |")
    lines.append("")
    lines.append(f"**Complaint IDs identical across all runs:** {comparison.complaint_ids_identical}  ")
    lines.append(f"**Jaccard similarity (min pairwise):** {comparison.jaccard_similarity:.4f}  ")
    lines.append(f"**Ordering stable:** {comparison.ordering_stable}  ")
    lines.append("")
    lines.append(f"> **ID overlap:** {comparison.id_overlap_note}")
    lines.append(f"> **Ordering:** {comparison.ordering_note}")
    lines.append("")

    lines.append("## Source mutation analysis (three-category breakdown)")
    lines.append("")
    lines.append(
        "Mutation is split into three named categories. Only classification-input "
        "mutations affect pipeline outputs. Volatile metadata differences are "
        "expected for live CFPB pulls and are never counted as a stability issue."
    )
    lines.append("")

    # Category 1: Classification inputs
    clf_icon = "🔴 DETECTED" if comparison.classification_mutation_detected else "✅ NONE"
    lines.append(f"### 1. Classification-input mutation — {clf_icon}")
    lines.append("")
    lines.append(
        "Fields: `complaint_what_happened`, `product`, `sub_product`, `issue`, `sub_issue`  "
    )
    lines.append("Impact: **can alter mechanism assignment, operational flag, ODR outcome**  ")
    lines.append(f"Detected: **{comparison.classification_mutation_detected}**  ")
    if comparison.classification_mutation_details:
        lines.append("")
        lines.append(f"({len(comparison.classification_mutation_details)} record(s) affected)")
        for m in comparison.classification_mutation_details[:10]:
            lines.append(f"- {m}")
        if len(comparison.classification_mutation_details) > 10:
            lines.append(
                f"- … and {len(comparison.classification_mutation_details) - 10} more"
            )
    lines.append("")

    # Category 2: Stable business fields
    biz_icon = "⚠️ DETECTED" if comparison.business_mutation_detected else "✅ NONE"
    lines.append(f"### 2. Stable-business-field mutation — {biz_icon}")
    lines.append("")
    lines.append(
        "Fields: `company`, `state`, `zip_code`, `tags`, `submitted_via`, "
        "`has_narrative`, `date_received`, `complaint_id`  "
    )
    lines.append("Impact: **unexpected; does not affect classification outputs**  ")
    lines.append(f"Detected: **{comparison.business_mutation_detected}**  ")
    if comparison.business_mutation_details:
        lines.append("")
        for m in comparison.business_mutation_details[:10]:
            lines.append(f"- {m}")
        if len(comparison.business_mutation_details) > 10:
            lines.append(
                f"- … and {len(comparison.business_mutation_details) - 10} more"
            )
    lines.append("")

    # Category 3: Volatile metadata
    meta_icon = "ℹ️ YES (expected)" if comparison.metadata_differs else "✅ NONE"
    lines.append(f"### 3. Volatile-metadata differences — {meta_icon}")
    lines.append("")
    lines.append(
        "Fields: `company_response`, `timely`, `date_sent_to_company`, "
        "`company_public_response`, `_retrieved_at`, `_retrieval_url`, "
        "`_access_method`, `_source_name`  "
    )
    lines.append(
        "Impact: **none — these fields are not read by the classifier; "
        "differences are expected for live CFPB pulls**  "
    )
    lines.append(
        f"Records with metadata differences: **{comparison.metadata_differs_count}**  "
    )
    lines.append(f"> {comparison.metadata_differs_note}")
    lines.append("")

    lines.append("## Verdict and Evidence Ceiling")
    lines.append("")
    lines.append(f"- Verdict consistent: **{comparison.verdict_consistent}** ({set(comparison.verdicts)})")
    lines.append(f"- Ceiling consistent: **{comparison.ceiling_consistent}** ({set(comparison.evidence_ceilings)})")
    lines.append("")

    lines.append("## Mechanism distribution")
    lines.append("")
    lines.append(f"- Common to all runs: {comparison.common_mechanisms or '(none)'}")
    lines.append(f"- Present in any run: {comparison.any_run_mechanisms or '(none)'}")
    lines.append(f"- Mechanism stable: **{comparison.mechanism_stable}**")
    lines.append("")
    for i, mechs in enumerate(comparison.mechanisms_per_run, 1):
        lines.append(f"- Run {i}: {mechs or ['(none)']}")
    lines.append("")

    lines.append("## Findings and opportunities")
    lines.append("")
    lines.append("| Run # | Findings | Opportunities |")
    lines.append("|---|---|---|")
    for i, (f, o) in enumerate(zip(comparison.findings_per_run, comparison.opportunities_per_run), 1):
        lines.append(f"| {i} | {f} | {o} |")
    lines.append("")

    lines.append("## Proof gate consistency")
    lines.append("")
    if comparison.inconsistent_gates:
        lines.append(f"Gates with status variation: {comparison.inconsistent_gates}  ")
        lines.append(
            "Note: data-dependent gates (PG-03–PG-14) may vary across runs. "
            "PG-15 and PG-16 must remain constant."
        )
    else:
        lines.append("All gate statuses are consistent across all runs.")
    lines.append("")

    lines.append("## Stability notes")
    lines.append("")
    for note in comparison.stability_notes:
        lines.append(f"- {note}")
    lines.append("")

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)
