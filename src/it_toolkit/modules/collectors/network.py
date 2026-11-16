import ipaddress
import json
import re
import socket
from pathlib import Path

from it_toolkit.enums import OperatingSystem
from it_toolkit.modules.collectors.command import run_command


def _linux_network() -> dict:
    interfaces = []
    gateways = []
    warnings = []

    address_result = run_command(
        ["ip", "-j", "address", "show"]
    )

    if address_result["returncode"] == 0:
        try:
            raw_interfaces = json.loads(
                address_result["stdout"]
            )

            for item in raw_interfaces:
                addresses = []

                for address in item.get("addr_info", []):
                    addresses.append({
                        "family": address.get("family"),
                        "address": address.get("local"),
                        "prefix_length": address.get("prefixlen"),
                                        "scope": address.get("scope"),
                    })

                interfaces.append({
                    "name": item.get("ifname"),
                    "state": item.get("operstate"),
                    "addresses": addresses,
                })

        except (ValueError, TypeError):
            warnings.append(
                "Unable to parse Linux interface information."
            )
    else:
        warnings.append(
            "The ip command is unavailable or failed."
        )

    route_result = run_command(
        ["ip", "-j", "route", "show"]
    )

    routes = []

    if route_result["returncode"] == 0:
        try:
            routes = json.loads(route_result["stdout"])
            
            for route in routes:
                if route.get("dst") != "default":
                    continue

                gateway = route.get("gateway")

                if gateway:
                    gateways.append({
                        "address": gateway,
                        "interface": route.get("dev"),
                    })
        except (ValueError, TypeError):
            warnings.append("Unable to parse Linux route table.")

    dns_servers = []

    try:
        with open(
            "/etc/resolv.conf",
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                match = re.match(
                    r"^\s*nameserver\s+(\S+)",
                    line,
                )

                if match:
                    dns_servers.append(match.group(1))

    except OSError:
        warnings.append(
            "Unable to read /etc/resolv.conf."
        )

    return {
        "interfaces": interfaces,
        "default_gateways": gateways,
        "dns_servers": dns_servers,
        "routes": routes,
        "warnings": warnings,
    }


def _windows_network() -> dict:
    interfaces = []
    gateways = []
    dns_servers = []
    warnings = []

    result = run_command(["ipconfig", "/all"])

    if result["returncode"] != 0:
        return {
            "interfaces": [],
            "default_gateways": [],
            "dns_servers": [],
            "routes": [],
            "warnings": ["ipconfig could not be executed."],
        }

    current = None
    continuation_field = None

    def add_address(target, value):
        value = value.replace("(Preferred)", "").strip()
        value = value.split("%", 1)[0].strip()

        try:
            parsed = ipaddress.ip_address(value)
        except ValueError:
            return

        target.append({
            "family": "ipv4" if parsed.version == 4 else "ipv6",
            "address": value,
            "prefix_length": None,
            "scope": None,
        })

    for line in result["stdout"].splitlines():
        stripped = line.strip()

        if not stripped:
            continuation_field = None
            continue

        header = re.match(
            r"^(.+ adapter .+):$",
            stripped,
            re.IGNORECASE,
        )

        if header:
            if current:
                interfaces.append(current)

            current = {
                "name": header.group(1),
                "state": "unknown",
                "addresses": [],
            }
            continuation_field = None
            continue

        if current is None:
            continue

        if "Media disconnected" in stripped:
            current["state"] = "down"
            continuation_field = None
            continue

        if "IPv4 Address" in stripped or "IPv6 Address" in stripped:
            add_address(
                current["addresses"],
                stripped.split(":", 1)[-1],
            )
            continuation_field = None
            continue

        if "Default Gateway" in stripped:
            continuation_field = "gateway"
            value = stripped.split(":", 1)[-1].strip()

            if value:
                try:
                    ipaddress.ip_address(value)
                    gateways.append({
                        "address": value,
                        "interface": current["name"],
                    })
                except ValueError:
                    pass

            continue

        if "DNS Servers" in stripped:
            continuation_field = "dns"
            value = stripped.split(":", 1)[-1].strip()

            if value:
                try:
                    ipaddress.ip_address(value)
                    dns_servers.append(value)
                except ValueError:
                    pass

            continue

        if continuation_field in {"dns", "gateway"}:
            try:
                ipaddress.ip_address(stripped)
            except ValueError:
                continuation_field = None
                continue

            if continuation_field == "dns":
                dns_servers.append(stripped)
            else:
                gateways.append({
                    "address": stripped,
                    "interface": current["name"],
                })

    if current:
        interfaces.append(current)

    route_result = run_command(["route", "print", "-4"])

    route_text = (
        route_result["stdout"][:12000]
        if route_result["returncode"] == 0
        else ""
    )

    routes = (
        [{"raw": route_text}]
        if route_text
        else []
    )

    return {
        "interfaces": interfaces,
        "default_gateways": gateways,
        "dns_servers": sorted(set(dns_servers)),
        "routes": routes,
        "warnings": warnings,
    }


def _macos_network() -> dict:
    interfaces = []
    gateways = []
    dns_servers = []
    warnings = []

    result = run_command(["ifconfig", "-a"])

    if result["returncode"] == 0:
        current = None

        for line in result["stdout"].splitlines():
            header = re.match(
                r"^([^\s:]+):\s+flags=",
                line,
            )

            if header:
                if current:
                    interfaces.append(current)

                current = {
                    "name": header.group(1),
                    "state": (
                        "up"
                        if "UP" in line.split("<", 1)[-1].split(">", 1)[0]
                        else "down"
                    ),
                    "addresses": [],
                }
                continue

            if current is None:
                continue

            ipv4 = re.search(
                r"\binet\s+(\d+\.\d+\.\d+\.\d+)",
                line,
            )

            ipv6 = re.search(
                r"\binet6\s+([0-9a-fA-F:]+)",
                line,
            )

            if ipv4:
                current["addresses"].append({
                    "family": "ipv4",
                    "address": ipv4.group(1),
                    "prefix_length": None,
                    "scope": None,
                })

            if ipv6:
                current["addresses"].append({
                    "family": "ipv6",
                    "address": ipv6.group(1),
                    "prefix_length": None,
                    "scope": None,
                })

        if current:
            interfaces.append(current)
    else:
        warnings.append("ifconfig could not be executed.")

    gateway_result = run_command(
        ["route", "-n", "get", "default"]
    )

    if gateway_result["returncode"] == 0:
        match = re.search(
            r"^\s*gateway:\s*(\S+)",
            gateway_result["stdout"],
            re.MULTILINE,
        )

        if match:
            gateways.append({
                "address": match.group(1),
                "interface": None,
            })

    route_table_result = run_command(["netstat", "-rn"])
    routes = (
        [{"raw": route_table_result["stdout"][:12000]}]
        if route_table_result["returncode"] == 0
        else []
    )

    dns_result = run_command(["scutil", "--dns"])

    if dns_result["returncode"] == 0:
        for match in re.finditer(
            r"nameserver\[\d+\]\s*:\s*(\S+)",
            dns_result["stdout"],
        ):
            dns_servers.append(match.group(1))

    return {
        "interfaces": interfaces,
        "default_gateways": gateways,
        "dns_servers": sorted(set(dns_servers)),
        "routes": routes,
        "warnings": warnings,
    }


def collect_network_information(
    operating_system: OperatingSystem,
) -> dict:
    collectors = {
        OperatingSystem.WINDOWS: _windows_network,
        OperatingSystem.LINUX: _linux_network,
        OperatingSystem.MACOS: _macos_network,
    }

    collector = collectors.get(operating_system)

    if collector is None:
        return {
            "interfaces": [],
            "default_gateways": [],
            "dns_servers": [],
            "routes": [],
            "warnings": [
                "Network collection is unsupported on this operating system."
            ],
        }

    data = collector()

    data["interface_names"] = [
        item["name"]
        for item in data["interfaces"]
        if item.get("name")
    ]

    return data