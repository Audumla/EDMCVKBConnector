"""
agent_management.py - Externalized agent lifecycle management operations.

This module owns run dispatch and run lifecycle actions so UI layers can remain
presentation-only.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from agent_runner_utils import PROJECT_ROOT, write_json_safe
from runtime_paths import RUNTIME_ROOT, ARTIFACTS_ROOT
from tag_parser import parse_inline_tags


def _build_plan_content(prompt: str) -> str:
    return f"""# BOUNDARY ENFORCEMENT & SAFETY MANDATE
- **Workspace**: You MUST only work within the current directory.
- **Isolation**: You are running in an isolated Git worktree on a dedicated branch.
- **No Escaping**: Do not attempt to access paths outside of the current directory tree.
- **Goal**: {prompt}
"""


def dispatch_task(
    prompt: str,
    planner: str,
    executor: str,
    budget: str,
    model: str | None = None,
) -> tuple[bool, str]:
    if not prompt.strip():
        return False, "Prompt is required."

    # Apply inline tag overrides (#plan, #exec, #budget, #agent:...)
    tags = parse_inline_tags(prompt)
    if tags["planner"]:
        planner = tags["planner"]
    if tags["executor"]:
        executor = tags["executor"]
    if tags["budget"]:
        budget = tags["budget"]
    # Use the cleaned prompt (tags stripped) as the plan goal
    clean = tags["clean_prompt"] or prompt.strip()

    plan_dir = ARTIFACTS_ROOT / planner / "temp"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_file = plan_dir / f"dispatch_{int(time.time())}.md"
    plan_file.write_text(_build_plan_content(clean), encoding="utf-8")

    cmd: list[str] = [
        sys.executable,
        str(RUNTIME_ROOT / "agent_system" / "core" / "run_agent_plan.py"),
        "--planner",
        planner,
        "--executor",
        executor,
        "--thinking-budget",
        budget,
        "--plan-file",
        str(plan_file),
        "--task-summary",
        clean[:50],
        "--workspace",
        str(PROJECT_ROOT),
    ]
    if model:
        cmd.extend(["--executor-model", model])

    creationflags = 0x00000008 if os.name == "nt" else 0
    subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    model_label = model or "default model"
    return True, f"Task dispatched: {model_label}"


def merge_run(run: dict[str, Any]) -> tuple[bool, str]:
    branch = run.get("branch")
    if not branch:
        return False, "Selected run has no branch to merge."

    shutil.rmtree(run["dir"] / "worktree", ignore_errors=True)
    result = subprocess.run(["git", "merge", branch], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "merge failed").strip()
        return False, f"Merge failed: {err}"

    if "lifecycle" not in run:
        run["lifecycle"] = {}
    run["lifecycle"]["state"] = "merged"
    write_json_safe(run["dir"] / "metadata.json", run)
    return True, "Merged successfully."


def kill_run(run: dict[str, Any]) -> tuple[bool, str]:
    pid = run.get("pid")
    if not pid:
        return False, "Selected run has no process id."

    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "taskkill failed").strip()
            return False, f"Kill failed: {err}"
        return True, "Process killed."

    try:
        os.kill(int(pid), 9)
        return True, "Process killed."
    except OSError as exc:
        return False, f"Kill failed: {exc}"


def delete_run(run: dict[str, Any]) -> tuple[bool, str]:
    run_id = run.get("id")
    agent = run.get("agent")
    if not run_id or not agent:
        return False, "Selected run metadata is incomplete."

    shutil.rmtree(run["dir"], ignore_errors=True)
    worktree_dir = ARTIFACTS_ROOT / agent / "temp" / "worktrees" / run_id.replace(":", "_")
    if worktree_dir.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_dir)],
            cwd=PROJECT_ROOT,
            capture_output=True,
        )
        shutil.rmtree(worktree_dir, ignore_errors=True)

    branch = run.get("branch")
    if branch:
        subprocess.run(["git", "branch", "-D", branch], cwd=PROJECT_ROOT, capture_output=True)
    subprocess.run(["git", "worktree", "prune"], cwd=PROJECT_ROOT, capture_output=True)
    return True, "Artifacts and worktree purged."


def run_maintenance() -> tuple[bool, str]:
    cmd = [sys.executable, str(RUNTIME_ROOT / "agent_system" / "core" / "agent_maintenance.py")]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "maintenance failed").strip()
        return False, f"Maintenance failed: {err}"
    return True, "Maintenance completed."
