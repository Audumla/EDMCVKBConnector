"""Executor dispatch command construction and process handling."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from runtime_paths import RUNTIME_ROOT, ARTIFACTS_ROOT


def build_executor_command(
    *,
    project_root: Path,
    executor: str,
    executor_cfg: dict[str, Any],
    plan_file: Path,
    task_summary: str,
    thinking_budget: str,
    extra_args: list[str],
    executor_model: str | None,
) -> tuple[list[str], str]:
    runner_script = executor_cfg.get("runner", "run_codex_plan.py")
    runner_name = Path(runner_script).name.lower()
    output_root = ARTIFACTS_ROOT / executor / "reports" / "plan_runs"
    worktree_root = ARTIFACTS_ROOT / executor / "temp" / "worktrees"

    cmd = [
        sys.executable,
        str(RUNTIME_ROOT / "agent_system" / runner_script),
        "--plan-file", str(plan_file),
        "--output-root", str(output_root),
        "--worktree-root", str(worktree_root),
        "--task-summary", task_summary,
        "--workspace", str(project_root),
    ]

    model_override = executor_model or executor_cfg.get("model")
    if model_override:
        cmd.extend(["--model", str(model_override)])

    if thinking_budget and thinking_budget != "none":
        cmd.extend(["--thinking-budget", thinking_budget])

    if "bin" in executor_cfg:
        # Codex runner uses a dedicated arg name for its CLI executable.
        bin_flag = "--codex-bin" if runner_name == "run_codex_plan.py" else "--bin"
        if not any(arg == bin_flag for arg in extra_args):
            cmd.extend([bin_flag, str(executor_cfg["bin"])])

    runner_args = executor_cfg.get("runner_args", [])
    if isinstance(runner_args, list):
        cmd.extend([str(arg) for arg in runner_args])

    cmd.extend(extra_args)
    return cmd, runner_script


def run_executor_process(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, (proc.stdout or ""), (proc.stderr or "")


def extract_run_directory(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith("Run directory:") or line.startswith("Dry run created:"):
            return line.split(":", 1)[1].strip()
    return None
