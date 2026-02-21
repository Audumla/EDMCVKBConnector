# release.ps1 - One-command release workflow for Windows
# This script prepares the changelog and triggers the release-please workflow

$ErrorActionPreference = "Stop"

$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $PROJECT_ROOT

Write-Host "[Release Workflow] Starting release workflow..." -ForegroundColor Yellow
Write-Host ""

# Step 1: Prepare changelog
Write-Host "[Step 1/2] Preparing changelog..." -ForegroundColor Yellow
try {
    python scripts/changelog_activity.py --strict
    Write-Host "✓ Changelog prepared" -ForegroundColor Green
}
catch {
    Write-Host "✗ Changelog preparation failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Trigger release-please workflow
Write-Host "[Step 2/2] Triggering release-please workflow..." -ForegroundColor Yellow
try {
    gh workflow run release-please.yml
    Write-Host "✓ Release workflow triggered" -ForegroundColor Green
}
catch {
    Write-Host "✗ Failed to trigger workflow (ensure 'gh' CLI is installed and authenticated)" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "[Release Workflow] Complete! Check GitHub for the release PR." -ForegroundColor Green
Write-Host ""
Write-Host "Release notes preview: dist/RELEASE_NOTES.preview.md"
Write-Host "Next: Review the release PR on GitHub, merge to finalize release."
