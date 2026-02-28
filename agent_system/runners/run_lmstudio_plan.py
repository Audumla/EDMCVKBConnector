"""
run_lmstudio_plan.py - LM Studio local LLM runner.

Sends the plan to LM Studio's OpenAI-compatible API at http://localhost:1234.
LM Studio must be open with a model loaded and the local server started
(Developer tab > Start Server) before this runner is invoked.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import generic_api_runner


def main() -> int:
    return generic_api_runner(
        agent_type="lmstudio",
        default_model="local-model",
        default_base_url="http://localhost:1234/v1",
        api_key_env=None,          # LM Studio uses "lm-studio" as a dummy key
        api_key_default="lm-studio",
        extra_description="LM Studio local server",
    )


if __name__ == "__main__":
    sys.exit(main())
