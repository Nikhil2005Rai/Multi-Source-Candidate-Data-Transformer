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

        # Identity-map inversion note:
        # GitHub records arrive with the mapped GitHub id, but groups are keyed
        # by candidate id. Building this reverse map gives O(1) lookup for each
        # GitHub record and preserves correctness: checking id_map.values()
        # could tell us a GitHub id exists, but not which candidate key owns it.
        github_to_candidate = {v.lower(): k for k, v in self.id_map.items()}
        csv_github_to_candidate = self._csv_github_identities(candidates)

        for candidate in candidates:
            identity = None
            identity_method = None
            if candidate.source.source_type == SourceType.CSV and candidate.raw_id in self.id_map:
                identity = str(candidate.raw_id)
                identity_method = "explicit_id_map"
            elif candidate.source.source_type == SourceType.GITHUB and candidate.raw_id and candidate.raw_id.lower() in github_to_candidate:
                identity = github_to_candidate[candidate.raw_id.lower()]
                identity_method = "explicit_id_map"

            if identity is None:
                identity = self._github_identity(candidate, csv_github_to_candidate)
                identity_method = "github_url" if identity else None
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
            elif identity_method == "github_url":
                diagnostics_by_identity[identity].append(
                    DiagnosticEntry(
                        source=candidate.source.source_id,
                        stage="identity",
                        message="Resolved identity using CSV GitHub URL fallback.",
                        raw_value=candidate.raw_id or candidate.github_url,
                        field="links.github",
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

    def _github_identity(self, candidate: RawCandidate, csv_github_to_candidate: dict[str, str]) -> str | None:
        username = candidate.raw_id if candidate.source.source_type == SourceType.GITHUB else candidate.github_url
        normalized = self._normalize_github_username(username)
        if normalized:
            return csv_github_to_candidate.get(normalized)
        return None

    def _csv_github_identities(self, candidates: list[RawCandidate]) -> dict[str, str]:
        identities: dict[str, str] = {}
        for candidate in candidates:
            if candidate.source.source_type != SourceType.CSV or not candidate.github_url:
                continue
            username = self._normalize_github_username(candidate.github_url)
            if username:
                identities[username] = str(candidate.raw_id or candidate.source.source_id)
        return identities

    @staticmethod
    def _normalize_github_username(value: str | None) -> str | None:
        if not value:
            return None
        text = value.strip().rstrip("/")
        if not text:
            return None
        username = text.split("/")[-1]
        return username.lower() if username else None
