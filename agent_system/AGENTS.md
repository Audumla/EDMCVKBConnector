# Agent Workspace Policy

All agent execution artifacts must stay under the `agent_artifacts/` directory.

- Reports: `agent_artifacts/<agent>/reports/`
- Temporary scripts and scratch files: `agent_artifacts/<agent>/temp/`

Do not write agent-generated reports or temp files anywhere else in this repository.

## Agent Delegation Protocol

Whenever the user includes dispatch tags in their prompt, the active agent MUST follow this delegation workflow.

### Tag Syntax

| Tag | Example | Effect |
| :--- | :--- | :--- |
| `#plan <provider>` | `#plan gemini` | Sets the planning agent |
| `#exec <provider>` | `#exec codex` | Sets the executor agent |
| `#budget <level>` | `#budget high` | Sets thinking budget (none/low/medium/high) |
| `#agent:<budget>:<planner>` | `#agent:deep:gemini` | Legacy: sets planner + budget (backward compat) |
| `/agent:<budget>:<planner>` | `/agent:fast:claude` | Legacy forward-slash form (backward compat) |

All tags are case-insensitive. Any combination is valid — omitted tags fall back to `delegation-config.json` defaults.

### Quick Reference (Legacy Labels)

| Label | Planner | Budget | Executor |
| :--- | :--- | :--- | :--- |
| `#agent:deep:gemini` | Gemini | High | Chosen via config |
| `#agent:deep:claude` | Claude | High | Chosen via config |
| `#agent:fast:gemini` | Gemini | Low | Chosen via config |
| `#agent:fast:claude` | Claude | Low | Chosen via config |

### Required Action Sequence

1. **Plan:** Analyze the request. Write a detailed Markdown plan to your agent-specific temp folder:
   - **Copilot:** `agent_artifacts/copilot/temp/plan.md`
   - **Gemini/Claude:** `agent_artifacts/gemini/temp/plan.md`
2. **Execute (Background):** Launch the orchestration script in the **background**:
   `python agent_system/core/run_agent_plan.py --planner <planner> --executor <executor> --thinking-budget <budget> --plan-file <path_to_plan.md> --cleanup-worktree --task-summary "<task>"`
3. **Maintenance:** To purge old temporary files and stale worktrees:
   `python agent_system/core/agent_maintenance.py`
4. **Finish:** Immediately report the Run ID and the background command to the user. Do not wait for completion.

### Mandatory Output Format

The agent MUST output a handoff receipt similar to:

> **DELEGATION ACTIVE**
>
> - **Planner:** Planner Name
> - **Executor:** Native CLI (Isolated Worktree)
> - **Budget:** High/Low
> - **Monitor:** `python agent_system/dashboard/agent_dashboard.py`

### Monitoring

Users can monitor progress via the Interactive Dashboard:
`python agent_system/dashboard/agent_dashboard.py`

## Changelog Policy

### At the START of every session

Read `agent_system/docs/reporting/CHANGELOG.json` to understand what has already been accomplished and avoid duplicating work.

### After completing ANY task that modifies files

Update the changelog immediately using the logging script:

```bash
python agent_system/reporting/log_change.py \
    --agent <agent> \
    --group "<WorkstreamSlug>" \
    --tags "<Tag1>" "<Tag2>" \
    --summary "One-sentence description" \
    --details "Bullet point summary"
```

The script generates a globally unique ID and rebuilds the `CHANGELOG.md` automatically.

### Release Preparation

Before pushing for release, run:

```bash
python agent_system/reporting/changelog_activity.py --strict
```

This rebuilds the master log and generates release-note previews.
