import platform

from it_toolkit.detectors.base_detector import BaseDetector
from it_toolkit.enums import Architecture, OperatingSystem
from it_toolkit.models.operating_system import OperatingSystemInfo

class MacOSDetector(BaseDetector):
    def detect(self) -> OperatingSystemInfo:
        version = platform.mac_ver()[0]

        if not version:
            version = platform.release()

        return OperatingSystemInfo(
            family=OperatingSystem.MACOS,
            name="macOS",
            version=version,
            architecture=self._detect_architecture(),
            distribution="macos",
            kernel=platform.release(),
        )

    @staticmethod
    def _detect_architecture() -> Architecture:
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return Architecture.X86_64
        if machine in ("arm64", "aarch64"):
            return Architecture.ARM64
        return Architecture.UNKNOWN