import unittest

from transformer.models.canonical import CanonicalProfile, CanonicalSkill
from transformer.models.config import FieldConfig, OnMissing, ProjectionConfig
from transformer.projector import Projector
from transformer.validator import OutputValidator, ValidationError


class ProjectorTest(unittest.TestCase):
    def test_projects_array_path(self) -> None:
        profile = CanonicalProfile(
            candidate_id="candidate-1",
            full_name="Asha Mehta",
            emails=["asha@example.com"],
            skills=[
                CanonicalSkill("Python", 0.9, ["csv"]),
                CanonicalSkill("Spark", 0.8, ["github"]),
            ],
        )
        config = ProjectionConfig(
            fields=[
                FieldConfig("primary_email", "emails[0]", "string"),
                FieldConfig("skills", "skills[].name", "string[]"),
            ]
        )

        projected = Projector().project(profile, config)

        self.assertEqual(projected["primary_email"], "asha@example.com")
        self.assertEqual(projected["skills"], ["Python", "Spark"])

    def test_required_null_projected_field_passes_when_on_missing_null(self) -> None:
        profile = CanonicalProfile(candidate_id="candidate-1")
        config = ProjectionConfig(
            fields=[FieldConfig("headline", "headline", "string", required=True)],
            on_missing=OnMissing.NULL,
        )
        projected = Projector().project(profile, config)

        self.assertIsNone(projected["headline"])
        OutputValidator().validate(projected, config)

    def test_required_missing_field_errors_when_on_missing_error(self) -> None:
        profile = CanonicalProfile(candidate_id="candidate-1")
        config = ProjectionConfig(
            fields=[FieldConfig("headline", "headline", "string", required=True)],
            on_missing=OnMissing.ERROR,
        )

        with self.assertRaises(ValueError):
            Projector().project(profile, config)

    def test_required_projected_field_with_value_passes_validation(self) -> None:
        profile = CanonicalProfile(candidate_id="candidate-1", headline="Data Engineer")
        config = ProjectionConfig(
            fields=[FieldConfig("headline", "headline", "string", required=True)],
            on_missing=OnMissing.NULL,
        )
        projected = Projector().project(profile, config)

        OutputValidator().validate(projected, config)

    def test_optional_null_projected_field_passes_validation(self) -> None:
        profile = CanonicalProfile(candidate_id="candidate-1")
        config = ProjectionConfig(
            fields=[FieldConfig("headline", "headline", "string", required=False)],
            on_missing=OnMissing.NULL,
        )
        projected = Projector().project(profile, config)

        self.assertIsNone(projected["headline"])
        OutputValidator().validate(projected, config)


if __name__ == "__main__":
    unittest.main()
