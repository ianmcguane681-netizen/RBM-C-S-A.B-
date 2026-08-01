"""Closed-schema validation for controlled RBM-001 records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError


@dataclass(frozen=True, slots=True)
class SchemaRegistry:
    """Validate records against schemas from the loaded authority bundle."""

    validators: dict[str, Draft202012Validator]

    @classmethod
    def from_authority(cls, authority: AuthorityBundle) -> "SchemaRegistry":
        validators: dict[str, Draft202012Validator] = {}
        for name, path in authority.schemas.items():
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            validators[name] = Draft202012Validator(
                schema,
                format_checker=FormatChecker(),
            )
        return cls(validators=validators)

    def validate(self, schema_name: str, record: dict[str, Any]) -> None:
        validator = self.validators.get(schema_name)
        if validator is None:
            raise RBEError(
                "RBE_UNKNOWN_SCHEMA",
                f"Unknown controlled schema: {schema_name}",
                "RBE-ES-SCH-002",
            )
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
        if not errors:
            return
        error = errors[0]
        field = ".".join(str(part) for part in error.absolute_path) or "$"
        raise RBEError(
            "RBE_SCHEMA_INVALID",
            f"{schema_name} rejected field {field}: {error.message}",
            "RBE-ES-SCH-002",
            {
                "schema": schema_name,
                "field": field,
                "validation_error_count": len(errors),
            },
        )
