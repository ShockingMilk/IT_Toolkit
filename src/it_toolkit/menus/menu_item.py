from dataclasses import dataclass

from it_toolkit.enums import CapabilityType

@dataclass(frozen=True)
class MenuItem:
    key: str
    label: str
    action: str
    capability: CapabilityType | None = None
    description: str = ""