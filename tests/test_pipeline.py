import unittest
from pathlib import Path

from transformer.identity import IdentityResolver
from transformer.models.config import ProjectionConfig
from transformer.pipeline import CandidatePipeline


class PipelineTest(unittest.TestCase):
    def test_pipeline_merges_csv_and_github_sources(self) -> None:
        config = ProjectionConfig.from_file("configs/custom_projection.json")
        identity = IdentityResolver.from_file("samples/identity_map.json")

        outputs = CandidatePipeline().run(
            [Path("samples/candidates.csv"), Path("samples/github_profiles.json")],
            config,
            identity,
        )

        self.assertEqual(len(outputs), 2)
        first = outputs[0]
        self.assertEqual(first["full_name"], "Nikhil Rai")
        self.assertEqual(first["primary_phone"], "+919876543210")
        self.assertIn("TypeScript", first["skills"])
        self.assertIn("provenance", first)

    def test_default_output_includes_education_and_normalized_dates(self) -> None:
        outputs = CandidatePipeline().run(
            [Path("samples/candidates.csv")],
            ProjectionConfig.default(),
            IdentityResolver.from_file("samples/identity_map.json"),
        )

        first = outputs[0]
        self.assertEqual(first["experience"][0]["start"], "2023-01")
        self.assertEqual(first["education"][0]["end_year"], 2025)


if __name__ == "__main__":
    unittest.main()
