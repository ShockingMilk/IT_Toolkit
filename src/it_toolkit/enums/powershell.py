from enum import Enum

class PowerShellEdition(str, Enum):
    DESKTOP = "desktop"
    CORE = "core"
    UNKNOWN = "unknown"

class PowerShellStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    LEGACY = "legacy"
    SUPPORTED = "supported"
    UNKNOWN = "unknown"