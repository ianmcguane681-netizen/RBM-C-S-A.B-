"""The pipeline stops one step short of the only irreversible action it could take.

A folder on disk can be deleted, a wrong reading can be corrected, a page can be rebuilt.
An email that has arrived at a business cannot be recalled, and the difference between the
two is the whole reason there is no sending code in this package. These tests assert the
absence, because an absence is exactly the kind of property that gets filled in by someone
being helpful.
"""
from __future__ import annotations

import pathlib

from prospector import cli
from prospector.business import Business, Fact
from prospector.cascade import Decision, PREPARE
from prospector.dossier import write
from prospector.presence import Presence
from prospector.states import NO_SITE_LISTED

AT = "2026-08-25T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731
PACKAGE = pathlib.Path(__file__).resolve().parent.parent

BUSINESS = Business("node/1", FACT("Bridge End Barbers"), FACT("hairdresser"),
                    fields={"phone": FACT("+353 74 912 0001"), "city": FACT("Town")})
DECISION = Decision(PREPARE, "presence", "no website listed",
                    opening_claim="I could not find a website listed for you.")


def test_the_package_contains_no_way_to_send_an_email():
    """`smtplib` is not imported anywhere, and this test is why it must stay that way.

    The parent repository makes the same kind of assertion about its chain lane: the
    inability to sign is a property of the code, not a setting, and a test guards it so
    that adding the capability has to be a deliberate, visible act.
    """

    sources = [p for p in PACKAGE.rglob("*.py") if "tests" not in p.parts]
    assert sources
    for path in sources:
        text = path.read_text(encoding="utf-8")
        assert "smtplib" not in text, f"{path} imports smtplib"
        assert "sendmail" not in text, f"{path} can send mail"


def test_the_draft_note_says_it_has_not_been_sent(tmp_path):
    folder = write(BUSINESS, Presence(NO_SITE_LISTED), None, DECISION,
                   out_dir=tmp_path, operator="Ian McGuane")
    note = (folder / "NOTE.md").read_text(encoding="utf-8")
    assert "Nothing has been sent" in note
    assert "for you to read, edit and send yourself" in note


def test_the_dossier_records_where_every_fact_came_from(tmp_path):
    """So that "where did you get my phone number" has a one-line answer, written down."""

    folder = write(BUSINESS, Presence(NO_SITE_LISTED), None, DECISION,
                   out_dir=tmp_path, operator="Ian McGuane")
    evidence = (folder / "EVIDENCE.md").read_text(encoding="utf-8")
    assert "openstreetmap:node/1" in evidence
    assert "+353 74 912 0001" in evidence


def test_a_weak_presence_carries_its_warning_into_the_dossier(tmp_path):
    """The person reading the folder is warned in the folder, not only in a run log."""

    folder = write(BUSINESS, Presence(NO_SITE_LISTED), None, DECISION,
                   out_dir=tmp_path, operator="Ian McGuane")
    evidence = (folder / "EVIDENCE.md").read_text(encoding="utf-8")
    assert "Do not write that this business has no website" in evidence


def test_an_automation_cannot_sign_a_sample_page(capsys):
    """Carried over from the parent repository's refused prefixes, for the same reason.

    Approaching a stranger's business over somebody's name is a judgement a person makes.
    The signature on the page is that person's, so a run that tries to sign as an agent is
    refused rather than quietly attributed.
    """

    for name in ("agent: prospector", "ai:builder", "bot: outreach"):
        code = cli.main(["--area", "Anywhere", "--operator", name, "--dry",
                         "--from-file", str(PACKAGE / "fixtures/synthetic-area.overpass.json")])
        assert code == 2
        assert "names an automation" in capsys.readouterr().err
