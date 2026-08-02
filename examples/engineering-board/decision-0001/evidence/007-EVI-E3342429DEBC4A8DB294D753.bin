"""Join an FJC Integrated Database case to its RECAP docket.

The IDB codes *who won* but says almost nothing about *what the case was about*.
Its statutory fields are `title=15, section=1681` on every FCRA record, with
`subsection` empty throughout, so an IDB row establishes that a Fair Credit
Reporting Act violation was found and not which duty was breached.

That gap is not academic. The first adjudicated record this study retrieved that
established occurrence was:

    United States v. Vivint Smart Home
    suit nature: 890 Other Statutory Actions

a government enforcement action about improperly *using* consumer reports to
qualify customers. It is a real FCRA violation, judicially resolved against the
respondent, and it has nothing to do with the reinvestigation failures this study
is about. Admitting it as corroboration would have proved the study's mechanism
with a case about something else -- an error that would have read as a success.

So this module exists to verify and to exclude, never to classify. It:

  * reconstructs the PACER docket number from the IDB's coded office and docket
    fields, giving a deterministic join key;
  * confirms the case exists in RECAP, so an IDB row is corroborated by a second
    record of the same dispute rather than trusted alone;
  * reads the docket's nature of suit, which is the one field that distinguishes a
    consumer credit case from an enforcement action filed under the same statute.

Docket *metadata* carries no narrative and no statutory subsection, so it cannot
supply a mechanism, and this module never infers one from a caption. The complaint
*document* is a different thing: it is the plaintiff's own account of what
happened, the same evidentiary class as a CFPB consumer narrative, so the study's
existing classifier applies to it unchanged. Where the join confirms a single
docket and the case is an original proceeding, that text is fetched, and it is what
finally gives an adjudicated record a mechanism.

The pairing carries a caveat that must travel with it: a complaint states what was
*alleged*, and the judgment establishes that a violation was *found*. Reading them
together assumes the judgment was entered on the pleaded claim, which is usually
but not always true where several counts are pleaded.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from core.http_retry import retrying_urlopen

COURTLISTENER_SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/search/"
USER_AGENT = "GS-CF001/0.1 methodology proof"
ACCESS_TIMEOUT_SECONDS = 45

# The join makes one request per adjudicated record, so a run of any size will meet
# the API's rate limit. Without backoff a limited run degrades every record to
# unjoined and the study's result depends on how busy the API was, which is the
# opposite of reproducible. A 429 is a request to wait, so the client waits.
INTER_REQUEST_DELAY_SECONDS = 0.5

# Nature of suit 480 is Consumer Credit, the category FCRA consumer claims are
# filed under. The FJC and RECAP render it variously as a bare code, a code with a
# label, or a label alone, so both forms are accepted -- and nothing else is.
CONSUMER_CREDIT_CODE = "480"
CONSUMER_CREDIT_LABEL = "consumer credit"


def pacer_docket_number(office: Any, fjc_docket_number: Any) -> str:
    """Rebuild the PACER docket number from the IDB's coded fields.

    The FJC stores a seven-digit docket number as a two-digit filing year followed
    by a five-digit sequence, with the division held separately in `office`. PACER
    renders the same case as ``office:YY-cv-NNNNN``. Verified against live data:
    ``office=2, docket=2100267, district=utd`` resolves to ``2:21-cv-00267``.

    Returns an empty string when the inputs cannot form a docket number, so a
    malformed row produces no lookup rather than a wrong one.
    """

    office_text = str(office or "").strip()
    digits = "".join(character for character in str(fjc_docket_number or "") if character.isdigit())
    if not office_text or len(digits) != 7:
        return ""
    return f"{office_text}:{digits[:2]}-cv-{digits[2:]}"


def court_id_from_district(district: Any) -> str:
    """Extract the CourtListener court id from an IDB district resource URL."""

    text = str(district or "").strip()
    if not text:
        return ""
    if "://" not in text:
        return text
    parts = [part for part in text.rstrip("/").split("/") if part]
    return parts[-1] if parts else ""


def is_consumer_credit_suit(suit_nature: Any) -> bool:
    """Whether a docket's nature of suit is the consumer credit category.

    This is the check that excludes *United States v. Vivint Smart Home*: an FCRA
    enforcement action carrying nature of suit 890, judicially resolved against the
    respondent, and entirely off this study's mechanism.
    """

    text = str(suit_nature or "").strip().lower()
    if not text:
        return False
    if CONSUMER_CREDIT_LABEL in text:
        return True
    leading = text.split()[0].strip(":;,")
    return leading == CONSUMER_CREDIT_CODE


class DocketJoinAdapter:
    """Look up the RECAP docket for a reconstructed docket number."""

    method_name = "courtlistener_docket_join"

    def __init__(
        self,
        fetch_json: Callable[[str], tuple[dict[str, Any], dict[str, str], str]] | None = None,
        *,
        token: str = "",
    ) -> None:
        self._fetch_json = fetch_json or self._default_fetch_json
        self.token = token

    def build_url(self, court_id: str, docket_number: str) -> str:
        params = {
            "type": "r",
            "q": f'docketNumber:"{docket_number}"',
            "court": court_id,
        }
        return f"{COURTLISTENER_SEARCH_URL}?{urllib.parse.urlencode(params)}"

    def lookup(self, court_id: str, docket_number: str) -> dict[str, Any]:
        """Return join fields for one case. Never raises: a failed join is a
        recorded absence, because an unreachable lookup must not look the same as
        a case that does not exist."""

        if not court_id or not docket_number:
            return _join_result(False, "insufficient join key")
        url = self.build_url(court_id, docket_number)
        try:
            payload, _headers, _status = self._fetch_json(url)
        except urllib.error.HTTPError as exc:
            return _join_result(False, f"docket lookup failed: HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
            return _join_result(False, f"docket lookup failed: {exc}")
        results = payload.get("results") or []
        if not results:
            return _join_result(False, "no RECAP docket matched the reconstructed number")
        if len(results) > 1:
            # An ambiguous join is not a join. Two dockets sharing a number in one
            # court means the reconstruction is not identifying a single case.
            return _join_result(False, f"ambiguous join: {len(results)} dockets matched")
        row = results[0]
        suit_nature = str(row.get("suitNature") or "")
        return {
            "join_verified": True,
            "join_note": "IDB case confirmed against a single RECAP docket.",
            "joined_case_name": row.get("caseName") or "",
            "joined_cause": row.get("cause") or "",
            "joined_suit_nature": suit_nature,
            "joined_docket_id": str(row.get("docket_id") or ""),
            "on_study_suit_nature": is_consumer_credit_suit(suit_nature),
        }

    def _default_fetch_json(self, url: str) -> tuple[dict[str, Any], dict[str, str], str]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        request = urllib.request.Request(url, headers=headers)
        with retrying_urlopen(request, timeout=ACCESS_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return json.loads(body), dict(response.headers.items()), str(response.status)


RECAP_DOCUMENTS_URL = "https://www.courtlistener.com/api/rest/v4/recap-documents/"

# FJC origin codes. Only an original proceeding begins with a complaint: a removed
# case opens with a notice of removal, a transferred one with transfer papers. So
# "document 1 is the complaint" is true exactly when origin is 1, and the database
# says which -- no assumption required.
FJC_ORIGIN_ORIGINAL_PROCEEDING = 1

COMPLAINT_LIMITATIONS = (
    "A complaint states the alleged mechanism; the judgment establishes that a violation was found.",
    "A complaint may plead several counts, and judgment may have been entered on only one of them.",
    "Pairing a pleaded mechanism with a judgment assumes the judgment was on the pleaded claim.",
    "RECAP document coverage depends on user contributions; absence of text proves nothing.",
)


def fetch_complaint_text(
    docket_id: str,
    origin: Any,
    *,
    fetch_json: Callable[[str], dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """Return the complaint's text for an original proceeding, and why or why not.

    This is what gives an adjudicated record a mechanism. The IDB says a violation
    was found but never which duty was breached, and docket metadata carries no
    narrative. A complaint does: it is the plaintiff's own account of what happened,
    the same evidentiary class as a CFPB consumer narrative, so the study's existing
    classifier applies to it unchanged rather than needing a new inference.

    Returns empty text whenever the document cannot be identified with certainty.
    RECAP coverage is contributed by users, so an absent document is an absence of
    information and never evidence that nothing was alleged.
    """

    if not str(docket_id).strip():
        return "", "no docket id"
    try:
        if int(origin) != FJC_ORIGIN_ORIGINAL_PROCEEDING:
            return "", (
                f"origin {origin} is not an original proceeding, so document 1 is not the complaint"
            )
    except (TypeError, ValueError):
        return "", "origin not recorded, so the initiating document cannot be identified"

    url = f"{RECAP_DOCUMENTS_URL}?{urllib.parse.urlencode({'docket_entry__docket__id': docket_id, 'page_size': '20'})}"
    try:
        payload = (fetch_json or _default_fetch_json)(url)
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        return "", f"document retrieval failed: {error}"

    for row in payload.get("results") or []:
        if str(row.get("document_number") or "").strip() != "1":
            continue
        text = " ".join(str(row.get("plain_text") or "").split())
        if text:
            return text, "complaint text from RECAP document 1 of an original proceeding"
    return "", "no document 1 text available in RECAP for this docket"


def _default_fetch_json(url: str) -> dict[str, Any]:
    """Module-level document fetch, distinct from the adapter's search fetch."""

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    token = os.environ.get("COURTLISTENER_API_TOKEN", "")
    if token:
        headers["Authorization"] = f"Token {token}"
    request = urllib.request.Request(url, headers=headers)
    with retrying_urlopen(request, timeout=ACCESS_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def _join_result(verified: bool, note: str) -> dict[str, Any]:
    return {
        "join_verified": verified,
        "join_note": note,
        "joined_case_name": "",
        "joined_cause": "",
        "joined_suit_nature": "",
        "joined_docket_id": "",
        # Unknown is not permission. An unjoined record cannot be shown to be on
        # this study's subject matter, so it is treated as though it is not.
        "on_study_suit_nature": False,
    }


def join_idb_record(
    record: dict[str, Any],
    adapter: DocketJoinAdapter,
    *,
    fetch_documents: Callable[[str], dict[str, Any]] | None = None,
    with_complaint_text: bool = True,
) -> dict[str, Any]:
    """Enrich one normalised IDB record in place with its docket join fields.

    Where the join confirms a single docket, the complaint's text is fetched too.
    That is what carries the mechanism: without it an adjudicated record classifies
    to the unclassified fallback and cannot corroborate anything, which is exactly
    where the review board left this study.
    """

    docket_number = pacer_docket_number(record.get("office"), record.get("docket_number"))
    court_id = court_id_from_district(record.get("district"))
    result = adapter.lookup(court_id, docket_number)
    record.update(result)
    record["pacer_docket_number"] = docket_number
    record["join_court_id"] = court_id

    text, note = "", "not attempted"
    if with_complaint_text and result.get("join_verified"):
        time.sleep(INTER_REQUEST_DELAY_SECONDS)
        text, note = fetch_complaint_text(
            result.get("joined_docket_id", ""), record.get("origin"), fetch_json=fetch_documents
        )
    record["complaint_text"] = text
    record["complaint_text_note"] = note
    record["complaint_limitations"] = list(COMPLAINT_LIMITATIONS) if text else []
    return record
