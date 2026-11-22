import json
import tempfile
import unittest

from pathlib import Path

from it_toolkit.enums import RuntimeOperationStatus
from it_toolkit.managers.runtime_record_manager import RuntimeAuditLogError, RuntimeRecordManager
from it_toolkit.models.runtime_operation import RuntimeOperationResult


class RuntimeRecordManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.history_path = Path(self.temporary_directory.name) / "runtime-history.jsonl"
        self.manager = RuntimeRecordManager(self.history_path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def make_result(
        self,
        operation="stage",
        runtime_id="python-test",
        status=RuntimeOperationStatus.STAGED,
    ):
        return RuntimeOperationResult(
            operation=operation,
            runtime_id=runtime_id,
            runtime="python",
            version="3.12.1",
            status=status,
            source_path="/repository/python.zip",
            destination_path="/staging/python-test/3.12.1",
            sha256="a" * 64,
            message="Test operation",
        )

    def test_record_creates_audit_file(self):
        record = self.manager.record(self.make_result())

        self.assertTrue(self.history_path.is_file())
        self.assertEqual(record.operation, "stage")
        self.assertEqual(self.manager.count(), 1)

    def test_records_can_be_filtered(self):
        self.manager.record(self.make_result())
        self.manager.record(
            self.make_result(
                operation="select",
                runtime_id="python-other",
                status=RuntimeOperationStatus.SELECTED,
            )
        )

        self.assertEqual(len(self.manager.get_records(runtime_id="python-test")), 1)
        self.assertEqual(len(self.manager.get_records(operation="select")), 1)
        self.assertEqual(len(self.manager.get_records(status=RuntimeOperationStatus.SELECTED)), 1)

    def test_invalid_audit_line_raises_error(self):
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(
            "{invalid json}\n",
            encoding="utf-8",
        )

        with self.assertRaises(RuntimeAuditLogError):
            self.manager.get_records()

    def test_record_round_trip(self):
        original = self.make_result()
        self.manager.record(original)

        records = self.manager.get_records()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].runtime_id, original.runtime_id)
        self.assertEqual(records[0].status, original.status)

    def test_audit_records_are_json_lines(self):
        self.manager.record(self.make_result())
        self.manager.record(
            self.make_result(
                operation="select",
                status=RuntimeOperationStatus.SELECTED,
            )
        )

        lines = self.history_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["operation"], "stage")
        self.assertEqual(json.loads(lines[1])["operation"], "select")


if __name__ == "__main__":
    unittest.main()
