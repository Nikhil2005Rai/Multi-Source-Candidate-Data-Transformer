import unittest

from transformer.models.canonical import CanonicalProfile, CanonicalSkill
from transformer.models.config import FieldConfig, ProjectionConfig
from transformer.projector import Projector


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


if __name__ == "__main__":
    unittest.main()
