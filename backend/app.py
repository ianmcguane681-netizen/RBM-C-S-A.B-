"""FastAPI projection and command boundary for the operator UI.

Reads are projections of the same files and domain objects used by the CLI.  A reaper
command calls :func:`lib.reaping.reap` directly rather than shelling out, so the UI and CLI
cannot grow two definitions of what a run means.  Sending orders is disabled unless both the
request and the server configuration explicitly opt in.

**Reads carry money data and are therefore behind the same key as commands.** The first
version left them open, and `/api/v1/overview` returns the portfolio's assets and lanes,
every open decision's subject, each lane's ring-fence balance and its unsettled exposure —
which is precisely the set this repository gitignores because it is public. The server
also binds every interface by default so container previews can reach it, so "open" meant
open to the network rather than to the desktop. An absent key now withholds that data
instead of publishing it, the same way an absent autonomy key resolves to manual rather
than to placing freely.

`/health` stays open, because a liveness probe that needs a secret is a liveness probe
nobody wires up, and it discloses nothing but the fact that a process is running.
"""
from __future__ import annotations

import os
from hmac import compare_digest
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import status
from lib.preflight import all_lanes
from lib.reaping import reap
from lib.ui_contract import serialise


_run_lock = Lock()
_static = Path(__file__).with_name("static")


def _jsonable(value: Any) -> Any:
    """The repository's one serialiser, not a second one that happens to agree.

    This was a private copy, and it did not agree. It checked `is_dataclass` before
    anything else and had no `to_dict` branch, so every domain type that had spent effort
    on an honest projection was flattened straight back to its raw fields on the way out
    of this API: an UNRESOLVED placement reported `filled_quantity: 0.0` for an order that
    MAY EXIST, dropped `needs_a_person`, and carried no `schema_version`. The CLI's
    `--reap --json` and this endpoint returned two different shapes for the same run.

    `lib.ui_contract.serialise` prefers `to_dict` and falls back to dataclass fields, so
    types that curate their own view keep it and types that do not are unchanged.
    """

    return serialise(value)


