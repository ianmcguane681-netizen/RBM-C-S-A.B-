from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import TypedDict


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "docs" / "rbe-001" / "v1.1.0"
ARCHIVE_NAME = "RBE-001_AI_Reader_Package_v1.1.0.zip"
CHECKSUM_NAME = f"{ARCHIVE_NAME}.sha256"
MANIFEST_NAME = "MANIFEST.json"
REQUIREMENT_REGISTER = PACKAGE_ROOT / "registers" / "requirement_register.json"
MIGRATION_REGISTER = PACKAGE_ROOT / "registers" / "requirement_id_migration.csv"
FULL_ARCHITECTURE = (
    PACKAGE_ROOT / "architecture" / "RBE-001_Reference_Architecture_v1.1.0.md"
)

REQUIREMENT_PATTERN = re.compile(
    r"^\*\*(RBE-(?:ES-)?[A-Z]+-\d{3})\*\*\s+(.+)$"
)
ENGINEERING_ID_PATTERN = re.compile(r"\bRBE-ES-([A-Z]+)-(\d{3})\b")
REQUIREMENT_TERMINATORS = (".", "?", "!")
SEMANTICALLY_NORMALIZED_ENGINEERING_DOMAINS = {"DEC", "LIF", "TST"}

CANONICAL_OUTCOMES = [
    "PASS",
    "PASS_WITH_FINDINGS",
    "FAIL",
    "INSUFFICIENT_EVIDENCE",
    "DEFER_FOR_FURTHER_RESEARCH",
]
CANONICAL_PROCESS_STATUSES = [
    "READY",
    "PROCEDURALLY_INCOMPLETE",
    "BLOCKED",
    "VOID",
]
LEGACY_ENGINEERING_STATES = {
    "CREATED",
    "INPUT_VALIDATION",
    "READY_FOR_ASSIGNMENT",
    "SPECIALIST_REVIEW",
    "METHOD_REVIEW",
    "SCEPTICAL_REVIEW",
    "DECISION_PENDING",
    "DECISION_COMPLETE",
    "REMEDIATION_REQUIRED",
    "RE_REVIEW_PENDING",
    "CANCELLED",
}
FORBIDDEN_RELEASE_TEXT = {
    "Controlled architecture draft",
    "pending final RBM-001 terminology lock",
    "complete the sectional draft",
    "controlled sectional draft intended",
}


class PackageValidationError(RuntimeError):
    pass


class RequirementRecord(TypedDict):
    id: str
    line_end: int
    line_start: int
    section: str
    source: str
    statement: str


def package_path_sort_key(path: Path) -> tuple[str, str]:
    """Match the controlled package's canonical case-insensitive path order."""

    relative = path.relative_to(PACKAGE_ROOT).as_posix()
    return relative.casefold(), relative


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def source_documents() -> list[Path]:
    chapters = sorted(
        (PACKAGE_ROOT / "architecture" / "chapters").glob("*.md"),
        key=package_path_sort_key,
    )
    engineering = sorted(
        (PACKAGE_ROOT / "engineering").glob("*.md"),
        key=package_path_sort_key,
    )
    return chapters + engineering


def architecture_document_bytes() -> bytes:
    header = """---
document_id: RBE-001
title: Review Board Engine Reference Architecture
release_version: 1.1.0
status: normalization-release-candidate
publication_date: 2026-07-19
proposed_supersedes: RBE-001-v1.0.0
supersession_effective_on: named-human-principal-architect-approval
source_sha256: 0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31
---

# RBE-001 Review Board Engine Reference Architecture

## Document Control

| Field | Value |
|---|---|
| Document identifier | RBE-001 |
| Version | 1.1.0 |
| Status | Normalization release candidate - ready for human approval |
| Coverage | Chapters 1-23 |
| Historical source | RBE-001 v1.0.0 controlled PDF, checksum recorded above |
| Implementation consumer | Codex and engineering teams |
| Methodology relationship | Methodology-neutral core; live use requires an ACTIVE profile |
| Owner | Project Exchange / Provena |

## Normalization Authority

This candidate retains the normative v1.0.0 architectural substance while resolving release
metadata, outcome semantics, state ownership, requirement namespaces, and the relationship
between constitutional architecture, implementation profiles, and active methodologies. The
normalization registers are normative where they explicitly resolve a v1.0.0 conflict.
"""
    parts = [header.rstrip()]
    chapters = sorted(
        (PACKAGE_ROOT / "architecture" / "chapters").glob("*.md"),
        key=package_path_sort_key,
    )
    for chapter in chapters:
        text = chapter.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise PackageValidationError(f"Chapter lacks front matter: {chapter.name}")
        end = text.index("\n---\n", 4) + len("\n---\n")
        parts.append(text[end:].strip())
    return ("\n\n".join(parts).rstrip() + "\n").encode("utf-8")


