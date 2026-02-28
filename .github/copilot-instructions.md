# Agent System - Development Instructions

Universal AI Agent Orchestration and Automated Changelog Management System.

## Project Details

- **Language:** Python 3.9+
- **Purpose:** Delegate complex engineering tasks across multiple AI models with isolated verification.
- **Key Modules:**
  - **Core:** Orchestration, maintenance, and worktree synchronization.
  - **Runners:** Native CLI wrappers for Gemini, Claude, Codex, and Local LLMs.
  - **Dashboard:** Textual TUI for real-time monitoring and lifecycle management.
  - **Reporting:** Structured JSON changelog system with LLM summarization.

## Agent Workspace Policy

All execution artifacts must stay under `agent_artifacts/`.
Use the workspace-specific temp folders for planning:
- **Copilot:** `agent_artifacts/copilot/temp/plan.md`
- **Gemini/Claude:** `agent_artifacts/gemini/temp/plan.md`

## Agent Delegation Protocol

You support inline dispatch tags. When a user includes any of these in a prompt, follow the delegation workflow below.

### Tag Syntax

| Tag | Example | Effect |
| :--- | :--- | :--- |
| `#plan <provider>` | `#plan gemini` | Sets the planning agent |
| `#exec <provider>` | `#exec codex` | Sets the executor agent |
| `#budget <level>` | `#budget high` | Sets thinking budget (none/low/medium/high) |
| `#agent:<budget>:<planner>` | `#agent:deep:gemini` | Legacy form: sets planner + budget |

All tags are optional and case-insensitive. Omitted tags fall back to `delegation-config.json` defaults.

### When you see dispatch tags

1. Parse the tags to determine planner/executor/budget.
2. Research the task, then write a detailed execution plan at `agent_artifacts/copilot/temp/plan.md`.
3. Execute the delegation script in the background:
   `python agent_system/core/run_agent_plan.py --planner <planner> --executor <executor> --thinking-budget <budget> --plan-file agent_artifacts/copilot/temp/plan.md --cleanup-worktree --task-summary "Copilot: <user_task_description>"`
4. Provide a Delegation Receipt and exit immediately.

## Changelog Policy

Every change must be recorded via the logging script:

```bash
python agent_system/reporting/log_change.py --agent <agent> --group <Workstream> --tags <Tags> --summary <Text> --details <Bullets>
```
