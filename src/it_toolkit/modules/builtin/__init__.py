from it_toolkit.modules.registry import ModuleRegistry

from it_toolkit.modules.builtin.system_overview import (
    SystemOverviewModule,
)

from it_toolkit.modules.builtin.runtime_overview import (
    RuntimeOverviewModule,
)

from it_toolkit.modules.builtin.hardware_overview import (
    HardwareOverviewModule,
)

from it_toolkit.modules.builtin.network.interface_diagnostics import (
    InterfaceDiagnosticsModule,
)

from it_toolkit.modules.builtin.network.connectivity_diagnostics import (
    ConnectivityDiagnosticsModule,
)

from it_toolkit.modules.builtin.storage.filesystem_diagnostics import (
    FilesystemDiagnosticsModule,
)


def register_builtin_modules(
    registry: ModuleRegistry,
) -> None:
    """
    Explicitly register built-in diagnostic modules.

    Explicit registration keeps module availability predictable
    in air-gapped environments.
    """

    modules = (
        SystemOverviewModule(),
        RuntimeOverviewModule(),
        HardwareOverviewModule(),
        InterfaceDiagnosticsModule(),
        ConnectivityDiagnosticsModule(),
        FilesystemDiagnosticsModule(),
    )

    for module in modules:
        registry.register(module)