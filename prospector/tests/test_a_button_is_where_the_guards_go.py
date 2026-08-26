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
                    costs=PACKAGE / "costs.example.json", operator="Ian McGuane")
    runner._argv = lambda **options: [  # noqa: SLF001 - the fixture stands in for a network
        "--area", "Invented Town", "--operator", "Ian McGuane", "--from-file", FIXTURE,
        "--out", str(runner.out_dir), "--register", str(runner.register),
        "--images", "none", "--browser", "never", "--no-fetch",
        "--costs", str(PACKAGE / "costs.example.json")]
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
