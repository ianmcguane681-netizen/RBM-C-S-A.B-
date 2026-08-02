"""Which methodology profiles this runtime recognises, and where they live.

The package validator used to hold `PROFILE_ID = "RBM-001"` as a module constant, and
that was not laziness -- it is the cross-check. A package states its own identity in
`PROFILE.json`, so validating that identity against the profile itself proves only
that a file equals itself. The constant is the independent claim the package is
measured against.

Supporting a second profile therefore cannot mean reading identity from the package.
It means having more than one independent claim, which is what this registry is.
Every entry is a statement by the runtime -- not by the package -- that a profile of
this id and version is expected at this path, and a package that disagrees fails to
load rather than redefining what it is.

Adding a profile is adding an entry here plus the directory it names. Nothing else in
the runtime enumerates profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class PackageSpec:
    """A controlled methodology package: its identity, location, and expected contents.

    `schema_files` and `reviewer_spec_count` are declared rather than counted from the
    directory for the same reason as the identity: a validator that derives its
    expectations from what it finds cannot detect a missing file.
    """

    profile_id: str
    profile_version: str
    package_root: Path
    schema_files: frozenset[str]
    reviewer_spec_count: int
    methodology_document: str
    methodology_terms: frozenset[str] = field(default_factory=frozenset)

    @property
    def profile_path(self) -> Path:
        return self.package_root / "PROFILE.json"

    @property
    def manifest_path(self) -> Path:
        return self.package_root / "MANIFEST.json"

    @property
    def schema_root(self) -> Path:
        return self.package_root / "schemas"

    @property
    def spec_root(self) -> Path:
        return self.package_root / "specs"


_CANONICAL_SCHEMAS = frozenset(
    {
        "tpl-rir.schema.json",
        "tpl-fnd.schema.json",
        "tpl-rrr.schema.json",
        "tpl-bdr.schema.json",
        "tpl-rmp.schema.json",
        "tpl-mri.schema.json",
        "tpl-cor.schema.json",
    }
)

# The record templates are RBE architecture, not methodology: every profile produces
# independent reviews, findings, and a board decision record. A profile varies in what
# those records are *about*, so the schema set is shared and stated per profile rather
# than assumed -- a profile that legitimately needed a different set would say so here,
# and the difference would be visible instead of silent.

RBM_001 = PackageSpec(
    profile_id="RBM-001",
    profile_version="2.2.0",
    package_root=REPO_ROOT / "docs" / "review-board",
    schema_files=_CANONICAL_SCHEMAS,
    reviewer_spec_count=8,
    methodology_document="REVIEW-BOARD-METHODOLOGY.md",
    methodology_terms=frozenset(
        {
            "## 10. Process Status and Decision Framework",
            "`INSUFFICIENT_EVIDENCE`",
            "`PROCEDURALLY_INCOMPLETE`",
            "### 6B. Canonical RBE Lifecycle Mapping",
            "### 16.2 Activation Gate",
            "Decision Finalisation and Publication Separation",
        }
    ),
)

RBM_002 = PackageSpec(
    profile_id="RBM-002",
    profile_version="1.0.0",
    package_root=REPO_ROOT / "docs" / "engineering-board",
    schema_files=_CANONICAL_SCHEMAS,
    reviewer_spec_count=8,
    methodology_document="ENGINEERING-REVIEW-METHODOLOGY.md",
    methodology_terms=frozenset(
        {
            "## 10. Process Status and Decision Framework",
            "`INSUFFICIENT_EVIDENCE`",
            "`PROCEDURALLY_INCOMPLETE`",
            "### 6B. Canonical RBE Lifecycle Mapping",
            "### 16.2 Activation Gate",
            "Decision Finalisation and Publication Separation",
        }
    ),
)

RBM_003 = PackageSpec(
    profile_id="RBM-003",
    profile_version="1.0.0",
    package_root=REPO_ROOT / "docs" / "crypto-board",
    schema_files=_CANONICAL_SCHEMAS,
    reviewer_spec_count=8,
    methodology_document="CRYPTO-REVIEW-METHODOLOGY.md",
    methodology_terms=frozenset(
        {
            "## 10. Process Status and Decision Framework",
            "`INSUFFICIENT_EVIDENCE`",
            "`PROCEDURALLY_INCOMPLETE`",
            "### 6B. Canonical RBE Lifecycle Mapping",
            "### 16.2 Activation Gate",
            "Decision Finalisation and Publication Separation",
        }
    ),
)
RBM_004 = PackageSpec(
    profile_id="RBM-004",
    profile_version="1.0.0",
    package_root=REPO_ROOT / "docs" / "stocks-board",
    schema_files=_CANONICAL_SCHEMAS,
    reviewer_spec_count=8,
    methodology_document="STOCKS-REVIEW-METHODOLOGY.md",
    methodology_terms=frozenset(
        {
            "## 10. Process Status and Decision Framework",
            "`INSUFFICIENT_EVIDENCE`",
            "`PROCEDURALLY_INCOMPLETE`",
            "### 6B. Canonical RBE Lifecycle Mapping",
            "### 16.2 Activation Gate",
            "Decision Finalisation and Publication Separation",
        }
    ),
)

RBM_005 = PackageSpec(
    profile_id="RBM-005",
    profile_version="1.0.0",
    package_root=REPO_ROOT / "docs" / "arb-board",
    schema_files=_CANONICAL_SCHEMAS,
    reviewer_spec_count=8,
    methodology_document="ARBITRAGE-REVIEW-METHODOLOGY.md",
    methodology_terms=frozenset(
        {
            "## 10. Process Status and Decision Framework",
            "`INSUFFICIENT_EVIDENCE`",
            "`PROCEDURALLY_INCOMPLETE`",
            "### 6B. Canonical RBE Lifecycle Mapping",
            "### 16.2 Activation Gate",
            "Decision Finalisation and Publication Separation",
        }
    ),
)


PROFILES: dict[str, PackageSpec] = {
    RBM_001.profile_id: RBM_001,
    RBM_002.profile_id: RBM_002,
    RBM_003.profile_id: RBM_003,
    RBM_004.profile_id: RBM_004,
    RBM_005.profile_id: RBM_005,
}

DEFAULT_PROFILE_ID = RBM_001.profile_id


def get(profile_id: str | None = None) -> PackageSpec:
    """Resolve a registered profile, defaulting to the research review board.

    An unknown id raises rather than falling back. A caller that asked for RBM-002 and
    silently received RBM-001 would run an engineering review under research rules and
    have no way to tell.
    """

    resolved = profile_id or DEFAULT_PROFILE_ID
    try:
        return PROFILES[resolved]
    except KeyError:
        raise LookupError(
            f"No methodology profile registered as {resolved!r}. "
            f"Registered: {', '.join(sorted(PROFILES))}"
        ) from None
