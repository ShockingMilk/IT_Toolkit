import json
import tempfile
import unittest

from pathlib import Path

from it_toolkit.enums import DependencyType, InstallationStatus
from it_toolkit.managers.installation_record_manager import (
    AuditLogError,
    InstallationRecordManager,
)
from it_toolkit.models.installation import InstallationResult


class InstallationRecordManagerTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.history_path = (
            self.root / "reports" / "installations.jsonl"
        )

        self.manager = InstallationRecordManager(
            self.history_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def make_result(
        package_id="sample.package",
        status=InstallationStatus.INSTALLED,
    ):
        return InstallationResult(
            package_id=package_id,
            package_name="Sample Package",
            version="1.0.0",
            dependency_type=DependencyType.PYTHON_MODULE,
            status=status,
            source_path="/repository/sample.whl",
            destination_path="/managed/sample/1.0.0",
            sha256="a" * 64,
            message="Test operation",
        )

    def test_record_creates_history_file(self):
        result = self.make_result()

        record = self.manager.record(result)

        self.assertTrue(self.history_path.is_file())
        self.assertEqual(record.package_id, result.package_id)

    def test_record_can_be_loaded_again(self):
        result = self.make_result()

        saved = self.manager.record(result)
        loaded = self.manager.get_records()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].record_id, saved.record_id)
        self.assertEqual(loaded[0].package_id, result.package_id)
        self.assertEqual(loaded[0].status, result.status)
        self.assertEqual(loaded[0].sha256, result.sha256)

    def test_multiple_records_are_preserved(self):
        first = self.make_result("first.package")
        second = self.make_result(
            "second.package",
            InstallationStatus.FAILED,
        )

        self.manager.record(first)
        self.manager.record(second)

        records = self.manager.get_records()

        self.assertEqual(len(records), 2)
        self.assertEqual(
            [record.package_id for record in records],
            ["first.package", "second.package"],
        )

    def test_records_can_be_filtered_by_package(self):
        self.manager.record(self.make_result("first.package"))
        self.manager.record(self.make_result("second.package"))

        records = self.manager.get_records(
            package_id="second.package"
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].package_id, "second.package")

    def test_records_can_be_filtered_by_status(self):
        self.manager.record(
            self.make_result(status=InstallationStatus.INSTALLED)
        )
        self.manager.record(
            self.make_result(
                "failed.package",
                InstallationStatus.FAILED,
            )
        )

        records = self.manager.get_records(
            status=InstallationStatus.FAILED
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0].status,
            InstallationStatus.FAILED,
        )

    def test_missing_history_returns_empty_list(self):
        self.assertEqual(self.manager.get_records(), [])
        self.assertEqual(self.manager.count(), 0)

    def test_count_returns_number_of_records(self):
        self.manager.record(self.make_result("first.package"))
        self.manager.record(self.make_result("second.package"))

        self.assertEqual(self.manager.count(), 2)

    def test_corrupt_history_raises_error(self):
        self.history_path.parent.mkdir(parents=True)
        self.history_path.write_text(
            "{invalid json}\n",
            encoding="utf-8",
        )

        with self.assertRaises(AuditLogError):
            self.manager.get_records()

    def test_invalid_record_type_is_rejected(self):
        with self.assertRaises(TypeError):
            self.manager.record({"package_id": "not-a-result"})

    def test_saved_records_are_independent_json_lines(self):
        self.manager.record(self.make_result("first.package"))
        self.manager.record(self.make_result("second.package"))

        lines = self.history_path.read_text(
            encoding="utf-8"
        ).splitlines()

        self.assertEqual(len(lines), 2)

        for line in lines:
            self.assertIsInstance(json.loads(line), dict)


if __name__ == "__main__":
    unittest.main()