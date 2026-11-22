import tarfile
import zipfile

from pathlib import Path

from it_toolkit.enums import RuntimeArchiveFormat
from it_toolkit.managers.runtime_catalog_manager import RuntimeCatalogManager, RuntimeRepositoryError
from it_toolkit.models.runtime_inspection import RuntimeInspection, RuntimeVerificationReport
from it_toolkit.utils.checksum import calculate_sha256


class RuntimeVerifier:
    """
    Verify local portable runtime archives.

    This manager is read-only. It does not extract, execute,
    install, or modify runtime archives.
    """

    def __init__(self, repository_path: Path):
        self.catalog = RuntimeCatalogManager(repository_path)
        self.repository_path = Path(repository_path).resolve()

    @staticmethod
    def _profile_value(value) -> str | None:
        if value is None:
            return None

        return str(getattr(value, "value", value)).lower()

    @staticmethod
    def _detect_archive_format(path: Path):
        """
        Detect the actual archive format using standard-library readers.

        Returns a RuntimeArchiveFormat or None if the archive is
        unsupported or invalid.
        """
        if not path.is_file():
            return None

        if zipfile.is_zipfile(path):
            return RuntimeArchiveFormat.ZIP

        try:
            with path.open("rb") as archive_file:
                signature = archive_file.read(8)
        except OSError:
            return None

        # Compression signatures are checked before generic TAR.
        if signature.startswith(b"\x1f\x8b"):
            try:
                with tarfile.open(path, mode="r:gz"):
                    return RuntimeArchiveFormat.TAR_GZ
            except (tarfile.TarError, OSError):
                return None

        if signature.startswith(b"\xfd7zXZ\x00"):
            try:
                with tarfile.open(path, mode="r:xz"):
                    return RuntimeArchiveFormat.TAR_XZ
            except (tarfile.TarError, OSError):
                return None

        if signature.startswith(b"BZh"):
            try:
                with tarfile.open(path, mode="r:bz2"):
                    return RuntimeArchiveFormat.TAR_BZ2
            except (tarfile.TarError, OSError):
                return None

        try:
            with tarfile.open(path, mode="r:"):
                return RuntimeArchiveFormat.TAR
        except (tarfile.TarError, OSError):
            return None

    @staticmethod
    def _check_compatibility(entry, profile) -> tuple[bool, list[str]]:
        issues = []

        if profile is None:
            return True, issues

        operating_system = RuntimeVerifier._profile_value(
            getattr(
                getattr(profile, "operating_system", None),
                "family",
                None,
            )
        )

        architecture = RuntimeVerifier._profile_value(
            getattr(
                getattr(profile, "operating_system", None),
                "architecture",
                None,
            )
        )

        compatible = True

        if operating_system is None:
            compatible = False
            issues.append(
                "Unable to determine the host operating system."
            )
        elif operating_system not in entry.operating_systems:
            compatible = False
            issues.append(
                f"Unsupported operating system: {operating_system}"
            )

        if architecture is None:
            compatible = False
            issues.append(
                "Unable to determine the host architecture."
            )
        elif architecture not in entry.architectures:
            compatible = False
            issues.append(
                f"Unsupported architecture: {architecture}"
            )

        return compatible, issues

    def verify_runtime(
        self,
        runtime_id: str,
        version: str,
        profile=None,
    ) -> RuntimeInspection:
        """Verify one exact runtime archive."""

        entry = self.catalog.get_runtime(
            runtime_id,
            version,
        )

        issues = []

        try:
            archive_path = self.catalog.resolve_archive_path(entry)
        except RuntimeRepositoryError as error:
            return RuntimeInspection(
                runtime_id=entry.runtime_id,
                runtime=entry.runtime.value,
                version=entry.version,
                archive_path=str(self.repository_path / entry.archive),
                archive_exists=False,
                issues=[str(error)],
            )

        if not archive_path.is_file():
            return RuntimeInspection(
                runtime_id=entry.runtime_id,
                runtime=entry.runtime.value,
                version=entry.version,
                archive_path=str(archive_path),
                archive_exists=False,
                checksum_valid=False,
                compatible=None,
                format_valid=False,
                issues=["Runtime archive is missing."],
            )

        try:
            checksum_valid = calculate_sha256(archive_path) == entry.sha256
        except OSError as error:
            checksum_valid = False
            issues.append(
                f"Unable to calculate archive checksum: {error}"
            )

        if not checksum_valid and not issues:
            issues.append(
                "Runtime archive SHA-256 does not match the manifest."
            )

        compatible, compatibility_issues = self._check_compatibility(entry, profile)
        issues.extend(compatibility_issues)

        actual_format = self._detect_archive_format(
            archive_path
        )

        format_valid = actual_format == entry.archive_format

        if actual_format is None:
            issues.append(
                "Archive is invalid or uses an unsupported format."
            )
        elif not format_valid:
            issues.append(
                "Archive format mismatch: "
                f"manifest declares {entry.archive_format.value}, "
                f"but archive is {actual_format.value}."
            )

        return RuntimeInspection(
            runtime_id=entry.runtime_id,
            runtime=entry.runtime.value,
            version=entry.version,
            archive_path=str(archive_path),
            archive_exists=True,
            checksum_valid=checksum_valid,
            compatible=compatible,
            format_valid=format_valid,
            issues=issues,
        )

    def verify_repository(self, profile=None):
        """Verify every runtime listed in the local manifest."""

        manifest = self.catalog.load_manifest()
        inspections = []

        for entry in manifest.runtimes:
            inspection = self.verify_runtime(
                entry.runtime_id,
                entry.version,
                profile,
            )
            inspections.append(inspection)

        return RuntimeVerificationReport(
            repository_name=manifest.repository_name,
            manifest_path=str(self.catalog.manifest_path),
            runtimes=inspections,
        )