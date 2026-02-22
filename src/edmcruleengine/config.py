"""
Configuration management for EDMC VKB Connector.

Uses EDMC's standard configuration API for storing plugin preferences.
Configuration is persisted by EDMC in the system-appropriate location
(registry on Windows, plist on macOS, etc.).
"""

import json
from pathlib import Path
from typing import Any

from . import plugin_logger

try:
    from config import config
except Exception:
    # Fallback for local testing without EDMC
    config = None

logger = plugin_logger(__name__)

# Configuration key prefix to namespace plugin settings
CONFIG_PREFIX = "VKBConnector_"

DEFAULTS_FILE_NAME = "config_defaults.json"

# Fallback defaults used if the external defaults file cannot be read.
_FALLBACK_DEFAULTS = {
    "vkb_host": "127.0.0.1",
    "vkb_port": 50995,
    "socket_timeout": 5,
    "enabled": True,
    "debug": False,
    "rules_path": "",
    "vkb_header_byte": 0xA5,
    "vkb_command_byte": 13,
    "test_shift_bitmap": 0,
    "test_subshift_bitmap": 0,
    "vkb_ini_path": "",
    "vkb_link_exe_path": "",
    "vkb_link_install_dir": "",
    "vkb_link_version": "",
    "vkb_link_managed": False,
    "vkb_link_auto_manage": True,
    "vkb_link_auto_install_cryptography": False,
    "vkb_link_restart_on_failure": True,
    "vkb_link_launch_mode": "legacy",
    # VKB-Link lifecycle timings.
    "vkb_link_warmup_delay_seconds": 5,
    "vkb_link_process_monitor_interval_seconds": 5,
    "vkb_link_probe_listener_before_connect": False,
    "vkb_link_operation_timeout_seconds": 10,
    "vkb_link_poll_interval_seconds": 0.25,
    "vkb_link_restart_delay_seconds": 0.25,
    # Preferences/UI timings.
    "vkb_ui_apply_delay_seconds": 4,
    "vkb_ui_poll_interval_seconds": 2,
    "track_unregistered_events": False,
    "recorder_mock_commander": "CMDR",
    "recorder_mock_fid": "F0000000",
}


def _load_defaults_from_file() -> dict[str, Any]:
    defaults = dict(_FALLBACK_DEFAULTS)
    defaults_path = Path(__file__).resolve().with_name(DEFAULTS_FILE_NAME)
    try:
        raw = defaults_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(
            "Could not read defaults file '%s': %s; using built-in defaults",
            defaults_path,
            e,
        )
        return defaults

    try:
        loaded = json.loads(raw)
    except Exception as e:
        logger.warning(
            "Failed parsing defaults file '%s': %s; using built-in defaults",
            defaults_path,
            e,
        )
        return defaults

    if not isinstance(loaded, dict):
        logger.warning(
            "Defaults file '%s' is not a JSON object; using built-in defaults",
            defaults_path,
        )
        return defaults

    for key, value in loaded.items():
        if isinstance(key, str):
            defaults[key] = value
    return defaults


# Defaults for all configuration keys. Loaded from config_defaults.json.
DEFAULTS = _load_defaults_from_file()


class Config:
    """
    Manages configuration for VKB Connector using EDMC's config API.

    Configuration is stored in EDMC's persistent storage and can be
    managed via EDMC's settings dialog if the plugin provides a UI panel.

    For local testing without EDMC, falls back to in-memory defaults.
    """

    def __init__(self):
        """Initialize configuration (loads from EDMC's config store)."""
        pass

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key name.
            default: Default value if key not found (uses DEFAULTS if not provided).

        Returns:
            Configuration value, or default.
        """
        if default is None:
            default = DEFAULTS.get(key)

        if config is None:
            # Local testing mode: return defaults
            return default

        try:
            # Determine the type of value we're expecting based on DEFAULTS
            if key in DEFAULTS:
                expected_type = type(DEFAULTS[key])

                # Use type-specific getters for EDMC's config API
                if expected_type is str:
                    return config.get_str(f"{CONFIG_PREFIX}{key}", default)
                elif expected_type is int:
                    return config.get_int(f"{CONFIG_PREFIX}{key}", default)
                elif expected_type is bool:
                    return config.get_bool(f"{CONFIG_PREFIX}{key}", default)
                elif expected_type is list:
                    return config.get_list(f"{CONFIG_PREFIX}{key}", default)

            # Fallback for unknown types
            return default

        except Exception as e:
            logger.warning(f"Failed to retrieve config key '{key}': {e}")
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key name.
            value: Value to store.
        """
        if config is None:
            # Local testing mode: silently ignore
            logger.debug(f"Config.set({key}, {value}) called in test mode (no EDMC config)")
            return

        try:
            config.set(f"{CONFIG_PREFIX}{key}", value)
            logger.debug(f"Configuration '{key}' set to {value}")
        except Exception as e:
            logger.error(f"Failed to set config key '{key}': {e}")

    def delete(self, key: str) -> None:
        """
        Delete configuration value.

        Args:
            key: Configuration key name to delete.
        """
        if config is None:
            # Local testing mode: silently ignore
            logger.debug(f"Config.delete({key}) called in test mode (no EDMC config)")
            return

        try:
            config.delete(f"{CONFIG_PREFIX}{key}")
            logger.debug(f"Configuration '{key}' deleted")
        except Exception as e:
            logger.error(f"Failed to delete config key '{key}': {e}")

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style assignment."""
        self.set(key, value)
