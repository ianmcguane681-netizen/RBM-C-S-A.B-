"""A dashboard is exactly where the two refusals would quietly become one-click actions.

The command line makes you type what you are doing. A page with buttons on it does not, and
the two buttons that must never exist are the ones a page like this grows first: send, and
publish. Neither is disabled-until-later here; both are absent, and these tests keep them
absent by checking the routes rather than the wording.

The rest is about the states. A scan that finished having prepared nobody is a real answer
and must not read like a failure; a scan that raised must not read like a quiet success;
and nothing at all having run yet is a third thing again — which is the state a dashboard
is most tempted to draw as "all clear".
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from prospector import cli, ireland
from prospector.dashboard import (FAILED, FINISHED, HOST, IDLE, RUNNING, Runner, serve)

PACKAGE = Path(__file__).resolve().parent.parent
FIXTURE = str(PACKAGE / "fixtures/synthetic-area.overpass.json")


@pytest.fixture()
def dashboard(tmp_path):
    runner = Runner(out_dir=tmp_path / "dossiers", register=tmp_path / "prepared.json",
                    costs=PACKAGE / "costs.example.json", operator="Ian McGuane",
                    engagements=tmp_path / "engagements.json",
                    history=tmp_path / "runs.json", watch_dir=tmp_path / "watch")
    runner._argv = lambda **options: [  # noqa: SLF001 - the fixture stands in for a network
        "--area", "Invented Town", "--operator", "Ian McGuane", "--from-file", FIXTURE,
        "--out", str(runner.out_dir), "--register", str(runner.register),
        "--images", "none", "--browser", "never", "--no-fetch",
        "--costs", str(PACKAGE / "costs.example.json"),
        "--history", str(runner.history)]
    server = serve(runner, 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield runner, f"http://{HOST}:{port}"
    server.shutdown()


def _get(base, path):
    return json.loads(urllib.request.urlopen(base + path, timeout=10).read())


def _post(base, path, payload):
    request = urllib.request.Request(base + path, data=json.dumps(payload).encode(),
                                     headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _settle(runner, seconds=30.0):
    deadline = time.time() + seconds
    while runner.status == RUNNING and time.time() < deadline:
        time.sleep(0.1)
    return runner.status


def test_there_is_no_send_route_and_no_publish_route(dashboard):
    """Checked as routes, not as wording. A button is a route with a label on it."""

    _, base = dashboard
    for path in ("/api/send", "/api/publish", "/api/deploy", "/api/email"):
        status, payload = _post(base, path, {})
        assert status == 404, path
        assert payload["error"] == "no such route"


def test_nothing_having_run_is_its_own_state(dashboard):
    """Not "all clear". Nobody has looked yet, which is the thing a dashboard hides."""

    _, base = dashboard
    state = _get(base, "/api/state")
    assert state["status"] == IDLE
    assert state["log"] == []


def test_a_scan_runs_and_ends_finished(dashboard):
    runner, base = dashboard
    status, payload = _post(base, "/api/scan", {"area": "Donegal"})
    assert status == 200 and payload["started"]
    assert _settle(runner) == FINISHED
    assert runner.exit_code == 0
    assert any("PREPARED" in line for line in runner.log)


def test_a_second_scan_is_refused_while_one_is_running(dashboard):
    """One at a time, because two runs share a register and would race on it."""

    runner, base = dashboard
    runner.status = RUNNING
    status, payload = _post(base, "/api/scan", {"area": "Mayo"})
    assert status == 409
    assert not payload["started"]
    assert "already running" in payload["message"]


def test_a_scan_with_no_area_is_refused_rather_than_guessing_one(dashboard):
    _, base = dashboard
    status, payload = _post(base, "/api/scan", {"area": "   "})
    assert status == 409
    assert "pick an area" in payload["message"]


def test_a_scan_that_raises_ends_failed_with_the_traceback_on_the_page(dashboard):
    """A failure in a worker thread is otherwise a page that just stops updating."""

    runner, base = dashboard
    runner._argv = lambda **options: ["--area", "x"]  # missing --operator: argparse exits
    _post(base, "/api/scan", {"area": "Donegal"})
    assert _settle(runner) == FAILED
    assert runner.error
    assert runner.log


def test_the_dossier_list_is_read_from_disk_rather_than_from_the_log(dashboard):
    """The log says what a run reported; the disk says what exists, and they diverge."""

    runner, base = dashboard
    _post(base, "/api/scan", {"area": "Donegal"})
    _settle(runner)
    rows = _get(base, "/api/dossiers")["dossiers"]
    assert rows
    assert all(row["has_briefing"] for row in rows)
    assert {row["name"] for row in rows} >= {"Bridge End Barbers"}


def test_a_dossier_whose_evidence_will_not_parse_is_listed_as_broken(dashboard):
    """Not skipped. A silently shorter list is how a half-written run looks fine."""

    runner, base = dashboard
    _post(base, "/api/scan", {"area": "Donegal"})
    _settle(runner)
    folder = next(runner.out_dir.glob("*/*/evidence.json"))
    folder.write_text("{ not json", encoding="utf-8")
    rows = _get(base, "/api/dossiers")["dossiers"]
    assert any(row.get("broken") for row in rows)


def test_files_outside_the_dossier_directory_are_refused(dashboard):
    """The server hands out files from a folder; that is a traversal bug waiting to be
    written, so it is a resolved-path check rather than a string one."""

    runner, base = dashboard
    runner.out_dir.mkdir(parents=True, exist_ok=True)
    for attempt in ("../../../etc/passwd", "..%2f..%2fetc%2fpasswd", "/etc/passwd"):
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"{base}/files/{attempt}", timeout=10)
        assert caught.value.code == 404


def test_the_dashboard_only_ever_binds_the_loopback_address():
    """It serves client contact details and what an hour of somebody's time is worth."""

    assert HOST == "127.0.0.1"
    source = (PACKAGE / "dashboard.py").read_text(encoding="utf-8")
    assert "0.0.0.0" not in source


