"""
run_localllm_plan.py - API-based Local LLM runner.
"""
import argparse
import sys
import json
import time
import os
import requests
from pathlib import Path

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import (
    utc_now, slugify, write_json_safe, 
    create_isolated_worktree, cleanup_worktree,
    extract_summary_from_plan
)

def _resolve_endpoint(bin_arg: str) -> str:
    endpoint = "http://localhost:11434/v1"

    if bin_arg and (bin_arg.startswith("http://") or bin_arg.startswith("https://")):
        return bin_arg

    config_path = Path(__file__).resolve().parent.parent / "config" / ".local-llm" / "settings.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            endpoint = cfg.get("endpoint", endpoint)
        except Exception:
            pass

    if endpoint == "http://localhost:11434/v1":
        changelog_config_path = Path(__file__).resolve().parent.parent / "reporting" / "changelog-config.json"
        if changelog_config_path.exists():
            try:
                cl_cfg = json.loads(changelog_config_path.read_text(encoding="utf-8"))
                endpoint = cl_cfg.get("changelog_summarization", {}).get("local_llm", {}).get("base_url", endpoint)
            except Exception:
                pass

    return endpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--worktree-root", required=True, type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--bin", default="local-llm") # May be URL for API endpoint.
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--task-summary", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan_file = args.plan_file.resolve()
    output_root = args.output_root.resolve()
    worktree_root = args.worktree_root.resolve()
    workspace = args.workspace.resolve()

    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ')}_{slugify(args.plan_file.stem)}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    endpoint = _resolve_endpoint(args.bin)
    branch = None
    worktree = None
    repo = None

    # Resolve task summary
    task_summary = args.task_summary or extract_summary_from_plan(args.plan_file)

    if args.dry_run:
        meta = {
            "task_summary": task_summary,
            "isolation": {"branch_name": None},
            "cost_estimate": {
                "model": args.model,
                "total_usd": 0.0,
                "note": "Cost estimation not available for local runner dry run",
            },
        }
        status = {
            "run_id": run_id,
            "state": "dry_run",
            "started_at": utc_now(),
            "ended_at": utc_now(),
            "pid": None,
        }
        write_json_safe(run_dir / "metadata.json", meta)
        write_json_safe(run_dir / "status.json", status)
        print(f"Dry run created: {run_dir}")
        return 0

    # 1. Setup isolated execution environment
    branch, worktree, repo = create_isolated_worktree(workspace, run_id, worktree_root)

    status = {
        "run_id": run_id,
        "state": "running",
        "started_at": utc_now(),
        "pid": os.getpid(),
    }
    write_json_safe(run_dir / "status.json", status)

    meta = {
        "task_summary": task_summary,
        "isolation": {"branch_name": branch},
        "cost_estimate": {
            "model": args.model,
            "total_usd": 0.0,
            "note": "Cost estimation not available for native runner"
        }
    }
    write_json_safe(run_dir / "metadata.json", meta)

    # 2. Execute API Call
    # Robust encoding detection for plan file
    try:
        plan_text = plan_file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            plan_text = plan_file.read_text(encoding="utf-16")
        except UnicodeDecodeError:
            plan_text = plan_file.read_text(encoding="latin-1")

    returncode = 1
    try:
        url = f"{endpoint.rstrip('/')}/chat/completions"
        payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": plan_text}],
            "temperature": 0.0,
            "stream": True
        }
        
        print(f"[local-llm] Sending streaming request to {url}...")
        response = requests.post(url, json=payload, timeout=300, stream=True)
        response.raise_for_status()
        
        with open(run_dir / "stdout.log", "w", encoding="utf-8") as out:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith("data: "):
                        data_str = line_text[6:].strip()
                        if data_str == "[DONE]": break
                        try:
                            chunk = json.loads(data_str)
                            content = chunk['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                out.write(content)
                                out.flush()
                        except Exception:
                            pass

        status["state"] = "succeeded"
        returncode = 0

    except Exception as e:
        error_msg = f"API Error: {str(e)}"
        print(f"[local-llm] ERROR: {error_msg}")
        with open(run_dir / "stderr.log", "w", encoding="utf-8") as err:
            err.write(error_msg)
        status["state"] = "failed"

    # 3. Finalize
    status["ended_at"] = utc_now()
    write_json_safe(run_dir / "status.json", status)

    if (not args.no_cleanup) and repo is not None and worktree is not None and branch is not None:
        cleanup_worktree(repo, worktree, branch, keep_branch=(status["state"] == "succeeded"))

    print(f"Run directory: {run_dir}")
    return returncode

if __name__ == "__main__":
    sys.exit(main())
