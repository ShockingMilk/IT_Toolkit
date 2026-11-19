from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from it_toolkit.enums import DependencyType, InstallationStatus


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InstallationResult:
    """Describes the outcome of a package installation or staging operation."""

    package_id: str
    package_name: str
    version: str
    dependency_type: DependencyType
    status: InstallationStatus

    source_path: str
    destination_path: str | None = None
    sha256: str = ""

    started_at: str = field(default_factory=_utc_timestamp)
    completed_at: str = field(default_factory=_utc_timestamp)

    message: str = ""
    issues: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status in (
            InstallationStatus.INSTALLED,
            InstallationStatus.STAGED,
        )

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "version": self.version,
            "dependency_type": self.dependency_type.value,
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
class InstallationRecord:
    """Persistent audit record for an installation or staging operation."""

    package_id: str
    package_name: str
    version: str
    dependency_type: DependencyType
    status: InstallationStatus

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
    def from_result(
        cls,
        result: InstallationResult,
    ) -> "InstallationRecord":
        return cls(
            package_id=result.package_id,
            package_name=result.package_name,
            version=result.version,
            dependency_type=result.dependency_type,
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
    def from_dict(cls, data: dict) -> "InstallationRecord":
        """Reconstruct an audit record from saved JSON data."""

        if not isinstance(data, dict):
            raise ValueError("Installation record must be an object.")

        required = (
            "record_id",
            "recorded_at",
            "package_id",
            "package_name",
            "version",
            "dependency_type",
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
            raise ValueError(
                "Installation record is missing fields: "
                + ", ".join(missing)
            )

        if not isinstance(data["issues"], list) or not all(isinstance(item, str) for item in data["issues"]):
            raise ValueError("Installation record issues must be a list of strings.")

        string_fields = (
            "record_id",
            "recorded_at",
            "package_id",
            "package_name",
            "version",
            "source_path",
            "sha256",
            "started_at",
            "completed_at",
            "message",
        )

        for key in string_fields:
            if not isinstance(data[key], str):
                raise ValueError(f"Installation record field {key!r} must be a string.")

        destination = data["destination_path"]

        if destination is not None and not isinstance(destination, str):
            raise ValueError("Installation record destination_path must be a string or null.")

        return cls(
            record_id=data["record_id"],
            recorded_at=data["recorded_at"],
            package_id=data["package_id"],
            package_name=data["package_name"],
            version=data["version"],
            dependency_type=DependencyType(data["dependency_type"]),
            status=InstallationStatus(data["status"]),
            source_path=data["source_path"],
            destination_path=destination,
            sha256=data["sha256"],
            started_at=data["started_at"],
            completed_at=data["completed_at"],
            message=data["message"],
            issues=list(data["issues"]),
        )

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "recorded_at": self.recorded_at,
            "package_id": self.package_id,
            "package_name": self.package_name,
            "version": self.version,
            "dependency_type": self.dependency_type.value,
            "status": self.status.value,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "sha256": self.sha256,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "message": self.message,
            "issues": list(self.issues),
        }