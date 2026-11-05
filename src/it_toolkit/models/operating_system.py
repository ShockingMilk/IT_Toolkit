from dataclasses import dataclass

from it_toolkit.enums import Architecture, OperatingSystem

@dataclass
class OperatingSystemInfo:
    family: OperatingSystem
    name: str
    version: str
    architecture: Architecture
    build: str | None = None
    distribution: str | None = None
    kernel: str | None = None