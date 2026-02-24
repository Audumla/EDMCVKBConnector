"""
run_agent_plan.py - Generic agent orchestration wrapper for planning and delegation.

This script allows an agent (planner) to write a plan file and delegate its execution
to another agent/service (executor). It records planning metadata, execution results,
and combined cost estimates.

Usage:
    python agent_system/core/run_agent_plan.py \
        --planner gemini \
        --executor codex \
        --plan-file agent_artifacts/gemini/temp/my_plan.md \
        --task-summary "Description of the task" \
        --thinking-budget medium \
        [--planner-model gemini-2.0-flash] \
        [--planner-input-tokens 5000] [--planner-output-tokens 2000] \
        [--run-name label] [--dry-run] ...

All remaining args after known flags are forwarded to the executor's runner script
(e.g., run_codex_plan.py).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from agent_runner_utils import build_formatted_results, build_report, utc_now, extract_summary_from_plan

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
            "planner": _config_data.get("default_planner", "claude"),
            "executor": _config_data.get("default_executor", "codex"),
        }
    except json.JSONDecodeError:
        pass


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Agent orchestration wrapper: plans with one agent and delegates to another.",
        add_help=True,
    )
    # Orchestration args
    parser.add_argument("--planner", default=_config_defaults.get("planner", "claude"),
                        choices=["claude", "gemini", "codex", "opencode", "copilot", "local-llm"],
                        help="The agent that performed the planning.")
    parser.add_argument("--executor", default=_config_defaults.get("executor", "codex"),
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


def get_planner_defaults(planner: str) -> dict[str, Any]:
    cfg = _planners_config.get(planner, {})
    if not cfg.get("enabled", True):
        print(f"ERROR: Planner '{planner}' is currently disabled in configuration.", file=sys.stderr)
        sys.exit(1)
    return cfg


def run_executor(executor: str, plan_file: Path, thinking_budget: str, task_summary: str, extra_args: list[str]) -> tuple[int, str | None]:
    executor_cfg = _executors_config.get(executor, {})
    if not executor_cfg.get("enabled", True):
        print(f"ERROR: Executor '{executor}' is currently disabled in configuration.", file=sys.stderr)
        sys.exit(1)

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

    # Pass the specific model for the executor if defined in config
    if "model" in executor_cfg:
        cmd.extend(["--model", executor_cfg["model"]])

    # Pass thinking budget if not 'none'
    if thinking_budget and thinking_budget != "none":
        cmd.extend(["--thinking-budget", thinking_budget])

    # If the executor has a specific binary, pass it if the runner supports it
    if "bin" in executor_cfg:
        # Check if --bin is already in extra_args to avoid duplication
        if not any(arg == "--bin" for arg in extra_args):
            cmd.extend(["--bin", executor_cfg["bin"]])

    cmd.extend(extra_args)
    print(f"[run_agent_plan] Delegating to {executor} via {runner_script}", flush=True)
    print(f"[run_agent_plan] Launching: {' '.join(cmd)}", flush=True)

    proc = subprocess.run(cmd, capture_output=False, text=True,
                          stdout=subprocess.PIPE, stderr=None)
    stdout = proc.stdout or ""

    # Print so the caller can see progress
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

    # Resolve task summary
    task_summary = args.task_summary
    if not task_summary:
        task_summary = extract_summary_from_plan(args.plan_file)
        print(f"[run_agent_plan] Extracted summary: {task_summary}")

    # Resolve planner settings
    planner_defaults = get_planner_defaults(args.planner)
    model = args.planner_model or planner_defaults.get("model")
    in_tokens = args.planner_input_tokens if args.planner_input_tokens is not None else planner_defaults.get("input_tokens", 0)
    out_tokens = args.planner_output_tokens if args.planner_output_tokens is not None else planner_defaults.get("output_tokens", 0)
    
    # Resolve budget: CLI --thinking-budget (if provided) > Planner config > default 'none'
    budget = args.thinking_budget
    if budget is None:
        budget = planner_defaults.get("thinking_budget", "none")

    # Resolve executor settings
    executor_defaults = _executors_config.get(args.executor, {})
    executor_model = executor_defaults.get("model", "gpt-5")

    # Run the executor
    returncode, run_dir_str = run_executor(args.executor, args.plan_file, budget, task_summary, extra_args)

    if run_dir_str is None:
        print("[run_agent_plan] ERROR: Could not parse run directory from executor output.", file=sys.stderr)
        return returncode or 1

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
    
    report_file = run_dir / "agent_report.json"
    report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    
    formatted_results_file = run_dir / "agent_results.md"
    formatted_results_file.write_text(build_formatted_results(report), encoding="utf-8")
    
    print(f"[run_agent_plan] Report written: {report_file}", flush=True)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
