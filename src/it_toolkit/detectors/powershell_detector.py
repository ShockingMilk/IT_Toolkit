import os
import shutil
import sys

from pathlib import Path

from it_toolkit.config.config_manager import ConfigManager
from it_toolkit.detectors.base_detector import BaseDetector
from it_toolkit.enums import PowerShellEdition, PowerShellStatus
from it_toolkit.models.powershell_info import PowerShellInfo
from it_toolkit.utils.command_runner import run_command
from it_toolkit.utils.version_utils import version_at_least

class PowerShellDetector(BaseDetector):
    def __init__(self, config: ConfigManager):
        self.config = config

    def detect(self) -> list[PowerShellInfo]:
        installations = []
        minimum = self.config.get(
            "requirements.powershell.minimum_version",
            "7.1",
        )

        for executable in self._find_executables():
            result = self._inspect(executable)

            if not result:
                continue

            version = result.get("version", "")
            edition = result.get("edition", "Unknown")
            meets_requirement = version_at_least(
                version,
                minimum,
            )
            status = (
                PowerShellStatus.SUPPORTED
                if meets_requirement
                else PowerShellStatus.LEGACY
            )

            if edition.lower() == "desktop":
                edition_type = PowerShellEdition.DESKTOP
            elif edition.lower() == "core":
                edition_type = PowerShellEdition.CORE
            else:
                edition_type = PowerShellEdition.UNKNOWN

            installations.append(
                PowerShellInfo(
                    installed=True,
                    version=version,
                    edition=edition_type,
                    status=status,
                    executable=executable,
                    meets_requirement=meets_requirement,
                )
            )
        return self._remove_duplicates(installations)

    def _find_executables(self) -> list[str]:
        executables = []

        if sys.platform == "win32":
            candidates = [
                "powershell.exe",
                "pwsh.exe",
            ]
            program_files = os.environ.get(
                "ProgramFiles",
                r"C:\Program Files",
            )
            candidates.extend([
                str(
                    Path(program_files)
                    / "PowerShell"
                    / "7"
                    / "pwsh.exe"
                ),
                str(
                    Path(program_files)
                    / "PowerShell"
                    / "7-preview"
                    / "pwsh.exe"
                ),
            ])
        else:
            candidates = [
                "pwsh",
            ]

        for candidate in candidates:
            if Path(candidate).is_file():
                executable = str(Path(candidate).resolve())
            else:
                executable = shutil.which(candidate)
            if executable and executable not in executables:
                executables.append(executable)
        return executables

    @staticmethod
    def _inspect(executable: str) -> dict | None:
        command = (
            "$PSVersionTable | "
            "Select-Object "
            "@{Name='version';Expression={$_.PSVersion.ToString()}},"
            "@{Name='edition';Expression={$_.PSEdition}} | "
            "ConvertTo-Json -Compress"
        )
        result = run_command(
            [
                executable,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            timeout=15,
        )

        if not result.success:
            return None

        try:
            import json
            return json.loads(result.stdout)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _remove_duplicates(
        installations: list[PowerShellInfo],
    ) -> list[PowerShellInfo]:
        unique = {}

        for installation in installations:
            key = (
                installation.executable,
                installation.version,
            )
            unique[key] = installation
        return list(unique.values())