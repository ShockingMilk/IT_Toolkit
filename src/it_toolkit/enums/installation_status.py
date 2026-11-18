from enum import Enum

class InstallationStatus(str, Enum):
    INSTALLED = "installed"
    STAGED = "staged"
    FAILED = "failed"
    SKIPPED = "skipped"