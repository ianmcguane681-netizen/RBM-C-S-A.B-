from __future__ import annotations

import csv
import io
import json
import zipfile

from controlled_authority import rbe_package as package


def test_package_is_current_and_valid() -> None:
    package.check()


def test_manifest_uses_canonical_cross_platform_path_order() -> None:
    paths = [
        path.relative_to(package.PACKAGE_ROOT).as_posix()
        for path in package.inventory_paths()
    ]
    manifest = json.loads(
        (package.PACKAGE_ROOT / package.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert paths == sorted(paths, key=lambda value: (value.casefold(), value))
    assert [item["path"] for item in manifest["files"]] == paths


def test_outcome_and_process_status_are_separate() -> None:
    taxonomy = json.loads(
        (package.PACKAGE_ROOT / "registers" / "verdict_taxonomy.json").read_text(
            encoding="utf-8"
        )
    )
    outcomes = taxonomy["substantive_outcomes"]
    statuses = {item["id"]: item for item in taxonomy["process_statuses"]}

    assert outcomes == package.CANONICAL_OUTCOMES
    assert statuses["READY"]["allows_outcome"] is True
    assert all(
        statuses[status]["allows_outcome"] is False
        for status in ("PROCEDURALLY_INCOMPLETE", "BLOCKED", "VOID")
    )
    assert taxonomy["rules"]["insufficient_evidence_required_for_active_profile"] is True
    assert taxonomy["rules"]["defer_omission_maps_to_insufficient_evidence"] is True


def test_state_machine_uses_only_canonical_states() -> None:
    package.validate_source_documents()
    state_machine = json.loads(
        (package.PACKAGE_ROOT / "registers" / "state_machine.json").read_text(
            encoding="utf-8"
        )
    )
    states = {item["id"] for item in state_machine["states"]}
    transitions = {tuple(item) for item in state_machine["transitions"]}

    assert states.isdisjoint(package.LEGACY_ENGINEERING_STATES)
    assert {"DRAFT", "INDEPENDENT_REVIEW", "GOVERNANCE_VALIDATION", "PUBLISHED"} <= states
    assert state_machine["initial_state"] == "DRAFT"
    assert ("REMANDED", "ASSIGNMENT") in transitions


def test_state_machine_has_no_unreachable_or_nonterminal_dead_end_state() -> None:
    state_machine = json.loads(
        (package.PACKAGE_ROOT / "registers" / "state_machine.json").read_text(
            encoding="utf-8"
        )
    )
    states = {item["id"]: item for item in state_machine["states"]}
    transitions = {tuple(item) for item in state_machine["transitions"]}
    outgoing = {source for source, _ in transitions}

    assert all(
        item["terminal"] or state_id in outgoing for state_id, item in states.items()
    )

    reachable = {state_machine["initial_state"]}
    frontier = list(reachable)
    while frontier:
        source = frontier.pop()
        for transition_source, target in transitions:
            if transition_source == source and target not in reachable:
                reachable.add(target)
                frontier.append(target)
    assert reachable == set(states)


def test_requirement_namespaces_do_not_collide() -> None:
    requirements = package.collect_requirements()
    identifiers = [item["id"] for item in requirements]
    architecture = {item for item in identifiers if not item.startswith("RBE-ES-")}
    engineering = {item for item in identifiers if item.startswith("RBE-ES-")}

    assert len(identifiers) == len(set(identifiers))
    assert architecture
    assert engineering
    assert architecture.isdisjoint(engineering)


def test_requirement_register_preserves_wrapped_statements_and_line_ranges() -> None:
    requirements = {item["id"]: item for item in package.collect_requirements()}

    assert requirements["RBE-LIF-101"]["statement"].endswith(
        "it SHALL NOT edit the original record."
    )
    assert requirements["RBE-MAN-001"]["statement"] == (
        "The engine SHALL exist to execute an approved Review Board Methodology, not to create, "
        "amend or reinterpret that methodology during a live review."
    )
    assert all(item["line_start"] <= item["line_end"] for item in requirements.values())
    assert all(
        str(item["statement"]).endswith(package.REQUIREMENT_TERMINATORS)
        for item in requirements.values()
    )


def test_every_engineering_requirement_has_migration_lineage() -> None:
    requirements = package.collect_requirements()
    engineering = {item["id"] for item in requirements if item["id"].startswith("RBE-ES-")}
    migration = package.migration_register_bytes(requirements).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(migration)))

    engineering_rows = {
        row["new_id"]
        for row in rows
        if row["source_document"] == "RBE-001 Engineering Specification"
    }
    assert engineering_rows == engineering
    assert all(row["old_id"].startswith("RBE-") for row in rows)
    semantic_rows = [
        row
        for row in rows
        if row["disposition"].startswith("SEMANTIC_NORMALISATION")
    ]
    assert semantic_rows
    assert all(
        row["new_id"].split("-")[2]
        in package.SEMANTICALLY_NORMALIZED_ENGINEERING_DOMAINS
        for row in semantic_rows
    )


