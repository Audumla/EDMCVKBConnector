# Agent Workspace Policy

All Codex execution artifacts must stay under `agent_artifacts/codex/`.

- Reports: `agent_artifacts/codex/reports/`
- Temporary scripts and scratch files: `agent_artifacts/codex/temp/`

Do not write Codex-generated reports or temp files anywhere else in this repository.

## Verbose Agent Protocol

Whenever the user includes a label in the format `#agent:<budget>:<planner>` or `/agent:<budget>:<planner>` in their prompt, the active agent MUST follow this strict delegation workflow.

### Protocol Labels
| Label | Planner | Budget | Executor |
| :--- | :--- | :--- | :--- |
| `#agent:deep:gemini` | Gemini | High | Codex |
| `#agent:deep:claude` | Claude | High | Codex |
| `#agent:fast:gemini` | Gemini | Low | Codex |
| `#agent:fast:claude` | Claude | Low | Codex |

### Required Action Sequence
1. **Plan:** Analyze the request and write a detailed Markdown plan to your workspace-specific temp folder:
   - **Copilot:** `agent_artifacts/copilot/temp/plan.md`
   - **Gemini/Claude:** `agent_artifacts/gemini/temp/plan.md`
2. **Execute (Background):** Launch the delegation script in the **background** to minimize session overhead.
   `python scripts/agent_runners/run_agent_plan.py --planner <planner> --thinking-budget <budget> --plan-file <path_to_plan.md> --cleanup-worktree --task-summary "<task>"`

### Maintenance
To purge old temporary files and stale worktrees:
`python scripts/agent_runners/cleanup_artifacts.py`
3. **Finish:** Immediately report the Run ID and the background command to the user. Do not wait for completion.

### Mandatory Output Format
The agent MUST output a handoff receipt similar to:
> **DELEGATION ACTIVE**
> - **Planner:** <Agent Name>
> - **Executor:** Codex (Isolated Worktree)
> - **Budget:** <High/Low>
> - **Monitor:** `python scripts/agent_runners/watch_run.py`

### Monitoring
Users can monitor background progress without agent overhead using:
`python scripts/agent_runners/watch_run.py`


The project uses a structured Agent Runner system for delegating complex engineering tasks.

- **Tutorial:** [docs/AGENT_RUNNER_TUTORIAL.md](docs/AGENT_RUNNER_TUTORIAL.md)
- **Configuration:** `scripts/agent_runners/delegation-config.json`
- **Output:** `agent_artifacts/codex/reports/plan_runs/`

## Changelog Policy

### At the START of every session

Read `docs/changelog/CHANGELOG.json` to understand what every agent has already done. Use it to avoid duplicating work and to understand the current state of the codebase.

### After completing ANY task that modifies files

Before declaring the task done, you MUST record what was changed. Do not skip this step. Do not wait for the user to ask. Updating the changelog is the final step of every task.

Run this script — it handles all file updates automatically:

```bash
python scripts/changelog/log_change.py \
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
python scripts/changelog/changelog_activity.py --strict
```

This rebuilds `CHANGELOG.md` and writes compact unreleased release-note preview to `dist/RELEASE_NOTES.preview.md`.

### Approved `--tags` values

Use one or more of these exact strings:

`Bug Fix` · `New Feature` · `Code Refactoring` · `Configuration Cleanup` ·
`Documentation Update` · `Test Update` · `Dependency Update` ·
`Performance Improvement` · `UI Improvement` · `Build / Packaging`
