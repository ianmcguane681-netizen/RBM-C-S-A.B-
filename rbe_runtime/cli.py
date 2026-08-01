"""Headless inspection and export commands for the RBE runtime."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from rbe_runtime.artifacts import ArtifactExporter
from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.canonical import canonical_json
from rbe_runtime.constants import ENGINE_VERSION
from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rbe-runtime",
        description="Deterministic, non-binding RBE-001 Foundation runtime tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("version", help="Show runtime and authority versions")
    subparsers.add_parser(
        "validate-authority",
        help="Validate the controlled RBE-001 and RBM-001 packages",
    )

    audit = subparsers.add_parser("verify-audit", help="Verify a session audit chain")
    audit.add_argument("--database", required=True, type=Path)
    audit.add_argument("--session", required=True)

    export = subparsers.add_parser(
        "export", help="Export a deterministic review bundle"
    )
    export.add_argument("--database", required=True, type=Path)
    export.add_argument("--session", required=True)
    export.add_argument("--output", required=True, type=Path)

    bundle = subparsers.add_parser(
        "verify-bundle", help="Verify an exported review bundle"
    )
    bundle.add_argument("--bundle", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "version":
            authority = AuthorityBundle.load()
            result = {
                "engine_version": ENGINE_VERSION,
                "architecture_release": authority.state_machine[
                    "architecture_release"
                ],
                "methodology_profile_id": authority.profile["profile_id"],
                "methodology_version": authority.profile["version"],
                "methodology_status": authority.profile["status"],
                "binding": authority.profile["binding"],
            }
        elif args.command == "validate-authority":
            authority = AuthorityBundle.load()
            result = {
                "valid": True,
                "architecture_release": authority.state_machine[
                    "architecture_release"
                ],
                "profile_id": authority.profile["profile_id"],
                "profile_version": authority.profile["version"],
                "profile_status": authority.profile["status"],
                "profile_checksum": authority.profile["checksum"],
                "manifest_root_sha256": authority.profile_manifest["root_sha256"],
            }
        elif args.command == "verify-audit":
            runtime = RBERuntime(args.database)
            result = runtime.repository.verify_audit(args.session)
        elif args.command == "export":
            runtime = RBERuntime(args.database)
            result = ArtifactExporter(
                runtime.repository, runtime.authority
            ).export(args.session, args.output)
        elif args.command == "verify-bundle":
            result = ArtifactExporter.verify(args.bundle)
        else:  # pragma: no cover - argparse enforces the closed command set.
            raise AssertionError(f"Unhandled command: {args.command}")
    except RBEError as exc:
        print(canonical_json(exc.to_dict()), file=sys.stderr)
        return 2
    except Exception as exc:  # Fail safely without paths, secrets, or stack traces.
        print(
            canonical_json(
                {
                    "error": {
                        "code": "RBE_COMMAND_FAILED",
                        "message": "The command failed safely; inspect controlled logs.",
                        "error_type": type(exc).__name__,
                    }
                }
            ),
            file=sys.stderr,
        )
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