def test_architecture_id_collisions_have_explicit_migrations() -> None:
    requirements = package.collect_requirements()
    rows = list(
        csv.DictReader(io.StringIO(package.migration_register_bytes(requirements).decode("utf-8")))
    )
    architecture_rows = [
        row for row in rows if row["disposition"] == "ARCHITECTURE_COLLISION_RESOLVED"
    ]

    assert len(architecture_rows) == 5
    assert {row["new_id"] for row in architecture_rows} == {
        "RBE-IBR-001",
        "RBE-AI-130",
        "RBE-AI-131",
        "RBE-OUT-010",
        "RBE-OUT-011",
    }


def test_archive_contains_manifest_and_all_searchable_sources() -> None:
    archive_path = package.PACKAGE_ROOT / package.ARCHIVE_NAME
    manifest = json.loads(
        (package.PACKAGE_ROOT / package.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    expected = {item["path"] for item in manifest["files"]}

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == expected | {package.MANIFEST_NAME}
        assert len([name for name in archive.namelist() if "/chapters/" in name]) == 23

    assert manifest["release_status"] == "normalization-release-candidate"
    assert manifest["supersession_effective_on"] == "named-human-principal-architect-approval"


def test_release_does_not_claim_human_or_methodology_activation() -> None:
    readme = (package.PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
    authority = (
        package.PACKAGE_ROOT / "registers" / "AUTHORITY_AND_CONFORMANCE.md"
    ).read_text(encoding="utf-8")

    assert "Principal Architect approval: required" in readme
    assert "Effective supersession of v1.0.0: pending" in readme
    assert "Only an `ACTIVE` profile may govern a binding live decision" in authority
    assert authority.index("Reference Architecture") < authority.index("ACTIVE methodology")


def test_repository_entrypoint_rejects_the_invalid_historical_archive() -> None:
    readme = (package.REPO_ROOT / "docs" / "rbe-001" / "README.md").read_text(
        encoding="utf-8"
    )
    instructions = (
        package.REPO_ROOT / "docs" / "rbe-001" / "CODEX_REVIEW_INSTRUCTIONS.md"
    ).read_text(encoding="utf-8")

    assert "v1.1.0" in readme
    assert "MUST NOT be used" in readme
    assert "Do not extract or review from the root-level v1.0.0 ZIP" in instructions


def test_process_status_and_publication_fields_are_not_misrepresented() -> None:
    architecture = (
        package.PACKAGE_ROOT / "architecture" / "chapters" / "06-decision-framework.md"
    ).read_text(encoding="utf-8")
    engineering = (
        package.PACKAGE_ROOT
        / "engineering"
        / "RBE-001_Engineering_Specification_v1.1.0.md"
    ).read_text(encoding="utf-8")

    assert "This outcome indicates that a legitimate substantive decision" not in architecture
    assert (
        "`PROCEDURALLY_INCOMPLETE`, `BLOCKED`, and `VOID` are process statuses"
        in architecture
    )
    assert "| published_by | ActorRef | Required only when status is PUBLISHED" in engineering


def test_controlled_package_has_cross_platform_line_endings() -> None:
    attributes = (package.REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "docs/rbe-001/v1.1.0/** text eol=lf" in attributes
    assert "docs/rbe-001/v1.1.0/*.zip -text -eol" in attributes
