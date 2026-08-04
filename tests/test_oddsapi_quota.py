"""Running out of quota reads as no arbs, and narrowing the scan reads as no arbs too.

`Usage` exists because a scan that stopped because the free tier was spent must not be
reported as a scan that found nothing. That care was being undone one layer up: the
sentinel `-1` went straight into `scan_arb.py --json` as `quota_remaining`, where a reader
renders minus one request remaining, or worse, treats any number it gets as a measurement.

The bookmaker filter is the same hazard approached from the other side. Asking for five
named books instead of a whole region halves what every scan costs, which matters on 500
credits against a thirty-minute cadence — but a book that is misspelled, retired, or not
carried in this region comes back as a 200 with that book absent and no error anywhere.
The lane then reports a quiet market from a narrower look than anybody chose. So the
filter is opt-in, an oversized list is refused rather than silently repriced, and the
books asked for are published beside the books seen.
"""
from __future__ import annotations

import json
import urllib.parse

import pytest

from connectors.oddsapi import UK_IE_EU, OddsApiCredentials, OddsApiSource, Usage


class _Response:
    """The feed's own answer shape, with the usage headers a live call carries."""

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return json.dumps([]).encode("utf-8")


def _recorder(headers: dict[str, str] | None = None):
    seen: list[str] = []

    def opener(request):
        seen.append(request.full_url)
        return _Response(headers)

    return seen, opener


def _query(url: str) -> dict[str, list[str]]:
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)


def test_an_unmeasured_quota_is_unknown_rather_than_minus_one():
    """The sentinel is for comparisons, not for publication.

    `-1` is a perfectly good "no header arrived" inside this module and an actively
    misleading figure the moment it crosses into JSON, where nothing distinguishes it
    from a reading.
    """

    assert Usage().to_dict() == {
        "status": "UNKNOWN",
        "remaining": None,
        "used": None,
        "last_request_cost": None,
    }


def test_a_measured_quota_publishes_what_the_last_call_cost():
    """Cost is per region and per market, so a widened scan spends faster than it looks."""

    seen, opener = _recorder({
        "x-requests-remaining": "480",
        "x-requests-used": "20",
        "x-requests-last": "2",
    })
    source = OddsApiSource(OddsApiCredentials("test-key"), opener=opener)
    source.quotes("soccer_epl")

    assert source.usage.to_dict() == {
        "status": "KNOWN", "remaining": 480, "used": 20, "last_request_cost": 2,
    }


def test_a_response_with_no_usage_headers_leaves_the_quota_unknown():
    """Reached, and did not say. Not the same as reached and reported a full tier."""

    _seen, opener = _recorder()
    source = OddsApiSource(OddsApiCredentials("test-key"), opener=opener)
    source.quotes("soccer_epl")

    assert source.usage.to_dict()["status"] == "UNKNOWN"


def test_by_default_the_whole_region_is_asked_for_and_nothing_is_narrowed():
    """The filter costs less and can hide books, so no caller gets it without asking.

    A default book list would apply that risk to every existing caller, and the failure
    it produces — fewer books, no error, no arb — is indistinguishable from a quiet
    afternoon.
    """

    seen, opener = _recorder()
    source = OddsApiSource(OddsApiCredentials("test-key"), opener=opener)
    source.quotes("soccer_epl")

    assert _query(seen[0])["regions"] == [UK_IE_EU]
    assert "bookmakers" not in _query(seen[0])
    assert source.bookmakers == ()


def test_named_books_are_asked_for_in_the_request_that_is_already_paid_for():
    """Filtering afterwards costs the same as not filtering; the quota goes on the call."""

    seen, opener = _recorder()
    source = OddsApiSource(
        OddsApiCredentials("test-key"), bookmakers=("skybet", "paddypower"), opener=opener
    )
    source.quotes("soccer_epl")

    assert _query(seen[0])["bookmakers"] == ["skybet,paddypower"]
    assert "regions" not in _query(seen[0])


def test_an_eleventh_bookmaker_is_refused_rather_than_quietly_doubling_the_cost():
    """The API prices each ten named books as one region, and the step is invisible.

    Crossing it does not fail, it charges double for every scan from then on, on a lane
    running every thirty minutes against a free tier of 500.
    """

    with pytest.raises(ValueError, match="silently doubles"):
        OddsApiSource(OddsApiCredentials("test-key"),
                      bookmakers=tuple(f"book{n}" for n in range(11)))


def test_scan_arb_asks_the_feed_for_the_books_it_was_given(monkeypatch):
    """`--books` is how a list is TRIED before it goes into `data/reapers.json`.

    A provider key that is misspelled or not carried in this region narrows the arb lane
    permanently and silently, so the one place to find that out is a scan whose requested
    books can be compared against the books that answered.
    """

    import scan_arb

    asked: dict = {}

    def fake_from_directory(*_args, **kw):
        asked.update(kw)
        return OddsApiSource(None, **kw)

    monkeypatch.setattr(scan_arb.OddsApiSource, "from_directory", fake_from_directory)

    # No credentials, so this returns 2 before scanning. The construction is the assertion.
    assert scan_arb.main("soccer_epl", as_json=False, books=("skybet",)) == 2
    assert asked["bookmakers"] == ("skybet",)


def test_repeated_and_blank_book_names_do_not_consume_the_ten_that_are_paid_for():
    source = OddsApiSource(
        OddsApiCredentials("test-key"),
        bookmakers=("skybet", " skybet ", "", "  ", "paddypower"),
    )

    assert source.bookmakers == ("skybet", "paddypower")
