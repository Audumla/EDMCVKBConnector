# release.ps1 - Wrapper around scripts/release_workflow.py for Windows

$ErrorActionPreference = "Stop"

$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $PROJECT_ROOT

$python = Join-Path $PROJECT_ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python scripts/release/release_workflow.py @args
exit $LASTEXITCODE
