import os
import re
import shutil
import tempfile

from datetime import datetime, timezone
from pathlib import Path

from it_toolkit.enums import DependencyType, InstallationStatus
from it_toolkit.managers.dependency_manager import DependencyManager, RepositoryError
from it_toolkit.models.installation import InstallationResult


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ExecutableStager:
    """
    Verify and stage executable packages from a local offline repository.

    Staging copies the original package file into a managed directory.
    It never executes the staged file or modifies system locations.
    """

    def __init__(
        self,
        repository_path: Path,
        staging_root: Path,
        record_manager=None,
    ):
        self.repository_path = Path(repository_path).resolve()
        self.staging_root = Path(staging_root).resolve()
        self.dependency_manager = DependencyManager(self.repository_path)
        self.record_manager = record_manager

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_component(value: str, field_name: str) -> str:
        if (
            not isinstance(value, str)
            or not _SAFE_COMPONENT.fullmatch(value)
            or value in {".", ".."}
        ):
            raise ValueError(f"Unsafe {field_name}: {value!r}")

        return value

    @staticmethod
    def _find_package(manifest, package_id: str, version: str):
        for package in manifest.packages:
            if package.package_id == package_id and package.version == version:
                return package

        raise RepositoryError(f"Package not found: {package_id} {version}")

    def _result(
        self,
        package,
        status: InstallationStatus,
        started_at: str,
        message: str,
        source_path: Path | None = None,
        destination_path: Path | None = None,
        issues: list[str] | None = None,
    ) -> InstallationResult:
        result = InstallationResult(
            package_id=package.package_id,
            package_name=package.name,
            version=package.version,
            dependency_type=package.dependency_type,
            status=status,
            source_path=str(source_path or ""),
            destination_path=(
                str(destination_path)
                if destination_path is not None
                else None
            ),
            sha256=package.sha256,
            started_at=started_at,
            completed_at=self._timestamp(),
            message=message,
            issues=issues or [],
        )

        if self.record_manager is not None:
            self.record_manager.record(result)

        return result

    def stage(
        self,
        package_id: str,
        version: str,
        profile,
        approved: bool = False,
    ) -> InstallationResult:
        """
        Stage one verified executable package.

        `approved` must only be True after explicit user confirmation.
        The staged file is never executed by this method.
        """

        started_at = self._timestamp()
        manifest = self.dependency_manager.load_manifest()
        package = self._find_package(
            manifest,
            package_id,
            version,
        )

        if package.dependency_type != DependencyType.EXECUTABLE:
            return self._result(
                package,
                InstallationStatus.SKIPPED,
                started_at,
                "Package is not an executable package.",
            )

        if not approved:
            return self._result(
                package,
                InstallationStatus.SKIPPED,
                started_at,
                "Staging requires explicit approval.",
            )

        try:
            safe_package_id = self._safe_component(
                package.package_id,
                "package ID",
            )
            safe_version = self._safe_component(
                package.version,
                "package version",
            )
        except ValueError as error:
            return self._result(
                package,
                InstallationStatus.FAILED,
                started_at,
                "Package metadata contains an unsafe path component.",
                issues=[str(error)],
            )

        report = self.dependency_manager.inspect_repository(profile)
        inspection = next(
            (
                item
                for item in report.packages
                if (
                    item.package_id == package.package_id
                    and item.version == package.version
                )
            ),
            None,
        )

        if inspection is None:
            return self._result(
                package,
                InstallationStatus.FAILED,
                started_at,
                "Package inspection did not return the selected package.",
            )

        if not inspection.valid or inspection.compatible is not True:
            issues = list(inspection.issues)

            if inspection.compatible is not True and not issues:
                issues.append(
                    "Package compatibility could not be confirmed."
                )

            return self._result(
                package,
                InstallationStatus.FAILED,
                started_at,
                "Package failed integrity or compatibility checks.",
                source_path=Path(inspection.file_path),
                issues=issues,
            )

        source_path = Path(inspection.file_path).resolve()

        if not source_path.is_file():
            return self._result(
                package,
                InstallationStatus.FAILED,
                started_at,
                "Verified package file is no longer available.",
                source_path=source_path,
            )

        filename = source_path.name

        if not filename or filename in {".", ".."}:
            return self._result(
                package,
                InstallationStatus.FAILED,
                started_at,
                "Package filename is invalid.",
                source_path=source_path,
            )

        package_directory = (self.staging_root / safe_package_id / safe_version).resolve()

        try:
            package_directory.relative_to(self.staging_root)
        except ValueError:
            return self._result(
                package,
                InstallationStatus.FAILED,
                started_at,
                "Staging destination escapes the managed staging root.",
                source_path=source_path,
            )

        destination_path = package_directory / filename

        if destination_path.exists() or destination_path.is_symlink():
            return self._result(
                package,
                InstallationStatus.SKIPPED,
                started_at,
                "Destination already exists; existing files are never overwritten.",
                source_path=source_path,
                destination_path=destination_path,
            )

        try:
            package_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            # Re-check after directory creation in case the path was
            # replaced with a symlink between resolution and creation.
            resolved_directory = package_directory.resolve()
            resolved_directory.relative_to(self.staging_root)

            if destination_path.exists() or destination_path.is_symlink():
                return self._result(
                    package,
                    InstallationStatus.SKIPPED,
                    started_at,
                    "Destination already exists; existing files are never overwritten.",
                    source_path=source_path,
                    destination_path=destination_path,
                )

            # Create a temporary copy in the destination directory.
            # A hard link publishes it without replacing an existing file.
            temporary_path = None

            try:
                with tempfile.NamedTemporaryFile(
                    prefix=".staging-",
                    dir=resolved_directory,
                    delete=False,
                ) as temporary_file:
                    temporary_path = Path(temporary_file.name)

                shutil.copy2(source_path, temporary_path)

                # os.link fails if the destination already exists.
                # It therefore avoids silently replacing another file.
                os.link(temporary_path, destination_path)

            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

            return self._result(
                package,
                InstallationStatus.STAGED,
                started_at,
                "Executable package was verified and staged. It was not executed.",
                source_path=source_path,
                destination_path=destination_path,
            )

        except (OSError, ValueError) as error:
            # Remove only a destination created by this attempt.
            # Never remove a pre-existing file.
            return self._result(
                package,
                InstallationStatus.FAILED,
                started_at,
                "Unable to stage executable package.",
                source_path=source_path,
                destination_path=destination_path,
                issues=[str(error)],
            )