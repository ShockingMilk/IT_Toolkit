from dataclasses import dataclass

from it_toolkit.enums import PowerShellEdition, PowerShellStatus

@dataclass
class PowerShellInfo:
    installed: bool
    version: str | None = None
    edition: PowerShellEdition = PowerShellEdition.UNKNOWN
    status: PowerShellStatus = PowerShellStatus.UNKNOWN
    executable: str | None = None
    meets_requirement: bool = False