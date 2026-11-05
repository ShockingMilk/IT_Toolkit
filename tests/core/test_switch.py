import unittest

from it_toolkit.core.switch import switch_os
from it_toolkit.enums import OperatingSystem

class TestSwitch(unittest.TestCase):
    def test_windows_handler(self):
        result = switch_os(
            OperatingSystem.WINDOWS,
            handlers={
                OperatingSystem.WINDOWS:
                    lambda: "Windows",
                OperatingSystem.LINUX:
                    lambda: "Linux",
            },
        )
        self.assertEqual(result, "Windows")

    def test_linux_handler(self):
        result = switch_os(
            OperatingSystem.LINUX,
            handlers={
                OperatingSystem.WINDOWS:
                    lambda: "Windows",
                OperatingSystem.LINUX:
                    lambda: "Linux",
            },
        )
        self.assertEqual(result, "Linux")

    def test_default_handler(self):
        result = switch_os(
            OperatingSystem.UNKNOWN,
            handlers={},
            default=lambda: "Unknown",
        )
        self.assertEqual(result, "Unknown")

    def test_missing_handler_raises_error(self):
        with self.assertRaises(NotImplementedError):
            switch_os(
                OperatingSystem.UNKNOWN,
                handlers={},
            )

if __name__ == "__main__":
    unittest.main()