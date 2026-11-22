import json
import os
import re
import shutil
import stat
import tarfile
import tempfile
import zipfile

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from it_toolkit.enums import RuntimeOperationStatus
from it_toolkit.managers.runtime_catalog_manager import RuntimeCatalogManager, RuntimeRepositoryError
from it_toolkit.managers.runtime_verifier import RuntimeVerifier
from it_toolkit.models.runtime_operation import RuntimeOperationResult
from it_toolkit.utils.checksum import calculate_sha256


class RuntimeStagingError(Exception):
    """Raised when a portable runtime cannot be staged safely."""


class RuntimeStager:
    """
    Safely extracts verified portable runtimes into managed storage.

    Staging does not execute the runtime or modify system configuration.
    """

    METADATA_FILENAME = ".runtime-staged.json"

    def __init__(
        self,
        repository_path: Path,
        staging_root: Path,
        record_manager=None,
        max_files: int = 10000,
        max_file_size: int = 512 * 1024 * 1024,
        max_total_size: int = 2 * 1024 * 1024 * 1024,
    ):
        if max_files < 1 or max_file_size < 1 or max_total_size < 1:
            raise ValueError("Runtime staging limits must be positive.")

        self.repository_path = Path(repository_path)
        self.staging_root = Path(staging_root)
        self.record_manager = record_manager

        self.max_files = max_files
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size

        self.catalog = RuntimeCatalogManager(self.repository_path)
        self.verifier = RuntimeVerifier(self.repository_path)

    @staticmethod
    def _validate_component(value: str, label: str) -> str:
        if not isinstance(value, str) or not value:
            raise RuntimeStagingError(f"{label} must be a non-empty string.")

        if value in (".", "..") or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*",
            value,
        ):
            raise RuntimeStagingError(f"Unsafe {label}: {value!r}")

        return value

    @staticmethod
    def _safe_member_path(name: str) -> Path:
        if not isinstance(name, str) or not name or "\x00" in name:
            raise RuntimeStagingError("Archive contains an invalid member name.")

        if "\\" in name or name.startswith("/"):
            raise RuntimeStagingError(f"Archive contains an unsafe path: {name!r}")

        normalized = name[:-1] if name.endswith("/") else name

        if re.match(r"^[A-Za-z]:", normalized):
            raise RuntimeStagingError(f"Archive contains a drive-qualified path: {name!r}")

        parts = normalized.split("/")

        if not parts or any(part in ("", ".", "..") for part in parts):
            raise RuntimeStagingError(f"Archive contains an unsafe path: {name!r}")

        return Path(*parts)

    def _destination(
        self,
        runtime_id: str,
        version: str,
    ) -> tuple[Path, Path]:
        runtime_id = self._validate_component(runtime_id, "runtime ID")
        version = self._validate_component(version, "runtime version")

        self.staging_root.mkdir(parents=True, exist_ok=True)
        root = self.staging_root.resolve()

        parent = root / runtime_id
        parent.mkdir(parents=True, exist_ok=True)

        resolved_parent = parent.resolve()
        try:
            resolved_parent.relative_to(root)
        except ValueError as error:
            raise RuntimeStagingError("Runtime staging directory escapes the staging root.") from error

        destination = resolved_parent / version
        return resolved_parent, destination

    def _register_member(
        self,
        relative_path: Path,
        is_directory: bool,
        seen: dict[str, str],
    ) -> None:
        key = relative_path.as_posix().casefold()

        if key in seen:
            raise RuntimeStagingError(f"Archive contains a duplicate path: {relative_path}")

        # Prevent a file from being used as a parent directory.
        for parent in relative_path.parents:
            if parent == Path("."):
                continue
            parent_key = parent.as_posix().casefold()
            if seen.get(parent_key) == "file":
                raise RuntimeStagingError(f"Archive path conflicts with an existing file: {relative_path}")

        # Prevent replacing a directory that already has children with a file.
        if not is_directory:
            prefix = key + "/"
            if any(existing.startswith(prefix) for existing in seen):
                raise RuntimeStagingError(f"Archive file conflicts with an existing directory: {relative_path}")

        seen[key] = "directory" if is_directory else "file"

    def _prepare_member(
        self,
        name: str,
        is_directory: bool,
        seen: dict[str, str],
        member_count: int,
    ) -> Path:
        if member_count > self.max_files:
            raise RuntimeStagingError(f"Archive exceeds the {self.max_files}-member limit.")

        if name.endswith("/") and not is_directory:
            raise RuntimeStagingError(f"Archive file has a directory-style path: {name!r}")

        relative_path = self._safe_member_path(name)

        self._register_member(relative_path, is_directory, seen)
        return relative_path

    def _write_stream(
        self,
        source,
        target: Path,
        expected_size: int,
        total_written: int,
    ) -> int:
        if expected_size < 0 or expected_size > self.max_file_size:
            raise RuntimeStagingError(f"Archive member exceeds the per-file size limit: {target}")

        target.parent.mkdir(parents=True, exist_ok=True)

        written = 0

        try:
            with target.open("xb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break

                    written += len(chunk)

                    if written > expected_size:
                        raise RuntimeStagingError(f"Archive member expanded beyond its declared size: {target}")

                    if written > self.max_file_size:
                        raise RuntimeStagingError(f"Archive member exceeds the per-file size limit: {target}")

                    if total_written + written > self.max_total_size:
                        raise RuntimeStagingError("Archive exceeds the total extracted size limit.")

                    output.write(chunk)

        except Exception:
            target.unlink(missing_ok=True)
            raise

        if written != expected_size:
            target.unlink(missing_ok=True)
            raise RuntimeStagingError(f"Archive member size mismatch: {target}")

        return total_written + written

    @staticmethod
    def _safe_file_mode(mode: int) -> int:
        # Strip setuid, setgid, sticky, and other special permission bits.
        return stat.S_IMODE(mode) & 0o755

    def _extract_zip(self, archive: Path, destination: Path) -> None:
        seen = {}
        total_declared = 0
        total_written = 0

        with zipfile.ZipFile(archive, "r") as source:
            infos = source.infolist()

            if len(infos) > self.max_files:
                raise RuntimeStagingError(f"Archive exceeds the {self.max_files}-member limit.")

            prepared = []

            for info in infos:
                if info.flag_bits & 0x1:
                    raise RuntimeStagingError("Encrypted ZIP members are not supported.")

                is_directory = info.is_dir()
                relative = self._prepare_member(
                    info.filename,
                    is_directory,
                    seen,
                    len(prepared) + 1,
                )

                mode = info.external_attr >> 16
                file_type = stat.S_IFMT(mode)

                if file_type == stat.S_IFLNK:
                    raise RuntimeStagingError(f"ZIP symbolic links are not allowed: {info.filename}")

                if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise RuntimeStagingError(f"ZIP special files are not allowed: {info.filename}")

                if is_directory and info.file_size != 0:
                    raise RuntimeStagingError(f"ZIP directory has unexpected content: {info.filename}")

                if not is_directory:
                    if info.file_size > self.max_file_size:
                        raise RuntimeStagingError(f"ZIP member exceeds the per-file size limit: {info.filename}")

                    total_declared += info.file_size
                    if total_declared > self.max_total_size:
                        raise RuntimeStagingError("ZIP archive exceeds the total extracted size limit.")

                prepared.append((info, relative, is_directory, mode))

            for info, relative, is_directory, mode in prepared:
                target = destination / relative

                if is_directory:
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                with source.open(info, "r") as member:
                    total_written = self._write_stream(
                        member,
                        target,
                        info.file_size,
                        total_written,
                    )

                safe_mode = self._safe_file_mode(mode)
                if safe_mode:
                    target.chmod(safe_mode)

    def _extract_tar(self, archive: Path, destination: Path) -> None:
        seen = {}
        total_declared = 0
        total_written = 0

        with tarfile.open(archive, mode="r:*") as source:
            members = source.getmembers()

            if len(members) > self.max_files:
                raise RuntimeStagingError(f"Archive exceeds the {self.max_files}-member limit.")

            prepared = []

            for member in members:
                is_directory = member.isdir()

                if not (is_directory or member.isreg()):
                    raise RuntimeStagingError(f"TAR links and special files are not allowed: {member.name}")

                if getattr(member, "sparse", None):
                    raise RuntimeStagingError(f"Sparse TAR files are not supported: {member.name}")

                relative = self._prepare_member(
                    member.name,
                    is_directory,
                    seen,
                    len(prepared) + 1,
                )

                if not is_directory:
                    if member.size > self.max_file_size:
                        raise RuntimeStagingError(f"TAR member exceeds the per-file size limit: {member.name}")

                    total_declared += member.size
                    if total_declared > self.max_total_size:
                        raise RuntimeStagingError("TAR archive exceeds the total extracted size limit.")

                prepared.append((member, relative, is_directory))

            for member, relative, is_directory in prepared:
                target = destination / relative

                if is_directory:
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                stream = source.extractfile(member)
                if stream is None:
                    raise RuntimeStagingError(f"Unable to read TAR member: {member.name}")

                with stream:
                    total_written = self._write_stream(
                        stream,
                        target,
                        member.size,
                        total_written,
                    )

                safe_mode = self._safe_file_mode(member.mode)
                if safe_mode:
                    target.chmod(safe_mode)

    def _extract_archive(
        self,
        archive: Path,
        archive_format,
        destination: Path,
    ) -> None:
        format_value = getattr(archive_format, "value", archive_format)

        if format_value == "zip":
            self._extract_zip(archive, destination)
        elif format_value in ("tar", "tar.gz", "tar.xz", "tar.bz2"):
            self._extract_tar(archive, destination)
        else:
            raise RuntimeStagingError(f"Unsupported runtime archive format: {format_value}")

    @staticmethod
    def _validate_executable_path(value: str) -> Path:
        if not isinstance(value, str) or not value or "\x00" in value:
            raise RuntimeStagingError("Runtime manifest has an invalid executable path.")

        if "\\" in value or value.startswith("/"):
            raise RuntimeStagingError("Runtime executable path must be relative.")

        parts = value.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise RuntimeStagingError("Runtime executable path contains unsafe components.")

        if re.match(r"^[A-Za-z]:", value):
            raise RuntimeStagingError("Runtime executable path cannot be drive-qualified.")

        return Path(*parts)

    def _record(self, result: RuntimeOperationResult) -> RuntimeOperationResult:
        if self.record_manager is not None:
            self.record_manager.record(result)
        return result

    def stage(
        self,
        runtime_id: str,
        version: str,
        profile=None,
        approved: bool = False,
    ) -> RuntimeOperationResult:
        started_at = datetime.now(timezone.utc).isoformat()

        result = RuntimeOperationResult(
            operation="stage",
            runtime_id=str(runtime_id),
            runtime="unknown",
            version=str(version),
            status=RuntimeOperationStatus.FAILED,
            started_at=started_at,
        )

        temporary_path = None
        lock_path = None

        try:
            entry = self.catalog.get_runtime(runtime_id, version)

            result.runtime = entry.runtime.value
            result.sha256 = entry.sha256

            archive = self.catalog.resolve_archive_path(entry)
            result.source_path = str(archive)

            if not approved:
                result.status = RuntimeOperationStatus.SKIPPED
                result.message = "Runtime staging requires explicit approval."
                return self._record(result)

            inspection = self.verifier.verify_runtime(
                runtime_id,
                version,
                profile=profile,
            )

            if not inspection.valid:
                result.issues.extend(inspection.issues)
                raise RuntimeStagingError("Runtime verification failed; staging was not attempted.")

            parent, destination = self._destination(runtime_id, version)
            result.destination_path = str(destination)

            if destination.exists() or destination.is_symlink():
                raise RuntimeStagingError("A staged runtime already exists at the destination.")

            lock_path = parent / f".{version}.staging.lock"

            try:
                lock_fd = os.open(
                    lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError as error:
                raise RuntimeStagingError("Another staging operation may already be in progress.") from error

            os.close(lock_fd)

            # Check again after acquiring the operation lock.
            if destination.exists() or destination.is_symlink():
                raise RuntimeStagingError("A staged runtime already exists at the destination.")

            temporary_path = Path(
                tempfile.mkdtemp(
                    prefix=f".{version}.staging-",
                    dir=parent,
                )
            )

            self._extract_archive(
                archive,
                entry.archive_format,
                temporary_path,
            )

            executable_relative = self._validate_executable_path(entry.executable)
            executable = temporary_path / executable_relative

            if executable.is_symlink() or not executable.is_file():
                raise RuntimeStagingError("The manifest-declared runtime executable was not found as a regular file after extraction.")

            # The manifest identifies this file as the runtime executable.
            # Add execute permission on POSIX without changing other files.
            if os.name != "nt":
                executable.chmod(
                    executable.stat().st_mode | stat.S_IXUSR
                )

            metadata_path = temporary_path / self.METADATA_FILENAME

            if metadata_path.exists() or metadata_path.is_symlink():
                raise RuntimeStagingError("Archive contains a reserved runtime metadata filename.")

            metadata = {
                "metadata_version": 1,
                "runtime_id": entry.runtime_id,
                "runtime": entry.runtime.value,
                "version": entry.version,
                "archive_sha256": entry.sha256,
                "executable": executable_relative.as_posix(),
                "executable_sha256": calculate_sha256(executable),
                "staged_at": datetime.now(timezone.utc).isoformat(),
            }

            metadata_path.write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            # Publish only after extraction and validation have completed.
            if destination.exists() or destination.is_symlink():
                raise RuntimeStagingError("Destination appeared during staging; refusing to replace it.")

            os.rename(temporary_path, destination)
            temporary_path = None

            result.status = RuntimeOperationStatus.STAGED
            result.message = "Runtime was staged successfully."
            return self._record(result)

        except (
            OSError,
            ValueError,
            RuntimeRepositoryError,
            RuntimeStagingError,
            zipfile.BadZipFile,
            tarfile.TarError,
            EOFError,
            RuntimeError,
        ) as error:
            result.status = RuntimeOperationStatus.FAILED
            result.message = str(error)
            result.issues.append(str(error))
            return self._record(result)

        finally:
            if temporary_path is not None:
                shutil.rmtree(temporary_path, ignore_errors=True)

            if lock_path is not None:
                lock_path.unlink(missing_ok=True)
