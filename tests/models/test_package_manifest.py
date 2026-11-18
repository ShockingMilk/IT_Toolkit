import unittest

from it_toolkit.enums import DependencyType
from it_toolkit.models.package_manifest import (
    ManifestError,
    PackageEntry,
    PackageManifest,
)


VALID_PACKAGE = {
    "package_id": "example.tool",
    "name": "Example Tool",
    "version": "1.0.0",
    "type": "executable",
    "file": "packages/example-tool.bin",
    "sha256": "a" * 64,
    "operating_systems": ["linux"],
    "architectures": ["x86_64"],
}


class PackageManifestTests(unittest.TestCase):

    def test_valid_package_entry(self):
        package = PackageEntry.from_dict(VALID_PACKAGE)

        self.assertEqual(package.package_id, "example.tool")
        self.assertEqual(package.version, "1.0.0")
        self.assertEqual(
            package.dependency_type,
            DependencyType.EXECUTABLE,
        )

    def test_invalid_checksum_rejected(self):
        data = dict(VALID_PACKAGE)
        data["sha256"] = "not-a-checksum"

        with self.assertRaises(ManifestError):
            PackageEntry.from_dict(data)

    def test_parent_directory_path_rejected(self):
        data = dict(VALID_PACKAGE)
        data["file"] = "../outside/package.bin"

        with self.assertRaises(ManifestError):
            PackageEntry.from_dict(data)

    def test_absolute_path_rejected(self):
        data = dict(VALID_PACKAGE)
        data["file"] = "/outside/package.bin"

        with self.assertRaises(ManifestError):
            PackageEntry.from_dict(data)

    def test_windows_separator_rejected(self):
        data = dict(VALID_PACKAGE)
        data["file"] = "packages\\package.bin"

        with self.assertRaises(ManifestError):
            PackageEntry.from_dict(data)

    def test_unknown_dependency_type_rejected(self):
        data = dict(VALID_PACKAGE)
        data["type"] = "unknown"

        with self.assertRaises(ManifestError):
            PackageEntry.from_dict(data)

    def test_duplicate_package_version_rejected(self):
        manifest = {
            "manifest_version": 1,
            "repository_name": "Test Repository",
            "packages": [
                VALID_PACKAGE,
                VALID_PACKAGE,
            ],
        }

        with self.assertRaises(ManifestError):
            PackageManifest.from_dict(manifest)

    def test_empty_repository_is_valid(self):
        manifest = PackageManifest.from_dict({
            "manifest_version": 1,
            "repository_name": "Test Repository",
            "packages": [],
        })

        self.assertEqual(manifest.packages, ())


if __name__ == "__main__":
    unittest.main()