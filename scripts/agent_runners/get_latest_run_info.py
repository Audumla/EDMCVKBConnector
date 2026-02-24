"""
get_latest_run_info.py - Helper to find the latest successful agent run branch.
"""
from pathlib import Path
import json
import argparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_TYPES = ["codex", "gemini", "claude", "opencode", "copilot"]

def find_latest_success(agent_filter=None):
    all_runs = []
    agents = [agent_filter] if agent_filter else AGENT_TYPES
    
    for agent in agents:
        output_root = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs"
        if output_root.exists():
            for p in output_root.iterdir():
                status_file = p / "status.json"
                if status_file.exists():
                    try:
                        status = json.loads(status_file.read_text(encoding="utf-8"))
                        if status.get("state") == "succeeded":
                            all_runs.append(p)
                    except: pass
    
    if not all_runs: return None
    all_runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return all_runs[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=AGENT_TYPES, help="Filter by specific agent")
    parser.add_argument("--run-id", help="Target a specific Run ID")
    parser.add_argument("--list", action="store_true", help="List last 5 successful runs")
    args = parser.parse_args()

    if args.run_id and args.run_id.strip():
        # Search all agents for this specific ID
        for agent in AGENT_TYPES:
            candidate = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs" / args.run_id
            if candidate.exists():
                run_dir = candidate
                break
        else:
            return
    else:
        run_dir = find_latest_success(args.agent)
    if run_dir:
        meta_file = run_dir / "metadata.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            branch = meta.get("isolation", {}).get("branch_name")
            if branch:
                print(branch)

if __name__ == "__main__":
    main()
