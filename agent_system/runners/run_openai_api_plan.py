"""
run_openai_api_plan.py - Generic OpenAI-compatible API executor runner.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import (
    utc_now,
    slugify,
    write_json_safe,
    create_isolated_worktree,
    cleanup_worktree,
    extract_summary_from_plan,
)


def _read_plan_text(plan_file: Path) -> str:
    try:
        return plan_file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return plan_file.read_text(encoding="utf-16")
        except UnicodeDecodeError:
            return plan_file.read_text(encoding="latin-1")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--worktree-root", required=True, type=Path)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--thinking-budget", choices=["none", "low", "medium", "high"], default="none")
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--task-summary", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ')}_api_{slugify(args.plan_file.stem)}"
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    branch, worktree, repo = create_isolated_worktree(Path.cwd(), run_id, args.worktree_root)

    status = {
        "run_id": run_id,
        "state": "running",
        "phase": "executing",
        "started_at": utc_now(),
        "pid": os.getpid(),
    }
    write_json_safe(run_dir / "status.json", status)

    task_summary = args.task_summary or extract_summary_from_plan(args.plan_file)
    meta = {
        "task_summary": task_summary,
        "isolation": {"branch_name": branch},
        "cost_estimate": {
            "model": args.model,
            "total_usd": 0.0,
            "note": "Cost estimation unavailable for generic API runner",
        },
    }
    write_json_safe(run_dir / "metadata.json", meta)

    if args.dry_run:
        status["state"] = "dry_run"
        status["ended_at"] = utc_now()
        write_json_safe(run_dir / "status.json", status)
        print(f"Dry run created: {run_dir}")
        return 0

    api_key = os.getenv(args.api_key_env, "").strip()
    if not api_key:
        err = f"Missing API key env var: {args.api_key_env}"
        (run_dir / "stderr.log").write_text(err, encoding="utf-8")
        status["state"] = "failed"
        status["error"] = err
        status["ended_at"] = utc_now()
        write_json_safe(run_dir / "status.json", status)
        return 1

    plan_text = _read_plan_text(args.plan_file)
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": plan_text}],
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{args.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        content = ""
        if isinstance(data, dict):
            choices = data.get("choices", [])
            if choices and isinstance(choices[0], dict):
                content = (choices[0].get("message", {}) or {}).get("content", "")
        (run_dir / "stdout.log").write_text(str(content), encoding="utf-8")
        status["state"] = "succeeded"
        status["phase"] = "done"
        return_code = 0
    except Exception as e:
        err = f"API Error: {e}"
        (run_dir / "stderr.log").write_text(err, encoding="utf-8")
        status["state"] = "failed"
        status["phase"] = "done"
        status["error"] = err
        return_code = 1

    status["ended_at"] = utc_now()
    write_json_safe(run_dir / "status.json", status)

    if not args.no_cleanup:
        cleanup_worktree(repo, worktree, branch, keep_branch=(status["state"] == "succeeded"))

    print(f"Run directory: {run_dir}")
    return return_code


if __name__ == "__main__":
    sys.exit(main())
