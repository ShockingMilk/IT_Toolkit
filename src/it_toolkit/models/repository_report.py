from dataclasses import dataclass, field


@dataclass
class PackageInspection:
    package_id: str
    version: str
    file_path: str
    file_exists: bool
    checksum_valid: bool | None = None
    compatible: bool | None = None
    issues: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        if not self.file_exists:
            return False

        if self.checksum_valid is False:
            return False

        if self.compatible is False:
            return False

        return True

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "version": self.version,
            "file_path": self.file_path,
            "file_exists": self.file_exists,
            "checksum_valid": self.checksum_valid,
            "compatible": self.compatible,
            "valid": self.valid,
            "issues": list(self.issues),
        }


@dataclass
class RepositoryInspection:
    repository_name: str
    manifest_path: str
    packages: list[PackageInspection] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return all(package.valid for package in self.packages)

    def to_dict(self) -> dict:
        return {
            "repository_name": self.repository_name,
            "manifest_path": self.manifest_path,
            "valid": self.valid,
            "package_count": len(self.packages),
            "valid_package_count": sum(
                package.valid for package in self.packages
            ),
            "packages": [
                package.to_dict()
                for package in self.packages
            ],
        }