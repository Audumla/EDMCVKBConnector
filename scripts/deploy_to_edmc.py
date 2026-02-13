"""Deploy this plugin into a sibling EDMarketConnector clone for local development.

Default target:
    ../EDMarketConnector/plugins/EDMCVKBConnector

Usage:
    python scripts/deploy_to_edmc.py
    python scripts/deploy_to_edmc.py --edmc-root ../EDMarketConnector
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EDMC_ROOT = (PROJECT_ROOT.parent / "EDMarketConnector").resolve()
PLUGIN_NAME = "EDMCVKBConnector"
DEPLOY_PACKAGE_DIR = "edmcruleengine"

INCLUDE = [
    "load.py",
    "PLUGIN_REGISTRY.py",
    "LICENSE",
    "README.md",
    "rules.json.example",
    "config.json.example",
    "src/edmcruleengine/__init__.py",
    "src/edmcruleengine/config.py",
    "src/edmcruleengine/event_handler.py",
    "src/edmcruleengine/message_formatter.py",
    "src/edmcruleengine/rules_engine.py",
    "src/edmcruleengine/vkb_client.py",
]


def deploy_relpath(rel: str) -> str:
    """Map source-tree paths to deployment layout paths."""
    if rel.startswith("src/edmcruleengine/"):
        return rel.replace("src/edmcruleengine/", f"{DEPLOY_PACKAGE_DIR}/", 1)
    return rel


def deploy(edmc_root: Path) -> Path:
    if not edmc_root.exists():
        raise FileNotFoundError(f"EDMC root not found: {edmc_root}")

    plugins_dir = edmc_root / "plugins"
    if not plugins_dir.exists():
        raise FileNotFoundError(f"EDMC plugins directory not found: {plugins_dir}")

    dest = plugins_dir / PLUGIN_NAME
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    copied = 0
    for rel in INCLUDE:
        src = PROJECT_ROOT / rel
        if not src.exists():
            print(f"[WARN] Missing: {rel}")
            continue

        target = dest / deploy_relpath(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied += 1
        print(f"  + {target.relative_to(dest)}")

    rules_src = PROJECT_ROOT / "rules.json"
    if rules_src.exists():
        shutil.copy2(rules_src, dest / "rules.json")
        copied += 1
        print("  + rules.json")
    else:
        shutil.copy2(PROJECT_ROOT / "rules.json.example", dest / "rules.json")
        copied += 1
        print("  + rules.json (from rules.json.example)")

    config_src = PROJECT_ROOT / "config.json"
    if config_src.exists():
        shutil.copy2(config_src, dest / "config.json")
        copied += 1
        print("  + config.json")
    else:
        shutil.copy2(PROJECT_ROOT / "config.json.example", dest / "config.json")
        copied += 1
        print("  + config.json (from config.json.example)")

    print(f"\nDeployed {copied} files to: {dest}")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy plugin into EDMC source clone")
    parser.add_argument(
        "--edmc-root",
        default=str(DEFAULT_EDMC_ROOT),
        help="Path to EDMarketConnector clone root",
    )
    args = parser.parse_args()

    deploy(Path(args.edmc_root).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

