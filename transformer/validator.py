"""Pydantic validation for projected JSON output."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError as PydanticValidationError, create_model

from transformer.models.config import ProjectionConfig


class ValidationError(ValueError):
    """Raised when projected output does not match the requested schema."""


class DefaultOutputModel(BaseModel):
    """Minimum schema expected for full canonical projection."""

    model_config = ConfigDict(extra="allow")

    candidate_id: str
    emails: list[str]
    phones: list[str]
    links: dict[str, Any]
    skills: list[dict[str, Any]]
    provenance: list[dict[str, Any]]


class OutputValidator:
    """Validate projected output using Pydantic."""

    def validate(self, output: dict[str, Any], config: ProjectionConfig) -> None:
        try:
            if not config.fields:
                DefaultOutputModel.model_validate(output)
                return

            model_fields: dict[str, tuple[Any, Any]] = {}
            for field in config.fields:
                py_type = self._python_type(field.type)
                if field.path in output:
                    model_fields[field.path] = (py_type | None, ...)
                elif field.required:
                    model_fields[field.path] = (py_type | None, ...)
                else:
                    model_fields[field.path] = (py_type | None, None)

            ProjectionModel = create_model(
                "ProjectionModel",
                __config__=ConfigDict(extra="allow"),
                **model_fields,
            )
            ProjectionModel.model_validate(output)
        except PydanticValidationError as exc:
            raise ValidationError(str(exc)) from exc

    @staticmethod
    def _python_type(expected: str) -> Any:
        if expected == "string":
            return str
        if expected == "string[]":
            return list[str]
        if expected == "number":
            return float
        if expected == "boolean":
            return bool
        if expected == "object":
            return dict[str, Any]
        if expected == "object[]":
            return list[dict[str, Any]]
        raise ValidationError(f"Unsupported field type '{expected}'.")
