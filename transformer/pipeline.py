"""End-to-end orchestration for candidate transformation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transformer.github_api import GitHubApiClient
from transformer.identity import IdentityResolver
from transformer.merger import MergeEngine
from transformer.models.canonical import DiagnosticEntry
from transformer.models.config import ProjectionConfig
from transformer.models.raw import RawCandidate
from transformer.parsers.csv_parser import CsvParser
from transformer.parsers.github_parser import GitHubParser
from transformer.projector import Projector
from transformer.validator import OutputValidator


class CandidatePipeline:
    """Coordinate parsing, identity resolution, merge, projection, validation."""

    def __init__(self) -> None:
        self.parsers = {
            ".csv": CsvParser(),
            ".json": GitHubParser(),
        }
        self.merger = MergeEngine()
        self.projector = Projector()
        self.validator = OutputValidator()

    def run(
        self,
        inputs: list[Path],
        config: ProjectionConfig,
        identity_resolver: IdentityResolver | None = None,
        github_users: list[str] | None = None,
        github_token: str | None = None,
    ) -> list[dict[str, Any]]:
        raw_candidates: list[RawCandidate] = []
        diagnostics: list[DiagnosticEntry] = []

        for path in inputs:
            parser = self.parsers.get(path.suffix.lower())
            if parser is None:
                diagnostics.append(
                    DiagnosticEntry(
                        source=str(path),
                        stage="detect",
                        message=f"No parser registered for extension '{path.suffix}'.",
                    )
                )
                continue
            result = parser.parse(path)
            raw_candidates.extend(result.candidates)
            diagnostics.extend(result.diagnostics)

        if github_users:
            github_client = GitHubApiClient(token=github_token)
            for username in github_users:
                result = github_client.fetch_candidate(username)
                raw_candidates.extend(result.candidates)
                diagnostics.extend(result.diagnostics)

        resolver = identity_resolver or IdentityResolver()
        identity_result = resolver.resolve(raw_candidates)
        grouped = identity_result.groups

        outputs: list[dict[str, Any]] = []
        for candidate_id in sorted(grouped):
            group_diagnostics = diagnostics + identity_result.diagnostics_by_identity.get(candidate_id, [])
            profile = self.merger.merge_group(candidate_id, grouped[candidate_id], group_diagnostics)
            projected = self.projector.project(profile, config)
            self.validator.validate(projected, config)
            outputs.append(projected)
        return outputs
