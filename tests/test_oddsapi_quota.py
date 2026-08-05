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

from connectors.oddsapi import (
    UK_IE_EU,
    OddsApiCredentials,
    OddsApiSource,
    QuotaFloorReached,
    Usage,
    credits_per_day,
    describe_burn,
)


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


class TestTheFloorStopsAScanRatherThanAKeyRunningOut:
    """An exhausted key reports no arb, and that sentence costs more than the scan did.

    Two scheduler lanes were asking every thirty minutes at two and four credits a run —
    288 a day against a free tier of 500 A MONTH. The allowance goes in under two days,
    and what happens on day three is not an error anybody sees: the request fails, the
    lane reports COULD_NOT_LOOK if it is lucky and an empty scan if it is not, and a
    spent account looks exactly like a quiet market for the rest of the month.

    The floor is not nought because the last credits are worth more than the earlier ones.
    They are what lets a person run one scan by hand, on a fixture they care about, after
    the cadence has been stopped.
    """

    def _source(self, tmp_path, remaining: int | None, **kw):
        usage = tmp_path / "usage.json"
        if remaining is not None:
            usage.write_text(json.dumps({"remaining": remaining, "used": 500 - remaining,
                                         "last": 2, "recorded_at": "2026-08-04T00:00:00Z"}))
        _seen, opener = _recorder({"x-requests-remaining": "400", "x-requests-used": "100"})
        return OddsApiSource(OddsApiCredentials("test-key"), usage_path=usage,
                             opener=opener, **kw), usage

    def test_a_scan_below_the_floor_refuses_before_spending_anything(self, tmp_path):
        source, _ = self._source(tmp_path, remaining=10)

        with pytest.raises(QuotaFloorReached, match="10 request"):
            source.quotes("soccer_epl")

    def test_the_refusal_names_what_a_person_can_go_and_do(self, tmp_path):
        source, usage = self._source(tmp_path, remaining=10)

        with pytest.raises(QuotaFloorReached) as stopped:
            source.quotes("soccer_epl")

        message = str(stopped.value)
        assert "NOTHING WAS SCANNED" in message
        assert "not a report that no arb exists" in message
        assert "cadence" in message and str(usage) in message

    def test_refusing_is_an_exception_so_it_becomes_could_not_look(self, tmp_path):
        """Every caller turns a raise from `look()` into COULD_NOT_LOOK and an empty list
        into "scanned, found nothing". Returning `()` here would report a lane that
        declined to spend as a lane that looked at a quiet market."""

        source, _ = self._source(tmp_path, remaining=0)

        with pytest.raises(RuntimeError):
            source.quotes("soccer_epl")

    def test_above_the_floor_the_scan_proceeds(self, tmp_path):
        source, _ = self._source(tmp_path, remaining=400)

        assert source.quotes("soccer_epl") == ()      # the stub returns no events
        assert source.usage.remaining == 400          # and the response updated the count

    def test_a_quota_never_measured_does_not_block(self, tmp_path):
        """Never having looked is not the same as having looked and found it spent.

        Refusing to spend a credit we have no evidence is gone would make a missing file
        indistinguishable from an empty account, and the first run of a fresh key has no
        file. One request teaches us and the floor applies from there.
        """

        source, _ = self._source(tmp_path, remaining=None)

        assert source.usage.to_dict()["status"] == "UNKNOWN"
        source.quotes("soccer_epl")                   # does not raise
        assert source.usage.remaining == 400

    def test_the_reading_survives_the_process_that_took_it(self, tmp_path):
        """A per-process count guards one run, and the lane runs on a cadence.

        Each `run.py --reap arb` is a fresh process, so without persistence the floor
        protects a single invocation and nothing else — which is the exact shape that
        empties a monthly allowance.
        """

        source, usage = self._source(tmp_path, remaining=None)
        source.quotes("soccer_epl")

        _seen, opener = _recorder()
        reopened = OddsApiSource(OddsApiCredentials("k"), usage_path=usage, opener=opener)

        assert reopened.usage.remaining == 400

    def test_an_unwritable_usage_file_does_not_take_the_scan_down_with_it(self, tmp_path):
        """The guard's own bookkeeping failing must not become an outage.

        A guard that stops the thing it was guarding, because it could not write its
        notes, has done more damage than the risk it was covering.
        """

        _seen, opener = _recorder({"x-requests-remaining": "400", "x-requests-used": "100"})
        source = OddsApiSource(OddsApiCredentials("k"), opener=opener,
                               usage_path=tmp_path / "nope" / "deep" / "usage.json")
        (tmp_path / "nope").write_text("not a directory", encoding="utf-8")

        assert source.quotes("soccer_epl") == ()


class TestTheCostIsStatedBeforeAKeyIsPlaced:
    """The only moment a burn rate can change a decision is before the key exists.

    The alternative is finding out from a lane that stopped finding anything three weeks
    in — and an exhausted key is indistinguishable from a quiet market, so the discovery
    arrives late and disguised as an answer about the world.
    """

    def test_a_second_sport_doubles_the_bill(self):
        one = credits_per_day(sports=1, cadence_seconds=8 * 3600)
        two = credits_per_day(sports=2, cadence_seconds=8 * 3600)

        assert two == 2 * one

    def test_naming_books_halves_it_against_two_regions(self):
        """Up to ten named books cost what one region costs, and uk,eu is two."""

        wide = credits_per_day(sports=1, cadence_seconds=8 * 3600, regions=UK_IE_EU)
        narrow = credits_per_day(sports=1, cadence_seconds=8 * 3600,
                                 bookmakers=("skybet", "paddypower"))

        assert narrow == wide / 2

    def test_the_settings_that_emptied_the_tier_are_reported_as_overspending(self):
        """Two lanes at thirty minutes, which is what this guard was written for."""

        daily = (credits_per_day(sports=2, cadence_seconds=1800)
                 + credits_per_day(sports=1, cadence_seconds=1800))

        assert daily == 288
        assert "OVERSPENDS" in describe_burn(daily)
        assert "1.7 day" in describe_burn(daily)

    def test_the_shipped_cadence_is_reported_as_fitting(self):
        daily = credits_per_day(sports=2, cadence_seconds=8 * 3600) + 2

        assert "fits" in describe_burn(daily)

    def test_a_cadence_of_nothing_is_refused_rather_than_dividing_by_zero(self):
        with pytest.raises(ValueError, match="immediately"):
            credits_per_day(sports=1, cadence_seconds=0)
