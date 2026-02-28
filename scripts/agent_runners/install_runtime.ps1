param(
    [switch]$ForceReinstall,
    [switch]$WithWeb
)

$ErrorActionPreference = "Stop"

$runtimeRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$managerScript = Join-Path $PSScriptRoot "manage_runtime.py"

if (-not (Test-Path $managerScript)) {
    throw "Runtime manager script not found: $managerScript"
}

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $args = @("-3", $managerScript, "install")
    if ($ForceReinstall) { $args += "--force-reinstall" }
    if ($WithWeb) { $args += "--with-web" }
    & py @args
    exit $LASTEXITCODE
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $args = @($managerScript, "install")
    if ($ForceReinstall) { $args += "--force-reinstall" }
    if ($WithWeb) { $args += "--with-web" }
    & python @args
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python 3 and retry."