def collect_requirements() -> list[RequirementRecord]:
    requirements: list[RequirementRecord] = []
    seen: dict[str, str] = {}
    for path in source_documents():
        lines = path.read_text(encoding="utf-8").splitlines()
        current_heading = ""
        line_index = 0
        while line_index < len(lines):
            line = lines[line_index]
            if line.startswith("#"):
                current_heading = line.lstrip("#").strip()
            match = REQUIREMENT_PATTERN.match(line)
            if not match:
                line_index += 1
                continue
            requirement_id, first_fragment = match.groups()
            relative = path.relative_to(PACKAGE_ROOT).as_posix()
            if requirement_id in seen:
                raise PackageValidationError(
                    f"Duplicate requirement {requirement_id}: {seen[requirement_id]} and {relative}"
                )

            fragments = [first_fragment.strip()]
            end_index = line_index
            while not fragments[-1].endswith(REQUIREMENT_TERMINATORS):
                end_index += 1
                if end_index >= len(lines):
                    raise PackageValidationError(
                        f"Unterminated requirement {requirement_id} in {relative}"
                    )
                continuation = lines[end_index].strip()
                if (
                    not continuation
                    or continuation.startswith(("#", "<!--", "|", "- ", "* ", "```"))
                    or REQUIREMENT_PATTERN.match(lines[end_index])
                ):
                    raise PackageValidationError(
                        f"Requirement {requirement_id} ends before terminal punctuation in {relative}"
                    )
                fragments.append(continuation)

            statement = " ".join(fragments)
            seen[requirement_id] = relative
            requirements.append(
                {
                    "id": requirement_id,
                    "line_end": end_index + 1,
                    "line_start": line_index + 1,
                    "section": current_heading,
                    "source": relative,
                    "statement": statement,
                }
            )
            line_index = end_index + 1
    return sorted(requirements, key=lambda item: item["id"])


def requirement_register_bytes(requirements: list[RequirementRecord]) -> bytes:
    payload = {
        "architecture_release": "1.1.0",
        "requirements": requirements,
        "schema_id": "rbe.requirement-register",
        "schema_version": "1.0.0",
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def migration_register_bytes(requirements: list[RequirementRecord]) -> bytes:
    architecture_ids = {
        item["id"] for item in requirements if not item["id"].startswith("RBE-ES-")
    }
    engineering_ids = sorted(
        item["id"] for item in requirements if item["id"].startswith("RBE-ES-")
    )
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "source_document",
            "source_version",
            "old_id",
            "new_id",
            "disposition",
            "note",
        ]
    )
    architecture_migrations = [
        (
            "Reference Architecture Chapter 2",
            "RBE-INF-001",
            "RBE-IBR-001",
            "Information-barrier requirement separated from the infrastructure namespace.",
        ),
        (
            "Reference Architecture Chapter 2",
            "RBE-AI-001",
            "RBE-AI-130",
            "Later Chapter 17 definition retains RBE-AI-001.",
        ),
        (
            "Reference Architecture Chapter 2",
            "RBE-AI-002",
            "RBE-AI-131",
            "Later Chapter 17 definition retains RBE-AI-002.",
        ),
        (
            "Reference Architecture Chapter 11",
            "RBE-OUT-001",
            "RBE-OUT-010",
            "Earlier Chapter 1 definition retains RBE-OUT-001.",
        ),
        (
            "Reference Architecture Chapter 11",
            "RBE-OUT-002",
            "RBE-OUT-011",
            "Earlier Chapter 1 definition retains RBE-OUT-002.",
        ),
    ]
    current_ids = {item["id"] for item in requirements}
    for source, old_id, new_id, note in architecture_migrations:
        if new_id not in current_ids:
            raise PackageValidationError(f"Missing normalized architecture ID: {new_id}")
        writer.writerow(
            [
                source,
                "1.0.0",
                old_id,
                new_id,
                "ARCHITECTURE_COLLISION_RESOLVED",
                note,
            ]
        )
    for new_id in engineering_ids:
        match = ENGINEERING_ID_PATTERN.fullmatch(new_id)
        if match is None:
            raise PackageValidationError(f"Invalid engineering requirement ID: {new_id}")
        old_id = f"RBE-{match.group(1)}-{match.group(2)}"
        collision = old_id in architecture_ids
        semantically_normalized = match.group(1) in SEMANTICALLY_NORMALIZED_ENGINEERING_DOMAINS
        if semantically_normalized:
            disposition = (
                "SEMANTIC_NORMALISATION_AND_NAMESPACE_COLLISION_RESOLVED"
                if collision
                else "SEMANTIC_NORMALISATION_AND_RENAMESPACE"
            )
            note = (
                "Requirement was renamespaced and revised by the v1.1.0 canonical state, "
                "verdict, or acceptance-test normalization; compare the source-qualified lineage."
            )
        else:
            disposition = "NAMESPACE_COLLISION_RESOLVED" if collision else "RENAMED_WITH_LINEAGE"
            note = (
                "Architecture retains the historical ID; engineering definition is superseded."
                if collision
                else "Engineering requirement moved to the explicit RBE-ES namespace."
            )
        writer.writerow(
            [
                "RBE-001 Engineering Specification",
                "1.0.0",
                old_id,
                new_id,
                disposition,
                note,
            ]
        )
    return buffer.getvalue().encode("utf-8")


