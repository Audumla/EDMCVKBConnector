# Agent System

A universal AI agent orchestration and automated changelog management system.

## Features

- **Agent Runner**: Orchestrate planning and execution between different AI models (Gemini, Claude, Codex, Local LLMs).
- **Interactive Dashboard**: Professional TUI for monitoring logs, managing runs, and merging results.
- **Automated Changelog**: Structured JSON-based changelog that lives in your target workspace's git history.
- **Isolated Execution**: Every agent run executes in a temporary Git worktree for safety and non-blocking development.
- **Cross-Agent Protocol**: Unified inline tag dispatch (`#plan`, `#exec`, `#budget`) for Copilot, Claude, Gemini, and local agents.
- **Portable Install**: One script installs the system globally and injects VS Code tasks into any workspace.

---

## Installation

The agent system lives in its own git repository, separate from any project you work on.
Run `install.py` to set it up. All you need is Python 3.9+.

### New machine — first time setup

```bash
# Clone the repo to a persistent location (recommended)
git clone <repo-url> ~/.agent-system/runtime

# Install and wire up your current workspace
python ~/.agent-system/runtime/install.py install --workspace .
```

Or use the platform wrapper from inside the cloned repo:

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File .\scripts\agent_runners\bootstrap.ps1 -Workspace (Get-Location).Path

# macOS / Linux
bash ./scripts/agent_runners/bootstrap.sh --workspace .
```

The installer:

1. Creates a `.venv` inside the runtime dir and installs Python dependencies
2. Injects `[agent]` tasks into your workspace's `.vscode/tasks.json`
3. Appends a `.gitignore` block to exclude machine-local agent files
4. Seeds empty `agent_system/CHANGELOG.md` and data files in your workspace (tracked by that project's git)
5. Writes `.vscode/agent-system.json` (machine-local, git-ignored — stores the runtime path)

### Wiring to an additional workspace

```bash
python ~/.agent-system/runtime/install.py install --workspace /path/to/other-project
```

### Install options

| Flag | Description |
| --- | --- |
| `--workspace <path>` | Target project path (default: current directory) |
| `--runtime-dir <path>` | Where to install the runtime (default: `~/.agent-system/runtime`) |
| `--state-home <path>` | Artifact storage root (default: `~/.agent-system`) |
| `--repo-url <url>` | Git URL to clone from (auto-detected if run from inside the repo) |
| `--force` | Recreate the virtual environment from scratch |

---

## Updating

```bash
python ~/.agent-system/runtime/install.py update
```

This pulls the latest code via `git pull --ff-only` (never force-resets local changes) and upgrades pip dependencies.

Or from VS Code: run the **[agent] Update Agent System** task.

---

## Launching the dashboard

```bash
python ~/.agent-system/runtime/install.py start --workspace .
```

Or from VS Code: run the **[agent] Open Dashboard** task.

---

## Uninstalling from a workspace

```bash
# Remove VS Code tasks and .gitignore block only (keeps runtime)
python ~/.agent-system/runtime/install.py uninstall --workspace .

# Also delete the runtime directory
python ~/.agent-system/runtime/install.py uninstall --workspace . --remove-runtime
```

---

## Inline dispatch tags

When writing prompts in Claude Code, Copilot Chat, Gemini CLI, or any other AI provider's
inline window, use these tags to route work to specific agents:

```text
#plan gemini #exec codex fix the broken unit tests
#plan claude #exec opencode #budget high refactor the VKB manager
#agent:deep:gemini add telemetry to the event handler
```

| Tag | Effect |
| --- | --- |
| `#plan <provider>` | Sets the planning agent |
| `#exec <provider>` | Sets the executor agent |
| `#budget <level>` | Sets thinking budget (`none`/`low`/`medium`/`high`) |
| `#agent:<budget>:<planner>` | Legacy form — sets planner + budget |

---

## Changelog

Changelog entries are stored in **your workspace** (not the runtime repo) so they become
part of your project's git history:

```text
<workspace>/
├── agent_system/
│   ├── CHANGELOG.md               ← human-readable, auto-generated
│   └── reporting/data/
│       ├── CHANGELOG.json         ← active entries
│       ├── CHANGELOG.archive.json ← released entries
│       └── CHANGELOG.summaries.json
```

Log a change:

```bash
python ~/.agent-system/runtime/agent_system/reporting/log_change.py \
    --agent claude \
    --group "MyFeature" \
    --tags "New Feature" \
    --summary "Added inline tag dispatch" \
    --details "Parses #plan and #exec tags" "Routes to configured providers"
```

Or use the VS Code **[agent] Log Change** task.

---

## What gets committed to your workspace's git

| File | Tracked | Reason |
| --- | --- | --- |
| `agent_system/CHANGELOG.md` | Yes | Project history |
| `agent_system/reporting/data/*.json` | Yes | Changelog data |
| `.vscode/tasks.json` | Yes | Shared with team |
| `.vscode/settings.json` | Yes | Python env config |
| `.vscode/agent-system.json` | **No** | Machine-local path |
| `agent_artifacts/` | **No** | Runtime outputs |
| `.agent-state/` | **No** | Runtime state |

---

## Project structure

```text
agent_system/
├── core/          Central orchestration and path resolution
├── runners/       Native CLI wrappers (Claude, Gemini, Codex, ...)
├── dashboard/     Textual TUI monitoring interface
├── reporting/     Changelog and release note automation
└── config/        Provider registry and delegation config

scripts/agent_runners/
├── install.py (root)    Portable installer entry point
├── manage_runtime.py    Venv + dashboard launcher
├── vscode_tasks.py      VS Code task injection helper
├── gitignore_inject.py  .gitignore block helper
├── bootstrap.sh/.ps1    Platform wrappers
└── start_dashboard.*    Direct dashboard launchers
```

---

## Maintenance

Identify and purge orphaned branches and temporary files:

```bash
python ~/.agent-system/runtime/agent_system/core/agent_maintenance.py
```

Or use the VS Code **[agent] Maintenance Audit** task.
