import unittest

from services.update_service import is_newer_version


class UpdateServiceTests(unittest.TestCase):
    def test_is_newer_version_handles_semantic_numbers(self):
        self.assertTrue(is_newer_version("1.0.1", "1.0.0"))
        self.assertTrue(is_newer_version("1.10.0", "1.9.9"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.0"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.1"))

    def test_is_newer_version_handles_date_style_versions(self):
        self.assertTrue(is_newer_version("2026.4.25.2", "2026.4.25.1"))
        self.assertTrue(is_newer_version("2026.5", "2026.4.99"))
        self.assertFalse(is_newer_version("2026.4.25.1", "2026.4.25.1"))


if __name__ == "__main__":
    unittest.main()
