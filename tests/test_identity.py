import unittest

from transformer.identity import IdentityResolver
from transformer.models.raw import RawCandidate, SourceMeta, SourceType


class IdentityResolverTest(unittest.TestCase):
    def test_unresolved_record_is_flagged(self) -> None:
        candidate = RawCandidate(
            source=SourceMeta("candidates.csv:row-2", SourceType.CSV),
            raw_id="row-2",
            full_name="No Email",
        )

        result = IdentityResolver().resolve([candidate])

        self.assertIn("csv:row-2", result.groups)
        self.assertEqual(result.diagnostics_by_identity["csv:row-2"][0].stage, "identity")

    def test_github_username_matches_csv_github_url(self) -> None:
        csv_candidate = RawCandidate(
            source=SourceMeta("candidates.csv:cand-001", SourceType.CSV),
            raw_id="cand-001",
            github_url="https://github.com/Nikhil2005Rai",
        )
        github_candidate = RawCandidate(
            source=SourceMeta("github:Nikhil2005Rai", SourceType.GITHUB),
            raw_id="Nikhil2005Rai",
        )

        result = IdentityResolver().resolve([csv_candidate, github_candidate])

        self.assertEqual(len(result.groups["cand-001"]), 2)
        self.assertEqual(result.diagnostics_by_identity["cand-001"][0].field, "links.github")


if __name__ == "__main__":
    unittest.main()
