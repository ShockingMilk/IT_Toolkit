from enum import Enum

class Architecture(str, Enum):
    X86 = "x86"
    X86_64 = "x86_64"
    ARM32 = "arm32"
    ARM64 = "arm64"
    UNKNOWN = "unknown"