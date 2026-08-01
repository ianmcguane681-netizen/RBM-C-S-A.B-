"""Build and validate a controlled methodology profile package.

Originally this validated exactly one package, RBM-001, with its identity and location
as module constants. Every function now takes a `PackageSpec` describing which package
it is working on, defaulting to RBM-001 so existing callers are unchanged.

What did *not* move into the spec matters as much as what did. The canonical RBE
lifecycle states, the four permitted outcomes, the four process statuses and the
decision matrix are architecture: they are RBE-001's, and a methodology profile maps
onto them rather than replacing them. A profile that could redefine its own outcome
vocabulary could also decide what "FAIL" means.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from controlled_authority.profiles import PackageSpec
from controlled_authority.profiles import get as get_profile_spec


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_TEXT_SUFFIXES = {".json", ".md"}

# Retained as module-level names because scripts and tests refer to them, and because
# RBM-001 remains the default package. They are now derived from the registry rather
# than being the only statement of it.
_DEFAULT_SPEC = get_profile_spec()
PACKAGE_ROOT = _DEFAULT_SPEC.package_root
PROFILE_PATH = _DEFAULT_SPEC.profile_path
MANIFEST_PATH = _DEFAULT_SPEC.manifest_path
SCHEMA_ROOT = _DEFAULT_SPEC.schema_root
PROFILE_ID = _DEFAULT_SPEC.profile_id
PROFILE_VERSION = _DEFAULT_SPEC.profile_version

PROCESS_STATUSES = {"READY", "PROCEDURALLY_INCOMPLETE", "BLOCKED", "VOID"}
OUTCOMES = {"PASS", "PASS_WITH_FINDINGS", "FAIL", "INSUFFICIENT_EVIDENCE"}
CANONICAL_RBE_STATES = {
    "DRAFT",
    "SUBMITTED",
    "INTAKE_VALIDATION",
    "RETURNED",
    "ACCEPTED",
    "EVIDENCE_LOCKED",
    "ASSIGNMENT",
    "INDEPENDENT_REVIEW",
    "CHALLENGE",
    "CLARIFICATION",
    "CONSOLIDATION",
    "GOVERNANCE_VALIDATION",
    "BLOCKED",
    "DECIDED",
    "PUBLISHED",
    "APPEALED",
    "APPEAL_REVIEW",
    "UPHELD",
    "SUPERSEDED",
    "REMANDED",
    "FINAL",
    "ARCHIVED",
    "VOID",
    "WITHDRAWN",
}
SCHEMA_FILES = set(_DEFAULT_SPEC.schema_files)


class PackageValidationError(ValueError):
    """Raised when a controlled package is stale or internally inconsistent."""


def package_path_sort_key(path: Path, spec: PackageSpec | None = None) -> tuple[str, str]:
    """Match the controlled package's canonical case-insensitive path order."""

    relative = path.relative_to((spec or _DEFAULT_SPEC).package_root).as_posix()
    return relative.casefold(), relative


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageValidationError(f"Invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PackageValidationError(f"Expected JSON object: {path}")
    return value


def calculate_profile_checksum(profile: dict[str, Any]) -> str:
    payload = copy.deepcopy(profile)
    payload["checksum"] = None
    return f"sha256:{sha256_bytes(canonical_json(payload))}"


def controlled_files(spec: PackageSpec | None = None) -> list[Path]:
    spec = spec or _DEFAULT_SPEC
    return sorted(
        (
            path
            for path in spec.package_root.rglob("*")
            if path.is_file() and path != spec.manifest_path
        ),
        key=lambda path: package_path_sort_key(path, spec),
    )


def build_manifest(spec: PackageSpec | None = None) -> dict[str, Any]:
    spec = spec or _DEFAULT_SPEC
    files = [
        {
            "path": path.relative_to(spec.package_root).as_posix(),
            "sha256": sha256_bytes(path.read_bytes()),
            "size": path.stat().st_size,
        }
        for path in controlled_files(spec)
    ]
    return {
        "schema_version": "1.0.0",
        "package_id": spec.profile_id,
        "package_version": spec.profile_version,
        "files": files,
        "root_sha256": f"sha256:{sha256_bytes(canonical_json(files))}",
    }


def normalize_controlled_text_files(spec: PackageSpec | None = None) -> None:
    """Write controlled text with canonical LF endings before hashing it."""

    for path in controlled_files(spec):
        if path.suffix.lower() not in CONTROLLED_TEXT_SUFFIXES:
            continue
        raw = path.read_bytes()
        normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if normalized != raw:
            path.write_bytes(normalized)


def _validate_controlled_line_endings(spec: PackageSpec | None = None) -> None:
    spec = spec or _DEFAULT_SPEC
    invalid = []
    for path in [*controlled_files(spec), spec.manifest_path]:
        if path.suffix.lower() in CONTROLLED_TEXT_SUFFIXES and b"\r" in path.read_bytes():
            invalid.append(path.relative_to(spec.package_root).as_posix())
    if invalid:
        raise PackageValidationError(
            f"Controlled text must use canonical LF endings: {sorted(invalid)}"
        )


def write_control_files(spec: PackageSpec | None = None) -> None:
    spec = spec or _DEFAULT_SPEC
    normalize_controlled_text_files(spec)
    profile = load_json(spec.profile_path)
    profile["checksum"] = calculate_profile_checksum(profile)
    spec.profile_path.write_text(
        json.dumps(profile, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = build_manifest(spec)
    spec.manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def evaluate_outcome(
    *,
    process_status: str,
    unresolved_sev1: int,
    unresolved_sev2: int,
    accepted_sev2_remediation: int,
    substantive_evidence_sufficient: bool,
) -> str | None:
    if process_status not in PROCESS_STATUSES:
        raise ValueError(f"Unknown process status: {process_status}")
    if min(unresolved_sev1, unresolved_sev2, accepted_sev2_remediation) < 0:
        raise ValueError("Finding counts cannot be negative")
    if accepted_sev2_remediation > unresolved_sev2:
        raise ValueError("Accepted SEV-2 remediation exceeds unresolved SEV-2 count")
    if process_status != "READY":
        return None
    if unresolved_sev1 >= 1:
        return "FAIL"
    if unresolved_sev2 >= 2:
        return "FAIL"
    if unresolved_sev2 == 1 and accepted_sev2_remediation == 0:
        return "FAIL"
    if not substantive_evidence_sufficient:
        return "INSUFFICIENT_EVIDENCE"
    if unresolved_sev2 == 1:
        return "PASS_WITH_FINDINGS"
    return "PASS"


def is_merge_permitted(
    *, profile_status: str, binding: bool, process_status: str, outcome: str | None
) -> bool:
    return (
        profile_status == "ACTIVE"
        and binding
        and process_status == "READY"
        and outcome in {"PASS", "PASS_WITH_FINDINGS"}
    )


def _require_fields(record: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(field for field in fields if field not in record)
    if missing:
        raise PackageValidationError(f"{label} missing required fields: {missing}")


def validate_decision_bundle(
    initiation: dict[str, Any],
    decision: dict[str, Any],
    indicator: dict[str, Any],
    *,
    profile: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
    spec: PackageSpec | None = None,
) -> None:
    """Validate decision invariants that cannot be expressed safely in JSON Schema.

    `spec` names which registry entry the profile is being held to. It defaults to
    RBM-001, which was the only profile when this was written and silently became wrong
    when there were three: publishing an RBM-003 decision passed its own profile in and
    had it checked against RBM-001's registry entry, failing with "Profile ID mismatch"
    on a package that was entirely valid.

    The default stays rather than becoming required, because the check must never read the
    identity from the profile it is checking -- a package that decided its own identity
    would always agree with itself. The caller knows which profile it loaded and says so.
    """

    active_profile = copy.deepcopy(profile) if profile is not None else load_json(PROFILE_PATH)
    active_manifest = manifest if manifest is not None else load_json(MANIFEST_PATH)
    _validate_profile(active_profile, spec)

    _require_fields(
        initiation,
        {
            "review_id",
            "artefact_sha",
            "tier",
            "methodology_profile_id",
            "methodology_version",
            "methodology_status",
            "methodology_checksum",
            "manifest_root_sha256",
            "human_approval_record",
            "binding",
            "board_chair",
            "methodology_auditor",
            "sceptical_reviewer",
            "specialists",
            "input_process_status",
        },
        "TPL-RIR",
    )
    _require_fields(
        decision,
        {
            "review_id",
            "artefact_sha",
            "tier",
            "methodology_profile_id",
            "methodology_version",
            "methodology_status",
            "methodology_checksum",
            "binding",
            "process_status",
            "outcome",
            "finding_snapshot",
            "substantive_evidence_sufficient",
            "merge_permitted",
            "board_chair",
            "board_chair_signature_ref",
            "governance_validator",
            "governance_validation_ref",
        },
        "TPL-BDR",
    )
    _require_fields(
        indicator,
        {
            "review_id",
            "artefact_sha",
            "review_risk_tier",
            "methodology_profile_id",
            "methodology_version",
            "methodology_status",
            "methodology_checksum",
            "binding",
            "process_status",
            "outcome",
            "merge_permitted",
            "board_chair",
            "governance_validator",
            "publication_authority",
            "unresolved_sev1_count",
            "unresolved_sev2_count",
        },
        "TPL-MRI",
    )

    expected_profile_values = {
        "methodology_profile_id": active_profile["profile_id"],
        "methodology_version": active_profile["version"],
        "methodology_status": active_profile["status"],
        "methodology_checksum": active_profile["checksum"],
        "binding": active_profile["binding"],
    }
    for label, record in (
        ("TPL-RIR", initiation),
        ("TPL-BDR", decision),
        ("TPL-MRI", indicator),
    ):
        for field, expected in expected_profile_values.items():
            if record[field] != expected:
                raise PackageValidationError(f"{label} {field} does not match profile")

    if initiation["manifest_root_sha256"] != active_manifest.get("root_sha256"):
        raise PackageValidationError("TPL-RIR manifest root does not match package manifest")
    if initiation["human_approval_record"] != active_profile["human_approval_record"]:
        raise PackageValidationError("TPL-RIR human approval record does not match profile")

    for field in ("review_id", "artefact_sha"):
        values = {initiation[field], decision[field], indicator[field]}
        if len(values) != 1:
            raise PackageValidationError(f"Cross-record {field} mismatch")
    if not (
        initiation["tier"] == decision["tier"] == indicator["review_risk_tier"]
    ):
        raise PackageValidationError("Cross-record review tier mismatch")

    specialists = initiation["specialists"]
    if not isinstance(specialists, dict):
        raise PackageValidationError("TPL-RIR specialists must be an object")

    # Read from the profile, never hardcoded. This was {"saa","bca","dea","qra","spa",
    # "poa"} -- RBM-001's roles, correct when RBM-001 was the only profile and silently
    # wrong the moment there were three. An RBM-003 initiation naming its own six
    # specialists failed as "incomplete" against a pool it was never meant to match.
    specialist_pool = {
        role.lower()
        for tier in active_profile.get("quorum", {}).values()
        for role in tier.get("specialist_pool", ())
    }
    if not specialist_pool:
        raise PackageValidationError("Profile declares no specialist pool")
    if set(specialists) != specialist_pool:
        raise PackageValidationError(
            f"TPL-RIR specialist role set does not match the profile pool: "
            f"expected {sorted(specialist_pool)}, got {sorted(specialists)}"
        )
    assigned_specialists = {
        role: reviewer for role, reviewer in specialists.items() if reviewer
    }
    quorum = active_profile["quorum"][f"tier_{initiation['tier']}"]
    required_pool = set(quorum["specialist_pool"])
    assigned_in_pool = {
        role.upper()
        for role in assigned_specialists
        if role.upper() in required_pool
    }
    if len(assigned_in_pool) < quorum["specialists_required"]:
        raise PackageValidationError("Specialist quorum is not satisfied")

    role_holders = [
        initiation["board_chair"],
        initiation["methodology_auditor"],
        initiation["sceptical_reviewer"],
        *assigned_specialists.values(),
    ]
    if len(role_holders) != len(set(role_holders)):
        raise PackageValidationError("Board roles are not held by distinct humans")
    if decision["board_chair"] != initiation["board_chair"]:
        raise PackageValidationError("Board Chair identity mismatch")
    if decision.get("single_authority"):
        # A single-authority decision has no governance validator by construction.
        # It must also be non-binding and never merge-permitted; the profile
        # forbids the mode outright once ACTIVE.
        if decision.get("governance_validator") or indicator.get("governance_validator"):
            raise PackageValidationError(
                "Single-authority decision must not name a governance validator"
            )
        if decision.get("merge_permitted") or indicator.get("merge_permitted"):
            raise PackageValidationError("Single-authority decision cannot permit merge")
        if active_profile.get("status") == "ACTIVE" or active_profile.get("binding"):
            raise PackageValidationError(
                "Single-authority decision is not permitted under a binding methodology"
            )
        if decision["board_chair"] != initiation["board_chair"]:
            raise PackageValidationError(
                "Single-authority decision must be signed by the initiated Board Chair"
            )
        return
    if decision["governance_validator"] != initiation["methodology_auditor"]:
        raise PackageValidationError("Governance validator must be the assigned MA")
    if indicator["board_chair"] != decision["board_chair"]:
        raise PackageValidationError("Published Board Chair identity mismatch")
    if indicator["governance_validator"] != decision["governance_validator"]:
        raise PackageValidationError("Published governance validator identity mismatch")
    if indicator["publication_authority"] in {
        decision["board_chair"],
        decision["governance_validator"],
    }:
        raise PackageValidationError(
            "Publication authority must differ from Board Chair and governance validator"
        )

    snapshot = decision["finding_snapshot"]
    _require_fields(
        snapshot,
        {"unresolved_sev1", "unresolved_sev2", "accepted_sev2_remediation"},
        "TPL-BDR finding snapshot",
    )
    expected_outcome = evaluate_outcome(
        process_status=decision["process_status"],
        unresolved_sev1=snapshot["unresolved_sev1"],
        unresolved_sev2=snapshot["unresolved_sev2"],
        accepted_sev2_remediation=snapshot["accepted_sev2_remediation"],
        substantive_evidence_sufficient=decision["substantive_evidence_sufficient"],
    )
    if decision["outcome"] != expected_outcome:
        raise PackageValidationError("Board outcome does not match deterministic precedence")
    for field in ("process_status", "outcome", "merge_permitted"):
        if indicator[field] != decision[field]:
            raise PackageValidationError(f"Published {field} does not match decision")
    if indicator["unresolved_sev1_count"] != snapshot["unresolved_sev1"]:
        raise PackageValidationError("Published SEV-1 count does not match decision")
    if indicator["unresolved_sev2_count"] != snapshot["unresolved_sev2"]:
        raise PackageValidationError("Published SEV-2 count does not match decision")
    if decision["merge_permitted"] and not is_merge_permitted(
        profile_status=active_profile["status"],
        binding=active_profile["binding"],
        process_status=decision["process_status"],
        outcome=decision["outcome"],
    ):
        raise PackageValidationError("Decision claims merge permission outside the guard")


AGENT_PROHIBITED_ROLES = {"BC"}
AGENT_INDEPENDENCE_CONTROLS = {
    "distinct_instruction_version_per_seat",
    "sceptical_seat_is_blind_to_proposed_outcome",
    "record_model_and_instruction_version_per_seat",
    "shared_model_across_seats_must_be_recorded",
}


def _validate_agent_seat_policy(profile: dict[str, Any]) -> None:
    """Agent seats may not erode accountability or reviewer independence.

    A profile that permits agent-held seats must keep the Board Chair human,
    keep ratification and publication human, require a named human verifier,
    mark such reviews advisory, and carry every independence control. Any of
    those missing would let a board of correlated agents produce consensus that
    looks like assurance.
    """

    policy = profile.get("agent_seat_policy")
    if policy is None:
        return
    if policy.get("agent_seats_permitted") is not True:
        raise PackageValidationError("Agent seat policy present but not enabled")
    permitted = set(policy.get("permitted_agent_roles", []))
    prohibited = set(policy.get("prohibited_agent_roles", []))
    if not permitted:
        raise PackageValidationError("Agent seat policy permits no roles")
    if not AGENT_PROHIBITED_ROLES.issubset(prohibited):
        raise PackageValidationError(
            "The accountable Board Chair seat must be prohibited to agents"
        )
    if permitted & AGENT_PROHIBITED_ROLES:
        raise PackageValidationError("An accountable role is listed as agent-permitted")
    if permitted & prohibited:
        raise PackageValidationError("A role is both permitted and prohibited to agents")
    if not policy.get("agent_actor_prefixes"):
        raise PackageValidationError("Agent seat policy defines no actor prefix")
    for control in (
        "named_human_verifier_required",
        "ratification_authority_must_be_human",
        "publication_authority_must_be_human",
        "agent_seat_review_is_advisory_only",
    ):
        if policy.get(control) is not True:
            raise PackageValidationError(f"Agent seat control not enforced: {control}")
    independence = policy.get("independence_requirements", {})
    missing = sorted(
        control
        for control in AGENT_INDEPENDENCE_CONTROLS
        if independence.get(control) is not True
    )
    if missing:
        raise PackageValidationError(
            f"Agent seat independence controls incomplete: {missing}"
        )


def _validate_profile(profile: dict[str, Any], spec: PackageSpec | None = None) -> None:
    spec = spec or _DEFAULT_SPEC
    # Checked against the registry, never against the profile's own claim: a package
    # that decided its own identity would always agree with itself.
    if profile.get("profile_id") != spec.profile_id:
        raise PackageValidationError("Profile ID mismatch")
    if profile.get("version") != spec.profile_version:
        raise PackageValidationError("Profile version mismatch")
    if profile.get("checksum") != calculate_profile_checksum(profile):
        raise PackageValidationError("Profile checksum mismatch")
    if set(profile.get("permitted_outcomes", [])) != OUTCOMES:
        raise PackageValidationError("Canonical outcome subset mismatch")
    if set(profile.get("process_statuses", [])) != PROCESS_STATUSES:
        raise PackageValidationError("Canonical process status set mismatch")
    if profile.get("omitted_outcome_mapping", {}).get(
        "DEFER_FOR_FURTHER_RESEARCH"
    ) != "INSUFFICIENT_EVIDENCE":
        raise PackageValidationError("Missing bounded-research outcome mapping")
    status = profile.get("status")
    if status not in {"RELEASE_CANDIDATE", "ACTIVE", "RETIRED"}:
        raise PackageValidationError("Unknown profile status")
    if status == "RELEASE_CANDIDATE":
        if profile.get("binding") is not False:
            raise PackageValidationError("Release candidate cannot be binding")
        if profile.get("human_approval_record") is not None:
            raise PackageValidationError(
                "Release candidate must not claim an operative human approval record"
            )
    elif status == "ACTIVE":
        if profile.get("binding") is not True:
            raise PackageValidationError("Active profile must be binding")
        if not profile.get("human_approval_record"):
            raise PackageValidationError("Active profile requires a human approval record")
    elif profile.get("binding") is not False:
        raise PackageValidationError("Retired profile cannot be binding")
    role_policy = profile.get("role_policy", {})
    required_role_controls = {
        "distinct_human_per_board_role",
        "board_chair_and_governance_validator_must_differ",
        "decision_assembler_and_publication_control_must_differ",
        "governance_validator_and_publication_control_must_differ",
    }
    if not all(role_policy.get(key) is True for key in required_role_controls):
        raise PackageValidationError("Separation-of-duties policy is incomplete")
    _validate_agent_seat_policy(profile)
    priorities = [rule.get("priority") for rule in profile.get("decision_precedence", [])]
    if priorities != [1, 2, 3, 4, 5, 6]:
        raise PackageValidationError("Decision precedence is incomplete or unordered")
    lifecycle = profile.get("canonical_lifecycle_mapping", {})
    mapped_states = [state for states in lifecycle.values() for state in states]
    if len(mapped_states) != len(set(mapped_states)):
        raise PackageValidationError("Canonical lifecycle mapping contains duplicate states")
    if set(mapped_states) != CANONICAL_RBE_STATES:
        raise PackageValidationError("Canonical lifecycle mapping is incomplete")


def _validate_schemas(spec: PackageSpec | None = None) -> None:
    spec = spec or _DEFAULT_SPEC
    expected = set(spec.schema_files)
    actual = {path.name for path in spec.schema_root.glob("*.schema.json")}
    if actual != expected:
        raise PackageValidationError(
            f"Schema set mismatch: expected {sorted(expected)}, got {sorted(actual)}"
        )
    for name in sorted(expected):
        schema = load_json(spec.schema_root / name)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise PackageValidationError(f"Wrong JSON Schema draft: {name}")
        if not str(schema.get("$id", "")).endswith(f"/{spec.profile_version}"):
            raise PackageValidationError(f"Wrong schema version: {name}")
        if schema.get("type") != "object":
            raise PackageValidationError(f"Schema root must be an object: {name}")
        if name in {"tpl-bdr.schema.json", "tpl-mri.schema.json"}:
            merge_guard = any(
                rule.get("if", {}).get("properties", {}).get("merge_permitted")
                == {"const": True}
                and rule.get("then", {}).get("properties", {}).get(
                    "methodology_status"
                )
                == {"const": "ACTIVE"}
                and rule.get("then", {}).get("properties", {}).get("binding")
                == {"const": True}
                and rule.get("then", {}).get("properties", {}).get("process_status")
                == {"const": "READY"}
                for rule in schema.get("allOf", [])
            )
            if not merge_guard:
                raise PackageValidationError(f"Merge guard missing from schema: {name}")


def _validate_documents(spec: PackageSpec | None = None) -> None:
    spec = spec or _DEFAULT_SPEC
    methodology = (spec.package_root / spec.methodology_document).read_text(
        encoding="utf-8"
    )
    required_methodology_terms = {
        f"**Version:** {spec.profile_version}",
        *spec.methodology_terms,
    }
    missing = sorted(term for term in required_methodology_terms if term not in methodology)
    if missing:
        raise PackageValidationError(f"Methodology terms missing: {missing}")

    reviewer_specs = sorted(
        spec.spec_root.glob("RBS-*.md"),
        key=lambda path: package_path_sort_key(path, spec),
    )
    if len(reviewer_specs) != spec.reviewer_spec_count:
        raise PackageValidationError(
            f"Expected exactly {spec.reviewer_spec_count} reviewer specifications, "
            f"found {len(reviewer_specs)}"
        )
    for reviewer_spec in reviewer_specs:
        text = reviewer_spec.read_text(encoding="utf-8")
        # These five controls are not RBM-001's; they are what makes any reviewer
        # specification safe to act on. A profile cannot opt out of them.
        required = {
            f"**Version:** {spec.profile_version}",
            f"**Governing Methodology:** {spec.profile_id} v{spec.profile_version}",
            "## 10. Board Decision Contribution",
            "non-authoritative AI assistant",
            "unsigned draft",
        }
        absent = sorted(term for term in required if term not in text)
        if absent:
            raise PackageValidationError(f"{reviewer_spec.name} missing controls: {absent}")


def _validate_decision_coverage() -> None:
    observed: set[str | None] = set()
    for process_status in PROCESS_STATUSES:
        for sev1 in range(3):
            for sev2 in range(4):
                for remediation in range(sev2 + 1):
                    for sufficient in (False, True):
                        outcome = evaluate_outcome(
                            process_status=process_status,
                            unresolved_sev1=sev1,
                            unresolved_sev2=sev2,
                            accepted_sev2_remediation=remediation,
                            substantive_evidence_sufficient=sufficient,
                        )
                        if process_status != "READY" and outcome is not None:
                            raise PackageValidationError(
                                "Non-ready process produced a substantive outcome"
                            )
                        if process_status == "READY" and outcome not in OUTCOMES:
                            raise PackageValidationError(
                                "Ready process did not produce one permitted outcome"
                            )
                        observed.add(outcome)
    if observed != OUTCOMES | {None}:
        raise PackageValidationError("Decision matrix does not reach every permitted result")


def validate_package(spec: PackageSpec | None = None) -> None:
    spec = spec or _DEFAULT_SPEC
    _validate_controlled_line_endings(spec)
    profile = load_json(spec.profile_path)
    _validate_profile(profile, spec)
    _validate_schemas(spec)
    _validate_documents(spec)
    # Not parameterised, deliberately. The decision matrix is RBE architecture, so
    # every profile is checked against the same one -- a profile that could supply its
    # own would be marking its own homework.
    _validate_decision_coverage()
    expected_manifest = build_manifest(spec)
    actual_manifest = load_json(spec.manifest_path)
    if actual_manifest != expected_manifest:
        raise PackageValidationError("Package manifest is stale or invalid")
