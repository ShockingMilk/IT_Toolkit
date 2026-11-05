$ErrorActionPreference = "Stop"

$ToolkitRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $ToolkitRoot "src"
$env:IT_TOOLKIT_LAUNCHER_SHELL = "powershell"

Write-Host ""
Write-Host "=========================================="
Write-Host "              IT TOOLKIT"
Write-Host "=========================================="
Write-Host ""

$PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue

if (-not $PythonCommand) {
    Write-Host "Python was not detected."
    Write-Host "Python 3.10 or newer is required."

    exit 1
}

$PythonVersion = & $PythonCommand.Source -c `
    "import sys; print('.'.join(map(str, sys.version_info[:3])))"
$ParsedVersion = [Version]$PythonVersion

if ($ParsedVersion -lt [Version]"3.10") {
    Write-Host "Unsupported Python version: $PythonVersion"
    exit 1
}

Write-Host "Python detected: $PythonVersion"
Write-Host ""

& $PythonCommand.Source -m it_toolkit.main

exit $LASTEXITCODE