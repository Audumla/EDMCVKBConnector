"""
run_localllm_plan.py - Native Local LLM CLI runner.
"""
from pathlib import Path
import sys

# Add core to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import generic_native_runner

def main():
    return generic_native_runner(
        agent_type="local-llm",
        default_model="local-model",
        default_bin="local-llm",
        extra_cmd_args=["-p", "{plan_text}", "-m", "{model}"]
    )

if __name__ == "__main__":
    sys.exit(main())
