# Claude Project Guide - Agent System

This project is a universal AI agent orchestration and automated changelog management system.

## Project Structure
- `agent_system/core`: Orchestration logic and maintenance.
- `agent_system/runners`: Native CLI wrappers for different AI models.
- `agent_system/dashboard`: Textual-based monitoring interface.
- `agent_system/reporting`: Changelog and release note automation.

## Agent Delegation Protocol
This project uses a specific delegation protocol via `#agent:<budget>:<planner>` tags. When you see one:
1. Research the task.
2. Write a Markdown plan to `agent_artifacts/claude/temp/plan.md`.
3. Execute: `python agent_system/core/run_agent_plan.py --planner claude --thinking-budget <budget> --plan-file agent_artifacts/claude/temp/plan.md --cleanup-worktree --task-summary "Claude: <task>"`
4. Provide a Delegation Receipt and exit.

## Changelog Policy
Every change must be recorded:
`python agent_system/reporting/log_change.py --agent claude --group <Workstream> --tags <Tags> --summary <Text> --details <Bullets>`
