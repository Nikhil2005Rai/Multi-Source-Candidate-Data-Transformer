"""Runtime projection configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class OnMissing(str, Enum):
    """How projection handles a requested value that is absent."""

    NULL = "null"
    OMIT = "omit"
    ERROR = "error"


class NormalizeDirective(str, Enum):
    """Optional normalization applied after path extraction."""

    E164 = "E164"
    CANONICAL = "canonical"


SUPPORTED_FIELD_TYPES = {
    "string",
    "string[]",
    "number",
    "boolean",
    "object",
    "object[]",
}


@dataclass(frozen=True)
class FieldConfig:
    """One field in the projected output."""

    path: str
    from_path: str
    type: str = "string"
    required: bool = False
    normalize: NormalizeDirective | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "FieldConfig":
        path = data.get("path")
        if not path or not isinstance(path, str):
            raise ValueError("Each configured field requires a string 'path'.")

        field_type = data.get("type", "string")
        if field_type not in SUPPORTED_FIELD_TYPES:
            raise ValueError(f"Unsupported field type '{field_type}' for '{path}'.")

        normalize = data.get("normalize")
        return cls(
            path=path,
            from_path=data.get("from", path),
            type=field_type,
            required=bool(data.get("required", False)),
            normalize=NormalizeDirective(normalize) if normalize else None,
        )


@dataclass(frozen=True)
class ProjectionConfig:
    """Configuration used by the projector.

    Empty fields means emit the full canonical schema.
    """

    fields: list[FieldConfig] = field(default_factory=list)
    include_provenance: bool = True
    include_confidence: bool = True
    include_diagnostics: bool = True
    on_missing: OnMissing = OnMissing.NULL

    @classmethod
    def default(cls) -> "ProjectionConfig":
        return cls()

    @classmethod
    def from_file(cls, path: str | Path) -> "ProjectionConfig":
        with Path(path).open(encoding="utf-8") as f:
            data = json.load(f)

        on_missing_raw = data.get("on_missing", OnMissing.NULL.value)
        return cls(
            fields=[FieldConfig.from_dict(item) for item in data.get("fields", [])],
            include_provenance=bool(data.get("include_provenance", True)),
            include_confidence=bool(data.get("include_confidence", True)),
            include_diagnostics=bool(data.get("include_diagnostics", True)),
            on_missing=OnMissing(on_missing_raw),
        )
