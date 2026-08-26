"""The agent has a name now, which is exactly when the guards have to be tested.

A named agent invites two mistakes. The first is letting it sign things: a page carrying a
stranger's business name, signed "Webatron", is an unsigned page, and the operator field is
where that would happen. The second is letting the briefing become the claim — an assembly
step that summarises measurements is useful, and an assembly step that adds a sentence of
its own has quietly become the source of that sentence.

So: it proposes, it never authorises, and every number on a briefing traces to a
measurement or a costed line somebody set. The parent repository's rule, unchanged — agent
output is analysis or a proposal, never evidence.
"""
from __future__ import annotations

import pathlib

from prospector import case as case_mod, cli, contacts as contacts_mod, costs as costs_mod
from prospector import standard, webatron
from prospector.business import Business, Fact
from prospector.site import render
from prospector.webatron import Prepared

AT = "2026-08-25T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731
PACKAGE = pathlib.Path(__file__).resolve().parent.parent
BUSINESS = Business("node/1", FACT("Bridge End Barbers"), FACT("hairdresser"),
                    fields={"phone": FACT("+353 74 912 0001"),
                            "street": FACT("Main Street"), "city": FACT("Donegal Town"),
                            "postcode": FACT("F94 X2P8"), "email": FACT("hi@example.ie"),
                            "opening_hours": FACT("Tu-Fr 09:00-18:00")},
                    raw={"lat": 54.65, "lon": -8.11})

OLD_SITE = ('<html><head><title>Old</title></head><body>'
            '<table width="980"><tr><td><font>Call 074 912 0001</font></td></tr></table>'
            '</body></html>')


def _reports():
    theirs = standard.assess(OLD_SITE, status=200, https_available=False, reached=True,
                             byte_size=len(OLD_SITE))
    page = render(BUSINESS, operator="Ian McGuane")
    ours = standard.assess(page, status=200, https_available=True, reached=True,
                           byte_size=len(page))
    return theirs, ours


def _prepared(folder, **overrides):
    theirs, ours = _reports()
    fields = dict(identity="node/1", name="Bridge End Barbers", folder=folder,
                  contacts=contacts_mod.assemble(BUSINESS),
                  case=case_mod.build(theirs, ours))
    fields.update(overrides)
    return Prepared(**fields)


def test_webatron_cannot_be_the_operator(capsys):
    """It assembles the briefing. A person signs the page and sends the mail."""

    for name in ("Webatron", "webatron", "prospector"):
        code = cli.main(["--area", "Anywhere", "--operator", name, "--dry",
                         "--browser", "never",
                         "--from-file", str(PACKAGE / "fixtures/synthetic-area.overpass.json")])
        assert code == 2
        assert "names an automation" in capsys.readouterr().err


def test_the_case_is_two_measurements_rather_than_an_opinion():
    """Every point prints both sides, so a recipient can check it on their own phone."""

    theirs, ours = _reports()
    case = case_mod.build(theirs, ours)
    assert case.status == case_mod.CASE_MADE
    for point in case.fixed:
        assert point.theirs and point.ours
        assert point.why


def test_a_failure_the_sample_does_not_fix_is_listed_rather_than_dropped():
    """A pitch that only lists wins reads like every other pitch."""

    theirs, ours = _reports()
    # Their site has no contact path; a sample built without an email would not fix it.
    bare = Business("node/2", FACT("Bare Shop"), FACT("shop"), fields={"city": FACT("Town")})
    page = render(bare, operator="Ian McGuane")
    ours_bare = standard.assess(page, status=200, https_available=True, reached=True,
                                byte_size=len(page))
    case = case_mod.build(theirs, ours_bare)
    assert case.not_addressed
    assert "This one needs them" in case.describe()


def test_a_craft_win_is_never_a_reason_to_write():
    theirs, ours = _reports()
    case = case_mod.build(theirs, ours)
    assert all(point.tier != standard.CRAFT for point in case.fixed)
    assert case.craft


def test_a_business_with_no_site_gets_a_case_rather_than_an_error():
    """No site to compare is not a checker that failed — it is the clearest case there is."""

    _, ours = _reports()
    case = case_mod.build(None, ours, has_site=False)
    assert case.status == case_mod.NO_SITE_TO_COMPARE
    assert case.offered
    assert all(point.tier in standard.APPROACHABLE_TIERS for point in case.offered)


def test_an_unestablished_absence_is_worded_as_one():
    """The sentence that decides whether this is honest, one more time."""

    _, ours = _reports()
    weak = case_mod.build(None, ours, has_site=False, established_absence=False)
    strong = case_mod.build(None, ours, has_site=False, established_absence=True)
    assert "nothing listed for them" in weak.offered[0].theirs
    assert "they have no website" in strong.offered[0].theirs


def test_the_briefing_names_everything_waiting_on_a_person(tmp_path):
    from prospector.states import NO_SITE_LISTED

    prepared = _prepared(tmp_path, presence_status=NO_SITE_LISTED,
                         language="pt", language_reviewed=False)
    waiting = prepared.blocked_on_a_person
    assert any("NOT established" in item for item in waiting)
    assert any("translation has not been read" in item for item in waiting)
    path = webatron.write_briefing(prepared, operator="Ian McGuane",
                                   costing=costs_mod.cost_of_one_site({}))
    page = path.read_text(encoding="utf-8")
    assert "things need you" in page
    assert "Webatron" in page


def test_a_business_with_no_contact_route_is_flagged_as_unsendable(tmp_path):
    prepared = _prepared(tmp_path,
                         contacts=contacts_mod.Contacts(contacts_mod.NO_ROUTE_FOUND))
    assert any("nowhere" in item for item in prepared.blocked_on_a_person)


def test_the_briefing_says_nothing_has_been_sent_or_published(tmp_path):
    path = webatron.write_briefing(_prepared(tmp_path), operator="Ian McGuane",
                                   costing=costs_mod.cost_of_one_site({}))
    page = path.read_text(encoding="utf-8")
    assert "Nothing here has been sent" in page
    assert "cannot send" in page and "cannot publish" in page


def test_the_digest_carries_the_run_and_its_money(tmp_path):
    prepared = _prepared(tmp_path / "one")
    (tmp_path / "one").mkdir()
    digest = webatron.write_digest([prepared], out_dir=tmp_path, operator="Ian McGuane",
                                   costing=costs_mod.cost_of_one_site({}), area="Donegal",
                                   refused=["Somebody — [contactable] nothing listed"])
    text = digest.read_text(encoding="utf-8")
    assert "Bridge End Barbers" in text
    assert "Refused, and by which stage" in text
    assert "UNPRICED" in text
    assert "No revenue appears here" in text


def test_a_notifier_that_fails_says_so_rather_than_going_quiet(tmp_path):
    """A run nobody hears about is worse than no notifier at all."""

    digest = tmp_path / "WEBATRON.md"
    digest.write_text("x", encoding="utf-8")
    sent, how = webatron.notify("/definitely/not/a/command {digest}", digest)
    assert not sent
    assert "would not run" in how
    sent, how = webatron.notify("", digest)
    assert not sent


def test_a_notifier_receives_the_digest_path(tmp_path):
    digest = tmp_path / "WEBATRON.md"
    digest.write_text("x", encoding="utf-8")
    sent, how = webatron.notify("/bin/sh -c 'test -f \"$0\"' {digest}", digest)
    assert sent, how
