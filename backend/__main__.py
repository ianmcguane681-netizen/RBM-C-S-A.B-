"""Run the operator API on the interface and port supplied by the host."""
import os

import uvicorn


def server_address(environ: dict[str, str] | None = None) -> tuple[str, int]:
    """Resolve a preview-safe bind address without fixing it to container localhost."""

    env = os.environ if environ is None else environ
    host = env.get("HOST", "0.0.0.0").strip() or "0.0.0.0"
    try:
        port = int(env.get("PORT", "8000"))
    except ValueError as error:
        raise SystemExit("PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535")
    return host, port


if __name__ == "__main__":
    host, port = server_address()
    uvicorn.run("backend.app:app", host=host, port=port, reload=False)
