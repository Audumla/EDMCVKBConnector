param(
    [string]$Workspace = (Get-Location).Path,
    [string]$StateHome = "$HOME\.agent-system",
    [switch]$Web
)

$ErrorActionPreference = "Stop"

$managerScript = Join-Path $PSScriptRoot "manage_runtime.py"
if (-not (Test-Path $managerScript)) {
    throw "Runtime manager script not found: $managerScript"
}

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $args = @($managerScript, "start", "--workspace", $Workspace, "--state-home", $StateHome)
    if ($Web) { $args += "--web" }
    & py -3 @args
    exit $LASTEXITCODE
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $args = @($managerScript, "start", "--workspace", $Workspace, "--state-home", $StateHome)
    if ($Web) { $args += "--web" }
    & python @args
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python 3 and retry."
