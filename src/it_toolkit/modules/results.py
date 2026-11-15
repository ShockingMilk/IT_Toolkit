from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from it_toolkit.enums import DiagnosticStatus


def _json_safe(value):
    """
    Convert common Python objects into JSON-compatible values.
    """

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    return repr(value)


@dataclass
class DiagnosticResult:
    module_id: str
    module_name: str

    status: DiagnosticStatus

    summary: str

    data: dict[str, Any] = field(default_factory=dict)

    warnings: list[str] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)

    started_at: str | None = None

    completed_at: str | None = None

    duration_seconds: float | None = None

    def to_dict(self) -> dict:
        return {
            "module_id": self.module_id,
            "module_name": self.module_name,
            "status": self.status.value,
            "summary": self.summary,
            "data": _json_safe(self.data),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
        }