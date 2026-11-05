# Detection Engine

## Purpose

Identify the environment before loading platform-specific
toolkit functionality.

## Detected Information

### Operating System

- Operating system family
- Distribution
- Version
- Kernel
- Architecture

### Python

- Version
- Executable
- Implementation
- Minimum requirement status

### PowerShell

- Installation path
- Version
- Edition
- Minimum requirement status

### Shell

- Launching shell

## PowerShell Compatibility

PowerShell installations are evaluated independently.

Windows PowerShell 5.x is classified as legacy when
the configured minimum is PowerShell 7.1.

PowerShell 7.x is evaluated against the configured
minimum version.

## Output

The detection engine generates:

    reports/system_profile.json

This profile becomes the input to future toolkit menus
and diagnostic modules.
