"""Run EDMarketConnector GUI from local EDMC (DEV) repository.

Default EDMC (DEV) path:
    ../EDMarketConnector

This script launches `EDMarketConnector.py` from the EDMC (DEV) root.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EDMC_ROOT = (PROJECT_ROOT.parent / "EDMarketConnector").resolve()


def default_python() -> Path:
    if os.name == "nt":
        candidate = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = PROJECT_ROOT / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else Path(sys.executable)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EDMC GUI from local EDMC (DEV) repository")
    parser.add_argument(
        "--edmc-root",
        default=str(DEFAULT_EDMC_ROOT),
        help="Path to EDMC (DEV) repository root",
    )
    parser.add_argument(
        "--python",
        dest="python_exec",
        default=str(default_python()),
        help="Python executable to use for launch",
    )
    parser.add_argument(
        "--no-ensure-deps",
        action="store_true",
        help="Skip automatic EDMC dependency install check",
    )
    parser.add_argument(
        "edmc_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to EDMarketConnector.py (prefix with --)",
    )
    return parser.parse_args()


def has_module(python_exec: Path, module_name: str) -> bool:
    result = subprocess.run(
        [str(python_exec), "-c", f"import {module_name}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def ensure_edmc_deps(python_exec: Path, edmc_root: Path) -> bool:
    requirements = edmc_root / "requirements.txt"
    if not requirements.exists():
        print(f"[WARN] EDMC requirements.txt not found at {requirements}; skipping dependency install")
        return True

    # `semantic_version` is an EDMC import that fails early when deps are missing.
    if has_module(python_exec, "semantic_version"):
        return True

    print(f"[INFO] Installing EDMC dependencies from {requirements}")
    result = subprocess.run(
        [str(python_exec), "-m", "pip", "install", "-r", str(requirements)],
        cwd=str(edmc_root),
        check=False,
    )
    if result.returncode != 0:
        print("[FAIL] Could not install EDMC dependencies")
        return False

    if not has_module(python_exec, "semantic_version"):
        print("[FAIL] EDMC dependency check still failing after install")
        return False

    return True


def main() -> int:
    args = parse_args()
    edmc_root = Path(args.edmc_root).resolve()
    python_exec = Path(args.python_exec).resolve()
    entrypoint = edmc_root / "EDMarketConnector.py"

    if not edmc_root.exists() or not (edmc_root / ".git").exists():
        print(f"[FAIL] EDMC (DEV) repo not found at: {edmc_root}")
        print("       Run bootstrap first: python scripts/bootstrap_dev_env.py")
        return 1
    if not entrypoint.exists():
        print(f"[FAIL] EDMC entrypoint not found: {entrypoint}")
        return 1
    if not python_exec.exists():
        print(f"[FAIL] Python executable not found: {python_exec}")
        return 1
    if not args.no_ensure_deps and not ensure_edmc_deps(python_exec, edmc_root):
        return 1

    forwarded = args.edmc_args
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    cmd = [str(python_exec), str(entrypoint), *forwarded]
    print(f"[RUN] ({edmc_root}) {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(edmc_root), check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
