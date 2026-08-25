"""A look that failed must never come back as a look that found nothing.

At three levels, because the defect appears at all three and the consequence differs each
time. An unresolvable area name returning an empty county wastes a run. A source outage
returning an empty list makes a county look served when it was never read. And a single
failed fetch reported as a dead website puts a false sentence in an email to a business —
the most expensive of the three, because it is the one a stranger reads.
"""
from __future__ import annotations

from prospector import condition
from prospector.sources import overpass
from prospector.states import (AREA_UNKNOWN, DEFICIENT, LOOKED, SOURCE_UNREADABLE,
                               UNDETERMINED)


class _Transport:
    endpoint = "test://overpass"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def query(self, ql):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_an_unknown_area_is_not_an_empty_area():
    discovery = overpass.discover("Nowhere At All", transport=_Transport({"elements": []}))
    assert discovery.status == AREA_UNKNOWN
    assert discovery.businesses == ()
    assert "nothing was searched" in discovery.describe()


def test_a_source_that_could_not_be_read_is_never_an_empty_list():
    discovery = overpass.discover("County Donegal", transport=_Transport(OSError("reset")))
    assert discovery.status == SOURCE_UNREADABLE
    assert "not the same as the area having no businesses" in discovery.describe()


def test_a_failure_selecting_businesses_does_not_report_a_quiet_county():
    """The area resolved, so the run got further — and it still knows nothing."""

    transport = _Transport({"elements": [{"id": 282898}]}, TimeoutError("slow"))
    discovery = overpass.discover("County Donegal", transport=transport)
    assert discovery.status == SOURCE_UNREADABLE
    assert transport.calls == 2


def test_an_area_that_resolves_and_holds_nothing_is_a_real_empty_answer():
    """The one case where an empty list is the truth, kept separate from the two above."""

    transport = _Transport({"elements": [{"id": 1}]}, {"elements": []})
    discovery = overpass.discover("Some Townland", transport=transport)
    assert discovery.status == LOOKED
    assert discovery.businesses == ()


def test_one_failed_fetch_is_not_a_dead_website():
    """Two attempts, because 'your website is offline' is the worst sentence to get wrong.

    The first attempt failing and the second succeeding is a transient network fault, which
    says nothing about the business and must not reach a page of findings.
    """

    attempts = []

    def fetcher(url, timeout=condition.TIMEOUT):
        attempts.append(url)
        if len(attempts) == 1:
            return condition.Fetch(False, error="TimeoutError()")
        return condition.Fetch(True, "<html><head><meta name='viewport' content='x'>"
                                     "<title>Open</title></head><body>" + "x" * 400 +
                                     "</body></html>", 200, url, scheme="https")

    assessed = condition.assess("https://example.ie", fetcher=fetcher, retry_pause=0)
    assert assessed.status != UNDETERMINED
    assert not any(f.code in ("UNREACHABLE", "DOMAIN_DOES_NOT_RESOLVE")
                   for f in assessed.findings)


def test_two_failed_fetches_are_a_finding_and_name_which_kind():
    def dead(url, timeout=condition.TIMEOUT):
        return condition.Fetch(False, error="URLError(gaierror(-2, 'Name or service not known'))")

    assessed = condition.assess("http://gone.example", fetcher=dead, retry_pause=0)
    assert assessed.status == DEFICIENT
    assert assessed.defects[0].code == "DOMAIN_DOES_NOT_RESOLVE"


def test_a_site_that_blocks_robots_is_undetermined_rather_than_deficient():
    """A 403 to this user agent grades the checker, not the website."""

    def blocked(url, timeout=condition.TIMEOUT):
        return condition.Fetch(True, "", 403, url, scheme="https")

    assessed = condition.assess("https://guarded.example", fetcher=blocked, retry_pause=0)
    assert assessed.status == UNDETERMINED
    assert "a person opening it in a browser" in assessed.describe()
