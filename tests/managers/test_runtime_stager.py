import hashlib
import json
import tempfile
import unittest
import zipfile

from pathlib import Path
from types import SimpleNamespace

from it_toolkit.enums import Architecture, OperatingSystem, RuntimeOperationStatus
from it_toolkit.managers.runtime_stager import RuntimeStager


class RuntimeStagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

        self.repository = self.root / "repository"
        self.staging = self.root / "staging"

        self.repository.mkdir()

        self.archive = self.repository / "python-runtime.zip"

        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("bin/", "")
            archive.writestr("bin/python3", "#!/bin/sh\n")

        checksum = hashlib.sha256(self.archive.read_bytes()).hexdigest()

        self.manifest = {
            "manifest_version": 1,
            "repository_name": "test-runtimes",
            "runtimes": [
                {
                    "runtime_id": "python-test",
                    "runtime": "python",
                    "version": "3.12.1",
                    "archive": "python-runtime.zip",
                    "archive_format": "zip",
                    "sha256": checksum,
                    "operating_systems": ["linux"],
                    "architectures": ["x86_64"],
                    "executable": "bin/python3",
                }
            ],
        }

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        self.profile = SimpleNamespace(
            operating_system=SimpleNamespace(
                family=OperatingSystem.LINUX,
                architecture=Architecture.X86_64,
            )
        )

        self.stager = RuntimeStager(
            self.repository,
            self.staging,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_stage_requires_explicit_approval(self):
        result = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.SKIPPED)
        self.assertFalse((self.staging / "python-test" / "3.12.1").exists())

    def test_stage_valid_runtime(self):
        result = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        destination = self.staging / "python-test" / "3.12.1"

        self.assertEqual(result.status, RuntimeOperationStatus.STAGED)
        self.assertTrue((destination / "bin" / "python3").is_file())
        self.assertTrue((destination / RuntimeStager.METADATA_FILENAME).is_file())

    def test_stage_does_not_overwrite_existing_runtime(self):
        first = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )
        self.assertTrue(first.success)

        second = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        self.assertEqual(second.status, RuntimeOperationStatus.FAILED)
        self.assertTrue(
            (self.staging / "python-test" / "3.12.1" / "bin" / "python3").is_file()
        )

    def test_stage_rejects_archive_path_traversal(self):
        malicious = self.repository / "malicious.zip"

        with zipfile.ZipFile(malicious, "w") as archive:
            archive.writestr("../outside.txt", "bad")

        self.manifest["runtimes"][0]["archive"] = "malicious.zip"
        self.manifest["runtimes"][0]["sha256"] = hashlib.sha256(malicious.read_bytes()).hexdigest()

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        result = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)
        self.assertFalse((self.root / "outside.txt").exists())

    def test_stage_rejects_symbolic_link_in_zip(self):
        malicious = self.repository / "link.zip"

        with zipfile.ZipFile(malicious, "w") as archive:
            info = zipfile.ZipInfo("bin/python3")
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            archive.writestr(info, "../../outside")

        self.manifest["runtimes"][0]["archive"] = "link.zip"
        self.manifest["runtimes"][0]["sha256"] = hashlib.sha256(malicious.read_bytes()).hexdigest()

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        result = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

    def test_stage_rejects_missing_manifest_executable(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("bin/not-python", "placeholder")

        self.manifest["runtimes"][0]["sha256"] = hashlib.sha256(self.archive.read_bytes()).hexdigest()

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        result = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

    def test_stage_rejects_oversized_archive_member(self):
        stager = RuntimeStager(
            self.repository,
            self.staging,
            max_file_size=4,
        )

        result = stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

    def test_failed_staging_cleans_temporary_directory(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("../escape.txt", "bad")

        self.manifest["runtimes"][0]["sha256"] = hashlib.sha256(self.archive.read_bytes()).hexdigest()

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        result = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

        runtime_parent = self.staging / "python-test"
        if runtime_parent.exists():
            self.assertEqual(list(runtime_parent.iterdir()), [])


    def test_stage_tar_directory_without_trailing_slash(self):
        import io
        import tarfile

        archive_path = self.repository / "python-runtime.tar.gz"

        with tarfile.open(archive_path, "w:gz") as archive:
            directory = tarfile.TarInfo("bin")
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)

            executable_data = b"#!/bin/sh\n"
            executable = tarfile.TarInfo("bin/python3")
            executable.size = len(executable_data)
            archive.addfile(
                executable,
                io.BytesIO(executable_data),
            )

        self.manifest["runtimes"][0]["archive"] = archive_path.name
        self.manifest["runtimes"][0]["archive_format"] = "tar.gz"
        self.manifest["runtimes"][0]["sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()

        (self.repository / "manifest.json").write_text(
            json.dumps(self.manifest),
            encoding="utf-8",
        )

        result = self.stager.stage(
            "python-test",
            "3.12.1",
            profile=self.profile,
            approved=True,
        )

        destination = self.staging / "python-test" / "3.12.1"

        self.assertEqual(result.status, RuntimeOperationStatus.STAGED)
        self.assertTrue((destination / "bin" / "python3").is_file())



if __name__ == "__main__":
    unittest.main()
