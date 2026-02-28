"""
run_ollama_plan.py - Ollama local LLM runner.

Sends the plan to Ollama's OpenAI-compatible API at http://localhost:11434.
Ollama must be running (`ollama serve`) before this runner is invoked.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from agent_runner_utils import generic_api_runner


def main() -> int:
    return generic_api_runner(
        agent_type="ollama",
        default_model="qwen2.5-coder:7b",
        default_base_url="http://localhost:11434/v1",
        api_key_env=None,          # Ollama has no auth by default
        extra_description="Ollama local LLM",
    )


if __name__ == "__main__":
    sys.exit(main())
