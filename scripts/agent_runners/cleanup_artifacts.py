"""
cleanup_artifacts.py - Forcefully clean up stale agent worktrees and temporary files.
"""

import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def run_git(args):
    return subprocess.run(["git", *args], capture_output=True, text=True)

def main():
    print("Pruning git worktrees...")
    run_git(["worktree", "prune"])
    
    agents = ["codex", "gemini", "claude", "opencode", "copilot"]
    
    for agent in agents:
        temp_dir = PROJECT_ROOT / "agent_artifacts" / agent / "temp"
        if temp_dir.exists():
            print(f"Cleaning {temp_dir}...")
            # Use rmtree to force delete everything, including stubborn worktree files
            shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir.mkdir(parents=True, exist_ok=True)
            (temp_dir / "worktrees").mkdir(exist_ok=True)
            
    print("Cleanup complete. Repository is now lean.")

if __name__ == "__main__":
    main()
