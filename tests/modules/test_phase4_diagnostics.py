import unittest

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from it_toolkit.enums import (
    CapabilityType,
    DiagnosticStatus,
    OperatingSystem,
)

from it_toolkit.models.capability import Capability
from it_toolkit.modules.context import ModuleContext

from it_toolkit.modules.builtin.hardware_overview import (
    HardwareOverviewModule,
)

from it_toolkit.modules.builtin.network.interface_diagnostics import (
    InterfaceDiagnosticsModule,
)

from it_toolkit.modules.builtin.network.connectivity_diagnostics import (
    ConnectivityDiagnosticsModule,
)

from it_toolkit.modules.builtin.storage.filesystem_diagnostics import (
    FilesystemDiagnosticsModule,
)


def make_context(config=None):
    profile = SimpleNamespace(
        operating_system=SimpleNamespace(
            family=OperatingSystem.LINUX,
        ),
        capabilities=[
            Capability(
                name=CapabilityType.SYSTEM_INFORMATION,
                available=True,
            ),
            Capability(
                name=CapabilityType.NETWORK,
                available=True,
            ),
            Capability(
                name=CapabilityType.STORAGE,
                available=True,
            ),
        ],
    )

    return ModuleContext(
        profile=profile,
        toolkit_root=Path("."),
        config=config or {},
    )


class TestHardwareOverview(unittest.TestCase):

    @patch(
        "it_toolkit.modules.builtin.hardware_overview.collect_system_information"
    )
    def test_hardware_overview(self, collector):
        collector.return_value = {
            "platform": {"system": "Linux"},
            "cpu": {"logical_processors": 4},
            "memory": {"available": True},
            "python": {"version": "3.11"},
        }

        result = HardwareOverviewModule().run(
            make_context()
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SUCCESS,
        )

        self.assertEqual(
            result.data["cpu"]["logical_processors"],
            4,
        )


class TestNetworkDiagnostics(unittest.TestCase):

    @patch(
        "it_toolkit.modules.builtin.network.interface_diagnostics.collect_network_information"
    )
    def test_passive_interface_inspection(self, collector):
        collector.return_value = {
            "interfaces": [
                {
                    "name": "eth0",
                    "addresses": [],
                }
            ],
            "interface_names": ["eth0"],
            "default_gateways": [],
            "dns_servers": ["10.0.0.1"],
            "routes": [],
            "warnings": [],
        }

        result = InterfaceDiagnosticsModule().run(
            make_context()
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SUCCESS,
        )

        self.assertEqual(
            result.data["interface_names"],
            ["eth0"],
        )

        collector.assert_called_once()

    def test_active_tests_skip_without_targets(self):
        context = make_context({
            "network": {
                "active_tests": {
                    "enabled": True,
                    "dns_targets": [],
                    "tcp_targets": [],
                    "test_gateways": False,
                }
            }
        })

        result = ConnectivityDiagnosticsModule().run(
            context
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SKIPPED,
        )

    def test_active_tests_disabled(self):
        context = make_context({
            "network": {
                "active_tests": {
                    "enabled": False,
                }
            }
        })

        result = ConnectivityDiagnosticsModule().run(
            context
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SKIPPED,
        )


class TestStorageDiagnostics(unittest.TestCase):

    @patch(
        "it_toolkit.modules.builtin.storage.filesystem_diagnostics.collect_storage_information"
    )
    def test_filesystem_inspection(self, collector):
        collector.return_value = {
            "filesystem_count": 1,
            "filesystems": [
                {
                    "mountpoint": "/",
                    "total_bytes": 1000,
                    "used_bytes": 400,
                    "free_bytes": 600,
                    "usage_percent": 40.0,
                    "available": True,
                }
            ],
            "warnings": [],
        }

        result = FilesystemDiagnosticsModule().run(
            make_context()
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SUCCESS,
        )

        self.assertEqual(
            result.data["filesystem_count"],
            1,
        )


if __name__ == "__main__":
    unittest.main()