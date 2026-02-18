# Agent Workspace Policy

All Claude execution artifacts must stay under `agent_artifacts/claude/`.

- Reports: `agent_artifacts/claude/reports/`
- Temporary scripts and scratch files: `agent_artifacts/claude/temp/`

Do not write Claude-generated reports or temp files anywhere else in this repository.

## Changelog Policy

### At the START of every session

Read `CHANGELOG.json` (repo root) to understand what every agent has already done. Use it to avoid duplicating work and to understand the current state of the codebase.

### After completing ANY task that modifies files

Before declaring the task done, you MUST record what was changed. Do not skip this step. Do not wait for the user to ask. Updating the changelog is the final step of every task.

Run this script — it handles all file updates automatically:

```bash
python scripts/log_change.py \
    --agent claude \
    --tags "<Tag1>" "<Tag2>" \
    --summary "One-sentence description" \
    --details "Bullet one" "Bullet two" "Bullet three"
```

The script auto-increments the CHG-NNN id, appends to `CHANGELOG.json`, and prepends the row and detail section to `CHANGELOG.md`. Do not edit those files manually.

### Approved `--tags` values

Use one or more of these exact strings:

`Bug Fix` · `New Feature` · `Code Refactoring` · `Configuration Cleanup` ·
`Documentation Update` · `Test Update` · `Dependency Update` ·
`Performance Improvement` · `UI Improvement` · `Build / Packaging`