def test_the_dashboard_refuses_an_automation_as_operator(capsys):
    from prospector.dashboard import main

    assert main(["--operator", "Webatron"]) == 2
    assert "names an automation" in capsys.readouterr().out


def test_every_irish_authority_is_offered_and_the_north_is_marked_separately(dashboard):
    _, base = dashboard
    areas = _get(base, "/api/areas")["areas"]
    names = {area["name"] for area in areas}
    assert len(areas) == len(ireland.ALL)
    assert {"Donegal", "Cork City", "County Cork", "Fingal", "Tipperary"} <= names
    northern = [area for area in areas if area["group"].startswith("Northern")]
    assert len(northern) == len(ireland.NORTH)


def test_the_areas_that_are_two_places_say_so(dashboard):
    """The trap that quietly halves a county: the city is not inside it."""

    _, base = dashboard
    areas = {area["name"]: area for area in _get(base, "/api/areas")["areas"]}
    assert "NOT inside County Cork" in areas["Cork City"]["note"]
    assert "excludes Cork City" in areas["County Cork"]["note"]


def test_a_northern_scan_is_run_as_the_united_kingdom(tmp_path):
    """Different country, different sending rules, and the scan says so without asking."""

    runner = Runner(out_dir=tmp_path, register=tmp_path / "r.json",
                    costs=tmp_path / "c.json", operator="Ian McGuane")
    assert "--country" in runner._argv(area="County Antrim")
    argv = runner._argv(area="County Antrim")
    assert argv[argv.index("--country") + 1] == "GB"
    assert runner._argv(area="Donegal")[-1] == "IE"


def test_the_scan_is_the_same_code_path_as_the_command_line():
    """No second implementation to drift. The button builds an argv and calls main."""

    assert callable(cli.main)
    source = (PACKAGE / "dashboard.py").read_text(encoding="utf-8")
    assert "cli.main(" in source


# ---------------------------------------------------------------------------------------
# Everything else on the page: the ledgers, the money, and the two actions that are allowed
# ---------------------------------------------------------------------------------------

def test_recording_what_a_person_said_is_allowed_and_being_that_person_is_not(dashboard):
    """The dashboard writes down a decision. It cannot make one.

    A named person authorising publication is exactly the record the gate wants, and typing
    it in is data entry. What the page cannot do is supply the name itself, so the same
    constructor refusal applies here as on the command line.
    """

    runner, base = dashboard
    status, payload = _post(base, "/api/record", {
        "identity": "node/1", "name": "Bridge End Barbers", "status": "AUTHORISED",
        "by": "agent: webatron", "role": "owner", "via": "email", "on": "2026-08-27"})
    assert status == 400
    assert "names an automation" in payload["message"]

    status, payload = _post(base, "/api/record", {
        "identity": "node/1", "name": "Bridge End Barbers", "status": "AUTHORISED",
        "by": "Cathy Doherty", "role": "owner", "via": "email 2026-08-27",
        "on": "2026-08-27"})
    assert status == 200 and payload["ok"]
    rows = _get(base, "/api/engagements")["engagements"]
    assert rows[0]["by"] == "Cathy Doherty"


def test_an_authorisation_with_no_medium_is_refused_on_the_page_too(dashboard):
    runner, base = dashboard
    status, payload = _post(base, "/api/record", {
        "identity": "node/1", "by": "Cathy Doherty", "role": "owner", "via": "",
        "on": "2026-08-27"})
    assert status == 400
    assert "how it was given" in payload["message"]


def test_marking_a_business_live_needs_the_authorisation_first(dashboard):
    runner, base = dashboard
    status, payload = _post(base, "/api/record", {"identity": "node/2", "status": "LIVE"})
    assert status == 400
    assert "needs an authorisation" in payload["message"]


def test_an_unreadable_engagement_ledger_is_shown_as_unknown_rather_than_empty(dashboard):
    """An empty list would read as "nobody has replied", which is a different fact."""

    runner, base = dashboard
    runner.engagements.parent.mkdir(parents=True, exist_ok=True)
    runner.engagements.write_text("{ not json", encoding="utf-8")
    rows = _get(base, "/api/engagements")["engagements"]
    assert rows and rows[0]["status"] == "UNKNOWN"


