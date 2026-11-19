import json
import os

from pathlib import Path

from it_toolkit.enums import InstallationStatus
from it_toolkit.models.installation import InstallationRecord, InstallationResult


class AuditLogError(Exception):
    """Raised when installation audit history cannot be read or written."""


class InstallationRecordManager:
    """
    Persistent JSON Lines audit history for package operations.

    Each operation is stored as an independent JSON object on one line.
    Existing records are never silently replaced.
    """

    def __init__(self, history_path: Path):
        self.history_path = Path(history_path)

    def record(
        self,
        result: InstallationResult,
    ) -> InstallationRecord:
        """Persist an installation or staging result."""

        if not isinstance(result, InstallationResult):
            raise TypeError("record() requires an InstallationResult.")

        record = InstallationRecord.from_result(result)

        try:
            self.history_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            serialized = json.dumps(
                record.to_dict(),
                sort_keys=True,
                ensure_ascii=False,
            )

            with self.history_path.open("a", encoding="utf-8", newline="\n") as history_file:
                history_file.write(serialized + "\n")
                history_file.flush()
                os.fsync(history_file.fileno())

        except (OSError, TypeError, ValueError) as error:
            raise AuditLogError(f"Unable to write installation audit history: {error}") from error

        return record

    def get_records(
        self,
        package_id: str | None = None,
        status: InstallationStatus | None = None,
    ) -> list[InstallationRecord]:
        """Load audit records, optionally filtering the results."""

        if not self.history_path.exists():
            return []

        records = []

        try:
            with self.history_path.open("r", encoding="utf-8",) as history_file:
                for line_number, line in enumerate(history_file, start=1):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                        record = InstallationRecord.from_dict(data)

                    except (json.JSONDecodeError, ValueError, TypeError) as error:
                        raise AuditLogError(f"Invalid audit record at line {line_number}: {error}") from error

                    if package_id is not None and record.package_id != package_id:
                        continue

                    if status is not None and record.status != status:
                        continue

                    records.append(record)

        except OSError as error:
            raise AuditLogError(f"Unable to read installation audit history: {error}") from error

        return records

    def count(self) -> int:
        """Return the number of valid records in the history."""

        return len(self.get_records())