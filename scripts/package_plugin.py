"""
Package EDMC VKB Connector plugin into a distributable ZIP.

Creates: dist/EDMCVKBConnector-<version>.zip
Contents are rooted inside an EDMCVKBConnector/ folder so the user
can extract directly into EDMC's plugins directory.

Usage:
    python scripts/package_plugin.py
"""

import re
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
PLUGIN_NAME = "EDMCVKBConnector"
DEPLOY_PACKAGE_DIR = "edmcruleengine"

# Files/dirs to include (relative to project root)
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


def archive_relpath(rel: str) -> str:
    """Map source-tree paths to deployment layout paths inside the zip."""
    if rel.startswith("src/edmcruleengine/"):
        return rel.replace("src/edmcruleengine/", f"{DEPLOY_PACKAGE_DIR}/", 1)
    return rel


def get_version() -> str:
    """Extract version from pyproject.toml or PLUGIN_REGISTRY.py."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if pyproject.exists():
        match = re.search(r'version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
        if match:
            return match.group(1)

    registry = PROJECT_ROOT / "PLUGIN_REGISTRY.py"
    if registry.exists():
        match = re.search(r'VERSION\s*=\s*"([^"]+)"', registry.read_text(encoding="utf-8"))
        if match:
            return match.group(1)

    return "0.0.0"


def package() -> Path:
    version = get_version()
    DIST_DIR.mkdir(exist_ok=True)

    zip_name = f"{PLUGIN_NAME}-{version}.zip"
    zip_path = DIST_DIR / zip_name

    missing = [f for f in INCLUDE if not (PROJECT_ROOT / f).exists()]
    if missing:
        print(f"WARNING: Missing files (will be skipped): {missing}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        count = 0
        for rel in INCLUDE:
            src = PROJECT_ROOT / rel
            if not src.exists():
                continue
            arcname = f"{PLUGIN_NAME}/{archive_relpath(rel)}"
            zf.write(src, arcname)
            print(f"  + {arcname}")
            count += 1

        # Include concrete rules.json/config.json for out-of-the-box usability.
        # Prefer user-provided files, otherwise fall back to the example files.
        rules = PROJECT_ROOT / "rules.json"
        if rules.exists():
            zf.write(rules, f"{PLUGIN_NAME}/rules.json")
            print(f"  + {PLUGIN_NAME}/rules.json")
            count += 1
        else:
            rules_example = PROJECT_ROOT / "rules.json.example"
            if rules_example.exists():
                zf.write(rules_example, f"{PLUGIN_NAME}/rules.json")
                print(f"  + {PLUGIN_NAME}/rules.json (from rules.json.example)")
                count += 1

        config = PROJECT_ROOT / "config.json"
        if config.exists():
            zf.write(config, f"{PLUGIN_NAME}/config.json")
            print(f"  + {PLUGIN_NAME}/config.json")
            count += 1
        else:
            config_example = PROJECT_ROOT / "config.json.example"
            if config_example.exists():
                zf.write(config_example, f"{PLUGIN_NAME}/config.json")
                print(f"  + {PLUGIN_NAME}/config.json (from config.json.example)")
                count += 1

    print(f"\nPackaged {count} files -> {zip_path} ({zip_path.stat().st_size:,} bytes)")
    return zip_path


if __name__ == "__main__":
    package()

