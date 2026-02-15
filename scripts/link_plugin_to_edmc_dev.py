"""Link this plugin into EDMC (DEV) repository plugins folder.

Default target:
    ../EDMarketConnector/plugins/EDMCVKBConnector

"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EDMC_ROOT = (PROJECT_ROOT.parent / "EDMarketConnector").resolve()
PLUGIN_NAME = "EDMCVKBConnector"


def remove_existing(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def create_windows_junction(link_path: Path, target_path: Path) -> None:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"Failed to create junction: {details}")


def create_link(link_path: Path, target_path: Path) -> str:
    try:
        os.symlink(str(target_path), str(link_path), target_is_directory=True)
        return "symlink"
    except OSError as exc:
        if os.name != "nt":
            raise RuntimeError(f"Failed to create symlink: {exc}") from exc
        create_windows_junction(link_path, target_path)
        return "junction"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Link plugin into EDMC (DEV) plugins folder")
    parser.add_argument(
        "--edmc-root",
        default=str(DEFAULT_EDMC_ROOT),
        help="Path to EDMC (DEV) repository root",
    )
    parser.add_argument(
        "--plugin-name",
        default=PLUGIN_NAME,
        help="Plugin directory name inside EDMC plugins folder",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing plugin directory/link if present",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    edmc_root = Path(args.edmc_root).resolve()
    plugins_dir = edmc_root / "plugins"

    if not edmc_root.exists() or not (edmc_root / ".git").exists():
        print(f"[FAIL] EDMC (DEV) repo not found at: {edmc_root}")
        print("       Run bootstrap first: python scripts/bootstrap_dev_env.py")
        return 1
    plugins_dir.mkdir(parents=True, exist_ok=True)

    target_path = PROJECT_ROOT.resolve()
    link_path = plugins_dir / args.plugin_name

    if link_path.exists() or link_path.is_symlink():
        if link_path.is_symlink() and link_path.resolve() == target_path:
            print(f"[OK] Link already exists: {link_path} -> {target_path}")
            return 0
        if not args.force:
            print(f"[FAIL] Path already exists: {link_path}")
            print("       Re-run with --force to replace it.")
            return 1
        print(f"[INFO] Replacing existing path: {link_path}")
        remove_existing(link_path)

    link_type = create_link(link_path, target_path)
    print(f"[SUCCESS] Created {link_type}:")
    print(f"  {link_path} -> {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
