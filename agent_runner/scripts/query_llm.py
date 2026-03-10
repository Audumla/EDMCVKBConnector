#!/usr/bin/env python3
"""Workspace wrapper — makes a one-shot query to the configured local LLM.

Auto-resolves the runtime from .vscode/agent-system.json.

Usage:
  python agent_runner/scripts/query_llm.py "Summarise: ..."
  echo "long text" | python agent_runner/scripts/query_llm.py -
  python agent_runner/scripts/query_llm.py --ensure-running "hello"
  python agent_runner/scripts/query_llm.py --model qwen2.5:0.5b "hello"
  python agent_runner/scripts/query_llm.py --system "You are a reviewer." "Is this code safe?"
"""
import json, subprocess, sys
from pathlib import Path


def _load_config():
    for parent in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        cfg = parent / ".vscode" / "agent-system.json"
        if cfg.exists():
            return parent, json.loads(cfg.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        ".vscode/agent-system.json not found — run install.py install first"
    )


if __name__ == "__main__":
    _ws, cfg = _load_config()
    rt = Path(cfg["runtimeDir"])
    query = str(rt / "agent_system" / "core" / "llm" / "query_llm.py")
    cmd = [cfg["venvPython"], query, "--workspace", str(_ws)] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)
