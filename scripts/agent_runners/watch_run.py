"""
watch_run.py - Live progress monitor for Agent Runner plan executions.
Displays the state, heartbeats, and live stdout from a background run.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_TYPES = ["codex", "gemini", "claude"]

def find_latest_run_dir() -> Path | None:
    all_runs = []
    for agent in AGENT_TYPES:
        output_root = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs"
        if output_root.exists():
            all_runs.extend([p for p in output_root.iterdir() if p.is_dir()])
    
    if not all_runs:
        return None
        
    all_runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return all_runs[0]

def main():
    parser = argparse.ArgumentParser(description="Watch a Codex/Agent plan run in real-time.")
    parser.add_argument("--run-dir", type=Path, help="Specific run directory to watch.")
    parser.add_argument("--interval", type=float, default=1.0, help="Refresh interval in seconds.")
    args = parser.parse_args()

    run_dir = args.run_dir or find_latest_run_dir()
    if not run_dir:
        print("No run directory found.")
        return

    status_file = run_dir / "status.json"
    stdout_file = run_dir / "stdout.log"
    
    # Pre-check if finished
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text(encoding="utf-8"))
            state = status.get("state", "unknown")
            if state in ("succeeded", "failed", "cancelled", "dry_run"):
                print(f"Run {run_dir.name} is already finished ({state.upper()}).")
                # Still show the logs once
                if stdout_file.exists():
                    print("\n--- Final Logs ---")
                    print(stdout_file.read_text(encoding="utf-8", errors="replace"))
                return
        except:
            pass

    print(f"Watching run: {run_dir.name}")
    print(f"Status file: {status_file}")
    print("-" * 60)

    last_pos = 0
    try:
        while True:
            # Check Status
            if status_file.exists():
                try:
                    status = json.loads(status_file.read_text(encoding="utf-8"))
                    state = status.get("state", "unknown")
                    heartbeat = status.get("heartbeat_at", "n/a")
                    print(f"\r[STATUS] State: {state.upper()} | Heartbeat: {heartbeat}", end="", flush=True)
                    
                    if state in ("succeeded", "failed", "cancelled", "dry_run"):
                        print(f"\nRun finished with state: {state.upper()}")
                        if state == "succeeded":
                            metadata_file = run_dir / "metadata.json"
                            if metadata_file.exists():
                                meta = json.loads(metadata_file.read_text(encoding="utf-8"))
                                branch = meta.get("isolation", {}).get("branch_name")
                                if branch:
                                    print(f"\n[MERGE] To apply these changes, run:")
                                    print(f"git merge {branch}")
                        break
                except:
                    pass
            
            # Check Stdout
            if stdout_file.exists():
                with stdout_file.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(last_pos)
                    chunk = f.read()
                    if chunk:
                        if last_pos == 0:
                            print("\n--- Live Logs ---")
                        print(chunk, end="", flush=True)
                        last_pos = f.tell()
            
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped watching. (Run continues in background)")

if __name__ == "__main__":
    main()
