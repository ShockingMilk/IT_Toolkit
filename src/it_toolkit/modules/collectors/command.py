import shutil
import subprocess


def run_command(
    command: list[str],
    timeout: int = 5,
) -> dict:
    """
    Run a native diagnostic command without invoking a shell.

    Returns a consistent result even when the command is unavailable.
    """

    if not command:
        return {
            "available": False,
            "stdout": "",
            "stderr": "No command specified.",
            "returncode": None,
        }

    executable = shutil.which(command[0])

    if executable is None:
        return {
            "available": False,
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
            "returncode": None,
        }

    try:
        result = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        return {
            "available": True,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "stdout": "",
            "stderr": "Command timed out.",
            "returncode": None,
        }

    except OSError as error:
        return {
            "available": False,
            "stdout": "",
            "stderr": str(error),
            "returncode": None,
        }