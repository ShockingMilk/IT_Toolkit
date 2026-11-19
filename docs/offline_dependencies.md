# Offline Dependency Management

## Purpose

The offline dependency system provides a controlled repository for
packages that may be used by IT Toolkit.

It is divided into two implementation phases:

- **Phase 6A — Offline Package Repository:** inventory, manifest
  validation, integrity checks, and compatibility evaluation.
- **Phase 6B — Installation and Verification:** explicitly approved
  installation of local Python wheels, executable staging, and
  persistent operation records.

Phase 6C will address portable runtime management separately.

## Repository Layout

    dependencies/
        repository/
            manifest.json
            README.md
            packages/
            runtimes/

The manifest is the authoritative inventory of packages.

Package paths are relative to the repository directory.

## Manifest Format

Each package entry contains:

- `package_id`
- `name`
- `version`
- `type`
- `file`
- `sha256`
- `operating_systems`
- `architectures`

Optional Python compatibility fields:

- `python_min_version`
- `python_max_version`
- `python_implementation`

Supported dependency types are defined by the centralized
`DependencyType` enum.

## Repository Inspection

The dependency manager:

1. Loads the repository manifest.
2. Validates the manifest structure.
3. Rejects duplicate package/version entries.
4. Rejects unsafe relative paths.
5. Checks that package files exist.
6. Calculates SHA-256 checksums.
7. Compares calculated checksums against manifest values.
8. Optionally evaluates compatibility against `SystemProfile`.

Compatibility checks include:

- Operating system
- Processor architecture
- Python minimum version, when specified
- Python maximum version, when specified
- Python implementation, when specified

A missing file, checksum mismatch, or incompatibility prevents
installation or staging.

## Python Package Installation

`PythonPackageInstaller` supports local Python wheel files.

Installation behavior:

- Requires explicit approval through `approved=True`.
- Requires a compatible Python interpreter.
- Verifies repository integrity and compatibility before installation.
- Installs into a toolkit-managed destination.
- Uses `pip` with `--no-index` and `--no-deps`.
- Does not resolve or download dependencies.
- Does not modify system-managed Python packages.
- Does not overwrite an existing installation.
- Verifies installed package metadata after installation.

Only `.whl` files are currently supported.

## Executable Staging

`ExecutableStager` copies verified executable packages into a
toolkit-managed staging directory.

Staging behavior:

- Requires explicit approval through `approved=True`.
- Verifies repository integrity and compatibility.
- Rejects unsafe package identifiers and versions.
- Does not overwrite an existing destination.
- Does not execute the staged file.
- Does not install software into system locations.

Staging is not the same as installing or executing an executable.
A staged file remains under toolkit management until a future
workflow explicitly handles it.

## Installation Audit History

`InstallationRecordManager` stores operation history in JSON Lines
format.

The default recommended location is:

    reports/installations.jsonl

Each line contains one independent record with:

- Record ID
- Record timestamp
- Package ID and name
- Package version
- Dependency type
- Operation status
- Source path
- Destination path
- SHA-256 checksum
- Operation start and completion timestamps
- Result message
- Issues encountered

The manager supports:

- Appending records
- Loading all records
- Filtering by package ID
- Filtering by installation status
- Counting records

The history is persistent across application restarts.

The audit file is a local operational history, not a tamper-proof
security log. Protect it from unauthorized modification and deletion.
It may contain local filesystem paths.

Operations that produce an `InstallationResult` are recorded when
an `InstallationRecordManager` is supplied to the installer or stager.
An unknown package that cannot be resolved from the manifest raises
`RepositoryError` before an operation result is created.

## Example Usage

Create one record manager and share it between both installation paths:

    from pathlib import Path

    from it_toolkit.managers.installation_record_manager import (
        InstallationRecordManager,
    )
    from it_toolkit.managers.python_package_installer import (
        PythonPackageInstaller,
    )
    from it_toolkit.managers.executable_stager import (
        ExecutableStager,
    )

    repository = Path("dependencies/repository")
    history = InstallationRecordManager(
        Path("reports/installations.jsonl")
    )

    python_installer = PythonPackageInstaller(
        repository_path=repository,
        installation_root=Path("managed/python"),
        record_manager=history,
    )

    executable_stager = ExecutableStager(
        repository_path=repository,
        staging_root=Path("managed/executables"),
        record_manager=history,
    )

The caller must inspect the package, present the operation details,
obtain explicit user approval, and then call the relevant method with
`approved=True`.

The installer and stager do not provide a user interface or obtain
approval themselves.

## Security and Offline Behavior

The installation workflow does not:

- Contact external package repositories
- Download dependencies
- Automatically install packages at startup
- Install without explicit approval
- Install into system-managed Python locations
- Silently replace existing package versions
- Execute staged executable files
- Modify system configuration

A failed verification prevents the operation.

A failure to write an audit record raises `AuditLogError`. The
underlying package operation may already have completed, so callers
must handle audit persistence failures separately.

## Testing

Run the complete test suite:

    python -m unittest discover -s tests -v

Run repository tests:

    python -m unittest tests.managers.test_dependency_manager -v
    python -m unittest tests.models.test_package_manifest -v
    python -m unittest tests.utils.test_checksum -v

Run installation tests:

    python -m unittest tests.models.test_installation -v
    python -m unittest tests.managers.test_installation_record_manager -v
    python -m unittest tests.managers.test_python_package_installer -v
    python -m unittest tests.managers.test_executable_stager -v

## Future Work

Phase 6C will introduce portable runtime discovery, validation,
and management.

The diagnostic core will remain independent of optional runtimes
and graphical presentation components.
