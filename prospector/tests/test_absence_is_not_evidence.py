"""The strongest claim this package makes is the one it is most tempted to overstate.

Every test here defends one sentence: **"this business has no website" is a claim about a
business, and nothing in a directory can establish it.** A missing tag in OpenStreetMap is
a gap in a volunteer dataset, and rural coverage is patchy enough that the gap is the
common case. If that distinction is ever collapsed — by a default, by a falsy check, by
someone tidying three states into two — the tool starts telling businesses something untrue
about themselves in writing, over the operator's name.
"""
from __future__ import annotations

from prospector import presence
from prospector.business import ABSENT, Business, Fact
from prospector.states import COULD_NOT_LOOK, NO_SITE_FOUND, NO_SITE_LISTED, SITE_LISTED

AT = "2026-08-25T00:00:00+00:00"


def _business(**tags) -> Business:
    fact = lambda v: Fact(v, "openstreetmap:node/1", AT)  # noqa: E731
    website = tags.pop("website", ABSENT)
    return Business(
        identity="node/1", name=fact("Test Shop"), kind=fact("hairdresser"),
        website=fact(website) if website is not ABSENT else ABSENT,
        fields={k: fact(v) for k, v in tags.items()})


class _FoundNothing:
    def find(self, name, locality):
        return presence.SearchResult(NO_SITE_FOUND)


def test_a_missing_website_tag_is_not_a_business_without_a_website():
    assessed = presence.assess(_business(phone="+353 1 000 0000"))
    assert assessed.status == NO_SITE_LISTED
    assert not assessed.may_claim_no_website


def test_only_a_search_that_looked_may_claim_the_absence():
    assessed = presence.assess(_business(phone="+353 1 000 0000"), searcher=_FoundNothing())
    assert assessed.status == NO_SITE_FOUND
    assert assessed.may_claim_no_website


def test_the_default_searcher_says_it_could_not_look_rather_than_finding_nothing():
    """The default must never be the flattering answer.

    Out of the box there is no search backend. The honest report of that is "I did not
    look", and the tempting one — an empty result read as an absence — is the exact defect
    this package exists to refuse.
    """

    result = presence.NoSearcher().find("Test Shop", "Somewhere")
    assert result.status == COULD_NOT_LOOK
    assert result.status != NO_SITE_FOUND


def test_a_facebook_page_is_recorded_as_a_social_page_rather_than_a_website():
    """Otherwise the best prospects in the county are filtered out as already served."""

    assessed = presence.assess(_business(website="https://facebook.com/testshop"))
    assert assessed.status == SITE_LISTED
    assert assessed.is_social_only


def test_a_real_site_is_not_mistaken_for_a_social_page():
    assessed = presence.assess(_business(website="https://testshop.ie"))
    assert assessed.status == SITE_LISTED
    assert not assessed.is_social_only
