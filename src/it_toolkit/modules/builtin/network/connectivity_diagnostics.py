
"""Active network connectivity diagnostics.

These tests generate network traffic but do not modify system configuration.
They are disabled or skipped when no test targets are configured.
"""

from __future__ import annotations

import socket
import time

from collections.abc import Mapping
from typing import Any

from it_toolkit.enums import CapabilityType, DiagnosticStatus, ModuleSafety, OperatingSystem
from it_toolkit.modules.base import DiagnosticModule
from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.definition import ModuleDefinition
from it_toolkit.modules.results import DiagnosticResult


class ConnectivityDiagnosticsModule(DiagnosticModule):
    """Run optional DNS, TCP, and gateway connectivity tests."""

    definition = ModuleDefinition(
        module_id="network.connectivity",
        name="Active Connectivity Tests",
        category="Network Diagnostics",
        description=(
            "Optionally tests DNS resolution, TCP connectivity, "
            "and gateway reachability using configured targets."
        ),
        supported_operating_systems=(
            OperatingSystem.WINDOWS,
            OperatingSystem.LINUX,
            OperatingSystem.MACOS,
        ),
        required_capabilities=(CapabilityType.NETWORK,),
        dependencies=(),
        safety=ModuleSafety.READ_ONLY,
    )

    def run(self, context: ModuleContext) -> DiagnosticResult:
        """Execute configured connectivity tests."""

        started = time.monotonic()

        network_config = context.config.get("network", {})

        if not isinstance(network_config, Mapping):
            network_config = {}

        active_config = network_config.get("active_tests", {})

        if not isinstance(active_config, Mapping):
            active_config = {}

        if not active_config.get("enabled", False):
            return self._result(
                status=DiagnosticStatus.SKIPPED,
                message="Active connectivity tests are disabled.",
                data={},
                started=started,
            )

        dns_targets = self._normalize_targets(
            active_config.get("dns_targets", [])
        )

        tcp_targets = self._normalize_targets(
            active_config.get("tcp_targets", [])
        )

        test_gateways = bool(
            active_config.get("test_gateways", False)
        )

        if not dns_targets and not tcp_targets and not test_gateways:
            return self._result(
                status=DiagnosticStatus.SKIPPED,
                message=(
                    "No DNS, TCP, or gateway connectivity targets "
                    "are configured."
                ),
                data={},
                started=started,
            )

        timeout = self._get_timeout(
            active_config.get("timeout_seconds", 3)
        )

        results: dict[str, Any] = {
            "dns": [],
            "tcp": [],
            "gateways": [],
            "configuration": {
                "timeout_seconds": timeout,
                "dns_target_count": len(dns_targets),
                "tcp_target_count": len(tcp_targets),
                "gateway_testing_enabled": test_gateways,
            },
        }

        warnings: list[str] = []

        # DNS resolution tests.
        for hostname in dns_targets[:20]:
            results["dns"].append(
                self._test_dns(hostname)
            )

        # TCP connection tests.
        for target in tcp_targets[:20]:
            result = self._test_tcp(target, timeout)

            if result is not None:
                results["tcp"].append(result)
            else:
                warnings.append(
                    f"Invalid TCP target configuration: {target!r}"
                )

        # Optional gateway reachability tests.
        if test_gateways:
            gateways = self._get_default_gateways(context)

            for gateway in gateways[:5]:
                results["gateways"].append(
                    self._test_gateway(gateway)
                )

            if not gateways:
                warnings.append(
                    "Gateway testing was enabled, but no default "
                    "gateways were available from the system profile."
                )

        all_tests = (
            results["dns"]
            + results["tcp"]
            + results["gateways"]
        )

        successful = sum(
            1 for item in all_tests
            if item.get("success") is True
        )

        failed = sum(
            1 for item in all_tests
            if item.get("success") is False
        )

        if warnings:
            status = DiagnosticStatus.PARTIAL
            message = "Connectivity tests completed with warnings."
        elif failed and successful:
            status = DiagnosticStatus.PARTIAL
            message = "Some connectivity tests succeeded and others failed."
        elif failed:
            status = DiagnosticStatus.WARNING
            message = "All configured connectivity tests failed."
        elif successful:
            status = DiagnosticStatus.SUCCESS
            message = "All configured connectivity tests succeeded."
        else:
            status = DiagnosticStatus.SKIPPED
            message = "No connectivity tests were executed."

        results["summary"] = {
            "total_tests": len(all_tests),
            "successful": successful,
            "failed": failed,
        }

        results["warnings"] = warnings

        return self._result(
            status=status,
            message=message,
            data=results,
            started=started,
        )

    @staticmethod
    def _normalize_targets(value: Any) -> list[Any]:
        """Normalize configured target values into a list."""

        if isinstance(value, str):
            return [value] if value.strip() else []

        if isinstance(value, (list, tuple)):
            return list(value)

        return []

    @staticmethod
    def _get_timeout(value: Any) -> float:
        """Return a validated timeout between 0.5 and 15 seconds."""

        try:
            timeout = float(value)
        except (TypeError, ValueError):
            timeout = 3.0

        return max(0.5, min(timeout, 15.0))

    @staticmethod
    def _test_dns(hostname: str) -> dict[str, Any]:
        """Resolve a hostname using the system DNS resolver."""

        started = time.monotonic()

        try:
            addresses = socket.getaddrinfo(
                hostname,
                None,
                type=socket.SOCK_STREAM,
            )

            resolved = sorted(
                {
                    item[4][0]
                    for item in addresses
                    if item[4]
                }
            )

            return {
                "target": hostname,
                "success": bool(resolved),
                "addresses": resolved,
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": None if resolved else "No addresses returned.",
            }

        except socket.gaierror as exc:
            return {
                "target": hostname,
                "success": False,
                "addresses": [],
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": str(exc),
            }

        except OSError as exc:
            return {
                "target": hostname,
                "success": False,
                "addresses": [],
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": str(exc),
            }

    @staticmethod
    def _test_tcp(
        target: Any,
        timeout: float,
    ) -> dict[str, Any] | None:
        """Attempt a TCP connection to a configured host and port."""

        if not isinstance(target, Mapping):
            return None

        host = target.get("host")
        port = target.get("port")

        if not isinstance(host, str) or not host.strip():
            return None

        # bool is a subclass of int, so explicitly reject it.
        if isinstance(port, bool) or not isinstance(port, int):
            return None

        if not 1 <= port <= 65535:
            return None

        started = time.monotonic()

        try:
            with socket.create_connection(
                (host.strip(), port),
                timeout=timeout,
            ):
                return {
                    "host": host,
                    "port": port,
                    "success": True,
                    "duration_seconds": round(
                        time.monotonic() - started, 3
                    ),
                    "error": None,
                }

        except OSError as exc:
            return {
                "host": host,
                "port": port,
                "success": False,
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": str(exc),
            }

    @staticmethod
    def _get_default_gateways(
        context: ModuleContext,
    ) -> list[str]:
        """Retrieve default gateways from the detected system profile."""

        gateways: list[str] = []

        profile = context.profile

        # The profile may expose network details as an attribute.
        network = getattr(profile, "network", None)

        if network is None:
            return gateways

        default_gateways = getattr(
            network,
            "default_gateways",
            [],
        )

        if isinstance(default_gateways, (list, tuple)):
            for gateway in default_gateways:
                if isinstance(gateway, str) and gateway.strip():
                    gateways.append(gateway.strip())

        return list(dict.fromkeys(gateways))

    @staticmethod
    def _test_gateway(gateway: str) -> dict[str, Any]:
        """Attempt one ping against a default gateway."""

        import platform
        import subprocess

        started = time.monotonic()

        system = platform.system().lower()

        if system == "windows":
            command = [
                "ping",
                "-n",
                "1",
                "-w",
                "1500",
                gateway,
            ]
        else:
            command = [
                "ping",
                "-c",
                "1",
                "-W",
                "2",
                gateway,
            ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )

            success = completed.returncode == 0

            return {
                "gateway": gateway,
                "success": success,
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": (
                    None
                    if success
                    else completed.stderr.strip()
                    or completed.stdout.strip()
                    or "Ping failed."
                ),
            }

        except FileNotFoundError:
            return {
                "gateway": gateway,
                "success": False,
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": "Ping executable was not found.",
            }

        except subprocess.TimeoutExpired:
            return {
                "gateway": gateway,
                "success": False,
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": "Ping command timed out.",
            }

        except OSError as exc:
            return {
                "gateway": gateway,
                "success": False,
                "duration_seconds": round(
                    time.monotonic() - started, 3
                ),
                "error": str(exc),
            }

    @staticmethod
    def _result(
        status: DiagnosticStatus,
        message: str,
        data: dict[str, Any],
        started: float,
    ) -> DiagnosticResult:
        """Create a standardized diagnostic result."""

        return DiagnosticResult(
            module_id="network.connectivity",
            module_name="Network Connectivity",
            status=status,
            summary=message,
            data=data,
            duration_seconds=round(
                time.monotonic() - started, 3
            ),
        )
