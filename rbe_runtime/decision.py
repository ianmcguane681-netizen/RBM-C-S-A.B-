"""Pure, profile-driven decision evaluation for RBM-001."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from itertools import product
from typing import Any

from rbe_runtime.canonical import canonical_hash
from rbe_runtime.constants import ENGINE_VERSION
from rbe_runtime.errors import RBEError
from rbe_runtime.models import DecisionEvaluation, Finding


_BOOLEAN_TOKEN = re.compile(r"\b(true|false)\b", re.IGNORECASE)
_CONTEXT_FIELDS = frozenset(
    {
        "unresolved_sev1",
        "unresolved_sev2",
        "accepted_sev2_remediation",
        "substantive_evidence_sufficient",
    }
)


def _normalize_boolean_tokens(expression: str) -> str:
    return _BOOLEAN_TOKEN.sub(
        lambda match: "True" if match.group(1).lower() == "true" else "False",
        expression,
    )


@dataclass(frozen=True, slots=True)
class CompiledRule:
    priority: int
    rule_id: str
    condition: str
    outcome: str
    expression: ast.Expression

    def matches(self, context: dict[str, int | bool]) -> bool:
        return bool(_evaluate_node(self.expression.body, context))


def _evaluate_node(node: ast.AST, context: dict[str, int | bool]) -> int | bool:
    if isinstance(node, ast.Name):
        if node.id not in _CONTEXT_FIELDS:
            raise RBEError(
                "RBE_UNKNOWN_RULE_INPUT",
                f"Decision rule references unknown input {node.id}",
                "RBE-ES-DEC-004",
            )
        return context[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int)):
        return node.value
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        values = [bool(_evaluate_node(value, context)) for value in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not bool(_evaluate_node(node.operand, context))
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        left = _evaluate_node(node.left, context)
        right = _evaluate_node(node.comparators[0], context)
        operator = node.ops[0]
        if isinstance(operator, ast.Eq):
            return left == right
        if isinstance(operator, ast.NotEq):
            return left != right
        if isinstance(operator, ast.Gt):
            return left > right
        if isinstance(operator, ast.GtE):
            return left >= right
        if isinstance(operator, ast.Lt):
            return left < right
        if isinstance(operator, ast.LtE):
            return left <= right
    raise RBEError(
        "RBE_UNSAFE_DECISION_EXPRESSION",
        f"Unsupported syntax in methodology condition: {type(node).__name__}",
        "RBE-ES-DEC-003",
    )


class DecisionEngine:
    """Evaluate normalized finding snapshots without side effects."""

    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile
        self.rules = self._compile_rules(profile)
        self._validate_total_coverage()

    @staticmethod
    def _compile_rules(profile: dict[str, Any]) -> tuple[CompiledRule, ...]:
        raw_rules = profile.get("decision_precedence")
        if not isinstance(raw_rules, list) or not raw_rules:
            raise RBEError(
                "RBE_DECISION_RULES_MISSING",
                "Methodology profile has no decision precedence rules",
                "RBE-ES-DEC-003",
            )
        permitted = set(profile.get("permitted_outcomes", []))
        compiled: list[CompiledRule] = []
        for raw in raw_rules:
            try:
                expression = ast.parse(
                    _normalize_boolean_tokens(raw["condition"]), mode="eval"
                )
                rule = CompiledRule(
                    priority=int(raw["priority"]),
                    rule_id=str(raw["rule_id"]),
                    condition=str(raw["condition"]),
                    outcome=str(raw["outcome"]),
                    expression=expression,
                )
                _evaluate_node(
                    expression.body,
                    {
                        "unresolved_sev1": 0,
                        "unresolved_sev2": 0,
                        "accepted_sev2_remediation": 0,
                        "substantive_evidence_sufficient": True,
                    },
                )
            except (KeyError, SyntaxError, TypeError, ValueError) as exc:
                raise RBEError(
                    "RBE_DECISION_RULE_INVALID",
                    "A methodology decision rule is malformed",
                    "RBE-ES-DEC-003",
                ) from exc
            if rule.outcome not in permitted:
                raise RBEError(
                    "RBE_DECISION_OUTCOME_NOT_PERMITTED",
                    f"Rule {rule.rule_id} emits an outcome outside the profile",
                    "RBE-ES-DEC-004",
                )
            compiled.append(rule)
        compiled.sort(key=lambda item: item.priority)
        priorities = [item.priority for item in compiled]
        rule_ids = [item.rule_id for item in compiled]
        if len(priorities) != len(set(priorities)) or len(rule_ids) != len(set(rule_ids)):
            raise RBEError(
                "RBE_DECISION_PRECEDENCE_AMBIGUOUS",
                "Decision priorities and rule IDs must be unique",
                "RBE-ES-DEC-003",
            )
        return tuple(compiled)

    def _validate_total_coverage(self) -> None:
        # Boundary values cover all branches in RBM's threshold rules.
        for sev1, sev2, sufficient in product(range(3), range(4), (False, True)):
            for accepted in range(sev2 + 1):
                context: dict[str, int | bool] = {
                    "unresolved_sev1": sev1,
                    "unresolved_sev2": sev2,
                    "accepted_sev2_remediation": accepted,
                    "substantive_evidence_sufficient": sufficient,
                }
                if not any(rule.matches(context) for rule in self.rules):
                    raise RBEError(
                        "RBE_DECISION_RULES_NOT_TOTAL",
                        "Methodology rules do not cover every valid decision input",
                        "RBE-ES-DEC-003",
                        {"uncovered_context": context},
                    )

    def evaluate(
        self,
        *,
        findings: tuple[Finding, ...],
        process_status: str,
        substantive_evidence_sufficient: bool,
        accepted_remediation_finding_ids: tuple[str, ...] = (),
        counter_evidence: tuple[str, ...] = (),
        process_blockers: tuple[str, ...] = (),
    ) -> DecisionEvaluation:
        if process_status not in self.profile["process_statuses"]:
            raise RBEError(
                "RBE_UNKNOWN_PROCESS_STATUS",
                f"Unknown methodology process status: {process_status}",
                "RBE-ES-DEC-004",
            )
        if process_status == "READY" and process_blockers:
            raise RBEError(
                "RBE_READY_PROCESS_HAS_BLOCKERS",
                "A READY decision snapshot cannot contain process blockers",
                "RBE-ES-DEC-004",
            )
        unresolved_statuses = set(self.profile["unresolved_finding_statuses"])
        normalized_findings = tuple(
            sorted(
                (
                    {
                        "finding_id": finding.finding_id,
                        "severity": finding.severity,
                        "category": finding.category,
                        "status": finding.status,
                        "remediation_required": finding.remediation_required,
                        "source_report_id": finding.source_report_id,
                        "raw_record_sha256": finding.raw_record_sha256,
                    }
                    for finding in findings
                ),
                key=lambda item: (
                    item["severity"],
                    item["category"],
                    item["finding_id"],
                ),
            )
        )
        unresolved = [
            item for item in normalized_findings if item["status"] in unresolved_statuses
        ]
        known_finding_ids = {item["finding_id"] for item in normalized_findings}
        unknown_remediation = sorted(
            set(accepted_remediation_finding_ids) - known_finding_ids
        )
        if unknown_remediation:
            raise RBEError(
                "RBE_UNKNOWN_REMEDIATED_FINDING",
                "Accepted remediation references an unknown finding",
                "RBE-ES-DOM-002",
                {"finding_ids": unknown_remediation},
            )
        accepted_remediation = set(accepted_remediation_finding_ids)
        context: dict[str, int | bool] = {
            "unresolved_sev1": sum(
                item["severity"] == "SEV-1" for item in unresolved
            ),
            "unresolved_sev2": sum(
                item["severity"] == "SEV-2" for item in unresolved
            ),
            "accepted_sev2_remediation": sum(
                item["severity"] == "SEV-2"
                and item["finding_id"] in accepted_remediation
                for item in unresolved
            ),
            "substantive_evidence_sufficient": substantive_evidence_sufficient,
        }
        snapshot = {
            "profile_id": self.profile["profile_id"],
            "profile_version": self.profile["version"],
            "profile_checksum": self.profile["checksum"],
            "process_status": process_status,
            "decision_inputs": context,
            "findings": normalized_findings,
            "accepted_remediation_finding_ids": sorted(accepted_remediation),
            "counter_evidence": sorted(counter_evidence),
            "process_blockers": sorted(process_blockers),
        }
        snapshot_hash = canonical_hash(snapshot)
        finding_ids = tuple(item["finding_id"] for item in normalized_findings)
        if process_status != "READY":
            return DecisionEvaluation(
                process_status=process_status,
                outcome=None,
                reason_codes=(
                    tuple(sorted(process_blockers))
                    or (f"PROCESS_{process_status}",)
                ),
                rules_applied=("RBE_PROCESS_STATUS_GATE",),
                findings_considered=finding_ids,
                counter_evidence=tuple(sorted(counter_evidence)),
                process_blockers=tuple(sorted(process_blockers)),
                profile_id=self.profile["profile_id"],
                profile_version=self.profile["version"],
                profile_checksum=self.profile["checksum"],
                engine_version=ENGINE_VERSION,
                snapshot_hash=snapshot_hash,
                explanation=(
                    f"Process status is {process_status}; the canonical taxonomy "
                    "therefore permits no substantive outcome."
                ),
            )

        applied: list[str] = []
        selected: CompiledRule | None = None
        for rule in self.rules:
            applied.append(rule.rule_id)
            if rule.matches(context):
                selected = rule
                break
        if selected is None:
            raise RBEError(
                "RBE_DECISION_RULES_NOT_TOTAL",
                "No methodology rule matched a valid decision snapshot",
                "RBE-ES-DEC-003",
                {"context": context},
            )
        return DecisionEvaluation(
            process_status=process_status,
            outcome=selected.outcome,
            reason_codes=(selected.rule_id,),
            rules_applied=tuple(applied),
            findings_considered=finding_ids,
            counter_evidence=tuple(sorted(counter_evidence)),
            process_blockers=tuple(sorted(process_blockers)),
            profile_id=self.profile["profile_id"],
            profile_version=self.profile["version"],
            profile_checksum=self.profile["checksum"],
            engine_version=ENGINE_VERSION,
            snapshot_hash=snapshot_hash,
            explanation=(
                f"{selected.outcome} was selected by {selected.rule_id} from the "
                "frozen finding counts and substantive-evidence assessment."
            ),
        )
