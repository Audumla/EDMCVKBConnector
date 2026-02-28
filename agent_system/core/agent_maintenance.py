"""
agent_maintenance.py - Audit and cleanup of orphaned agent resources.
"""
import argparse
import subprocess
import json
import shutil
import sys
from pathlib import Path
from agent_runner_utils import AGENT_TYPES
from runtime_paths import WORKSPACE_ROOT, ARTIFACTS_ROOT

PROJECT_ROOT = WORKSPACE_ROOT

def run_git(args):
    res = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return res.stdout.strip().splitlines()

def get_orphans():
    # 1. Get all agent-prefixed branches
    all_branches = run_git(["branch", "--list", "*plan-runs*"])
    branches = [b.strip().replace("* ", "") for b in all_branches]
    
    # 2. Get all report folders
    report_folders = []
    for agent in AGENT_TYPES:
        path = ARTIFACTS_ROOT / agent / "reports" / "plan_runs"
        if path.exists():
            report_folders.extend(list(path.iterdir()))
            
    # 3. Cross-check
    orphaned_branches = []
    for br in branches:
        run_id = br.split("/")[-1]
        found = any(f.name == run_id for f in report_folders)
        if not found:
            orphaned_branches.append(br)
            
    orphaned_reports = []
    for folder in report_folders:
        meta_file = folder / "metadata.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8-sig"))
                br_name = meta.get("isolation", {}).get("branch_name")
                if br_name and br_name not in branches:
                    orphaned_reports.append(folder)
            except: orphaned_reports.append(folder)
        else: orphaned_reports.append(folder)

    return orphaned_branches, orphaned_reports

def purge_all_temps():
    print("[cleanup] Purging all temporary agent artifacts and worktrees...")
    subprocess.run(["git", "worktree", "prune"], cwd=str(PROJECT_ROOT))
    for agent in AGENT_TYPES:
        temp_dir = ARTIFACTS_ROOT / agent / "temp"
        if temp_dir.exists():
            print(f"  - Cleaning {temp_dir}...")
            # 1. Clean worktrees
            shutil.rmtree(temp_dir / "worktrees", ignore_errors=True)
            (temp_dir / "worktrees").mkdir(parents=True, exist_ok=True)
            
            # 2. Clean hanging plans and dispatch files
            for f in temp_dir.glob("*.md"):
                try: f.unlink()
                except: pass
            for f in temp_dir.glob("dispatch_*.md"):
                try: f.unlink()
                except: pass
    print("[cleanup] Temporary files purged.")

def main():
    parser = argparse.ArgumentParser(description="Agent resource maintenance and audit.")
    parser.add_argument("--purge-all", action="store_true", help="Forcefully purge all temporary files and worktrees.")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts.")
    args = parser.parse_args()

    if args.purge_all:
        purge_all_temps()
        return

    print("[audit] Auditing Agent Resources...")
    brs, reps = get_orphans()
    
    if brs:
        print("\n[warn] Dangling Branches (No Report Folder):")
        for b in brs: print(f"  - {b}")
        
    if reps:
        print("\n[warn] Dangling Reports (No Git Branch):")
        for r in reps: print(f"  - {r.name}")
        
    if not brs and not reps:
        print("\n[ok] Everything is clean. No orphans found.")
    else:
        if args.yes:
            ans = 'y'
        else:
            ans = input("\nWould you like to purge these orphans? (y/N): ")
            
        if ans.lower() == 'y':
            for b in brs: 
                subprocess.run(["git", "branch", "-D", b], cwd=str(PROJECT_ROOT))
            for r in reps:
                shutil.rmtree(r, ignore_errors=True)
            subprocess.run(["git", "worktree", "prune"], cwd=str(PROJECT_ROOT))
            print("[cleanup] Orphans purged.")

if __name__ == "__main__":
    main()
