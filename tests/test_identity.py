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


if __name__ == "__main__":
    unittest.main()
