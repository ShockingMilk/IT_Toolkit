from it_toolkit.enums import (
    CapabilityType,
    DiagnosticStatus,
    ModuleSafety,
    OperatingSystem,
)

from it_toolkit.modules.base import DiagnosticModule
from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.definition import ModuleDefinition
from it_toolkit.modules.results import DiagnosticResult


class RuntimeOverviewModule(DiagnosticModule):

    _definition = ModuleDefinition(
        module_id="runtime.overview",
        name="Runtime Inventory",
        category="System Information",
        description="View detected Python and PowerShell installations.",

        supported_operating_systems=(
            OperatingSystem.WINDOWS,
            OperatingSystem.LINUX,
            OperatingSystem.MACOS,
        ),

        required_capabilities=(
            CapabilityType.SYSTEM_INFORMATION,
        ),

        safety=ModuleSafety.READ_ONLY,
    )

    @property
    def definition(self) -> ModuleDefinition:
        return self._definition

    def run(self, context: ModuleContext) -> DiagnosticResult:

        profile = context.profile

        python = profile.python

        powershell_installations = [
            {
                "version": item.version,
                "edition": item.edition.value,
                "status": item.status.value,
                "executable": item.executable,
                "installed": item.installed,
                "meets_requirement": item.meets_requirement,
            }
            for item in profile.powershell
        ]

        data = {
            "python": {
                "installed": python.installed,
                "version": python.version,
                "executable": python.executable,
                "implementation": python.implementation,
                "meets_requirement": python.meets_requirement,
            },
            "powershell": powershell_installations,
        }

        warnings = []

        if not python.meets_requirement:
            warnings.append(
                "The detected Python runtime does not meet the configured minimum."
            )

        if not powershell_installations:
            warnings.append(
                "No PowerShell installations were detected."
            )

        status = (
            DiagnosticStatus.WARNING
            if warnings
            else DiagnosticStatus.SUCCESS
        )

        return DiagnosticResult(
            module_id=self.definition.module_id,
            module_name=self.definition.name,
            status=status,
            summary="Runtime inventory completed.",
            data=data,
            warnings=warnings,
        )