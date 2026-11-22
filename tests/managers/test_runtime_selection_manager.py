import json
import tempfile
import unittest

from pathlib import Path

from it_toolkit.enums import RuntimeOperationStatus
from it_toolkit.managers.runtime_stager import RuntimeStager
from it_toolkit.managers.runtime_selection_manager import RuntimeSelectionManager


class RuntimeSelectionManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.staging = self.root / "staging"

        self.runtime_path = self.staging / "python-test/3.12.1"
        self.executable = self.runtime_path / "bin/python3"

        self.executable.parent.mkdir(parents=True)
        self.executable.write_text(
            "#!/bin/sh\n",
            encoding="utf-8",
        )

        metadata = {
            "metadata_version": 1,
            "runtime_id": "python-test",
            "runtime": "python",
            "version": "3.12.1",
            "archive_sha256": "a" * 64,
            "executable": "bin/python3",
            "staged_at": "2026-01-01T00:00:00+00:00",
        }

        (self.runtime_path / RuntimeStager.METADATA_FILENAME).write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )

        self.manager = RuntimeSelectionManager(self.staging)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_selection_requires_explicit_approval(self):
        result = self.manager.select("python-test", "3.12.1")

        self.assertEqual(result.status, RuntimeOperationStatus.SKIPPED)
        self.assertIsNone(self.manager.get_selection())

    def test_select_valid_staged_runtime(self):
        result = self.manager.select(
            "python-test",
            "3.12.1",
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.SELECTED)

        selection = self.manager.get_selection()

        self.assertEqual(selection["runtime_id"], "python-test")
        self.assertEqual(selection["version"], "3.12.1")
        self.assertEqual(
            Path(selection["executable_path"]).resolve(),
            self.executable.resolve(),
        )

    def test_selection_does_not_execute_runtime(self):
        marker = self.root / "executed.txt"

        self.executable.write_text(
            f"#!/bin/sh\ntouch '{marker}'\n",
            encoding="utf-8",
        )

        result = self.manager.select(
            "python-test",
            "3.12.1",
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.SELECTED)
        self.assertFalse(marker.exists())

    def test_selection_rejects_missing_runtime(self):
        result = self.manager.select(
            "missing-runtime",
            "1.0",
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

    def test_selection_rejects_missing_executable(self):
        self.executable.unlink()

        result = self.manager.select(
            "python-test",
            "3.12.1",
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

    def test_selection_rejects_unsafe_executable_path(self):
        metadata_path = self.runtime_path / RuntimeStager.METADATA_FILENAME

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["executable"] = "../../outside"

        metadata_path.write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )

        result = self.manager.select(
            "python-test",
            "3.12.1",
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

    def test_selection_rejects_metadata_identity_mismatch(self):
        metadata_path = self.runtime_path / RuntimeStager.METADATA_FILENAME

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["runtime_id"] = "different-runtime"

        metadata_path.write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )

        result = self.manager.select(
            "python-test",
            "3.12.1",
            approved=True,
        )

        self.assertEqual(result.status, RuntimeOperationStatus.FAILED)

    def test_new_selection_replaces_previous_selection(self):
        first = self.manager.select(
            "python-test",
            "3.12.1",
            approved=True,
        )
        self.assertTrue(first.success)

        second_runtime = self.staging / "python-other" / "3.13.0"
        second_executable = second_runtime / "bin" / "python3"
        second_executable.parent.mkdir(parents=True)
        second_executable.write_text("placeholder", encoding="utf-8")

        second_metadata = {
            "metadata_version": 1,
            "runtime_id": "python-other",
            "runtime": "python",
            "version": "3.13.0",
            "archive_sha256": "b" * 64,
            "executable": "bin/python3",
            "staged_at": "2026-01-01T00:00:00+00:00",
        }

        (second_runtime / RuntimeStager.METADATA_FILENAME).write_text(
            json.dumps(second_metadata),
            encoding="utf-8",
        )

        second = self.manager.select(
            "python-other",
            "3.13.0",
            approved=True,
        )

        self.assertTrue(second.success)
        self.assertEqual(
            self.manager.get_selection()["runtime_id"],
            "python-other",
        )


if __name__ == "__main__":
    unittest.main()
