import unittest
from unittest.mock import patch

from it_toolkit.config.config_manager import ConfigManager
from it_toolkit.managers.detection_manager import DetectionManager
from it_toolkit.enums import OperatingSystem, Runtime

class TestDetectionManager(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager()
        self.manager = DetectionManager(
            self.config
        )

    @patch("it_toolkit.managers.detection_manager.platform.system")
    def test_detect_windows(self, mock_system):
        mock_system.return_value = "Windows"
        result = self.manager._detect_os()

        self.assertEqual(
            result,
            OperatingSystem.WINDOWS,
        )

    @patch("it_toolkit.managers.detection_manager.platform.system")
    def test_detect_linux(self, mock_system):
        mock_system.return_value = "Linux"
        result = self.manager._detect_os()

        self.assertEqual(
            result,
            OperatingSystem.LINUX,
        )

    @patch("it_toolkit.managers.detection_manager.platform.system")
    def test_detect_macos(self, mock_system):
        mock_system.return_value = "Darwin"
        result = self.manager._detect_os()

        self.assertEqual(
            result,
            OperatingSystem.MACOS,
        )

    @patch.dict(
        "os.environ",
        {"IT_TOOLKIT_LAUNCHER_SHELL": "powershell"},
    )
    def test_detect_powershell_shell(self):
        result = self.manager._detect_shell()
        self.assertEqual(
            result,
            Runtime.POWERSHELL,
        )

if __name__ == "__main__":
    unittest.main()