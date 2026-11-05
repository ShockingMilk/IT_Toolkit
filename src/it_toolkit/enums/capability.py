from enum import Enum

class CapabilityType(str, Enum):
    SYSTEM_INFORMATION = "system.information"
    PYTHON = "runtime.python"
    POWERSHELL_LEGACY = "runtime.powershell.legacy"
    POWERSHELL_MODERN = "runtime.powershell.modern"
    NETWORK = "network.diagnostics"
    STORAGE = "storage.diagnostics"
    REPORTING = "reporting"