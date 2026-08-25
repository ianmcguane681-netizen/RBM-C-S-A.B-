"""The standard is the part a business owner could argue with, so it has to be arguable.

Everything else in this package refuses to guess, and this is where the guessing would
otherwise happen: "their website is bad" is taste until the criteria are written down. The
tests here defend the three properties that make the written version worth anything.

**Nothing is summed.** A site that does not work on a phone cannot pass on the strength of
its meta description, and there is no total for it to pass on.

**Only the first three tiers are a reason to approach anybody.** Craft findings are real
and are recorded, and a cold email about a missing favicon is how this activity earns a
reputation.

**The tool meets its own standard.** A page pitched at a business whose site fails
`VIEWPORT` cannot itself fail `VIEWPORT`.
"""
from __future__ import annotations

from prospector import standard
from prospector.business import Business, Fact
from prospector.site import render
from prospector.standard import (APPROACHABLE_TIERS, BLOCKING, CONVERSION, CRAFT, FAILS,
                                 MEETS, MOBILE, NOT_ASSESSED, assess)

AT = "2026-08-25T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731

MODERN = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width, initial-scale=1">'
          '<meta name="description" content="A shop"><title>A shop</title>'
          '<link rel="icon" href="/i.png">'
          '<meta property="og:title" content="A shop">'
          '<meta property="og:image" content="/i.png">'
          '<script type="application/ld+json">{"@type":"LocalBusiness",'
          '"address":{"streetAddress":"1 Main Street"},"openingHours":"Mo-Fr 09:00-17:00"}'
          '</script></head><body><h1>A shop</h1>'
          '<p>Opening hours: Mon-Fri 09:00-17:00</p>'
          '<p><a href="tel:+353740000000">Call</a></p>'
          '<p><a href="mailto:hi@shop.example">Email</a></p>'
          '<p>1 Main Street, Donegal Town, F94 X2P8</p></body></html>')


def _state(report, code):
    return next(a.state for a in report.assessments if a.code == code)


def test_a_modern_page_meets_every_criterion():
    """Otherwise the standard is a machine for generating false accusations."""

    report = assess(MODERN, status=200, https_available=True, reached=True,
                    byte_size=len(MODERN))
    failed = [a.code for a in report.assessments if a.state == FAILS]
    assert failed == []


def test_a_desktop_era_page_fails_the_mobile_tier_by_name():
    page = ('<html><head><title>Old</title></head><body>'
            '<table width="980"><tr><td><font size="2">Call 074 912 0001</font>'
            '</td></tr></table></body></html>')
    report = assess(page, status=200, https_available=True, reached=True,
                    byte_size=len(page))
    assert _state(report, "VIEWPORT") == FAILS
    assert _state(report, "NO_FIXED_WIDTH") == FAILS
    assert _state(report, "NO_LEGACY_MARKUP") == FAILS
    assert report.lead.tier == MOBILE


def test_a_phone_number_that_is_only_text_fails_conversion():
    """The highest-value finding this tool produces, and invisible on a desktop."""

    page = MODERN.replace('<a href="tel:+353740000000">Call</a>', "074 912 0001")
    report = assess(page, status=200, https_available=True, reached=True,
                    byte_size=len(page))
    assert _state(report, "PHONE_TAPPABLE") == FAILS
    assert "tapped" in next(a.detail for a in report.assessments
                            if a.code == "PHONE_TAPPABLE")


def test_craft_failures_alone_are_never_a_reason_to_approach_a_business():
    """The rule the tiers exist to produce, and the one that keeps this defensible."""

    page = (MODERN.replace('<meta name="description" content="A shop">', "")
                  .replace('<link rel="icon" href="/i.png">', ""))
    report = assess(page, status=200, https_available=True, reached=True,
                    byte_size=len(page))
    assert [a.code for a in report.failures()] == ["META_DESCRIPTION", "FAVICON"]
    assert report.approachable_failures == ()
    assert report.lead is None


