"""
EDMC Plugin Entry Point for VKB Connector.

This module is the entry point for the EDMC plugin system.
EDMC will import and call the module-level functions defined here.
"""

import logging
from pathlib import Path
from typing import Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Plugin metadata
plugin_name = "EDMC VKB Connector"
plugin_version = "0.1.0"

# Global instances
_config = None
_event_handler = None


def plugin_start3(plugin_dir: str) -> Optional[str]:
    """
    Start the plugin (called by EDMC 5.0+).
    
    Args:
        plugin_dir: Directory where the plugin is installed.
        
    Returns:
        Plugin name if successful, None otherwise.
    """
    global _config, _event_handler

    try:
        # Import here to avoid issues if EDMC modules aren't available during testing
        from edmcvkbconnector import Config, EventHandler

        logger.info(f"Starting {plugin_name} v{plugin_version}")

        # Load configuration
        config_file = Path(plugin_dir) / "config.json"
        _config = Config(str(config_file) if config_file.exists() else None)

        # Initialize event handler
        _event_handler = EventHandler(_config)

        # Connect to VKB hardware
        if not _event_handler.connect():
            logger.warning("Failed to connect to VKB hardware on startup")

        return plugin_name

    except Exception as e:
        logger.error(f"Failed to start {plugin_name}: {e}", exc_info=True)
        return None


def plugin_stop() -> None:
    """
    Stop the plugin (called by EDMC on shutdown).
    """
    global _event_handler

    try:
        logger.info(f"Stopping {plugin_name}")
        if _event_handler:
            _event_handler.disconnect()
    except Exception as e:
        logger.error(f"Error stopping {plugin_name}: {e}", exc_info=True)


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Called when preferences are changed (optional).
    
    Args:
        cmdr: Commander name.
        is_beta: Whether running beta version.
    """
    global _event_handler

    try:
        if _event_handler:
            # Reconnect in case settings changed
            _event_handler.disconnect()
            _event_handler.connect()
    except Exception as e:
        logger.error(f"Error in prefs_changed: {e}", exc_info=True)


# Event handlers - called by EDMC for various game events
# Format: def journal_event_handler(cmdr: str, is_beta: bool, entry: dict)


def journal_entry(cmdr: str, is_beta: bool, entry: dict, state: dict) -> Optional[str]:
    """
    Called when EDMC receives a journal event from Elite Dangerous.
    
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

        # Forward to VKB hardware
        _event_handler.handle_event(event_type, entry)

    except Exception as e:
        logger.error(f"Error handling journal entry: {e}", exc_info=True)

    return None
