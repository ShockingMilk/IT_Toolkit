import platform
from pathlib import Path

from it_toolkit.detectors.base_detector import BaseDetector
from it_toolkit.enums import Architecture, OperatingSystem
from it_toolkit.models.operating_system import OperatingSystemInfo

class LinuxDetector(BaseDetector):
    def detect(self) -> OperatingSystemInfo:
        release = self._read_os_release()

        return OperatingSystemInfo(
            family=OperatingSystem.LINUX,
            name=release.get("NAME", "Linux"),
            version=release.get("VERSION_ID", platform.release()),
            architecture=self._detect_architecture(),
            distribution=release.get("ID", "unknown"),
            build=release.get("BUILD_ID"),
            kernel=platform.release(),
        )

    @staticmethod
    def _read_os_release() -> dict:
        release_path = Path("/etc/os-release")

        if not release_path.exists():
            return {}
        result = {}

        try:
            for line in release_path.read_text(
                encoding="utf-8"
            ).splitlines():
                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                result[key] = value.strip().strip('"').strip("'")
        except OSError:
            return {}
        return result

    @staticmethod
    def _detect_architecture() -> Architecture:
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return Architecture.X86_64
        if machine in ("i386", "i486", "i586", "i686", "x86"):
            return Architecture.X86
        if machine in ("aarch64", "arm64"):
            return Architecture.ARM64
        if machine.startswith(("arm", "armv")):
            return Architecture.ARM32
        return Architecture.UNKNOWN