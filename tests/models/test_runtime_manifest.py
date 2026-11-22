import unittest

from it_toolkit.enums import Runtime, RuntimeArchiveFormat
from it_toolkit.models.runtime_manifest import RuntimeManifest, RuntimeManifestError, RuntimePackageEntry


VALID_RUNTIME = {
    "runtime_id": "python-cpython-3.12.8-linux-x86_64",
    "runtime": "python",
    "version": "3.12.8",
    "archive": "packages/python/python-3.12.8-linux-x86_64.tar.gz",
    "archive_format": "tar.gz",
    "sha256": "a" * 64,
    "operating_systems": ["linux"],
    "architectures": ["x86_64"],
    "executable": "bin/python3",
    "python_implementation": "CPython",
}


class RuntimePackageEntryTests(unittest.TestCase):

    def test_valid_python_entry(self):
        entry = RuntimePackageEntry.from_dict(VALID_RUNTIME)

        self.assertEqual(entry.runtime, Runtime.PYTHON)
        self.assertEqual(entry.version, "3.12.8")
        self.assertEqual(
            entry.archive_format,
            RuntimeArchiveFormat.TAR_GZ,
        )
        self.assertEqual(entry.executable, "bin/python3")
        self.assertEqual(entry.operating_systems, ("linux",))

    def test_valid_powershell_entry(self):
        data = {
            "runtime_id": "powershell-7.4.6-windows-x86_64",
            "runtime": "powershell",
            "version": "7.4.6",
            "archive": "packages/powershell/pwsh.zip",
            "archive_format": "zip",
            "sha256": "b" * 64,
            "operating_systems": ["windows"],
            "architectures": ["x86_64"],
            "executable": "pwsh.exe",
            "powershell_edition": "Core",
        }

        entry = RuntimePackageEntry.from_dict(data)

        self.assertEqual(entry.runtime, Runtime.POWERSHELL)
        self.assertEqual(entry.powershell_edition, "Core")

    def test_missing_required_field_rejected(self):
        data = dict(VALID_RUNTIME)
        del data["executable"]

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_invalid_runtime_type_rejected(self):
        data = dict(VALID_RUNTIME)
        data["runtime"] = "bash"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_invalid_archive_format_rejected(self):
        data = dict(VALID_RUNTIME)
        data["archive_format"] = "rar"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_invalid_checksum_rejected(self):
        data = dict(VALID_RUNTIME)
        data["sha256"] = "invalid"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_archive_parent_traversal_rejected(self):
        data = dict(VALID_RUNTIME)
        data["archive"] = "../outside/runtime.zip"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_executable_parent_traversal_rejected(self):
        data = dict(VALID_RUNTIME)
        data["executable"] = "../../outside/python"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_absolute_archive_path_rejected(self):
        data = dict(VALID_RUNTIME)
        data["archive"] = "/outside/runtime.zip"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_windows_drive_path_rejected(self):
        data = dict(VALID_RUNTIME)
        data["archive"] = "C:/outside/runtime.zip"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_windows_separator_rejected(self):
        data = dict(VALID_RUNTIME)
        data["executable"] = "bin\\python.exe"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_unknown_operating_system_rejected(self):
        data = dict(VALID_RUNTIME)
        data["operating_systems"] = ["freebsd"]

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_unknown_architecture_rejected(self):
        data = dict(VALID_RUNTIME)
        data["architectures"] = ["riscv64"]

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_python_cannot_define_powershell_edition(self):
        data = dict(VALID_RUNTIME)
        data["powershell_edition"] = "Core"

        with self.assertRaises(RuntimeManifestError):
            RuntimePackageEntry.from_dict(data)

    def test_duplicate_runtime_version_rejected(self):
        manifest = {
            "manifest_version": 1,
            "repository_name": "Test Runtimes",
            "runtimes": [
                VALID_RUNTIME,
                VALID_RUNTIME,
            ],
        }

        with self.assertRaises(RuntimeManifestError):
            RuntimeManifest.from_dict(manifest)

    def test_empty_runtime_repository_is_valid(self):
        manifest = RuntimeManifest.from_dict({
            "manifest_version": 1,
            "repository_name": "Test Runtimes",
            "runtimes": [],
        })

        self.assertEqual(manifest.runtimes, ())

    def test_unsupported_manifest_version_rejected(self):
        with self.assertRaises(RuntimeManifestError):
            RuntimeManifest.from_dict({
                "manifest_version": 2,
                "repository_name": "Test Runtimes",
                "runtimes": [],
            })


if __name__ == "__main__":
    unittest.main()
