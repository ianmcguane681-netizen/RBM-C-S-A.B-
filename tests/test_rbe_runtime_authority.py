from __future__ import annotations

import ast
from pathlib import Path

import pytest

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError
from rbe_runtime.models import ExecutionMode
from rbe_runtime.state_machine import CanonicalStateMachine


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def authority() -> AuthorityBundle:
    return AuthorityBundle.load()


def test_authoritative_packages_load_without_reinterpretation(
    authority: AuthorityBundle,
) -> None:
    assert authority.state_machine["architecture_release"] == "1.1.0"
    assert authority.profile["profile_id"] == "RBM-001"
    assert authority.profile["version"] == "2.2.0"
    assert authority.profile["status"] == "RELEASE_CANDIDATE"
    assert authority.profile["binding"] is False
    assert len(authority.reviewer_specs) == 8
    assert len(authority.schemas) == 7


def test_runtime_does_not_import_engineering_scripts() -> None:
    violations: list[str] = []
    for path in sorted((REPO_ROOT / "rbe_runtime").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name == "scripts" or name.startswith("scripts.") for name in names):
                violations.append(f"{path.name}:{node.lineno}")
    assert violations == []


def test_release_candidate_is_advisory_only(authority: AuthorityBundle) -> None:
    authority.require_execution_mode(ExecutionMode.ADVISORY_DRY_RUN)
    with pytest.raises(RBEError, match="ACTIVE") as error:
        authority.require_execution_mode(ExecutionMode.BINDING_LIVE)
    assert error.value.code == "RBE_PROFILE_NOT_ACTIVE"


def test_every_registered_transition_is_permitted(authority: AuthorityBundle) -> None:
    machine = CanonicalStateMachine.from_register(authority.state_machine)
    assert machine.transitions == {
        tuple(item) for item in authority.state_machine["transitions"]
    }
    for source, target in machine.transitions:
        machine.require_transition(source, target)


def test_every_unregistered_state_pair_is_prohibited(
    authority: AuthorityBundle,
) -> None:
    machine = CanonicalStateMachine.from_register(authority.state_machine)
    for source in machine.states:
        for target in machine.states:
            if (source, target) in machine.transitions:
                continue
            with pytest.raises(RBEError) as error:
                machine.require_transition(source, target)
            expected = (
                "RBE_TERMINAL_STATE"
                if source in machine.terminal_states
                else "RBE_INVALID_TRANSITION"
            )
            assert error.value.code == expected


def test_unknown_state_is_rejected(authority: AuthorityBundle) -> None:
    machine = CanonicalStateMachine.from_register(authority.state_machine)
    with pytest.raises(RBEError) as error:
        machine.require_transition("DRAFT", "DECISION_COMPLETE")
    assert error.value.code == "RBE_UNKNOWN_STATE"
