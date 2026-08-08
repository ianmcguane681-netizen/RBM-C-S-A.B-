"""A controlled package whose line endings are not pinned is validated on Linux and broken
on Windows, and the repository looks identical either way.

Each methodology profile is a controlled package: its files are hashed and its manifest is
compared byte for byte. Git on Windows defaults to `core.autocrlf=true`, which rewrites text
to CRLF **on checkout** — so the bytes on disk stop being the bytes that were hashed, and
`validate_package` refuses the profile. Nothing is wrong with the commit; the working tree
was rewritten on the way out.

`.gitattributes` pins `eol=lf` to prevent that, and it listed RBM-001, 002 and 003 because
those were the profiles that existed when it was written. RBM-004 and RBM-005 arrived later
and were never added. The defect was invisible to every Linux checkout and to CI, and
surfaced the first time somebody cloned the repository on Windows: nine failures, all
reporting that a controlled package failed validation, on a checkout that was correct.

This is the same shape as the lane registry problem — a list that must be extended in a
second place, where forgetting is silent. So the property is not "these five paths are
listed"; it is **every profile the registry knows about is covered**, derived from the
registry, so that adding a sixth profile without a line here fails here rather than on
somebody's laptop months later.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from controlled_authority.profiles import PROFILES

REPO_ROOT = Path(__file__).resolve().parents[1]
GITATTRIBUTES = REPO_ROOT / ".gitattributes"

#: Suffixes whose bytes are hashed. Matches CONTROLLED_TEXT_SUFFIXES in rbm_package.
CONTROLLED_TEXT = {".md", ".json", ".txt", ".yaml", ".yml"}


def patterns() -> list[str]:
    lines = GITATTRIBUTES.read_text(encoding="utf-8").splitlines()
    return [line.split()[0] for line in lines
            if line.strip() and not line.lstrip().startswith("#")]


def covering_pattern(relative: str) -> str | None:
    """The `.gitattributes` entry that pins this path, or None.

    Only `dir/**` and exact paths are recognised. That is deliberately narrower than git's
    own matching: a pattern this cannot understand is one a reader cannot be sure about
    either, and the answer to an unclear pin is to write a clear one.
    """

    for pattern in patterns():
        stem = pattern[:-3] if pattern.endswith("/**") else pattern
        if relative == stem or relative.startswith(stem.rstrip("/") + "/"):
            return pattern
    return None


class TestEveryControlledPackageHasItsLineEndingsPinned:
    @pytest.mark.parametrize("profile_id", sorted(PROFILES))
    def test_each_profile_package_is_pinned_to_lf(self, profile_id):
        """The property that was false for RBM-004 and RBM-005 for months."""

        spec = PROFILES[profile_id]
        relative = spec.package_root.relative_to(REPO_ROOT).as_posix()
        pattern = covering_pattern(relative)

        assert pattern is not None, (
            f"{profile_id} lives at {relative}/ and no .gitattributes entry covers it. "
            f"Its controlled text will be rewritten to CRLF by a Windows checkout and its "
            f"manifest hashes will stop matching, so the package fails validation on a "
            f"clone that is correct in the repository. Add:\n"
            f"    {relative}/** text eol=lf"
        )

    @pytest.mark.parametrize("profile_id", sorted(PROFILES))
    def test_the_pin_is_lf_and_not_merely_text(self, profile_id):
        """`text` alone normalises in the index and still checks out CRLF on Windows.

        Only `eol=lf` forces the working tree to match the bytes that were hashed, which is
        the thing the manifest comparison actually depends on.
        """

        spec = PROFILES[profile_id]
        relative = spec.package_root.relative_to(REPO_ROOT).as_posix()
        pattern = covering_pattern(relative)
        line = next(l for l in GITATTRIBUTES.read_text(encoding="utf-8").splitlines()
                    if l.strip().startswith(pattern))

        assert "eol=lf" in line, (
            f"{profile_id} is matched by {pattern!r}, which does not pin eol=lf. "
            f"`text` alone leaves the checkout platform-dependent."
        )


class TestTheControlledBytesAreActuallyLF:
    @pytest.mark.parametrize("profile_id", sorted(PROFILES))
    def test_no_controlled_text_file_contains_a_carriage_return(self, profile_id):
        """The pin is the mechanism; this is the outcome it exists for.

        It also catches a file committed with CRLF already in it, which `.gitattributes`
        would not fix on its own.
        """

        spec = PROFILES[profile_id]
        offenders = [
            path.relative_to(spec.package_root).as_posix()
            for path in sorted(spec.package_root.rglob("*"))
            if path.is_file() and path.suffix.lower() in CONTROLLED_TEXT
            and b"\r" in path.read_bytes()
        ]

        assert not offenders, (
            f"{profile_id} has controlled text with carriage returns: {offenders}. "
            f"If this fails on a fresh clone, .gitattributes did not take effect — run "
            f"`git rm --cached -r .` then `git reset --hard` to re-checkout with the "
            f"attributes applied."
        )
