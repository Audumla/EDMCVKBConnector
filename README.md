# Agent System

A universal AI agent orchestration and automated changelog management system.

## Features

- **Agent Runner**: Orchestrate planning and execution between different AI models (Gemini, Claude, Codex, Local LLMs).
- **Interactive Dashboard**: Professional TUI for monitoring logs, managing runs, and merging results.
- **Automated Changelog**: Structured JSON-based changelog system with LLM-powered summarization.
- **Isolated Execution**: Every agent run executes in a temporary Git worktree for safety and non-blocking development.
- **Cross-Agent Protocol**: Unified instruction set for Copilot, Claude, Gemini, and local agents.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Open the Dashboard:
   ```bash
   python agent_system/dashboard/agent_dashboard.py
   ```

## Project Structure

- `agent_system/core`: Central orchestration and maintenance logic.
- `agent_system/runners`: Native CLI wrappers for different AI models.
- `agent_system/dashboard`: Textual-based monitoring interface.
- `agent_system/reporting`: Changelog and release note automation.
- `agent_system/config`: Agent and delegation configurations.

## Maintenance

Identify and purge orphaned branches and temporary files:
```bash
python agent_system/core/agent_maintenance.py
```
