"""
Central path constants for plugin-bundled data files.

All plugin data files live under a single subdirectory within the plugin root.
This module is the single source of truth for that subdirectory name so that
``plugin_dir / PLUGIN_DATA_DIR / filename`` is the only pattern used anywhere
in the codebase.
"""

from pathlib import Path

# Subdirectory within plugin_dir (and project root) that holds bundled data files.
PLUGIN_DATA_DIR = "data"


def data_path(plugin_dir: "str | Path", filename: str) -> Path:
    """Return the absolute path to a bundled data file.

    Args:
        plugin_dir: The plugin root directory (equiv. project root in dev).
        filename:   Filename inside the data subdirectory.

    Returns:
        ``Path(plugin_dir) / PLUGIN_DATA_DIR / filename``
    """
    return Path(plugin_dir) / PLUGIN_DATA_DIR / filename
