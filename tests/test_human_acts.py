"""Every act reserved for a named human refuses every prefix that is not one.

`CLAUDE.md` names five judgements a machine may not make and states that each refuses six
automation prefixes. That was documentation rather than a fact: `lib.arb` and
`rbe_runtime.profile` each listed four, so a settlement equivalence could be declared by
`bot: scanner` and a board decision ratified by `system: importer`. Both guards fired
convincingly for `agent:`, which is the prefix anyone checking reaches for first, and
neither list looked short — four plausible prefixes read exactly as complete as six.

So the property under test is not "this guard rejects an agent". It is that the whole set
of guarded acts rejects the whole set of prefixes, asserted by walking both — because the
defect was never a guard being absent, it was two guards quietly disagreeing about what
automation is. A file that tests each act against its own idea of the list would have
passed throughout.

The acts are exercised through their real entry points rather than through the predicate,
since a guard that stopped calling the predicate would satisfy any test written against
the predicate alone.
"""
from __future__ import annotations

import pytest

from guards.human_acts import AUTOMATION_PREFIXES, is_automation

A_PERSON = "Ian McGuane"

#: Written out rather than imported, so a prefix silently dropped from the shared tuple
#: fails here instead of narrowing the guards and the test together.
THE_SIX = ("agent:", "ai:", "model:", "automation:", "bot:", "system:")


def _equivalence(author: str) -> None:
    from lib.arb import EquivalenceDeclaration

    EquivalenceDeclaration(
        declared_by=author,
        reasoning="both books void the market on abandonment before the 80th minute",
        scenarios_checked=("abandonment", "non-runner"),
    )


def _thesis(author: str) -> None:
    from lib.thesis import Thesis

    Thesis(
        subject="USDC", declared_by=author,
        reasoning="Treasury exposure to a dollar-pegged asset for working capital.",
        considered=("the issuer can freeze an address", "the peg can break"),
        declared_at="2026-08-02T19:00:00Z", expires_at="2027-08-02T19:00:00Z",
        max_exposure=100.0,
    )


def _standing_authority(author: str) -> None:
    from lib.arb_reaper import StandingAuthority

    StandingAuthority(
        declared_by=author,
        reasoning="the position makes no claim about the fixture, only about the prices",
        considered=("a book can void one leg and settle the other",),
        expires_at="2027-08-02T19:00:00Z", max_exposure=500.0,
    )


def _forecast_criterion(author: str) -> None:
    from lib.stocks_reaper import FORECAST, Criterion

    Criterion(
        name="margin recovers", kind=FORECAST,
        statement="gross margin returns above 40% within four quarters",
        test=lambda filings: ("PASSED", "asserted"),
        declared_by=author,
    )


def _breaker_reset(author: str, tmp_path) -> None:
    from lib.breakers import Breakers, Ringfence

    controls = Breakers(Ringfence("arb", 1000.0), tmp_path / "breakers.json",
                        kill_switch=tmp_path / "HALT")
    controls.reset(author, "the pricing error that tripped it has been corrected")


def _resume_autonomy(author: str, tmp_path) -> None:
    from lib.operating import resume

    resume(tmp_path, author, "the source that was flapping has been stable for a week")


#: Every act `CLAUDE.md` reserves for a named human, and how to attempt it. `board verify`
#: is the one that is a predicate rather than a constructor, and is asserted separately.
ACTS = {
    "declaring settlement equivalence": _equivalence,
    "authoring a thesis": _thesis,
    "holding a standing authority": _standing_authority,
    "declaring a FORECAST criterion": _forecast_criterion,
}

ACTS_NEEDING_A_DIRECTORY = {
    "re-arming a tripped breaker": _breaker_reset,
    "resuming autonomous placement": _resume_autonomy,
}


class TestNoGuardedActAcceptsAutomation:

    @pytest.mark.parametrize("act", sorted(ACTS))
    @pytest.mark.parametrize("prefix", THE_SIX)
    def test_a_guarded_act_refuses_every_automation_prefix(self, act, prefix):
        with pytest.raises(ValueError):
            ACTS[act](f"{prefix} whatever-it-calls-itself")

    @pytest.mark.parametrize("act", sorted(ACTS_NEEDING_A_DIRECTORY))
    @pytest.mark.parametrize("prefix", THE_SIX)
    def test_an_act_taking_a_directory_refuses_every_prefix(self, act, prefix, tmp_path):
        with pytest.raises(ValueError):
            ACTS_NEEDING_A_DIRECTORY[act](f"{prefix} whatever-it-calls-itself", tmp_path)

    @pytest.mark.parametrize("prefix", THE_SIX)
    def test_board_verify_reads_every_prefix_as_an_agent(self, prefix):
        """The act that publishes a decision, and the half of the pair that had drifted."""

        from rbe_runtime.profile import is_agent_actor

        assert is_agent_actor(f"{prefix} whatever-it-calls-itself") is True

    @pytest.mark.parametrize("act", sorted(ACTS))
    def test_a_named_person_may_still_perform_every_guarded_act(self, act):
        """A guard that refused everybody would pass every test above and be useless."""

        ACTS[act](A_PERSON)

    @pytest.mark.parametrize("act", sorted(ACTS_NEEDING_A_DIRECTORY))
    def test_a_named_person_may_still_reset_and_resume(self, act, tmp_path):
        ACTS_NEEDING_A_DIRECTORY[act](A_PERSON, tmp_path)


class TestTheListItself:

    def test_the_shared_list_holds_all_six_prefixes(self):
        """Named separately from the acts, so shrinking the tuple cannot pass quietly."""

        assert set(AUTOMATION_PREFIXES) == set(THE_SIX)

    def test_no_guard_writes_its_own_copy_of_the_list(self):
        """The defect was two copies disagreeing, so the fix is that copies do not exist.

        Checked by identity against the shared tuple rather than by equality, because two
        equal literals in two files is the exact arrangement that drifted.
        """

        from lib import operating, stocks_reaper, thesis
        from rbe_runtime import profile

        for module in (thesis, operating, stocks_reaper, profile):
            assert module.AUTOMATION_PREFIXES is AUTOMATION_PREFIXES, (
                f"{module.__name__} holds its own copy of the automation prefixes; that "
                f"is how `lib.arb` and `rbe_runtime.profile` came to disagree"
            )

    @pytest.mark.parametrize("actor", ["BOT: Scanner", "  system: importer", "Agent: X"])
    def test_case_and_surrounding_space_are_not_a_loophole(self, actor):
        assert is_automation(actor) is True

    def test_a_person_whose_name_merely_contains_a_prefix_is_not_automation(self):
        """`startswith`, not `in` — refusing every name with "ai" in it refuses Blair."""

        assert is_automation("Alastair Campbell") is False
        assert is_automation("Ian McGuane") is False
