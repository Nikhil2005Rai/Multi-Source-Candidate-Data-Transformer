import json
import unittest
from unittest.mock import patch

from transformer.github_api import GitHubApiClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class GitHubApiClientTest(unittest.TestCase):
    def test_normalizes_github_profile_url_to_username(self) -> None:
        self.assertEqual(
            GitHubApiClient._normalize_username("https://github.com/octocat/"),
            "octocat",
        )

    @patch("transformer.github_api.urlopen")
    def test_fetch_candidate_builds_raw_candidate_from_live_payload(self, mocked_urlopen) -> None:
        mocked_urlopen.side_effect = [
            FakeResponse(
                {
                    "login": "octocat",
                    "name": "The Octocat",
                    "bio": "GitHub mascot",
                    "html_url": "https://github.com/octocat",
                }
            ),
            FakeResponse([{"name": "hello-world", "language": "Ruby"}]),
        ]

        result = GitHubApiClient().fetch_candidate("octocat")

        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].raw_id, "octocat")
        self.assertEqual(result.candidates[0].full_name, "The Octocat")
        self.assertEqual(result.candidates[0].skills[0].raw_name, "Ruby")


if __name__ == "__main__":
    unittest.main()
