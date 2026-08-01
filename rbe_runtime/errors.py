"""Stable runtime error contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(eq=False)
class RBEError(RuntimeError):
    code: str
    message: str
    requirement: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "requirement": self.requirement,
                "details": self.details,
            }
        }

