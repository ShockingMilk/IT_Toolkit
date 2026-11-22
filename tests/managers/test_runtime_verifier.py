import hashlib
import json
import tarfile
import tempfile
import unittest
import zipfile

from pathlib import Path
from types import SimpleNamespace

from it_toolkit.enums import Architecture, OperatingSystem
from it_toolkit.managers.runtime_verifier import RuntimeVerifier


class RuntimeVerifierTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.repository = self.root / "runtimes"
        self.package_directory = self.repository / "packages/python"
        self.package_directory.mkdir(parents=True)

        self.archive = self.package_directory / "python-runtime.zip"

        self._create_zip(self.archive)

        self.manifest = {
            "manifest_version": 1,
            "repository_name": "Test Runtimes",
            "runtimes": [
                {
                    "runtime_id": "python-test",
                    "runtime": "python",
                    "version": "3.12.8",
                    "archive": (
                        "packages/python/python-runtime.zip"
                    ),
                    "archive_format": "zip",
                    "sha256": self._checksum(self.archive),
                    "operating_systems": ["linux"],
                    "architectures": ["x86_64"],
                    "executable": "bin/python3",
                    "python_implementation": "CPython",
                }
            ],
        }

        self.write_manifest()
        self.verifier = RuntimeVerifier(self.repository)
        self.profile = self.make_profile()

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _checksum(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _create_zip(path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "bin/python3",
                "placeholder runtime executable",
            )

    @staticmethod
    def _create_tar(path):
        source = path.parent / "runtime-file"
        source.write_text("placeholder", encoding="utf-8")

        with tarfile.open(path, "w:gz") as archive:
            archive.add(source, arcname="bin/python3")

        source.unlink()

    def write_manifest(self):
        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

    @staticmethod
    def make_profile(
        operating_system=OperatingSystem.LINUX,
        architecture=Architecture.X86_64,
    ):
        return SimpleNamespace(
            operating_system=SimpleNamespace(
                family=operating_system,
                architecture=architecture,
            )
        )

    def test_valid_runtime_archive(self):
        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            self.profile,
        )

        self.assertTrue(result.valid)
        self.assertTrue(result.archive_exists)
        self.assertTrue(result.checksum_valid)
        self.assertTrue(result.compatible)
        self.assertTrue(result.format_valid)
        self.assertEqual(result.issues, [])

    def test_checksum_mismatch(self):
        self.archive.write_bytes(b"modified archive")

        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            self.profile,
        )

        self.assertFalse(result.valid)
        self.assertFalse(result.checksum_valid)

    def test_missing_archive(self):
        self.archive.unlink()

        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            self.profile,
        )

        self.assertFalse(result.valid)
        self.assertFalse(result.archive_exists)

    def test_incompatible_operating_system(self):
        profile = self.make_profile(operating_system=OperatingSystem.WINDOWS)

        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            profile,
        )

        self.assertFalse(result.valid)
        self.assertFalse(result.compatible)

    def test_incompatible_architecture(self):
        profile = self.make_profile(architecture=Architecture.ARM64)

        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            profile,
        )

        self.assertFalse(result.valid)
        self.assertFalse(result.compatible)

    def test_unknown_host_platform_is_incompatible(self):
        profile = SimpleNamespace(
            operating_system=SimpleNamespace(
                family=None,
                architecture=None,
            )
        )

        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            profile,
        )

        self.assertFalse(result.valid)
        self.assertFalse(result.compatible)
        self.assertEqual(len(result.issues), 2)

    def test_no_profile_skips_platform_check(self):
        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
        )

        self.assertTrue(result.valid)
        self.assertTrue(result.compatible)

    def test_archive_format_mismatch(self):
        self.manifest["runtimes"][0]["archive_format"] = "tar.gz"
        self.write_manifest()

        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            self.profile,
        )

        self.assertFalse(result.valid)
        self.assertFalse(result.format_valid)
        self.assertTrue(
            any("format mismatch" in issue.lower()
                for issue in result.issues)
        )

    def test_invalid_archive_rejected(self):
        self.archive.write_bytes(b"not an archive")
        self.manifest["runtimes"][0]["sha256"] = (
            self._checksum(self.archive)
        )
        self.write_manifest()

        result = self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            self.profile,
        )

        self.assertFalse(result.valid)
        self.assertFalse(result.format_valid)

    def test_tar_gz_archive_detected(self):
        tar_archive = self.package_directory / "runtime.tar.gz"
        self._create_tar(tar_archive)

        from it_toolkit.managers.runtime_verifier import RuntimeVerifier

        detected = RuntimeVerifier._detect_archive_format(tar_archive)

        self.assertEqual(detected.value, "tar.gz")

    def test_repository_verification(self):
        report = self.verifier.verify_repository(self.profile)

        self.assertTrue(report.valid)
        self.assertEqual(report.runtime_count, 1)
        self.assertEqual(report.valid_runtime_count, 1)

    def test_repository_report_serializes(self):
        report = self.verifier.verify_repository(self.profile)
        data = report.to_dict()

        self.assertEqual(data["runtime_count"], 1)
        self.assertTrue(data["valid"])
        self.assertEqual(
            data["runtimes"][0]["runtime_id"],
            "python-test",
        )

    def test_verification_does_not_modify_archive(self):
        original = self.archive.read_bytes()

        self.verifier.verify_runtime(
            "python-test",
            "3.12.8",
            self.profile,
        )

        self.assertEqual(self.archive.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
