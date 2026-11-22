from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from it_toolkit.models.system_profile import SystemProfile


def _freeze(value):
    """
    Recursively convert configuration values into read-only structures.
    """

    if isinstance(value, dict):
        return MappingProxyType({
            key: _freeze(item)
            for key, item in value.items()
        })

    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)

    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)

    return value


@dataclass(frozen=True)
class ModuleContext:
    profile: SystemProfile
    toolkit_root: Path
    config: Mapping[str, Any] = field(default_factory=dict)

    runtime_executor: Any | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    execution_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    def __post_init__(self):
        object.__setattr__(
            self,
            "toolkit_root",
            Path(self.toolkit_root),
        )

        object.__setattr__(
            self,
            "config",
            _freeze(deepcopy(dict(self.config))),
        )