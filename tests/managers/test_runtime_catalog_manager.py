import json
import tempfile
import unittest

from pathlib import Path

from it_toolkit.enums import Runtime
from it_toolkit.managers.runtime_catalog_manager import RuntimeCatalogManager, RuntimeRepositoryError


class RuntimeCatalogManagerTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repository = self.root / "runtimes"
        self.repository.mkdir()

        self.archive_directory = self.repository / "packages/python"
        self.archive_directory.mkdir(parents=True)

        self.archive = self.archive_directory / "python-runtime.tar.gz"
        self.archive.write_bytes(b"placeholder archive")

        self.manifest = {
            "manifest_version": 1,
            "repository_name": "Test Runtimes",
            "runtimes": [
                {
                    "runtime_id": "python-test",
                    "runtime": "python",
                    "version": "3.12.8",
                    "archive": (
                        "packages/python/python-runtime.tar.gz"
                    ),
                    "archive_format": "tar.gz",
                    "sha256": "a" * 64,
                    "operating_systems": ["linux"],
                    "architectures": ["x86_64"],
                    "executable": "bin/python3",
                    "python_implementation": "CPython",
                }
            ],
        }

        self.write_manifest()
        self.manager = RuntimeCatalogManager(self.repository)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_manifest(self):
        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

    def test_load_manifest(self):
        manifest = self.manager.load_manifest()

        self.assertEqual(
            manifest.repository_name,
            "Test Runtimes",
        )
        self.assertEqual(len(manifest.runtimes), 1)

    def test_list_runtimes(self):
        runtimes = self.manager.list_runtimes()

        self.assertEqual(len(runtimes), 1)
        self.assertEqual(runtimes[0].runtime, Runtime.PYTHON)

    def test_get_exact_runtime(self):
        entry = self.manager.get_runtime(
            "python-test",
            "3.12.8",
        )

        self.assertEqual(entry.version, "3.12.8")

    def test_unknown_runtime_raises_error(self):
        with self.assertRaises(RuntimeRepositoryError):
            self.manager.get_runtime(
                "missing-runtime",
                "1.0",
            )

    def test_resolve_archive_path(self):
        entry = self.manager.get_runtime(
            "python-test",
            "3.12.8",
        )

        resolved = self.manager.resolve_archive_path(entry)

        self.assertEqual(resolved, self.archive.resolve())

    def test_archive_symlink_escape_is_rejected(self):
        outside = self.root / "outside.tar.gz"
        outside.write_bytes(b"outside")

        link = self.archive_directory / "outside.tar.gz"

        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable.")

        self.manifest["runtimes"][0]["archive"] = "packages/python/outside.tar.gz"
        self.write_manifest()

        entry = self.manager.get_runtime(
            "python-test",
            "3.12.8",
        )

        with self.assertRaises(RuntimeRepositoryError):
            self.manager.resolve_archive_path(entry)

    def test_missing_manifest_raises_error(self):
        (self.repository / "manifest.json").unlink()

        with self.assertRaises(RuntimeRepositoryError):
            self.manager.load_manifest()

    def test_invalid_manifest_raises_error(self):
        (self.repository / "manifest.json").write_text(
            "{invalid json",
            encoding="utf-8",
        )

        with self.assertRaises(RuntimeRepositoryError):
            self.manager.load_manifest()


if __name__ == "__main__":
    unittest.main()