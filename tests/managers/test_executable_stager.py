import hashlib
import json
import tempfile
import unittest

from pathlib import Path

from it_toolkit.enums import InstallationStatus
from it_toolkit.managers.executable_stager import ExecutableStager
from it_toolkit.managers.installation_record_manager import InstallationRecordManager


class ExecutableStagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.repository = self.root / "repository"
        self.package_directory = self.repository / "packages"
        self.package_directory.mkdir(parents=True)

        self.staging_root = self.root / "staged"
        self.package_file = (
            self.package_directory / "sample-tool.bin"
        )
        self.package_file.write_bytes(
            b"sample executable package"
        )

        checksum = hashlib.sha256(
            self.package_file.read_bytes()
        ).hexdigest()

        manifest = {
            "manifest_version": 1,
            "repository_name": "Test Repository",
            "packages": [
                {
                    "package_id": "sample-tool",
                    "name": "Sample Tool",
                    "version": "1.0.0",
                    "type": "executable",
                    "file": "packages/sample-tool.bin",
                    "sha256": checksum,
                    "operating_systems": ["linux"],
                    "architectures": ["x86_64"],
                }
            ],
        }

        self.repository.mkdir(exist_ok=True)
        (self.repository / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        self.profile = self._make_profile()
        self.stager = ExecutableStager(
            self.repository,
            self.staging_root,
        )

    @staticmethod
    def _make_profile():
        from types import SimpleNamespace

        return SimpleNamespace(
            operating_system=SimpleNamespace(
                family=SimpleNamespace(value="linux"),
                architecture=SimpleNamespace(value="x86_64"),
            ),
            python=SimpleNamespace(
                version="3.12.0",
                implementation="CPython",
            ),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_approval_is_required(self):
        result = self.stager.stage(
            "sample-tool",
            "1.0.0",
            self.profile,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.SKIPPED,
        )
        self.assertFalse(self.staging_root.exists())

    def test_successful_staging_copies_file(self):
        result = self.stager.stage(
            "sample-tool",
            "1.0.0",
            self.profile,
            approved=True,
        )

        expected = (
            self.staging_root
            / "sample-tool"
            / "1.0.0"
            / "sample-tool.bin"
        )

        self.assertEqual(
            result.status,
            InstallationStatus.STAGED,
        )
        self.assertEqual(
            Path(result.destination_path).resolve(),
            expected.resolve(),
        )
        self.assertTrue(expected.is_file())
        self.assertEqual(
            expected.read_bytes(),
            self.package_file.read_bytes(),
        )
        self.assertIn("not executed", result.message.lower())

    def test_existing_destination_is_not_overwritten(self):
        destination = (
            self.staging_root
            / "sample-tool"
            / "1.0.0"
            / "sample-tool.bin"
        )
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"existing file")

        result = self.stager.stage(
            "sample-tool",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.SKIPPED,
        )
        self.assertEqual(
            destination.read_bytes(),
            b"existing file",
        )

    def test_checksum_mismatch_prevents_staging(self):
        manifest_path = self.repository / "manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        manifest["packages"][0]["sha256"] = "0" * 64
        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        result = self.stager.stage(
            "sample-tool",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.FAILED,
        )
        self.assertFalse(self.staging_root.exists())

    def test_incompatible_platform_prevents_staging(self):
        self.profile.operating_system.family.value = "windows"

        result = self.stager.stage(
            "sample-tool",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.FAILED,
        )
        self.assertFalse(self.staging_root.exists())

    def test_python_package_is_not_staged(self):
        manifest_path = self.repository / "manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        manifest["packages"][0]["type"] = "python_module"
        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        result = self.stager.stage(
            "sample-tool",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.SKIPPED,
        )
        self.assertFalse(self.staging_root.exists())

    def test_unknown_package_raises_repository_error(self):
        from it_toolkit.managers.dependency_manager import RepositoryError

        with self.assertRaises(RepositoryError):
            self.stager.stage(
                "unknown-tool",
                "1.0.0",
                self.profile,
                approved=True,
            )

    def test_successful_staging_is_recorded(self):
        record_manager = InstallationRecordManager(
            self.root / "reports" / "installations.jsonl"
        )

        stager = ExecutableStager(
            self.repository,
            self.staging_root,
            record_manager=record_manager,
        )

        result = stager.stage(
            "sample-tool",
            "1.0.0",
            self.profile,
            approved=True,
        )

        records = record_manager.get_records()

        self.assertEqual(result.status, InstallationStatus.STAGED)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].package_id, "sample-tool")
        self.assertEqual(records[0].status, InstallationStatus.STAGED)


if __name__ == "__main__":
    unittest.main()