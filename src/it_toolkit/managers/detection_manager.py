import platform
import socket
import getpass
import os

from it_toolkit.core.switch import switch_os
from it_toolkit.config.config_manager import ConfigManager
from it_toolkit.detectors.windows_detector import WindowsDetector
from it_toolkit.detectors.linux_detector import LinuxDetector
from it_toolkit.detectors.macos_detector import MacOSDetector
from it_toolkit.detectors.python_detector import PythonDetector
from it_toolkit.detectors.powershell_detector import PowerShellDetector
from it_toolkit.enums import OperatingSystem, Runtime, ToolkitMode
from it_toolkit.models.system_profile import SystemProfile
from it_toolkit.models.python_info import PythonInfo
from it_toolkit.models.operating_system import OperatingSystemInfo
from it_toolkit.enums import Architecture

class DetectionManager:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.detectors = {
            OperatingSystem.WINDOWS: WindowsDetector(),
            OperatingSystem.LINUX: LinuxDetector(),
            OperatingSystem.MACOS: MacOSDetector(),
        }

    def detect(self) -> SystemProfile:
        operating_system = self._detect_os()
        os_info = switch_os(
            operating_system,
            handlers={
                OperatingSystem.WINDOWS:
                    lambda: self.detectors[
                        OperatingSystem.WINDOWS
                    ].detect(),
                OperatingSystem.LINUX:
                    lambda: self.detectors[
                        OperatingSystem.LINUX
                    ].detect(),
                OperatingSystem.MACOS:
                    lambda: self.detectors[
                        OperatingSystem.MACOS
                    ].detect(),
            },

            default=self._unknown_os,
        )
        python_info = PythonDetector(
            self.config
        ).detect()
        powershell_info = PowerShellDetector(
            self.config
        ).detect()
        profile = SystemProfile(
            operating_system=os_info,
            python=python_info,
            powershell=powershell_info,
            shell=self._detect_shell(),
            hostname=socket.gethostname(),
            username=getpass.getuser(),
        )
        profile.toolkit_mode = self._determine_mode(profile)

        return profile

    @staticmethod
    def _detect_os() -> OperatingSystem:
        system = platform.system().lower()
        handlers = {
            "windows": OperatingSystem.WINDOWS,
            "linux": OperatingSystem.LINUX,
            "darwin": OperatingSystem.MACOS,
        }

        return handlers.get(
            system,
            OperatingSystem.UNKNOWN,
        )

    @staticmethod
    def _unknown_os() -> OperatingSystemInfo:
        return OperatingSystemInfo(
            family=OperatingSystem.UNKNOWN,
            name="Unknown",
            version="Unknown",
            architecture=Architecture.UNKNOWN,
        )

    @staticmethod
    def _detect_shell() -> Runtime:
        # Launch scripts provide the most reliable indication.
        launcher_shell = os.environ.get(
            "IT_TOOLKIT_LAUNCHER_SHELL",
            "",
        ).lower()
        shell_map = {
            "powershell": Runtime.POWERSHELL,
            "pwsh": Runtime.POWERSHELL,
            "cmd": Runtime.CMD,
            "bash": Runtime.BASH,
            "zsh": Runtime.ZSH,
        }
        if launcher_shell in shell_map:
            return shell_map[launcher_shell]
        if os.environ.get("PSModulePath"):
            return Runtime.POWERSHELL
        shell_name = os.path.basename(
            os.environ.get("SHELL", "")
        ).lower()
        return shell_map.get(
            shell_name,
            Runtime.UNKNOWN,
        )

    def _determine_mode(
        self,
        profile: SystemProfile,
    ) -> ToolkitMode:
        if profile.python.meets_requirement:
            return ToolkitMode.MODERN
        if self.config.get(
            "behavior.allow_legacy_mode",
            True,
        ):
            return ToolkitMode.LEGACY
        return ToolkitMode.LIMITED