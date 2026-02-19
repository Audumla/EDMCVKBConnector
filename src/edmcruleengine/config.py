"""
Configuration management for EDMC VKB Connector.

Uses EDMC's standard configuration API for storing plugin preferences.
Configuration is persisted by EDMC in the system-appropriate location
(registry on Windows, plist on macOS, etc.).
"""

import logging
from typing import Any, List, Optional

from . import plugin_logger

try:
    from config import config
except Exception:
    # Fallback for local testing without EDMC
    config = None

logger = plugin_logger(__name__)

# Configuration key prefix to namespace plugin settings
CONFIG_PREFIX = "VKBConnector_"

# Defaults for all configuration keys
DEFAULTS = {
    "vkb_host": "127.0.0.1",
    "vkb_port": 50995,
    "enabled": True,
    "debug": False,
    "event_types": [
        # Journal events
        "Status", "Location", "FSDJump", "DockingGranted", "Undocked",
        "LaunchSRV", "DockSRV", "Docked", "LaunchFighter", "DockFighter",
        # CAPI events (forwarded by EDMC via cmdr_data / capi_fleetcarrier)
        "CmdrData", "CapiFleetCarrier",
    ],
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
    "vkb_link_restart_on_failure": True,
    "vkb_link_recovery_cooldown": 60,
    "track_unregistered_events": False,
    "recorder_mock_commander": "CMDR",
    "recorder_mock_fid": "F0000000",
}


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
