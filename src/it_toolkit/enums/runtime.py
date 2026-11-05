from enum import Enum

class Runtime(str, Enum):
    PYTHON = "python"
    POWERSHELL = "powershell"
    BASH = "bash"
    ZSH = "zsh"
    CMD = "cmd"
    UNKNOWN = "unknown"