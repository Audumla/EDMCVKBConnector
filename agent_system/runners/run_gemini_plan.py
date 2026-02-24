"""
run_gemini_plan.py - Native Gemini CLI runner.
"""
from pathlib import Path
import sys

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import generic_native_runner

def main():
    return generic_native_runner(
        agent_type="gemini",
        default_model="gemini-2.0-flash-exp",
        default_bin="gemini",
        extra_cmd_args=["--yolo", "-p", "{plan_text}", "-m", "{model}"]
    )

if __name__ == "__main__":
    sys.exit(main())
