from dataclasses import dataclass
import re
from pathlib import PurePosixPath

from it_toolkit.enums import DependencyType


_SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


class ManifestError(ValueError):
    """Raised when package manifest data is invalid."""


@dataclass(frozen=True)
class PackageEntry:
    package_id: str
    name: str
    version: str
    dependency_type: DependencyType
    file: str
    sha256: str
    operating_systems: tuple[str, ...]
    architectures: tuple[str, ...]
    python_min_version: str | None = None
    python_max_version: str | None = None
    python_implementation: str | None = None
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PackageEntry":
        if not isinstance(data, dict):
            raise ManifestError("Each package entry must be an object.")

        required = (
            "package_id",
            "name",
            "version",
            "type",
            "file",
            "sha256",
            "operating_systems",
            "architectures",
        )

        for field_name in required:
            if field_name not in data:
                raise ManifestError(
                    f"Package entry is missing '{field_name}'."
                )

        for field_name in ("package_id", "name", "version"):
            value = data[field_name]

            if not isinstance(value, str) or not value.strip():
                raise ManifestError(
                    f"Package field '{field_name}' must be a non-empty string."
                )

        try:
            dependency_type = DependencyType(data["type"])
        except (ValueError, TypeError) as error:
            raise ManifestError(
                f"Unsupported dependency type: {data['type']!r}"
            ) from error

        file_name = data["file"]

        if not isinstance(file_name, str) or not file_name.strip():
            raise ManifestError("Package file must be a non-empty string.")

        # Repository paths use POSIX separators on every platform.
        # Reject absolute paths, parent traversal, and Windows separators.
        relative_path = PurePosixPath(file_name)

        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or "\\" in file_name
        ):
            raise ManifestError(
                f"Unsafe package file path: {file_name!r}"
            )

        checksum = data["sha256"]

        if not isinstance(checksum, str) or not _SHA256_PATTERN.fullmatch(checksum):
            raise ManifestError(
                f"Package '{data['package_id']}' has an invalid SHA-256 checksum."
            )

        operating_systems = data["operating_systems"]
        architectures = data["architectures"]

        if not isinstance(operating_systems, list) or not operating_systems:
            raise ManifestError(
                "operating_systems must be a non-empty list."
            )

        if not isinstance(architectures, list) or not architectures:
            raise ManifestError(
                "architectures must be a non-empty list."
            )

        if not all(
            isinstance(item, str) and item.strip()
            for item in operating_systems + architectures
        ):
            raise ManifestError(
                "Operating systems and architectures must contain strings."
            )

        optional_string_fields = (
            "python_min_version",
            "python_max_version",
            "python_implementation",
            "description",
        )

        for field_name in optional_string_fields:
            value = data.get(field_name)

            if value is not None and not isinstance(value, str):
                raise ManifestError(
                    f"'{field_name}' must be a string or null."
                )

        return cls(
            package_id=data["package_id"].strip(),
            name=data["name"].strip(),
            version=data["version"].strip(),
            dependency_type=dependency_type,
            file=file_name,
            sha256=checksum.lower(),
            operating_systems=tuple(
                item.lower() for item in operating_systems
            ),
            architectures=tuple(
                item.lower() for item in architectures
            ),
            python_min_version=data.get("python_min_version"),
            python_max_version=data.get("python_max_version"),
            python_implementation=data.get("python_implementation"),
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class PackageManifest:
    manifest_version: int
    repository_name: str
    packages: tuple[PackageEntry, ...]

    @classmethod
    def from_dict(cls, data: dict) -> "PackageManifest":
        if not isinstance(data, dict):
            raise ManifestError("Manifest root must be an object.")

        manifest_version = data.get("manifest_version")

        if manifest_version != 1:
            raise ManifestError(
                f"Unsupported manifest version: {manifest_version!r}"
            )

        repository_name = data.get("repository_name")

        if not isinstance(repository_name, str) or not repository_name.strip():
            raise ManifestError(
                "repository_name must be a non-empty string."
            )

        raw_packages = data.get("packages")

        if not isinstance(raw_packages, list):
            raise ManifestError("Manifest packages must be a list.")

        packages = tuple(
            PackageEntry.from_dict(item)
            for item in raw_packages
        )

        seen = set()

        for package in packages:
            identity = (package.package_id, package.version)

            if identity in seen:
                raise ManifestError(
                    "Duplicate package/version entry: "
                    f"{package.package_id} {package.version}"
                )

            seen.add(identity)

        return cls(
            manifest_version=manifest_version,
            repository_name=repository_name.strip(),
            packages=packages,
        )