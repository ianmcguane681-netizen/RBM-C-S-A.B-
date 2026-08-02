"""Federal court records via CourtListener, as an independent source family.

CFPB complaints are consumer allegations made to a regulator. Federal docket
records are claims filed in court, by different parties, in a different forum,
with legal consequences attached. That makes them a genuinely separate source
family rather than another CFPB distribution method.

What this source can and cannot do is narrow and deliberate. A filed complaint is
an allegation, not a finding of fact. A settlement is not an admission. This
connector therefore supports repetition and independence of the *alleged*
operational mechanism; it never establishes that any alleged failure occurred.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from connectors.base import RetrievalResult
from core.ids import stable_id, utc_now
from core.models import AccessDiagnostic, Source, SourceReliabilityAssessment

COURTLISTENER_SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/search/"
SOURCE_FAMILY = "Federal court records"
RELIABILITY_VERSION = "COURTLISTENER-SRA-001"
ACCESS_TIMEOUT_SECONDS = 45
USER_AGENT = "GS-CF001/0.1 methodology proof"

# 15 U.S.C. 1681 is the Fair Credit Reporting Act. CourtListener exposes the
# statutory cause as structured metadata, so admission is a deterministic check
# against the statute rather than a keyword guess about the case name.
FCRA_STATUTE = "1681"
DEFAULT_QUERY = '"Fair Credit Reporting Act" reinvestigation'


def courtlistener_source() -> Source:
    return Source(
        source_id="COURTLISTENER-FCRA-001",
        name="CourtListener Federal Court Records (RECAP)",
        source_type="federal_judicial_records",
        base_url=COURTLISTENER_SEARCH_URL,
        jurisdiction="United States",
        role="discovery",
        source_family=SOURCE_FAMILY,
        notes=(
            "Independent of CFPB complaints. Filed claims are allegations, not "
            "findings of fact, and must be verified before supporting findings."
        ),
    )


def courtlistener_reliability_assessment(
    access_method: str, retrieved_at: str
) -> SourceReliabilityAssessment:
    return SourceReliabilityAssessment(
        source_id="COURTLISTENER-FCRA-001",
        source_name="CourtListener Federal Court Records (RECAP)",
        publisher="Free Law Project",
        publisher_type="Non-profit publisher of United States court records",
        authority_level="Primary court records republished by a non-profit",
        jurisdiction="United States",
        source_family=SOURCE_FAMILY,
        retrieval_method=access_method,
        retrieval_timestamp=retrieved_at,
        update_frequency="Continuously updated from PACER via RECAP contributions.",
        coverage_period="Depends on the retrieved docket set.",
        record_granularity="Individual federal court docket.",
        known_limitations=[
            "A filed complaint states allegations, not established facts.",
            "A settlement or dismissal is not an admission of liability.",
            "RECAP coverage depends on documents contributed by users and is incomplete.",
            "Docket metadata may be amended, sealed, or corrected after retrieval.",
            "Litigation volume reflects propensity to sue, not only underlying failure rates.",
            "Represented plaintiffs are not a representative sample of affected consumers.",
            "Case captions may not identify the operationally responsible party.",
        ],
        verification_constraints=[
            "Repeated statutory causes can support a repeated alleged mechanism.",
            "Court records alone do not establish that an alleged failure occurred.",
            "A judgment or documented finding is required before asserting proven failure.",
        ],
        independence_constraints=[
            "Independent of CFPB complaints: different parties, different forum.",
            "Multiple dockets from one plaintiff firm are weak independent evidence.",
            "Consolidated or related cases must not be counted as separate events.",
        ],
        representativeness_warning=(
            "Federal dockets are not a statistically representative sample of the market."
        ),
        data_completeness_warning=(
            "RECAP is a partial mirror of PACER; absence of a case proves nothing."
        ),
        permitted_uses=[
            "Corroborate that an alleged mechanism recurs outside the CFPB.",
            "Establish a second independent source family.",
            "Identify companies repeatedly named in the same statutory cause.",
        ],
        prohibited_inferences=[
            "Do not infer that alleged failures definitely occurred.",
            "Do not treat a settlement as proof of wrongdoing.",
            "Do not infer market prevalence from case volume alone.",
        ],
        reliability_version=RELIABILITY_VERSION,
        last_reviewed_date="2026-07-25",
    )


def _diagnostic(
    endpoint: str,
    access_method: str,
    request_headers: dict[str, str],
    response_status: str,
    response_headers: dict[str, str],
    response_body_summary: str,
    final_interpretation: str,
) -> AccessDiagnostic:
    attempted_at = utc_now()
    payload = {
        "endpoint": endpoint,
        "access_method": access_method,
        "status": response_status,
        "at": attempted_at,
    }
    return AccessDiagnostic(
        diagnostic_id=stable_id("ADIAG", payload),
        endpoint=endpoint,
        attempted_at=attempted_at,
        environment="local-urllib-transport",
        request_method="GET",
        request_headers={
            key: value
            for key, value in request_headers.items()
            if key.lower() not in {"authorization", "cookie"}
        },
        response_status=response_status,
        response_headers=response_headers,
        response_body_summary=response_body_summary[:1000],
        retry_result="not retried",
        final_interpretation=final_interpretation,
        access_method=access_method,
    )


def cites_fcra(cause: str, suit_nature: str = "") -> bool:
    """Admit a docket only when its statutory cause is the FCRA."""

    return FCRA_STATUTE in str(cause or "") or FCRA_STATUTE in str(suit_nature or "")


class CourtListenerSearchAdapter:
    method_name = "courtlistener_search_api"

    def __init__(
        self,
        fetch_json: Callable[[str], tuple[dict[str, Any], dict[str, str], str]] | None = None,
        *,
        query: str = DEFAULT_QUERY,
    ) -> None:
        self._fetch_json = fetch_json or self._default_fetch_json
        self.query = query

    def build_url(self, limit: int = 1) -> str:
        params = {
            "q": self.query,
            "type": "r",
            "order_by": "dateFiled desc",
        }
        return f"{COURTLISTENER_SEARCH_URL}?{urllib.parse.urlencode(params)}"

    def retrieve(
        self, limit: int
    ) -> tuple[str, list[dict[str, Any]], list[str], list[AccessDiagnostic]]:
        url = self.build_url(limit)
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            payload, response_headers, status = self._fetch_json(url)
            records = self._extract_records(payload, url, limit)
            diagnostic = _diagnostic(
                url,
                self.method_name,
                headers,
                status,
                response_headers,
                f"Retrieved {len(records)} FCRA docket record(s).",
                "CourtListener search API returned parseable JSON.",
            )
            return url, records, [], [diagnostic]
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            response_headers = dict(exc.headers.items()) if exc.headers else {}
            diagnostic = _diagnostic(
                url,
                self.method_name,
                headers,
                str(exc.code),
                response_headers,
                body,
                "CourtListener search API request failed from this environment.",
            )
            return url, [], [f"CourtListener access failed: HTTP {exc.code}"], [diagnostic]
        except Exception as exc:
            diagnostic = _diagnostic(
                url,
                self.method_name,
                headers,
                "error",
                {},
                str(exc),
                "CourtListener request failed before a response was parsed.",
            )
            return url, [], [f"CourtListener access failed: {exc}"], [diagnostic]

    def _default_fetch_json(self, url: str) -> tuple[dict[str, Any], dict[str, str], str]:
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=ACCESS_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return json.loads(body), dict(response.headers.items()), str(response.status)

    def _extract_records(
        self, payload: dict[str, Any], retrieval_url: str, limit: int
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in payload.get("results") or []:
            # Deterministic admission: the statutory cause must be the FCRA.
            if not cites_fcra(row.get("cause"), row.get("suitNature")):
                continue
            records.append(_normalise_docket_row(row, self.method_name, retrieval_url))
            if len(records) >= limit:
                break
        return records


def _party_names(row: dict[str, Any]) -> list[str]:
    party = row.get("party")
    if isinstance(party, list):
        return [str(item) for item in party if str(item).strip()]
    if isinstance(party, str) and party.strip():
        return [party.strip()]
    return []


def _normalise_docket_row(
    row: dict[str, Any], access_method: str, retrieval_url: str
) -> dict[str, Any]:
    docket_id = str(row.get("docket_id") or "")
    absolute_url = str(row.get("docket_absolute_url") or "")
    return {
        "docket_id": docket_id,
        "case_name": row.get("caseName") or "",
        "case_name_full": row.get("case_name_full") or "",
        "court": row.get("court") or "",
        "court_id": row.get("court_id") or "",
        "docket_number": row.get("docketNumber") or "",
        "date_filed": row.get("dateFiled") or "",
        "date_terminated": row.get("dateTerminated") or "",
        "cause": row.get("cause") or "",
        "suit_nature": row.get("suitNature") or "",
        "jurisdiction_type": row.get("jurisdictionType") or "",
        "assigned_to": row.get("assignedTo") or "",
        "parties": _party_names(row),
        "_source_record_id": docket_id,
        "_retrieval_url": (
            f"https://www.courtlistener.com{absolute_url}" if absolute_url else retrieval_url
        ),
        "_source_name": courtlistener_source().name,
        "_access_method": access_method,
    }


class CourtListenerConnector:
    source = courtlistener_source()

    def __init__(
        self,
        access_adapter: CourtListenerSearchAdapter | None = None,
        fetch_json: Callable[[str], tuple[dict[str, Any], dict[str, str], str]] | None = None,
    ) -> None:
        self.access_adapter = access_adapter or CourtListenerSearchAdapter(fetch_json=fetch_json)

    def build_url(self, limit: int = 1) -> str:
        return self.access_adapter.build_url(limit)

    def retrieve(self, limit: int = 1) -> RetrievalResult:
        retrieved_at = utc_now()
        retrieval_url, records, errors, diagnostics = self.access_adapter.retrieve(limit)
        for record in records:
            record["_retrieved_at"] = retrieved_at
        return RetrievalResult(
            self.source,
            retrieval_url,
            retrieved_at,
            records,
            errors,
            access_method=self.access_adapter.method_name,
            diagnostics=diagnostics,
            source_reliability=courtlistener_reliability_assessment(
                self.access_adapter.method_name, retrieved_at
            ),
        )
