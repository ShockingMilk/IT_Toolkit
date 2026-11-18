import json
import re
from pathlib import Path

from it_toolkit.enums import DependencyType
from it_toolkit.models.package_manifest import (
    ManifestError,
    PackageEntry,
    PackageManifest,
)
from it_toolkit.models.repository_report import (
    PackageInspection,
    RepositoryInspection,
)
from it_toolkit.utils.checksum import verify_sha256


class RepositoryError(Exception):
    """Raised when an offline package repository cannot be inspected."""


_VERSION_PATTERN = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def _parse_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.match(value or "")

    if not match:
        raise ValueError(f"Invalid version value: {value!r}")

    parts = [
        int(part) if part is not None else 0
        for part in match.groups()
    ]

    return tuple(parts)


class DependencyManager:
    """
    Read-only manager for the local offline package repository.

    This manager does not install, remove, or modify packages.
    """

    MANIFEST_FILENAME = "manifest.json"

    def __init__(self, repository_path: Path):
        self.repository_path = Path(repository_path).resolve()
        self.manifest_path = (
            self.repository_path / self.MANIFEST_FILENAME
        )

    def load_manifest(self) -> PackageManifest:
        if not self.repository_path.is_dir():
            raise RepositoryError(
                f"Repository directory does not exist: {self.repository_path}"
            )

        if not self.manifest_path.is_file():
            raise RepositoryError(
                f"Repository manifest not found: {self.manifest_path}"
            )

        try:
            with self.manifest_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            return PackageManifest.from_dict(data)

        except (OSError, json.JSONDecodeError, ManifestError) as error:
            raise RepositoryError(
                f"Unable to load repository manifest: {error}"
            ) from error

    def _resolve_package_path(self, package: PackageEntry) -> Path:
        """
        Resolve a package path and ensure it remains inside the repository.

        The final resolved path check also prevents a symlink from escaping
        the repository directory.
        """

        candidate = (
            self.repository_path / Path(package.file)
        ).resolve()

        try:
            candidate.relative_to(self.repository_path)
        except ValueError as error:
            raise RepositoryError(
                f"Package path escapes repository: {package.file}"
            ) from error

        return candidate

    @staticmethod
    def _evaluate_compatibility(
        package: PackageEntry,
        profile,
    ) -> tuple[bool, list[str]]:
        issues = []

        operating_system = (
            profile.operating_system.family.value.lower()
        )

        architecture = (
            profile.operating_system.architecture.value.lower()
        )

        if operating_system not in package.operating_systems:
            issues.append(
                f"Unsupported operating system: {operating_system}"
            )

        if architecture not in package.architectures:
            issues.append(
                f"Unsupported architecture: {architecture}"
            )

        if package.dependency_type == DependencyType.PYTHON_MODULE:
            python_version = profile.python.version
            implementation = profile.python.implementation

            if not python_version:
                issues.append(
                    "Python version is unavailable for compatibility checking."
                )
            else:
                try:
                    current = _parse_version(python_version)

                    if package.python_min_version:
                        minimum = _parse_version(
                            package.python_min_version
                        )

                        if current < minimum:
                            issues.append(
                                "Python version is below the package minimum."
                            )

                    if package.python_max_version:
                        maximum = _parse_version(
                            package.python_max_version
                        )

                        if current > maximum:
                            issues.append(
                                "Python version exceeds the package maximum."
                            )

                except ValueError as error:
                    issues.append(str(error))

            if package.python_implementation:
                expected = package.python_implementation.lower()
                actual = (implementation or "").lower()

                if expected != actual:
                    issues.append(
                        "Python implementation mismatch: "
                        f"expected {expected}, found {actual or 'unknown'}."
                    )

        return not issues, issues

    def inspect_repository(self, profile=None) -> RepositoryInspection:
        """
        Inspect all package entries.

        When a SystemProfile is supplied, compatibility is evaluated.
        Without one, this performs repository integrity checks only.
        """

        manifest = self.load_manifest()

        report = RepositoryInspection(
            repository_name=manifest.repository_name,
            manifest_path=str(self.manifest_path),
        )

        for package in manifest.packages:
            package_path = self._resolve_package_path(package)

            inspection = PackageInspection(
                package_id=package.package_id,
                version=package.version,
                file_path=str(package_path),
                file_exists=package_path.is_file(),
            )

            if not inspection.file_exists:
                inspection.issues.append(
                    "Package file is missing."
                )
            else:
                try:
                    inspection.checksum_valid = verify_sha256(
                        package_path,
                        package.sha256,
                    )

                    if not inspection.checksum_valid:
                        inspection.issues.append(
                            "SHA-256 checksum mismatch."
                        )

                except OSError as error:
                    inspection.checksum_valid = False
                    inspection.issues.append(
                        f"Unable to read package file: {error}"
                    )

            if profile is not None:
                inspection.compatible, compatibility_issues = (
                    self._evaluate_compatibility(package, profile)
                )

                inspection.issues.extend(compatibility_issues)

            report.packages.append(inspection)

        return report