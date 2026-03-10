#!/usr/bin/env python3
"""Workspace wrapper — runs the AgentRunner project-separation lint check.

Usage:
  python agent_runner/scripts/check_sep.py            # report only
  python agent_runner/scripts/check_sep.py --strict   # exit 1 on violations
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
    rt = Path(cfg["runtimeDir"])
    check_sep = str(rt / "agent_system" / "core" / "tools" / "check_separation.py")
    env = {**os.environ, "AGENT_WORKSPACE_ROOT": str(ws)}
    extra = sys.argv[1:] if sys.argv[1:] else ["--workspace", str(ws)]
    result = subprocess.run([cfg["venvPython"], check_sep] + extra, env=env)
    sys.exit(result.returncode)
