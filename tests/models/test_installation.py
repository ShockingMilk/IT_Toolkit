import unittest

from it_toolkit.enums import DependencyType, InstallationStatus
from it_toolkit.models.installation import InstallationRecord, InstallationResult


class InstallationModelTests(unittest.TestCase):

    def make_result(
        self,
        status=InstallationStatus.INSTALLED,
    ):
        return InstallationResult(
            package_id="example.package",
            package_name="Example Package",
            version="1.0.0",
            dependency_type=DependencyType.PYTHON_MODULE,
            status=status,
            source_path="packages/example.whl",
            destination_path="managed/python",
            sha256="a" * 64,
            message="Test installation",
        )

    def test_successful_installation(self):
        result = self.make_result()

        self.assertTrue(result.success)
        self.assertEqual(
            result.status,
            InstallationStatus.INSTALLED,
        )

    def test_successful_staging(self):
        result = self.make_result(InstallationStatus.STAGED)

        self.assertTrue(result.success)

    def test_failed_installation(self):
        result = self.make_result(InstallationStatus.FAILED)

        self.assertFalse(result.success)

    def test_skipped_installation(self):
        result = self.make_result(InstallationStatus.SKIPPED)

        self.assertFalse(result.success)

    def test_result_serialization(self):
        result = self.make_result()
        data = result.to_dict()

        self.assertEqual(
            data["package_id"],
            "example.package",
        )

        self.assertEqual(
            data["dependency_type"],
            "python_module",
        )

        self.assertEqual(
            data["status"],
            "installed",
        )

        self.assertTrue(data["success"])

    def test_record_created_from_result(self):
        result = self.make_result()

        record = InstallationRecord.from_result(result)

        self.assertEqual(
            record.package_id,
            result.package_id,
        )

        self.assertEqual(
            record.version,
            result.version,
        )

        self.assertEqual(
            record.status,
            result.status,
        )

    def test_records_have_unique_ids(self):
        first = InstallationRecord.from_result(self.make_result())

        second = InstallationRecord.from_result(self.make_result())

        self.assertNotEqual(
            first.record_id,
            second.record_id,
        )

    def test_record_serialization(self):
        record = InstallationRecord.from_result(self.make_result())

        data = record.to_dict()

        self.assertIn("record_id", data)
        self.assertIn("recorded_at", data)
        self.assertEqual(
            data["package_id"],
            "example.package",
        )

    def test_issues_are_preserved(self):
        result = self.make_result(InstallationStatus.FAILED)

        result.issues.append("Package checksum verification failed.")

        record = InstallationRecord.from_result(result)

        self.assertEqual(
            record.issues,
            result.issues,
        )


if __name__ == "__main__":
    unittest.main()