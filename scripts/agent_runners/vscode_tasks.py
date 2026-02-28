"""
vscode_tasks.py - Safe merge/remove of agent-system tasks in .vscode/tasks.json.

Injection is idempotent: tasks are identified by their label and a sentinel string
in their 'detail' field ("__agent-system__"). Re-running inject updates existing
tasks in-place and adds any missing ones without touching unrelated tasks.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

SENTINEL = "__agent-system__"


def _venv_python(runtime_dir: Path) -> str:
    if os.name == "nt":
        return str(runtime_dir / ".venv" / "Scripts" / "python.exe")
    return str(runtime_dir / ".venv" / "bin" / "python")


def build_task_definitions(runtime_dir: Path, workspace_var: str = "${workspaceFolder}") -> list[dict[str, Any]]:
    """Return the canonical list of agent-system VS Code task definitions."""
    py = _venv_python(runtime_dir)
    install = str(runtime_dir / "install.py")
    maintenance = str(runtime_dir / "agent_system" / "core" / "agent_maintenance.py")
    run_info = str(runtime_dir / "agent_system" / "core" / "get_latest_run_info.py")
    log_change = str(runtime_dir / "agent_system" / "reporting" / "log_change.py")
    build_cl = str(runtime_dir / "agent_system" / "reporting" / "build_changelog.py")

    tasks: list[dict[str, Any]] = [
        {
            "label": "[agent] Open Dashboard",
            "type": "shell",
            "command": py,
            "args": [install, "start", "--workspace", workspace_var],
            "presentation": {"reveal": "always", "panel": "dedicated", "focus": True},
            "problemMatcher": [],
            "detail": f"Launch the agent monitoring dashboard {SENTINEL}",
        },
        {
            "label": "[agent] Open Dashboard (Window)",
            "type": "shell",
            "command": "start" if os.name == "nt" else "bash",
            "args": (
                ["powershell", "{", py, install, "start", "--workspace", workspace_var, "}"]
                if os.name == "nt"
                else ["-c", f"{py} {install} start --workspace {workspace_var}"]
            ),
            "presentation": {"reveal": "never", "panel": "shared"},
            "problemMatcher": [],
            "detail": f"Launch the agent dashboard in a separate terminal window {SENTINEL}",
        },
        {
            "label": "[agent] Maintenance Audit",
            "type": "shell",
            "command": py,
            "args": [maintenance],
            "presentation": {"reveal": "always", "panel": "dedicated", "focus": True},
            "problemMatcher": [],
            "detail": f"Identify and purge orphaned agent branches and report folders {SENTINEL}",
        },
        {
            "label": "[agent] Merge Latest Changes",
            "type": "shell",
            "command": "git",
            "args": [
                "merge",
                f"$({py} {run_info} --agent ${{input:agentChoice}} --run-id \"${{input:runIdOverride}}\")",
            ],
            "presentation": {"reveal": "always", "panel": "dedicated", "focus": True},
            "problemMatcher": [],
            "detail": f"Merge the latest agent run branch into current branch {SENTINEL}",
        },
        {
            "label": "[agent] Update Agent System",
            "type": "shell",
            "command": py,
            "args": [install, "update"],
            "presentation": {"reveal": "always", "panel": "dedicated", "focus": True},
            "problemMatcher": [],
            "detail": f"Pull the latest agent-system code and update dependencies {SENTINEL}",
        },
        {
            "label": "[agent] Log Change",
            "type": "shell",
            "command": py,
            "args": [log_change, "--agent", "${input:agentChoice}", "--group", "${input:changeGroup}",
                     "--tags", "${input:changeTags}", "--summary", "${input:changeSummary}",
                     "--details", "${input:changeDetails}"],
            "presentation": {"reveal": "always", "panel": "dedicated", "focus": True},
            "problemMatcher": [],
            "detail": f"Record a change entry in the project changelog {SENTINEL}",
        },
        {
            "label": "[agent] Rebuild Changelog",
            "type": "shell",
            "command": py,
            "args": [build_cl],
            "presentation": {"reveal": "always", "panel": "dedicated", "focus": True},
            "problemMatcher": [],
            "detail": f"Regenerate CHANGELOG.md from JSON changelog data {SENTINEL}",
        },
    ]
    return tasks


AGENT_TASK_LABELS = {
    "[agent] Open Dashboard",
    "[agent] Open Dashboard (Window)",
    "[agent] Maintenance Audit",
    "[agent] Merge Latest Changes",
    "[agent] Update Agent System",
    "[agent] Log Change",
    "[agent] Rebuild Changelog",
}

AGENT_INPUTS = [
    {
        "id": "agentChoice",
        "type": "pickString",
        "description": "Select the agent whose work you want to review/merge",
        "default": "gemini",
        "options": ["gemini", "claude", "codex", "opencode", "copilot"],
    },
    {
        "id": "runIdOverride",
        "type": "promptString",
        "description": "Optional: Enter a specific Run ID (leave blank for latest)",
        "default": "",
    },
    {
        "id": "changeGroup",
        "type": "promptString",
        "description": "Workstream/group slug for the changelog entry",
        "default": "",
    },
    {
        "id": "changeTags",
        "type": "promptString",
        "description": "Tag(s) for the changelog entry (e.g. 'New Feature')",
        "default": "New Feature",
    },
    {
        "id": "changeSummary",
        "type": "promptString",
        "description": "One-sentence summary of the change",
        "default": "",
    },
    {
        "id": "changeDetails",
        "type": "promptString",
        "description": "Bullet-point details (separate with semicolons)",
        "default": "",
    },
]


def _load_tasks_json(tasks_file: Path) -> dict[str, Any]:
    if tasks_file.exists():
        try:
            return json.loads(tasks_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"version": "2.0.0", "tasks": [], "inputs": []}


def _write_tasks_json(tasks_file: Path, data: dict[str, Any]) -> None:
    tasks_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = tasks_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    if tasks_file.exists():
        bak = tasks_file.with_suffix(".json.bak")
        shutil.copy2(tasks_file, bak)
    tmp.replace(tasks_file)


def inject_tasks(workspace: Path, runtime_dir: Path) -> list[str]:
    """Merge agent-system tasks into workspace/.vscode/tasks.json.

    Returns the list of task labels that were added or updated.
    """
    tasks_file = workspace / ".vscode" / "tasks.json"
    data = _load_tasks_json(tasks_file)

    existing_tasks: list[dict] = data.get("tasks", [])
    existing_inputs: list[dict] = data.get("inputs", [])

    new_definitions = build_task_definitions(runtime_dir)
    new_by_label = {t["label"]: t for t in new_definitions}

    # Update existing agent-system tasks, remove stale ones
    kept = [t for t in existing_tasks if t.get("label") not in AGENT_TASK_LABELS]
    changed: list[str] = []
    for label, task_def in new_by_label.items():
        kept.append(task_def)
        changed.append(label)

    # Merge inputs: update existing by id, add missing
    existing_input_ids = {inp.get("id") for inp in existing_inputs}
    merged_inputs = list(existing_inputs)
    for inp in AGENT_INPUTS:
        if inp["id"] not in existing_input_ids:
            merged_inputs.append(inp)

    data["tasks"] = kept
    data["inputs"] = merged_inputs
    _write_tasks_json(tasks_file, data)
    return changed


def remove_tasks(workspace: Path) -> list[str]:
    """Remove all agent-system tasks from workspace/.vscode/tasks.json.

    Returns the list of task labels that were removed.
    """
    tasks_file = workspace / ".vscode" / "tasks.json"
    if not tasks_file.exists():
        return []
    data = _load_tasks_json(tasks_file)
    before = {t.get("label") for t in data.get("tasks", [])}
    data["tasks"] = [t for t in data.get("tasks", []) if t.get("label") not in AGENT_TASK_LABELS]
    agent_input_ids = {inp["id"] for inp in AGENT_INPUTS}
    data["inputs"] = [i for i in data.get("inputs", []) if i.get("id") not in agent_input_ids]
    _write_tasks_json(tasks_file, data)
    removed = list(before & AGENT_TASK_LABELS)
    return removed


if __name__ == "__main__":
    # Quick CLI for testing: python vscode_tasks.py inject <workspace> <runtime>
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["inject", "remove"])
    p.add_argument("workspace", type=Path)
    p.add_argument("runtime", type=Path, nargs="?", default=None)
    args = p.parse_args()
    if args.action == "inject":
        if not args.runtime:
            print("runtime dir required for inject", file=sys.stderr)
            sys.exit(1)
        labels = inject_tasks(args.workspace, args.runtime)
        print(f"Injected/updated {len(labels)} tasks: {', '.join(labels)}")
    else:
        labels = remove_tasks(args.workspace)
        print(f"Removed {len(labels)} tasks: {', '.join(labels)}")
