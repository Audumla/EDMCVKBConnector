"""
run_copilot_plan.py - Native Copilot CLI runner.
"""
from pathlib import Path
import sys

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import generic_native_runner

def main():
    return generic_native_runner(
        agent_type="copilot",
        default_model="gpt-4o",
        default_bin="gh copilot",
        extra_cmd_args=["explain", "{plan_text}"] # Simple example for copilot
    )

if __name__ == "__main__":
    sys.exit(main())
