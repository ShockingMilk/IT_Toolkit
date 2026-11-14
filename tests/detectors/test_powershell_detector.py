import unittest

from unittest.mock import patch

from it_toolkit.config.config_manager import ConfigManager
from it_toolkit.detectors.powershell_detector import PowerShellDetector
from it_toolkit.enums import PowerShellEdition, PowerShellStatus

class TestPowerShellDetector(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager()
        self.detector = PowerShellDetector(self.config)

        @patch.object(
            PowerShellDetector,
            "_find_executables",
        )
        @patch.object(
            PowerShellDetector,
            "_inspect",
        )
        def test_detect_modern_powershell(
            self,
            mock_inspect,
            mock_executables,
        ):
            mock_executables.return_value = ["/usr/bin/pwsh"]
            mock_inspection.return_value = {
                "version": "7.4.6",
                "edition": "Core",
            }

            result = self.detector.detect()

            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[0].status,
                PowerShellStatus.SUPPORTED,
            )
            self.assertEqual(
                result[0].edition,
                PowerShellEdition.CORE
            )

            self.assertTrue(result[0].meets_requirement)

        @patch.object(PowerShellDetector, "_find_executables")
        @patch.object(PowerShellDetector, "_inspect")
        def test_detect_legacy_powershell(
            self,
            mock_inspect,
            mock_executables,
        ):
            mock_executables.return_value = [
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            ]
            mock_inspect.return_value = {
                "version": "5.1.19041.1",
                "edition": "Desktop",
            }

            result = self.detector.detect()

            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[0].status,
                PowerShellStatus.LEGACY,
            )
            self.assertEqual(
                result[0].edition,
                PowerShellEdition.DESKTOP,
            )
            self.assertFalse(
                result[0].meets_requirement
            )

        @patch.object(PowerShellDetector, "_find_executables")
        @patch.object(PowerShellDetector, "_inspect")
        def test_detect_multiple_installations(
            self,
            mock_inspect,
            mock_executables,
        ):
            legacy = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            modern = r"C:\Program Files\PowerShell\7\pwsh.exe"

            mock_executables.return_value = [legacy, modern]

            mock_inspect.side_effect = [
                {
                    "version": "5.1.19041.1",
                    "edition": "Desktop",
                },
                {
                    "version": "7.4.6",
                    "edition": "Core",
                },
            ]

            result = self.detector.detect()

            self.assertEqual(len(result), 2)
            self.assertEqual(
                result[0].status,
                PowerShellStatus.LEGACY,
            )
            self.assertEqual(
                result[1].status,
                PowerShellStatus.SUPPORTED,
            )

        @patch.object(PowerShellDetector, "_find_executables")
        @patch.object(PowerShellDetector, "_inspect")
        def test_unreadable_installation_is_skipped(
            self,
            mock_inspect,
            mock_executables,
        ):
            mock_executables.return_value = ["/usr/bin/pwsh"]
            mock_inspect.return_value = None

            result = self.detector.detect()

            self.assertEqual(result, [])

if __name__ == "__main__":
    unittest.main()