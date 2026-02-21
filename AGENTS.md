# Agent Workspace Policy

All Codex execution artifacts must stay under `agent_artifacts/codex/`.

- Reports: `agent_artifacts/codex/reports/`
- Temporary scripts and scratch files: `agent_artifacts/codex/temp/`

Do not write Codex-generated reports or temp files anywhere else in this repository.

## Changelog Policy

### At the START of every session

Read `docs/changelog/CHANGELOG.json` to understand what every agent has already done. Use it to avoid duplicating work and to understand the current state of the codebase.

### After completing ANY task that modifies files

Before declaring the task done, you MUST record what was changed. Do not skip this step. Do not wait for the user to ask. Updating the changelog is the final step of every task.

Run this script — it handles all file updates automatically:

```bash
python scripts/log_change.py \
    --agent codex \
    --group "<WorkstreamSlug>" \
    --tags "<Tag1>" "<Tag2>" \
    --summary "One-sentence description" \
    --details "Bullet one" "Bullet two" "Bullet three"
```

`--group` is recommended and should stay stable for related iterative work that will ship together.

The script generates a globally unique `CHG-*` id (branch-safe for merges), appends to `docs/changelog/CHANGELOG.json`, and rebuilds `CHANGELOG.md` from JSON sources. Do not edit those files manually.

### Release prep activity

Before pushing for release creation, run:

```bash
python scripts/changelog_activity.py --strict
```

This rebuilds `CHANGELOG.md` and writes compact unreleased release-note preview to `dist/RELEASE_NOTES.preview.md`.

### Approved `--tags` values

Use one or more of these exact strings:

`Bug Fix` · `New Feature` · `Code Refactoring` · `Configuration Cleanup` ·
`Documentation Update` · `Test Update` · `Dependency Update` ·
`Performance Improvement` · `UI Improvement` · `Build / Packaging`
