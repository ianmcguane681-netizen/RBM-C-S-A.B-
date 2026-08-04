"""The UI boundary must project truth and make moving money deliberately difficult."""
from __future__ import annotations

import asyncio
import json

from backend.app import create_app
from lib.reaping import Reaping


def request(app, method: str, path: str, *, payload=None, headers=None):
    """Exercise the ASGI app without Starlette's optional httpx2 test dependency."""

    body = json.dumps(payload).encode() if payload is not None else b""
    sent = []
    incoming = False

    async def receive():
        nonlocal incoming
        if incoming:
            return {"type": "http.disconnect"}
        incoming = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    if payload is not None:
        raw_headers.append((b"content-type", b"application/json"))
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "headers": raw_headers, "client": ("test", 1),
        "server": ("test", 80), "root_path": "",
    }
    asyncio.run(app(scope, receive, send))
    start = next(message for message in sent if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"") for message in sent if message["type"] == "http.response.body"
    )
    if not response_body:
        parsed = None
    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError:
        parsed = response_body.decode()
    return start["status"], parsed


def test_liveness_needs_no_secret_but_the_money_view_does(monkeypatch):
    """A probe that needs a key is a probe nobody wires up. The stakes are another matter.

    `/api/v1/overview` carries the portfolio's assets, every open decision's subject, and
    each lane's ring-fence and unsettled exposure — the same set this repository
    gitignores because it is public. The server binds every interface by default so
    container previews can reach it, so an open read is open to the network.
    """

    monkeypatch.delenv("PROVENA_COMMAND_KEY", raising=False)
    app = create_app()

    health_status, health = request(app, "GET", "/health")
    overview_status, _ = request(app, "GET", "/api/v1/overview")
    connectors_status, _ = request(app, "GET", "/api/v1/connectors")

    assert health_status == 200
    assert health == {"status": "ok"}
    assert overview_status == 503
    assert connectors_status == 503


def test_an_unset_key_withholds_the_money_view_rather_than_publishing_it(monkeypatch):
    """The absent-key case fails toward stopping, exactly as an absent autonomy key does.

    "Nobody configured a secret" must not resolve to "everybody may read the stakes". It
    is the same defect as an absent config key resolving to placing freely, arriving at
    the transport layer instead of the operating one.
    """

    monkeypatch.delenv("PROVENA_COMMAND_KEY", raising=False)

    response_status, body = request(create_app(), "GET", "/api/v1/overview")

    assert response_status == 503
    assert "not a public server" in json.dumps(body)


def test_the_money_view_is_served_to_a_caller_holding_the_key(monkeypatch):
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")

    response_status, overview = request(
        create_app(), "GET", "/api/v1/overview",
        headers={"X-Provena-Command-Key": "test-key"})

    assert response_status == 200
    assert {"capital", "decisions", "engines", "money_lanes"} <= set(overview)


def test_a_wrong_key_is_refused_rather_than_downgraded_to_a_read(monkeypatch):
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")

    response_status, _ = request(
        create_app(), "GET", "/api/v1/overview",
        headers={"X-Provena-Command-Key": "not-the-key"})

    assert response_status == 401


def test_browser_root_serves_the_operator_dashboard():
    status, response = request(create_app(), "GET", "/")

    assert status == 200
    assert "PROVENA" in response
    assert "app.js" in response


def test_standalone_asset_routes_support_the_same_dashboard_document():
    app = create_app()

    css_status, css = request(app, "GET", "/styles.css")
    js_status, script = request(app, "GET", "/app.js")

    assert css_status == js_status == 200
    assert "command-map" in css
    assert "offlineOverview" in script


def test_connector_projection_preserves_missing_as_missing(monkeypatch):
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")

    response_status, response = request(
        create_app(), "GET", "/api/v1/connectors",
        headers={"X-Provena-Command-Key": "test-key"})

    assert response_status == 200
    crypto = next(row for row in response["lanes"] if row["lane"] == "crypto")
    assert crypto["status"] == "BLOCKED"
    assert crypto["requirements"][0]["status"] == "NOT_CONFIGURED"


def test_reaper_command_is_unavailable_when_server_has_no_command_key(monkeypatch):
    monkeypatch.delenv("PROVENA_COMMAND_KEY", raising=False)
    response_status, _ = request(
        create_app(), "POST", "/api/v1/reapers/run", payload={"dry_run": True})

    assert response_status == 503


def test_live_execution_needs_server_switch_and_exact_confirmation(monkeypatch):
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")
    monkeypatch.delenv("PROVENA_EXECUTION_ENABLED", raising=False)
    response_status, _ = request(
        create_app(), "POST", "/api/v1/reapers/run",
        headers={"X-Provena-Command-Key": "test-key"},
        payload={"lane": "stocks", "dry_run": False, "confirmation": "MONEY MAY MOVE"},
    )

    assert response_status == 409


def test_dry_run_invokes_domain_reaper_without_placing(monkeypatch):
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")
    called = {}

    def fake_reap(*, lanes=None, place=True):
        called.update(lanes=lanes, place=place)
        return Reaping()

    monkeypatch.setattr("backend.app.reap", fake_reap)
    response_status, response = request(
        create_app(), "POST", "/api/v1/reapers/run",
        headers={"X-Provena-Command-Key": "test-key"},
        payload={"lane": "arb"},
    )

    assert response_status == 200
    assert called == {"lanes": ("arb",), "place": False}
    assert response["dry_run"] is True
