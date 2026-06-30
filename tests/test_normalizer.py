import unittest

from transformer.normalizer import Normalizer


class NormalizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = Normalizer()

    def test_normalizes_common_values(self) -> None:
        self.assertEqual(self.normalizer.normalize_email(" User@Example.COM "), "user@example.com")
        self.assertEqual(self.normalizer.normalize_phone("9876543210", "IN"), "+919876543210")
        self.assertEqual(self.normalizer.normalize_skill("js"), "JavaScript")
        self.assertEqual(self.normalizer.normalize_country("United States"), "US")
        self.assertEqual(self.normalizer.normalize_country("IND"), "IN")
        self.assertEqual(self.normalizer.normalize_date_month("Jan 2023"), "2023-01")
        self.assertEqual(self.normalizer.normalize_date_month("06/2021"), "2021-06")

    def test_invalid_values_return_none(self) -> None:
        self.assertIsNone(self.normalizer.normalize_email("not-an-email"))
        self.assertIsNone(self.normalizer.normalize_phone("123"))
        self.assertIsNone(self.normalizer.normalize_country("Atlantis"))


if __name__ == "__main__":
    unittest.main()
