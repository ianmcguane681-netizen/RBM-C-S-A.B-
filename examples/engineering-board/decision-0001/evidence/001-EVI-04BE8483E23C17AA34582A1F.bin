from __future__ import annotations

from typing import Any

from core.ids import stable_id, utc_now
from core.models import AnalysisArtifact


AI_DISABLED_METHOD = "deterministic_rules_no_ai"
AI_INSTRUCTION_VERSION = "AI-GOV-001"


def deterministic_analysis_artifact(
    input_evidence_ids: list[str],
    output: dict[str, Any],
    affected_finding_or_verdict: bool,
) -> AnalysisArtifact:
    return AnalysisArtifact(
        artifact_id=stable_id("ANL", {"inputs": input_evidence_ids, "output": output, "method": AI_DISABLED_METHOD}),
        method_used=AI_DISABLED_METHOD,
        instruction_version=AI_INSTRUCTION_VERSION,
        timestamp=utc_now(),
        input_evidence_ids=input_evidence_ids,
        output=output,
        confidence=1.0,
        known_limitations=["No AI interpretation was used in this run."],
        validation_status="rule_validated",
        affected_finding_or_verdict=affected_finding_or_verdict,
    )
