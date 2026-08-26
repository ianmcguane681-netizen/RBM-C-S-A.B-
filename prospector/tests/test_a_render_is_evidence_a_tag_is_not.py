"""What the markup says was intended, and what the browser says happens, are two claims.

A page can carry a perfect viewport tag and still push a 900px table off the side of a
phone. It can be small and still show nothing for eight seconds. The three criteria in this
file are the ones markup cannot answer, and they exist because the tool's whole pitch is a
finished thing shown to somebody — which means the evidence behind the approach has to be
the same kind of thing: what actually happens, in a window the size of a phone.

Two properties are defended here, and the second is the one that keeps this honest.

**A browser that is not installed never produces a pass.** The criteria come back
`NOT_ASSESSED` and the run says the mobile checks were markup-only, which is a weaker claim
and is stated as one.

**A render whose stylesheets did not arrive is not a render of that page.** Screenshotting
somebody's site with its CSS missing, and putting it in an email beside your own work, is a
misrepresentation of theirs. That capture is `CAPTURE_INCOMPLETE`: the picture is kept for
a person to look at and no criterion is decided from it.
"""
from __future__ import annotations

import pytest

from prospector import browser, standard
from prospector.browser import (BROWSER_UNAVAILABLE, CAPTURE_INCOMPLETE, CAPTURED, Capture)
from prospector.standard import FAILS, MEETS, NOT_ASSESSED, assess

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

FITS = Capture(CAPTURED, url="https://shop.example", scroll_width=390, inner_width=390,
               smallest_font_px=16.0, first_paint_ms=900.0, load_ms=1200.0)


def _state(report, code):
    return next(a.state for a in report.assessments if a.code == code)


def _assess(capture=None):
    return assess(MODERN, status=200, https_available=True, reached=True,
                  byte_size=len(MODERN), capture=capture)


def test_without_a_browser_the_measured_criteria_are_unassessed_never_met():
    report = _assess(None)
    for code in ("NO_SIDEWAYS_SCROLL", "READABLE_TEXT", "PAINTS_QUICKLY"):
        assert _state(report, code) == NOT_ASSESSED
    assert report.depth == standard.MARKUP_ONLY
    assert "markup" in report.describe().splitlines()[0]


def test_a_missing_browser_does_not_block_the_whole_run():
    """The absence is a fact about the machine, stated once, not a mystery about this site.

    Blocking on it would mean a run without Playwright installed could never conclude
    anything about anybody, which is a worse answer than a stated weaker one.
    """

    assert not _assess(None).blocked


def test_a_render_that_fits_the_phone_meets_the_criterion():
    report = _assess(FITS)
    assert _state(report, "NO_SIDEWAYS_SCROLL") == MEETS
    assert report.depth == standard.RENDERED


def test_a_document_wider_than_the_window_fails_however_good_the_markup_is():
    """The point of the stage. Perfect viewport tag, 520px of page off the side."""

    wide = Capture(CAPTURED, scroll_width=910, inner_width=390, smallest_font_px=16.0,
                   first_paint_ms=800.0)
    report = _assess(wide)
    assert _state(report, "VIEWPORT") == MEETS
    assert _state(report, "NO_SIDEWAYS_SCROLL") == FAILS
    assert "910px wide on a 390px phone screen" in next(
        a.detail for a in report.assessments if a.code == "NO_SIDEWAYS_SCROLL")


def test_a_desktop_layout_the_phone_shrinks_is_a_failure_not_a_pass():
    """The subtlety that makes this stage worth having.

    A page with no viewport tag lays out at ~980px and lets the phone scale the whole
    thing down, so nothing overflows its own layout: measured against `innerWidth` it
    passes, and the person holding the phone is reading 5px text. Measured against the
    screen it fails, which is what they experience.
    """

    shrunk = Capture(CAPTURED, scroll_width=988, inner_width=988, width=390,
                     smallest_font_px=13.0, first_paint_ms=300.0)
    report = _assess(shrunk)
    assert _state(report, "NO_SIDEWAYS_SCROLL") == FAILS
    assert "scales down to fit" in next(a.detail for a in report.assessments
                                        if a.code == "NO_SIDEWAYS_SCROLL")
    assert _state(report, "READABLE_TEXT") == FAILS
    assert "5.1px on the screen" in next(a.detail for a in report.assessments
                                         if a.code == "READABLE_TEXT")


