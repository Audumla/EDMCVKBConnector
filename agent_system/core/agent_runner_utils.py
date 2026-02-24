"""
agent_runner_utils.py - Shared utilities for native agent runners.
"""
import json
import os
import re
import subprocess
import shutil
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_TYPES = ["gemini", "claude", "codex", "opencode", "copilot", "local-llm"]

def _safe_read_json(path: Path):
    if not path.exists(): return None
    for _ in range(3):
        try: return json.loads(path.read_text(encoding="utf-8-sig"))
        except: time.sleep(0.05)
    return None

def get_all_runs(limit: int = 30, state_filter: str = None) -> list[dict]:
    all_runs = []
    for agent in AGENT_TYPES:
        output_root = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs"
        if output_root.exists():
            for p in output_root.iterdir():
                status_file = p / "status.json"
                meta_file = p / "metadata.json"
                if status_file.exists():
                    try:
                        status = _safe_read_json(status_file)
                        if not status: continue
                        if state_filter and status.get("state") != state_filter:
                            continue
                            
                        meta = _safe_read_json(meta_file) if meta_file.exists() else {}
                        mtime = max(p.stat().st_mtime, status_file.stat().st_mtime)
                        all_runs.append({
                            "id": p.name,
                            "agent": agent,
                            "dir": p,
                            "state": status.get("state", "unknown"),
                            "pid": status.get("pid"),
                            "model": status.get("cost_estimate", {}).get("model", "n/a"),
                            "cost": float(status.get("cost_estimate", {}).get("total_usd") or 0.0),
                            "tokens": int(status.get("token_usage", {}).get("output_tokens") or 0),
                            "branch": meta.get("isolation", {}).get("branch_name") if meta else None,
                            "summary": meta.get("task_summary", "No summary provided") if meta else "No summary provided",
                            "mtime": mtime
                        })
                    except: continue
    all_runs.sort(key=lambda x: x["mtime"], reverse=True)
    return all_runs[:limit]

def load_delegation_config() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parent.parent / "config" / "delegation-config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}

def get_enabled_planners() -> list[str]:
    config = load_delegation_config()
    planners = config.get("planners", {})
    return [p for p in planners if planners[p].get("enabled", True)]

def get_enabled_executors() -> list[str]:
    config = load_delegation_config()
    executors = config.get("executors", {})
    return [e for e in executors if executors[e].get("enabled", True)]

def get_agent_models(agent_type: str) -> list[str]:
    config = load_delegation_config()
    # Check both planners and executors for models
    models = set()
    planner_cfg = config.get("planners", {}).get(agent_type, {})
    if planner_cfg.get("model"):
        models.add(planner_cfg["model"])
    
    executor_cfg = config.get("executors", {}).get(agent_type, {})
    if executor_cfg.get("model"):
        models.add(executor_cfg["model"])
        
    return sorted(list(models)) if models else ["default"]

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return cleaned.strip("-") or "run"

