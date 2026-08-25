"""Crossing a border breaks three things, and only one of them is the words.

The words are the visible one: a sample site for a padaria in Braga written in English is
a sample of somebody else's idea of their business. The other two are quieter and just as
telling — an address printed in the wrong order looks wrong to the person who lives there,
and the rule about sending a stranger a commercial email is different on the other side of
a border in a way that is nobody's intuition.

The property under test is the same one the whole package is built on, wearing its most
plausible disguise. A missing translation is the perfect silent failure: the page still
renders, it still looks finished, and the only sign anything went wrong is that a shop in
Kraków has been sent a page in a language nobody there asked for. So an unavailable
language stops that business and says which one was wanted.
"""
from __future__ import annotations

import pathlib

from prospector import cascade, cli
from prospector.business import Business, Fact
from prospector.cascade import Decision, PREPARE, INDETERMINATE
from prospector.countries import COUNTRY_KNOWN, COUNTRY_UNKNOWN, lookup, from_area_tags
from prospector.locales import (CATALOGUE, LANGUAGE_AVAILABLE, LANGUAGE_UNAVAILABLE,
                                REQUIRED, choose)
from prospector.site import render

AT = "2026-08-25T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731
PACKAGE = pathlib.Path(__file__).resolve().parent.parent


def test_a_language_with_no_strings_refuses_rather_than_falling_back():
    choice = choose("sv")
    assert choice.status == LANGUAGE_UNAVAILABLE
    assert "sv" in choice.describe()
    assert "worse than none" in choice.describe()


def test_no_language_and_no_country_is_a_refusal_not_english():
    """The most tempting default in the package, and the one that would go unnoticed."""

    assert choose().status == LANGUAGE_UNAVAILABLE


def test_the_country_picks_the_language_when_nobody_said():
    choice = choose(country_languages=("pt",), country="Portugal")
    assert choice.status == LANGUAGE_AVAILABLE
    assert choice.locale.code == "pt"
    assert "usual language of business" in choice.basis


def test_an_explicit_language_is_honoured_over_the_country():
    """Ireland does business in English; a run asked for Irish gets Irish."""

    choice = choose("ga", country_languages=("en", "ga"), country="Ireland")
    assert choice.locale.code == "ga"
    assert choice.basis == "you asked for it"


def test_every_locale_carries_every_string():
    """A missing key is one English sentence in the middle of a page in another language."""

    for code, locale in CATALOGUE.items():
        missing = [key for key in REQUIRED if key not in locale.strings]
        assert not missing, f"{code} is missing {missing}"


def test_only_english_claims_to_have_been_reviewed():
    """A translation nobody has checked is not one you send over your own name.

    They are usable and every artefact built from one says so. What is refused is the
    quiet version, where an unreviewed translation is indistinguishable from a checked one.
    """

    assert CATALOGUE["en"].reviewed
    for code, locale in CATALOGUE.items():
        if code != "en":
            assert not locale.reviewed
            assert "native speaker" in locale.caveat


def test_the_page_is_built_in_the_chosen_language():
    business = Business("node/1", FACT("Padaria da Ponte"), FACT("bakery"),
                        fields={"city": FACT("Braga")})
    page = render(business, operator="Ian McGuane", locale="pt")
    assert 'lang="pt"' in page
    assert "Exemplo não oficial" in page
    assert "Unofficial sample" not in page


def test_the_facts_are_never_translated():
    """The street is the street. Rendering it into English would invent an address."""

    business = Business("node/1", FACT("Padaria da Ponte"), FACT("bakery"),
                        fields={"street": FACT("Rua Inventada"), "city": FACT("Braga")})
    for code in ("pt", "en", "de"):
        page = render(business, operator="Ian McGuane", locale=code)
        assert "Rua Inventada" in page
        assert "Invented Street" not in page


def test_a_name_the_map_itself_carries_in_another_language_is_a_fact_and_may_be_used():
    business = Business("node/1", FACT("Oficina Silva"), FACT("car_repair"),
                        fields={"city": FACT("Braga")},
                        raw={"tags": {"name": "Oficina Silva", "name:en": "Silva Garage"}})
    assert business.name_in("en").value == "Silva Garage"
    assert business.name_in("pt").value == "Oficina Silva"
    # And it keeps the provenance of the name it came from, because it is the same tag set.
    assert business.name_in("en").source == business.name.source


def test_the_address_is_written_the_way_the_country_writes_it():
    """Same facts, different order. The comma after the postcode is the giveaway."""

    business = Business("node/1", FACT("Bäckerei Hoffmann"), FACT("bakery"),
                        fields={"housenumber": FACT("12"), "street": FACT("Hauptstraße"),
                                "postcode": FACT("10115"), "city": FACT("Berlin")})
    german = render(business, operator="Ian", locale="de")
    english = render(business, operator="Ian", locale="en")
    assert "Hauptstraße 12, 10115 Berlin" in german
    assert "12 Hauptstraße, Berlin, 10115" in english


