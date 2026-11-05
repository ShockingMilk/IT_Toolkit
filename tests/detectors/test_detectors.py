import unittest
from unittest.mock import patch

from it_toolkit.detectors.windows_detector import WindowsDetector
from it_toolkit.detectors.linux_detector import LinuxDetector
from it_toolkit.detectors.macos_detector import MacOSDetector
from it_toolkit.enums import Architecture, OperatingSystem

class TestWindowsDetector(unittest.TestCase):
    @patch("it_toolkit.detectors.windows_detector.platform.machine")
    @patch("it_toolkit.detectors.windows_detector.platform.win32_ver")
    def test_detect_windows(
        self,
        mock_version,
        mock_machine,
    ):
        mock_version.return_value = (
            "11",
            "10.0.26100",
            "SP0",
            "Multiprocessor Free",
        )
        mock_machine.return_value = "AMD64"
        result = WindowsDetector().detect()
        self.assertEqual(
            result.family,
            OperatingSystem.WINDOWS,
        )
        self.assertEqual(
            result.architecture,
            Architecture.X86_64,
        )

class TestLinuxDetector(unittest.TestCase):
    @patch("it_toolkit.detectors.linux_detector.platform.machine")
    @patch.object(LinuxDetector, "_read_os_release")
    def test_detect_linux(
        self,
        mock_release,
        mock_machine,
    ):
        mock_release.return_value = {
            "NAME": "Debian GNU/Linux",
            "VERSION_ID": "13",
            "ID": "debian",
        }
        mock_machine.return_value = "x86_64"
        result = LinuxDetector().detect()
        self.assertEqual(
            result.family,
            OperatingSystem.LINUX,
        )
        self.assertEqual(
            result.distribution,
            "debian",
        )

class TestMacOSDetector(unittest.TestCase):
    @patch("it_toolkit.detectors.macos_detector.platform.mac_ver")
    @patch("it_toolkit.detectors.macos_detector.platform.machine")
    def test_detect_macos(
        self,
        mock_machine,
        mock_version,
    ):
        mock_machine.return_value = "arm64"
        mock_version.return_value = (
            "15.0",
            ("", "", ""),
            "arm64",
        )
        result = MacOSDetector().detect()
        self.assertEqual(
            result.family,
            OperatingSystem.MACOS,
        )
        self.assertEqual(
            result.architecture,
            Architecture.ARM64,
        )

if __name__ == "__main__":
    unittest.main()