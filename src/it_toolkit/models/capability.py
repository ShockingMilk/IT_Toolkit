from dataclasses import dataclass

from it_toolkit.enums import CapabilityType

@dataclass
class Capability:
    name: CapabilityType
    available: bool
    reason: str | None = None