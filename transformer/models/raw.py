"""Raw parser output models.

Parsers convert each source into RawCandidate objects. These models preserve
source-specific uncertainty: fields are optional and values are not assumed to
be normalized yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    """Supported source categories."""

    CSV = "csv"
    GITHUB = "github"


@dataclass(frozen=True)
class SourceMeta:
    """Where a RawCandidate came from."""

    source_id: str
    source_type: SourceType
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RawSkill:
    """Skill before canonicalization."""

    raw_name: str
    context: str | None = None


@dataclass
class RawExperience:
    """Experience entry before normalization."""

    company: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    summary: str | None = None


@dataclass
class RawEducation:
    """Education entry before normalization."""

    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    end_year: str | None = None


@dataclass
class RawCandidate:
    """Candidate data extracted from one source."""

    source: SourceMeta
    raw_id: str | None = None
    full_name: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    city: str | None = None
    region: str | None = None
    country: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    headline: str | None = None
    years_experience: float | None = None
    skills: list[RawSkill] = field(default_factory=list)
    experience: list[RawExperience] = field(default_factory=list)
    education: list[RawEducation] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
