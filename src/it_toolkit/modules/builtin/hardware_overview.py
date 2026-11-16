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
from it_toolkit.modules.collectors.system import (
    collect_system_information,
)


class HardwareOverviewModule(DiagnosticModule):

    _definition = ModuleDefinition(
        module_id="system.hardware",
        name="Hardware Overview",
        category="System Information",
        description="Inspect CPU, memory, and platform information.",
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
        data = collect_system_information()

        warnings = []

        if not data["memory"].get("available"):
            warnings.append(
                "Physical memory information could not be fully collected."
            )

        if not data["cpu"].get("logical_processors"):
            warnings.append(
                "Logical processor count is unavailable."
            )

        return DiagnosticResult(
            module_id=self.definition.module_id,
            module_name=self.definition.name,
            status=(
                DiagnosticStatus.PARTIAL
                if warnings
                else DiagnosticStatus.SUCCESS
            ),
            summary="Hardware and platform inspection completed.",
            data=data,
            warnings=warnings,
        )