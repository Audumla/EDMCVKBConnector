"""Development path configuration for local EDMC workflows.

Config precedence (highest to lowest):
1) Explicit CLI argument passed by a script
2) Environment variable override
3) Value from dev_paths.json
4) Repo-local default
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EDMC_ROOT = (PROJECT_ROOT.parent / "EDMarketConnector").resolve()

ENV_MAP = {
    "edmc_root": "EDMC_DEV_ROOT",
    "plugin_dir": "EDMC_PLUGIN_DIR",
    "python_exec": "EDMC_DEV_PYTHON",
    "venv_dir": "EDMC_DEV_VENV",
}


def default_python() -> Path:
    if os.name == "nt":
        candidate = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = PROJECT_ROOT / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else Path(sys.executable)


def load_dev_config(config_file: Path) -> Dict[str, Any]:
    if not config_file.exists():
        return {}

    with config_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {config_file}, found {type(data).__name__}")

    return data


def resolve_path(key: str, config_data: Dict[str, Any], fallback: Path) -> Path:
    env_name = ENV_MAP.get(key)
    if env_name:
        env_value = os.environ.get(env_name)
        if env_value:
            return Path(env_value).expanduser().resolve()

    config_value = config_data.get(key)
    if config_value:
        return Path(str(config_value)).expanduser().resolve()

    return fallback.resolve()
