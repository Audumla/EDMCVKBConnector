"""
run_localllm_plan.py - API-based Local LLM runner.
"""
import argparse
import sys
import json
import time
import requests
from pathlib import Path

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import (
    utc_now, slugify, write_json_safe, 
    create_isolated_worktree, cleanup_worktree,
    extract_summary_from_plan
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--worktree-root", required=True, type=Path)
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--bin", default="local-llm") # Ignored for API or used as URL
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--task-summary", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ')}_{slugify(args.plan_file.stem)}"
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load local settings
    endpoint = "http://localhost:11434/v1"
    
    # 1. Check if --bin is a URL
    if args.bin and (args.bin.startswith("http://") or args.bin.startswith("https://")):
        endpoint = args.bin
    else:
        # 2. Check .local-llm/settings.json
        config_path = Path(__file__).resolve().parent.parent / "config" / ".local-llm" / "settings.json"
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                endpoint = cfg.get("endpoint", endpoint)
            except: pass

        # 3. Fallback to changelog-config.json
        if endpoint == "http://localhost:11434/v1":
            changelog_config_path = Path(__file__).resolve().parent.parent / "reporting" / "changelog-config.json"
            if changelog_config_path.exists():
                try:
                    cl_cfg = json.loads(changelog_config_path.read_text(encoding="utf-8"))
                    endpoint = cl_cfg.get("changelog_summarization", {}).get("local_llm", {}).get("base_url", endpoint)
                except: pass

    # 1. Setup Environment
    branch, worktree, repo = create_isolated_worktree(Path.cwd(), run_id, args.worktree_root)
    
    status = {
        "run_id": run_id, 
        "state": "running", 
        "started_at": utc_now(),
        "pid": os.getpid() # Capture PID
    }
    write_json_safe(run_dir / "status.json", status)

    # Resolve task summary
    task_summary = args.task_summary or extract_summary_from_plan(args.plan_file)

    # Write initial metadata
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

    if args.dry_run:
        status["state"] = "dry_run"
        status["ended_at"] = utc_now()
        write_json_safe(run_dir / "status.json", status)
        print(f"Dry run created: {run_dir}")
        return 0

    # 2. Execute API Call
    # Robust encoding detection for plan file
    try:
        plan_text = args.plan_file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try: plan_text = args.plan_file.read_text(encoding="utf-16")
        except UnicodeDecodeError: plan_text = args.plan_file.read_text(encoding="latin-1")
    
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
                        except: pass
            
        status["state"] = "succeeded"
        returncode = 0
        
    except Exception as e:
        error_msg = f"API Error: {str(e)}"
        print(f"[local-llm] ERROR: {error_msg}")
        with open(run_dir / "stderr.log", "w", encoding="utf-8") as err:
            err.write(error_msg)
        status["state"] = "failed"
        returncode = 1

    # 3. Finalize
    status["ended_at"] = utc_now()
    write_json_safe(run_dir / "status.json", status)
    
    if not args.no_cleanup:
        cleanup_worktree(repo, worktree, branch, keep_branch=(status["state"] == "succeeded"))

    print(f"Run directory: {run_dir}")
    return returncode

if __name__ == "__main__":
    sys.exit(main())
