import unittest

from transformer.merger import MergeEngine
from transformer.models.raw import RawCandidate, RawEducation, RawExperience, SourceMeta, SourceType


class MergeEngineTest(unittest.TestCase):
    def test_invalid_phone_is_recorded_in_provenance(self) -> None:
        raw = RawCandidate(
            source=SourceMeta("csv:1", SourceType.CSV),
            raw_id="1",
            phones=["123"],
        )

        profile = MergeEngine().merge_group("1", [raw])

        self.assertEqual(profile.phones, [])
        self.assertEqual(profile.provenance[0].field, "phones")
        self.assertEqual(profile.provenance[0].note, "invalid_value:not_emitted")

    def test_experience_dates_and_education_are_normalized(self) -> None:
        raw = RawCandidate(
            source=SourceMeta("csv:1", SourceType.CSV),
            raw_id="1",
            experience=[
                RawExperience(company="OldCo", title="Engineer", start="01/2020", end="12/2022"),
                RawExperience(company="NewCo", title="Senior Engineer", start="Jan 2023", end="Present"),
            ],
            education=[
                RawEducation(
                    institution="NIET",
                    degree="B.Tech",
                    field="Computer Science",
                    end_year="2025",
                )
            ],
        )

        profile = MergeEngine().merge_group("1", [raw])

        self.assertEqual(profile.experience[0].company, "NewCo")
        self.assertEqual(profile.experience[0].start, "2023-01")
        self.assertEqual(profile.education[0].end_year, 2025)

    def test_single_source_scalar_keeps_base_confidence_when_uncontested(self) -> None:
        raw = RawCandidate(
            source=SourceMeta("csv:1", SourceType.CSV),
            raw_id="1",
            years_experience=4.0,
        )

        profile = MergeEngine().merge_group("1", [raw])

        years = next(item for item in profile.provenance if item.field == "years_experience")
        self.assertEqual(years.confidence, 0.9)

    def test_scalar_conflict_penalizes_only_the_winning_confidence(self) -> None:
        csv_raw = RawCandidate(
            source=SourceMeta("csv:1", SourceType.CSV),
            raw_id="1",
            full_name="Asha Mehta",
        )
        github_raw = RawCandidate(
            source=SourceMeta("github:asha", SourceType.GITHUB),
            raw_id="asha",
            full_name="Asha M.",
        )

        profile = MergeEngine().merge_group("1", [csv_raw, github_raw])

        winner = next(item for item in profile.provenance if item.field == "full_name" and item.note is None)
        self.assertEqual(profile.full_name, "Asha Mehta")
        self.assertEqual(winner.confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
