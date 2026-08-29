"""The UI boundary must project truth and make moving money deliberately difficult."""
from __future__ import annotations

import asyncio
import json

import pytest

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
    monkeypatch.delenv("PROVENA_VIEW_KEY", raising=False)
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
    monkeypatch.delenv("PROVENA_VIEW_KEY", raising=False)

    response_status, body = request(create_app(), "GET", "/api/v1/overview")

    assert response_status == 503
    assert "not a public server" in json.dumps(body)


def test_the_view_key_opens_the_money_view_and_not_the_lanes(monkeypatch):
    """The whole reason there are two secrets: the browser only ever needs the weaker one.

    A dashboard is a static page with nowhere safe to keep a key, so live state in a
    browser means a key in browser storage. This test pins which key that can be — one
    whose entire power is seeing what the CLI already prints. A single key for both would
    make the convenient thing also the thing that puts a lane-running credential one
    cross-site script away.
    """

    monkeypatch.setenv("PROVENA_VIEW_KEY", "view-key")
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "command-key")
    app = create_app()
    headers = {"X-Provena-View-Key": "view-key"}

    read_status, overview = request(app, "GET", "/api/v1/overview", headers=headers)
    command_status, _ = request(
        app, "POST", "/api/v1/reapers/run", payload={"dry_run": True}, headers=headers)

    assert read_status == 200
    assert {"capital", "money_lanes"} <= set(overview)
    assert command_status == 401


def test_the_command_key_also_reads_because_it_already_outranks_the_view_key(monkeypatch):
    monkeypatch.setenv("PROVENA_VIEW_KEY", "view-key")
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "command-key")

    response_status, _ = request(
        create_app(), "GET", "/api/v1/overview",
        headers={"X-Provena-Command-Key": "command-key"})

    assert response_status == 200


def test_a_view_key_alone_still_refuses_every_command(monkeypatch):
    """No view key configuration turns into a command surface, even with no command key.

    With only a view key set the commands are unconfigured, and unconfigured refuses.
    """

    monkeypatch.setenv("PROVENA_VIEW_KEY", "view-key")
    monkeypatch.delenv("PROVENA_COMMAND_KEY", raising=False)

    response_status, _ = request(
        create_app(), "POST", "/api/v1/reapers/run", payload={"dry_run": True},
        headers={"X-Provena-View-Key": "view-key"})

    assert response_status == 503


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
    # The dashboard no longer ships a fabricated offline state. It used to invent
    # NOT_CONNECTED lane statuses and UNKNOWN breaker states to have something to draw when
    # it could not read the API — in the same words the measured ones use — so a page that
    # had asked nothing was indistinguishable from one reporting three dead lanes and an
    # unarmed breaker. Ian saw exactly that and said the key should be needed before entry.
    assert "offlineOverview" not in script
    assert "offlineConnectors" not in script
    assert "showGate" in script


def test_the_dashboard_body_is_hidden_until_the_api_has_answered():
    """Nothing may render before the key, and the four reasons must stay distinguishable.

    `hidden` on `<main>` is what makes "I have not asked" visually different from "I asked
    and the lanes are down". Serving the document with the body already visible would put
    the fabricated-state defect straight back, since the tiles ship with placeholder text.
    """

    _, document = request(create_app(), "GET", "/")

    assert 'id="nexus" hidden' in document.replace("  ", " ")
    assert 'id="gate"' in document
    assert document.index('id="gate"') < document.index('id="nexus"')


def test_the_hidden_attribute_is_not_defeated_by_a_display_rule():
    """A one-line CSS bug that hid nothing, found by screenshotting the unlocked page.

    `hidden` is a UA-stylesheet `display:none`, so ANY author `display` beats it. `.gate`
    sets `display:grid` to centre its card, which silently un-hid the gate: the unlocked
    dashboard rendered with the key prompt still sitting above it. Reading the diff did not
    show this and could not have.
    """

    _, css = request(create_app(), "GET", "/styles.css")

    assert "[hidden]{display:none!important}" in css.replace(" ", "")


@pytest.fixture
def crypto_unparked(monkeypatch):
    """Put crypto back in the rotation for the length of one test.

    The two projection tests below are about the PROJECTION — a missing credential must
    reach the API as missing, a present one as ready — and crypto is the vehicle because
    it is the one lane whose credential is a single environment variable a test can own.
    The lane itself was parked on 2026-08-29, so the fixture states that dependency out
    loud instead of the tests quietly asserting something about a lane that is no longer
    evaluated. Parking is meant to be one line to undo; this is that line.
    """

    import lib.reaping as reaping

    monkeypatch.setattr(reaping, "LANES", reaping.LANES + ("crypto",))
    monkeypatch.setattr(reaping, "PARKED_LANES", {})
    monkeypatch.setattr(reaping, "ALL_LANES", reaping.LANES + ("crypto",))


