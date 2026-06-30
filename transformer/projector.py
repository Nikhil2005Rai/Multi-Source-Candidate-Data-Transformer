"""Projection from internal canonical profile to requested output JSON."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from transformer.models.canonical import CanonicalProfile
from transformer.models.config import FieldConfig, NormalizeDirective, OnMissing, ProjectionConfig
from transformer.normalizer import Normalizer


MISSING = object()


class ProjectionError(ValueError):
    """Raised when projection cannot satisfy the requested config."""


class Projector:
    """Apply runtime projection config to a CanonicalProfile."""

    def __init__(self) -> None:
        self.normalizer = Normalizer()

    def project(self, profile: CanonicalProfile, config: ProjectionConfig) -> dict[str, Any]:
        if not config.fields:
            return self._full_canonical(profile, config)

        output: dict[str, Any] = {}
        for field in config.fields:
            value = self._extract_path(profile, field.from_path)
            value = self._apply_normalization(value, field)
            if value is MISSING or value is None or value == []:
                self._handle_missing(output, field, config)
                continue
            output[field.path] = value

        if config.include_confidence:
            output["overall_confidence"] = profile.overall_confidence
        if config.include_provenance:
            output["provenance"] = [asdict(item) for item in profile.provenance]
        if config.include_diagnostics and profile.diagnostics:
            output["diagnostics"] = [asdict(item) for item in profile.diagnostics]
        return output

    def _full_canonical(self, profile: CanonicalProfile, config: ProjectionConfig) -> dict[str, Any]:
        result = asdict(profile)
        if not config.include_confidence:
            result.pop("overall_confidence", None)
        if not config.include_provenance:
            result.pop("provenance", None)
        if not config.include_diagnostics:
            result.pop("diagnostics", None)
        return result

    def _handle_missing(
        self,
        output: dict[str, Any],
        field: FieldConfig,
        config: ProjectionConfig,
    ) -> None:
        if config.on_missing == OnMissing.ERROR:
            raise ProjectionError(f"Missing required projected field '{field.path}'.")
        if config.on_missing == OnMissing.NULL:
            output[field.path] = None

    # Projector type-coercion note:
    # FieldConfig.type describes the expected output shape for OutputValidator;
    # it is not an instruction for the projector to coerce extracted values.
    # Keeping projection non-coercive preserves source/merge semantics and
    # surfaces mismatches at validation time instead of silently converting data.
    def _apply_normalization(self, value: Any, field: FieldConfig) -> Any:
        if value is MISSING or field.normalize is None:
            return value
        if field.normalize == NormalizeDirective.E164:
            if isinstance(value, list):
                return [item for item in (self.normalizer.normalize_phone(v) for v in value) if item]
            return self.normalizer.normalize_phone(value)
        if field.normalize == NormalizeDirective.CANONICAL:
            if isinstance(value, list):
                return [item for item in (self.normalizer.normalize_skill(v) for v in value) if item]
            return self.normalizer.normalize_skill(value)
        return value

    def _extract_path(self, obj: Any, path: str) -> Any:
        return self._extract_parts(obj, path.split("."))

    def _extract_parts(self, obj: Any, parts: list[str]) -> Any:
        current: Any = obj
        for index, part in enumerate(parts):
            if "[]" in part:
                name = part.replace("[]", "")
                items = self._get_attr(current, name)
                if items is MISSING or not isinstance(items, list):
                    return MISSING
                rest = parts[index + 1 :]
                if not rest:
                    return items
                return [value for item in items if (value := self._extract_parts(item, rest)) is not MISSING]
            if "[" in part and part.endswith("]"):
                name, index_text = part[:-1].split("[", 1)
                items = self._get_attr(current, name)
                if items is MISSING:
                    return MISSING
                try:
                    current = items[int(index_text)]
                except (IndexError, ValueError, TypeError):
                    return MISSING
                continue
            current = self._get_attr(current, part)
            if current is MISSING:
                return MISSING
        return current

    @staticmethod
    def _get_attr(obj: Any, name: str) -> Any:
        if obj is MISSING:
            return MISSING
        if isinstance(obj, dict):
            return obj.get(name, MISSING)
        if is_dataclass(obj):
            return getattr(obj, name, MISSING)
        return getattr(obj, name, MISSING)
