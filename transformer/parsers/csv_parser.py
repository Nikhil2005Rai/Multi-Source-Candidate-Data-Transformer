"""Recruiter CSV parser."""

from __future__ import annotations

import csv
from pathlib import Path

from transformer.models.canonical import DiagnosticEntry
from transformer.models.raw import RawCandidate, RawEducation, RawExperience, RawSkill, SourceMeta, SourceType
from transformer.parsers.base import ParseResult, SourceParser


class CsvParser(SourceParser):
    """Parse the structured recruiter CSV source."""

    def parse(self, path: Path) -> ParseResult:
        source_id = str(path)
        candidates: list[RawCandidate] = []
        diagnostics: list[DiagnosticEntry] = []

        try:
            with path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return ParseResult(
                        diagnostics=[
                            DiagnosticEntry(
                                source=source_id,
                                stage="parse",
                                message="CSV file has no header row.",
                            )
                        ]
                    )

                for row_number, row in enumerate(reader, start=2):
                    try:
                        candidate = self._candidate_from_row(path, row, row_number)
                        candidates.append(candidate)
                    except Exception as exc:
                        diagnostics.append(
                            DiagnosticEntry(
                                source=source_id,
                                stage="parse",
                                message=f"Skipped malformed CSV row {row_number}: {exc}",
                                raw_value=row,
                            )
                        )
        except OSError as exc:
            diagnostics.append(
                DiagnosticEntry(
                    source=source_id,
                    stage="parse",
                    message=f"Could not read CSV file: {exc}",
                )
            )

        return ParseResult(candidates=candidates, diagnostics=diagnostics)

    def _candidate_from_row(self, path: Path, row: dict[str, str], row_number: int) -> RawCandidate:
        raw_id = self._first(row, "candidate_id", "id", "row_id") or f"row-{row_number}"
        skills = [
            RawSkill(raw_name=item.strip(), context="csv_field:skills")
            for item in self._split_multi(self._first(row, "skills", "skill_names"))
        ]

        current_company = self._first(row, "current_company", "company")
        title = self._first(row, "title", "current_title")
        experience = []
        if current_company or title:
            experience.append(
                RawExperience(
                    company=current_company,
                    title=title,
                    start=self._first(row, "start", "start_date"),
                    end=self._first(row, "end", "end_date"),
                    summary=self._first(row, "summary"),
                )
            )

        education = []
        institution = self._first(row, "institution", "school", "university", "education_institution")
        degree = self._first(row, "degree", "education_degree")
        field = self._first(row, "field", "major", "education_field")
        end_year = self._first(row, "end_year", "graduation_year", "education_end_year")
        if institution or degree or field or end_year:
            education.append(
                RawEducation(
                    institution=institution,
                    degree=degree,
                    field=field,
                    end_year=end_year,
                )
            )

        return RawCandidate(
            source=SourceMeta(source_id=f"{path.name}:{raw_id}", source_type=SourceType.CSV),
            raw_id=raw_id,
            full_name=self._first(row, "name", "full_name"),
            emails=self._split_multi(self._first(row, "email", "emails")),
            phones=self._split_multi(self._first(row, "phone", "phones")),
            city=self._first(row, "city"),
            region=self._first(row, "region", "state"),
            country=self._first(row, "country"),
            github_url=self._first(row, "github", "github_url"),
            linkedin_url=self._first(row, "linkedin", "linkedin_url"),
            portfolio_url=self._first(row, "portfolio", "portfolio_url"),
            headline=title,
            years_experience=self._float_or_none(self._first(row, "years_experience", "yoe")),
            skills=skills,
            experience=experience,
            education=education,
            extra={"row_number": row_number},
        )

    @staticmethod
    def _first(row: dict[str, str], *names: str) -> str | None:
        lower = {key.lower().strip(): value for key, value in row.items() if key}
        for name in names:
            value = lower.get(name.lower())
            if value is not None and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _split_multi(value: str | None) -> list[str]:
        if not value:
            return []
        normalized = value.replace("|", ",").replace(";", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]

    @staticmethod
    def _float_or_none(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None
