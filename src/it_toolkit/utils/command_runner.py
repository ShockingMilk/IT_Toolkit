import subprocess

from dataclasses import dataclass


@dataclass
class CommandResult:

    success: bool

    stdout: str = ""

    stderr: str = ""

    return_code: int = -1


def run_command(
    command: list[str],
    timeout: int = 10,
) -> CommandResult:
    """
    Execute a system command safely.

    No shell=True, so arguments are passed directly.
    """

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        return CommandResult(
            success=result.returncode == 0,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            return_code=result.returncode,
        )

    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        PermissionError,
        OSError,
    ) as error:

        return CommandResult(
            success=False,
            stderr=str(error),
        )