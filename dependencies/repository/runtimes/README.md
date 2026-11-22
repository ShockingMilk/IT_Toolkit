# Portable Runtime Repository

This directory contains locally supplied portable runtime distributions.

## Layout

    runtimes/
        manifest.json
        README.md
        packages/
            python/
            powershell/

The manifest is the authoritative inventory of runtime archives.

## Supported Runtime Types

- Python
- PowerShell

## Supported Archive Formats

- ZIP
- TAR
- TAR.GZ
- TAR.XZ
- TAR.BZ2

## Runtime Manifest Fields

Each runtime entry defines:

- `runtime_id`: Unique safe identifier.
- `runtime`: `python` or `powershell`.
- `version`: Runtime version.
- `archive`: Archive path relative to this directory.
- `archive_format`: Supported archive format.
- `sha256`: SHA-256 checksum of the complete archive.
- `operating_systems`: Supported operating systems.
- `architectures`: Supported processor architectures.
- `executable`: Executable path relative to the extracted runtime root.

Optional metadata:

- `python_implementation`
- `powershell_edition`
- `description`

## Important

Runtime archives must be supplied locally.

The toolkit does not download runtimes or resolve external dependencies.

Do not add an archive until its source and checksum have been independently
verified. The checksum in the manifest is an integrity reference, not a
digital signature or proof of publisher identity.