def test_a_couple_of_pixels_of_slack_is_not_a_finding():
    """Sub-pixel rounding on a scaled render is not a defect somebody should be emailed
    about."""

    report = _assess(Capture(CAPTURED, scroll_width=392, inner_width=390,
                             smallest_font_px=16.0, first_paint_ms=500.0))
    assert _state(report, "NO_SIDEWAYS_SCROLL") == MEETS


def test_text_too_small_to_read_standing_up_fails():
    report = _assess(Capture(CAPTURED, scroll_width=390, inner_width=390,
                             smallest_font_px=9.0, first_paint_ms=500.0))
    assert _state(report, "READABLE_TEXT") == FAILS


def test_a_slow_first_paint_fails_and_says_which_measurement_it_used():
    report = _assess(Capture(CAPTURED, scroll_width=390, inner_width=390,
                             smallest_font_px=16.0, first_paint_ms=6200.0))
    assert _state(report, "PAINTS_QUICKLY") == FAILS
    assert "first paint at 6.2s" in next(a.detail for a in report.assessments
                                         if a.code == "PAINTS_QUICKLY")


def test_the_load_event_stands_in_where_paint_timing_is_unavailable():
    report = _assess(Capture(CAPTURED, scroll_width=390, inner_width=390,
                             smallest_font_px=16.0, first_paint_ms=None, load_ms=400.0))
    assert _state(report, "PAINTS_QUICKLY") == MEETS
    assert "the load event" in next(a.detail for a in report.assessments
                                    if a.code == "PAINTS_QUICKLY")


def test_a_capture_missing_the_pages_own_stylesheets_decides_nothing():
    """Screenshotting a stranger's site with its CSS missing, and putting it beside your
    own work, misrepresents theirs."""

    broken = Capture(CAPTURE_INCOMPLETE, url="https://shop.example",
                     scroll_width=1400, inner_width=390, smallest_font_px=8.0,
                     failed_subresources=("stylesheet 404: /site.css",),
                     screenshot_path="theirs.png")
    assert not broken.usable
    report = _assess(broken)
    assert _state(report, "NO_SIDEWAYS_SCROLL") == NOT_ASSESSED
    assert report.depth == standard.MARKUP_ONLY


def test_an_unmeasured_number_never_prints_as_a_zero():
    """A first paint of 0ms would be the best number on the page."""

    described = Capture(CAPTURED, scroll_width=390, inner_width=390,
                        smallest_font_px=None, first_paint_ms=None).describe()
    assert "not measured" in described
    assert "0ms" not in described


def test_an_unavailable_browser_says_what_a_person_can_go_and_do():
    capture = Capture(BROWSER_UNAVAILABLE, reason="Playwright is not installed. `pip "
                                                  "install playwright` ...")
    assert "pip install playwright" in capture.describe()
    assert "not the same as them passing" in capture.describe()


@pytest.mark.skipif(not browser.available()[0], reason="Playwright is not installed here")
def test_a_real_browser_measures_the_sample_page(tmp_path):
    """The end of the argument: the page this package produces, opened at phone size.

    Skipped rather than failed where no browser is installed, because the point of the
    stage is that it is optional — but where one IS installed, the sample had better fit
    the screen it is pitched about.
    """

    from prospector.business import Business, Fact
    from prospector.site import render

    at = "2026-08-25T00:00:00+00:00"
    fact = lambda v: Fact(v, "openstreetmap:node/1", at)  # noqa: E731
    business = Business("node/1", fact("Bridge End Barbers"), fact("hairdresser"),
                        fields={"phone": fact("+353 74 912 0001"),
                                "street": fact("Main Street"), "city": fact("Donegal Town"),
                                "postcode": fact("F94 X2P8"),
                                "opening_hours": fact("Tu-Fr 09:00-18:00")},
                        raw={"lat": 54.65, "lon": -8.11})
    page = tmp_path / "index.html"
    page.write_text(render(business, operator="Ian McGuane"), encoding="utf-8")
    capture = browser.capture(page.resolve().as_uri(), out_path=tmp_path / "shot.png")
    assert capture.status == CAPTURED, capture.describe()
    assert capture.scroll_width <= capture.inner_width + browser.SCROLL_SLACK_PX
    assert capture.smallest_font_px >= browser.MIN_READABLE_PX
    assert (tmp_path / "shot.png").stat().st_size > 1000
