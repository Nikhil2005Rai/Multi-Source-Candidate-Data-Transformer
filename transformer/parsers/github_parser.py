"""GitHub profile parser for API-compatible JSON fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from transformer.models.canonical import DiagnosticEntry
from transformer.models.raw import RawCandidate, RawSkill, SourceMeta, SourceType
from transformer.parsers.base import ParseResult, SourceParser


class GitHubParser(SourceParser):
    """Parse a GitHub profile JSON file.

    The expected shape is intentionally close to GitHub REST responses:
    profile fields plus optional repositories with language metadata.
    """

    def parse(self, path: Path) -> ParseResult:
        source_id = str(path)
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return ParseResult(
                diagnostics=[
                    DiagnosticEntry(
                        source=source_id,
                        stage="parse",
                        message=f"Could not parse GitHub JSON: {exc}",
                    )
                ]
            )

        return self.parse_data(data, source_id=source_id)

    def parse_data(self, data: Any, source_id: str) -> ParseResult:
        """Parse API-compatible GitHub profile data already loaded in memory."""
        profiles = data if isinstance(data, list) else [data]
        candidates: list[RawCandidate] = []
        diagnostics: list[DiagnosticEntry] = []

        for index, profile in enumerate(profiles):
            if not isinstance(profile, dict):
                diagnostics.append(
                    DiagnosticEntry(
                        source=source_id,
                        stage="parse",
                        message=f"Skipped GitHub entry {index}: expected object.",
                        raw_value=profile,
                    )
                )
                continue
            candidates.append(self._candidate_from_profile(source_id, profile))

        return ParseResult(candidates=candidates, diagnostics=diagnostics)

    def _candidate_from_profile(self, source_id: str, profile: dict[str, Any]) -> RawCandidate:
        username = str(profile.get("login") or profile.get("username") or "unknown")
        skills = self._skills_from_profile(profile)
        html_url = profile.get("html_url") or f"https://github.com/{username}"

        return RawCandidate(
            source=SourceMeta(source_id=f"github:{username}", source_type=SourceType.GITHUB),
            raw_id=username,
            full_name=self._clean(profile.get("name")),
            emails=[email] if (email := self._clean(profile.get("email"))) else [],
            country=self._clean(profile.get("location")),
            github_url=self._clean(html_url),
            headline=self._clean(profile.get("bio")),
            skills=skills,
            extra={
                "public_repos": profile.get("public_repos"),
                "source": source_id,
            },
        )

    def _skills_from_profile(self, profile: dict[str, Any]) -> list[RawSkill]:
        skills: dict[str, RawSkill] = {}

        for language in profile.get("languages", []) or []:
            if isinstance(language, str) and language.strip():
                skills[language.strip()] = RawSkill(language.strip(), "github_profile:languages")

        for repo in profile.get("repositories", []) or []:
            if not isinstance(repo, dict):
                continue
            language = self._clean(repo.get("language"))
            if language:
                skills.setdefault(language, RawSkill(language, "github_repo:language"))
            for language in repo.get("languages", []) or []:
                if isinstance(language, str) and language.strip():
                    skills.setdefault(language.strip(), RawSkill(language.strip(), "github_repo:languages"))

        return list(skills.values())

    @staticmethod
    def _clean(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
