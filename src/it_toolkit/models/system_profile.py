from dataclasses import dataclass, field
from datetime import datetime, timezone

from it_toolkit.enums import Runtime, ToolkitMode

from it_toolkit.models.capability import Capability
from it_toolkit.models.operating_system import OperatingSystemInfo
from it_toolkit.models.powershell_info import PowerShellInfo
from it_toolkit.models.python_info import PythonInfo


@dataclass
class SystemProfile:

    operating_system: OperatingSystemInfo

    python: PythonInfo

    powershell: list[PowerShellInfo] = field(
        default_factory=list
    )

    shell: Runtime = Runtime.UNKNOWN

    toolkit_mode: ToolkitMode = ToolkitMode.UNKNOWN

    capabilities: list[Capability] = field(
        default_factory=list
    )

    hostname: str = ""

    username: str = ""

    timestamp: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    def to_dict(self) -> dict:

        return {
            "toolkit": {
                "mode": self.toolkit_mode.value
            },

            "timestamp": self.timestamp,

            "system": {
                "hostname": self.hostname,
                "username": self.username,
            },

            "operating_system": {
                "family": self.operating_system.family.value,
                "name": self.operating_system.name,
                "version": self.operating_system.version,
                "architecture": self.operating_system.architecture.value,
                "distribution": self.operating_system.distribution,
                "build": self.operating_system.build,
                "kernel": self.operating_system.kernel,
            },

            "shell": self.shell.value,

            "python": {
                "installed": self.python.installed,
                "version": self.python.version,
                "executable": self.python.executable,
                "implementation": self.python.implementation,
                "meets_requirement": self.python.meets_requirement,
            },

            "powershell": [
                {
                    "installed": item.installed,
                    "version": item.version,
                    "edition": item.edition.value,
                    "status": item.status.value,
                    "executable": item.executable,
                    "meets_requirement": item.meets_requirement,
                }
                for item in self.powershell
            ],

            "capabilities": [
                {
                    "name": item.name.value,
                    "available": item.available,
                    "reason": item.reason,
                }
                for item in self.capabilities
            ],
        }