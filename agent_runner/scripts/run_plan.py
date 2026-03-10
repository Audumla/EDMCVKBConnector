#!/usr/bin/env python3
"""Workspace wrapper — delegates agent work via AgentRunner run_agent_plan.py.

Usage:
  python agent_runner/scripts/run_plan.py \
    --planner <name> --executor <name> \
    --plan-file agent_runner/artifacts/<planner>/temp/plan.md \
    --cleanup-worktree
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
    run_plan = str(rt / "agent_system" / "core" / "run_agent_plan.py")
    env = {**os.environ, "AGENT_WORKSPACE_ROOT": str(ws)}
    result = subprocess.run([cfg["venvPython"], run_plan] + sys.argv[1:], env=env)
    sys.exit(result.returncode)
