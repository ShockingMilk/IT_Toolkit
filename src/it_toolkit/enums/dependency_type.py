from enum import Enum


class DependencyType(str, Enum):
    EXECUTABLE = "executable"
    PYTHON_MODULE = "python_module"