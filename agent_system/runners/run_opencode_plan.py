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
        default_model="opencode-latest",
        default_bin="opencode",
        # Pass model before the positional message to avoid ambiguity
        extra_cmd_args=["run", "-m", "{model}", "{plan_text}"]
    )

if __name__ == "__main__":
    sys.exit(main())
