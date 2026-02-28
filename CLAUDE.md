# Claude Project Guide - Agent System

This project is a universal AI agent orchestration and automated changelog management system.

## Project Structure
- `agent_system/core`: Orchestration logic and maintenance.
- `agent_system/runners`: Native CLI wrappers for different AI models.
- `agent_system/dashboard`: Textual-based monitoring interface.
- `agent_system/reporting`: Changelog and release note automation.

## Agent Delegation Protocol
This project uses inline dispatch tags to route planning and execution to any configured provider.

### Tag Syntax

| Tag | Example | Effect |
| --- | ------- | ------ |
| `#plan <provider>` | `#plan gemini` | Sets the planning agent |
| `#exec <provider>` | `#exec codex` | Sets the executor agent |
| `#budget <level>` | `#budget high` | Sets thinking budget (none/low/medium/high) |
| `#agent:<budget>:<planner>` | `#agent:deep:gemini` | Legacy: sets planner + budget (backward compat) |

All tags are optional and case-insensitive. Tags are stripped from the prompt before it becomes the plan goal.
Valid providers: `claude`, `gemini`, `codex`, `opencode`, `copilot`, `cline`, `ollama`, `lmstudio` (subject to `delegation-config.json` enabled flags).

### When you see dispatch tags

1. Parse the tags to determine planner/executor/budget.
2. Research the task, then write a Markdown plan to `agent_artifacts/claude/temp/plan.md`.
3. Execute (background): `python agent_system/core/run_agent_plan.py --planner <planner> --executor <executor> --thinking-budget <budget> --plan-file agent_artifacts/claude/temp/plan.md --cleanup-worktree --task-summary "Claude: <task>"`
4. Provide a Delegation Receipt and exit.

### Example prompts

```text
#plan gemini #exec codex fix the broken unit tests
#plan claude #exec opencode #budget high refactor the VKB manager
#agent:deep:gemini add telemetry to the event handler
```

## Changelog Policy
Every change must be recorded:
`python agent_system/reporting/log_change.py --agent claude --group <Workstream> --tags <Tags> --summary <Text> --details <Bullets>`
