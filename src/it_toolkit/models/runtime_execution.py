from dataclasses import dataclass, field


@dataclass
class RuntimeExecutionResult:
    """Result of invoking an explicitly selected portable runtime."""

    runtime_id: str
    runtime: str
    version: str

    executable: str
    arguments: list[str] = field(default_factory=list)

    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""

    started: bool = False
    timed_out: bool = False
    error: str | None = None

    @property
    def success(self) -> bool:
        return (
            self.started
            and not self.timed_out
            and self.error is None
            and self.return_code == 0
        )

    def to_dict(self) -> dict:
        return {
            "runtime_id": self.runtime_id,
            "runtime": self.runtime,
            "version": self.version,
            "executable": self.executable,
            "arguments": list(self.arguments),
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started": self.started,
            "timed_out": self.timed_out,
            "error": self.error,
            "success": self.success,
        }