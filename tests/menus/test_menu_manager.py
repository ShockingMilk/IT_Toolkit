import unittest

from unittest.mock import Mock

from it_toolkit.menus.menu_manager import MenuManager
from it_toolkit.menus.menu_item import MenuItem
from it_toolkit.models.system_profile import SystemProfile
from it_toolkit.models.operating_system import OperatingSystemInfo
from it_toolkit.models.python_info import PythonInfo
from it_toolkit.enums import OperatingSystem, Architecture

class TestMenuManager(unittest.TestCase):
    def setUp(self):
        self.profile = SystemProfile(
            operating_system=OperatingSystemInfo(
                family=OperatingSystem.LINUX,
                name="Linux",
                version="Test",
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

        self.view = Mock()
        self.main_menu = Mock()

        self.main_menu.build.return_value = {
            MenuItem(
                key="test",
                label="Test",
                action="test",
            )
        }

        self.manager = MenuManager(
            view=self.view,
            main_menu=self.main_menu,
        )

    def test_exit_returns_from_menu(self):
        self.view.display.return_value = "0"

        self.manager.run(
            self.profile,
            handlers={},
        )

        self.view.output.assert_called_once()

    def test_action_handler_runs(self):
        self.view.display.side_effect = ["test", "0"]

        handler = Mock()

        self.manager.run(
            self.profile,
            handlers={"test": handler},
        )

        handler.assert_called_once()

    def test_unknown_action_does_not_crash(self):
        self.view.display.side_effect = ["unknown", "0"]

        self.manager.run(
            self.profile,
            handlers={}
        )

        self.view.output.assert_any_call("\nThis menu action is not implemented.")

if __name__ == "__main__":
    unittest.main()