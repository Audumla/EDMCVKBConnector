"""
run_agent_plan.py - Generic agent orchestration wrapper for planning and delegation.

This script allows an agent (planner) to write a plan file and delegate its execution
to another agent/service (executor). It records planning metadata, execution results,
and combined cost estimates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from agent_runner_utils import (
    build_formatted_results, build_report, utc_now, 
    extract_summary_from_plan, slugify, write_json_safe
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load default configuration
CONFIG_FILE = PROJECT_ROOT / "agent_system" / "config" / "delegation-config.json"
_config_defaults = {}
_planners_config = {}
_executors_config = {}

if CONFIG_FILE.exists():
    try:
        _config_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        _planners_config = _config_data.get("planners", {})
        _executors_config = _config_data.get("executors", {})
        _config_defaults = {
            "planner": _config_data.get("default_planner", "gemini"),
            "executor": _config_data.get("default_executor", "gemini"),
        }
    except json.JSONDecodeError:
        pass


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Agent orchestration wrapper: plans with one agent and delegates to another.",
        add_help=True,
    )
    # Orchestration args
    parser.add_argument("--planner", default=_config_defaults.get("planner", "gemini"),
                        choices=["claude", "gemini", "codex", "opencode", "copilot", "local-llm"],
                        help="The agent that performed the planning.")
    parser.add_argument("--executor", default=_config_defaults.get("executor", "gemini"),
                        choices=["codex", "opencode", "gemini", "local-llm"],
                        help="The agent/service that will execute the plan.")
    
    # Planner-specific overrides
    parser.add_argument("--planner-model", help="Override planner model ID.")
    parser.add_argument("--planner-input-tokens", type=int, help="Input tokens used by planner.")
    parser.add_argument("--planner-output-tokens", type=int, help="Output tokens used by planner.")
    
    # Common args
    parser.add_argument("--thinking-budget", default=None,
                        choices=["none", "low", "medium", "high"],
                        help="Complexity/thinking budget for the task.")
    parser.add_argument("--task-summary", default="",
                        help="One-line description of the task.")
    
    # Required: plan file
    parser.add_argument("--plan-file", required=True, type=Path,
                        help="Path to the plan file to execute.")

    return parser.parse_known_args()


def create_failure_report(executor: str, task_summary: str, error_msg: str, generated_at: str) -> Path:
    """Create a minimal failure report directory for the dashboard."""
    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ')}_val-fail"
    run_dir = PROJECT_ROOT / "agent_artifacts" / executor / "reports" / "plan_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    status = {
        "run_id": run_id,
        "state": "failed",
        "started_at": generated_at,
        "ended_at": utc_now(),
        "error": error_msg
    }
    write_json_safe(run_dir / "status.json", status)
    
    meta = {
        "task_summary": f"VALIDATION FAILED: {task_summary}",
        "isolation": {"branch_name": "none"},
        "cost_estimate": {"model": "n/a", "total_usd": 0.0}
    }
    write_json_safe(run_dir / "metadata.json", meta)
    
    with open(run_dir / "stderr.log", "w", encoding="utf-8") as f:
        f.write(error_msg)
        
    return run_dir


def run_executor(executor: str, plan_file: Path, thinking_budget: str, task_summary: str, extra_args: list[str]) -> tuple[int, str | None]:
    executor_cfg = _executors_config.get(executor, {})
    if not executor_cfg.get("enabled", True):
        return 1, None # Validation should have caught this, but safety first

    runner_script = executor_cfg.get("runner", "run_codex_plan.py")
    
    # Dynamically set artifact paths based on the executor name
    output_root = PROJECT_ROOT / "agent_artifacts" / executor / "reports" / "plan_runs"
    worktree_root = PROJECT_ROOT / "agent_artifacts" / executor / "temp" / "worktrees"

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "agent_system" / runner_script),
        "--plan-file", str(plan_file),
        "--output-root", str(output_root),
        "--worktree-root", str(worktree_root),
        "--task-summary", task_summary,
    ]

    if "model" in executor_cfg:
        cmd.extend(["--model", executor_cfg["model"]])

    if thinking_budget and thinking_budget != "none":
        cmd.extend(["--thinking-budget", thinking_budget])

    if "bin" in executor_cfg:
        if not any(arg == "--bin" for arg in extra_args):
            cmd.extend(["--bin", executor_cfg["bin"]])

    cmd.extend(extra_args)
    print(f"[run_agent_plan] Launching: {' '.join(cmd)}", flush=True)

    proc = subprocess.run(cmd, capture_output=False, text=True,
                          stdout=subprocess.PIPE, stderr=None)
    stdout = proc.stdout or ""
    print(stdout, end="", flush=True)

    run_dir: str | None = None
    for line in stdout.splitlines():
        if line.startswith("Run directory:") or line.startswith("Dry run created:"):
            run_dir = line.split(":", 1)[1].strip()
            break

    return proc.returncode, run_dir


def main() -> int:
    args, extra_args = parse_args()
    generated_at = utc_now()

    # 1. Pre-flight Validation
    error_msg = None
    if not args.plan_file.exists():
        error_msg = f"Plan file not found: {args.plan_file}"
    else:
        planner_cfg = _planners_config.get(args.planner, {})
        if not planner_cfg.get("enabled", True):
            error_msg = f"Planner '{args.planner}' is currently disabled in configuration."
        
        executor_cfg = _executors_config.get(args.executor, {})
        if not executor_cfg.get("enabled", True):
            error_msg = f"Executor '{args.executor}' is currently disabled in configuration."
            
    if error_msg:
        print(f"ERROR: {error_msg}", file=sys.stderr)
        create_failure_report(args.executor, args.task_summary or args.plan_file.stem, error_msg, generated_at)
        return 1

    # Resolve task summary
    task_summary = args.task_summary or extract_summary_from_plan(args.plan_file)

    # Resolve planner settings
    planner_defaults = _planners_config.get(args.planner, {})
    model = args.planner_model or planner_defaults.get("model")
    in_tokens = args.planner_input_tokens if args.planner_input_tokens is not None else planner_defaults.get("input_tokens", 0)
    out_tokens = args.planner_output_tokens if args.planner_output_tokens is not None else planner_defaults.get("output_tokens", 0)
    
    budget = args.thinking_budget or planner_defaults.get("thinking_budget", "none")
    executor_defaults = _executors_config.get(args.executor, {})
    executor_model = executor_defaults.get("model", "gpt-5")

    # 2. Run the executor
    returncode, run_dir_str = run_executor(args.executor, args.plan_file, budget, task_summary, extra_args)

    if run_dir_str is None:
        print("[run_agent_plan] ERROR: Executor failed to provide a run directory.", file=sys.stderr)
        create_failure_report(args.executor, task_summary, "Executor failed to provide a run directory.", generated_at)
        return returncode or 1

    # 3. Final Report
    run_dir = Path(run_dir_str)
    report = build_report(
        run_dir=run_dir,
        planner_model=model,
        planner_input_tokens=in_tokens,
        planner_output_tokens=out_tokens,
        thinking_budget=budget,
        codex_model_hint=executor_model,
        task_summary=task_summary,
        codex_returncode=returncode,
        generated_at=generated_at,
    )
    
    (run_dir / "agent_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (run_dir / "agent_results.md").write_text(build_formatted_results(report), encoding="utf-8")
    
    print(f"[run_agent_plan] Report written: {run_dir / 'agent_report.json'}", flush=True)
    return returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
