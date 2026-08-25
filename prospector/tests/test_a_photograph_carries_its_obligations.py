"""A photograph on a page about somebody's business makes a claim, and owes something.

Two obligations, from different places, and the tests treat them alike because a page that
breaks either is a page that should not be sent.

**Licences.** A stock photograph is used under a licence with conditions, and attribution
is a condition rather than a courtesy. An NC image cannot be used in commercial work at
all, and an ND image cannot be cropped to a layout, so neither may enter the set — a
judgement not left to whoever is building the page at the time.

**Truth.** A stock photograph of *a* bakery on a page headed with *this* bakery's name says
these are their premises. That is a fact-shaped thing on the page that did not come from
evidence, which is the defect the whole package refuses, so the label is checked as
strictly as the licence.
"""
from __future__ import annotations

import json

from prospector import images as images_mod
from prospector.images import Image, ImageSet, Openverse, gather
from prospector.states import (COULD_NOT_LOOK_FOR_IMAGES, IMAGES_FOUND, LICENSED_STOCK,
                               NO_IMAGE_FOUND, SUBJECT_OWN, UNSOURCED_CLAIMS, VERIFIED)
from prospector.verify import verify

AT = "2026-08-25T00:00:00+00:00"


class _Payload:
    """A stand-in for the Openverse endpoint."""

    def __init__(self, results):
        self.results = results

    def __call__(self, request, timeout=None):
        payload = json.dumps({"results": self.results}).encode("utf-8")

        class _Response:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return False

            def read(self_inner):
                return payload

        return _Response()


def _result(**overrides):
    base = {"url": "https://example.org/photo.jpg", "license": "by", "license_version": "4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "attribution": '"A photo" by Somebody is licensed under CC BY 4.0.',
            "creator": "Somebody", "title": "A photo", "width": 1600, "height": 1200,
            "foreign_landing_url": "https://example.org/photo"}
    base.update(overrides)
    return base


def test_a_licence_forbidding_derivatives_never_enters_the_set():
    """Cropping a photograph to a layout is a derivative work, so ND is not usable here."""

    source = Openverse(opener=_Payload([_result(license="by-nd")]))
    assert source.search("bakery").status == NO_IMAGE_FOUND


def test_a_non_commercial_licence_never_enters_the_set():
    source = Openverse(opener=_Payload([_result(license="by-nc-sa")]))
    assert source.search("bakery").status == NO_IMAGE_FOUND


def test_an_image_too_small_to_build_a_page_around_is_not_offered():
    source = Openverse(opener=_Payload([_result(width=320, height=240)]))
    assert source.search("bakery").status == NO_IMAGE_FOUND


def test_a_usable_image_arrives_with_its_licence_and_attribution():
    source = Openverse(opener=_Payload([_result()]))
    found = source.search("bakery")
    assert found.status == IMAGES_FOUND
    image = found.images[0]
    assert image.licence.startswith("CC BY")
    assert image.attribution
    assert image.must_be_labelled
    assert image.must_be_attributed


def test_a_search_that_failed_is_not_a_search_that_found_nothing():
    def explode(request, timeout=None):
        raise OSError("connection reset")

    assert Openverse(opener=explode).search("bakery").status == COULD_NOT_LOOK_FOR_IMAGES


def test_their_own_photographs_come_first():
    """A page showing a business its own shopfront is doing what stock cannot."""

    stock = Image(url="https://example.org/a.jpg", provenance=LICENSED_STOCK, retrieved_at=AT)
    theirs = Image(url="https://theirs.example/b.jpg", provenance=SUBJECT_OWN, retrieved_at=AT)
    combined = gather(ImageSet(IMAGES_FOUND, (stock,)), ImageSet(IMAGES_FOUND, (theirs,)))
    assert combined.images[0].provenance == SUBJECT_OWN


def test_a_robots_file_that_cannot_be_read_is_not_permission():
    """The cheap, correct response to not knowing whether you may read a site is not to."""

    def explode(request, timeout=None):
        raise OSError("timeout")

    assert images_mod._may_fetch("https://someone.example/", opener=explode) is None


def test_a_site_that_disallows_this_reader_is_not_read(monkeypatch):
    monkeypatch.setattr(images_mod, "_may_fetch", lambda url, **kw: False)
    result = images_mod.from_subject("https://someone.example/")
    assert result.status == COULD_NOT_LOOK_FOR_IMAGES
    assert "robots.txt" in result.reason


def test_an_unlabelled_stock_photograph_fails_verification():
    """The page would be presenting somebody else's premises as this business's."""

    evidence = {
        "language": "en",
        "business": {"name": {"value": "Invented Bakery"}, "kind": {"value": "bakery"},
                     "fields": {}, "raw": {"tags": {}}},
        "images": [{"url": "https://example.org/photo.jpg", "local_path": "images/stock-1.jpg",
                    "provenance": LICENSED_STOCK, "label": "Stock photograph — not this "
                    "business's premises.", "attribution": "by Somebody, CC BY 4.0.",
                    "creator": "Somebody"}],
    }
    page = ('<html lang="en"><head><meta name=robots content="noindex, nofollow">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<p>Unofficial sample, not affiliated with them. Ian McGuane.</p>'
            '<h1>Invented Bakery</h1><img src="images/stock-1.jpg" alt="A bakery">'
            '<p>by Somebody, CC BY 4.0.</p></body></html>')
    verdict = verify(page, evidence, operator="Ian McGuane")
    assert verdict.status == UNSOURCED_CLAIMS
    assert any(p.code == "UNLABELLED_STOCK" for p in verdict.problems)


def test_a_labelled_and_attributed_stock_photograph_passes():
    evidence = {
        "language": "en",
        "business": {"name": {"value": "Invented Bakery"}, "kind": {"value": "bakery"},
                     "fields": {}, "raw": {"tags": {}}},
        "images": [{"url": "https://example.org/photo.jpg", "local_path": "images/stock-1.jpg",
                    "provenance": LICENSED_STOCK,
                    "label": "Stock photograph — not this business's premises.",
                    "attribution": "by Somebody, CC BY 4.0.", "creator": "Somebody"}],
    }
    page = ('<html lang="en"><head><meta name=robots content="noindex, nofollow">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<p>Unofficial sample, not affiliated with them. Ian McGuane.</p>'
            '<h1>Invented Bakery</h1><img src="images/stock-1.jpg" alt="A bakery">'
            '<figcaption>Stock photograph — not this business\'s premises</figcaption>'
            '<p>by Somebody, CC BY 4.0.</p></body></html>')
    assert verify(page, evidence, operator="Ian McGuane").status == VERIFIED


def test_a_photograph_nobody_recorded_fails_verification():
    """Including one a designer liked the look of and dropped in from somewhere else."""

    evidence = {"language": "en", "business": {"name": {"value": "Invented Bakery"}, "kind": {"value": "bakery"},
                             "fields": {}, "raw": {"tags": {}}}, "images": []}
    page = ('<html lang="en"><head><meta name=robots content="noindex">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<p>Unofficial sample, not affiliated. Ian McGuane.</p>'
            '<img src="https://somewhere-else.example/nice.jpg"></body></html>')
    verdict = verify(page, evidence, operator="Ian McGuane")
    assert any(p.code == "UNRECORDED_IMAGE" for p in verdict.problems)
