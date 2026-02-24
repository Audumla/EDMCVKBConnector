"""
list_agent_runs.py - Lists the last 10 successful agent runs with summaries and branches.
"""
from pathlib import Path
import json
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_TYPES = ["codex", "gemini", "claude", "opencode", "copilot"]

def main():
    all_runs = []
    for agent in AGENT_TYPES:
        output_root = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs"
        if output_root.exists():
            for p in output_root.iterdir():
                status_file = p / "status.json"
                meta_file = p / "metadata.json"
                if status_file.exists() and meta_file.exists():
                    try:
                        status = json.loads(status_file.read_text(encoding="utf-8"))
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        if status.get("state") == "succeeded":
                            all_runs.append({
                                "id": p.name,
                                "agent": agent,
                                "summary": meta.get("task_summary", "n/a"),
                                "branch": meta.get("isolation", {}).get("branch_name"),
                                "time": p.stat().st_mtime
                            })
                    except: pass
    
    if not all_runs:
        print("No successful runs found.")
        return

    all_runs.sort(key=lambda x: x["time"], reverse=True)
    
    print(f"{'AGENT':<10} | {'TASK SUMMARY':<40} | {'RUN ID'}")
    print("-" * 80)
    for run in all_runs[:10]:
        summary = (run["summary"][:37] + "..") if len(run["summary"]) > 37 else run["summary"]
        print(f"{run['agent']:<10} | {summary:<40} | {run['id']}")

if __name__ == "__main__":
    main()
