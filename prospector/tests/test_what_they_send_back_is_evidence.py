"""The reply is the point of the gaps, and what comes back has a source like anything else.

The sample ships full of labelled holes — no copy, no prices, no photographs of their own,
hours in the syntax a volunteer typed. Those holes are what gets answered, and the answers
are the difference between a speculative page and their page.

Two rules are under test, and the second is the one that does not move.

**Owner facts outrank map facts.** The map says what a passer-by recorded, sometimes years
ago; the owner says what is true. Both sources survive in the evidence, because "where did
you get my opening hours" needs a better answer than "OpenStreetMap, probably 2019".

**Their copy is evidence; generated copy is still invention.** What changes when a business
replies is not the rule about inventing sentences — it is that the sentences now exist and
have somebody's name on them.
"""
from __future__ import annotations

import json

from prospector import handover
from prospector.business import Business, Fact
from prospector.handover import Handover, merge, read, template_for
from prospector.states import HANDOVER_UNREADABLE, NOTHING_SUPPLIED, SUPPLIED

AT = "2026-08-01T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731
BUSINESS = Business("node/1", FACT("Bridge End Barbers"), FACT("hairdresser"),
                    fields={"phone": FACT("+353 74 912 0001"),
                            "city": FACT("Donegal Town"),
                            "opening_hours": FACT("Tu-Fr 09:00-18:00")})


def _write(folder, **payload):
    template_for(folder)
    data = json.loads((folder / handover.FILENAME).read_text(encoding="utf-8"))
    data.update(payload)
    (folder / handover.FILENAME).write_text(json.dumps(data), encoding="utf-8")
    return folder


def test_an_untouched_template_is_nothing_supplied(tmp_path):
    template_for(tmp_path)
    assert read(tmp_path).status == NOTHING_SUPPLIED


def test_a_file_that_will_not_parse_is_not_nothing_supplied(tmp_path):
    """They may well have replied. Nothing was read, which is a different fact."""

    (tmp_path / handover.FILENAME).write_text("{ oops", encoding="utf-8")
    result = read(tmp_path)
    assert result.status == HANDOVER_UNREADABLE
    assert "not the same as them not answering" in result.describe()


def test_content_with_nobody_behind_it_is_refused(tmp_path):
    """Anything in this file is printed on their page as fact. It needs a source."""

    _write(tmp_path, fields={"phone": "+353 74 912 9999"})
    result = read(tmp_path)
    assert result.status == HANDOVER_UNREADABLE
    assert "no source" in result.reason


def test_what_they_said_replaces_what_the_map_said(tmp_path):
    _write(tmp_path,
           **{"from": {"person": "Cathy Doherty", "role": "owner",
                       "medium": "email", "on": "2026-08-27"},
              "fields": {"opening_hours": "Tue-Sat 9am-6pm, closed Mondays"}})
    updated = merge(BUSINESS, read(tmp_path))
    hours = updated.get("opening_hours")
    assert hours.value == "Tue-Sat 9am-6pm, closed Mondays"
    assert hours.source == "owner:Cathy Doherty via email on 2026-08-27"


def test_a_field_they_did_not_mention_keeps_its_mapped_value_and_its_provenance(tmp_path):
    """The reply was about the hours. Losing the address to it would be absurd."""

    _write(tmp_path,
           **{"from": {"person": "Cathy Doherty", "role": "owner", "medium": "email",
                       "on": "2026-08-27"},
              "fields": {"opening_hours": "Tue-Sat 9am-6pm"}})
    updated = merge(BUSINESS, read(tmp_path))
    assert updated.get("city").value == "Donegal Town"
    assert updated.get("city").source == "openstreetmap:node/1"


def test_their_words_appear_on_the_page_exactly_as_written(tmp_path):
    from prospector.site import render

    _write(tmp_path,
           **{"from": {"person": "Cathy Doherty", "role": "owner", "medium": "email",
                       "on": "2026-08-27"},
              "copy": {"about": "Two chairs, no appointments, and the kettle is on."}})
    supplied = read(tmp_path)
    page = render(BUSINESS, operator="Ian McGuane", copy=supplied.copy)
    assert "Two chairs, no appointments, and the kettle is on." in page


def test_a_gap_they_have_filled_stops_being_advertised_as_a_gap(tmp_path):
    from prospector.site import render

    _write(tmp_path,
           **{"from": {"person": "Cathy Doherty", "role": "owner", "medium": "email",
                       "on": "2026-08-27"},
              "copy": {"about": "Two chairs, no appointments.",
                       "services": "Cuts, beard trims, wet shaves."}})
    supplied = read(tmp_path)
    page = render(BUSINESS, operator="Ian McGuane", copy=supplied.copy)
    # The photographs gap survives, because they sent none.
    assert "What is missing" in page
    assert page.count('class="gap"') == 1


def test_their_own_sentences_are_sourced_and_do_not_trip_the_verifier(tmp_path):
    """A claim the business made about itself is a claim with a source.

    "Family-run since 1998" written by anything else is invention and stays refused; the
    same sentence, sent by the owner, is a fact — and the difference is recorded rather
    than assumed.
    """

    from prospector.site import render
    from prospector.states import VERIFIED
    from prospector.verify import verify

    words = "Family-run since 1998, and still on the same street."
    page = render(BUSINESS, operator="Ian McGuane", copy={"about": words})
    evidence = {"language": "en", "copy": {"about": words},
                "business": {"name": {"value": "Bridge End Barbers"},
                             "kind": {"value": "hairdresser"},
                             "fields": {"phone": {"value": "+353 74 912 0001"}},
                             "raw": {"tags": {}}}, "images": []}
    assert verify(page, evidence, operator="Ian McGuane").status == VERIFIED


def test_the_same_sentence_with_nobody_behind_it_is_still_refused():
    """The rule that does not move when a business replies."""

    from prospector.site import render
    from prospector.states import UNSOURCED_CLAIMS
    from prospector.verify import verify

    page = render(BUSINESS, operator="Ian McGuane",
                  copy={"about": "Family-run since 1998, and still on the same street."})
    evidence = {"language": "en", "copy": {},
                "business": {"name": {"value": "Bridge End Barbers"},
                             "kind": {"value": "hairdresser"}, "fields": {},
                             "raw": {"tags": {}}}, "images": []}
    verdict = verify(page, evidence, operator="Ian McGuane")
    assert verdict.status == UNSOURCED_CLAIMS
    assert any(p.code == "UNSOURCED_CLAIM" for p in verdict.problems)
