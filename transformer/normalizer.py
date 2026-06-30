"""Normalization utilities used before merge and during projection."""

from __future__ import annotations

import re
from datetime import datetime

import phonenumbers
import pycountry
from phonenumbers import NumberParseException


SKILL_ALIASES = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "golang": "Go",
    "go": "Go",
    "reactjs": "React",
    "react": "React",
    "node": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
}

class Normalizer:
    """Pure normalization helpers.

    Invalid values return None so callers can preserve raw values in diagnostics.
    """

    def normalize_email(self, value: str | None) -> str | None:
        if not value:
            return None
        email = value.strip().lower()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return email
        return None

    def normalize_phone(self, value: str | None, default_country: str = "IN") -> str | None:
        if not value:
            return None
        region = (default_country or "IN").upper()
        try:
            parsed = phonenumbers.parse(value, region)
        except NumberParseException:
            return None
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        return None

    def normalize_skill(self, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value.strip())
        if not cleaned:
            return None
        return SKILL_ALIASES.get(cleaned.lower(), cleaned)

    def normalize_country(self, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = value.strip()
        if len(cleaned) == 2:
            country = pycountry.countries.get(alpha_2=cleaned.upper())
            return country.alpha_2 if country else None
        if len(cleaned) == 3:
            country = pycountry.countries.get(alpha_3=cleaned.upper())
            return country.alpha_2 if country else None
        try:
            return pycountry.countries.lookup(cleaned).alpha_2
        except LookupError:
            return None

    def normalize_date_month(self, value: str | None) -> str | None:
        if not value:
            return None
        text = value.strip()
        if text.lower() in {"present", "current", "now"}:
            return None

        for fmt in ("%Y-%m", "%Y/%m", "%m/%Y", "%b %Y", "%B %Y", "%Y"):
            try:
                parsed = datetime.strptime(text, fmt)
                return f"{parsed.year:04d}-{parsed.month:02d}"
            except ValueError:
                continue
        return None

    def normalize_end_year(self, value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"(19|20)\d{2}", value)
        return int(match.group(0)) if match else None
