"""The board can veto but never authorise; a thesis can authorise but never override a veto.

That asymmetry is the whole design, and written either way round one half becomes
decoration. A crypto review able to authorise would be claiming its hygiene checks
constitute an edge. A thesis able to proceed past a SEV-1 would make the review a formality
somebody skips on a busy day.

The second property is the one that keeps it honest under failure: findings that could not
be READ are not findings that do not exist. A position permitted because nobody retrieved
the evidence is the exact failure this repository is organised against, and it is the one a
`None` would quietly produce.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.thesis import (
    EXPIRED,
    INDETERMINATE,
    PERMITTED,
    REFUSED,
    Thesis,
    ThesisRegister,
    evaluate,
)

SUBJECT = "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def future(days=30):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")


def past(days=1):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def thesis(subject=SUBJECT, expires=None, limit=5000.0, by="Ian McGuane"):
    return Thesis(
        subject=subject, declared_by=by,
        reasoning="Treasury exposure to a dollar-pegged asset for working capital.",
        considered=("the issuer can freeze an address", "the peg can break"),
        declared_at="2026-08-02T19:00:00Z", expires_at=expires or future(),
        max_exposure=limit,
    )


def finding(severity="SEV-2", status="OPEN", title="upgradeable behind empty slots"):
    return {"severity": severity, "status": status, "title": title, "finding_id": "X"}


class TestAThesisMustBeDefensible:
    def test_automation_cannot_author_one(self):
        """This is the judgement a board deliberately does not make."""

        with pytest.raises(ValueError, match="originating its own reasons"):
            thesis(by="agent:cva")

    @pytest.mark.parametrize("prefix", ["ai:", "model:", "bot:", "system:", "automation:"])
    def test_every_automation_prefix_is_refused(self, prefix):
        with pytest.raises(ValueError):
            thesis(by=f"{prefix}something")

    def test_empty_reasoning_is_refused(self):
        with pytest.raises(ValueError, match="nobody has to defend"):
            Thesis(SUBJECT, "Ian McGuane", "   ", ("a risk",),
                   "2026-08-02T19:00:00Z", future(), 100.0)

    def test_considering_nothing_is_refused(self):
        with pytest.raises(ValueError, match="hope with a signature"):
            Thesis(SUBJECT, "Ian McGuane", "because", (),
                   "2026-08-02T19:00:00Z", future(), 100.0)

    def test_an_open_ended_grant_is_refused(self):
        with pytest.raises(ValueError, match="failure mode of every grant"):
            Thesis(SUBJECT, "Ian McGuane", "because", ("a risk",),
                   "2026-08-02T19:00:00Z", "", 100.0)

    def test_no_exposure_limit_is_refused(self):
        with pytest.raises(ValueError, match="IS the decision"):
            Thesis(SUBJECT, "Ian McGuane", "because", ("a risk",),
                   "2026-08-02T19:00:00Z", future(), 0.0)

    def test_a_self_granted_thesis_says_so_on_its_face(self):
        assert "SELF-GRANTED" in thesis().describe()


class TestTheBoardVetoesAndNeverAuthorises:
    def test_a_blocking_finding_refuses_despite_a_valid_thesis(self):
        result = evaluate(thesis(), subject=SUBJECT, findings=[finding("SEV-1")],
                          proposed_exposure=100.0)

        assert result.status == REFUSED

    def test_the_refusal_says_a_thesis_does_not_authorise_disbelief(self):
        text = evaluate(thesis(), subject=SUBJECT, findings=[finding()],
                        proposed_exposure=100.0).describe()

        assert "does not authorise disbelieving the evidence" in text

    def test_a_resolved_finding_no_longer_blocks(self):
        result = evaluate(thesis(), subject=SUBJECT,
                          findings=[finding(status="CLOSED")], proposed_exposure=100.0)

        assert result.status == PERMITTED

    def test_a_clean_board_is_stated_as_not_a_veto_rather_than_an_endorsement(self):
        text = evaluate(thesis(), subject=SUBJECT, findings=[], proposed_exposure=100.0
                        ).describe()

        assert "has not vetoed it" in text
        assert "It does NOT mean the board endorsed it" in text

    def test_a_clean_board_alone_permits_nothing_without_a_thesis(self):
        """The half this repository was missing: no reason to act, nothing to permit."""

        result = evaluate(None, subject=SUBJECT, findings=[], proposed_exposure=100.0)

        assert result.status == REFUSED


class TestUnreadEvidenceIsNotCleanEvidence:
    def test_findings_that_could_not_be_read_are_indeterminate_not_permitted(self):
        result = evaluate(thesis(), subject=SUBJECT, findings=None, proposed_exposure=100.0)

        assert result.status == INDETERMINATE

    def test_indeterminate_is_distinguished_from_a_refusal(self):
        text = evaluate(thesis(), subject=SUBJECT, findings=None,
                        proposed_exposure=100.0).describe()

        assert "not a refusal and it is not" in text

    def test_the_wording_refuses_to_call_unread_evidence_absent(self):
        text = evaluate(thesis(), subject=SUBJECT, findings=None,
                        proposed_exposure=100.0).describe()

        assert "NOT a finding that there are none" in text


class TestTheLimitAndTheClock:
    def test_exposure_over_the_stated_limit_refuses(self):
        result = evaluate(thesis(limit=1000.0), subject=SUBJECT, findings=[],
                          proposed_exposure=1000.01)

        assert result.status == REFUSED

    def test_exposure_within_the_limit_permits(self):
        result = evaluate(thesis(limit=1000.0), subject=SUBJECT, findings=[],
                          proposed_exposure=999.0)

        assert result.status == PERMITTED

    def test_an_unstated_exposure_is_indeterminate_not_unlimited(self):
        result = evaluate(thesis(), subject=SUBJECT, findings=[], proposed_exposure=0.0)

        assert result.status == INDETERMINATE

    def test_an_expired_thesis_reports_expired_rather_than_refused(self):
        """A lapsed authorisation is not a weaker one, and needs a different response."""

        result = evaluate(thesis(expires=past()), subject=SUBJECT, findings=[],
                          proposed_exposure=100.0)

        assert result.status == EXPIRED

    def test_a_thesis_for_another_subject_does_not_transfer(self):
        result = evaluate(thesis(subject="ethereum:0xOTHER"), subject=SUBJECT,
                          findings=[], proposed_exposure=100.0)

        assert result.status == REFUSED


class TestTheRegister:
    def test_the_newest_unexpired_thesis_wins(self, tmp_path):
        register = ThesisRegister(tmp_path / "t.json")
        register.add(thesis(limit=100.0))
        newer = Thesis(SUBJECT, "Ian McGuane", "revised", ("a risk",),
                       "2026-08-03T19:00:00Z", future(), 250.0)
        register.add(newer)

        assert register.current(SUBJECT).max_exposure == 250.0

    def test_an_expired_thesis_is_not_current(self, tmp_path):
        register = ThesisRegister(tmp_path / "t.json")
        register.add(thesis(expires=past()))

        assert register.current(SUBJECT) is None

    def test_a_superseded_thesis_is_kept_rather_than_deleted(self, tmp_path):
        register = ThesisRegister(tmp_path / "t.json")
        register.add(thesis(limit=100.0))
        register.add(Thesis(SUBJECT, "Ian McGuane", "revised", ("a risk",),
                            "2026-08-03T19:00:00Z", future(), 250.0))
        register.save()

        assert len(ThesisRegister(tmp_path / "t.json").entries) == 2

    def test_an_unreadable_register_refuses_to_be_written_through(self, tmp_path):
        path = tmp_path / "t.json"
        path.write_text("{not json", encoding="utf-8")

        with pytest.raises(RuntimeError):
            ThesisRegister(path).add(thesis())

    def test_an_unreadable_register_yields_no_thesis_and_says_it_is_unreadable(self, tmp_path):
        """So a caller reports INDETERMINATE rather than 'nobody ever authorised this'."""

        path = tmp_path / "t.json"
        path.write_text("nonsense", encoding="utf-8")
        register = ThesisRegister(path)

        assert register.current(SUBJECT) is None
        assert register.readable is False
