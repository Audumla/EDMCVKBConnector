"""
runtime_paths.py - Central path resolution for runtime repo vs target workspace.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


def _discover_workspace_root() -> Path:
    env_workspace = os.environ.get("AGENT_WORKSPACE_ROOT", "").strip()
    if env_workspace:
        return Path(env_workspace).expanduser().resolve()
    return Path.cwd().resolve()


def _workspace_key(workspace_root: Path) -> str:
    stable = str(workspace_root).lower().encode("utf-8")
    digest = hashlib.sha1(stable).hexdigest()[:10]
    return f"{workspace_root.name}-{digest}"


RUNTIME_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = _discover_workspace_root()
STATE_HOME = Path(os.environ.get("AGENT_STATE_HOME", str(Path.home() / ".agent-system"))).expanduser().resolve()
WORKSPACE_ID = _workspace_key(WORKSPACE_ROOT)
STATE_ROOT = STATE_HOME / "workspaces" / WORKSPACE_ID
ARTIFACTS_ROOT = STATE_ROOT / "agent_artifacts"

