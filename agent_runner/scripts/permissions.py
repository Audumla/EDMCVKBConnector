#!/usr/bin/env python3
"""Workspace wrapper — configure provider permission/approval behavior.

Auto-resolves the runtime from .vscode/agent-system.json.

Usage:
  python agent_runner/scripts/permissions.py                  # interactive prompts
  python agent_runner/scripts/permissions.py --mode all-on    # unattended mode
  python agent_runner/scripts/permissions.py --mode all-off   # interactive mode
  python agent_runner/scripts/permissions.py codex gemini     # subset
"""
import json, subprocess, sys
from pathlib import Path


def _load_config():
    start = Path(__file__).resolve().parent
    for parent in [start, *start.parents]:
        cfg = parent / ".vscode" / "agent-system.json"
        if cfg.exists():
            return parent, json.loads(cfg.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        ".vscode/agent-system.json not found — run install.py install first"
    )


def _resolve_installer(workspace: Path, runtime_dir: Path) -> Path:
    local = workspace / "agent_system" / "install.py"
    runtime = runtime_dir / "agent_system" / "install.py"
    if local.exists():
        return local
    if runtime.exists():
        return runtime
    raise FileNotFoundError(
        "install.py not found in workspace or configured runtime.\n"
        f"  workspace candidate: {local}\n"
        f"  runtime candidate:   {runtime}"
    )


if __name__ == "__main__":
    _ws, cfg = _load_config()
    rt = Path(cfg["runtimeDir"]).expanduser().resolve()
    installer = _resolve_installer(_ws, rt)
    py = Path(cfg.get("venvPython", sys.executable))
    if not py.exists():
        py = Path(sys.executable)
    cmd = [str(py), str(installer), "permissions", "--workspace", str(_ws), "--runtime-dir", str(rt)] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)