def write_json_safe(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for i in range(5):
        try:
            if path.exists(): os.remove(path)
            temp_path.replace(path)
            return
        except: time.sleep(0.1)

def resolve_git_root(workspace: Path) -> Path:
    res = subprocess.run(["git", "-C", str(workspace), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if res.returncode != 0: raise RuntimeError("Not a git repo")
    return Path(res.stdout.strip())

def create_isolated_worktree(workspace: Path, run_id: str, worktree_root: Path):
    repo_root = resolve_git_root(workspace)
    branch_name = f"agent/run/{run_id}"
    worktree_dir = worktree_root / run_id.replace(":", "_")
    
    print(f"Preparing worktree (new branch '{branch_name}')")
    subprocess.run(["git", "-C", str(repo_root), "worktree", "add", "-b", branch_name, str(worktree_dir), "HEAD"], check=True)
    
    # Sync all changes including untracked
    # We use stash push --include-untracked to ensure everything is captured
    status = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain"], capture_output=True, text=True)
    if status.stdout.strip():
        print(f"Syncing current workspace changes to worktree...")
        # Push everything to a temporary stash
        subprocess.run(["git", "-C", str(repo_root), "stash", "push", "--include-untracked", "-m", f"sync-{run_id}"], check=True)
        
        # Apply the stash to the new worktree
        # Note: we use 'apply' instead of 'pop' so the main branch remains clean during execution
        # but the worktree gets the files.
        subprocess.run(["git", "-C", str(worktree_dir), "stash", "apply", "stash@{0}"], check=True)
        
        # Pop it back onto the main branch immediately so the user doesn't lose their view
        subprocess.run(["git", "-C", str(repo_root), "stash", "pop"], check=True)
        
    return branch_name, worktree_dir, repo_root

def cleanup_worktree(repo_root: Path, worktree_dir: Path, branch_name: str, keep_branch=True):
    subprocess.run(["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree_dir)])
    if not keep_branch:
        subprocess.run(["git", "-C", str(repo_root), "branch", "-D", branch_name])
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)

def build_report(
    run_dir: Path,
    planner_model: str,
    planner_input_tokens: int,
    planner_output_tokens: int,
    thinking_budget: str,
    codex_model_hint: str,
    task_summary: str,
    codex_returncode: int,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "run_id": run_dir.name,
        "task_summary": task_summary,
        "generated_at": generated_at,
        "planner": {
            "model": planner_model,
            "input_tokens": planner_input_tokens,
            "output_tokens": planner_output_tokens,
            "thinking_budget": thinking_budget,
        },
        "executor": {
            "model": codex_model_hint,
            "returncode": codex_returncode,
            "state": "succeeded" if codex_returncode == 0 else "failed",
        },
        "stats": {
            "total_cost_usd": 0.0,  # Placeholder or calculate if needed
            "output_tokens": planner_output_tokens, # Simplified
        }
    }


def build_formatted_results(report: dict[str, Any]) -> str:
    return f"""# Execution Results: {report['run_id']}

- **Task**: {report['task_summary']}
- **Status**: {report['executor']['state'].upper()}
- **Planner Model**: {report['planner']['model']}
- **Executor Model**: {report['executor']['model']}
- **Thinking Budget**: {report['planner']['thinking_budget']}
- **Generated At**: {report['generated_at']}
"""


def extract_summary_from_plan(plan_file: Path) -> str:
    """Extract a one-line summary from the plan file (usually the first H1)."""
    if not plan_file.exists():
        return ""
    try:
        content = plan_file.read_text(encoding="utf-8-sig")
        # Find first H1
        match = re.search(r"^#\s+(.*)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        # Fallback to first non-empty line
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("<!--") and not line.startswith("```"):
                return line[:100] # Cap length
    except:
        pass
    return plan_file.stem


def generic_native_runner(
    agent_type: str,
    default_model: str,
    default_bin: str,
    extra_cmd_args: list[str] = None
):
    import argparse
    import time
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--worktree-root", required=True, type=Path)
    parser.add_argument("--model", default=default_model)
    parser.add_argument("--bin", default=default_bin)
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--thinking-budget", choices=["none", "low", "medium", "high"], default="none")
    parser.add_argument("--task-summary", default="")
    args, unknown = parser.parse_known_args()

    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ')}_{slugify(args.plan_file.stem)}"
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 0. Resolve task summary
    task_summary = args.task_summary or extract_summary_from_plan(args.plan_file)

    # 1. Setup Environment
    branch, worktree, repo = create_isolated_worktree(Path.cwd(), run_id, args.worktree_root)
    
    status = {"run_id": run_id, "state": "running", "started_at": utc_now()}
    write_json_safe(run_dir / "status.json", status)

    # Write initial metadata so dashboard shows it immediately
    meta = {
        "task_summary": task_summary,
        "isolation": {"branch_name": branch},
        "cost_estimate": {"model": args.model, "total_usd": 0.0}
    }
    write_json_safe(run_dir / "metadata.json", meta)

    # 2. Execute Native Command
    plan_text = args.plan_file.read_text(encoding="utf-8-sig")
    
    import shlex
    
    # ... remaining logic ...
    
    # Split the binary if it contains spaces (like "gh copilot")
    if os.name == 'nt':
        # Simple split for Windows, shlex.split can be weird with backslashes
        bin_parts = args.bin.split(' ')
    else:
        bin_parts = shlex.split(args.bin)

    resolved_bin = shutil.which(bin_parts[0])
    if resolved_bin:
        bin_parts[0] = resolved_bin

    cmd = bin_parts
    if extra_cmd_args:
        # Template replacement for common variables
        for arg in extra_cmd_args:
            arg = arg.replace("{model}", args.model)
            arg = arg.replace("{plan_text}", plan_text)
            arg = arg.replace("{plan_file}", str(args.plan_file.resolve()))
            arg = arg.replace("{thinking_budget}", args.thinking_budget)
            cmd.append(arg)
    else:
        # Default simple pattern
        cmd.extend(["-p", plan_text, "-m", args.model])
    
    with open(run_dir / "stdout.log", "w", encoding="utf-8") as out, \
         open(run_dir / "stderr.log", "w", encoding="utf-8") as err:
        # No shell=True, more secure and robust for long prompts
        proc = subprocess.run(cmd, cwd=str(worktree), stdout=out, stderr=err, text=True)

    # 3. Finalize
    status["state"] = "succeeded" if proc.returncode == 0 else "failed"
    status["ended_at"] = utc_now()
    write_json_safe(run_dir / "status.json", status)
    
    meta = {
        "task_summary": task_summary,
        "isolation": {"branch_name": branch},
        "cost_estimate": {"model": args.model, "total_usd": 0.0}
    }
    write_json_safe(run_dir / "metadata.json", meta)

    if not args.no_cleanup:
        cleanup_worktree(repo, worktree, branch, keep_branch=(status["state"] == "succeeded"))

    print(f"Run directory: {run_dir}")
    return proc.returncode
