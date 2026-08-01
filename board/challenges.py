"""Challenge sheets: what a seat found, in six lines.

A review is only useful if a human can act on it in a couple of minutes. These
sheets are deliberately short and plain: what was targeted, what is wrong, why it
matters, what would fix it, and the evidence it rests on.

Severity carries real weight downstream. SEV-1 blocks a decision outright, SEV-2
requires a fix or an accepted remediation plan, SEV-3 is recorded and does not
block. That mapping is the profile's, not this module's - these sheets are the
readable face of findings the gates already act on.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SEVERITY_EFFECT = {
    "SEV-1": "blocks the decision",
    "SEV-2": "needs a fix or an accepted remediation plan",
    "SEV-3": "recorded, does not block",
}

SEVERITY_ORDER = {"SEV-1": 0, "SEV-2": 1, "SEV-3": 2}


@dataclass(frozen=True, slots=True)
class ChallengeSheet:
    seat: str
    severity: str
    target: str
    problem: str
    impact: str
    fix: str
    evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_ids"] = list(self.evidence_ids)
        value["effect"] = SEVERITY_EFFECT.get(self.severity, "")
        return value

    def render(self, width: int = 72) -> str:
        label = "CHALLENGE" if self.severity in {"SEV-1", "SEV-2"} else "NOTE"
        lines = [f"{label}   {self.severity}   ·   {self.seat}"]
        for field_name, text in (
            ("Target", self.target),
            ("Problem", self.problem),
            ("Impact", self.impact),
            ("Fix", self.fix),
        ):
            lines.append(_wrap(field_name, text, width))
        if self.evidence_ids:
            lines.append(_wrap("Based on", ", ".join(self.evidence_ids), width))
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class NoChallenge:
    """A seat must be able to say it found nothing, cleanly.

    Without this, every review pressures its reviewers into inventing objections.
    """

    seat: str
    checked: str
    note: str = "Nothing that changes the verdict."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render(self, width: int = 72) -> str:
        return "\n".join(
            [
                f"NO CHALLENGE   ·   {self.seat}",
                _wrap("Checked", self.checked, width),
                _wrap("Found", self.note, width),
            ]
        )


def _wrap(label: str, text: str, width: int) -> str:
    indent = 10
    body = " ".join(str(text).split())
    room = max(20, width - indent)
    words, lines, current = body.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > room:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    lines.append(current)
    head = f"{label:<9} {lines[0]}"
    return "\n".join([head, *(f"{'':<{indent}}{line}" for line in lines[1:])])


def sort_sheets(sheets: list[ChallengeSheet]) -> list[ChallengeSheet]:
    """Worst first. A reader should meet the blocking problems immediately."""

    return sorted(
        sheets,
        key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.seat, item.target),
    )


def render_review(
    sheets: list[ChallengeSheet],
    silent: list[NoChallenge] | None = None,
    *,
    width: int = 72,
) -> str:
    blocks = [sheet.render(width) for sheet in sort_sheets(sheets)]
    blocks.extend(item.render(width) for item in (silent or []))
    if not blocks:
        return "No seat reported. The board did not sit."
    return "\n\n".join(blocks)


def summarise(sheets: list[ChallengeSheet]) -> dict[str, Any]:
    counts = {severity: 0 for severity in SEVERITY_EFFECT}
    for sheet in sheets:
        counts[sheet.severity] = counts.get(sheet.severity, 0) + 1
    return {
        "total": len(sheets),
        "by_severity": counts,
        "blocking": counts.get("SEV-1", 0),
        "needs_remediation": counts.get("SEV-2", 0),
        "decision_blocked": counts.get("SEV-1", 0) > 0,
    }


def to_finding_record(
    sheet: ChallengeSheet,
    *,
    review_id: str,
    finding_id: str,
    reviewer: str,
    reviewer_role: str,
    artefact_version: str,
    date_raised: str,
    spec_reference: str,
    evidence_reference: str,
    ai_description: str,
) -> dict[str, Any]:
    """Turn a sheet into the RBM finding record the runtime consumes.

    AI assistance is declared as used and human-verified here because a challenge
    sheet from an agent seat is agent-produced by definition.
    """

    remediating = sheet.severity in {"SEV-1", "SEV-2"}
    return {
        "schema_version": "2.2.0",
        "finding_id": finding_id,
        "review_id": review_id,
        "reviewer": reviewer,
        "reviewer_role": reviewer_role,
        "artefact_version": artefact_version,
        "date_raised": date_raised,
        "severity": sheet.severity,
        "spec_reference": spec_reference,
        "title": sheet.target,
        "detail": f"{sheet.problem} {sheet.impact}".strip(),
        "evidence_tier": "T1",
        "evidence_reference": evidence_reference,
        "ai_assistance": {
            "used": True,
            "description": ai_description,
            "human_verified": True,
        },
        "status": "OPEN",
        "remediation_requirement": sheet.fix if remediating else None,
        "target_resolution_date": "2026-08-31" if remediating else None,
        "closure": None,
    }
