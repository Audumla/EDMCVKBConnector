"""
agent_maintenance.py - Audit and cleanup of orphaned agent resources.
"""
import subprocess
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_TYPES = ["codex", "gemini", "claude", "opencode", "copilot"]

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
        path = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs"
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

def main():
    print("🔍 Auditing Agent Resources...")
    brs, reps = get_orphans()
    
    if brs:
        print("\n⚠️  Dangling Branches (No Report Folder):")
        for b in brs: print(f"  - {b}")
        
    if reps:
        print("\n⚠️  Dangling Reports (No Git Branch):")
        for r in reps: print(f"  - {r.name}")
        
    if not brs and not reps:
        print("\n✅ Everything is clean. No orphans found.")
    else:
        ans = input("\nWould you like to purge these orphans? (y/N): ")
        if ans.lower() == 'y':
            for b in brs: 
                subprocess.run(["git", "branch", "-D", b], cwd=str(PROJECT_ROOT))
            for r in reps:
                shutil.rmtree(r, ignore_errors=True)
            print("🔥 Orphans purged.")

if __name__ == "__main__":
    main()
