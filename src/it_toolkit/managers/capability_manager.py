from it_toolkit.enums import (
    CapabilityType,
    PowerShellStatus,
)
from it_toolkit.models.capability import Capability
from it_toolkit.models.system_profile import SystemProfile

class CapabilityManager:
    def evaluate(
        self,
        profile: SystemProfile,
    ) -> list[Capability]:
        capabilities = []
        capabilities.append(
            Capability(
                name=CapabilityType.SYSTEM_INFORMATION,
                available=True,
                reason="Operating system detection completed.",
            )
        )
        capabilities.append(
            Capability(
                name=CapabilityType.PYTHON,
                available=profile.python.meets_requirement,
                reason=(
                    "Python meets minimum requirements."
                    if profile.python.meets_requirement
                    else "Python does not meet minimum requirements."
                ),
            )
        )
        legacy_powershell = any(
            item.installed
            and item.status == PowerShellStatus.LEGACY
            for item in profile.powershell
        )
        modern_powershell = any(
            item.installed
            and item.status == PowerShellStatus.SUPPORTED
            for item in profile.powershell
        )
        capabilities.extend([
            Capability(
                name=CapabilityType.POWERSHELL_LEGACY,
                available=legacy_powershell,
                reason="Legacy PowerShell installation detected.",
            ),
            Capability(
                name=CapabilityType.POWERSHELL_MODERN,
                available=modern_powershell,
                reason="Supported PowerShell installation detected.",
            ),
        ])
        capabilities.append(
            Capability(
                name=CapabilityType.NETWORK,
                available=False,
                reason="Network diagnostic modules are not implemented in this release.",
            )
        )
        capabilities.append(
            Capability(
                name=CapabilityType.STORAGE,
                available=False,
                reason="Storage diagnostic modules are not implemented in this release.",
            )
        )
        capabilities.append(
            Capability(
                name=CapabilityType.REPORTING,
                available=profile.python.meets_requirement,
                reason="Python reporting engine available."
                if profile.python.meets_requirement
                else "Python reporting engine unavailable.",
            )
        )

        return capabilities