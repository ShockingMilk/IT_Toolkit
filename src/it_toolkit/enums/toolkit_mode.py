from enum import Enum

class ToolkitMode(str, Enum):
    MODERN = "modern"
    LEGACY = "legacy"
    LIMITED = "limited"
    UNKNOWN = "unknown"