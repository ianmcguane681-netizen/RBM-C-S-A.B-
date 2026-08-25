"""Once each page is designed rather than filled in, the guarantee has to move.

A single template can be audited once: it either invents facts or it does not, and the
answer holds for every business it is stamped onto. That is also what makes it worth what a
template is worth. The moment a page is designed for the business in front of you — by a
person, or by a model given the brief — nobody has read it before it exists, so the promise
"nothing on this page is invented" has to be enforced on the output instead.

These tests are that enforcement. They are written against the specific things a model
supplies without noticing, because a page with a plausible founding year reads better than
a page with a gap, and reading better is exactly what a generator optimises for.
"""
from __future__ import annotations

from prospector.states import COULD_NOT_VERIFY, UNSOURCED_CLAIMS, VERIFIED
from prospector.verify import verify

EVIDENCE = {
    "language": "en",
    "business": {
        "name": {"value": "Bridge End Barbers"},
        "kind": {"value": "hairdresser"},
        "fields": {"phone": {"value": "+353 74 912 0001"},
                   "street": {"value": "Main Street"}},
        "raw": {"tags": {"name": "Bridge End Barbers", "phone": "+353 74 912 0001"}},
    },
    "images": [],
}

GOOD = ('<html lang="en"><head><meta name="robots" content="noindex, nofollow">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
        '<p>Unofficial sample prepared by Ian McGuane. Not affiliated with Bridge End '
        'Barbers.</p><h1>Bridge End Barbers</h1><p>Main Street</p>'
        '<p>+353 74 912 0001</p></body></html>')


def _with(extra: str) -> str:
    return GOOD.replace("</body>", f"{extra}</body>")


def test_a_page_built_only_from_the_evidence_passes():
    assert verify(GOOD, EVIDENCE, operator="Ian McGuane").status == VERIFIED


def test_an_invented_founding_year_is_caught():
    verdict = verify(_with("<p>Serving the town since 1962.</p>"), EVIDENCE,
                     operator="Ian McGuane")
    assert verdict.status == UNSOURCED_CLAIMS
    assert any(p.code == "UNSOURCED_YEAR" for p in verdict.problems)


def test_an_invented_phone_number_is_caught():
    verdict = verify(_with("<p>Call 087 555 1234</p>"), EVIDENCE, operator="Ian McGuane")
    assert any(p.code == "UNSOURCED_NUMBER" for p in verdict.problems)


def test_an_invented_price_is_caught():
    verdict = verify(_with("<p>Dry cut €15</p>"), EVIDENCE, operator="Ian McGuane")
    assert any(p.code == "UNSOURCED_PRICE" for p in verdict.problems)


def test_the_house_style_of_invented_copy_is_caught():
    """"Family-run", "award-winning", "fully insured" — none of it came from a map."""

    for phrase in ("A family-run barbers.", "Award-winning cuts.", "Fully insured."):
        verdict = verify(_with(f"<p>{phrase}</p>"), EVIDENCE, operator="Ian McGuane")
        assert any(p.code == "UNSOURCED_CLAIM" for p in verdict.problems), phrase


def test_an_invented_claim_hidden_in_alt_text_is_caught():
    """Alt text is read aloud to a person, so it is page text and can carry a claim."""

    page = _with('<img src="x.jpg" alt="Family-run since 1962">')
    verdict = verify(page, EVIDENCE, operator="Ian McGuane")
    assert any(p.code == "UNSOURCED_CLAIM" for p in verdict.problems)


def test_a_page_that_drops_the_sample_banner_fails():
    """Which is the difference between speculative work and a forgery of their site."""

    stripped = GOOD.replace("Unofficial sample prepared by Ian McGuane. Not affiliated "
                            "with Bridge End Barbers.", "")
    verdict = verify(stripped, EVIDENCE, operator="Ian McGuane")
    assert any(p.code == "NO_SAMPLE_BANNER" for p in verdict.problems)
    assert any(p.code == "NO_DISCLAIMER" for p in verdict.problems)


def test_a_page_that_would_be_indexed_fails():
    """A sample about somebody's business must never compete with them in search."""

    indexable = GOOD.replace('<meta name="robots" content="noindex, nofollow">', "")
    verdict = verify(indexable, EVIDENCE, operator="Ian McGuane")
    assert any(p.code == "INDEXABLE" for p in verdict.problems)


def test_a_page_that_could_not_be_checked_is_not_a_page_that_passed():
    assert verify("", EVIDENCE).status == COULD_NOT_VERIFY
    assert verify(GOOD, {}).status == COULD_NOT_VERIFY


def test_the_reference_render_passes_its_own_verifier(tmp_path):
    """A generator that exempts its own output has a guarantee that stops at the first edit."""

    from prospector.business import Business, Fact
    from prospector.cascade import Decision, PREPARE
    from prospector.dossier import write
    from prospector.presence import Presence
    from prospector.states import NO_SITE_LISTED
    from prospector.verify import verify_folder

    at = "2026-08-25T00:00:00+00:00"
    fact = lambda v: Fact(v, "openstreetmap:node/1", at)  # noqa: E731
    business = Business("node/1", fact("Bridge End Barbers"), fact("hairdresser"),
                        fields={"phone": fact("+353 74 912 0001"), "city": fact("Town"),
                                "opening_hours": fact("Tu-Fr 09:00-18:00")})
    folder = write(business, Presence(NO_SITE_LISTED), None,
                   Decision(PREPARE, "presence", "no site listed", opening_claim="Hello."),
                   out_dir=tmp_path, operator="Ian McGuane", fetch_images=False)
    assert verify_folder(folder).status == VERIFIED
