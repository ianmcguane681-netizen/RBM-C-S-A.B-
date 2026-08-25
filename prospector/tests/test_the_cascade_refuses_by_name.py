"""A disqualifier is not a deduction, and an unmeasured stage is not a low mark.

These are the two properties a scored prospect list cannot have, and they are the reason
this package has a cascade instead. The tests are written against the consequences rather
than the mechanism: a business with a perfectly good website must never be prepared however
attractive it is on every other axis, and a business whose website could not be assessed
must not be prepared either — the second being the one a scoring scheme silently gets wrong
by treating "unknown" as "poor".
"""
from __future__ import annotations

from prospector import cascade
from prospector.business import ABSENT, Business, Fact
from prospector.condition import Condition, Finding, DEFECT, OBSERVATION
from prospector.presence import Presence
from prospector.seen import Sighting
from prospector.states import (DEFICIENT, NEW, NO_SITE_LISTED, SEEN_BEFORE, SERVICEABLE,
                               SITE_LISTED, UNCHECKED, UNDETERMINED)

AT = "2026-08-25T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731


def _business(**fields) -> Business:
    return Business("node/1", FACT("Test Shop"), FACT("hairdresser"),
                    fields={k: FACT(v) for k, v in fields.items()})


NEW_SIGHTING = Sighting(NEW, "node/1")
CONTACTABLE = dict(phone="+353 1 000 0000")


def test_a_site_with_no_named_defect_is_refused_rather_than_prepared():
    decision = cascade.decide(
        _business(**CONTACTABLE), NEW_SIGHTING,
        Presence(SITE_LISTED, url="https://good.example"),
        Condition(SERVICEABLE, url="https://good.example"))
    assert decision.status == cascade.REFUSED
    assert decision.stage == "condition"


def test_a_site_that_could_not_be_assessed_blocks_rather_than_scoring_low():
    decision = cascade.decide(
        _business(**CONTACTABLE), NEW_SIGHTING,
        Presence(SITE_LISTED, url="https://guarded.example"),
        Condition(UNDETERMINED, url="https://guarded.example", reason="HTTP 403"))
    assert decision.status == cascade.INDETERMINATE
    assert "Not a refusal and not permission" in decision.describe()


def test_observations_alone_never_justify_an_approach():
    """A dated copyright notice is true, interesting, and not a reason to email anyone.

    Severity is the whole difference between a finding worth telling a person and a finding
    worth acting on, and a scheme that summed findings would lose it.
    """

    only_observations = Condition(SERVICEABLE, url="https://fine.example", findings=(
        Finding("DATED_NOTICE", OBSERVATION, "newest copyright year is 2019"),
        Finding("HTTPS_UNKNOWN", OBSERVATION, "could not be established")))
    decision = cascade.decide(_business(**CONTACTABLE), NEW_SIGHTING,
                              Presence(SITE_LISTED, url="https://fine.example"),
                              only_observations)
    assert decision.status == cascade.REFUSED


def test_one_defect_among_many_observations_still_prepares():
    mixed = Condition(DEFICIENT, url="https://broken.example", findings=(
        Finding("DATED_NOTICE", OBSERVATION, "2019"),
        Finding("NO_HTTPS", DEFECT, "plain HTTP only"),
        Finding("HTTPS_UNKNOWN", OBSERVATION, "unclear")))
    decision = cascade.decide(_business(**CONTACTABLE), NEW_SIGHTING,
                              Presence(SITE_LISTED, url="https://broken.example"), mixed)
    assert decision.status == cascade.PREPARE
    assert "Not secure" in decision.opening_claim


def test_an_unreadable_register_blocks_preparation():
    """Because the alternative is approaching somebody for the second time."""

    decision = cascade.decide(_business(**CONTACTABLE),
                              Sighting(UNCHECKED, "node/1", reason="file will not parse"),
                              Presence(NO_SITE_LISTED), None)
    assert decision.status == cascade.INDETERMINATE
    assert decision.stage == "seen"


def test_a_business_prepared_before_is_refused_but_the_refusal_is_reversible():
    seen = Sighting(SEEN_BEFORE, "node/1", dates=("2026-06-01T00:00:00+00:00",))
    refused = cascade.decide(_business(**CONTACTABLE), seen, Presence(NO_SITE_LISTED), None)
    assert refused.status == cascade.REFUSED
    assert "--again" in refused.reason
    allowed = cascade.decide(_business(**CONTACTABLE), seen, Presence(NO_SITE_LISTED), None,
                             prepare_again=True)
    assert allowed.status == cascade.PREPARE


def test_a_business_with_no_way_to_reach_it_is_refused_before_the_network_is_touched():
    decision = cascade.decide(_business(), NEW_SIGHTING, Presence(NO_SITE_LISTED), None)
    assert decision.status == cascade.REFUSED
    assert decision.stage == "contactable"


def test_the_opening_claim_never_states_an_absence_the_evidence_does_not_support():
    """The sentence the whole package is built to get right.

    On `NO_SITE_LISTED` the note may say the operator could not find a site listed. It may
    not say the business has none, and it must leave room for the reply "we do have one".
    """

    decision = cascade.decide(_business(**CONTACTABLE), NEW_SIGHTING,
                              Presence(NO_SITE_LISTED), None)
    assert decision.status == cascade.PREPARE
    claim = decision.opening_claim.lower()
    assert "could not find a website listed" in claim
    assert "if you already have one" in claim
    assert "you have no website" not in claim
    assert "you don't have a website" not in claim
