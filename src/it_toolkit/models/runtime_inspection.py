from dataclasses import dataclass, field


@dataclass
class RuntimeInspection:
    runtime_id: str
    runtime: str
    version: str
    archive_path: str
    archive_exists: bool
    checksum_valid: bool | None = None
    compatible: bool | None = None
    format_valid: bool | None = None
    issues: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        if not self.archive_exists:
            return False

        if self.checksum_valid is not True:
            return False

        if self.compatible is False:
            return False

        if self.format_valid is not True:
            return False

        return True

    def to_dict(self) -> dict:
        return {
            "runtime_id": self.runtime_id,
            "runtime": self.runtime,
            "version": self.version,
            "archive_path": self.archive_path,
            "archive_exists": self.archive_exists,
            "checksum_valid": self.checksum_valid,
            "compatible": self.compatible,
            "format_valid": self.format_valid,
            "valid": self.valid,
            "issues": list(self.issues),
        }


@dataclass
class RuntimeVerificationReport:
    repository_name: str
    manifest_path: str
    runtimes: list[RuntimeInspection] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return all(runtime.valid for runtime in self.runtimes)

    @property
    def runtime_count(self) -> int:
        return len(self.runtimes)

    @property
    def valid_runtime_count(self) -> int:
        return sum(runtime.valid for runtime in self.runtimes)

    def to_dict(self) -> dict:
        return {
            "repository_name": self.repository_name,
            "manifest_path": self.manifest_path,
            "valid": self.valid,
            "runtime_count": self.runtime_count,
            "valid_runtime_count": self.valid_runtime_count,
            "runtimes": [
                runtime.to_dict()
                for runtime in self.runtimes
            ],
        }