def inventory_paths() -> list[Path]:
    excluded = {ARCHIVE_NAME, CHECKSUM_NAME, MANIFEST_NAME}
    return sorted(
        (
            path
            for path in PACKAGE_ROOT.rglob("*")
            if path.is_file() and path.name not in excluded
        ),
        key=package_path_sort_key,
    )


def manifest_bytes(paths: list[Path]) -> bytes:
    files = []
    for path in paths:
        content = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(PACKAGE_ROOT).as_posix(),
                "sha256": sha256_bytes(content),
                "size_bytes": len(content),
            }
        )
    root_hash = sha256_bytes(canonical_json(files))
    manifest = {
        "files": files,
        "package_id": "RBE-001-AI-READER",
        "package_version": "1.1.0",
        "publication_date": "2026-07-19",
        "release_status": "normalization-release-candidate",
        "supersession_effective_on": "named-human-principal-architect-approval",
        "root_hash": root_hash,
        "schema_id": "rbe.ai-reader-manifest",
        "schema_version": "1.0.0",
        "source_artifacts": [
            {
                "name": "RBE-001_Review_Board_Engine_Reference_Architecture_v1.0.0_FINAL.pdf",
                "sha256": "0b919c70c7a9b6991b329546b02de7d6d2cd42266e674caa361c867abee18d31",
            },
            {
                "name": "RBE-001_Review_Board_Engine_Engineering_Specification_v1.0.0.docx",
                "sha256": "92e159f084ab91d458e57f98d405b7a6146dd6f98db04af76d159b8e09b45ca4",
            },
            {
                "name": "RBE-001_Architecture_Consistency_and_Principal_Review_Report_v1.0.0.pdf",
                "sha256": "df09ffa514ac2fad2f98791e979ba372115c7e4e1b664ac5dc1773ff1b5877d1",
            },
            {
                "name": "RBE-001_Architecture_Consistency_and_Principal_Review_Report_v1.0.0.docx",
                "sha256": "923b62bc16be91a216349acc776bad12e717dcf955741571a0bdc9bf0f989c17",
            },
        ],
    }
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def archive_bytes(paths: list[Path], manifest: bytes) -> bytes:
    buffer = io.BytesIO()
    entries = [(path.relative_to(PACKAGE_ROOT).as_posix(), path.read_bytes()) for path in paths]
    entries.append((MANIFEST_NAME, manifest))
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(2026, 7, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return buffer.getvalue()


def validate_source_documents() -> None:
    chapters = sorted(
        (PACKAGE_ROOT / "architecture" / "chapters").glob("*.md"),
        key=package_path_sort_key,
    )
    if len(chapters) != 23:
        raise PackageValidationError(f"Expected 23 architecture chapters, found {len(chapters)}")
    expected_prefixes = [f"{number:02d}-" for number in range(1, 24)]
    actual_prefixes = [path.name[:3] for path in chapters]
    if actual_prefixes != expected_prefixes:
        raise PackageValidationError("Architecture chapter numbering is incomplete or unordered")

    architecture = (
        PACKAGE_ROOT / "architecture" / "RBE-001_Reference_Architecture_v1.1.0.md"
    ).read_text(encoding="utf-8")
    engineering = (
        PACKAGE_ROOT / "engineering" / "RBE-001_Engineering_Specification_v1.1.0.md"
    ).read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_RELEASE_TEXT:
        if forbidden.casefold() in architecture.casefold():
            raise PackageValidationError(f"Unresolved release text found: {forbidden}")
    for state in LEGACY_ENGINEERING_STATES:
        if re.search(rf"\b{re.escape(state)}\b", engineering):
            raise PackageValidationError(f"Legacy engineering state remains authoritative: {state}")
    legacy_ids = sorted(set(re.findall(r"\bRBE-(?!ES-)[A-Z]+-\d{3}\b", engineering)))
    if legacy_ids:
        raise PackageValidationError(
            "Unnamespaced engineering requirement IDs remain: " + ", ".join(legacy_ids[:10])
        )
    if (
        "This outcome indicates that a legitimate substantive decision cannot be issued"
        in architecture
    ):
        raise PackageValidationError("Process status is still described as a substantive outcome")
    if "| published_by | ActorRef | Required |" in engineering:
        raise PackageValidationError(
            "BoardDecision requires publication authority before publication"
        )

    package_readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
    if "supersedes RBE-001 v1.0.0 for future implementation" in package_readme:
        raise PackageValidationError("Release candidate claims effective supersession")

    repository_readme = (REPO_ROOT / "docs" / "rbe-001" / "README.md").read_text(
        encoding="utf-8"
    )
    repository_instructions = (
        REPO_ROOT / "docs" / "rbe-001" / "CODEX_REVIEW_INSTRUCTIONS.md"
    ).read_text(encoding="utf-8")
    if "v1.1.0" not in repository_readme or "v1.1.0" not in repository_instructions:
        raise PackageValidationError("Repository RBE entrypoint does not identify v1.1.0")
    if "extract the archive" in repository_instructions.casefold():
        raise PackageValidationError("Repository instructions still direct reviewers to v1.0 ZIP")


def validate_registers() -> None:
    verdicts = json.loads(
        (PACKAGE_ROOT / "registers" / "verdict_taxonomy.json").read_text(encoding="utf-8")
    )
    if verdicts["substantive_outcomes"] != CANONICAL_OUTCOMES:
        raise PackageValidationError("Canonical outcome register does not match v1.1.0")
    if not verdicts["rules"].get("insufficient_evidence_required_for_active_profile"):
        raise PackageValidationError("ACTIVE profiles may suppress insufficient evidence")
    statuses = [item["id"] for item in verdicts["process_statuses"]]
    if statuses != CANONICAL_PROCESS_STATUSES:
        raise PackageValidationError("Canonical process-status register does not match v1.1.0")
    for item in verdicts["process_statuses"]:
        if item["id"] != "READY" and item["allows_outcome"]:
            raise PackageValidationError(f"Non-ready process status allows an outcome: {item['id']}")

    state_machine = json.loads(
        (PACKAGE_ROOT / "registers" / "state_machine.json").read_text(encoding="utf-8")
    )
    states = [item["id"] for item in state_machine["states"]]
    if len(states) != len(set(states)):
        raise PackageValidationError("State register contains duplicate states")
    known = set(states)
    outgoing: set[str] = set()
    transition_pairs: set[tuple[str, str]] = set()
    for source, target in state_machine["transitions"]:
        if source not in known or target not in known:
            raise PackageValidationError(f"Transition references unknown state: {source} -> {target}")
        if (source, target) in transition_pairs:
            raise PackageValidationError(f"Duplicate transition: {source} -> {target}")
        transition_pairs.add((source, target))
        outgoing.add(source)
    for item in state_machine["states"]:
        if item["terminal"] and item["id"] in outgoing:
            raise PackageValidationError(f"Terminal state has outgoing transition: {item['id']}")
        if not item["terminal"] and item["id"] not in outgoing:
            raise PackageValidationError(f"Non-terminal state is a dead end: {item['id']}")

    initial_state = state_machine.get("initial_state")
    if initial_state not in known:
        raise PackageValidationError("State register lacks a valid initial state")
    reachable = {initial_state}
    frontier = [initial_state]
    while frontier:
        source = frontier.pop()
        for transition_source, target in transition_pairs:
            if transition_source == source and target not in reachable:
                reachable.add(target)
                frontier.append(target)
    if reachable != known:
        raise PackageValidationError(
            "State register contains unreachable states: " + ", ".join(sorted(known - reachable))
        )
    if ("REMANDED", "ASSIGNMENT") not in transition_pairs:
        raise PackageValidationError("Canonical remand re-entry transition is missing")


def validate_archive(archive_content: bytes, manifest_content: bytes) -> None:
    manifest = json.loads(manifest_content)
    expected = {item["path"]: item for item in manifest["files"]}
    with zipfile.ZipFile(io.BytesIO(archive_content)) as archive:
        if archive.testzip() is not None:
            raise PackageValidationError("ZIP CRC validation failed")
        names = set(archive.namelist())
        if names != set(expected) | {MANIFEST_NAME}:
            raise PackageValidationError("ZIP entries do not match the manifest")
        for name, item in expected.items():
            content = archive.read(name)
            if sha256_bytes(content) != item["sha256"]:
                raise PackageValidationError(f"ZIP content hash mismatch: {name}")
        if archive.read(MANIFEST_NAME) != manifest_content:
            raise PackageValidationError("ZIP manifest differs from repository manifest")


def build() -> None:
    FULL_ARCHITECTURE.write_bytes(architecture_document_bytes())
    validate_source_documents()
    validate_registers()
    requirements = collect_requirements()
    REQUIREMENT_REGISTER.write_bytes(requirement_register_bytes(requirements))
    MIGRATION_REGISTER.write_bytes(migration_register_bytes(requirements))

    paths = inventory_paths()
    manifest = manifest_bytes(paths)
    (PACKAGE_ROOT / MANIFEST_NAME).write_bytes(manifest)
    archive = archive_bytes(paths, manifest)
    validate_archive(archive, manifest)
    (PACKAGE_ROOT / ARCHIVE_NAME).write_bytes(archive)
    checksum = f"{sha256_bytes(archive)}  {ARCHIVE_NAME}\n".encode("ascii")
    (PACKAGE_ROOT / CHECKSUM_NAME).write_bytes(checksum)


def check() -> None:
    if FULL_ARCHITECTURE.read_bytes() != architecture_document_bytes():
        raise PackageValidationError("Complete architecture is stale relative to chapter sources")
    validate_source_documents()
    validate_registers()
    requirements = collect_requirements()
    expected_requirement = requirement_register_bytes(requirements)
    expected_migration = migration_register_bytes(requirements)
    if REQUIREMENT_REGISTER.read_bytes() != expected_requirement:
        raise PackageValidationError("Requirement register is stale; run the package builder")
    if MIGRATION_REGISTER.read_bytes() != expected_migration:
        raise PackageValidationError("Requirement migration register is stale")

    paths = inventory_paths()
    expected_manifest = manifest_bytes(paths)
    actual_manifest = (PACKAGE_ROOT / MANIFEST_NAME).read_bytes()
    if actual_manifest != expected_manifest:
        raise PackageValidationError("Manifest is stale or inconsistent")
    expected_archive = archive_bytes(paths, expected_manifest)
    actual_archive = (PACKAGE_ROOT / ARCHIVE_NAME).read_bytes()
    if actual_archive != expected_archive:
        raise PackageValidationError("Archive is not the deterministic derivative of Markdown sources")
    expected_checksum = f"{sha256_bytes(actual_archive)}  {ARCHIVE_NAME}\n".encode("ascii")
    if (PACKAGE_ROOT / CHECKSUM_NAME).read_bytes() != expected_checksum:
        raise PackageValidationError("Archive checksum file is stale")
    validate_archive(actual_archive, actual_manifest)
