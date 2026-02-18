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

Update two files:

### 1. `CHANGELOG.json` (repo root)

Append a new JSON object to the array:

```json
{
  "id": "CHG-NNN",
  "plugin_version": "<read from src/edmcruleengine/version.py>",
  "date": "<YYYY-MM-DD>",
  "agent": "claude",
  "summary_tags": ["<tag1>", "<tag2>"],
  "summary": "<one sentence>",
  "details": [
    "<bullet 1>",
    "<bullet 2>"
  ]
}
```

Increment `NNN` from the last entry in the file (e.g. if last is CHG-003, use CHG-004).

### 2. `CHANGELOG.md`

- Insert a new row at the **top** of the summary table (below the header).
- Insert a new `### CHG-NNN` detail section **above** the first existing detail section.

### Approved Summary Tags

Use one or more of these exact strings:

`Bug Fix` · `New Feature` · `Code Refactoring` · `Configuration Cleanup` ·
`Documentation Update` · `Test Update` · `Dependency Update` ·
`Performance Improvement` · `UI Improvement` · `Build / Packaging`
