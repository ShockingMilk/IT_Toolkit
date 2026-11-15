from dataclasses import dataclass

from it_toolkit.enums import DependencyType


@dataclass(frozen=True)
class ModuleDependency:
    name: str
    dependency_type: DependencyType

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Dependency name cannot be empty.")