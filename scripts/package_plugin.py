"""
Package EDMC VKB Connector plugin into a distributable ZIP.

Creates: dist/EDMCVKBConnector-<version>.zip
Contents are rooted inside an EDMCVKBConnector/ folder so the user
can extract directly into EDMC's plugins directory.

Usage:
    python scripts/package_plugin.py
"""

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
    "data/rules.json.example",
    "data/signals_catalog.json",
    "data/icon_map.json",
    "src/edmcruleengine/__init__.py",
    "src/edmcruleengine/version.py",
    "src/edmcruleengine/config.py",
    "src/edmcruleengine/event_handler.py",
    "src/edmcruleengine/event_recorder.py",
    "src/edmcruleengine/message_formatter.py",
    "src/edmcruleengine/paths.py",
    "src/edmcruleengine/prefs_panel.py",
    "src/edmcruleengine/rule_editor.py",
    "src/edmcruleengine/rule_loader.py",
    "src/edmcruleengine/rules_engine.py",
    "src/edmcruleengine/signal_derivation.py",
    "src/edmcruleengine/signals_catalog.py",
    "src/edmcruleengine/ui_components.py",
    "src/edmcruleengine/unregistered_events_tracker.py",
    "src/edmcruleengine/vkb_client.py",
]


def archive_relpath(rel: str) -> str:
    """Map source-tree paths to deployment layout paths inside the zip."""
    if rel.startswith("src/edmcruleengine/"):
        return rel.replace("src/edmcruleengine/", f"{DEPLOY_PACKAGE_DIR}/", 1)
    return rel


def get_version() -> str:
    """Load version from the single-source version module."""
    namespace: dict[str, str] = {}
    version_file = PROJECT_ROOT / "src" / "edmcruleengine" / "version.py"
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return str(namespace.get("__version__", "0.0.0"))


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

        # Include rules.json for out-of-the-box usability.
        # Prefers user-provided file, otherwise falls back to the example.
        rules = PROJECT_ROOT / "rules.json"
        if rules.exists():
            zf.write(rules, f"{PLUGIN_NAME}/rules.json")
            print(f"  + {PLUGIN_NAME}/rules.json")
            count += 1
        else:
            rules_example = PROJECT_ROOT / "data" / "rules.json.example"
            if rules_example.exists():
                zf.write(rules_example, f"{PLUGIN_NAME}/rules.json")
                print(f"  + {PLUGIN_NAME}/rules.json (from rules.json.example)")
                count += 1

        # Include release notes if they have been generated
        release_notes = DIST_DIR / "RELEASE_NOTES.md"
        if release_notes.exists():
            zf.write(release_notes, f"{PLUGIN_NAME}/RELEASE_NOTES.md")
            print(f"  + {PLUGIN_NAME}/RELEASE_NOTES.md")
            count += 1

    print(f"\nPackaged {count} files -> {zip_path} ({zip_path.stat().st_size:,} bytes)")
    return zip_path


if __name__ == "__main__":
    package()

