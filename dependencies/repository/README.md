# Offline Package Repository

This directory contains locally staged packages approved for use by IT Toolkit.

## Structure

- `manifest.json` describes the packages available in this repository.
- Package files are stored in subdirectories referenced by their manifest entries.

## Package Integrity

Every package entry must include a SHA-256 checksum.

The toolkit verifies the checksum against the actual package file before
considering that package valid.

## Compatibility

Each package entry identifies its supported:

- Operating systems
- Processor architectures
- Python versions, when applicable
- Python implementation, when applicable

## Adding Packages

Do not manually add a package entry without first verifying:

1. The package's source and provenance.
2. The package version.
3. Its supported platforms and architectures.
4. Its SHA-256 checksum.
5. Its compatibility requirements.

The manifest is the repository's inventory, not a guarantee that a package
is trustworthy merely because it is listed.

## Offline Requirement

The repository is local-only.

The toolkit must never download missing packages or attempt an Internet
fallback when a package is unavailable.