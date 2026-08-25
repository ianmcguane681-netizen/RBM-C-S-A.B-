"""A page carrying a stranger's business name is either a labelled sample or a forgery.

The line between the two is thin, entirely a matter of what the page says about itself, and
easy to erase by accident — a tidier template, a client who asks for "the version without
the banner", a refactor that makes the operator name optional. These tests make erasing it
break the build.

The second property is quieter and matters as much: nothing appears on the page that did
not come from a `Fact`. A generated sentence about a business you have never spoken to is
indistinguishable from a retrieved one once it is on the page, and the first invented
detail a recipient reads ends the conversation.
"""
from __future__ import annotations

import pytest

from prospector.business import ABSENT, Business, Fact
from prospector.site import render

AT = "2026-08-25T00:00:00+00:00"
FACT = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731

BUSINESS = Business(
    "node/1", FACT("Bridge End Barbers"), FACT("hairdresser"), website=ABSENT,
    fields={"phone": FACT("+353 74 912 0001"), "street": FACT("Main Street"),
            "city": FACT("Invented Town")},
    raw={"lat": 54.65, "lon": -8.11})


def test_the_sample_page_always_says_it_is_unofficial_and_unaffiliated():
    page = render(BUSINESS, operator="Ian McGuane")
    assert "Unofficial sample" in page
    assert "not affiliated with" in page.lower()
    assert "Ian McGuane" in page


def test_a_sample_page_cannot_be_produced_without_naming_who_prepared_it():
    with pytest.raises(ValueError):
        render(BUSINESS, operator="   ")


def test_a_field_that_is_absent_leaves_a_labelled_gap_rather_than_inventing_one():
    """No opening hours were retrieved, so no opening hours appear. Not plausible ones."""

    page = render(BUSINESS, operator="Ian McGuane")
    assert "Opening hours" not in page
    assert "What is missing from this sample" in page


def test_a_field_that_is_present_appears_with_its_value():
    page = render(BUSINESS, operator="Ian McGuane")
    assert "+353 74 912 0001" in page
    assert "Main Street, Invented Town" in page


def test_the_page_carries_no_photograph_of_the_business():
    """Their photographs are theirs. The space is reserved and asked for instead."""

    page = render(BUSINESS, operator="Ian McGuane")
    assert "<img" not in page
    assert "belong to that business" in page


def test_the_page_is_built_for_a_phone():
    """The tool refuses sites with no viewport tag; producing one would be quite a look."""

    page = render(BUSINESS, operator="Ian McGuane")
    assert 'name="viewport"' in page


def test_a_business_name_with_markup_in_it_cannot_inject_into_the_page():
    hostile = Business("node/2", FACT('Bob<script>alert(1)</script>'), FACT("shop"),
                       fields={"city": FACT("Town")})
    page = render(hostile, operator="Ian McGuane")
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_the_page_asks_search_engines_not_to_index_it():
    """It is a sample about somebody else's business. It should not compete with them."""

    assert 'name="robots" content="noindex, nofollow"' in render(BUSINESS, operator="Ian")
