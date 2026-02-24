# Gemini Project Guide - Agent System

This project is a universal AI agent orchestration and automated changelog management system.

## Project Structure
- `agent_system/core`: Orchestration logic and maintenance.
- `agent_system/runners`: Native CLI wrappers for different AI models.
- `agent_system/dashboard`: Textual-based monitoring interface.
- `agent_system/reporting`: Changelog and release note automation.

## Post-Action Validation Mandate
EVERY task performed MUST conclude with:
1. **Integrity Check**: `python -m py_compile` on changed files.
2. **Functional Verification**: Demonstrate the new capability.
3. **Zero-Regression**: Run relevant tests in `agent_system/core/`.

## Agent Delegation Protocol
When you see an `#agent` tag:
1. Write a plan to `agent_artifacts/gemini/temp/plan.md`.
2. Execute: `python agent_system/core/run_agent_plan.py --planner gemini --thinking-budget <budget> --plan-file agent_artifacts/gemini/temp/plan.md --cleanup-worktree --task-summary "Gemini: <task>"`
3. Provide a Delegation Receipt and exit.
