"""
run_claude_plan.py - Native Claude CLI runner.
"""
from pathlib import Path
import sys

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import generic_native_runner

def main():
    return generic_native_runner(
        agent_type="claude",
        default_model="claude-3-5-sonnet",
        default_bin="claude",
        extra_cmd_args=["-p", "{plan_text}", "-m", "{model}"]
    )

if __name__ == "__main__":
    sys.exit(main())
