"""Read a company's numbers from what it filed, not from what a screener computed.

SEC EDGAR is to an equity what contract state is to a token: the thing itself, retrievable
by anyone, immutable once filed, and identified precisely enough that two people arguing
about a figure can settle it. Every value here carries the accession number, form type,
fiscal period and filing date that produced it.

Three defects shape this module, and each is the family this repository keeps meeting.

**A concept the filer never reports is not zero.** Ask EDGAR for a tag a company does not
use and you get a 404. Rendered as 0 it says "this company has no debt" when the truth is
"this company does not report that tag" -- possibly because it reports the same thing under
a different one. `NOT_REPORTED` never renders as a number.

**A restated figure and an original are two different facts.** The same fiscal period is
filed more than once: an original 10-K, then an amended one, then a comparative in a later
filing. EDGAR returns all of them. Picking the newest silently would quietly replace what
a company said with what it later said instead, and picking the first would ignore a
correction. Both are surfaced and the choice is the reviewer's.

**Periods are not comparable just because they are adjacent.** A 10-K covers a year and a
10-Q a quarter; `frame` data mixes them. Duration and form travel with every datapoint so
a caller cannot subtract a quarter from a year without noticing.

No API key. EDGAR requires only a declared User-Agent identifying the caller, and refusing
to send a real one is both against their terms and how a client gets blocked.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Sequence

from lib.http_retry import TransientRetrievalError, retrying_urlopen

REPORTED = "REPORTED"
NOT_REPORTED = "NOT_REPORTED"
INDETERMINATE = "INDETERMINATE"

BASE = "https://data.sec.gov"
TICKER_INDEX = "https://www.sec.gov/files/company_tickers.json"

# EDGAR asks every client to identify itself and to say who to contact. A generic or
# absent agent is both a terms violation and the fastest way to be blocked.
DEFAULT_AGENT = "evidence-board research ianmcguane681@gmail.com"

# Forms whose figures describe a period the filer has closed. An 8-K may carry numbers
# but is an announcement, and treating one as a reported period mixes guidance with
# accounts.
PERIODIC_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F"})


@dataclass(frozen=True, slots=True)
class Datapoint:
    """One reported value, and everything needed to find it again."""

    value: float
    unit: str
    period_end: str
    accession: str
    form: str
    filed: str
    fiscal_year: int | None = None
    fiscal_period: str = ""
    period_start: str = ""

    @property
    def is_amendment(self) -> bool:
        return self.form.endswith("/A")

    @property
    def duration(self) -> str:
        """Start and end together, because the end alone does not identify a figure.

        Apple's FY2017 revenue and its Q4-2017 revenue both end on 2017-09-30 and differ
        by a factor of four. Keyed on the end date alone they look like a restatement of
        each other, which is what the first version of this module reported.
        """

        return f"{self.period_start or '?'}..{self.period_end}"

    @property
    def covers_a_year(self) -> bool:
        """Whether the datapoint spans roughly a year rather than a quarter.

        Judged from the dates rather than the form, because a 10-K carries quarterly
        figures too and a caller comparing "annual revenue" needs the span, not the
        document it arrived in.
        """

        if not self.period_start or not self.period_end:
            return self.form.startswith(("10-K", "20-F", "40-F"))
        return (int(self.period_end[:4]) * 12 + int(self.period_end[5:7])) - (
            int(self.period_start[:4]) * 12 + int(self.period_start[5:7])
        ) >= 10

    def cite(self) -> str:
        return f"{self.form} {self.accession} period ending {self.period_end}"


@dataclass(frozen=True, slots=True)
class ConceptSeries:
    """Everything a filer has reported under one tag, with revisions kept visible."""

    status: str
    cik: str
    concept: str
    entity: str = ""
    datapoints: tuple[Datapoint, ...] = ()
    units_seen: tuple[str, ...] = ()
    reason: str = ""
    # Other candidate tags that also carried data. A filer switching tags splits its
    # history across two of them, and neither alone is the whole series.
    alternates_with_data: tuple[str, ...] = ()
    # Which namespace was actually asked. NOT_REPORTED means "not under this taxonomy",
    # and saying which one keeps a wrong-namespace query from reading as a fact about the
    # company. Cover-page facts live in `dei`; asking `us-gaap` for them finds nothing.
    taxonomy: str = "us-gaap"

    @property
    def durations(self) -> tuple[str, ...]:
        """Distinct start..end spans, which is what identifies a reported figure."""

        return tuple(sorted({d.duration for d in self.datapoints}))

    @property
    def periods(self) -> tuple[str, ...]:
        return tuple(sorted({d.period_end for d in self.datapoints}))

    def for_duration(self, duration: str) -> tuple[Datapoint, ...]:
        """Every filing of one span, newest filing last. Never one of them."""

        return tuple(
            sorted(
                (d for d in self.datapoints if d.duration == duration),
                key=lambda d: (d.filed, d.accession),
            )
        )

    def revised_durations(self) -> dict[str, tuple[Datapoint, ...]]:
        """Spans filed more than once at DIFFERENT values.

        Two guards, and the second was learned from live data. Repetition alone is not a
        revision: a comparative repeating last year unchanged is the company agreeing with
        itself, and flagging it would make every long series look restated.

        And the span must be the whole span. Grouping on the end date alone put Apple's
        FY2017 revenue beside its Q4-2017 revenue -- both ending 2017-09-30, differing
        fourfold -- and called it a restatement.
        """

        revised: dict[str, tuple[Datapoint, ...]] = {}
        for duration in self.durations:
            filings = self.for_duration(duration)
            if len({d.value for d in filings}) > 1:
                revised[duration] = filings
        return revised

    def latest_annual(self) -> Datapoint | None:
        annual = [d for d in self.datapoints if d.covers_a_year and d.form in PERIODIC_FORMS]
        return max(annual, key=lambda d: (d.period_end, d.filed)) if annual else None

    def describe(self) -> str:
        if self.status == NOT_REPORTED:
            # The pointer to `dei` is only useful when `dei` is not what was asked. Printing
            # it after a `dei` query tells a reader to go and do the thing just done, which
            # reads as a bug in the message and makes the real sentence harder to trust.
            hint = "" if "dei" in self.taxonomy.split(" / ") else (
                " The same quantity may be reported under a different tag or a different "
                "taxonomy — cover-page facts live in `dei`, not `us-gaap`."
            )
            return (
                f"{self.entity or self.cik} does not report {self.concept} under the "
                f"{self.taxonomy} taxonomy. This is a statement about the filer's tagging "
                f"AND about which namespace was asked, NOT a value of zero." + hint
            )
        if self.status == INDETERMINATE:
            return (
                f"{self.concept} for {self.cik} could not be retrieved: {self.reason}. "
                f"This says nothing about whether the company reports it."
            )
        lines = [
            f"{self.entity} {self.concept}: {len(self.datapoints)} datapoint(s) across "
            f"{len(self.durations)} reporting span(s), units {', '.join(self.units_seen)}."
        ]
        if len(self.units_seen) > 1:
            lines.append(
                f"  MIXED UNITS: {', '.join(self.units_seen)}. Values in different units "
                f"are not comparable and are not combined here."
            )
        revised = self.revised_durations()
        if revised:
            lines.append(f"  {len(revised)} reporting span(s) were filed at more than one value:")
            for duration, filings in list(revised.items())[:5]:
                shown = ", ".join(f"{d.value:,.0f} ({d.form}, filed {d.filed})" for d in filings)
                lines.append(f"    {duration}: {shown}")
            lines.append(
                "  A restated figure and the original are two different facts. Neither is "
                "selected here."
            )
        if self.alternates_with_data:
            lines.append(
                f"  TAG CHANGE: this filer also reported under "
                f"{', '.join(self.alternates_with_data)}. The history is split across "
                f"tags and this series alone is not the whole of it."
            )
        latest = self.latest_annual()
        if latest:
            lines.append(f"  latest annual: {latest.value:,.0f} {latest.unit} [{latest.cite()}]")
        return "\n".join(lines)


class EdgarClient:
    """A thin, honest reader for EDGAR's XBRL company APIs."""

    def __init__(self, user_agent: str = DEFAULT_AGENT, *, opener=retrying_urlopen) -> None:
        if not user_agent.strip() or "@" not in user_agent:
            raise ValueError(
                "EDGAR requires a User-Agent naming the caller and a contact address"
            )
        self.user_agent = user_agent
        self._opener = opener

    def _get(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with self._opener(request) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise FileNotFoundError(url) from error
            raise TransientRetrievalError(f"EDGAR {error.code} for {url}") from error
        except OSError as error:
            raise TransientRetrievalError(f"EDGAR unreachable: {error}") from error

    def cik_for_ticker(self, ticker: str) -> str:
        """Resolve a ticker to a zero-padded CIK.

        Tickers are reused after a delisting and several filers can share one across
        exchanges, so this returns the SEC's own mapping and nothing cleverer. An
        unresolvable ticker raises rather than guessing at the closest match.
        """

        index = self._get(TICKER_INDEX)
        wanted = ticker.strip().upper()
        for row in index.values():
            if str(row.get("ticker", "")).upper() == wanted:
                return str(row["cik_str"]).zfill(10)
        raise LookupError(f"No CIK for ticker {ticker!r} in the SEC index")

    def concept(self, cik: str, concept: str, *, taxonomy: str = "us-gaap") -> ConceptSeries:
        """One tag's full reported history, revisions and all.

        A tag may name its own taxonomy as `dei:EntityCommonStockSharesOutstanding`.
        Cover-page facts live in `dei`, not `us-gaap`, and asking the wrong namespace
        returns nothing — which then renders as "the filer does not report it". That is a
        statement about the query wearing the clothes of a statement about the company,
        and it is how Modine came to be described as not reporting a share count it
        reports in every filing.
        """

        namespace, _, tag = concept.rpartition(":")
        taxonomy, concept = (namespace or taxonomy), tag
        cik = cik.zfill(10) if cik.isdigit() else cik
        url = f"{BASE}/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json"
        try:
            payload = self._get(url)
        except FileNotFoundError:
            # The filer does not use this tag IN THIS TAXONOMY. Not zero, not absent from
            # the world, and not necessarily absent from the filing.
            return ConceptSeries(NOT_REPORTED, cik, concept, taxonomy=taxonomy)
        except TransientRetrievalError as error:
            return ConceptSeries(
                INDETERMINATE, cik, concept, reason=str(error)[:120], taxonomy=taxonomy
            )

        points: list[Datapoint] = []
        for unit, rows in (payload.get("units") or {}).items():
            for row in rows:
                if not row.get("end") or row.get("val") is None:
                    continue
                points.append(Datapoint(
                    value=float(row["val"]), unit=unit, period_end=str(row["end"]),
                    accession=str(row.get("accn", "")), form=str(row.get("form", "")),
                    filed=str(row.get("filed", "")),
                    fiscal_year=row.get("fy"), fiscal_period=str(row.get("fp") or ""),
                    period_start=str(row.get("start") or ""),
                ))
        if not points:
            return ConceptSeries(
                NOT_REPORTED, cik, concept,
                entity=str(payload.get("entityName") or ""), taxonomy=taxonomy,
            )
        return ConceptSeries(
            REPORTED, cik, concept,
            entity=str(payload.get("entityName") or ""),
            datapoints=tuple(points),
            units_seen=tuple(sorted({p.unit for p in points})),
            taxonomy=taxonomy,
        )

    def first_reported(
        self, cik: str, concepts: Sequence[str], *, taxonomy: str = "us-gaap"
    ) -> ConceptSeries:
        """The candidate tag the filer is CURRENTLY using, not the first that ever answered.

        Companies tag the same idea differently -- `Revenues` here,
        `RevenueFromContractWithCustomerExcludingAssessedTax` there -- and they change tag
        mid-life. NVIDIA used the second through FY2022 and the first from FY2023.

        The original version returned the first candidate with any data at all, which for
        NVIDIA meant a four-year-old revenue figure reported with complete confidence
        beside a current net income. Every candidate is now queried and the one with the
        most recent data wins, with the others recorded: a filer that switched tags has its
        history split across both, and neither alone is the whole series.

        An INDETERMINATE anywhere in the walk is still returned rather than swallowed. A
        rate limit partway through must not read as "the filer uses none of these".
        """

        blocked: ConceptSeries | None = None
        found: list[ConceptSeries] = []
        asked: list[ConceptSeries] = []
        for name in concepts:
            series = self.concept(cik, name, taxonomy=taxonomy)
            asked.append(series)
            if series.status == REPORTED:
                found.append(series)
            elif series.status == INDETERMINATE and blocked is None:
                blocked = series
        if blocked is not None and not found:
            return blocked
        if not found:
            # Built from the namespaces actually queried, not from this function's default.
            # Synthesising the refusal without a taxonomy meant it fell back to `us-gaap`,
            # so a `dei`-only candidate list produced "does not report
            # dei:EntityCommonStockSharesOutstanding under the us-gaap taxonomy — cover
            # page facts live in `dei`", which contradicts itself in one sentence and is
            # the exact defect the split into two candidate lists was made to fix.
            namespaces = sorted({series.taxonomy for series in asked})
            return ConceptSeries(
                NOT_REPORTED, cik,
                # The namespace is stated separately, so it is not repeated in the tag.
                " / ".join(name.rpartition(":")[2] for name in concepts),
                entity=next((s.entity for s in asked if s.entity), ""),
                taxonomy=" / ".join(namespaces) or taxonomy,
            )

        def recency(series: ConceptSeries) -> str:
            return max((d.period_end for d in series.datapoints), default="")

        found.sort(key=recency, reverse=True)
        current = found[0]
        others = tuple(s.concept for s in found[1:])
        return ConceptSeries(
            current.status, current.cik, current.concept, current.entity,
            current.datapoints, current.units_seen, current.reason,
            alternates_with_data=others, taxonomy=current.taxonomy,
        )
