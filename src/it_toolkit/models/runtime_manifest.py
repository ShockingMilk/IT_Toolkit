import re

from dataclasses import dataclass
from pathlib import PurePosixPath

from it_toolkit.enums import Architecture, OperatingSystem, Runtime, RuntimeArchiveFormat


_SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


class RuntimeManifestError(ValueError):
    """Raised when portable runtime manifest data is invalid."""


def _validate_relative_path(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeManifestError(f"{field_name} must be a non-empty relative path.")

    path = PurePosixPath(value)

    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or "\x00" in value
        or _WINDOWS_DRIVE_PATTERN.match(value)
    ):
        raise RuntimeManifestError(f"Unsafe {field_name}: {value!r}")

    return value


@dataclass(frozen=True)
class RuntimePackageEntry:
    runtime_id: str
    runtime: Runtime
    version: str
    archive: str
    archive_format: RuntimeArchiveFormat
    sha256: str
    operating_systems: tuple[str, ...]
    architectures: tuple[str, ...]
    executable: str
    python_implementation: str | None = None
    powershell_edition: str | None = None
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "RuntimePackageEntry":
        if not isinstance(data, dict):
            raise RuntimeManifestError("Each runtime entry must be an object.")

        required = (
            "runtime_id",
            "runtime",
            "version",
            "archive",
            "archive_format",
            "sha256",
            "operating_systems",
            "architectures",
            "executable",
        )

        missing = [field_name for field_name in required if field_name not in data]

        if missing:
            raise RuntimeManifestError("Runtime entry is missing fields: " + ", ".join(missing))

        runtime_id = data["runtime_id"]
        version = data["version"]

        if not isinstance(runtime_id, str) or not _SAFE_ID_PATTERN.fullmatch(runtime_id):
            raise RuntimeManifestError(f"Invalid runtime_id: {runtime_id!r}")

        if not isinstance(version, str) or not version.strip():
            raise RuntimeManifestError("Runtime version must be a non-empty string.")

        try:
            runtime = Runtime(data["runtime"])
        except (ValueError, TypeError) as error:
            raise RuntimeManifestError(f"Unsupported runtime type: {data['runtime']!r}") from error

        if runtime not in (Runtime.PYTHON, Runtime.POWERSHELL):
            raise RuntimeManifestError("Only Python and PowerShell portable runtimes are currently supported.")

        try:
            archive_format = RuntimeArchiveFormat(data["archive_format"])
        except (ValueError, TypeError) as error:
            raise RuntimeManifestError(f"Unsupported runtime archive format: {data['archive_format']!r}") from error

        archive = _validate_relative_path(
            data["archive"],
            "archive",
        )
        executable = _validate_relative_path(
            data["executable"],
            "executable",
        )

        checksum = data["sha256"]

        if not isinstance(checksum, str) or not _SHA256_PATTERN.fullmatch(checksum):
            raise RuntimeManifestError(f"Runtime '{runtime_id}' has an invalid SHA-256 checksum.")

        operating_systems = data["operating_systems"]
        architectures = data["architectures"]

        if not isinstance(operating_systems, list) or not operating_systems:
            raise RuntimeManifestError("operating_systems must be a non-empty list.")

        if not isinstance(architectures, list) or not architectures:
            raise RuntimeManifestError("architectures must be a non-empty list.")

        valid_os = {item.value for item in OperatingSystem}
        valid_architectures = {
            item.value for item in Architecture
        }

        normalized_os = []
        for item in operating_systems:
            if not isinstance(item, str) or item.lower() not in valid_os:
                raise RuntimeManifestError(f"Unsupported operating system: {item!r}")
            normalized_os.append(item.lower())

        normalized_architectures = []
        for item in architectures:
            if not isinstance(item, str) or item.lower() not in valid_architectures:
                raise RuntimeManifestError(f"Unsupported architecture: {item!r}")
            normalized_architectures.append(item.lower())

        optional_fields = (
            "python_implementation",
            "powershell_edition",
            "description",
        )

        for field_name in optional_fields:
            value = data.get(field_name)
            if value is not None and not isinstance(value, str):
                raise RuntimeManifestError(f"{field_name} must be a string or null.")

        if runtime == Runtime.PYTHON and data.get("powershell_edition") is not None:
            raise RuntimeManifestError("Python entries cannot define powershell_edition.")

        if runtime == Runtime.POWERSHELL and data.get("python_implementation") is not None:
            raise RuntimeManifestError("PowerShell entries cannot define python_implementation.")

        return cls(
            runtime_id=runtime_id,
            runtime=runtime,
            version=version.strip(),
            archive=archive,
            archive_format=archive_format,
            sha256=checksum.lower(),
            operating_systems=tuple(normalized_os),
            architectures=tuple(normalized_architectures),
            executable=executable,
            python_implementation=data.get("python_implementation"),
            powershell_edition=data.get("powershell_edition"),
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class RuntimeManifest:
    manifest_version: int
    repository_name: str
    runtimes: tuple[RuntimePackageEntry, ...]

    @classmethod
    def from_dict(cls, data: dict) -> "RuntimeManifest":
        if not isinstance(data, dict):
            raise RuntimeManifestError("Runtime manifest root must be an object.")

        manifest_version = data.get("manifest_version")

        if not isinstance(manifest_version, int) or isinstance(manifest_version, bool) or manifest_version != 1:
            raise RuntimeManifestError(f"Unsupported runtime manifest version: {manifest_version!r}")

        repository_name = data.get("repository_name")

        if not isinstance(repository_name, str) or not repository_name.strip():
            raise RuntimeManifestError("repository_name must be a non-empty string.")

        raw_runtimes = data.get("runtimes")

        if not isinstance(raw_runtimes, list):
            raise RuntimeManifestError("Runtime manifest runtimes must be a list.")

        runtimes = tuple(
            RuntimePackageEntry.from_dict(item)
            for item in raw_runtimes
        )

        seen = set()

        for entry in runtimes:
            identity = (entry.runtime_id, entry.version)

            if identity in seen:
                raise RuntimeManifestError(f"Duplicate runtime/version entry: {entry.runtime_id} {entry.version}")

            seen.add(identity)

        return cls(
            manifest_version=manifest_version,
            repository_name=repository_name.strip(),
            runtimes=runtimes,
        )
