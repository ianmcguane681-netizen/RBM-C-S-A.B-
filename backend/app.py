"""FastAPI projection and command boundary for the operator UI.

Reads are projections of the same files and domain objects used by the CLI.  A reaper
command calls :func:`lib.reaping.reap` directly rather than shelling out, so the UI and CLI
cannot grow two definitions of what a run means.  Sending orders is disabled unless both the
request and the server configuration explicitly opt in.
"""
from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
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
    expected = os.environ.get("PROVENA_COMMAND_KEY", "")
    if not expected:
        raise HTTPException(503, "Command API is not configured; reads remain available")
    if provided != expected:
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
        allow_credentials=True,
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
    def overview() -> dict[str, Any]:
        return status.as_json()

    @app.get("/api/v1/connectors")
    def connectors(probe: bool = False) -> dict[str, Any]:
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
