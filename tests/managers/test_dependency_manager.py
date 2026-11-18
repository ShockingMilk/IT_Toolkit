import hashlib
import json
import tempfile
import unittest

from pathlib import Path

from it_toolkit.enums import (
    Architecture,
    OperatingSystem,
    Runtime,
    ToolkitMode,
)
from it_toolkit.managers.dependency_manager import (
    DependencyManager,
    RepositoryError,
)
from it_toolkit.models.operating_system import OperatingSystemInfo
from it_toolkit.models.python_info import PythonInfo
from it_toolkit.models.system_profile import SystemProfile


class DependencyManagerTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

        self.repository = self.root / "repository"
        self.repository.mkdir()

        self.package_directory = self.repository / "packages"
        self.package_directory.mkdir()

        self.package_file = (
            self.package_directory / "example.bin"
        )

        self.package_file.write_bytes(b"example package contents")

        self.checksum = hashlib.sha256(
            self.package_file.read_bytes()
        ).hexdigest()

        self.manifest = {
            "manifest_version": 1,
            "repository_name": "Test Repository",
            "packages": [
                {
                    "package_id": "example.tool",
                    "name": "Example Tool",
                    "version": "1.0.0",
                    "type": "executable",
                    "file": "packages/example.bin",
                    "sha256": self.checksum,
                    "operating_systems": ["linux"],
                    "architectures": ["x86_64"],
                    "description": "Test package",
                }
            ],
        }

        self.write_manifest()

        self.manager = DependencyManager(self.repository)

    def tearDown(self):
        self.temp_directory.cleanup()

    def write_manifest(self):
        manifest_path = self.repository / "manifest.json"

        manifest_path.write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

    @staticmethod
    def make_profile(
        operating_system=OperatingSystem.LINUX,
        architecture=Architecture.X86_64,
        python_version="3.12.1",
        implementation="CPython",
    ):
        return SystemProfile(
            operating_system=OperatingSystemInfo(
                family=operating_system,
                name=operating_system.value,
                version="1",
                architecture=architecture,
            ),
            python=PythonInfo(
                installed=True,
                version=python_version,
                implementation=implementation,
                meets_requirement=True,
            ),
            shell=Runtime.UNKNOWN,
            toolkit_mode=ToolkitMode.UNKNOWN,
        )

    def test_load_manifest(self):
        manifest = self.manager.load_manifest()

        self.assertEqual(
            manifest.repository_name,
            "Test Repository",
        )

        self.assertEqual(len(manifest.packages), 1)

    def test_valid_repository(self):
        report = self.manager.inspect_repository()

        self.assertTrue(report.valid)
        self.assertEqual(len(report.packages), 1)

        package = report.packages[0]

        self.assertTrue(package.file_exists)
        self.assertTrue(package.checksum_valid)
        self.assertIsNone(package.compatible)

    def test_checksum_mismatch(self):
        self.package_file.write_bytes(b"modified package")

        report = self.manager.inspect_repository()

        self.assertFalse(report.valid)
        self.assertFalse(
            report.packages[0].checksum_valid
        )

    def test_missing_package_file(self):
        self.package_file.unlink()

        report = self.manager.inspect_repository()

        self.assertFalse(report.valid)
        self.assertFalse(
            report.packages[0].file_exists
        )

    def test_compatible_profile(self):
        report = self.manager.inspect_repository(
            self.make_profile()
        )

        self.assertTrue(report.valid)
        self.assertTrue(
            report.packages[0].compatible
        )

    def test_incompatible_operating_system(self):
        report = self.manager.inspect_repository(
            self.make_profile(
                operating_system=OperatingSystem.WINDOWS
            )
        )

        self.assertFalse(report.valid)
        self.assertFalse(
            report.packages[0].compatible
        )

    def test_incompatible_architecture(self):
        report = self.manager.inspect_repository(
            self.make_profile(
                architecture=Architecture.ARM64
            )
        )

        self.assertFalse(report.valid)
        self.assertFalse(
            report.packages[0].compatible
        )

    def test_missing_manifest(self):
        (self.repository / "manifest.json").unlink()

        with self.assertRaises(RepositoryError):
            self.manager.load_manifest()

    def test_invalid_manifest(self):
        (self.repository / "manifest.json").write_text(
            "{invalid json",
            encoding="utf-8",
        )

        with self.assertRaises(RepositoryError):
            self.manager.load_manifest()

    def test_repository_path_escape_via_symlink(self):
        outside_file = self.root / "outside.bin"
        outside_file.write_bytes(b"outside")

        link_path = self.package_directory / "outside-link.bin"

        try:
            link_path.symlink_to(outside_file)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable.")

        self.manifest["packages"][0]["file"] = (
            "packages/outside-link.bin"
        )
        self.write_manifest()

        with self.assertRaises(RepositoryError):
            self.manager.inspect_repository()


if __name__ == "__main__":
    unittest.main()