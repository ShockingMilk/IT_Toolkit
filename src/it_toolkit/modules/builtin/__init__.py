from it_toolkit.modules.builtin.system_overview import (
    SystemOverviewModule,
)

from it_toolkit.modules.builtin.runtime_overview import (
    RuntimeOverviewModule,
)

from it_toolkit.modules.registry import ModuleRegistry


def register_builtin_modules(
    registry: ModuleRegistry,
) -> None:
    """
    Register all built-in diagnostic modules.

    Keep registration explicit so that module availability
    is predictable in air-gapped environments.
    """

    registry.register(SystemOverviewModule())
    registry.register(RuntimeOverviewModule())