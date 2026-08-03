"""The UI must see quota truth, and the backend must not buy prices it will discard."""
from __future__ import annotations

import json
import urllib.parse

from connectors.oddsapi import OddsApiCredentials, OddsApiSource, Usage


class Response:
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps([]).encode("utf-8")


def test_selected_books_are_in_the_paid_request_not_filtered_afterwards():
    requests = []

    def open_request(request):
        requests.append(request)
        return Response()

    source = OddsApiSource(
        OddsApiCredentials("test-key"),
        bookmakers=("bet365", "skybet"),
        opener=open_request,
    )
    source.quotes("soccer_epl")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(requests[0].full_url).query)

    assert query["bookmakers"] == ["bet365,skybet"]
    assert "regions" not in query


def test_unknown_quota_is_null_instead_of_zero():
    assert Usage().to_dict() == {
        "status": "UNKNOWN",
        "remaining": None,
        "used": None,
        "last_request_cost": None,
    }
