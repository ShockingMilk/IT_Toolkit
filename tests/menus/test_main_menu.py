import unittest

from unittest.mock import patch

from it_toolkit.enums import CapabilityType, OperatingSystem
from it_toolkit.menus.main_menu import MainMenu
from it_toolkit.models.capability import Capability
from it_toolkit.models.system_profile import SystemProfile
from it_toolkit.models.operating_system import OperatingSystemInfo
from it_toolkit.models.python_info import PythonInfo
from it_toolkit.enums import Architecture

class TestMainMenu(unittest.TestCase):
    def setUp(self):
        self.profile = SystemProfile(
            operating_system=OperatingSystemInfo(
                family=OperatingSystem.WINDOWS,
                name="Windows",
                version="11",
                architecture=Architecture.X86_64,
            ),
            python=PythonInfo(
                installed=True,
                version="3.12",
                executable="python",
                implementation="CPython",
                meets_requirement=True,
            ),
        )

        self.menu = MainMenu()

    def test_available_capabilities_are_displayed(self):
        self.profile.capabilities = [
            Capability(
                name=CapabilityType.SYSTEM_INFORMATION,
                available=True,
            ),
            Capability(
                name=CapabilityType.REPORTING,
                available=True,
            ),
        ]

        items = self.menu.build(self.profile)

        keys = [item.key for item in items]

        self.assertIn("system_profile", keys)
        self.assertIn("capability_status", keys)
        self.assertIn("report_information", keys)

    def test_unavailable_capabilities_are_hidden(self):
        self.profile.capabilities = [
            Capability(
                name=CapabilityType.SYSTEM_INFORMATION,
                available=True,
            ),
            Capability(
                name=CapabilityType.REPORTING,
                available=False,
            ),
        ]

        items = self.menu.build(self.profile)

        keys = [item.key for item in items]

        self.assertNotIn("report_information", keys)

    def test_platform_menu_routing(self):
        self.profile.capabilities = [
            Capability(
                name=CapabilityType.SYSTEM_INFORMATION,
                available=True,
            ),
        ]

        with patch(
            "it_toolkit.menus.main_menu.windows.get_menu_items",
            return_value=[],
        ) as mock_windows:

            self.menu.build(self.profile)

            mock_windows.assert_called_once()

if __name__ == "__main__":
    unittest.main()