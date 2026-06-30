"""Live GitHub API source."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from transformer.models.canonical import DiagnosticEntry
from transformer.parsers.base import ParseResult
from transformer.parsers.github_parser import GitHubParser


GITHUB_API_ROOT = "https://api.github.com"


class GitHubApiClient:
    """Fetch candidate signals from the public GitHub REST API."""

    def __init__(self, token: str | None = None, timeout_seconds: int = 10) -> None:
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.parser = GitHubParser()

    def fetch_candidate(self, username: str) -> ParseResult:
        username = self._normalize_username(username)
        source = f"github-api:{username}"
        diagnostics: list[DiagnosticEntry] = []

        profile = self._get_json(f"/users/{quote(username)}", source, diagnostics)
        if not isinstance(profile, dict):
            return ParseResult(diagnostics=diagnostics)

        repos = self._get_json(
            f"/users/{quote(username)}/repos?per_page=100&sort=updated",
            source,
            diagnostics,
        )
        if isinstance(repos, list):
            profile["repositories"] = repos
        else:
            profile["repositories"] = []

        parsed = self.parser.parse_data(profile, source_id=source)
        parsed.diagnostics.extend(diagnostics)
        return parsed

    def _get_json(
        self,
        path: str,
        source: str,
        diagnostics: list[DiagnosticEntry],
    ) -> Any | None:
        request = Request(
            f"{GITHUB_API_ROOT}{path}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = f"GitHub API returned HTTP {exc.code}."
            if exc.code == 403:
                message += " Rate limit may be exhausted; set GITHUB_TOKEN or pass --github-token."
            diagnostics.append(DiagnosticEntry(source=source, stage="fetch", message=message, raw_value=path))
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            diagnostics.append(
                DiagnosticEntry(
                    source=source,
                    stage="fetch",
                    message=f"GitHub API request failed: {exc}",
                    raw_value=path,
                )
            )
        return None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "eightfold-candidate-transformer",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def _normalize_username(value: str) -> str:
        value = value.strip().rstrip("/")
        if "/" in value:
            return value.split("/")[-1]
        return value
