import os
import re
import subprocess

from datetime import datetime, timezone
from pathlib import Path

from it_toolkit.enums import Runtime, RuntimeOperationStatus

from it_toolkit.managers.runtime_stager import RuntimeStager
from it_toolkit.models.runtime_execution import RuntimeExecutionResult
from it_toolkit.models.runtime_operation import RuntimeOperationResult
from it_toolkit.utils.checksum import calculate_sha256


class RuntimeExecutionError(Exception):
    """Raised when a selected portable runtime cannot be executed."""


class RuntimeExecutionManager:
    """
    Executes explicitly selected portable runtimes.

    This manager never changes the host system's PATH or system runtime.
    """

    def __init__(
        self,
        staging_root: Path,
        record_manager=None,
        default_timeout: int = 30,
    ):
        if default_timeout < 1:
            raise ValueError("Default timeout must be positive.")

        self.staging_root = Path(staging_root)
        self.selection_path = self.staging_root / "selected_runtime.json"
        self.record_manager = record_manager
        self.default_timeout = default_timeout

    @staticmethod
    def _validate_component(value: str, label: str) -> str:
        if not isinstance(value, str) or not value:
            raise RuntimeExecutionError(f"{label} must be a non-empty string.")

        if value in (".", "..") or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*",
            value,
        ):
            raise RuntimeExecutionError(f"Unsafe {label}: {value!r}")

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
            raise RuntimeExecutionError("Runtime executable path is invalid.")

        parts = value.split("/")

        if any(part in ("", ".", "..") for part in parts):
            raise RuntimeExecutionError("Runtime executable path contains unsafe components.")

        return Path(*parts)

    def _load_selected_runtime(self) -> dict:
        if not self.staging_root.exists():
            raise RuntimeExecutionError("Runtime staging directory does not exist.")

        root = self.staging_root.resolve()

        if self.selection_path.is_symlink():
            raise RuntimeExecutionError("Runtime selection file cannot be a symbolic link.")

        if not self.selection_path.is_file():
            raise RuntimeExecutionError("No portable runtime has been selected.")

        try:
            import json

            selection = json.loads(self.selection_path.read_text(encoding="utf-8"))

        except (OSError, ValueError) as error:
            raise RuntimeExecutionError(f"Unable to read runtime selection: {error}") from error

        if not isinstance(selection, dict):
            raise RuntimeExecutionError("Runtime selection must be a JSON object.")

        if selection.get("selection_version") != 1:
            raise RuntimeExecutionError("Unsupported runtime selection format.")

        runtime_id = self._validate_component(
            selection.get("runtime_id"),
            "runtime ID",
        )

        version = self._validate_component(
            selection.get("version"),
            "runtime version",
        )

        runtime_path = root / runtime_id / version

        if runtime_path.is_symlink() or not runtime_path.is_dir():
            raise RuntimeExecutionError("Selected runtime directory is missing or unsafe.")

        resolved_runtime = runtime_path.resolve()

        try:
            resolved_runtime.relative_to(root)

        except ValueError as error:
            raise RuntimeExecutionError("Selected runtime resolves outside the staging directory.") from error

        metadata_path = resolved_runtime / RuntimeStager.METADATA_FILENAME

        if metadata_path.is_symlink() or not metadata_path.is_file():
            raise RuntimeExecutionError("Selected runtime metadata is missing or unsafe.")

        try:
            import json

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        except (OSError, ValueError) as error:
            raise RuntimeExecutionError(f"Unable to read staged runtime metadata: {error}") from error

        if not isinstance(metadata, dict):
            raise RuntimeExecutionError("Runtime metadata must be a JSON object.")

        if (
            metadata.get("metadata_version") != 1
            or metadata.get("runtime_id") != runtime_id
            or metadata.get("version") != version
            or metadata.get("runtime") != selection.get("runtime")
            or metadata.get("archive_sha256")
            != selection.get("archive_sha256")
        ):
            raise RuntimeExecutionError("Selected runtime metadata does not match its selection.")

        executable_relative = self._safe_relative_path(metadata.get("executable"))

        executable = resolved_runtime / executable_relative

        if executable.is_symlink() or not executable.is_file():
            raise RuntimeExecutionError("Selected runtime executable is missing or unsafe.")

        expected_executable_hash = metadata.get(
            "executable_sha256"
        )

        if (
            not isinstance(expected_executable_hash, str)
            or not re.fullmatch(
                r"[a-fA-F0-9]{64}",
                expected_executable_hash,
            )
        ):
            raise RuntimeExecutionError(
                "Staged runtime executable checksum is missing or invalid. "
                "Restage this runtime using the updated staging manager."
            )

        actual_executable_hash = calculate_sha256(executable)

        if actual_executable_hash.lower() != expected_executable_hash.lower():
            raise RuntimeExecutionError(
                "Selected runtime executable failed its integrity check."
            )

        if selection.get("executable_sha256") != expected_executable_hash:
            raise RuntimeExecutionError(
                "Runtime selection executable checksum does not match metadata."
            )

        resolved_executable = executable.resolve()

        try:
            resolved_executable.relative_to(resolved_runtime)

        except ValueError as error:
            raise RuntimeExecutionError("Runtime executable resolves outside its runtime directory.") from error

        # Confirm the selection file identifies this same staged runtime.
        selected_path = selection.get("runtime_path")

        if not isinstance(selected_path, str):
            raise RuntimeExecutionError("Runtime selection does not contain a valid runtime path.")

        try:
            if Path(selected_path).resolve() != resolved_runtime:
                raise RuntimeExecutionError("Selected runtime path does not match its staged location.")
        except OSError as error:
            raise RuntimeExecutionError(f"Unable to resolve selected runtime path: {error}") from error

        return {
            "runtime_id": runtime_id,
            "runtime": metadata["runtime"],
            "version": version,
            "runtime_path": resolved_runtime,
            "executable": resolved_executable,
            "archive_sha256": metadata["archive_sha256"],
        }

    def get_selected_runtime(self) -> dict:
        """Return validated information about the selected runtime."""

        return self._load_selected_runtime()

    @staticmethod
    def _validate_arguments(arguments: list[str]) -> list[str]:
        if not isinstance(arguments, (list, tuple)):
            raise TypeError("Runtime arguments must be a list or tuple.")

        validated = []

        for argument in arguments:
            if not isinstance(argument, str):
                raise TypeError("Every runtime argument must be a string.")

            if "\x00" in argument:
                raise ValueError("Runtime arguments cannot contain null characters.")

            validated.append(argument)

        return validated

    def run_selected(
        self,
        arguments: list[str] | None = None,
        timeout: int | None = None,
    ) -> RuntimeExecutionResult:
        """Run a command using the explicitly selected portable runtime."""

        arguments = self._validate_arguments(
            arguments or []
        )

        timeout = (
            self.default_timeout
            if timeout is None
            else timeout
        )

        if timeout < 1:
            raise ValueError("Timeout must be positive.")

        selected = self._load_selected_runtime()

        executable = selected["executable"]

        result = RuntimeExecutionResult(
            runtime_id=selected["runtime_id"],
            runtime=selected["runtime"],
            version=selected["version"],
            executable=str(executable),
            arguments=arguments,
        )

        try:
            completed = subprocess.run(
                [str(executable), *arguments],
                cwd=str(selected["runtime_path"]),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                check=False,
            )

            result.started = True
            result.return_code = completed.returncode
            result.stdout = completed.stdout or ""
            result.stderr = completed.stderr or ""

        except subprocess.TimeoutExpired as error:
            result.started = True
            result.timed_out = True

            result.stdout = (
                error.stdout.decode(errors="replace")
                if isinstance(error.stdout, bytes)
                else error.stdout or ""
            )

            result.stderr = (
                error.stderr.decode(errors="replace")
                if isinstance(error.stderr, bytes)
                else error.stderr or ""
            )

            result.error = f"Runtime execution exceeded the {timeout}-second timeout."

        except OSError as error:
            result.error = f"Unable to execute selected runtime: {error}"

        self._record_execution(selected, result)

        return result

    def probe_selected_runtime(
        self,
        timeout: int | None = None,
    ) -> RuntimeExecutionResult:
        """
        Execute a version probe against the selected portable runtime.

        This is an explicit operation, not part of toolkit startup.
        """

        selected = self._load_selected_runtime()

        if selected["runtime"] == Runtime.PYTHON.value:
            arguments = ["--version"]

        elif selected["runtime"] == Runtime.POWERSHELL.value:
            arguments = [
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            ]

        else:
            raise RuntimeExecutionError(f"Unsupported portable runtime: {selected['runtime']}")

        result = self.run_selected(
            arguments=arguments,
            timeout=timeout,
        )

        if result.success:
            reported = result.stdout + result.stderr

            if selected["version"] not in reported:
                result.error = "Runtime launched successfully, but its reported version did not match the staged manifest version."

        return result

    def _record_execution(
        self,
        selected: dict,
        result: RuntimeExecutionResult,
    ) -> None:
        if self.record_manager is None:
            return

        status = (
            RuntimeOperationStatus.EXECUTED
            if result.started
            else RuntimeOperationStatus.FAILED
        )

        message = (
            f"Runtime process exited with code {result.return_code}."
            if result.started and not result.timed_out
            else result.error or "Runtime execution failed."
        )

        if result.timed_out:
            status = RuntimeOperationStatus.FAILED

        audit_result = RuntimeOperationResult(
            operation="execute",
            runtime_id=selected["runtime_id"],
            runtime=selected["runtime"],
            version=selected["version"],
            status=status,
            source_path=str(selected["executable"]),
            destination_path=str(selected["runtime_path"]),
            sha256=selected["archive_sha256"],
            message=message,
            issues=(
                [result.error]
                if result.error
                else []
            ),
        )

        self.record_manager.record(audit_result)