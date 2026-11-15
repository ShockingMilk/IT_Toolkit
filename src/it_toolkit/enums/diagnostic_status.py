from enum import Enum


class DiagnosticStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"