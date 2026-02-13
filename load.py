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
from typing import Any, Optional

try:
    # Allow overriding the EDMC installation path for local testing by setting
    # the EDMC_PATH or EDMC_HOME environment variable to the EDMC install folder.
    edmc_path = os.environ.get("EDMC_PATH") or os.environ.get("EDMC_HOME")
    if edmc_path:
        import sys

        if edmc_path not in sys.path:
            sys.path.insert(0, edmc_path)

    from config import appname, appversion
except Exception:
    # Allow local testing outside EDMC by providing sensible defaults
    appname = "EDMarketConnector"
    appversion = "0.0.0"

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
_plugin_dir = None
_prefs_vars = {}


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
    global _config, _event_handler, _plugin_dir

    try:
        # Import here to avoid issues if EDMC modules aren't available during testing
        from edmcvkbconnector import Config, EventHandler

        logger.info(f"VKB Connector v{VERSION} starting")

        # Initialize configuration (uses EDMC's stored preferences)
        _config = Config()
        _plugin_dir = plugin_dir

        vkb_host = _config.get("vkb_host", "127.0.0.1")
        vkb_port = _config.get("vkb_port", 50995)
        logger.info(
            f"VKB Connector v{VERSION} initialized. "
            f"Target: {vkb_host}:{vkb_port}"
        )

        # Initialize event handler with automatic reconnection
        _event_handler = EventHandler(_config, plugin_dir=_plugin_dir)

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


def _persist_prefs_from_ui() -> None:
    """
    Persist UI preferences to config if UI variables are present.
    Includes validation for port number.
    """
    global _config, _prefs_vars
    
    if not _prefs_vars or not _config:
        return
    
    # Host preference
    host_var = _prefs_vars.get("vkb_host")
    if host_var is not None:
        _config.set("vkb_host", host_var.get().strip())
    
    # Port preference (with validation)
    port_var = _prefs_vars.get("vkb_port")
    if port_var is not None:
        try:
            port_value = int(port_var.get())
            if 1 <= port_value <= 65535:
                _config.set("vkb_port", port_value)
            else:
                logger.warning(f"Invalid VKB port {port_value}; must be 1-65535")
        except ValueError:
            logger.warning("Invalid VKB port in preferences; must be an integer")


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Called when preferences are changed (optional).
    
    Reconnects to VKB hardware in case configuration settings changed.
    EDMC's config API automatically reloads settings, so we just reconnect
    with the new values.
    
    Args:
        cmdr: Commander name.
        is_beta: Whether running beta version.
    """
    global _event_handler

    if not _event_handler:
        return

    try:
        logger.info("Preferences changed, reconnecting VKB connector")
        _persist_prefs_from_ui()
        
        # Refresh VKB endpoint before reconnecting to use updated host/port
        _event_handler._refresh_vkb_endpoint()
        
        # Reload rules and reconnect with new settings
        _event_handler.reload_rules()
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
        _event_handler.handle_event(
            event_type,
            entry,
            source="journal",
            cmdr=cmdr,
            is_beta=is_beta,
        )

    except Exception as e:
        logger.error(f"Error handling journal entry: {e}", exc_info=True)

    return None


def _dispatch_notification(
    *,
    source: str,
    event_type: str,
    payload: dict,
    cmdr: str = "",
    is_beta: bool = False,
) -> None:
    """Route non-journal EDMC notifications into the same event pipeline."""
    global _event_handler

    if not _event_handler or not _event_handler.enabled:
        return

    _event_handler.handle_event(
        event_type,
        payload,
        source=source,
        cmdr=cmdr,
        is_beta=is_beta,
    )


def dashboard_entry(cmdr: str, is_beta: bool, entry: dict) -> None:
    """
    Called when EDMC receives a dashboard/status update.
    """
    try:
        event_type = str(entry.get("event", "Dashboard"))
        _dispatch_notification(
            source="dashboard",
            event_type=event_type,
            payload=entry,
            cmdr=cmdr,
            is_beta=is_beta,
        )
    except Exception as e:
        logger.error(f"Error handling dashboard entry: {e}", exc_info=True)


def cmdr_data(data: dict, is_beta: bool) -> Optional[str]:
    """
    Called when EDMC receives CAPI commander profile data.
    """
    try:
        cmdr_name = ""
        commander = data.get("commander")
        if isinstance(commander, dict):
            cmdr_name = str(commander.get("name") or "")

        _dispatch_notification(
            source="capi",
            event_type="CmdrData",
            payload=data,
            cmdr=cmdr_name,
            is_beta=is_beta,
        )
    except Exception as e:
        logger.error(f"Error handling cmdr_data: {e}", exc_info=True)
    return None


def capi_shipyard(data: dict, is_beta: bool) -> Optional[str]:
    """
    Called when EDMC receives CAPI shipyard data.
    """
    try:
        _dispatch_notification(
            source="capi_shipyard",
            event_type="CapiShipyard",
            payload=data,
            is_beta=is_beta,
        )
    except Exception as e:
        logger.error(f"Error handling capi_shipyard: {e}", exc_info=True)
    return None


def capi_outfitting(data: dict, is_beta: bool) -> Optional[str]:
    """
    Called when EDMC receives CAPI outfitting data.
    """
    try:
        _dispatch_notification(
            source="capi_outfitting",
            event_type="CapiOutfitting",
            payload=data,
            is_beta=is_beta,
        )
    except Exception as e:
        logger.error(f"Error handling capi_outfitting: {e}", exc_info=True)
    return None


def capi_fleetcarrier(data: dict, is_beta: bool) -> Optional[str]:
    """
    Called when EDMC receives CAPI fleet carrier data.
    """
    try:
        _dispatch_notification(
            source="capi_fleetcarrier",
            event_type="CapiFleetCarrier",
            payload=data,
            is_beta=is_beta,
        )
    except Exception as e:
        logger.error(f"Error handling capi_fleetcarrier: {e}", exc_info=True)
    return None


def plugin_prefs(parent, cmdr: str, is_beta: bool):
    """
    Build the plugin preferences UI for EDMC.
    """
    global _prefs_vars, _config

    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as e:
        logger.error(f"Failed to load tkinter for preferences UI: {e}")
        return None

    frame = ttk.Frame(parent)

    vkb_host = _config.get("vkb_host", "127.0.0.1") if _config else "127.0.0.1"
    vkb_port = _config.get("vkb_port", 50995) if _config else 50995

    host_var = tk.StringVar(value=str(vkb_host))
    port_var = tk.StringVar(value=str(vkb_port))

    _prefs_vars = {
        "vkb_host": host_var,
        "vkb_port": port_var,
    }

    ttk.Label(frame, text="VKB Host:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(frame, textvariable=host_var, width=24).grid(row=0, column=1, sticky="w", padx=4, pady=2)

    ttk.Label(frame, text="VKB Port:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(frame, textvariable=port_var, width=10).grid(row=1, column=1, sticky="w", padx=4, pady=2)

    return frame
