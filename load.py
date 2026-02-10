"""
EDMC Plugin Entry Point for VKB Connector.

This module is the entry point for the EDMC plugin system.
EDMC will import and call the module-level functions defined here.

Plugin: EDMC VKB Connector
Purpose: Forward Elite Dangerous game events to VKB HOTAS/HOSAS hardware via TCP/IP
Author: EDMC VKB Connector Contributors
License: MIT
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

from config import appname

# Plugin metadata
VERSION = "0.1.0"  # Required by EDMC standards for semantic versioning

# Logger setup per EDMC plugin requirements
# The plugin_name MUST be the folder name (edmcvkbconnector)
plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f"{appname}.{plugin_name}")

# Set up logging if it hasn't been already by core EDMC code
if not logger.hasHandlers():
    level = logging.INFO
    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(
        f"%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s:%(message)s"
    )
    logger_formatter.default_time_format = "%Y-%m-%d %H:%M:%S"
    logger_formatter.default_msec_format = "%s.%03d"
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)

# Global instances
_config = None
_event_handler = None


def plugin_start3(plugin_dir: str) -> Optional[str]:
    """
    Start the plugin (called by EDMC 5.0+).
    
    Initializes the VKB connector with automatic reconnection on startup.
    If initial connection fails, the plugin will continue running and attempt
    to reconnect automatically in the background.
    
    Args:
        plugin_dir: Directory where the plugin is installed.
        
    Returns:
        Plugin name as displayed in EDMC UI.
    """
    global _config, _event_handler

    try:
        # Import here to avoid issues if EDMC modules aren't available during testing
        from edmcvkbconnector import Config, EventHandler

        logger.info(f"VKB Connector v{VERSION} starting")

        # Load configuration
        config_file = Path(plugin_dir) / "config.json"
        _config = Config(str(config_file) if config_file.exists() else None)
        
        vkb_host = _config.get("vkb_host", "127.0.0.1")
        vkb_port = _config.get("vkb_port", 12345)
        logger.info(
            f"VKB Connector v{VERSION} initialized. "
            f"Target: {vkb_host}:{vkb_port}"
        )

        # Initialize event handler with automatic reconnection
        _event_handler = EventHandler(_config)

        # Connect to VKB hardware and start automatic reconnection
        # Note: connect() will start the reconnection worker even if initial connection fails
        if _event_handler.connect():
            logger.info("Successfully connected to VKB hardware on startup")
        else:
            logger.warning(
                f"Initial connection to VKB hardware failed at {vkb_host}:{vkb_port}. "
                "Automatic reconnection enabled (2s retry for 1 minute, then 10s fallback)."
            )

        # Return the internal name for the plugin (shown in EDMC UI)
        return "VKB Connector"

    except Exception as e:
        logger.error(f"Failed to start VKB Connector: {e}", exc_info=True)
        return None


def plugin_stop() -> None:
    """
    Stop the plugin (called by EDMC on shutdown).
    
    Gracefully shuts down the VKB connector and stops all background reconnection attempts.
    """
    global _event_handler

    try:
        logger.info("VKB Connector stopping")
        if _event_handler:
            _event_handler.disconnect()
            logger.info("VKB Connector stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping VKB Connector: {e}", exc_info=True)


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Called when preferences are changed (optional).
    
    Reconnects to VKB hardware in case configuration settings changed.
    
    Args:
        cmdr: Commander name.
        is_beta: Whether running beta version.
    """
    global _config, _event_handler

    try:
        if _event_handler:
            logger.info("Preferences changed, reconnecting VKB connector")
            
            # Reload configuration
            if _config:
                config_file = Path(_event_handler.vkb_client.host).parent / "config.json"
                _config.load_from_file(str(config_file))
            
            # Reconnect with new settings
            _event_handler.disconnect()
            _event_handler.connect()
    except Exception as e:
        logger.error(f"Error in prefs_changed: {e}", exc_info=True)


# Event handlers - called by EDMC for various game events
# Format: def journal_event_handler(cmdr: str, is_beta: bool, entry: dict)


def journal_entry(cmdr: str, is_beta: bool, entry: dict, state: dict) -> Optional[str]:
    """
    Called when EDMC receives a journal event from Elite Dangerous.
    
    Forwards events to VKB hardware. If the connection is lost, the event handler
    will trigger automatic reconnection attempts.
    
    Args:
        cmdr: Commander name.
        is_beta: Whether running beta version.
        entry: Journal entry data.
        state: Current game state.
        
    Returns:
        Optional return value (not typically used).
    """
    global _event_handler

    try:
        if not _event_handler or not _event_handler.enabled:
            return None

        # Get event type
        event_type = entry.get("event", "Unknown")

        # Forward to VKB hardware (handles reconnection internally if needed)
        _event_handler.handle_event(event_type, entry)

    except Exception as e:
        logger.error(f"Error handling journal entry: {e}", exc_info=True)

    return None
