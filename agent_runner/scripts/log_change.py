#!/usr/bin/env python3
"""Workspace wrapper — delegates to AgentRunner log_change.py with auto-resolved paths.

Usage:
  python agent_runner/scripts/log_change.py \
    --agent <name> --group <slug> --tags "<tag>" \
    --summary "<sentence>" --details "<bullet>" "<bullet>"
"""
import json, os, subprocess, sys
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
    ws, cfg = _load_config()
    env = {**os.environ, "AGENT_WORKSPACE_ROOT": str(ws)}
    result = subprocess.run(
        [cfg["venvPython"], cfg["logChangeScript"]] + sys.argv[1:],
        env=env,
    )
    sys.exit(result.returncode)
