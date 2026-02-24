# Development Guide - Agent System

This document is for contributors and maintainers of the **Agent System** project.

## Repository Layout

The project is organized into a modular structure under `agent_system/`:

- `agent_system/core/`: Central orchestration, maintenance, and shared utilities.
- `agent_system/runners/`: Native CLI wrappers for various AI models (Gemini, Codex, OpenCode, etc.).
- `agent_system/dashboard/`: Textual-based TUI for real-time monitoring and task dispatching.
- `agent_system/reporting/`: Automated changelog and release note management scripts.
- `agent_system/config/`: Configuration files for agents and delegation.
- `agent_system/docs/`: Technical documentation and reporting data sources.

## Core Modules

### Agent Runner (`core/run_agent_plan.py`)
The primary entry point for delegating tasks. It orchestrates between a **Planner** (which researches and writes a plan) and an **Executor** (which performs the work in an isolated Git worktree).

### Command Center (`dashboard/agent_dashboard.py`)
A modern Textual TUI that provides:
- Live log streaming from active runs.
- Real-time cost and token statistics.
- Direct task dispatching via a prompt panel.
- Lifecycle management (Merge, Kill, Delete).

### Maintenance (`core/agent_maintenance.py`)
A utility to identify and purge orphaned Git branches and leftover report folders from previous runs.

## Contribution Workflow

### 1. Development & Testing
Work is performed in isolated branches created by the Agent Runner. To run tests:
```bash
python -m pytest agent_system/core/test_agent_runner_logic.py
```

### 2. Changelog Management
Every change must be recorded using the standardized logging tool:
```bash
python agent_system/reporting/log_change.py \
    --agent <agent_name> \
    --group "<workstream_slug>" \
    --tags "<Tag>" \
    --summary "Concise description" \
    --details "Technical bullet point"
```

### 3. Release Preparation
Before creating a release, run the changelog activity script to rebuild the history and generate previews:
```bash
python agent_system/reporting/changelog_activity.py --strict
```

## Documentation Set

- `README.md`: Overview and getting started guide.
- `agent_system/AGENTS.md`: Master protocol and workspace policy.
- `agent_system/docs/AGENT_RUNNER_TUTORIAL.md`: Detailed guide on the planner-executor workflow.
- `agent_system/docs/DEVELOPMENT.md`: This guide.
