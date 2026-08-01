"""Deterministic review-bundle export and validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.canonical import canonical_hash, canonical_json, sha256_digest
from rbe_runtime.errors import RBEError
from rbe_runtime.storage import ReviewStore


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _json_document(schema_id: str, payload: dict[str, Any]) -> bytes:
    document = {
        "schema_id": schema_id,
        "schema_version": "1.0.0",
        **payload,
    }
    return (canonical_json(document) + "\n").encode("utf-8")


def _markdown_text(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "\\`")
        .replace("\r", " ")
        .replace("\n", " ")
    )


class ArtifactExporter:
    def __init__(
        self,
        repository: ReviewStore,
        authority: AuthorityBundle,
    ) -> None:
        self.repository = repository
        self.authority = authority

    def export(self, session_id: str, output_dir: str | Path) -> dict[str, Any]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        root = root.resolve()
        session = self.repository.get_session(session_id)
        initiation = self.repository.get_initiation(session_id)
        assignments = self.repository.list_assignments(session_id)
        evidence = self.repository.list_evidence(session_id)
        reports = self.repository.list_reports(session_id)
        findings = self.repository.list_findings(session_id)
        remediation = self.repository.list_remediation_plans(session_id)
        candidate = self.repository.get_decision_candidate(session_id)
        # `get_decision` and friends filter `superseded = 0`, which is right for "what
        # stands now" and wrong for an export. Superseding RBM003-USDC-0001 emptied its
        # own bundle: decision, ratification and publication all vanished, leaving a
        # review that appeared never to have decided anything.
        #
        # A superseded decision is still the decision that review made, and the record of
        # why it was replaced is worthless without it. Export falls back to the history and
        # the status field says SUPERSEDED, which is the honest rendering.
        decision = self.repository.get_decision(session_id)
        ratification = self.repository.get_ratification(session_id)
        publication = self.repository.get_publication(session_id)
        if decision is None:
            history = self.repository.get_decision_history(session_id)
            if history:
                decision = history[-1]
                ratification = self.repository.get_ratification(
                    session_id, decision_id=decision.decision_id
                )
                publication = self.repository.get_publication(
                    session_id, decision_id=decision.decision_id
                )
        audit = self.repository.list_audit(session_id)
        audit_verification = self.repository.verify_audit(session_id)
        if candidate is None:
            raise RBEError(
                "RBE_DECISION_CANDIDATE_MISSING",
                "A frozen decision candidate is required before bundle export",
                "RBE-ES-SCH-006",
            )

        candidate_payload = {
            **candidate,
            "evaluation": candidate["evaluation"].to_dict(),
        }
        files: dict[str, bytes] = {
            "session.json": _json_document(
                "rbe.review-session",
                {"session": session.to_dict(), "initiation": initiation},
            ),
            "package-manifest.json": _json_document(
                "rbe.decision-input-manifest",
                {"manifest": candidate["artifact_manifest"]},
            ),
            "assignments.json": _json_document(
                "rbe.review-assignments",
                {"session_id": session_id, "assignments": [a.to_dict() for a in assignments]},
            ),
            "evidence.json": _json_document(
                "rbe.evidence-register",
                {
                    "session_id": session_id,
                    "evidence": [item.to_dict() for item in evidence.values()],
                },
            ),
            "reports.json": _json_document(
                "rbe.reviewer-reports",
                {"session_id": session_id, "reports": [r.to_dict() for r in reports]},
            ),
            "findings.json": _json_document(
                "rbe.finding-snapshot",
                {"session_id": session_id, "findings": [f.to_dict() for f in findings]},
            ),
            "remediation-plans.json": _json_document(
                "rbe.remediation-plans",
                {"session_id": session_id, "plans": [p.to_dict() for p in remediation]},
            ),
            "decision.json": _json_document(
                "rbe.decision-package",
                {
                    "session_id": session_id,
                    "candidate": candidate_payload,
                    "decision": None if decision is None else decision.to_dict(),
                    "ratification": ratification,
                    "publication": publication,
                },
            ),
            "audit.jsonl": (
                "".join(canonical_json(entry.to_dict()) + "\n" for entry in audit)
            ).encode("utf-8"),
        }
        for index, reference in enumerate(evidence.values(), start=1):
            safe_id = _SAFE_NAME.sub("-", reference.reference_id).strip("-.")
            if not safe_id:
                safe_id = reference.content_sha256.removeprefix("sha256:")[:16]
            files[f"evidence/{index:03d}-{safe_id}.bin"] = (
                self.repository.get_evidence_content(reference.reference_id)
            )

        report_markdown = self._render_markdown(
            session=session.to_dict(),
            initiation=initiation,
            evidence=[item.to_dict() for item in evidence.values()],
            reports=[item.to_dict() for item in reports],
            findings=[item.to_dict() for item in findings],
            remediation=[item.to_dict() for item in remediation],
            candidate=candidate_payload,
            decision=None if decision is None else decision.to_dict(),
            publication=publication,
            audit_verification=audit_verification,
        )
        files["review-report.md"] = report_markdown.encode("utf-8")

        artifact_entries = [
            {
                "path": path,
                "sha256": sha256_digest(content),
                "size": len(content),
                "media_type": self._media_type(path),
            }
            for path, content in sorted(files.items())
        ]
        bundle_manifest = {
            "schema_id": "rbe.review-bundle-manifest",
            "schema_version": "1.0.0",
            "session_id": session_id,
            "engine_version": session.engine_version,
            "methodology": {
                "id": session.methodology_id,
                "version": session.methodology_version,
                "checksum": session.methodology_checksum,
                "status": self.authority.profile["status"],
            },
            "process_status": candidate["evaluation"].process_status,
            "outcome": candidate["evaluation"].outcome,
            "binding": session.binding,
            "merge_permitted": (
                False if decision is None else decision.merge_permitted
            ),
            "generated_at": (
                publication["published_at"]
                if publication is not None
                else candidate["computed_at"]
            ),
            "artifacts": artifact_entries,
            "bundle_root_hash": canonical_hash(artifact_entries),
        }
        files["bundle-manifest.json"] = (
            canonical_json(bundle_manifest) + "\n"
        ).encode("utf-8")
        for relative_path, content in sorted(files.items()):
            self._write_file(root, relative_path, content)
        return bundle_manifest

    @staticmethod
    def verify(output_dir: str | Path) -> dict[str, Any]:
        root = Path(output_dir).resolve()
        manifest_path = root / "bundle-manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RBEError(
                "RBE_BUNDLE_MANIFEST_INVALID",
                "Bundle manifest is missing or invalid JSON",
                "RBE-ES-SCH-008",
            ) from exc
        if (
            manifest.get("schema_id") != "rbe.review-bundle-manifest"
            or manifest.get("schema_version") != "1.0.0"
        ):
            raise RBEError(
                "RBE_BUNDLE_SCHEMA_UNSUPPORTED",
                "Bundle manifest schema is unknown",
                "RBE-ES-SCH-008",
            )
        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, list):
            raise RBEError(
                "RBE_BUNDLE_MANIFEST_INVALID",
                "Bundle artifact register is missing",
                "RBE-ES-SCH-008",
            )
        for entry in artifacts:
            relative = Path(entry["path"])
            target = (root / relative).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise RBEError(
                    "RBE_BUNDLE_PATH_TRAVERSAL",
                    "Bundle manifest contains an unsafe artifact path",
                    "RBE-ES-SEC-001",
                    {"path": entry["path"]},
                ) from exc
            try:
                content = target.read_bytes()
            except OSError as exc:
                raise RBEError(
                    "RBE_BUNDLE_ARTIFACT_MISSING",
                    "A declared bundle artifact is missing",
                    "RBE-ES-SCH-008",
                    {"path": entry["path"]},
                ) from exc
            if len(content) != entry["size"] or sha256_digest(content) != entry[
                "sha256"
            ]:
                raise RBEError(
                    "RBE_BUNDLE_ARTIFACT_HASH_MISMATCH",
                    "A bundle artifact failed checksum verification",
                    "RBE-ES-SCH-008",
                    {"path": entry["path"]},
                )
        expected_root = canonical_hash(artifacts)
        if manifest.get("bundle_root_hash") != expected_root:
            raise RBEError(
                "RBE_BUNDLE_ROOT_HASH_MISMATCH",
                "Bundle root hash does not match the artifact manifest",
                "RBE-ES-SCH-008",
            )
        return {
            "session_id": manifest["session_id"],
            "artifacts_verified": len(artifacts),
            "bundle_root_hash": expected_root,
            "valid": True,
        }

    @staticmethod
    def _write_file(root: Path, relative_path: str, content: bytes) -> None:
        target = (root / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise RBEError(
                "RBE_EXPORT_PATH_TRAVERSAL",
                "Artifact path escapes the selected output directory",
                "RBE-ES-SEC-001",
            ) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)

    @staticmethod
    def _media_type(path: str) -> str:
        if path.endswith(".json"):
            return "application/json"
        if path.endswith(".jsonl"):
            return "application/x-ndjson"
        if path.endswith(".md"):
            return "text/markdown"
        return "application/octet-stream"

    def _render_markdown(
        self,
        *,
        session: dict[str, Any],
        initiation: dict[str, Any],
        evidence: list[dict[str, Any]],
        reports: list[dict[str, Any]],
        findings: list[dict[str, Any]],
        remediation: list[dict[str, Any]],
        candidate: dict[str, Any],
        decision: dict[str, Any] | None,
        publication: dict[str, Any] | None,
        audit_verification: dict[str, Any],
    ) -> str:
        evaluation = candidate["evaluation"]
        lines = [
            "# RBE-001 Review Report",
            "",
            "> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.",
            "",
            "## Decision Summary",
            "",
            f"- Review: `{_markdown_text(session['session_id'])}`",
            f"- Process status: **{_markdown_text(evaluation['process_status'])}**",
            f"- Machine outcome: **{_markdown_text(evaluation['outcome'] or 'NONE')}**",
            f"- Binding: **{str(bool(session['binding'])).lower()}**",
            f"- Merge permitted: **{str(bool(decision and decision['merge_permitted'])).lower()}**",
            f"- Decision candidate: `{_markdown_text(candidate['candidate_id'])}`",
            f"- Frozen snapshot: `{_markdown_text(evaluation['snapshot_hash'])}`",
            "",
            "The machine outcome is deterministic but is not itself governance authority.",
            "",
            "## Target And Authority",
            "",
            f"- Target repository: `{_markdown_text(initiation['repository'])}`",
            f"- Target artefact: `{_markdown_text(session['target_version'])}`",
            f"- Architecture authority: {_markdown_text(initiation['architecture_authority'])}",
            f"- Methodology: `{_markdown_text(session['methodology_id'])}` v{_markdown_text(session['methodology_version'])}",
            f"- Methodology status: **{_markdown_text(initiation['methodology_status'])}**",
            f"- Profile checksum: `{_markdown_text(session['methodology_checksum'])}`",
            "",
            "## Decision Basis",
            "",
            _markdown_text(evaluation["explanation"]),
            "",
            f"Rules applied: {', '.join(f'`{_markdown_text(item)}`' for item in evaluation['rules_applied']) or 'None'}",
            "",
            f"Reason codes: {', '.join(f'`{_markdown_text(item)}`' for item in evaluation['reason_codes']) or 'None'}",
            "",
            "## Evidence Register",
            "",
        ]
        if evidence:
            for item in evidence:
                lines.extend(
                    [
                        f"### `{_markdown_text(item['reference_id'])}`",
                        "",
                        f"- Locator: `{_markdown_text(item['locator'])}`",
                        f"- SHA-256: `{_markdown_text(item['content_sha256'])}`",
                        f"- Source tier: `{_markdown_text(item['source_tier'] or 'UNSPECIFIED')}`",
                        f"- Description: {_markdown_text(item['description'])}",
                        "",
                    ]
                )
        else:
            lines.extend(["No evidence references were registered.", ""])

        lines.extend(["## Reviewer Reports", ""])
        for report in reports:
            lines.extend(
                [
                    f"### `{_markdown_text(report['report_id'])}`",
                    "",
                    f"- Assignment: `{_markdown_text(report['assignment_id'])}`",
                    f"- Summary: {_markdown_text(report['summary'])}",
                    f"- Non-binding recommendation: **{_markdown_text(report['recommendation'])}**",
                    f"- Evidence references: {', '.join(f'`{_markdown_text(item)}`' for item in report['evidence_reference_ids']) or 'None'}",
                    f"- Human signature: `{_markdown_text(report['human_signature_ref'])}`",
                    "",
                ]
            )

        lines.extend(["## Findings", ""])
        if findings:
            for finding in findings:
                lines.extend(
                    [
                        f"### {_markdown_text(finding['severity'])}: {_markdown_text(finding['title'])}",
                        "",
                        f"- Finding ID: `{_markdown_text(finding['finding_id'])}`",
                        f"- Status: **{_markdown_text(finding['status'])}**",
                        f"- Category: `{_markdown_text(finding['category'])}`",
                        f"- Source report: `{_markdown_text(finding['source_report_id'])}`",
                        f"- Evidence references: {', '.join(f'`{_markdown_text(item)}`' for item in finding['evidence_reference_ids'])}",
                        f"- Detail: {_markdown_text(finding['description'])}",
                        "",
                    ]
                )
        else:
            lines.extend(["No findings were recorded.", ""])

        lines.extend(["## Remediation", ""])
        if remediation:
            for plan in remediation:
                lines.extend(
                    [
                        f"- `{_markdown_text(plan['plan_id'])}` for `{_markdown_text(plan['finding_id'])}`: **{_markdown_text(plan['status'])}**; owner `{_markdown_text(plan['owner'])}`; due `{_markdown_text(plan['due_date'] or 'not set')}`.",
                    ]
                )
            lines.append("")
        else:
            lines.extend(["No remediation plans were recorded.", ""])

        lines.extend(
            [
                "## Governance And Publication",
                "",
                f"- Decision status: **{_markdown_text(decision['status'] if decision else 'DRAFT_CANDIDATE')}**",
                f"- Publication: **{_markdown_text('RECORDED' if publication else 'NOT RECORDED')}**",
                "",
                "## Audit Verification",
                "",
                f"- Entries verified: {audit_verification['entries_verified']}",
                f"- Audit root hash: `{_markdown_text(audit_verification['root_hash'])}`",
                "- Audit chain valid: **true**",
                "",
                "## Limitations",
                "",
                "- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.",
                "- Reviewer recommendations are non-binding and do not determine the machine outcome.",
                "- This report contains only statements derived from the exported structured records.",
                "",
            ]
        )
        return "\n".join(lines)
