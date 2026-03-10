#!/usr/bin/env python3
"""Workspace wrapper — manages the AgentRunner local LLM server.

Auto-resolves the runtime from .vscode/agent-system.json.

Usage:
  python agent_runner/scripts/local_llm.py status
  python agent_runner/scripts/local_llm.py start [--runner llamacpp]
  python agent_runner/scripts/local_llm.py stop
  python agent_runner/scripts/local_llm.py configure
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
    manager = str(rt / "agent_system" / "core" / "llm" / "local_llm_manager.py")
    # Always pass --workspace so the manager can load per-project config
    cmd = [cfg["venvPython"], manager, "--workspace", str(_ws)] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)
