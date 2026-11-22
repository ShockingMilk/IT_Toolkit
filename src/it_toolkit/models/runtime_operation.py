from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from it_toolkit.enums import RuntimeOperationStatus


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RuntimeOperationResult:
    """Describes a runtime staging or selection operation."""

    operation: str
    runtime_id: str
    runtime: str
    version: str
    status: RuntimeOperationStatus

    source_path: str = ""
    destination_path: str | None = None
    sha256: str = ""

    started_at: str = field(default_factory=_utc_timestamp)
    completed_at: str = field(default_factory=_utc_timestamp)

    message: str = ""
    issues: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status in (
            RuntimeOperationStatus.STAGED,
            RuntimeOperationStatus.SELECTED,
            RuntimeOperationStatus.EXECUTED,
        )

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "runtime_id": self.runtime_id,
            "runtime": self.runtime,
            "version": self.version,
            "status": self.status.value,
            "success": self.success,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "sha256": self.sha256,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "message": self.message,
            "issues": list(self.issues),
        }


@dataclass
class RuntimeOperationRecord:
    """Persistent audit record for a runtime operation."""

    operation: str
    runtime_id: str
    runtime: str
    version: str
    status: RuntimeOperationStatus

    source_path: str
    destination_path: str | None
    sha256: str

    started_at: str
    completed_at: str

    message: str = ""
    issues: list[str] = field(default_factory=list)

    record_id: str = field(default_factory=lambda: uuid4().hex)
    recorded_at: str = field(default_factory=_utc_timestamp)

    @classmethod
    def from_result(cls, result: RuntimeOperationResult) -> "RuntimeOperationRecord":
        return cls(
            operation=result.operation,
            runtime_id=result.runtime_id,
            runtime=result.runtime,
            version=result.version,
            status=result.status,
            source_path=result.source_path,
            destination_path=result.destination_path,
            sha256=result.sha256,
            started_at=result.started_at,
            completed_at=result.completed_at,
            message=result.message,
            issues=list(result.issues),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "RuntimeOperationRecord":
        if not isinstance(data, dict):
            raise ValueError("Runtime operation record must be an object.")

        required = (
            "record_id",
            "recorded_at",
            "operation",
            "runtime_id",
            "runtime",
            "version",
            "status",
            "source_path",
            "destination_path",
            "sha256",
            "started_at",
            "completed_at",
            "message",
            "issues",
        )

        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError("Runtime operation record is missing fields: " + ", ".join(missing))

        string_fields = (
            "record_id",
            "recorded_at",
            "operation",
            "runtime_id",
            "runtime",
            "version",
            "source_path",
            "sha256",
            "started_at",
            "completed_at",
            "message",
        )

        for key in string_fields:
            if not isinstance(data[key], str):
                raise ValueError(f"Runtime operation field {key!r} must be a string.")

        destination = data["destination_path"]
        if destination is not None and not isinstance(destination, str):
            raise ValueError("Runtime operation destination_path must be a string or null.")

        issues = data["issues"]
        if not isinstance(issues, list) or not all(isinstance(item, str) for item in issues):
            raise ValueError("Runtime operation issues must be a list of strings.")

        return cls(
            record_id=data["record_id"],
            recorded_at=data["recorded_at"],
            operation=data["operation"],
            runtime_id=data["runtime_id"],
            runtime=data["runtime"],
            version=data["version"],
            status=RuntimeOperationStatus(data["status"]),
            source_path=data["source_path"],
            destination_path=destination,
            sha256=data["sha256"],
            started_at=data["started_at"],
            completed_at=data["completed_at"],
            message=data["message"],
            issues=list(issues),
        )

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "recorded_at": self.recorded_at,
            "operation": self.operation,
            "runtime_id": self.runtime_id,
            "runtime": self.runtime,
            "version": self.version,
            "status": self.status.value,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "sha256": self.sha256,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "message": self.message,
            "issues": list(self.issues),
        }
