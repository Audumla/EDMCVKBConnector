# Agent Workspace Policy

All agent execution artifacts must stay under the `agent_artifacts/` directory.

- Reports: `agent_artifacts/<agent>/reports/`
- Temporary scripts and scratch files: `agent_artifacts/<agent>/temp/`

Do not write agent-generated reports or temp files anywhere else in this repository.

## Verbose Agent Protocol

Whenever the user includes a label in the format `#agent:<budget>:<planner>` or `/agent:<budget>:<planner>` in their prompt, the active agent MUST follow this strict delegation workflow.

### Protocol Labels
| Label | Planner | Budget | Executor |
| :--- | :--- | :--- | :--- |
| `#agent:deep:gemini` | Gemini | High | Chosen via config |
| `#agent:deep:claude` | Claude | High | Chosen via config |
| `#agent:fast:gemini` | Gemini | Low | Chosen via config |
| `#agent:fast:claude` | Claude | Low | Chosen via config |

### Required Action Sequence
1. **Plan:** Analyze the request and write a detailed Markdown plan to your agent-specific temp folder:
   - **Copilot:** `agent_artifacts/copilot/temp/plan.md`
   - **Gemini/Claude:** `agent_artifacts/gemini/temp/plan.md`
2. **Execute (Background):** Launch the orchestration script in the **background**:
   `python agent_system/core/run_agent_plan.py --planner <planner> --thinking-budget <budget> --plan-file <path_to_plan.md> --cleanup-worktree --task-summary "<task>"`
3. **Maintenance:** To purge old temporary files and stale worktrees:
   `python agent_system/core/agent_maintenance.py`
4. **Finish:** Immediately report the Run ID and the background command to the user. Do not wait for completion.

### Mandatory Output Format
The agent MUST output a handoff receipt similar to:
> **DELEGATION ACTIVE**
> - **Planner:** <Agent Name>
> - **Executor:** <Native CLI> (Isolated Worktree)
> - **Budget:** <High/Low>
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
