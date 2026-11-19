import hashlib
import json
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch, Mock

from it_toolkit.enums import (
    Architecture,
    OperatingSystem,
    Runtime,
    ToolkitMode,
    InstallationStatus,
)
from it_toolkit.managers.python_package_installer import PythonPackageInstaller
from it_toolkit.managers.installation_record_manager import InstallationRecordManager
from it_toolkit.models.operating_system import OperatingSystemInfo
from it_toolkit.models.python_info import PythonInfo
from it_toolkit.models.system_profile import SystemProfile


class PythonPackageInstallerTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

        self.repository = self.root / "repository"
        self.repository.mkdir()

        self.package_directory = self.repository / "packages"
        self.package_directory.mkdir()

        self.wheel = (
            self.package_directory / "example_package-1.0.0-py3-none-any.whl"
        )

        self.wheel.write_bytes(b"test wheel contents")

        checksum = hashlib.sha256(
            self.wheel.read_bytes()
        ).hexdigest()

        self.manifest = {
            "manifest_version": 1,
            "repository_name": "Test Repository",
            "packages": [
                {
                    "package_id": "example.package",
                    "name": "Example Package",
                    "version": "1.0.0",
                    "type": "python_module",
                    "file": "packages/example_package-1.0.0-py3-none-any.whl",
                    "sha256": checksum,
                    "operating_systems": ["linux"],
                    "architectures": ["x86_64"],
                    "python_min_version": "3.10",
                    "python_implementation": "CPython",
                }
            ],
        }

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        self.installation_root = (
            self.root / "managed" / "python"
        )

        self.fake_python = self.root / "python"

        self.fake_python.write_text(
            "test executable",
            encoding="utf-8",
        )

        self.profile = SystemProfile(
            operating_system=OperatingSystemInfo(
                family=OperatingSystem.LINUX,
                name="Linux",
                version="1",
                architecture=Architecture.X86_64,
            ),
            python=PythonInfo(
                installed=True,
                version="3.12.1",
                executable=str(self.fake_python),
                implementation="CPython",
                meets_requirement=True,
            ),
            shell=Runtime.UNKNOWN,
            toolkit_mode=ToolkitMode.UNKNOWN,
        )

        self.installer = PythonPackageInstaller(
            repository_path=self.repository,
            installation_root=self.installation_root,
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    def successful_installation(self, command, **kwargs):
        destination = Path(
            command[command.index("--target") + 1]
        )

        metadata = destination / (
            "example_package-1.0.0.dist-info"
        )

        metadata.mkdir(parents=True)

        (metadata / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: example-package\nVersion: 1.0.0\n",
            encoding="utf-8",
        )

        return Mock(
            returncode=0,
            stdout="Successfully installed example-package",
            stderr="",
        )

    def test_requires_explicit_approval(self):
        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.SKIPPED,
        )

        self.assertFalse(result.success)

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_successful_offline_installation(self, mock_run):
        mock_run.side_effect = self.successful_installation

        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.INSTALLED,
        )

        self.assertTrue(result.success)
        self.assertTrue(
            Path(result.destination_path).is_dir()
        )

        command = mock_run.call_args.args[0]

        self.assertIn("--no-index", command)
        self.assertIn("--no-deps", command)
        self.assertIn("--no-cache-dir", command)

        self.assertFalse(mock_run.call_args.kwargs["shell"])

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_inherited_pip_configuration_removed(self, mock_run):
        mock_run.side_effect = self.successful_installation

        with patch.dict(
            "os.environ",
            {
                "PIP_INDEX_URL": "https://example.invalid/simple",
                "PIP_TARGET": "/unexpected/location",
            },
        ):
            self.installer.install(
                "example.package",
                "1.0.0",
                self.profile,
                approved=True,
            )

        environment = mock_run.call_args.kwargs["env"]

        self.assertNotIn("PIP_INDEX_URL", environment)
        self.assertNotIn("PIP_TARGET", environment)
        self.assertEqual(environment["PIP_NO_INDEX"], "1")

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_pip_failure_is_reported(self, mock_run):
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Installation failed",
        )

        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.FAILED,
        )

        self.assertFalse(result.success)

        self.assertFalse(
            Path(result.destination_path).exists()
        )

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_missing_installation_metadata_is_failure(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr="",
        )

        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.FAILED,
        )

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_checksum_mismatch_prevents_installation(self, mock_run):
        self.wheel.write_bytes(b"modified wheel")

        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.FAILED,
        )

        mock_run.assert_not_called()

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_incompatible_package_prevents_installation(self, mock_run):
        self.manifest["packages"][0]["operating_systems"] = [
            "windows"
        ]

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.FAILED,
        )

        mock_run.assert_not_called()

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_existing_destination_is_not_overwritten(self, mock_run):
        destination = (
            self.installation_root
            / "example.package"
            / "1.0.0"
        )

        destination.mkdir(parents=True)

        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.SKIPPED,
        )

        mock_run.assert_not_called()

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_only_wheel_files_are_supported(self, mock_run):
        self.manifest["packages"][0]["file"] = (
            "packages/example_package.tar.gz"
        )

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        result = self.installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        self.assertEqual(
            result.status,
            InstallationStatus.FAILED,
        )

        mock_run.assert_not_called()

    def test_unknown_package_raises_error(self):
        from it_toolkit.managers.dependency_manager import RepositoryError

        with self.assertRaises(RepositoryError):
            self.installer.install(
                "missing.package",
                "1.0.0",
                self.profile,
                approved=True,
            )

    def test_invalid_timeout_rejected(self):
        with self.assertRaises(ValueError):
            PythonPackageInstaller(
                self.repository,
                self.installation_root,
                timeout_seconds=0,
            )

    @patch(
        "it_toolkit.managers.python_package_installer.subprocess.run"
    )
    def test_successful_installation_is_recorded(self, mock_run):
        mock_run.side_effect = self.successful_installation

        record_manager = InstallationRecordManager(
            self.root / "reports" / "installations.jsonl"
        )

        installer = PythonPackageInstaller(
            repository_path=self.repository,
            installation_root=self.installation_root,
            record_manager=record_manager,
        )

        result = installer.install(
            "example.package",
            "1.0.0",
            self.profile,
            approved=True,
        )

        records = record_manager.get_records()

        self.assertEqual(result.status, InstallationStatus.INSTALLED)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].package_id, "example.package")
        self.assertEqual(records[0].status, InstallationStatus.INSTALLED)


if __name__ == "__main__":
    unittest.main()