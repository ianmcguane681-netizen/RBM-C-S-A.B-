"""An agent seat's draft becomes reviewable material only when a person signs for it.

The runtime already refuses an AI-assisted report whose `human_verified` is not true.
That control was reachable only by hand-editing the draft JSON, which meant the process
that produced the draft was also the process that filled in the field attesting to it.

This repository has broken that separation before: a demonstration run recorded a named
human as the transcriber of a price the automation itself had read, and committed it.
The guard and the violation were authored minutes apart, by the same author.

So verification is a separate command, run by the person doing the verifying, and it
refuses an agent.
"""

from __future__ import annotations

import json

import pytest

from board.cli import main


def draft(tmp_path, *, verified=False):
    payload = {
        "reviewer_role": "MCA",
        "summary": "The census cannot distinguish a failed retrieval from a retrieved absence.",
        "recommendation": "Corrective",
        "evidence_reference_ids": ["EVI-1"],
        "finding_categories": {},
        "findings": [
            {
                "finding_id": "EG001-MCA-EG-02",
                "severity": "SEV-1",
                "title": "Rate-limited lookups are stored as archive absences",
                "ai_assistance": {"used": True, "human_verified": verified},
            }
        ],
        "report": {
            "reviewer_role": "MCA",
            "ai_assistance": {"used": True, "human_verified": verified, "method": "m/v1"},
            "human_signature_ref": "SIG-PENDING-MCA",
        },
    }
    path = tmp_path / "report-MCA.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


class TestWhoMayVerify:
    def test_a_named_human_may_verify(self, tmp_path, capsys):
        path = draft(tmp_path)

        assert main(["verify", "--report", str(path), "--by", "ian.mcguane"]) == 0

        stored = json.loads(path.read_text(encoding="utf-8"))
        assert stored["report"]["ai_assistance"]["human_verified"] is True
        assert stored["findings"][0]["ai_assistance"]["human_verified"] is True
        assert stored["report"]["human_signature_ref"] == "SIG-VERIFY-MCA-ian.mcguane"

    def test_an_agent_may_not_verify_agent_output(self, tmp_path):
        """Two agents are not a second pair of eyes, whatever the prefix says."""

        path = draft(tmp_path)

        # main() catches RBEError and returns 2, so the refusal is observed the way a
        # caller observes it -- through the exit code, not an exception it never sees.
        assert main(["verify", "--report", str(path), "--by", "agent:mca"]) == 2

    @pytest.mark.parametrize("actor", ["agent:sr", "ai:reviewer", "model:gpt", "automation:bot"])
    def test_every_automation_prefix_is_refused(self, tmp_path, actor):
        """A seat must not dodge the rule by renaming itself."""

        path = draft(tmp_path)

        assert main(["verify", "--report", str(path), "--by", actor]) == 2

    def test_a_refused_verification_leaves_the_draft_unverified(self, tmp_path):
        """The important half. Refusing loudly and writing anyway would be worse than
        not checking, because the file would then carry a verification nobody made."""

        path = draft(tmp_path)

        assert main(["verify", "--report", str(path), "--by", "agent:mca"]) == 2

        stored = json.loads(path.read_text(encoding="utf-8"))
        assert stored["report"]["ai_assistance"]["human_verified"] is False
        assert stored["findings"][0]["ai_assistance"]["human_verified"] is False


class TestWhatVerificationShows:
    def test_the_verifier_is_shown_what_they_are_signing_for(self, tmp_path, capsys):
        """A verification step that prints nothing is a checkbox."""

        path = draft(tmp_path)
        main(["verify", "--report", str(path), "--by", "ian.mcguane"])

        printed = capsys.readouterr().out
        assert "SEV-1" in printed
        assert "Rate-limited lookups are stored as archive absences" in printed
        assert "cannot distinguish" in printed
