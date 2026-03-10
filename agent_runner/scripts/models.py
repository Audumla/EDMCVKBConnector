#!/usr/bin/env python3
"""Workspace wrapper — manages the local LLM model catalog.

Auto-resolves the runtime from .vscode/agent-system.json.

Usage:
  python agent_runner/scripts/models.py list
  python agent_runner/scripts/models.py add
  python agent_runner/scripts/models.py download <model_id>
  python agent_runner/scripts/models.py start <model_id>
  python agent_runner/scripts/models.py stop <model_id>
  python agent_runner/scripts/models.py stop-all
  python agent_runner/scripts/models.py binary
  python agent_runner/scripts/models.py groups
  python agent_runner/scripts/models.py remove <model_id> [--delete-files]
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
    manager = str(rt / "agent_system" / "core" / "llm" / "local_llm_model_manager.py")
    sys.exit(subprocess.run([cfg["venvPython"], manager] + sys.argv[1:]).returncode)
