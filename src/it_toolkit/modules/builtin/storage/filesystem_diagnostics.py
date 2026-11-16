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
from it_toolkit.modules.collectors.storage import (
    collect_storage_information,
)


class FilesystemDiagnosticsModule(DiagnosticModule):

    _definition = ModuleDefinition(
        module_id="storage.filesystems",
        name="Filesystem Inspection",
        category="Storage Diagnostics",
        description="Inspect mounted filesystems and available capacity.",
        supported_operating_systems=(
            OperatingSystem.WINDOWS,
            OperatingSystem.LINUX,
            OperatingSystem.MACOS,
        ),
        required_capabilities=(
            CapabilityType.STORAGE,
        ),
        safety=ModuleSafety.READ_ONLY,
    )

    @property
    def definition(self) -> ModuleDefinition:
        return self._definition

    def run(self, context: ModuleContext) -> DiagnosticResult:
        data = collect_storage_information(
            context.profile.operating_system.family
        )

        warnings = list(data.get("warnings", []))

        if not data.get("filesystems"):
            warnings.append(
                "No filesystem capacity information was collected."
            )

        unavailable = [
            item["mountpoint"]
            for item in data.get("filesystems", [])
            if not item.get("available")
        ]

        if unavailable:
            warnings.append(
                f"{len(unavailable)} mount point(s) could not be inspected."
            )

        return DiagnosticResult(
            module_id=self.definition.module_id,
            module_name=self.definition.name,
            status=(
                DiagnosticStatus.PARTIAL
                if warnings
                else DiagnosticStatus.SUCCESS
            ),
            summary="Filesystem inspection completed.",
            data=data,
            warnings=warnings,
        )