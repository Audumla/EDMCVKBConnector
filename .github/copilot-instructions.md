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

You support the `#agent:<budget>:<planner>` directive. If a user includes this in a request:
1. Research the task.
2. Generate a detailed execution plan at `agent_artifacts/copilot/temp/plan.md`.
3. Execute the delegation script in the background: 
   `python agent_system/core/run_agent_plan.py --planner <planner> --executor <executor> --thinking-budget <budget> --plan-file agent_artifacts/copilot/temp/plan.md --cleanup-worktree --task-summary "Copilot: <user_task_description>"`
4. Provide a Delegation Receipt and exit immediately.

## Changelog Policy

Every change must be recorded via the logging script:
```bash
python agent_system/reporting/log_change.py --agent <agent> --group <Workstream> --tags <Tags> --summary <Text> --details <Bullets>
```
