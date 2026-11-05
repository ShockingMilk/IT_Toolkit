from typing import Callable, TypeVar

from it_toolkit.enums import OperatingSystem

T = TypeVar("T")

def switch_os(
    operating_system: OperatingSystem,
    handlers: dict[OperatingSystem, Callable[[], T]],
    default: Callable[[], T] | None = None,
) -> T:
    """
    Execute the implementation associated with an OS.

    Example:
        switch_os(
            OperatingSystem.WINDOWS,
            {
                OperatingSystem.WINDOWS: windows_handler,
                OperatingSystem.LINUX: linux_handler,
                OperatingSystem.MACOS: macos_handler,
            },
            default=unknown_handler,
        )
    """

    handler = handlers.get(operating_system)

    if handler is not None:
        return handler()

    if default is not None:
        return default()

    raise NotImplementedError(
        f"No handler registered for {operating_system.value}"
    )