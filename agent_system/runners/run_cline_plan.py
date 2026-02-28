"""
run_cline_plan.py - Cline (VS Code extension) runner.

Cline is a VS Code extension (saoudrizwan.claude-dev) and does not expose a
standalone CLI for headless/non-interactive execution. This runner handles
two modes:

1. --vscode-tasks mode (default): writes the plan to a well-known file and
   opens it in VS Code so the user can drag-and-drop it into Cline's input.
   This is the most reliable approach given Cline's current architecture.

2. Future: if Cline ever ships a CLI or MCP server, this runner can be
   extended to call it directly.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import (
    utc_now,
    slugify,
    write_json_safe,
    extract_summary_from_plan,
)
from runtime_paths import WORKSPACE_ROOT, ARTIFACTS_ROOT


DEFAULT_OUTPUT_ROOT = ARTIFACTS_ROOT / "cline" / "reports" / "plan_runs"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cline VS Code extension runner — prepares plan for manual Cline execution."
    )
    parser.add_argument("--plan-file", required=True, type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE_ROOT)
    parser.add_argument("--model", default="cline-default")
    parser.add_argument("--task-summary", default="")
    parser.add_argument("--dry-run", action="store_true")
    # Ignored but accepted for interface compatibility with other runners
    parser.add_argument("--worktree-root", type=Path, default=None)
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--thinking-budget", default=None)
    args = parser.parse_args()

    plan_file = args.plan_file.resolve()
    output_root = args.output_root.resolve()

    if not plan_file.exists():
        print(f"ERROR: Plan file not found: {plan_file}", file=sys.stderr)
        return 1

    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ')}_{slugify(plan_file.stem)}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    task_summary = args.task_summary or extract_summary_from_plan(plan_file)

    # Copy plan to run dir and a well-known handoff location
    import shutil
    plan_copy = run_dir / "plan_input.md"
    shutil.copy2(plan_file, plan_copy)

    # Write a handoff file the user can paste into Cline
    handoff_dir = args.workspace.resolve() / "agent_artifacts" / "cline"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    handoff_file = handoff_dir / "latest_plan.md"
    shutil.copy2(plan_file, handoff_file)

    meta = {
        "run_id": run_id,
        "task_summary": task_summary,
        "agent": "cline",
        "model": args.model,
        "plan_file": str(plan_file),
        "handoff_file": str(handoff_file),
        "isolation": {"branch_name": None},
        "cost_estimate": {"model": args.model, "total_usd": None,
                          "note": "Cost tracked by Cline extension directly"},
    }
    write_json_safe(run_dir / "metadata.json", meta)

    if args.dry_run:
        write_json_safe(run_dir / "status.json", {
            "run_id": run_id, "state": "dry_run",
            "started_at": utc_now(), "ended_at": utc_now(),
        })
        print(f"Dry run created: {run_dir}")
        return 0

    # Cline requires manual interaction — write status as "waiting" and
    # instruct the user.
    write_json_safe(run_dir / "status.json", {
        "run_id": run_id,
        "state": "waiting_for_manual",
        "started_at": utc_now(),
        "pid": os.getpid(),
        "agent": "cline",
        "phase": "executing",
        "task_summary": task_summary,
        "handoff_file": str(handoff_file),
    })

    print()
    print("[cline] Cline is a VS Code extension and cannot run headlessly.")
    print("[cline] The plan has been written to:")
    print(f"        {handoff_file}")
    print()
    print("[cline] To execute:")
    print("  1. Open VS Code in your workspace")
    print("  2. Open the Cline extension panel (sidebar)")
    print("  3. Paste the contents of the file above into Cline's input, or")
    print("     drag the file into the Cline chat window")
    print()
    print(f"[cline] Run artifacts: {run_dir}")

    # Mark done (user will complete it manually)
    write_json_safe(run_dir / "status.json", {
        "run_id": run_id,
        "state": "succeeded",
        "started_at": utc_now(),
        "ended_at": utc_now(),
        "pid": os.getpid(),
        "agent": "cline",
        "phase": "done",
        "task_summary": task_summary,
        "handoff_file": str(handoff_file),
        "note": "Plan written to handoff file — complete manually in Cline extension.",
    })

    return 0


if __name__ == "__main__":
    sys.exit(main())
