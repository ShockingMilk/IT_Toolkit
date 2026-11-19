import os
import re
import shutil
import subprocess

from datetime import datetime, timezone
from pathlib import Path

from it_toolkit.enums import DependencyType, InstallationStatus
from it_toolkit.managers.dependency_manager import DependencyManager, RepositoryError
from it_toolkit.models.installation import InstallationResult


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


class PythonPackageInstaller:
    """
    Installs verified Python wheel packages into a managed directory.

    Installation is strictly local:
    - No package index access.
    - No dependency resolution.
    - No automatic installation.
    - No modification of system Python packages.
    """

    def __init__(
        self,
        repository_path: Path,
        installation_root: Path,
        timeout_seconds: int = 300,
        record_manager=None,
    ):
        self.repository = DependencyManager(repository_path)
        self.record_manager = record_manager

        self.installation_root = Path(
            installation_root
        ).resolve()

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero."
            )

        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_component(value: str) -> bool:
        return bool(
            isinstance(value, str)
            and _SAFE_COMPONENT.fullmatch(value)
            and value not in (".", "..")
        )

    def _result(
        self,
        package,
        status,
        source_path,
        destination_path,
        started_at,
        message,
        issues=None,
    ) -> InstallationResult:
        result = InstallationResult(
            package_id=package.package_id,
            package_name=package.name,
            version=package.version,
            dependency_type=package.dependency_type,
            status=status,
            source_path=str(source_path),
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

    @staticmethod
    def _installation_environment() -> dict:
        """
        Prevent inherited pip configuration from changing behavior.
        """

        environment = os.environ.copy()

        for key in list(environment):
            if key.upper().startswith("PIP_"):
                environment.pop(key)

        environment["PIP_CONFIG_FILE"] = os.devnull
        environment["PIP_NO_INDEX"] = "1"
        environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

        return environment

    @staticmethod
    def _remove_partial_installation(path: Path) -> None:
        """
        Remove only the destination created for this operation.
        """

        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    def install(
        self,
        package_id: str,
        version: str,
        profile,
        approved: bool = False,
    ) -> InstallationResult:
        """
        Install one explicitly approved Python wheel.

        The caller must explicitly set approved=True.
        """

        started_at = self._timestamp()

        manifest = self.repository.load_manifest()

        package = next(
            (
                item
                for item in manifest.packages
                if (
                    item.package_id == package_id
                    and item.version == version
                )
            ),
            None,
        )

        if package is None:
            raise RepositoryError(
                f"Package not found: {package_id} {version}"
            )

        if package.dependency_type != DependencyType.PYTHON_MODULE:
            return self._result(
                package,
                InstallationStatus.SKIPPED,
                package.file,
                None,
                started_at,
                "Package is not a Python module.",
            )

        if not package.file.lower().endswith(".whl"):
            return self._result(
                package,
                InstallationStatus.FAILED,
                package.file,
                None,
                started_at,
                "Only Python wheel files are supported.",
                ["Unsupported package format."],
            )

        if not approved:
            return self._result(
                package,
                InstallationStatus.SKIPPED,
                package.file,
                None,
                started_at,
                "Installation requires explicit approval.",
            )

        if not self._safe_component(package.package_id):
            return self._result(
                package,
                InstallationStatus.FAILED,
                package.file,
                None,
                started_at,
                "Unsafe package identifier.",
            )

        if not self._safe_component(package.version):
            return self._result(
                package,
                InstallationStatus.FAILED,
                package.file,
                None,
                started_at,
                "Unsafe package version.",
            )

        if not profile.python.installed:
            return self._result(
                package,
                InstallationStatus.FAILED,
                package.file,
                None,
                started_at,
                "A Python interpreter is not available.",
            )

        executable = profile.python.executable

        if not executable:
            return self._result(
                package,
                InstallationStatus.FAILED,
                package.file,
                None,
                started_at,
                "Python executable path is unavailable.",
            )

        python_executable = Path(executable).resolve()

        if not python_executable.is_file():
            return self._result(
                package,
                InstallationStatus.FAILED,
                package.file,
                None,
                started_at,
                "Python executable does not exist.",
                [str(python_executable)],
            )

        # Verify the complete repository entry against the supplied profile.
        try:
            inspection = self.repository.inspect_repository(
                profile
            )
        except RepositoryError:
            raise

        package_inspection = next(
            (
                item
                for item in inspection.packages
                if (
                    item.package_id == package.package_id
                    and item.version == package.version
                )
            ),
            None,
        )

        if package_inspection is None:
            return self._result(
                package,
                InstallationStatus.FAILED,
                package.file,
                None,
                started_at,
                "Package inspection result is unavailable.",
            )

        if not package_inspection.valid:
            return self._result(
                package,
                InstallationStatus.FAILED,
                package_inspection.file_path,
                None,
                started_at,
                "Package failed repository verification.",
                list(package_inspection.issues),
            )

        if package_inspection.compatible is not True:
            return self._result(
                package,
                InstallationStatus.FAILED,
                package_inspection.file_path,
                None,
                started_at,
                "Package is not compatible with this system.",
                list(package_inspection.issues),
            )

        source_path = Path(
            package_inspection.file_path
        ).resolve()

        destination = (
            self.installation_root
            / package.package_id
            / package.version
        )

        destination = destination.resolve()

        try:
            destination.relative_to(
                self.installation_root
            )
        except ValueError:
            return self._result(
                package,
                InstallationStatus.FAILED,
                source_path,
                None,
                started_at,
                "Installation destination escapes managed storage.",
            )

        if destination.exists():
            return self._result(
                package,
                InstallationStatus.SKIPPED,
                source_path,
                destination,
                started_at,
                "An installation already exists at this destination.",
            )

        command = [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--disable-pip-version-check",
            "--no-input",
            "--no-cache-dir",
            "--target",
            str(destination),
            str(source_path),
        ]

        try:
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
                env=self._installation_environment(),
            )

        except subprocess.TimeoutExpired:
            self._remove_partial_installation(destination)

            return self._result(
                package,
                InstallationStatus.FAILED,
                source_path,
                destination,
                started_at,
                "Package installation timed out.",
            )

        except OSError as error:
            self._remove_partial_installation(destination)

            return self._result(
                package,
                InstallationStatus.FAILED,
                source_path,
                destination,
                started_at,
                "Unable to start the Python package installer.",
                [str(error)],
            )

        if completed.returncode != 0:
            self._remove_partial_installation(destination)

            details = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or "pip returned a non-zero exit status."
            )

            return self._result(
                package,
                InstallationStatus.FAILED,
                source_path,
                destination,
                started_at,
                "Python package installation failed.",
                [details],
            )

        metadata_files = list(destination.glob("*.dist-info/METADATA"))

        if not destination.is_dir() or not metadata_files:
            self._remove_partial_installation(destination)

            return self._result(
                package,
                InstallationStatus.FAILED,
                source_path,
                destination,
                started_at,
                "Installation completed without verifiable package metadata.",
            )

        return self._result(
            package,
            InstallationStatus.INSTALLED,
            source_path,
            destination,
            started_at,
            "Python package installed successfully.",
        )