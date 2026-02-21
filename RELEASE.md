# Release Workflow Guide

This document explains how to prepare and trigger releases using the automated release workflow integrated with VSCode.

## Overview

The release workflow is built on:
- **release-please**: Automated GitHub Actions workflow for version bumping and release creation
- **changelog_activity.py**: Script to prepare changelog and generate release notes
- **VSCode tasks**: Convenient commands to trigger the workflow from the editor

## Prerequisites

- Python 3.11+ with dependencies installed
- GitHub CLI (`gh`) installed and authenticated: `gh auth login`
- Git configured with your name and email

Verify GitHub CLI is working:
```bash
gh auth status
```

## Quick Start

### Option 1: Full Workflow in One Command (Recommended)

From VSCode:
1. Press `Ctrl+Shift+B` (or `Cmd+Shift+B` on macOS) to open **Build Tasks**
2. Select **"Release: Full workflow (prep + trigger)"**

Or from the command line:
```bash
bash scripts/release.sh
```

### Option 2: Step-by-Step

**Step 1: Prepare the changelog**
- VSCode: `Ctrl+Shift+B` → **"Release: Prepare changelog"**
- Or: `python scripts/changelog_activity.py --strict`

This will:
- Rebuild `CHANGELOG.md` from JSON sources
- Generate `dist/RELEASE_NOTES.preview.md` with unreleased changes

**Step 2: Review the preview**
- Check `dist/RELEASE_NOTES.preview.md` to verify the release notes look good

**Step 3: Trigger release-please**
- VSCode: `Ctrl+Shift+B` → **"Release: Trigger release-please workflow"**
- Or: `gh workflow run release-please.yml`

This will:
- Create a Release PR on GitHub with version bumps
- Auto-update version numbers in `pyproject.toml`, `src/edmcruleengine/version.py`

**Step 4: Review and merge the PR**
- Go to GitHub and review the Release PR
- Once approved, merge to trigger the release

## Customizing Keybindings (Optional)

To add keyboard shortcuts for release tasks:

1. Open VSCode Settings: `Ctrl+Shift+P` → **"Preferences: Open Keyboard Shortcuts (JSON)"**
2. Add these bindings:

```json
[
  {
    "key": "ctrl+shift+alt+c",
    "command": "workbench.action.tasks.runTask",
    "args": "Release: Prepare changelog"
  },
  {
    "key": "ctrl+shift+alt+r",
    "command": "workbench.action.tasks.runTask",
    "args": "Release: Full workflow (prep + trigger)"
  }
]
```

## Understanding the Release Process

### What `/codex` Delegation Changes Mean for Releases

When you use the `/codex` label to delegate tasks to Codex:
1. Codex changes are recorded in `docs/changelog/CHANGELOG.json` via `log_change.py`
2. Each change gets a unique `CHG-<commit-hash>` ID (e.g., `CHG-55c6ba67`)
   - IDs are based on git commit hashes (short form)
   - Merge-safe across branches (no conflicts on different branches)
3. When you run the release workflow, these entries are:
   - Stamped with the new version
   - Included in release notes
   - Archived for history

### Release Notes Generation

Release notes are generated from:
- Unreleased entries in `docs/changelog/CHANGELOG.json`
- Formatted with details, tags, and agent attribution
- Written to `dist/RELEASE_NOTES.md` in the release commit

### Versioning

This project uses:
- **Semantic Versioning**: `MAJOR.MINOR.PATCH`
- **Pre-releases**: `-alpha`, `-beta`, `-rc` suffixes (optional)
- **Version bumping**: Automatic via release-please based on commit types

Commit type hints come from:
- `--tags` values in `log_change.py` (mapped to conventional commits)
- "Bug Fix" → `fix:` (PATCH bump)
- "New Feature" → `feat:` (MINOR bump)
- "Code Refactoring" → `refactor:` (no bump, but noted)

## Troubleshooting

### `gh workflow run` fails with "authentication failed"

**Solution**: Authenticate with GitHub CLI:
```bash
gh auth login
# Follow prompts to select GitHub.com, HTTPS, and authenticate
```

### `gh workflow run` fails with "workflow not found"

**Solution**: Ensure the workflow file exists:
```bash
# Check for the workflow file
ls -la .github/workflows/release-please.yml

# List available workflows
gh workflow list
```

### Release notes look wrong

**Solution**: Check the `docs/changelog/CHANGELOG.json` entries:
- Ensure entries have proper `tags` values
- Verify the `summary` is descriptive
- Run `python scripts/changelog_activity.py --strict` again

### Version numbers didn't update after release

**Solution**: release-please may have created a PR but not merged it. Check:
1. Go to your GitHub repo → Pull Requests
2. Look for the "chore(main): release ..." PR
3. Merge it manually if needed
4. The next workflow run will create the actual release

## API Reference

### changelog_activity.py

Prepares the changelog for release.

```bash
python scripts/changelog_activity.py [--strict]
```

**Options:**
- `--strict`: Exit with error if there are no unreleased changes (recommended for CI)

**Output:**
- `CHANGELOG.md`: Updated changelog with latest entries
- `dist/RELEASE_NOTES.preview.md`: Compact preview of unreleased notes

### log_change.py

Record a change to the changelog (used by agents).

```bash
python scripts/log_change.py \
    --agent claude \
    --tags "New Feature" \
    --summary "Brief description" \
    --details "Bullet one" "Bullet two"
```

**Required args:**
- `--agent`: Name of the agent making the change
- `--summary`: One-line description
- `--tags`: One or more tags (space-separated)

**Optional args:**
- `--group`: Workstream grouping (stable across related work)
- `--details`: Bullet points (repeatable, one per arg)

**Approved tag values:**
- `Bug Fix` · `New Feature` · `Code Refactoring` · `Configuration Cleanup`
- `Documentation Update` · `Test Update` · `Dependency Update`
- `Performance Improvement` · `UI Improvement` · `Build / Packaging`

## See Also

- [CLAUDE.md](CLAUDE.md) — Agent workspace policies and `/codex` delegation
- [CHANGELOG.json](docs/changelog/CHANGELOG.json) — Complete change history
- [release-please-config.json](release-please-config.json) — Release workflow configuration
