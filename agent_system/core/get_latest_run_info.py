"""
get_latest_run_info.py - Helper to find the latest successful agent run branch or list recent runs.
"""
import argparse
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_runner_utils import get_all_runs, AGENT_TYPES, PROJECT_ROOT

def main():
    parser = argparse.ArgumentParser(description="Query agent run information.")
    parser.add_argument("--agent", choices=AGENT_TYPES, help="Filter by specific agent")
    parser.add_argument("--run-id", help="Target a specific Run ID")
    parser.add_argument("--list", action="store_true", help="List the last 10 successful runs")
    parser.add_argument("--limit", type=int, default=10, help="Limit for listing (default: 10)")
    args = parser.parse_args()

    if args.list:
        runs = get_all_runs(limit=args.limit, state_filter="succeeded")
        if args.agent:
            runs = [r for r in runs if r["agent"] == args.agent]
            
        if not runs:
            print("No successful runs found.")
            return

        print(f"{'AGENT':<10} | {'TASK SUMMARY':<40} | {'RUN ID'}")
        print("-" * 80)
        for run in runs:
            summary = (run["summary"][:37] + "..") if len(run["summary"]) > 37 else run["summary"]
            print(f"{run['agent']:<10} | {summary:<40} | {run['id']}")
        return

    # If run_id is provided, look for it specifically
    if args.run_id:
        runs = get_all_runs(limit=100) # search broader
        target = next((r for r in runs if r["id"] == args.run_id), None)
        if target and target["branch"]:
            print(target["branch"])
        return

    # Default: find latest successful
    runs = get_all_runs(limit=1, state_filter="succeeded")
    if args.agent:
        # We need to search specifically for this agent if the global latest isn't it
        runs = [r for r in get_all_runs(limit=50, state_filter="succeeded") if r["agent"] == args.agent][:1]
        
    if runs and runs[0]["branch"]:
        print(runs[0]["branch"])

if __name__ == "__main__":
    main()
