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
from dataclasses import asdict, is_dataclass
from hmac import compare_digest
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import status
from lib.preflight import all_lanes
from lib.reaping import reap


_run_lock = Lock()
_static = Path(__file__).with_name("static")


def _jsonable(value: Any) -> Any:
    """Turn domain results into a transport projection without changing the domain types."""

    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # Connector responses can contain provider objects. Their repr is diagnostic only and
    # must not turn a successful run into a serialization failure.
    return repr(value)


def _allowed_origins() -> list[str]:
    configured = os.environ.get("PROVENA_UI_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


class ReaperCommand(BaseModel):
    lane: Literal["arb", "stocks", "crypto"] | None = None
    dry_run: bool = True
    confirmation: str = Field(default="", max_length=80)


def _execution_enabled(command: ReaperCommand) -> bool:
    return (
        not command.dry_run
        and os.environ.get("PROVENA_EXECUTION_ENABLED", "").lower() == "true"
        and command.confirmation == "MONEY MAY MOVE"
    )


def _require_command_key(provided: str | None) -> None:
    """The one gate in front of both the money data and the money commands.

    `compare_digest` rather than `==`: the key is a fixed secret compared on every
    request, which is the shape a timing oracle needs, and the constant-time compare costs
    nothing to use.

    An absent key is 503 rather than an open door. There is no configuration of this
    server in which not having set a secret means everyone may read the stakes.
    """

    expected = os.environ.get("PROVENA_COMMAND_KEY", "")
    if not expected:
        raise HTTPException(
            503,
            "PROVENA_COMMAND_KEY is not set, so this API serves no lane data and accepts "
            "no commands. Set it on the server; an unset key is not a public server.",
        )
    if provided is None or not compare_digest(provided, expected):
        raise HTTPException(401, "A valid command key is required")


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
        allow_headers=["Content-Type", "X-Provena-Command-Key"],
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
        command_key: str | None = Header(default=None, alias="X-Provena-Command-Key"),
    ) -> dict[str, Any]:
        _require_command_key(command_key)
        return status.as_json()

    @app.get("/api/v1/connectors")
    def connectors(
        probe: bool = False,
        command_key: str | None = Header(default=None, alias="X-Provena-Command-Key"),
    ) -> dict[str, Any]:
        # Behind the key as well: this names which credentials exist and which lanes are
        # blocked without them, which is a map of the operator's setup even though it
        # never returns a secret. `probe=true` also spends real API quota on request.
        _require_command_key(command_key)
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
        return {
            "dry_run": command.dry_run,
            "execution_enabled": _execution_enabled(command),
            "result": _jsonable(result),
            "description": result.describe(),
        }

    return app


app = create_app()
