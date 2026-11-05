from dataclasses import dataclass

@dataclass
class PythonInfo:
    installed: bool
    version: str | None = None
    executable: str | None = None
    implementation: str | None = None
    meets_requirement: bool = False