"""A mandate refuses by default, and every way of not-knowing is a refusal.

The mandate is where this repository's recurring defect stops being a reporting problem
and starts being a trade. *Not found* rendering as *not there* has appeared in a court
archive, a proxy slot, a liquidity venue and a resample; here it would authorise someone
to move money on evidence nobody checked.

So the tests below are mostly about absence: a missing field, an unrecorded basis, an
unchecked artefact. Each must refuse, and each must refuse for a stated reason rather than
by returning False.
"""
from __future__ import annotations

import pytest

from rbe_runtime.mandate import (
    ESTABLISHED,
    EXPIRED,
    FAILED,
    INDETERMINATE,
    PERMITTED,
    REFUSED,
    UNEVALUATED,
    DriftObservation,
    MandateFinding,
    ProposedAction,
    evaluate,
)

SUBJECT = "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
NOW = "2026-08-02T00:00:00Z"
ACTION = ProposedAction(SUBJECT, "sell 10,000 units")


def package(**over):
    decision = {
        "evaluation": {"outcome": "PASS"},
        "binding": True,
        "single_authority": False,
        "superseded": False,
        "status": "SIGNED",
        "session_id": "REV-1",
    }
    indicator = {
        "expires_at": "2026-08-05T00:00:00Z",
        "unresolved_sev1_count": 0,
        "unresolved_sev2_count": 0,
        "review_id": "REV-1",
    }
    decision.update(over.pop("decision", {}))
    indicator.update(over.pop("indicator", {}))
    return {
        "decision": decision,
        "publication": {"indicator": indicator},
        "ratification": {"board_chair": "ian.mcguane"},
    }


SESSION = {"initiation": {"repository": SUBJECT}}
FULL_REPORTS = [
    {"raw_record": {"ai_assistance": {"human_verification_basis": "full-text"}}}
]
UNCHANGED = DriftObservation(25_700_000, "0xabc", "0xABC")


def check(pkg=None, action=ACTION, *, session=SESSION, reports=None, drift=UNCHANGED, now=NOW):
    return evaluate(
        pkg if pkg is not None else package(),
        action,
        now=now,
        session=session,
        reports=FULL_REPORTS if reports is None else reports,
        drift=drift,
    )


def condition(finding: MandateFinding, name: str):
    return next(c for c in finding.conditions if c.name == name)


class TestTheOnlyWayToPermit:
    def test_everything_established_permits(self):
        assert check().status == PERMITTED

    def test_every_condition_is_reported_even_when_it_passed(self):
        """A refusal that hides what held tells a caller nothing about what to change."""

        names = {c.name for c in check().conditions}

        assert names == {
            "outcome", "authority", "scrutiny", "expiry", "drift",
            "supersession", "scope", "findings",
        }


class TestAbsenceNeverPermits:
    @pytest.mark.parametrize("missing", ["expires_at", "unresolved_sev1_count"])
    def test_a_missing_indicator_field_is_unevaluated_not_satisfied(self, missing):
        pkg = package()
        del pkg["publication"]["indicator"][missing]

        assert check(pkg).status == INDETERMINATE

    def test_an_unchecked_artefact_is_not_an_unchanged_one(self):
        """The single most tempting shortcut in the whole design."""

        finding = check(drift=None)

        assert finding.status == INDETERMINATE
        assert "unchecked is not unchanged" in condition(finding, "drift").reason

    def test_no_recorded_scrutiny_is_unevaluated(self):
        assert check(reports=[]).status == INDETERMINATE

    def test_indeterminate_is_reported_apart_from_refused(self):
        """A caller must tell 'the decision says no' from 'I cannot tell what it says'."""

        cannot_tell = check(drift=None)
        says_no = check(package(decision={"outcome": "FAIL", "evaluation": {"outcome": "FAIL"}}))

        assert cannot_tell.status == INDETERMINATE
        assert says_no.status == REFUSED

    def test_the_description_says_an_unevaluated_condition_is_not_a_pass(self):
        assert "is a refusal, not a pass" in check(drift=None).describe()


