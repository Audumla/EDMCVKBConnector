#!/usr/bin/env python3
"""Workspace wrapper — view and kill active agents and local LLM servers.

Auto-resolves the runtime from .vscode/agent-system.json.

Usage:
  python agent_runner/scripts/manage.py status
  python agent_runner/scripts/manage.py kill agent <run_id_or_pid>
  python agent_runner/scripts/manage.py kill llm [--runner llamacpp|llama-swap|ollama|lmstudio]
  python agent_runner/scripts/manage.py kill model <model_id>
  python agent_runner/scripts/manage.py kill all
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
    manage = str(rt / "agent_system" / "core" / "tools" / "manage.py")
    cmd = [cfg["venvPython"], manage, "--workspace", str(_ws)] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)
