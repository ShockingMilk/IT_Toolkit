# Portable Runtime Management

## Purpose

Portable Runtime Management allows IT Toolkit to use locally stored,
verified Python and PowerShell runtimes without modifying the host
operating system's installed runtimes.

The system is designed for offline and air-gapped environments.

Portable runtimes are optional. The toolkit continues to use its
normal host environment unless a portable runtime is explicitly
selected.

## Design Principles

- No Internet downloads.
- No automatic runtime installation.
- No modification of system Python or PowerShell.
- No global PATH modification.
- No automatic runtime selection.
- Verify runtime archives before staging.
- Verify staged executables before execution.
- Require explicit approval for staging and selection.
- Keep runtime operations auditable.
- Use standard-library functionality wherever practical.

## Repository Layout

The runtime repository is maintained separately from staged runtimes.

Example:

    dependencies/
        repository/
            runtimes/
                manifest.json
                README.md
                python/
                powershell/

    dependencies/
        staged/
            runtimes/
                <runtime_id>/
                    <version>/

The repository contains original runtime archives and their manifest.

The staging directory contains extracted, toolkit-managed runtimes.

Do not manually modify staged runtime contents.

## Runtime Manifest

The runtime manifest describes available portable runtime packages.

Each entry identifies:

- Runtime ID
- Runtime type
- Version
- Archive filename
- Archive format
- SHA-256 checksum
- Supported operating systems
- Supported architectures
- Relative executable path
- Optional Python implementation
- Optional PowerShell edition
- Description

Supported archive formats:

- ZIP
- TAR
- TAR.GZ
- TAR.XZ
- TAR.BZ2

Paths in the manifest are relative to the runtime repository.

Unsafe paths and duplicate runtime/version entries are rejected.

## Runtime Inventory

RuntimeCatalogManager provides access to the runtime catalog.

It can:

- Load the runtime manifest.
- List available runtimes.
- Retrieve a specific runtime/version.
- Resolve archive paths safely.

The catalog does not install or execute runtimes.

## Runtime Verification

RuntimeVerifier checks each runtime archive before staging.

Verification includes:

1. Archive existence.
2. SHA-256 integrity.
3. Operating system compatibility.
4. Architecture compatibility.
5. Actual archive format.

Verification does not extract or execute the runtime.

A runtime must pass verification before staging.

### Integrity limitations

The manifest checksum confirms that an archive matches the checksum
recorded in the local manifest.

It does not independently prove publisher identity or authenticity.

The repository and manifest must therefore be obtained from and
maintained by a trusted source.

## Runtime Staging

RuntimeStager extracts verified runtime archives into the managed
staging directory.

Staging is separate from selection and execution.

The staging process must reject unsafe archive contents, including
path traversal and unsupported special files.

Existing staged runtime versions must not be silently overwritten.

Staged runtime metadata records the runtime identity, version,
archive checksum, executable location, and executable checksum.

The executable checksum is used for integrity verification before
execution.

## Runtime Selection

RuntimeSelectionManager manages explicit selection of a staged runtime.

Selection must verify that the requested runtime:

- Exists in the staging directory.
- Has valid staged metadata.
- Matches the requested runtime identity and version.
- Contains the expected executable.
- Has not been modified since staging.

Selection does not execute the runtime.

Selection does not modify system PATH or replace the host runtime.

## Runtime Execution

RuntimeExecutionManager executes the explicitly selected runtime.

Before execution, it validates:

- Selection metadata.
- Runtime identity and version.
- Staging directory location.
- Executable location.
- Executable integrity checksum.

Execution uses an argument list with shell execution disabled.

The manager supports:

- Explicit arguments.
- Execution timeouts.
- Captured standard output.
- Captured standard error.
- Return-code reporting.
- Execution result reporting.
- Runtime operation audit records.

The manager does not provide a general-purpose shell.

### Version probes

The manager supports explicit version probes for:

- Python
- PowerShell

A version probe executes the selected runtime and compares the
reported version with the staged runtime version.

Version probes are explicit operations, not startup actions.

## Runtime Audit History

Runtime operations are recorded separately from package installation
history.

The audit history supports reviewing runtime staging, selection,
and execution operations.

Audit records are local operational history. They are not tamper-proof
security logs.

Protect the audit directory from unauthorized modification.

## Host Runtime Independence

The host Python and installed PowerShell runtimes remain independently
detected by the normal system detection process.

Portable runtime management does not replace host detection.

This distinction ensures that system reports continue to describe
the actual host environment.

A diagnostic module must explicitly use the portable runtime execution
service if it needs to invoke a selected portable runtime.

## Offline Operation

Portable runtime management must not:

- Download runtime distributions.
- Contact external repositories.
- Automatically update runtimes.
- Install runtimes during toolkit startup.
- Change system runtime installations.
- Modify global PATH.
- Silently select a runtime.
- Execute a runtime simply because it was staged.

All runtime archives must be supplied through the local repository.

## Troubleshooting

### Runtime does not appear in the catalog

Check:

- The runtime manifest exists.
- The manifest is valid JSON.
- The runtime entry is present.
- Runtime ID and version are correct.

### Runtime fails verification

Check:

- The archive exists at the manifest path.
- The SHA-256 checksum matches.
- The archive format matches the manifest.
- The operating system and architecture are supported.

Do not bypass checksum failures.

### Runtime fails staging

Check:

- The runtime passed verification.
- The staging destination is writable.
- The destination does not already contain the same runtime/version.
- The archive contains the expected executable path.

### Runtime cannot be selected

Check:

- Staging completed successfully.
- Staged metadata exists.
- Runtime identity and version match.
- The executable exists and is a regular file.

### Runtime fails execution

Check:

- The runtime is explicitly selected.
- The executable checksum still matches.
- The executable has appropriate operating-system permissions.
- The runtime distribution supports the host platform.
- The execution timeout is sufficient.

If a staged runtime has been modified, restage it from a verified
repository archive.

## Testing

Run the complete test suite:

    python -m unittest discover -s tests -v

Run runtime-specific tests:

    python -m unittest tests.models.test_runtime_manifest -v
    python -m unittest tests.managers.test_runtime_catalog_manager -v
    python -m unittest tests.managers.test_runtime_verifier -v
    python -m unittest tests.managers.test_runtime_stager -v
    python -m unittest tests.managers.test_runtime_selection_manager -v
    python -m unittest tests.managers.test_runtime_record_manager -v
    python -m unittest tests.managers.test_runtime_execution_manager -v

Test actual portable runtime distributions separately from the
automated test suite.

## Future Considerations

Potential future improvements include:

- Multiple independently selected runtime profiles.
- Runtime health reporting.
- Runtime inventory in diagnostic reports.
- Runtime version policy and compatibility recommendations.
- Optional runtime discovery through the interactive menu.
- Integration with a future bootable recovery environment.

These improvements must preserve the separation between host
detection, portable runtime management, and diagnostic execution.
