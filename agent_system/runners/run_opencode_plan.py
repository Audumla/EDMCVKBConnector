"""
run_opencode_plan.py - Native OpenCode CLI runner.
"""
from pathlib import Path
import sys

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import generic_native_runner

def main():
    return generic_native_runner(
        agent_type="opencode",
        default_model="opencode/big-pickle",
        default_bin="opencode",
        # Explicitly pass --dir {worktree} to enforce boundaries
        extra_cmd_args=["run", "-m", "{model}", "--dir", "{worktree}", "{plan_text}"]
    )

if __name__ == "__main__":
    sys.exit(main())