def _allowed_origins() -> list[str]:
    configured = os.environ.get("PROVENA_UI_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


class ReaperCommand(BaseModel):
    """One run request. `lane` is validated against the registry, not a literal.

    It was `Literal["arb", "stocks", "crypto"]`, which turns adding a fourth lane into a
    422 from a file nobody would think to look in — the lane assembles, schedules and
    places perfectly well and only the API says it does not exist. More lanes are planned,
    so the allowed set is read from `lib.reaping.LANES` at validation time.
    """

    lane: str | None = None
    dry_run: bool = True
    confirmation: str = Field(default="", max_length=80)

    @field_validator("lane")
    @classmethod
    def _known_lane(cls, value: str | None) -> str | None:
        from lib.reaping import LANES

        if value is not None and value not in LANES:
            raise ValueError(f"unknown lane {value!r}; choose from {', '.join(LANES)}")
        return value


def _execution_enabled(command: ReaperCommand) -> bool:
    return (
        not command.dry_run
        and os.environ.get("PROVENA_EXECUTION_ENABLED", "").lower() == "true"
        and command.confirmation == "MONEY MAY MOVE"
    )


def _matches(provided: str | None, expected: str) -> bool:
    """`compare_digest` rather than `==`.

    The key is a fixed secret compared on every request, which is the shape a timing
    oracle needs, and a constant-time compare costs nothing to use.
    """

    return bool(expected) and provided is not None and compare_digest(provided, expected)


def _require_command_key(provided: str | None) -> None:
    """The gate in front of running a lane, which is the gate in front of moving money.

    An absent key is 503 rather than an open door. There is no configuration of this
    server in which not having set a secret means anyone may run a lane.
    """

    expected = os.environ.get("PROVENA_COMMAND_KEY", "")
    if not expected:
        raise HTTPException(
            503,
            "PROVENA_COMMAND_KEY is not set, so this API accepts no commands. Set it on "
            "the server; an unset key is not a public server.",
        )
    if not _matches(provided, expected):
        raise HTTPException(401, "A valid command key is required")


def _require_view_key(view: str | None, command: str | None) -> None:
    """Reads take EITHER key, and that split is the point rather than a convenience.

    The dashboard is a static page with nowhere safe to keep a secret, so showing live
    state in a browser means a key ends up in browser storage. `PROVENA_VIEW_KEY` exists
    so the key that ends up there is the one whose entire power is *seeing what the CLI
    already prints*. The key that can run a lane never has to leave the operator's shell.

    A single key for both would have made the convenient thing — paste it into the
    dashboard — also the thing that puts a money-moving credential one cross-site script
    away from an attacker. Two secrets, two powers, and the dangerous one stays out of the
    browser.

    Holding `PROVENA_COMMAND_KEY` implies the lesser power, so it is accepted here too.
    Neither configured is 503: unset still never means public.
    """

    view_key = os.environ.get("PROVENA_VIEW_KEY", "")
    command_key = os.environ.get("PROVENA_COMMAND_KEY", "")
    if not view_key and not command_key:
        raise HTTPException(
            503,
            "Neither PROVENA_VIEW_KEY nor PROVENA_COMMAND_KEY is set, so this API serves "
            "no lane data. Set PROVENA_VIEW_KEY for a read-only dashboard; an unset key "
            "is not a public server.",
        )
    if _matches(view, view_key) or _matches(command, command_key):
        return
    raise HTTPException(401, "A valid view key is required")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Provena Operator API",
        version="0.1.0",
        description="Read projections and governed commands for reapers and executions.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        # No credentials. Authentication here is an explicit header the caller sets, not a
        # cookie the browser attaches, so allowing credentials bought nothing — and paired
        # with a wildcard origin, which nothing stopped an operator configuring, it is the
        # combination that lets any page in the browser read this API as the operator.
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Provena-View-Key", "X-Provena-Command-Key"],
    )
    app.mount("/assets", StaticFiles(directory=_static), name="assets")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(_static / "index.html")

    @app.get("/styles.css", include_in_schema=False)
    def standalone_styles() -> FileResponse:
        return FileResponse(_static / "styles.css", media_type="text/css")

    @app.get("/app.js", include_in_schema=False)
    def standalone_script() -> FileResponse:
        return FileResponse(_static / "app.js", media_type="text/javascript")

    @app.get("/api/v1/overview")
    def overview(
        view_key: str | None = Header(default=None, alias="X-Provena-View-Key"),
        command_key: str | None = Header(default=None, alias="X-Provena-Command-Key"),
    ) -> dict[str, Any]:
        _require_view_key(view_key, command_key)
        return status.as_json()

    @app.get("/api/v1/connectors")
    def connectors(
        probe: bool = False,
        view_key: str | None = Header(default=None, alias="X-Provena-View-Key"),
        command_key: str | None = Header(default=None, alias="X-Provena-Command-Key"),
    ) -> dict[str, Any]:
        # Behind a key as well: this names which credentials exist and which lanes are
        # blocked without them, which is a map of the operator's setup even though it
        # never returns a secret. `probe=true` also spends real API quota on request.
        _require_view_key(view_key, command_key)
        lanes = all_lanes(probe=probe)
        return {
            "probed": probe,
            "lanes": [
                {
                    **_jsonable(lane),
                    "status": lane.status,
                    "missing": [requirement.name for requirement in lane.missing],
                }
                for lane in lanes
            ],
        }

    @app.post("/api/v1/reapers/run")
    def run_reapers(
        command: ReaperCommand,
        command_key: str | None = Header(default=None, alias="X-Provena-Command-Key"),
    ) -> dict[str, Any]:
        _require_command_key(command_key)
        if not command.dry_run and not _execution_enabled(command):
            raise HTTPException(
                409,
                "Live execution requires PROVENA_EXECUTION_ENABLED=true and the exact "
                "confirmation 'MONEY MAY MOVE'",
            )
        if not _run_lock.acquire(blocking=False):
            raise HTTPException(409, "A reaper command is already running")
        try:
            result = reap(
                lanes=(command.lane,) if command.lane else None,
                place=not command.dry_run,
            )
        finally:
            _run_lock.release()
        # `result.to_dict()` explicitly, not a generic projection of it. This is the same
        # run `run.py --reap --json` reports, so it is the same payload — carrying
        # schema_version, the four kinds of nothing kept apart, and placements beside the
        # harvests. Two shapes for one run is how a UI ends up believing something the CLI
        # would have told it plainly.
        return {
            "dry_run": command.dry_run,
            "execution_enabled": _execution_enabled(command),
            "result": result.to_dict(),
            "description": result.describe(),
        }

    return app


app = create_app()
