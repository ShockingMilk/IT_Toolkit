import platform

from it_toolkit.detectors.base_detector import BaseDetector
from it_toolkit.enums import Architecture, OperatingSystem
from it_toolkit.models.operating_system import OperatingSystemInfo

class WindowsDetector(BaseDetector):
    def detect(self) -> OperatingSystemInfo:
        name = "Windows"
        version = platform.win32_ver()[1] or platform.version()
        build = platform.win32_ver()[2] or None
        architecture = self._detect_architecture()

        return OperatingSystemInfo(
            family=OperatingSystem.WINDOWS,
            name=name,
            version=version,
            architecture=architecture,
            build=build,
            kernel=platform.release(),
        )

    @staticmethod
    def _detect_architecture() -> Architecture:
        machine = platform.machine().lower()

        # A 32-bit Python process can run on 64-bit Windows.
        import os

        machine = os.environ.get(
            "PROCESSOR_ARCHITEW6432",
            os.environ.get("PROCESSOR_ARCHITECTURE", machine),
        ).lower()
        if machine in ("x86_64", "amd64", "x64"):
            return Architecture.X86_64
        if machine in ("x86", "i386", "i686"):
            return Architecture.X86
        if machine in ("arm64", "aarch64"):
            return Architecture.ARM64
        if machine.startswith("arm"):
            return Architecture.ARM32
        return Architecture.UNKNOWN