def test_the_worst_tier_leads_even_when_several_things_are_wrong():
    """A dead site and a missing favicon are both failures; only one opens an email."""

    page = MODERN.replace('<link rel="icon" href="/i.png">', "")
    report = assess(page, status=503, https_available=False, reached=True,
                    byte_size=len(page))
    assert report.lead.tier == BLOCKING
    assert report.lead.code == "NOT_AN_ERROR"


def test_a_criterion_that_could_not_be_evaluated_blocks_rather_than_passing():
    """`https_available=None` means the fetcher could not tell — never that it is fine."""

    report = assess(MODERN, status=200, https_available=None, reached=True,
                    byte_size=len(MODERN))
    assert _state(report, "HTTPS") == NOT_ASSESSED
    assert report.blocked
    assert report.approachable_failures == ()


def test_the_older_viewport_form_is_not_reported_as_a_failure():
    """`initial-scale=1` gets browsers to the same place, and a wrong sentence in an email
    costs more than this criterion is worth being strict about."""

    page = MODERN.replace('content="width=device-width, initial-scale=1"',
                          'content="initial-scale=1,user-scalable=yes"')
    report = assess(page, status=200, https_available=True, reached=True,
                    byte_size=len(page))
    assert _state(report, "VIEWPORT") == MEETS


def test_font_tags_alone_are_untidy_rather_than_broken():
    """Plenty of usable pages carry one. The failure is a fixed-width table layout."""

    page = MODERN.replace("<h1>A shop</h1>", "<h1><font>A shop</font></h1>")
    report = assess(page, status=200, https_available=True, reached=True,
                    byte_size=len(page))
    assert _state(report, "NO_LEGACY_MARKUP") == MEETS


def test_blocking_zoom_fails_because_somebody_needs_larger_text():
    page = MODERN.replace('content="width=device-width, initial-scale=1"',
                          'content="width=device-width, user-scalable=no"')
    report = assess(page, status=200, https_available=True, reached=True,
                    byte_size=len(page))
    assert _state(report, "ZOOM_ALLOWED") == FAILS


def test_there_is_no_score_anywhere_in_the_report():
    """Not a stylistic objection. A total is what lets a phone failure be outvoted."""

    report = assess(MODERN, status=200, https_available=True, reached=True,
                    byte_size=len(MODERN))
    for attribute in ("score", "total", "points", "rating", "grade", "percent"):
        assert not hasattr(report, attribute)
    assert set(a.state for a in report.assessments) <= {MEETS, FAILS, NOT_ASSESSED}


def test_every_criterion_says_why_it_matters_to_the_business():
    """Because the first question a recipient asks is what exactly is wrong with it."""

    for criterion in standard.CRITERIA:
        assert criterion.why.strip()
        assert criterion.how.strip()
        assert criterion.tier in (BLOCKING, MOBILE, CONVERSION, CRAFT)


def test_the_sample_page_meets_the_standard_it_judges_others_by():
    """Emailing somebody about their viewport tag, attaching a page that fails it, is the
    single most avoidable way to discredit this whole exercise."""

    business = Business(
        "node/1", FACT("Bridge End Barbers"), FACT("hairdresser"),
        fields={"phone": FACT("+353 74 912 0001"), "housenumber": FACT("3"),
                "street": FACT("Main Street"), "city": FACT("Donegal Town"),
                "postcode": FACT("F94 X2P8"), "email": FACT("hello@example.ie"),
                "opening_hours": FACT("Tu-Fr 09:00-18:00")},
        raw={"lat": 54.65, "lon": -8.11})
    page = render(business, operator="Ian McGuane", sources=["openstreetmap:node/1"])
    report = assess(page, status=200, https_available=True, reached=True,
                    byte_size=len(page))
    failed = [a.code for a in report.assessments if a.state == FAILS]
    assert failed == []


def test_a_business_name_containing_a_script_tag_cannot_escape_the_structured_data():
    """The JSON-LD is built from a name a stranger controls, and json.dumps escapes quotes
    and nothing else."""

    hostile = Business("node/2", FACT('Bob</script><script>alert(1)</script>'),
                       FACT("shop"), fields={"city": FACT("Town")})
    page = render(hostile, operator="Ian McGuane")
    assert "<script>alert(1)</script>" not in page
    assert "\\u003c" in page
