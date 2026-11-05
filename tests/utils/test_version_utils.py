import unittest

from it_toolkit.utils.version_utils import (
    parse_version,
    version_at_least,
)

class TestVersionUtils(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(
            parse_version("7.4.2"),
            (7, 4, 2),
        )

    def test_parse_version_with_prefix(self):
        self.assertEqual(
            parse_version("v7.6.0"),
            (7, 6, 0),
        )

    def test_version_meets_requirement(self):
        self.assertTrue(
            version_at_least("7.4.0", "7.1")
        )

    def test_version_does_not_meet_requirement(self):
        self.assertFalse(
            version_at_least("7.0.0", "7.1")
        )

    def test_equal_version(self):
        self.assertTrue(
            version_at_least("7.1", "7.1.0")
        )

    def test_invalid_version(self):
        self.assertFalse(
            version_at_least("unknown", "7.1")
        )

if __name__ == "__main__":
    unittest.main()