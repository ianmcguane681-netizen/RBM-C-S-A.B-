"""Recompute a controlled package's own checksum and manifest root after an edit.

    python tools/repin_package.py RBM-004 RBM-005

A controlled package is hash-pinned: PROFILE.json carries a checksum over itself and
MANIFEST.json carries a root over every controlled file. Editing any file invalidates both,
which is the point -- an unnoticed edit to a methodology is exactly what the pinning
exists to catch.

This is the only sanctioned way to re-pin, and it refuses a package that any published
decision was decided under. A published decision records the checksum it was reviewed
against; re-pinning underneath it would leave a record claiming to have been reviewed
against a package that no longer exists, which is a fabricated audit chain.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from controlled_authority import profiles  # noqa: E402
from controlled_authority.rbm_package import (  # noqa: E402
    build_manifest,
    calculate_profile_checksum,
    normalize_controlled_text_files,
)

STORE = Path("data")


def decided_checksums() -> set[str]:
    """Every methodology checksum any stored review was opened against."""

    seen: set[str] = set()
    for db in STORE.glob("*.sqlite3"):
        try:
            connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            rows = connection.execute(
                "SELECT raw_record_json FROM review_sessions"
            ).fetchall()
        except sqlite3.Error:
            continue
        for (raw,) in rows:
            try:
                seen.add(json.loads(raw).get("methodology_checksum", ""))
            except (TypeError, ValueError):
                continue
        connection.close()
    return {c for c in seen if c}


def repin(profile_id: str, *, pinned: set[str]) -> tuple[str, str]:
    spec = profiles.get(profile_id)
    profile_path = spec.package_root / "PROFILE.json"
    current = json.loads(profile_path.read_text(encoding="utf-8"))["checksum"]
    if current in pinned:
        raise SystemExit(
            f"REFUSED: {profile_id} checksum {current} is recorded on a stored review. "
            f"Re-pinning underneath it would leave that review claiming to have been "
            f"decided against a package that no longer exists. Version the profile "
            f"instead."
        )

    normalize_controlled_text_files(spec)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["checksum"] = calculate_profile_checksum(profile)
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    manifest = build_manifest(spec)
    spec.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return profile["checksum"], manifest["root_sha256"]


def main(profile_ids: list[str]) -> int:
    pinned = decided_checksums()
    if pinned:
        print(f"{len(pinned)} checksum(s) are recorded on stored reviews and are refused.\n")
    for profile_id in profile_ids:
        checksum, root = repin(profile_id, pinned=pinned)
        print(f"{profile_id}\n  methodology_checksum   {checksum}\n"
              f"  manifest_root_sha256   {root}")
    print("\nAny initiation naming these packages must be re-pinned to match.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1:]))
