import hashlib
import json
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch, Mock

from it_toolkit.managers.runtime_execution_manager import RuntimeExecutionError, RuntimeExecutionManager


class RuntimeExecutionManagerTests(unittest.TestCase):


    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

        self.staging = self.root / "staging"

        self.runtime_path = self.staging / "python-test/3.12.1"

        self.executable = self.runtime_path / "bin/python3"

        # Create the placeholder executable first.
        self.executable.parent.mkdir(parents=True)
        self.executable.write_text(
            "placeholder",
            encoding="utf-8",
        )

        # Calculate its checksum after the file exists.
        executable_hash = hashlib.sha256(self.executable.read_bytes()).hexdigest()

        self.metadata = {
            "metadata_version": 1,
            "runtime_id": "python-test",
            "runtime": "python",
            "version": "3.12.1",
            "archive_sha256": "a" * 64,
            "executable": "bin/python3",
            "executable_sha256": executable_hash,
            "staged_at": "2026-01-01T00:00:00+00:00",
        }

        metadata_path = self.runtime_path / ".runtime-staged.json"

        metadata_path.write_text(
            json.dumps(self.metadata),
            encoding="utf-8",
        )

        self.selection = {
            "selection_version": 1,
            "runtime_id": "python-test",
            "runtime": "python",
            "version": "3.12.1",
            "runtime_path": str(self.runtime_path.resolve()),
            "executable_path": str(self.executable.resolve()),
            "executable_sha256": executable_hash,
            "archive_sha256": "a" * 64,
            "selected_at": "2026-01-01T00:00:00+00:00",
        }

        self.staging.mkdir(parents=True, exist_ok=True)

        self.selection_path = self.staging / "selected_runtime.json"

        self.selection_path.write_text(
            json.dumps(self.selection),
            encoding="utf-8",
        )

        self.manager = RuntimeExecutionManager(staging_root=self.staging,)


    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_load_selected_runtime(self):
        selected = self.manager.get_selected_runtime()

        self.assertEqual(
            selected["runtime_id"],
            "python-test",
        )

        self.assertEqual(
            selected["version"],
            "3.12.1",
        )

        self.assertEqual(
            selected["executable"],
            self.executable.resolve(),
        )

    @patch("it_toolkit.managers.runtime_execution_manager.subprocess.run")
    def test_run_selected_runtime(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Python 3.12.1",
            stderr="",
        )

        result = self.manager.run_selected(
            ["--version"]
        )

        self.assertTrue(result.success)
        self.assertEqual(result.return_code, 0)

        mock_run.assert_called_once()

        command = mock_run.call_args.args[0]
        options = mock_run.call_args.kwargs

        self.assertEqual(
            command,
            [str(self.executable.resolve()), "--version"],
        )

        self.assertFalse(options["shell"])
        self.assertEqual(
            options["cwd"],
            str(self.runtime_path.resolve()),
        )

    @patch("it_toolkit.managers.runtime_execution_manager.subprocess.run")
    def test_probe_selected_python(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Python 3.12.1",
            stderr="",
        )

        result = self.manager.probe_selected_runtime()

        self.assertTrue(result.success)

        command = mock_run.call_args.args[0]

        self.assertEqual(
            command[-1],
            "--version",
        )

    @patch("it_toolkit.managers.runtime_execution_manager.subprocess.run")
    def test_probe_rejects_wrong_reported_version(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Python 3.11.0",
            stderr="",
        )

        result = self.manager.probe_selected_runtime()

        self.assertFalse(result.success)
        self.assertIn("version", result.error.lower())

    @patch("it_toolkit.managers.runtime_execution_manager.subprocess.run")
    def test_run_uses_timeout(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr="",
        )

        self.manager.run_selected(
            ["--version"],
            timeout=10,
        )

        self.assertEqual(
            mock_run.call_args.kwargs["timeout"],
            10,
        )

    @patch("it_toolkit.managers.runtime_execution_manager.subprocess.run")
    def test_timeout_is_reported(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="python3",
            timeout=1,
        )

        result = self.manager.run_selected(
            ["--version"],
            timeout=1,
        )

        self.assertTrue(result.timed_out)
        self.assertFalse(result.success)

    def test_rejects_missing_selection(self):
        self.selection_path.unlink()

        with self.assertRaises(RuntimeExecutionError):
            self.manager.get_selected_runtime()

    def test_rejects_metadata_identity_mismatch(self):
        self.metadata["runtime_id"] = "different-runtime"

        (self.runtime_path / ".runtime-staged.json").write_text(
            json.dumps(self.metadata),
            encoding="utf-8",
        )

        with self.assertRaises(RuntimeExecutionError):
            self.manager.get_selected_runtime()

    def test_rejects_missing_executable(self):
        self.executable.unlink()

        with self.assertRaises(RuntimeExecutionError):
            self.manager.get_selected_runtime()

    def test_rejects_unsafe_executable_path(self):
        self.metadata["executable"] = "../../outside"

        (self.runtime_path / ".runtime-staged.json").write_text(
            json.dumps(self.metadata),
            encoding="utf-8",
        )

        with self.assertRaises(RuntimeExecutionError):
            self.manager.get_selected_runtime()

    def test_rejects_selection_path_mismatch(self):
        self.selection["runtime_path"] = str(self.root / "elsewhere")

        self.selection_path.write_text(
            json.dumps(self.selection),
            encoding="utf-8",
        )

        with self.assertRaises(RuntimeExecutionError):
            self.manager.get_selected_runtime()

    def test_rejects_null_argument(self):
        with self.assertRaises(ValueError):
            self.manager.run_selected(["bad\x00argument"])

    def test_rejects_modified_executable(self):
        self.executable.write_text(
            "modified executable",
            encoding="utf-8",
        )

        with self.assertRaises(RuntimeExecutionError):
            self.manager.get_selected_runtime()


    @patch("it_toolkit.managers.runtime_execution_manager.subprocess.run")
    def test_probe_selected_powershell(self, mock_run):
        # Create a separate staged PowerShell runtime.
        runtime_id = "powershell-test"
        version = "7.4.6"

        runtime_path = self.staging / runtime_id / version
        executable = runtime_path / "bin/pwsh"

        executable.parent.mkdir(parents=True)
        executable.write_text(
            "placeholder",
            encoding="utf-8",
        )

        executable_hash = hashlib.sha256(executable.read_bytes()).hexdigest()

        metadata = {
            "metadata_version": 1,
            "runtime_id": runtime_id,
            "runtime": "powershell",
            "version": version,
            "archive_sha256": "a" * 64,
            "executable": "bin/pwsh",
            "executable_sha256": executable_hash,
            "staged_at": "2026-01-01T00:00:00+00:00",
        }

        (runtime_path / ".runtime-staged.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )

        selection = {
            "selection_version": 1,
            "runtime_id": runtime_id,
            "runtime": "powershell",
            "version": version,
            "runtime_path": str(runtime_path.resolve()),
            "executable_path": str(executable.resolve()),
            "executable_sha256": executable_hash,
            "archive_sha256": "a" * 64,
            "selected_at": "2026-01-01T00:00:00+00:00",
        }

        self.selection_path.write_text(
            json.dumps(selection),
            encoding="utf-8",
        )

        mock_run.return_value = Mock(
            returncode=0,
            stdout="7.4.6",
            stderr="",
        )

        result = self.manager.probe_selected_runtime()

        self.assertTrue(result.success)

        command = mock_run.call_args.args[0]

        self.assertIn("-NoProfile", command)
        self.assertIn("-NonInteractive", command)
        self.assertIn("-Command", command)
        self.assertIn(
            "$PSVersionTable.PSVersion.ToString()",
            command,
        )


    @patch("it_toolkit.managers.runtime_execution_manager.subprocess.run")
    def test_execution_is_audited(self, mock_run):
        from it_toolkit.managers.runtime_record_manager import (
            RuntimeRecordManager,
        )

        from it_toolkit.enums import RuntimeOperationStatus

        mock_run.return_value = Mock(
            returncode=0,
            stdout="Python 3.12.1",
            stderr="",
        )

        audit = RuntimeRecordManager(
            self.root / "reports/runtime-history.jsonl"
        )

        manager = RuntimeExecutionManager(
            staging_root=self.staging,
            record_manager=audit,
        )

        result = manager.run_selected(["--version"])

        self.assertTrue(result.success)
        self.assertEqual(audit.count(), 1)

        records = audit.get_records(operation="execute")

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0].status,
            RuntimeOperationStatus.EXECUTED,
        )


if __name__ == "__main__":
    unittest.main()