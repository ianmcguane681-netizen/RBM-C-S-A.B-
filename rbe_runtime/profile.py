"""Profile-driven role, quorum, and reviewer-spec policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError


_ROLE_LINE = re.compile(r"^\*\*Reviewer Role:\*\* .*\(([A-Z]{2,3})\)$", re.MULTILINE)


# Any actor carrying one of these prefixes is automation, however it is named.
# Treating them all as agents stops a seat dodging the agent rules by choosing a
# different prefix, or dodging the human rules by choosing "agent:".
AUTOMATION_PREFIXES = ("agent:", "ai:", "model:", "automation:")


def is_agent_actor(actor: str) -> bool:
    return actor.lower().startswith(AUTOMATION_PREFIXES)


@dataclass(frozen=True, slots=True)
class RoleSeat:
    role: str
    actor: str
    reviewer_spec_id: str
    sequence: int
    is_agent: bool = False


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    profile: dict[str, Any]
    role_to_spec: dict[str, str]

    @classmethod
    def from_authority(cls, authority: AuthorityBundle) -> "ProfilePolicy":
        role_to_spec: dict[str, str] = {}
        for spec_id, path in authority.reviewer_specs.items():
            match = _ROLE_LINE.search(path.read_text(encoding="utf-8"))
            if match is None:
                raise RBEError(
                    "RBE_REVIEWER_SPEC_INVALID",
                    f"Reviewer role is absent from {path.name}",
                    "RBE-ES-ORC-004",
                )
            role = match.group(1)
            if role in role_to_spec:
                raise RBEError(
                    "RBE_REVIEWER_SPEC_INVALID",
                    f"Multiple reviewer specifications claim role {role}",
                    "RBE-ES-ORC-004",
                )
            role_to_spec[role] = spec_id
        return cls(profile=authority.profile, role_to_spec=role_to_spec)

    def plan_roles(self, initiation: dict[str, Any]) -> tuple[RoleSeat, ...]:
        tier = initiation["tier"]
        quorum = self.profile["quorum"][f"tier_{tier}"]
        specialists = {
            role.upper(): actor
            for role, actor in initiation["specialists"].items()
            if actor is not None
        }
        allowed_specialists = set(quorum["specialist_pool"])
        unexpected = sorted(set(specialists) - allowed_specialists)
        if unexpected:
            raise RBEError(
                "RBE_ROLE_NOT_PERMITTED_FOR_TIER",
                f"Tier {tier} includes specialists outside its configured pool",
                "RBE-ES-ORC-004",
                {"roles": unexpected},
            )
        if len(specialists) < quorum["specialists_required"]:
            raise RBEError(
                "RBE_QUORUM_INSUFFICIENT",
                f"Tier {tier} requires {quorum['specialists_required']} specialists",
                "RBE-ES-ORC-002",
                {"assigned_specialists": sorted(specialists)},
            )

        role_actors = {
            "BC": initiation["board_chair"],
            "MA": initiation["methodology_auditor"],
            "SR": initiation["sceptical_reviewer"],
            **specialists,
        }
        required_roles = set(quorum["required_roles"])
        missing = sorted(role for role in required_roles if not role_actors.get(role))
        if missing:
            raise RBEError(
                "RBE_REQUIRED_ROLE_MISSING",
                "A methodology-required board role is unassigned",
                "RBE-ES-ORC-002",
                {"roles": missing},
            )
        actors = list(role_actors.values())
        agent_roles = {
            role for role, actor in role_actors.items() if is_agent_actor(actor)
        }
        policy = self.profile.get("agent_seat_policy")
        if agent_roles:
            if not policy or policy.get("agent_seats_permitted") is not True:
                raise RBEError(
                    "RBE_NON_HUMAN_BOARD_ROLE",
                    "AI or automation actors cannot hold accountable board roles",
                    "RBE-ES-DES-002",
                    {"roles": sorted(agent_roles)},
                )
            permitted = set(policy.get("permitted_agent_roles", []))
            forbidden = sorted(agent_roles - permitted)
            if forbidden:
                raise RBEError(
                    "RBE_NON_HUMAN_BOARD_ROLE",
                    "This board role is accountable and must be held by a human",
                    "RBE-ES-DES-002",
                    {"roles": forbidden},
                )
        # Distinct actors regardless of kind. One agent holding two seats would
        # produce two identical reviews and destroy the independence the board exists for.
        if self.profile["role_policy"]["distinct_human_per_board_role"] and len(
            actors
        ) != len(set(actors)):
            raise RBEError(
                "RBE_ROLE_CONFLICT",
                "Board roles must be held by distinct actors",
                "RBE-ES-ORC-003",
            )

        review_roles = ["MA", *sorted(specialists), "SR"]
        return tuple(
            RoleSeat(
                role=role,
                actor=role_actors[role],
                reviewer_spec_id=self.role_to_spec[role],
                sequence=index,
                is_agent=is_agent_actor(role_actors[role]),
            )
            for index, role in enumerate(review_roles, start=1)
        )

    def require_role_spec(self, role: str, spec_id: str) -> None:
        expected = self.role_to_spec.get(role)
        if expected != spec_id:
            raise RBEError(
                "RBE_REVIEWER_SPEC_MISMATCH",
                f"Role {role} must use {expected or 'a known reviewer specification'}",
                "RBE-ES-ORC-004",
                {"role": role, "expected": expected, "received": spec_id},
            )
