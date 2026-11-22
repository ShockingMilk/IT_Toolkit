import json
import os
import re
import tempfile

from datetime import datetime, timezone
from pathlib import Path

from it_toolkit.enums import RuntimeOperationStatus
from it_toolkit.managers.runtime_stager import RuntimeStager
from it_toolkit.models.runtime_operation import RuntimeOperationResult


class RuntimeSelectionError(Exception):
    """Raised when a staged runtime cannot be selected safely."""


class RuntimeSelectionManager:
    """Manages the toolkit's explicitly selected portable runtime."""

    def __init__(
        self,
        staging_root: Path,
        record_manager=None,
    ):
        self.staging_root = Path(staging_root)
        self.selection_path = self.staging_root / "selected_runtime.json"
        self.record_manager = record_manager

    @staticmethod
    def _validate_component(value: str, label: str) -> str:
        if not isinstance(value, str) or not value:
            raise RuntimeSelectionError(f"{label} must be a non-empty string.")

        if value in (".", "..") or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*",
            value,
        ):
            raise RuntimeSelectionError(f"Unsafe {label}: {value!r}")

        return value

    @staticmethod
    def _safe_relative_path(value: str) -> Path:
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
            or "\\" in value
            or value.startswith("/")
            or re.match(r"^[A-Za-z]:", value)
        ):
            raise RuntimeSelectionError("Staged executable path is invalid.")

        parts = value.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise RuntimeSelectionError("Staged executable path contains unsafe components.")

        return Path(*parts)

    def _record(self, result: RuntimeOperationResult) -> RuntimeOperationResult:
        if self.record_manager is not None:
            self.record_manager.record(result)
        return result

    def _load_staged_runtime(
        self,
        runtime_id: str,
        version: str,
    ) -> tuple[Path, dict, Path]:
        runtime_id = self._validate_component(runtime_id, "runtime ID")
        version = self._validate_component(version, "runtime version")

        if not self.staging_root.exists():
            raise RuntimeSelectionError("Runtime staging directory does not exist.")

        root = self.staging_root.resolve()
        runtime_path = root / runtime_id / version

        if runtime_path.is_symlink() or not runtime_path.is_dir():
            raise RuntimeSelectionError("Requested runtime has not been staged.")

        resolved_runtime = runtime_path.resolve()

        try:
            resolved_runtime.relative_to(root)
        except ValueError as error:
            raise RuntimeSelectionError("Staged runtime resolves outside the staging root.") from error

        metadata_path = resolved_runtime / RuntimeStager.METADATA_FILENAME

        if metadata_path.is_symlink() or not metadata_path.is_file():
            raise RuntimeSelectionError("Staged runtime metadata is missing or unsafe.")

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeSelectionError(f"Unable to read staged runtime metadata: {error}") from error

        if not isinstance(metadata, dict):
            raise RuntimeSelectionError("Staged runtime metadata must be an object.")

        if metadata.get("metadata_version") != 1 or metadata.get("runtime_id") != runtime_id or metadata.get("version") != version:
            raise RuntimeSelectionError("Staged runtime metadata does not match the requested runtime.")

        executable_relative = self._safe_relative_path(metadata.get("executable"))
        executable = resolved_runtime / executable_relative

        if executable.is_symlink() or not executable.is_file():
            raise RuntimeSelectionError("Staged runtime executable is missing or unsafe.")

        try:
            executable.resolve().relative_to(resolved_runtime)
        except ValueError as error:
            raise RuntimeSelectionError("Staged runtime executable resolves outside its runtime directory.") from error

        return resolved_runtime, metadata, executable

    def select(
        self,
        runtime_id: str,
        version: str,
        approved: bool = False,
    ) -> RuntimeOperationResult:
        result = RuntimeOperationResult(
            operation="select",
            runtime_id=str(runtime_id),
            runtime="unknown",
            version=str(version),
            status=RuntimeOperationStatus.FAILED,
        )

        try:
            if not approved:
                result.status = RuntimeOperationStatus.SKIPPED
                result.message = "Runtime selection requires explicit approval."
                return self._record(result)

            runtime_path, metadata, executable = self._load_staged_runtime(
                runtime_id,
                version,
            )

            result.runtime = metadata.get("runtime", "unknown")
            result.sha256 = metadata.get("archive_sha256", "")
            result.source_path = str(runtime_path)
            result.destination_path = str(self.selection_path)

            self.staging_root.mkdir(parents=True, exist_ok=True)

            if self.selection_path.is_symlink():
                raise RuntimeSelectionError("Selection file cannot be a symbolic link.")

            selection = {
                "selection_version": 1,
                "runtime_id": runtime_id,
                "runtime": result.runtime,
                "version": version,
                "runtime_path": str(runtime_path),
                "executable_path": str(executable),
                "archive_sha256": result.sha256,
                "executable_sha256": metadata.get("executable_sha256"),
                "selected_at": datetime.now(timezone.utc).isoformat(),
            }

            # Write to a temporary file in the same directory so replace
            # remains an atomic operation on the same filesystem.
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=".selected-runtime-",
                suffix=".tmp",
                dir=self.staging_root,
                text=True,
            )

            temporary_path = Path(temporary_name)

            try:
                with os.fdopen(
                    file_descriptor,
                    "w",
                    encoding="utf-8",
                    newline="\n",
                ) as selection_file:
                    json.dump(
                        selection,
                        selection_file,
                        indent=2,
                        sort_keys=True,
                    )
                    selection_file.write("\n")
                    selection_file.flush()
                    os.fsync(selection_file.fileno())

                os.replace(temporary_path, self.selection_path)

            except Exception:
                temporary_path.unlink(missing_ok=True)
                raise

            result.status = RuntimeOperationStatus.SELECTED
            result.message = "Portable runtime selected. It has not been executed."
            return self._record(result)

        except (OSError, ValueError, RuntimeSelectionError) as error:
            result.status = RuntimeOperationStatus.FAILED
            result.message = str(error)
            result.issues.append(str(error))
            return self._record(result)

    def get_selection(self) -> dict | None:
        """Return the saved selection, or None when no selection exists."""

        if not self.selection_path.exists():
            return None

        if self.selection_path.is_symlink():
            raise RuntimeSelectionError("Selection file cannot be a symbolic link.")

        try:
            data = json.loads(self.selection_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeSelectionError(f"Unable to read runtime selection: {error}") from error

        if not isinstance(data, dict) or data.get("selection_version") != 1:
            raise RuntimeSelectionError("Runtime selection file has an unsupported format.")

        return data
