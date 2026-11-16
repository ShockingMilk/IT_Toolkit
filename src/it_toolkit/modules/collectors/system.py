import ctypes
import platform
import re
import sys

from it_toolkit.enums import OperatingSystem
from it_toolkit.modules.collectors.command import run_command


def _cpu_model() -> str | None:
    processor = platform.processor().strip()

    if processor:
        return processor

    system = platform.system().lower()

    if system == "linux":
        try:
            with open(
                "/proc/cpuinfo",
                "r",
                encoding="utf-8",
            ) as file:
                for line in file:
                    if line.lower().startswith(
                        ("model name", "hardware")
                    ):
                        return line.split(":", 1)[-1].strip()
        except OSError:
            pass

    if system == "darwin":
        result = run_command(
            ["sysctl", "-n", "machdep.cpu.brand_string"]
        )

        if result["returncode"] == 0 and result["stdout"]:
            return result["stdout"]

    return platform.machine() or None


def _linux_memory() -> dict:
    values = {}

    try:
        with open(
            "/proc/meminfo",
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                match = re.match(
                    r"^(\w+):\s+(\d+)\s+kB",
                    line,
                )

                if match:
                    values[match.group(1)] = (
                        int(match.group(2)) * 1024
                    )

    except OSError as error:
        return {
            "available": False,
            "error": str(error),
        }

    total = values.get("MemTotal")
    available = values.get("MemAvailable")

    if total is None:
        return {
            "available": False,
            "error": "MemTotal was not found.",
        }

    return {
        "available": True,
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": (
            total - available
            if available is not None
            else None
        ),
    }


def _windows_memory() -> dict:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)

    try:
        result = ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(status)
        )

        if not result:
            return {
                "available": False,
                "error": "GlobalMemoryStatusEx failed.",
            }

        return {
            "available": True,
            "total_bytes": status.ullTotalPhys,
            "available_bytes": status.ullAvailPhys,
            "used_bytes": (
                status.ullTotalPhys - status.ullAvailPhys
            ),
            "usage_percent": status.dwMemoryLoad,
        }

    except (AttributeError, OSError) as error:
        return {
            "available": False,
            "error": str(error),
        }


def _macos_memory() -> dict:
    total_result = run_command(
        ["sysctl", "-n", "hw.memsize"]
    )

    if (
        total_result["returncode"] != 0
        or not total_result["stdout"].isdigit()
    ):
        return {
            "available": False,
            "error": "Unable to determine physical memory.",
        }

    total = int(total_result["stdout"])

    vm_result = run_command(["vm_stat"])

    if vm_result["returncode"] != 0:
        return {
            "available": True,
            "total_bytes": total,
            "available_bytes": None,
            "used_bytes": None,
        }

    page_match = re.search(
        r"page size of (\d+) bytes",
        vm_result["stdout"],
    )

    page_size = (
        int(page_match.group(1))
        if page_match
        else 4096
    )

    page_counts = {}

    for line in vm_result["stdout"].splitlines():
        match = re.match(
            r"([^:]+):\s+([\d.]+)",
            line,
        )

        if match:
            page_counts[match.group(1).lower()] = int(
                float(match.group(2))
            )

    free_pages = sum(
        page_counts.get(name, 0)
        for name in (
            "pages free",
            "pages inactive",
            "pages speculative",
        )
    )

    available = free_pages * page_size

    return {
        "available": True,
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": max(total - available, 0),
    }


def collect_system_information() -> dict:
    """
    Collect common hardware and runtime information.

    Missing values are represented as None or unavailable fields.
    """

    system = platform.system().lower()

    memory_collectors = {
        "windows": _windows_memory,
        "linux": _linux_memory,
        "darwin": _macos_memory,
    }

    memory_collector = memory_collectors.get(system)

    memory = (
        memory_collector()
        if memory_collector
        else {
            "available": False,
            "error": "Unsupported operating system.",
        }
    )

    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": _cpu_model(),
            "architecture": platform.architecture()[0],
        },
        "cpu": {
            "logical_processors": (
                __import__("os").cpu_count()
            ),
            "model": _cpu_model(),
        },
        "memory": memory,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
    }