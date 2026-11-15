from it_toolkit.core.switch import switch_os
from it_toolkit.enums import CapabilityType, OperatingSystem
from it_toolkit.menus.menu_item import MenuItem
from it_toolkit.menus.platform import windows, linux, macos
from it_toolkit.models.system_profile import SystemProfile


class MainMenu:

    def build(
        self,
        profile: SystemProfile,
        reporting_enabled: bool = True,
        include_diagnostics: bool = False,
    ) -> list[MenuItem]:

        items = [
            MenuItem(
                key="system_profile",
                label="System Profile",
                action="system_profile",
                capability=CapabilityType.SYSTEM_INFORMATION,
                description="View detected system information.",
            ),

            MenuItem(
                key="capability_status",
                label="Capability Status",
                action="capability_status",
                capability=CapabilityType.SYSTEM_INFORMATION,
                description="View available and unavailable features.",
            ),
        ]

        if reporting_enabled:
            items.append(
                MenuItem(
                    key="report_information",
                    label="Report Information",
                    action="report_information",
                    capability=CapabilityType.REPORTING,
                    description="View generated report information.",
                )
            )

        if include_diagnostics:
            items.append(
                MenuItem(
                    key="diagnostics",
                    label="Diagnostics",
                    action="diagnostics",
                    description="Run available diagnostic modules.",
                )
            )

        available_capabilities = {
            capability.name
            for capability in profile.capabilities
            if capability.available
        }

        items = [
            item
            for item in items
            if (
                item.capability is None
                or item.capability in available_capabilities
            )
        ]

        platform_handlers = {
            OperatingSystem.WINDOWS: windows.get_menu_items,
            OperatingSystem.LINUX: linux.get_menu_items,
            OperatingSystem.MACOS: macos.get_menu_items,
        }

        platform_items = switch_os(
            profile.operating_system.family,
            handlers=platform_handlers,
            default=lambda: [],
        )

        # Apply the same capability filtering to platform entries.
        platform_items = [
            item
            for item in platform_items
            if (
                item.capability is None
                or item.capability in available_capabilities
            )
        ]

        items.extend(platform_items)

        return items