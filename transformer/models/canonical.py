"""Internal canonical candidate profile.

The merge engine produces CanonicalProfile objects and the projector consumes
them. This model is intentionally internal: callers receive only projected JSON.
"""

from __future__ import annotations

# Duplicate-model cleanup note:
# The historical Pydantic version of this module is dead code for the current
# architecture: parsers, merger, projector, and pipeline all import these
# dataclasses directly. We keep canonical models as dataclasses because they are
# internal transport objects that are created and reshaped frequently after
# parser-level normalization, where Pydantic's runtime validation overhead would
# not buy much safety. Pydantic remains valuable at the OutputValidator boundary,
# where external JSON shape is finally checked against the requested projection.

from dataclasses import dataclass, field
from typing import Any

from transformer.models.raw import SourceType


@dataclass(frozen=True)
class ValueEvidence:
    """A candidate value plus the trust metadata needed for merging."""

    field: str
    value: Any
    source_id: str
    source_type: SourceType
    method: str
    confidence: float
    raw_value: Any | None = None


@dataclass(frozen=True)
class ProvenanceEntry:
    """Audit trail for a value that appears in the canonical profile."""

    field: str
    source: str
    method: str
    confidence: float
    raw_value: Any | None = None
    note: str | None = None


@dataclass(frozen=True)
class DiagnosticEntry:
    """Non-fatal issue encountered while parsing, normalizing, or merging."""

    source: str
    stage: str
    message: str
    raw_value: Any | None = None
    field: str | None = None


@dataclass
class CanonicalLocation:
    city: str | None = None
    region: str | None = None
    country: str | None = None


@dataclass
class CanonicalLinks:
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other: list[str] = field(default_factory=list)


@dataclass
class CanonicalSkill:
    name: str
    confidence: float
    sources: list[str] = field(default_factory=list)


@dataclass
class CanonicalExperience:
    company: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    summary: str | None = None


@dataclass
class CanonicalEducation:
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    end_year: int | None = None


@dataclass
class CanonicalProfile:
    """Clean internal representation for one resolved candidate."""

    candidate_id: str
    full_name: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    location: CanonicalLocation = field(default_factory=CanonicalLocation)
    links: CanonicalLinks = field(default_factory=CanonicalLinks)
    headline: str | None = None
    years_experience: float | None = None
    skills: list[CanonicalSkill] = field(default_factory=list)
    experience: list[CanonicalExperience] = field(default_factory=list)
    education: list[CanonicalEducation] = field(default_factory=list)
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    diagnostics: list[DiagnosticEntry] = field(default_factory=list)
    overall_confidence: float = 0.0
