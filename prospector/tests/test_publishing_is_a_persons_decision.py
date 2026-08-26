"""The moment a sample becomes somebody's public face, and the gate in front of it.

Everything before this point is reversible. A folder can be deleted, a wrong reading
corrected, a page rebuilt. Publishing is not: the page goes up under a business's name,
their customers find it, and the "unofficial sample" banner — the one thing separating
generous speculative work from a passable forgery of their web presence — comes off.

So the banner comes off in exchange for exactly one thing: a record naming a person at that
business, what they authorised, when, and how. These tests defend that exchange, and the
refusals around it, in the same way the parent repository defends ratifying a board decision
or re-arming a breaker: structurally, with no `force=True` anywhere.
"""
from __future__ import annotations

import json

import pytest

from prospector.business import Business, Fact
from prospector.engagement import (AUTHORISED, Authorisation, Engagement, LIVE, Ledger,
                                   MONITOR, NotAuthorised, PUBLISH, SAMPLE, UNKNOWN, gate)
from prospector.site import render

AT = "2026-08-25T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731
BUSINESS = Business("node/1", FACT("Bridge End Barbers"), FACT("hairdresser"),
                    fields={"phone": FACT("+353 74 912 0001"), "city": FACT("Donegal Town")})


def _authorisation(**overrides):
    fields = dict(business_identity="node/1", person="Cathy Doherty", role="owner",
                  medium="email from cathy@example.ie", granted_on="2026-08-27",
                  scopes=(PUBLISH,))
    fields.update(overrides)
    return Authorisation(**fields)


def test_an_automation_cannot_authorise_publishing():
    """The same prefixes the parent repository refuses for a board ratification.

    Publishing a website under a stranger's business name is that kind of judgement, and
    the refusal is in the constructor so there is nowhere to route around it.
    """

    for name in ("agent: prospector", "ai:builder", "bot: outreach", "system: cron"):
        with pytest.raises(NotAuthorised, match="names an automation"):
            _authorisation(person=name)


def test_an_authorisation_must_say_how_it_was_given():
    """'They said yes' is not a record. The day somebody asks who agreed, it has to answer."""

    with pytest.raises(NotAuthorised, match="how it was given"):
        _authorisation(medium="")


def test_an_authorisation_must_name_somebody():
    with pytest.raises(NotAuthorised):
        _authorisation(person="  ")


def test_a_sample_page_carries_the_banner_and_asks_not_to_be_indexed():
    page = render(BUSINESS, operator="Ian McGuane")
    assert "Unofficial sample" in page
    assert "noindex" in page


def test_an_authorised_page_drops_the_banner_and_becomes_findable():
    page = render(BUSINESS, operator="Ian McGuane", authorisation=_authorisation())
    assert "Unofficial sample" not in page
    assert "noindex" not in page
    assert "Built by Ian McGuane for Bridge End Barbers" in page


def test_an_authorisation_for_something_else_does_not_publish():
    """Agreeing to have a site watched is not agreeing to have it published."""

    with pytest.raises(NotAuthorised, match="does not permit PUBLISH"):
        render(BUSINESS, operator="Ian McGuane",
               authorisation=_authorisation(scopes=(MONITOR,)))


def test_the_gate_refuses_a_business_that_has_not_agreed_to_anything():
    with pytest.raises(NotAuthorised, match="no recorded authorisation"):
        gate(Engagement("node/1", SAMPLE))


def test_the_gate_refuses_when_the_ledger_could_not_be_read(tmp_path):
    """An unreadable ledger is not an absence of engagements, and it is certainly not
    permission."""

    path = tmp_path / "engagements.json"
    path.write_text("{ not json", encoding="utf-8")
    engagement = Ledger(path).get("node/1")
    assert engagement.status == UNKNOWN
    with pytest.raises(NotAuthorised, match="could not be read"):
        gate(engagement)


def test_a_stored_authorisation_that_will_not_load_is_not_an_authorisation(tmp_path):
    """The record is the permission, so a corrupt record is no permission.

    Publishing on the strength of a half-written row is exactly the failure the row exists
    to prevent.
    """

    path = tmp_path / "engagements.json"
    path.write_text(json.dumps({"node/1": {
        "status": AUTHORISED, "name": "Bridge End Barbers",
        "authorisation": {"business_identity": "node/1", "person": "Cathy Doherty",
                          "role": "owner", "medium": "", "granted_on": "2026-08-27"}}}),
        encoding="utf-8")
    engagement = Ledger(path).get("node/1")
    assert engagement.status == UNKNOWN
    assert not engagement.may_publish


def test_a_ledger_that_has_never_been_written_reports_sample_not_unknown(tmp_path):
    """A fresh install must be able to start; an absent file is genuinely empty."""

    assert Ledger(tmp_path / "engagements.json").get("node/1").status == SAMPLE


def test_an_engagement_round_trips_through_the_ledger(tmp_path):
    path = tmp_path / "engagements.json"
    ledger = Ledger(path)
    engagement = Engagement("node/1", LIVE, "Bridge End Barbers", _authorisation(),
                            "https://bridgeendbarbers.ie", monitored=True)
    assert ledger.put(engagement)
    restored = ledger.get("node/1")
    assert restored.status == LIVE
    assert restored.may_publish
    assert restored.authorisation.person == "Cathy Doherty"
    assert restored.live_url == "https://bridgeendbarbers.ie"


def test_a_live_site_nobody_is_watching_says_so():
    """Monitoring is a promise, so it is recorded rather than assumed from a URL existing."""

    engagement = Engagement("node/1", LIVE, "Bridge End Barbers", _authorisation(),
                            "https://bridgeendbarbers.ie", monitored=False)
    assert "Nothing is checking that this stays up" in engagement.describe()


def test_the_command_line_refuses_to_mark_a_business_live_without_authorisation(tmp_path, capsys):
    from prospector.engagement import main

    code = main(["--ledger", str(tmp_path / "e.json"), "--identity", "node/1",
                 "--status", LIVE])
    assert code == 2
    assert "cannot be marked LIVE without an authorisation" in capsys.readouterr().err


def test_a_published_page_missing_its_authorisation_record_fails_verification():
    """The loudest finding the verifier has: a page on the internet under somebody's name
    with nothing recording that they agreed to it."""

    from prospector.verify import verify

    evidence = {"language": "en", "published": True, "authorisation": None,
                "business": {"name": {"value": "Bridge End Barbers"},
                             "kind": {"value": "hairdresser"}, "fields": {},
                             "raw": {"tags": {}}}, "images": []}
    page = render(BUSINESS, operator="Ian McGuane", authorisation=_authorisation())
    verdict = verify(page, evidence, operator="Ian McGuane")
    assert any(p.code == "PUBLISHED_WITHOUT_AUTHORISATION" for p in verdict.problems)


def test_a_live_site_still_carrying_the_sample_banner_fails_verification():
    from prospector.verify import verify

    evidence = {"language": "en", "published": True,
                "authorisation": {"person": "Cathy Doherty", "medium": "email"},
                "business": {"name": {"value": "Bridge End Barbers"},
                             "kind": {"value": "hairdresser"}, "fields": {},
                             "raw": {"tags": {}}}, "images": []}
    sample = render(BUSINESS, operator="Ian McGuane")
    verdict = verify(sample, evidence, operator="Ian McGuane")
    assert any(p.code == "BANNER_ON_A_LIVE_SITE" for p in verdict.problems)
    assert any(p.code == "LIVE_BUT_HIDDEN" for p in verdict.problems)
