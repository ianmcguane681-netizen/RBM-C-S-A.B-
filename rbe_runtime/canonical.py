"""Canonical serialization and deterministic identifiers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


UTC = timezone.utc


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def sha256_digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def canonical_hash(value: Any) -> str:
    return sha256_digest(canonical_json_bytes(value))


def deterministic_id(prefix: str, *parts: str, length: int = 24) -> str:
    seed = "\x1f".join(parts).encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:length].upper()
    return f"{prefix}-{digest}"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def require_rfc3339_utc(value: str) -> str:
    if not value.endswith("Z"):
        raise ValueError("Timestamp must use an RFC 3339 UTC Z suffix")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo != UTC:
        raise ValueError("Timestamp must be UTC")
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")

