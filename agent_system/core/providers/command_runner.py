"""Shared command/template helpers for provider usage callers."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def resolve_command(template: list[str], provider: str, provider_bin: str | None = None) -> list[str]:
    bin_value = (provider_bin or provider).strip()
    binary = bin_value.split(" ")[0] if bin_value else provider
    resolved_bin = shutil.which(binary) or binary
    return [
        str(part).replace("{bin}", resolved_bin).replace("{provider}", provider)
        for part in template
    ]


def run_command(cmd: list[str], timeout_sec: int = 10) -> subprocess.CompletedProcess[str]:
    # On Windows, .cmd/.bat entries from npm are safest through cmd /c in non-shell subprocess mode.
    if cmd and cmd[0].lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c", *cmd]
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        # Fallback when a previously-resolved absolute executable path disappears.
        if not cmd:
            raise
        exe = cmd[0]
        if "\\" not in exe and "/" not in exe:
            raise
        fallback_name = Path(exe).name
        fallback_cmd = [fallback_name, *cmd[1:]]
        return subprocess.run(
            fallback_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )


def usage_timeout(usage_cfg: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(usage_cfg.get(key, default))
    except (TypeError, ValueError):
        return default
