param(
    [string]$Workspace = (Get-Location).Path,
    [string]$StateHome = "$HOME\.agent-system",
    [switch]$Force,
    [switch]$Web
)

$ErrorActionPreference = "Stop"

$runtimeRoot = (Get-Item "$PSScriptRoot\..\.." ).FullName
$installScript = Join-Path $runtimeRoot "install.py"
if (-not (Test-Path $installScript)) {
    throw "install.py not found at: $installScript"
}

$cmdArgs = @($installScript, "install", "--workspace", $Workspace, "--state-home", $StateHome)
if ($Force) { $cmdArgs += "--force" }

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCmd) {
    & py -3 @cmdArgs
    exit $LASTEXITCODE
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    & python @cmdArgs
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python 3 and retry."
