"""Deterministic candidate identity grouping."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from transformer.models.canonical import DiagnosticEntry
from transformer.models.raw import RawCandidate, SourceType
from transformer.normalizer import Normalizer


@dataclass
class IdentityResolutionResult:
    groups: dict[str, list[RawCandidate]]
    diagnostics_by_identity: dict[str, list[DiagnosticEntry]] = field(default_factory=dict)


class IdentityResolver:
    """Group raw source records into candidate identities."""

    def __init__(self, id_map: dict[str, str] | None = None) -> None:
        self.id_map = id_map or {}
        self.normalizer = Normalizer()

    @classmethod
    def from_file(cls, path: str | Path | None) -> "IdentityResolver":
        if not path:
            return cls()
        with Path(path).open(encoding="utf-8") as f:
            return cls(json.load(f))

    def group(self, candidates: list[RawCandidate]) -> dict[str, list[RawCandidate]]:
        return self.resolve(candidates).groups

    def resolve(self, candidates: list[RawCandidate]) -> IdentityResolutionResult:
        groups: dict[str, list[RawCandidate]] = defaultdict(list)
        diagnostics_by_identity: dict[str, list[DiagnosticEntry]] = defaultdict(list)
        github_to_candidate = {v: k for k, v in self.id_map.items()}

        for candidate in candidates:
            identity = None
            identity_method = None
            if candidate.source.source_type == SourceType.CSV and candidate.raw_id in self.id_map:
                identity = str(candidate.raw_id)
                identity_method = "explicit_id_map"
            elif candidate.source.source_type == SourceType.GITHUB and candidate.raw_id in github_to_candidate:
                identity = github_to_candidate[str(candidate.raw_id)]
                identity_method = "explicit_id_map"

            if identity is None:
                identity = self._email_identity(candidate)
                identity_method = "email" if identity else None
            if identity is None:
                identity = f"{candidate.source.source_type.value}:{candidate.raw_id or candidate.source.source_id}"
                diagnostics_by_identity[identity].append(
                    DiagnosticEntry(
                        source=candidate.source.source_id,
                        stage="identity",
                        message="No explicit ID map or normalized email; emitted standalone unresolved profile.",
                        raw_value=candidate.raw_id,
                        field="candidate_id",
                    )
                )
            elif identity_method == "email":
                diagnostics_by_identity[identity].append(
                    DiagnosticEntry(
                        source=candidate.source.source_id,
                        stage="identity",
                        message="Resolved identity using normalized email fallback.",
                        raw_value=candidate.emails,
                        field="emails",
                    )
                )

            groups[identity].append(candidate)

        return IdentityResolutionResult(dict(groups), dict(diagnostics_by_identity))

    def _email_identity(self, candidate: RawCandidate) -> str | None:
        for email in candidate.emails:
            normalized = self.normalizer.normalize_email(email)
            if normalized:
                return f"email:{normalized}"
        return None
