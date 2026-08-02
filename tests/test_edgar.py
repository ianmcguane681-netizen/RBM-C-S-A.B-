"""A tag the filer does not use is not a zero, and a restatement is not a correction to apply.

Equities meet the same defect family as everything else here, wearing accounting clothes.
Ask EDGAR for a concept a company never tags and it 404s; rendered as 0 that reads as "no
debt", "no impairment", "no related-party transactions" -- always the flattering direction,
and always about the number someone is deciding on.

The second defect is particular to filings. The same fiscal period is filed repeatedly: an
original, an amendment, a comparative in next year's report. Silently taking the newest
replaces what a company said with what it later said instead; silently taking the first
ignores a correction. Both are facts and the reviewer picks.
"""
from __future__ import annotations

import json
import urllib.error
from io import BytesIO

import pytest

from connectors.edgar import (
    INDETERMINATE,
    NOT_REPORTED,
    REPORTED,
    ConceptSeries,
    Datapoint,
    EdgarClient,
)
from lib.http_retry import TransientRetrievalError


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def responder(payload=None, *, status=None):
    def _open(request, **_kw):
        if status is not None:
            raise urllib.error.HTTPError(request.full_url, status, "err", {}, None)
        return FakeResponse(json.dumps(payload).encode())

    return _open


def facts(rows, entity="Test Co", unit="USD"):
    return {"entityName": entity, "tag": "Concept", "units": {unit: rows}}


def row(val, end, accn, form="10-K", filed="2026-01-01", start=""):
    return {"val": val, "end": end, "accn": accn, "form": form, "filed": filed, "start": start}


def point(value, end, accn, form="10-K", filed="2026-01-01", start=""):
    return Datapoint(value, "USD", end, accn, form, filed, period_start=start)


class TestAnUnusedTagIsNotZero:
    def test_a_404_is_not_reported_rather_than_a_value(self):
        client = EdgarClient("test test@example.com", opener=responder(status=404))

        series = client.concept("0000320193", "SomeTagNobodyUses")

        assert series.status == NOT_REPORTED
        assert not series.datapoints

    def test_the_wording_refuses_to_claim_a_zero(self):
        client = EdgarClient("test test@example.com", opener=responder(status=404))

        described = client.concept("0000320193", "Goodwill").describe()

        assert "NOT a value of zero" in described
        assert "may be reported under a different tag" in described

    def test_an_empty_units_block_is_also_not_reported(self):
        """EDGAR occasionally answers 200 with nothing in it. Same meaning, same handling."""

        client = EdgarClient("test test@example.com", opener=responder(facts([])))

        assert client.concept("0000320193", "Goodwill").status == NOT_REPORTED


class TestAFailedFetchIsNotAnAbsence:
    def test_a_rate_limit_is_indeterminate_not_missing(self):
        client = EdgarClient("test test@example.com", opener=responder(status=503))

        series = client.concept("0000320193", "Revenues")

        assert series.status == INDETERMINATE

    def test_indeterminate_says_it_establishes_nothing(self):
        client = EdgarClient("test test@example.com", opener=responder(status=503))

        assert "says nothing about whether the company reports it" in (
            client.concept("0000320193", "Revenues").describe()
        )

    def test_a_blocked_probe_does_not_render_as_the_filer_using_no_tag(self):
        """first_reported walks several tags. A rate limit partway through must not come
        back as 'the company uses none of them'."""

        client = EdgarClient("test test@example.com", opener=responder(status=429))

        series = client.first_reported("0000320193", ["Revenues", "SalesRevenueNet"])

        assert series.status == INDETERMINATE


class TestRestatementsStayVisible:
    def test_a_period_filed_twice_at_different_values_is_flagged(self):
        series = ConceptSeries(
            REPORTED, "0000320193", "Revenues", "Test Co",
            datapoints=(
                point(100, "2025-12-31", "0001-25-001", filed="2026-01-01", start="2025-01-01"),
                point(90, "2025-12-31", "0001-26-002", form="10-K/A", filed="2026-06-01", start="2025-01-01"),
            ),
            units_seen=("USD",),
        )

        assert "2025-01-01..2025-12-31" in series.revised_durations()

    def test_a_repeated_but_unchanged_figure_is_not_a_restatement(self):
        """A comparative repeating last year's number unchanged is the company agreeing
        with itself. Flagging it would make every long series look revised."""

        series = ConceptSeries(
            REPORTED, "0000320193", "Revenues", "Test Co",
            datapoints=(
                point(100, "2025-12-31", "0001-25-001", filed="2026-01-01", start="2025-01-01"),
                point(100, "2025-12-31", "0001-26-002", filed="2027-01-01", start="2025-01-01"),
            ),
            units_seen=("USD",),
        )

        assert series.revised_durations() == {}

    def test_neither_filing_is_silently_chosen(self):
        series = ConceptSeries(
            REPORTED, "0000320193", "Revenues", "Test Co",
            datapoints=(
                point(100, "2025-12-31", "0001-25-001", filed="2026-01-01", start="2025-01-01"),
                point(90, "2025-12-31", "0001-26-002", form="10-K/A", filed="2026-06-01", start="2025-01-01"),
            ),
            units_seen=("USD",),
        )

        assert len(series.for_duration("2025-01-01..2025-12-31")) == 2
        assert "Neither is selected here" in series.describe()

    def test_every_value_carries_the_filing_that_produced_it(self):
        cited = point(100, "2025-12-31", "0000320193-26-000020").cite()

        assert "0000320193-26-000020" in cited
        assert "10-K" in cited


class TestPeriodsAreNotInterchangeable:
    def test_a_quarter_is_not_read_as_a_year(self):
        quarter = point(10, "2026-03-31", "a", form="10-Q", start="2026-01-01")

        assert quarter.covers_a_year is False

    def test_a_year_is_recognised_from_its_dates(self):
        year = point(40, "2025-12-31", "a", form="10-K", start="2025-01-01")

        assert year.covers_a_year is True

    def test_latest_annual_ignores_quarters(self):
        series = ConceptSeries(
            REPORTED, "c", "Revenues", "Test Co",
            datapoints=(
                point(40, "2025-12-31", "a", form="10-K", start="2025-01-01"),
                point(12, "2026-03-31", "b", form="10-Q", start="2026-01-01"),
            ),
            units_seen=("USD",),
        )

        assert series.latest_annual().value == 40

    def test_mixed_units_are_named_and_never_combined(self):
        series = ConceptSeries(
            REPORTED, "c", "Thing", "Test Co",
            datapoints=(point(1, "2025-12-31", "a"),),
            units_seen=("USD", "shares"),
        )

        assert "MIXED UNITS" in series.describe()
        assert "not comparable" in series.describe()


class TestTheClientIdentifiesItself:
    @pytest.mark.parametrize("agent", ["", "   ", "python-urllib", "researcher"])
    def test_an_agent_without_a_contact_is_refused(self, agent):
        """EDGAR requires a real contact. Sending a generic agent is a terms violation and
        the fastest route to being blocked for everyone using this tool."""

        with pytest.raises(ValueError):
            EdgarClient(agent)

    def test_a_contactable_agent_is_accepted(self):
        assert EdgarClient("evidence-board someone@example.com").user_agent
