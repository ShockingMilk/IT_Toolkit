# Diagnostic Modules

The IT Toolkit uses a modular diagnostic architecture.

Each diagnostic module:

- Declares its supported operating systems.
- Declares required capabilities.
- Declares dependencies when necessary.
- Uses a standardized execution context.
- Returns a DiagnosticResult.
- Defaults to read-only behavior.

## Privacy and Diagnostic Data

Diagnostic reports may contain information that identifies a user, computer, organization, or internal network.

Depending on the modules executed, reports may include:

- Computer hostnames and usernames
- Operating system and hardware information
- Local filesystem paths
- Network interface addresses
- DNS servers, gateways, and routing information
- Diagnostic errors and command output

Reports are intended for local troubleshooting and authorized IT review.

**Before sharing a report outside your organization, review it and remove any identifying or sensitive information.**

The IT Toolkit does not intentionally publish diagnostic reports. Users are responsible for reviewing exported information before distributing it.

## System Information

### System Overview

Displays information collected by the initial detection engine.

### Runtime Inventory

Displays detected Python and PowerShell installations.

### Hardware Overview

Collects:

- Processor model where available
- Logical processor count
- Physical memory
- Memory availability
- Platform and architecture information

Physical processor core counts and advanced hardware health
are not currently collected.

## Network Diagnostics

### Network Interface Inspection

Passive inspection of:

- Network interface names
- Interface addresses
- Interface state where available
- Default gateways
- DNS servers
- Routing information

Passive inspection does not intentionally initiate
connectivity tests.

Some information is collected through native operating
system commands. Availability depends on the installed
utilities and operating system permissions.

### Active Connectivity Tests

Active tests are a separate optional module.

Supported tests:

- DNS resolution
- TCP connection checks
- Optional gateway ping tests

Targets are configured in config/toolkit.json.

No public Internet endpoint is assumed or contacted by default.

Active tests generate network traffic but do not modify
network configuration.

## Storage Diagnostics

### Filesystem Inspection

Collects:

- Mounted filesystem
- Device or volume
- Filesystem type where available
- Total capacity
- Used capacity
- Available capacity
- Usage percentage

This module does not currently perform:

- SMART health checks
- Disk repair
- Filesystem repair
- Partition modification
- Disk benchmarking

## Safety

All Phase 4 modules are classified as read-only.

The toolkit does not:

- Change network settings
- Change DNS configuration
- Change routes
- Modify partitions
- Format filesystems
- Install software
- Repair operating systems

Active connectivity tests may generate network traffic.

## Configuration

Active network testing is controlled by the network.active_tests
section in config/toolkit.json.

Example:

    "network": {
        "active_tests": {
            "enabled": true,
            "timeout_seconds": 3,
            "test_gateways": false,
            "dns_targets": [],
            "tcp_targets": []
        }
    }

Targets should be appropriate for the environment being tested.
Internal DNS servers and internal application services are
valid targets in an air-gapped environment.
