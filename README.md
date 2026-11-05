# IT Toolkit

A modular, cross-platform IT troubleshooting and diagnostics toolkit.

Designed for Windows, Linux, and macOS environments, with an emphasis
on offline operation and air-gapped networks.

## Objectives

- Cross-platform system detection
- PowerShell version detection
- Python runtime detection
- Architecture identification
- Modular diagnostic tools
- Offline dependency management
- Standardized system reporting
- Future bootable recovery environment integration

## Supported Platforms

### Windows

- Windows PowerShell 5.x
- PowerShell 7.x
- Python 3.10+

### Linux

- Debian
- Ubuntu
- Other Linux distributions

### macOS

- Intel
- Apple Silicon

## Requirements

- Python 3.10 or newer
- No third-party Python dependencies for Phase 1

PowerShell is detected independently and is not required to run
the Python detection engine.

## Launching

### Windows

Run:

    scripts/START-HERE.bat

### PowerShell

Run:

    .\scripts\START-HERE.ps1

### Linux / macOS

Run:

    chmod +x scripts/START-HERE.sh

    ./scripts/START-HERE.sh

## Development

Create a virtual environment:

    python -m venv .venv

Activate it.

Windows:

    .venv\Scripts\Activate.ps1

Linux/macOS:

    source .venv/bin/activate

Install the project in editable mode:

    python -m pip install -e .

No Internet access is required when using an already available
Python installation and the project source.

## Testing

Run:

    python -m unittest discover -s tests -v

## Configuration

Main configuration:

    config/toolkit.json

Default profile:

    config/profiles/default.json

## Reports

Generated reports are stored under:

    reports/

These are runtime artifacts and are excluded from Git.

## Development Roadmap

1. Detection engine
2. Platform-specific menus
3. Core IT diagnostic modules
4. Offline dependency management
5. Reporting
6. Bootable recovery environment

## Design Philosophy

The toolkit uses modular components, centralized enums,
platform-specific implementations, and a common system profile.

The detection engine should not depend on the availability
of the diagnostic tools it is intended to help troubleshoot.
