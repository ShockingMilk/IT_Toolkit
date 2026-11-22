from enum import Enum


class RuntimeOperationStatus(str, Enum):
    STAGED = "staged"
    SELECTED = "selected"
    EXECUTED = "executed"
    FAILED = "failed"
    SKIPPED = "skipped"