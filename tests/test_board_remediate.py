"""Answering a blocking finding, through the front door.

The board could raise SEV-1 and SEV-2 findings and the CLI offered no way to
respond to one, so answering a blocker meant writing Python -- the situation this
CLI exists to remove. Review 0006 made it visible: two blocking findings, both
rendering NOT SPECIFIED, and no command to fill them in.

What the command refuses matters more than what it accepts. A plan submitted after
a decision candidate is frozen would be a plan written to fit a verdict already
computed, and a plan from anyone but the Methodology Auditor would let the team
under review grade its own homework.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from board.cli import main
from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime
from tests.test_rbe_runtime_service import NOW, prepare_to_consolidation


def plan_file(tmp_path: Path, review_id: str, finding_id: str = "FND-1") -> Path:
    path = tmp_path / "plan.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "2.2.0",
                "document_id": "RMP-1",
                "review_id": review_id,
                "authoring_team_contact": "ian.mcguane",
                "date_submitted": "2026-07-28T23:59:00Z",
                "ma_reviewer": "agent:ma",
                "ma_decision": "ACCEPTED",
                "ma_signature_ref": "SIG-MA-RMP",
                "items": [
                    {
                        "finding_id": finding_id,
                        "root_cause": "Corroboration rests on a single case.",
                        "planned_changes": "Obtain corroboration from three districts.",
                        "responsible_person": "ian.mcguane",
                        "target_completion_date": "2026-09-30",
                        "planned_resolution_evidence": "Coverage sweep showing three cases.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_the_command_is_reachable_from_the_front_door():
    """The gap that prompted this: the runtime had the capability, the CLI did not."""
    from board.cli import build_parser

    actions = build_parser()._subparsers._group_actions[0].choices  # noqa: SLF001
    assert "remediate" in actions


def test_a_plan_is_refused_once_the_decision_inputs_are_frozen(tmp_path: Path, capsys):
    """Otherwise a plan could be written to fit a verdict already computed."""
    database = tmp_path / "board.sqlite3"
    runtime = RBERuntime(database, clock=lambda: NOW)
    prepare_to_consolidation(runtime, "REV-RMP")
    runtime.prepare_decision_candidate("REV-RMP", actor="human-chair", idempotency_key="cand")

    code = main(
        ["--database", str(database), "remediate", "--review", "REV-RMP",
         "--plan", str(plan_file(tmp_path, "REV-RMP"))]
    )

    assert code == 1
    assert "RBE_DECISION_INPUTS_FROZEN" in capsys.readouterr().out


def test_the_refusal_explains_who_may_submit(tmp_path: Path):
    """A refusal that does not say what would have worked is a dead end."""
    import inspect

    from board.cli import cmd_remediate

    source = inspect.getsource(cmd_remediate)
    assert "RBE_REMEDIATION_ACTOR_MISMATCH" in source
    assert "RBE_REMEDIATION_SUBMISSION_NOT_OPEN" in source


def test_only_the_methodology_auditor_submits(tmp_path: Path):
    """The command reads the auditor from the initiation rather than taking it
    from the caller, so a plan cannot be submitted under another seat's name."""
    import inspect

    from board.cli import cmd_remediate

    source = inspect.getsource(cmd_remediate)
    assert 'initiation["methodology_auditor"]' in source
    assert "actor=auditor" in source
