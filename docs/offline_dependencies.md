# Offline Dependency Repository

## Purpose

The offline dependency repository provides a controlled location for
packages that may eventually be used by IT Toolkit.

Phase 6A implements repository inventory, manifest validation,
file verification, checksum validation, and compatibility evaluation.

It does not install or modify packages.

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

- package_id
- name
- version
- type
- file
- sha256
- operating_systems
- architectures

Optional Python compatibility fields:

- python_min_version
- python_max_version
- python_implementation

Supported dependency types are defined by the centralized
DependencyType enum.

## Integrity Validation

The dependency manager:

1. Loads the repository manifest.
2. Validates the manifest structure.
3. Rejects duplicate package/version entries.
4. Rejects unsafe relative paths.
5. Checks that package files exist.
6. Calculates SHA-256 checksums.
7. Compares calculated checksums against manifest values.
8. Optionally evaluates compatibility against SystemProfile.

A checksum mismatch makes the package invalid.

A missing package file makes the package invalid.

An incompatible package is reported as invalid for the supplied
system profile.

## Compatibility

Compatibility currently checks:

- Operating system
- Processor architecture
- Python minimum version, when specified
- Python maximum version, when specified
- Python implementation, when specified

Executable packages do not require Python compatibility checks.

## Security and Offline Behavior

The Phase 6A manager is read-only.

It does not:

- Download packages
- Contact external repositories
- Install packages
- Execute package files
- Modify system configuration
- Automatically repair missing files

Missing or invalid packages are reported to the caller.

## Testing

Run the complete test suite:

    python -m unittest discover -s tests -v

Run the dependency manager tests:

    python -m unittest tests.managers.test_dependency_manager -v

Run the manifest tests:

    python -m unittest tests.models.test_package_manifest -v

Run checksum tests:

    python -m unittest tests.utils.test_checksum -v

## Future Work

Phase 6B will introduce controlled installation from approved local
package sources.

Phase 6C will introduce portable runtime discovery and validation.