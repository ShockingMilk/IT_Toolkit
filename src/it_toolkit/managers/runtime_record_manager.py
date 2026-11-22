import json
import os

from pathlib import Path

from it_toolkit.enums import RuntimeOperationStatus
from it_toolkit.models.runtime_operation import RuntimeOperationRecord, RuntimeOperationResult


class RuntimeAuditLogError(Exception):
    """Raised when runtime audit history cannot be read or written."""


class RuntimeRecordManager:
    """Persistent JSON Lines audit history for runtime operations."""

    def __init__(self, history_path: Path):
        self.history_path = Path(history_path)

    def record(self, result: RuntimeOperationResult,) -> RuntimeOperationRecord:
        if not isinstance(result, RuntimeOperationResult):
            raise TypeError("record() requires a RuntimeOperationResult.")

        record = RuntimeOperationRecord.from_result(result)

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
            raise RuntimeAuditLogError(f"Unable to write runtime audit history: {error}") from error

        return record

    def get_records(
        self,
        runtime_id: str | None = None,
        operation: str | None = None,
        status: RuntimeOperationStatus | None = None,
    ) -> list[RuntimeOperationRecord]:
        if not self.history_path.exists():
            return []

        records = []

        try:
            with self.history_path.open("r", encoding="utf-8") as history_file:
                for line_number, line in enumerate(history_file, start=1):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                        record = RuntimeOperationRecord.from_dict(data)

                    except (json.JSONDecodeError, ValueError, TypeError) as error:
                        raise RuntimeAuditLogError(f"Invalid runtime audit record at line {line_number}: {error}") from error

                    if runtime_id is not None and record.runtime_id != runtime_id:
                        continue

                    if operation is not None and record.operation != operation:
                        continue

                    if status is not None and record.status != status:
                        continue

                    records.append(record)

        except OSError as error:
            raise RuntimeAuditLogError(f"Unable to read runtime audit history: {error}") from error

        return records

    def count(self) -> int:
        return len(self.get_records())