class TestOutcome:
    @pytest.mark.parametrize("outcome", ["FAIL", "INSUFFICIENT_EVIDENCE"])
    def test_a_non_permitting_outcome_refuses(self, outcome):
        finding = check(package(decision={"evaluation": {"outcome": outcome}}))

        assert finding.status == REFUSED
        assert condition(finding, "outcome").status == FAILED

    def test_insufficient_evidence_is_never_read_as_permission(self):
        """The sentinel defect at decision level: 'we could not tell' is not 'go ahead'."""

        finding = check(package(decision={"evaluation": {"outcome": "INSUFFICIENT_EVIDENCE"}}))

        assert finding.status != PERMITTED

    def test_pass_with_findings_may_permit(self):
        assert check(package(decision={"evaluation": {"outcome": "PASS_WITH_FINDINGS"}})).status == PERMITTED


class TestAuthority:
    def test_a_non_binding_decision_authorises_nothing(self):
        """RBM-003 section 11 states this outright, so a mandate must not outrank it."""

        finding = check(package(decision={"binding": False}))

        assert finding.status == REFUSED
        assert "non-binding" in condition(finding, "authority").reason

    def test_a_single_authority_decision_authorises_nothing(self):
        finding = check(package(decision={"single_authority": True}))

        assert condition(finding, "authority").status == FAILED


class TestScrutiny:
    def test_a_summary_reading_does_not_authorise(self):
        finding = check(reports=[
            {"raw_record": {"ai_assistance": {"human_verification_basis": "summary-reading"}}}
        ])

        assert finding.status == REFUSED
        assert "not a full reading" in condition(finding, "scrutiny").reason

    def test_one_weak_seat_is_enough_to_refuse(self):
        """A board is as scrutinised as its least-read seat."""

        finding = check(reports=FULL_REPORTS + [
            {"raw_record": {"ai_assistance": {"human_verification_basis": "summary-reading"}}}
        ])

        assert condition(finding, "scrutiny").status == FAILED


class TestFreshness:
    def test_expiry_alone_reports_expired_rather_than_refused(self):
        """'Permitted yesterday' and 'never permitted' are different instructions: one
        says re-run the review, the other says do not."""

        assert check(now="2026-08-06T00:00:00Z").status == EXPIRED

    def test_a_changed_implementation_refuses_inside_the_window(self):
        """Drift beats the wall clock. An upgradeable contract can invalidate every fact
        the board established without a second passing."""

        finding = check(drift=DriftObservation(25_700_000, "0xdead", "0xabc"))

        assert finding.status == REFUSED
        assert "implementation changed" in condition(finding, "drift").reason

    def test_expiry_alongside_another_failure_is_a_plain_refusal(self):
        finding = check(package(decision={"binding": False}), now="2026-08-06T00:00:00Z")

        assert finding.status == REFUSED


class TestSupersessionAndScope:
    def test_a_superseded_decision_permits_nothing(self):
        finding = check(package(decision={"superseded": True, "status": "SUPERSEDED"}))

        assert condition(finding, "supersession").status == FAILED

    def test_a_decision_about_another_subject_permits_nothing(self):
        finding = check(action=ProposedAction("ethereum:0xdAC17F958D2ee523a2206206994597C13D831ec7"))

        assert finding.status == REFUSED
        assert condition(finding, "scope").status == FAILED

    def test_the_subject_is_matched_case_insensitively(self):
        """Addresses are checksummed inconsistently across tools; case is not identity."""

        assert check(action=ProposedAction(SUBJECT.lower())).status == PERMITTED


class TestFindings:
    def test_an_unresolved_blocking_finding_refuses(self):
        finding = check(package(indicator={"unresolved_sev2_count": 4}))

        assert finding.status == REFUSED
        assert "4 unresolved SEV-2" in condition(finding, "findings").reason


class TestNoBooleans:
    def test_the_finding_exposes_no_boolean_verdict(self):
        """A caller reaching for `.permitted` would get a truthy object and act on it."""

        for forbidden in ("permitted", "ok", "allowed", "passed"):
            assert not hasattr(MandateFinding, forbidden)
