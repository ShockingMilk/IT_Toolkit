import tempfile
import unittest

from pathlib import Path

from it_toolkit.utils.checksum import (
    calculate_sha256,
    verify_sha256,
)


class ChecksumTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_directory.name) / "sample.bin"
        self.file_path.write_bytes(b"IT Toolkit checksum test")

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_calculate_sha256(self):
        checksum = calculate_sha256(self.file_path)

        self.assertEqual(len(checksum), 64)

    def test_verify_correct_checksum(self):
        checksum = calculate_sha256(self.file_path)

        self.assertTrue(
            verify_sha256(self.file_path, checksum)
        )

    def test_reject_incorrect_checksum(self):
        self.assertFalse(
            verify_sha256(self.file_path, "0" * 64)
        )

    def test_invalid_chunk_size_rejected(self):
        with self.assertRaises(ValueError):
            calculate_sha256(self.file_path, chunk_size=0)


if __name__ == "__main__":
    unittest.main()