def test_an_unavailable_language_blocks_a_business_that_would_otherwise_be_prepared():
    from prospector.presence import Presence
    from prospector.seen import Sighting
    from prospector.states import NEW, NO_SITE_LISTED

    business = Business("node/1", FACT("Sklep Rogowski"), FACT("bakery"),
                        fields={"city": FACT("Kraków"), "phone": FACT("+48 12 000")})
    decided = cascade.decide(business, Sighting(NEW, "node/1"), Presence(NO_SITE_LISTED),
                             None)
    assert decided.status == PREPARE
    blocked = cascade.with_language(decided, choose(country_languages=("pl",),
                                                    country="Poland"))
    assert blocked.status == INDETERMINATE
    assert blocked.stage == "language"


def test_the_country_comes_from_the_areas_iso_code():
    """Which is what lets --area "County Donegal" know it is in Ireland."""

    country = from_area_tags({"ISO3166-2": "IE-DL"})
    assert country.status == COUNTRY_KNOWN
    assert country.code == "IE"


def test_an_unknown_country_prints_the_strict_reading_of_the_sending_rules():
    """Fail toward stopping, applied where being wrong costs money rather than face."""

    from prospector.countries import UNKNOWN

    assert UNKNOWN.status == COUNTRY_UNKNOWN
    assert "assume consent is required" in UNKNOWN.outreach_rule


def test_the_sending_rules_differ_by_country_and_canada_is_the_strict_one():
    assert "consent" in lookup("CA").outreach_rule
    assert "Consent is not required" in lookup("US").outreach_rule
    assert lookup("CA").outreach_rule != lookup("US").outreach_rule


def test_a_run_in_another_country_builds_in_that_countrys_language(tmp_path, capsys):
    code = cli.main(["--area", "Braga", "--operator", "Ian McGuane",
                     "--from-file", str(PACKAGE / "fixtures/synthetic-area-pt.overpass.json"),
                     "--out", str(tmp_path / "d"), "--register", str(tmp_path / "p.json"),
                     "--images", "none", "--no-fetch"])
    assert code == 0
    out = capsys.readouterr().out
    assert "[pt]" in out
    assert "UNREVIEWED TRANSLATION" in out


def test_the_note_carries_the_local_sending_rule_and_an_english_gloss(tmp_path):
    from prospector.dossier import write
    from prospector.presence import Presence
    from prospector.states import NO_SITE_LISTED

    business = Business("node/1", FACT("Padaria da Ponte"), FACT("bakery"),
                        fields={"city": FACT("Braga"), "phone": FACT("+351 253 000 001")})
    folder = write(business, Presence(NO_SITE_LISTED), None,
                   Decision(PREPARE, "presence", "no site listed",
                            claim_key="claim_no_site_listed",
                            opening_claim="I could not find a website listed for you."),
                   out_dir=tmp_path, operator="Ian McGuane", locale="pt",
                   country=lookup("PT"), fetch_images=False)
    note = (folder / "NOTE.md").read_text(encoding="utf-8")
    assert "Não encontrei nenhum site" in note
    assert "GDPR" in note
    # The operator has to be able to read what they are about to send over their own name.
    assert "What it says, in English" in note


def test_a_page_in_another_language_is_verified_against_that_languages_banner(tmp_path):
    """An English banner check on a Portuguese page fails every correct page.

    And, worse, passes any page that quietly reverted to English — which is the failure
    the language stage exists to prevent, arriving through the checker instead.
    """

    from prospector.dossier import write
    from prospector.presence import Presence
    from prospector.states import NO_SITE_LISTED, VERIFIED
    from prospector.verify import verify_folder

    business = Business("node/1", FACT("Padaria da Ponte"), FACT("bakery"),
                        fields={"city": FACT("Braga"), "phone": FACT("+351 253 000 001")})
    folder = write(business, Presence(NO_SITE_LISTED), None,
                   Decision(PREPARE, "presence", "no site listed",
                            claim_key="claim_no_site_listed", opening_claim="..."),
                   out_dir=tmp_path, operator="Ian McGuane", locale="pt",
                   country=lookup("PT"), fetch_images=False)
    assert verify_folder(folder).status == VERIFIED


def test_a_page_whose_language_is_unrecorded_cannot_be_verified():
    from prospector.states import COULD_NOT_VERIFY
    from prospector.verify import verify

    evidence = {"business": {"name": {"value": "X"}, "kind": {"value": "shop"},
                             "fields": {}, "raw": {"tags": {}}}, "images": []}
    verdict = verify("<html><body>anything</body></html>", evidence)
    assert verdict.status == COULD_NOT_VERIFY
    assert "what language" in verdict.reason
