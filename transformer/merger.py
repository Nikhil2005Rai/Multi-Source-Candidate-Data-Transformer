"""Merge raw candidates into canonical profiles."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any

from transformer.models.canonical import (
    CanonicalEducation,
    CanonicalExperience,
    CanonicalProfile,
    CanonicalSkill,
    DiagnosticEntry,
    ProvenanceEntry,
    ValueEvidence,
)
from transformer.models.raw import RawCandidate, SourceType
from transformer.normalizer import Normalizer


BASE_CONFIDENCE = {
    SourceType.CSV: 0.90,
    SourceType.GITHUB: 0.70,
}

FIELD_WEIGHTS = {
    "full_name": 3.0,
    "emails": 3.0,
    "phones": 2.0,
    "headline": 1.5,
    "years_experience": 1.5,
    "location": 1.0,
    "links": 0.75,
    "skills": 1.25,
    "experience": 1.5,
    "education": 1.0,
}


class MergeEngine:
    """Resolve source records into a single canonical profile."""

    def __init__(self) -> None:
        self.normalizer = Normalizer()

    def merge_group(
        self,
        candidate_id: str,
        raw_candidates: list[RawCandidate],
        diagnostics: list[DiagnosticEntry] | None = None,
    ) -> CanonicalProfile:
        profile = CanonicalProfile(candidate_id=self._stable_candidate_id(candidate_id))
        profile.diagnostics.extend(diagnostics or [])

        evidence = self._collect_evidence(raw_candidates, profile)
        self._resolve_scalars(profile, evidence)
        self._resolve_lists(profile, evidence)
        self._resolve_structured_lists(profile, raw_candidates)
        profile.overall_confidence = self._overall_confidence(profile)
        return profile

    def _collect_evidence(
        self,
        raw_candidates: list[RawCandidate],
        profile: CanonicalProfile,
    ) -> dict[str, list[ValueEvidence]]:
        evidence: dict[str, list[ValueEvidence]] = defaultdict(list)

        for raw in raw_candidates:
            base = BASE_CONFIDENCE[raw.source.source_type]
            self._add(evidence, "full_name", raw.full_name, raw, "field:full_name", base)
            self._add(evidence, "headline", raw.headline, raw, "field:headline", base - 0.05)
            self._add(evidence, "years_experience", raw.years_experience, raw, "field:years_experience", base)
            self._add(evidence, "location.city", raw.city, raw, "field:city", base)
            self._add(evidence, "location.region", raw.region, raw, "field:region", base)

            country = self.normalizer.normalize_country(raw.country)
            if raw.country and not country and raw.source.source_type == SourceType.GITHUB:
                self._add(evidence, "location.city", raw.country, raw, "field:github_location", base - 0.05)
            elif raw.country and not country:
                profile.diagnostics.append(
                    DiagnosticEntry(raw.source.source_id, "normalize", "Unrecognized country.", raw.country, "location.country")
                )
            self._add(evidence, "location.country", country, raw, "normalize:country", base)

            self._add(evidence, "links.github", raw.github_url, raw, "field:github_url", base)
            self._add(evidence, "links.linkedin", raw.linkedin_url, raw, "field:linkedin_url", base)
            self._add(evidence, "links.portfolio", raw.portfolio_url, raw, "field:portfolio_url", base)

            for email in raw.emails:
                normalized = self.normalizer.normalize_email(email)
                if normalized:
                    self._add(evidence, "emails", normalized, raw, "normalize:email", base + 0.03, email)
                else:
                    profile.diagnostics.append(
                        DiagnosticEntry(raw.source.source_id, "normalize", "Invalid email ignored.", email, "emails")
                    )

            for phone in raw.phones:
                country_hint = self.normalizer.normalize_country(raw.country) or "IN"
                normalized = self.normalizer.normalize_phone(phone, country_hint)
                if normalized:
                    self._add(evidence, "phones", normalized, raw, "normalize:phone", base + 0.03, phone)
                else:
                    profile.provenance.append(
                        ProvenanceEntry(
                            field="phones",
                            source=raw.source.source_id,
                            method="normalize:phone",
                            confidence=0.0,
                            raw_value=phone,
                            note="invalid_value:not_emitted",
                        )
                    )
                    profile.diagnostics.append(
                        DiagnosticEntry(raw.source.source_id, "normalize", "Invalid phone ignored.", phone, "phones")
                    )

            for skill in raw.skills:
                normalized = self.normalizer.normalize_skill(skill.raw_name)
                if normalized:
                    confidence = base if raw.source.source_type == SourceType.CSV else base - 0.10
                    self._add(evidence, "skills", normalized, raw, skill.context or "normalize:skill", confidence, skill.raw_name)

        return evidence

    def _resolve_scalars(self, profile: CanonicalProfile, evidence: dict[str, list[ValueEvidence]]) -> None:
        scalar_fields = {
            "full_name": lambda value: setattr(profile, "full_name", value),
            "headline": lambda value: setattr(profile, "headline", value),
            "years_experience": lambda value: setattr(profile, "years_experience", value),
            "location.city": lambda value: setattr(profile.location, "city", value),
            "location.region": lambda value: setattr(profile.location, "region", value),
            "location.country": lambda value: setattr(profile.location, "country", value),
            "links.github": lambda value: setattr(profile.links, "github", value),
            "links.linkedin": lambda value: setattr(profile.links, "linkedin", value),
            "links.portfolio": lambda value: setattr(profile.links, "portfolio", value),
        }

        for field, setter in scalar_fields.items():
            winner = self._choose_winner(evidence.get(field, []))
            if not winner:
                continue
            setter(winner.value)
            profile.provenance.append(
                self._provenance(field, winner, confidence=self._adjusted_confidence(winner, evidence.get(field, [])))
            )
            for loser in evidence.get(field, []):
                if loser is not winner and loser.value != winner.value:
                    profile.provenance.append(
                        self._provenance(
                            field,
                            loser,
                            note=f"rejected_conflict:winner={winner.source_id}",
                        )
                    )
                    profile.diagnostics.append(
                        DiagnosticEntry(
                            source=loser.source_id,
                            stage="merge",
                            message=f"Value lost conflict to higher confidence source: {winner.source_id}",
                            raw_value=loser.raw_value if loser.raw_value is not None else loser.value,
                            field=field,
                        )
                    )

    def _resolve_lists(self, profile: CanonicalProfile, evidence: dict[str, list[ValueEvidence]]) -> None:
        profile.emails = self._dedup_values(evidence.get("emails", []), "emails", profile)
        profile.phones = self._dedup_values(evidence.get("phones", []), "phones", profile)

        skills_by_name: dict[str, list[ValueEvidence]] = defaultdict(list)
        for item in evidence.get("skills", []):
            skills_by_name[item.value].append(item)
        for name in sorted(skills_by_name):
            items = skills_by_name[name]
            confidence = min(1.0, max(item.confidence for item in items) + 0.05 * (len(items) - 1))
            if len({item.source_id for item in items}) == 1:
                confidence -= 0.10
            sources = sorted({item.source_id for item in items})
            profile.skills.append(CanonicalSkill(name=name, confidence=round(confidence, 3), sources=sources))
            profile.provenance.append(
                self._provenance(
                    f"skills[{name}]",
                    max(items, key=lambda item: item.confidence),
                    confidence=round(max(0.0, confidence), 3),
                )
            )

    def _resolve_structured_lists(self, profile: CanonicalProfile, raw_candidates: list[RawCandidate]) -> None:
        seen_experience: set[tuple[Any, ...]] = set()
        seen_education: set[tuple[Any, ...]] = set()
        for raw in raw_candidates:
            for item in raw.experience:
                experience = CanonicalExperience(
                    company=item.company,
                    title=item.title,
                    start=self.normalizer.normalize_date_month(item.start),
                    end=self.normalizer.normalize_date_month(item.end),
                    summary=item.summary,
                )
                key = tuple(asdict(experience).values())
                if key not in seen_experience and any(key):
                    seen_experience.add(key)
                    profile.experience.append(experience)
                    profile.provenance.append(
                        ProvenanceEntry(
                            field="experience",
                            source=raw.source.source_id,
                            method="normalize:experience",
                            confidence=BASE_CONFIDENCE[raw.source.source_type],
                            raw_value=asdict(item),
                        )
                    )

            for item in raw.education:
                education = CanonicalEducation(
                    institution=item.institution,
                    degree=item.degree,
                    field=item.field,
                    end_year=self.normalizer.normalize_end_year(item.end_year),
                )
                key = tuple(asdict(education).values())
                if key not in seen_education and any(key):
                    seen_education.add(key)
                    profile.education.append(education)
                    profile.provenance.append(
                        ProvenanceEntry(
                            field="education",
                            source=raw.source.source_id,
                            method="normalize:education",
                            confidence=BASE_CONFIDENCE[raw.source.source_type],
                            raw_value=asdict(item),
                        )
                    )

        profile.experience.sort(key=self._experience_sort_key, reverse=True)

    def _dedup_values(
        self,
        values: list[ValueEvidence],
        field: str,
        profile: CanonicalProfile,
    ) -> list[str]:
        best_by_value: dict[str, ValueEvidence] = {}
        for item in values:
            current = best_by_value.get(item.value)
            if current is None or item.confidence > current.confidence:
                best_by_value[item.value] = item
        for value in sorted(best_by_value):
            same_value_evidence = [item for item in values if item.value == value]
            profile.provenance.append(
                self._provenance(
                    field,
                    best_by_value[value],
                    confidence=self._adjusted_confidence(best_by_value[value], same_value_evidence),
                )
            )
        return sorted(best_by_value)

    def _choose_winner(self, values: list[ValueEvidence]) -> ValueEvidence | None:
        if not values:
            return None
        return sorted(values, key=lambda item: (item.confidence, item.source_type == SourceType.CSV), reverse=True)[0]

    def _add(
        self,
        evidence: dict[str, list[ValueEvidence]],
        field: str,
        value: Any,
        raw: RawCandidate,
        method: str,
        confidence: float,
        raw_value: Any | None = None,
    ) -> None:
        if value is None or value == "":
            return
        evidence[field].append(
            ValueEvidence(
                field=field,
                value=value,
                source_id=raw.source.source_id,
                source_type=raw.source.source_type,
                method=method,
                confidence=round(max(0.0, min(1.0, confidence)), 3),
                raw_value=value if raw_value is None else raw_value,
            )
        )

    @staticmethod
    def _provenance(
        field: str,
        evidence: ValueEvidence,
        note: str | None = None,
        confidence: float | None = None,
    ) -> ProvenanceEntry:
        return ProvenanceEntry(
            field=field,
            source=evidence.source_id,
            method=evidence.method,
            confidence=evidence.confidence if confidence is None else confidence,
            raw_value=evidence.raw_value,
            note=note,
        )

    @staticmethod
    def _adjusted_confidence(winner: ValueEvidence, values: list[ValueEvidence]) -> float:
        """Boost corroborated winners and penalize only genuine competing values."""
        corroborating_sources = {
            item.source_id for item in values if item.value == winner.value and item.source_id != winner.source_id
        }
        if corroborating_sources:
            return round(min(1.0, winner.confidence + 0.10), 3)

        # Confidence-penalty bug fix:
        # A single emitted value can mean either "another source tried this same
        # field and lost with a different value" or simply "no other source had
        # that field at all." The old flat penalty treated both as weak evidence,
        # which unfairly lowered CSV-only fields such as years_experience and
        # location.region. We keep the deterministic rule-based model, but make
        # the tradeoff explicit: lack of corroboration is neutral, while an
        # actual conflicting attempt from another source still reduces trust.
        conflicting_sources = {
            item.source_id for item in values if item.value != winner.value and item.source_id != winner.source_id
        }
        if conflicting_sources:
            return round(max(0.0, winner.confidence - 0.10), 3)
        return winner.confidence

    @staticmethod
    def _stable_candidate_id(identity: str) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in identity).strip("-")
        return safe or "candidate"

    @staticmethod
    def _overall_confidence(profile: CanonicalProfile) -> float:
        weighted_total = 0.0
        weight_total = 0.0
        for entry in profile.provenance:
            if entry.note and entry.note.startswith("rejected_conflict"):
                continue
            weight = MergeEngine._weight_for_field(entry.field)
            weighted_total += entry.confidence * weight
            weight_total += weight
        if not weight_total:
            return 0.0
        return round(weighted_total / weight_total, 3)

    @staticmethod
    def _weight_for_field(field: str) -> float:
        if field.startswith("location."):
            return FIELD_WEIGHTS["location"]
        if field.startswith("links."):
            return FIELD_WEIGHTS["links"]
        if field.startswith("skills["):
            return FIELD_WEIGHTS["skills"]
        return FIELD_WEIGHTS.get(field, 1.0)

    @staticmethod
    def _experience_sort_key(item: CanonicalExperience) -> tuple[int, str]:
        current_rank = 1 if item.end is None else 0
        date = item.start or "0000-00"
        return (current_rank, date)