def test_rebuilding_a_dossier_picks_up_what_the_business_sent_back(dashboard):
    """The revisions loop, from a button. Their words reach the page; nothing is invented."""

    runner, base = dashboard
    _post(base, "/api/scan", {"area": "Donegal"})
    _settle(runner)
    folder = next(runner.out_dir.glob("*/*/evidence.json")).parent
    handover = folder / "OWNER-SUPPLIED.json"
    handover.write_text(json.dumps({
        "from": {"person": "Cathy Doherty", "role": "owner", "medium": "email",
                 "on": "2026-08-27"},
        "copy": {"about": "Two chairs, no appointments, and the kettle is on."}}),
        encoding="utf-8")
    relative = str(folder.relative_to(runner.out_dir))
    status, payload = _post(base, "/api/rebuild", {"relative": relative})
    assert status == 200 and payload["ok"], payload
    assert "kettle is on" in (folder / "index.html").read_text(encoding="utf-8")


def test_a_rebuild_outside_the_dossier_directory_is_refused(dashboard):
    _, base = dashboard
    status, payload = _post(base, "/api/rebuild", {"relative": "../../../etc"})
    assert status == 400
    assert payload["message"] == "no such dossier"


def test_the_money_panel_says_what_has_not_been_priced(dashboard, tmp_path):
    """The panel exists because the largest line is the one that gets left out."""

    runner, base = dashboard
    runner.costs = tmp_path / "nothing.json"
    costs = _get(base, "/api/costs")
    assert not costs["complete"]
    assert "labour" in costs["unpriced"]
    assert "does not exist" in costs["note"]


def test_a_run_is_recorded_in_the_history_and_shown_against_the_area(dashboard):
    """So a cadence can come out of what happened rather than out of a guess."""

    runner, base = dashboard
    _post(base, "/api/scan", {"area": "Donegal"})
    _settle(runner)
    history = _get(base, "/api/history")
    assert history["runs"], "the run should be recorded"
    assert history["runs"][0]["area"] == "Invented Town"
    assert history["runs"][0]["outcome"] == "LOOKED"


def test_an_area_nobody_has_scanned_says_so_rather_than_showing_nothing(dashboard):
    runner, base = dashboard
    areas = _get(base, "/api/history")["areas"]
    assert areas["Mayo"]["status"] == "NEVER_SCANNED"


def test_an_unreadable_history_is_not_read_as_never_scanned(dashboard):
    """Which would send somebody over the same county the day the file went missing."""

    runner, base = dashboard
    runner.history.parent.mkdir(parents=True, exist_ok=True)
    runner.history.write_text("{ not a list", encoding="utf-8")
    areas = _get(base, "/api/history")["areas"]
    assert areas["Mayo"]["status"] == "UNKNOWN"


def test_a_live_site_with_no_baseline_is_not_watched_rather_than_fine(dashboard):
    runner, base = dashboard
    _post(base, "/api/record", {
        "identity": "node/1", "name": "Bridge End Barbers", "status": "AUTHORISED",
        "by": "Cathy Doherty", "role": "owner", "via": "email", "on": "2026-08-27",
        "live_url": "https://bridgeendbarbers.example"})
    watched = _get(base, "/api/watch")["watched"]
    assert watched and watched[0]["status"] == "NOT_WATCHED"
    assert "not the same as nothing having changed" in watched[0]["detail"]


def test_the_page_actually_runs_in_a_browser(dashboard):
    """A page that serves a 200 and then dies on a syntax error looks fine from Python.

    This test exists because that happened: an escape sequence in the template rendered as
    a real newline, the script broke on the first line that used it, and every panel sat
    on its placeholder while the API behind it answered perfectly. Nothing in a Python
    test could see it.
    """

    from prospector import browser

    if not browser.available()[0]:
        pytest.skip("Playwright is not installed here")

    from playwright.sync_api import sync_playwright

    runner, base = dashboard
    runner.out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    launch = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    executable = browser.chromium_path()
    if executable:
        launch["executable_path"] = executable
    proxy = __import__("os").environ.get("HTTPS_PROXY")
    if proxy:
        launch["proxy"] = {"server": proxy, "bypass": "localhost,127.0.0.1,::1"}
    with sync_playwright() as engine:
        chrome = engine.chromium.launch(**launch)
        try:
            page = chrome.new_page()
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(base + "/", wait_until="load", timeout=20000)
            page.wait_for_timeout(2000)
            options = page.eval_on_selector("#area", "el => el.options.length")
            status = page.inner_text("#status")
            money = page.inner_text("#costs")
        finally:
            chrome.close()

    assert errors == [], errors
    assert options == len(ireland.ALL), "the county picker did not populate"
    assert status in (IDLE, FINISHED, RUNNING, FAILED)
    assert "COST OF ONE SITE" in money, "the money panel never loaded"
