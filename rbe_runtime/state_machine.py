"""Canonical state-machine loader and transition guard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rbe_runtime.errors import RBEError


@dataclass(frozen=True, slots=True)
class CanonicalStateMachine:
    initial_state: str
    states: frozenset[str]
    terminal_states: frozenset[str]
    transitions: frozenset[tuple[str, str]]

    @classmethod
    def from_register(cls, register: dict[str, Any]) -> "CanonicalStateMachine":
        states = frozenset(item["id"] for item in register["states"])
        terminal = frozenset(
            item["id"] for item in register["states"] if item["terminal"]
        )
        transitions = frozenset(tuple(item) for item in register["transitions"])
        machine = cls(
            initial_state=register["initial_state"],
            states=states,
            terminal_states=terminal,
            transitions=transitions,
        )
        machine.validate_register()
        return machine

    def validate_register(self) -> None:
        if self.initial_state not in self.states:
            raise RBEError(
                "RBE_STATE_REGISTER_INVALID",
                "Initial state is absent from the canonical register",
                "RBE-ES-LIF-001",
            )
        unknown = {
            state
            for transition in self.transitions
            for state in transition
            if state not in self.states
        }
        if unknown:
            raise RBEError(
                "RBE_STATE_REGISTER_INVALID",
                "A transition references an unknown canonical state",
                "RBE-ES-LIF-001",
                {"unknown_states": sorted(unknown)},
            )
        outgoing = {source for source, _ in self.transitions}
        nonterminal_dead_ends = (self.states - self.terminal_states) - outgoing
        if nonterminal_dead_ends:
            raise RBEError(
                "RBE_STATE_REGISTER_INVALID",
                "A non-terminal canonical state has no outgoing transition",
                "RBE-ES-LIF-001",
                {"states": sorted(nonterminal_dead_ends)},
            )

    def can_transition(self, source: str, target: str) -> bool:
        return (source, target) in self.transitions

    def require_transition(self, source: str, target: str) -> None:
        if source not in self.states or target not in self.states:
            raise RBEError(
                "RBE_UNKNOWN_STATE",
                "Transition references a state outside the canonical register",
                "RBE-ES-LIF-001",
                {"source": source, "target": target},
            )
        if source in self.terminal_states:
            raise RBEError(
                "RBE_TERMINAL_STATE",
                f"{source} is terminal under ordinary commands",
                "RBE-ES-LIF-006",
                {"source": source, "target": target},
            )
        if not self.can_transition(source, target):
            raise RBEError(
                "RBE_INVALID_TRANSITION",
                f"{target} is not reachable directly from {source}",
                "RBE-ES-LIF-002",
                {"source": source, "target": target},
            )

