import ctypes
import re
import shutil
from pathlib import Path

from it_toolkit.enums import OperatingSystem


def _linux_mounts() -> list[dict]:
    mounts = []

    try:
        with open(
            "/proc/self/mounts",
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                parts = line.split()

                if len(parts) < 3:
                    continue

                device, mountpoint, filesystem = parts[:3]

                # Decode common mount-table escape sequences.
                mountpoint = (
                    mountpoint
                    .replace("\\040", " ")
                    .replace("\\011", "\t")
                    .replace("\\134", "\\")
                )

                if filesystem in {
                    "proc", "sysfs", "devtmpfs", "devpts",
                    "tmpfs", "cgroup", "cgroup2", "overlay",
                    "securityfs", "debugfs", "tracefs",
                    "pstore", "configfs", "mqueue",
                    "hugetlbfs", "fusectl", "autofs",
                }:
                    continue

                mounts.append({
                    "device": device,
                    "mountpoint": mountpoint,
                    "filesystem": filesystem,
                })

    except OSError:
        return []

    return mounts


def _macos_mounts() -> list[dict]:
    import subprocess

    try:
        result = subprocess.run(
            ["mount"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return []

    except (OSError, subprocess.TimeoutExpired):
        return []

    mounts = []

    for line in result.stdout.splitlines():
        match = re.match(
            r"(.+?) on (.+?) \(([^,]+)",
            line,
        )

        if not match:
            continue

        device, mountpoint, filesystem = match.groups()

        if filesystem in {
            "devfs", "autofs", "nullfs",
        }:
            continue

        mounts.append({
            "device": device,
            "mountpoint": mountpoint,
            "filesystem": filesystem,
        })

    return mounts


def _windows_mounts() -> list[dict]:
    mounts = []

    try:
        drive_mask = ctypes.windll.kernel32.GetLogicalDrives()

        for index in range(26):
            if not drive_mask & (1 << index):
                continue

            drive = f"{chr(65 + index)}:\\"

            mounts.append({
                "device": drive,
                "mountpoint": drive,
                "filesystem": "unknown",
            })

    except (AttributeError, OSError):
        return []

    return mounts


def collect_storage_information(
    operating_system: OperatingSystem,
) -> dict:
    collectors = {
        OperatingSystem.WINDOWS: _windows_mounts,
        OperatingSystem.LINUX: _linux_mounts,
        OperatingSystem.MACOS: _macos_mounts,
    }

    collector = collectors.get(operating_system)

    if collector is None:
        return {
            "filesystems": [],
            "warnings": [
                "Storage collection is unsupported on this operating system."
            ],
        }

    mounts = collector()
    filesystems = []
    warnings = []

    for mount in mounts:
        mountpoint = mount["mountpoint"]

        try:
            usage = shutil.disk_usage(mountpoint)

            total = usage.total
            used = usage.used
            free = usage.free

            filesystems.append({
                **mount,
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "usage_percent": (
                    round((used / total) * 100, 2)
                    if total
                    else None
                ),
                "available": True,
            })

        except (OSError, PermissionError) as error:
            filesystems.append({
                **mount,
                "total_bytes": None,
                "used_bytes": None,
                "free_bytes": None,
                "usage_percent": None,
                "available": False,
                "error": str(error),
            })

            warnings.append(
                f"Unable to inspect mount point: {mountpoint}"
            )

    return {
        "filesystems": filesystems,
        "filesystem_count": len(filesystems),
        "warnings": warnings,
    }