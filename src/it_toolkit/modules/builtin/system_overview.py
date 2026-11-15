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


class SystemOverviewModule(DiagnosticModule):

    _definition = ModuleDefinition(
        module_id="system.overview",
        name="System Overview",
        category="System Information",
        description="View a summary of the detected host system.",

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
        operating_system = profile.operating_system

        data = {
            "hostname": profile.hostname,
            "username": profile.username,
            "operating_system": {
                "family": operating_system.family.value,
                "name": operating_system.name,
                "version": operating_system.version,
                "distribution": operating_system.distribution,
                "architecture": operating_system.architecture.value,
                "kernel": operating_system.kernel,
                "build": operating_system.build,
            },
            "toolkit_mode": profile.toolkit_mode.value,
        }

        return DiagnosticResult(
            module_id=self.definition.module_id,
            module_name=self.definition.name,
            status=DiagnosticStatus.SUCCESS,
            summary="System information retrieved successfully.",
            data=data,
        )