from enum import Enum


class ModuleSafety(str, Enum):
    READ_ONLY = "read_only"
    SYSTEM_CHANGE = "system_change"