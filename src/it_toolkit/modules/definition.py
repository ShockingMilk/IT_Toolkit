from dataclasses import dataclass, field

from it_toolkit.enums import (
    CapabilityType,
    ModuleSafety,
    OperatingSystem,
)

from it_toolkit.modules.dependency import ModuleDependency


@dataclass(frozen=True)
class ModuleDefinition:
    module_id: str
    name: str
    category: str
    description: str

    supported_operating_systems: tuple[OperatingSystem, ...]

    required_capabilities: tuple[CapabilityType, ...] = field(
        default_factory=tuple
    )

    dependencies: tuple[ModuleDependency, ...] = field(
        default_factory=tuple
    )

    safety: ModuleSafety = ModuleSafety.READ_ONLY

    def __post_init__(self):
        if not self.module_id.strip():
            raise ValueError("Module ID cannot be empty.")

        if not self.name.strip():
            raise ValueError("Module name cannot be empty.")

        if not self.category.strip():
            raise ValueError("Module category cannot be empty.")

        if not self.supported_operating_systems:
            raise ValueError(
                "A module must declare at least one supported operating system."
            )

        if len(set(self.supported_operating_systems)) != len(
            self.supported_operating_systems
        ):
            raise ValueError(
                "Supported operating systems cannot contain duplicates."
            )