def test_a_parked_lane_projects_as_parked_rather_than_blocked(monkeypatch):
    """The API must not report a stood-down lane as a credential somebody should go and
    set. BLOCKED is a job on a list; PARKED is a decision that has already been made."""

    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")
    monkeypatch.delenv("QUICKNODE_ETHEREUM_URL", raising=False)

    response_status, response = request(
        create_app(), "GET", "/api/v1/connectors",
        headers={"X-Provena-Command-Key": "test-key"})

    assert response_status == 200
    crypto = next(row for row in response["lanes"] if row["lane"] == "crypto")
    assert crypto["status"] == "PARKED"
    # And it is not silently dropped, which would read as a lane that never existed.
    assert crypto["requirements"] == []


def test_connector_projection_preserves_missing_as_missing(monkeypatch, crypto_unparked):
    """A missing connector must project as missing, and the test must MAKE it missing.

    This asserted crypto was BLOCKED without removing `QUICKNODE_ETHEREUM_URL`, so it
    passed only on machines that had never configured the lane it was testing. The first
    person to set that variable — the intended outcome of the deployment runbook — got a
    red suite for doing the thing the documentation told them to do. A suite that goes red
    when you configure the system is one people stop believing, which costs far more than
    the assertion is worth.

    The endpoint reads the real environment by design, so the test owns its preconditions
    rather than inheriting whatever the developer's machine happens to hold.
    """

    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")
    monkeypatch.delenv("QUICKNODE_ETHEREUM_URL", raising=False)

    response_status, response = request(
        create_app(), "GET", "/api/v1/connectors",
        headers={"X-Provena-Command-Key": "test-key"})

    assert response_status == 200
    crypto = next(row for row in response["lanes"] if row["lane"] == "crypto")
    assert crypto["status"] == "BLOCKED"
    assert crypto["requirements"][0]["status"] == "NOT_CONFIGURED"


def test_a_configured_chain_endpoint_projects_as_ready(monkeypatch, crypto_unparked):
    """The other half, which nothing asserted: a lane that IS configured says so.

    Without this the suite only ever checked the unconfigured case, so the projection
    could have reported BLOCKED unconditionally and stayed green.
    """

    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")
    monkeypatch.setenv("QUICKNODE_ETHEREUM_URL", "https://example.invalid/abc123")

    response_status, response = request(
        create_app(), "GET", "/api/v1/connectors",
        headers={"X-Provena-Command-Key": "test-key"})

    assert response_status == 200
    crypto = next(row for row in response["lanes"] if row["lane"] == "crypto")
    assert crypto["status"] == "READY"


def test_the_connector_projection_never_carries_the_endpoint_secret(monkeypatch):
    """A QuickNode URL embeds its auth token in the path, and this endpoint is reachable
    from a browser. Reporting the lane as configured must not report WITH WHAT."""

    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")
    monkeypatch.setenv("QUICKNODE_ETHEREUM_URL", "https://example.invalid/s3cr3t-token")

    _, response = request(
        create_app(), "GET", "/api/v1/connectors",
        headers={"X-Provena-Command-Key": "test-key"})

    assert "s3cr3t-token" not in json.dumps(response)


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


def test_the_api_and_the_cli_report_one_run_the_same_way(monkeypatch):
    """Two serialisers for one domain is two answers to one question.

    `backend/app.py` kept a private `_jsonable` that checked `is_dataclass` first and had
    no `to_dict` branch, so every domain type that had curated an honest projection was
    flattened back to raw fields on the way out of this API. An UNRESOLVED placement —
    an order that MAY EXIST — reported `filled_quantity: 0.0` and dropped
    `needs_a_person`, while `run.py --reap --json` reported null and true for the same
    object. A caller reading this endpoint would resubmit an order the CLI would have
    told it to go and query.
    """

    from lib.placing import UNRESOLVED, Placement
    from lib.reaping import CONFIGURED, Assembly, Reaping

    reaping = Reaping(
        assemblies=(Assembly("stocks", CONFIGURED),),
        placements=(Placement("stocks", UNRESOLVED, subject="ACME",
                              position_id="POS-1", client_order_id="abc",
                              requested_quantity=3.0, reason="the broker returned 502"),),
    )
    monkeypatch.setenv("PROVENA_COMMAND_KEY", "test-key")
    # `backend.app` binds `reap` at import, so the name to replace is the one it holds.
    monkeypatch.setattr("backend.app.reap", lambda **_kw: reaping)

    _status, body = request(
        create_app(), "POST", "/api/v1/reapers/run", payload={"dry_run": True},
        headers={"X-Provena-Command-Key": "test-key"})

    assert body["result"] == reaping.to_dict()
    placement = body["result"]["placements"][0]
    assert placement["filled_quantity"] is None
    assert placement["needs_a_person"] is True
    assert body["result"]["schema_version"]
