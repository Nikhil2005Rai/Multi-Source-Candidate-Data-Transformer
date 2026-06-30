"""Parser interface for source-specific extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from transformer.models.canonical import DiagnosticEntry
from transformer.models.raw import RawCandidate


class ParseResult:
    """Candidates plus non-fatal parser diagnostics."""

    def __init__(
        self,
        candidates: list[RawCandidate] | None = None,
        diagnostics: list[DiagnosticEntry] | None = None,
    ) -> None:
        self.candidates = candidates or []
        self.diagnostics = diagnostics or []


class SourceParser(ABC):
    """Base class for parsers.

    Parsers must not raise for malformed source records. They return diagnostics
    and keep extracting anything usable.
    """

    @abstractmethod
    def parse(self, path: Path) -> ParseResult:
        """Parse a source file into raw candidates."""
