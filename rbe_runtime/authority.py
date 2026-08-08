"""Load and verify authoritative RBE and RBM packages.

The loader used to know one profile by hardcoded path. It now resolves a profile from
the registry in `controlled_authority.profiles`, so a review is conducted under a named
methodology rather than under whichever one happened to be on disk. The architecture
package (RBE-001) is not parameterised: profiles map onto it, they do not replace it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from controlled_authority.profiles import PackageSpec
from controlled_authority.profiles import get as get_profile_spec
from controlled_authority.rbe_package import check as validate_rbe_package
from controlled_authority.rbm_package import validate_package as validate_rbm_package
from rbe_runtime.constants import RBE_RELEASE
from rbe_runtime.errors import RBEError
from rbe_runtime.models import ExecutionMode


def _semver(value: str) -> tuple[int, int, int]:
    try:
        major, minor, patch = value.split(".")
        return int(major), int(minor), int(patch)
    except (AttributeError, TypeError, ValueError) as exc:
        raise RBEError(
            "RBE_INVALID_VERSION",
            f"Invalid semantic version: {value!r}",
            "RBE-ES-VER-003",
        ) from exc


@dataclass(frozen=True, slots=True)
class AuthorityBundle:
    repo_root: Path
    state_machine: dict[str, Any]
    verdict_taxonomy: dict[str, Any]
    profile: dict[str, Any]
    profile_manifest: dict[str, Any]
    reviewer_specs: dict[str, Path]
    schemas: dict[str, Path]
    spec: PackageSpec

    @property
    def profile_id(self) -> str:
        return self.spec.profile_id

    @classmethod
    def load(
        cls, repo_root: str | Path | None = None, *, profile_id: str | None = None
    ) -> "AuthorityBundle":
        spec = get_profile_spec(profile_id)
        canonical_root = Path(__file__).resolve().parents[1]
        root = Path(repo_root).resolve() if repo_root else canonical_root
        # validate_rbe_package/validate_rbm_package derive their own package roots
        # from controlled_authority.__file__ and cannot be pointed elsewhere, so a
        # different repo_root would load documents that were never validated.
        # Refuse it rather than silently trusting unvalidated authority material.
        if root != canonical_root:
            raise RBEError(
                "RBE_AUTHORITY_ROOT_NOT_VALIDATABLE",
                "Authority packages can only be validated at the canonical repository root",
                "RBE-ES-DEC-002",
                {"requested_root": str(root), "canonical_root": str(canonical_root)},
            )
        try:
            validate_rbe_package()
            validate_rbm_package(spec)
        except Exception as exc:
            # The reason travels with the refusal. This used to carry only
            # `type(exc).__name__`, which turned "Controlled text must use canonical LF
            # endings: ['STOCKS-REVIEW-METHODOLOGY.md']" — a message naming the file and
            # the fix — into "PackageValidationError", and a Windows checkout into an
            # afternoon. A refusal that does not say what a person can go and do about it
            # trains the reader to skim it.
            raise RBEError(
                "RBE_AUTHORITY_PACKAGE_INVALID",
                f"The controlled RBE or RBM package failed validation: {exc}",
                "RBE-ES-DEC-002",
                {"error_type": type(exc).__name__, "reason": str(exc)[:500],
                 "profile_id": spec.profile_id},
            ) from exc

        rbe_root = root / "docs" / "rbe-001" / "v1.1.0"
        rbm_root = spec.package_root
        state_machine = json.loads(
            (rbe_root / "registers" / "state_machine.json").read_text(
                encoding="utf-8"
            )
        )
        verdict_taxonomy = json.loads(
            (rbe_root / "registers" / "verdict_taxonomy.json").read_text(
                encoding="utf-8"
            )
        )
        profile = json.loads((rbm_root / "PROFILE.json").read_text(encoding="utf-8"))
        profile_manifest = json.loads(
            (rbm_root / "MANIFEST.json").read_text(encoding="utf-8")
        )
        reviewer_specs = {
            "-".join(path.name.split("-")[:2]): path
            for path in sorted((rbm_root / "specs").glob("RBS-*.md"))
        }
        schemas = {
            path.name.removesuffix(".schema.json"): path
            for path in sorted((rbm_root / "schemas").glob("*.schema.json"))
        }

        bundle = cls(
            repo_root=root,
            state_machine=state_machine,
            verdict_taxonomy=verdict_taxonomy,
            profile=profile,
            profile_manifest=profile_manifest,
            reviewer_specs=reviewer_specs,
            schemas=schemas,
            spec=spec,
        )
        bundle.validate_identity()
        return bundle

    def validate_identity(self) -> None:
        if self.state_machine.get("architecture_release") != RBE_RELEASE:
            raise RBEError(
                "RBE_ARCHITECTURE_VERSION_MISMATCH",
                "State-machine release does not match the runtime authority",
                "RBE-ES-LIF-001",
            )
        if self.profile.get("profile_id") != self.spec.profile_id or self.profile.get(
            "version"
        ) != self.spec.profile_version:
            raise RBEError(
                "RBE_PROFILE_IDENTITY_MISMATCH",
                f"The loaded methodology is not {self.spec.profile_id} "
                f"v{self.spec.profile_version}",
                "RBE-ES-DEC-002",
            )
        minimum = self.profile.get("architecture_authority", {}).get(
            "minimum_compatible_version"
        )
        if _semver(RBE_RELEASE) < _semver(minimum):
            raise RBEError(
                "RBE_PROFILE_ARCHITECTURE_INCOMPATIBLE",
                "The methodology requires a newer RBE architecture",
                "RBE-ES-DEC-002",
                {"minimum": minimum, "loaded": RBE_RELEASE},
            )
        # Counts come from the registry, not from what the directory happens to hold.
        # A validator that derives its expectation from what it finds cannot detect a
        # missing file -- it would simply expect one fewer.
        if len(self.reviewer_specs) != self.spec.reviewer_spec_count or len(
            self.schemas
        ) != len(self.spec.schema_files):
            raise RBEError(
                "RBE_PROFILE_INCOMPLETE",
                "Reviewer specifications or schemas are incomplete for this profile",
                "RBE-ES-DEC-002",
                {
                    "profile_id": self.spec.profile_id,
                    "reviewer_specs": len(self.reviewer_specs),
                    "expected_reviewer_specs": self.spec.reviewer_spec_count,
                    "schemas": len(self.schemas),
                    "expected_schemas": len(self.spec.schema_files),
                },
            )

    def require_execution_mode(self, mode: ExecutionMode) -> None:
        status = self.profile["status"]
        binding = self.profile["binding"]
        if mode == ExecutionMode.ADVISORY_DRY_RUN:
            if status not in {"RELEASE_CANDIDATE", "ACTIVE"}:
                raise RBEError(
                    "RBE_PROFILE_INACTIVE",
                    "The profile cannot be used for an advisory dry run",
                    "RBE-ES-DEC-002",
                    {"profile_status": status},
                )
            return
        if status != "ACTIVE" or binding is not True or not self.profile.get(
            "human_approval_record"
        ):
            raise RBEError(
                "RBE_PROFILE_NOT_ACTIVE",
                "Binding execution requires an ACTIVE, human-approved profile",
                "RBE-ES-DEC-002",
                {"profile_status": status, "binding": binding},
            )
