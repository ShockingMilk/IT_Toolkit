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
from it_toolkit.modules.collectors.network import (
    collect_network_information,
)


class InterfaceDiagnosticsModule(DiagnosticModule):

    _definition = ModuleDefinition(
        module_id="network.interfaces",
        name="Network Interface Inspection",
        category="Network Diagnostics",
        description="Inspect network interfaces, addresses, gateways, DNS, and routes.",
        supported_operating_systems=(
            OperatingSystem.WINDOWS,
            OperatingSystem.LINUX,
            OperatingSystem.MACOS,
        ),
        required_capabilities=(
            CapabilityType.NETWORK,
        ),
        safety=ModuleSafety.READ_ONLY,
    )

    @property
    def definition(self) -> ModuleDefinition:
        return self._definition

    def run(self, context: ModuleContext) -> DiagnosticResult:
        data = collect_network_information(
            context.profile.operating_system.family
        )

        warnings = list(data.get("warnings", []))

        if not data.get("interfaces"):
            warnings.append(
                "No network interfaces could be enumerated."
            )

        if not data.get("dns_servers"):
            warnings.append(
                "No DNS servers were identified."
            )

        return DiagnosticResult(
            module_id=self.definition.module_id,
            module_name=self.definition.name,
            status=(
                DiagnosticStatus.PARTIAL
                if warnings
                else DiagnosticStatus.SUCCESS
            ),
            summary="Passive network inspection completed. No connectivity tests were initiated.",
            data=data,
            warnings=warnings,
        )