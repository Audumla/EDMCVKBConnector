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
import json
import time
from pathlib import Path
from typing import Any, Optional

try:
    # Allow overriding the EDMC installation path for local testing by setting
    # the EDMC_PATH or EDMC_HOME environment variable to the EDMC install folder.
    edmc_path = os.environ.get("EDMC_PATH") or os.environ.get("EDMC_HOME")
    if edmc_path:
        import sys

        if edmc_path not in sys.path:
            sys.path.insert(0, edmc_path)

    # Support local source-tree runs where package code lives under ./src.
    plugin_src_path = os.path.join(os.path.dirname(__file__), "src")
    if os.path.isdir(plugin_src_path):
        import sys

        if plugin_src_path not in sys.path:
            sys.path.insert(0, plugin_src_path)

    from config import appname, appversion
except Exception:
    # Allow local testing outside EDMC by providing sensible defaults
    appname = "EDMarketConnector"
    appversion = "0.0.0"

# Plugin metadata (single-source version from package module)
from edmcruleengine.version import __version__ as VERSION
from edmcruleengine.paths import PLUGIN_DATA_DIR

# Logger setup per EDMC plugin requirements
# The plugin_name MUST be the plugin folder name.
plugin_name = os.path.basename(os.path.dirname(__file__))

try:
    # Prefer EDMC's plugin logger so records include context fields
    # (e.g. osthreadid/qualname) expected by EDMC formatters.
    from EDMCLogging import get_plugin_logger  # type: ignore

    logger = get_plugin_logger(plugin_name)
    _using_edmc_logger = True
except Exception:
    # Fallback for local testing outside EDMC.
    plugin_logger_name = f"{appname}.{plugin_name}"
    logger = logging.getLogger(plugin_logger_name)
    _using_edmc_logger = False

plugin_logger_name = logger.name

# Tell submodules to log under the same EDMC-managed hierarchy.
from edmcruleengine import set_plugin_logger_name
set_plugin_logger_name(plugin_logger_name)

# Ensure lifecycle visibility even if EDMC/root defaults are WARNING.
if logger.getEffectiveLevel() > logging.INFO:
    logger.setLevel(logging.INFO)

# Local-only fallback logging if EDMC logging isn't available.
if not _using_edmc_logger and not logger.hasHandlers():
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
_event_recorder = None
_plugin_dir = None
_prefs_vars = {}
_vkb_link_started_by_plugin = False


def _compute_test_shift_bitmaps_from_ui() -> tuple[Optional[int], Optional[int]]:
    """Compute shift/subshift bitmap values from UI checkbox vars."""
    global _prefs_vars

    shift_vars = _prefs_vars.get("test_shift_vars")
    subshift_vars = _prefs_vars.get("test_subshift_vars")
    if not isinstance(shift_vars, list) or not isinstance(subshift_vars, list):
        return None, None

    shift_bitmap = 0
    # Shift1/Shift2 are stored in bits 0/1.
    for var, shift_code in zip(shift_vars, (1, 2)):
        if hasattr(var, "get") and bool(var.get()):
            shift_bitmap |= (1 << (shift_code - 1))

    subshift_bitmap = 0
    # Subshift1..7 are stored in bits 0..6.
    for code in range(1, min(8, len(subshift_vars) + 1)):
        var = subshift_vars[code - 1]
        if hasattr(var, "get") and bool(var.get()):
            subshift_bitmap |= (1 << (code - 1))

    return shift_bitmap, subshift_bitmap


def _restore_test_shift_state_from_config() -> None:
    """Restore persisted test Shift/Subshift bitmaps into the event handler."""
    global _config, _event_handler

    if not _config or not _event_handler:
        return

    shift_bitmap = int(_config.get("test_shift_bitmap", 0)) & 0x03
    subshift_bitmap = int(_config.get("test_subshift_bitmap", 0)) & 0x7F
    _event_handler._shift_bitmap = shift_bitmap
    _event_handler._subshift_bitmap = subshift_bitmap


def _ensure_rules_file_exists(plugin_dir: str) -> None:
    """
    Ensure rules.json exists, creating from example if needed.
    
    This ensures that users' rules are never overridden when the plugin updates.
    On first run, the default rules.json.example is copied to rules.json.
    
    Args:
        plugin_dir: The plugin installation directory.
    """
    rules_path = os.path.join(plugin_dir, "rules.json")
    rules_example_path = os.path.join(plugin_dir, PLUGIN_DATA_DIR, "rules.json.example")
    
    # If rules.json already exists, user has configured it - don't touch it
    if os.path.exists(rules_path):
        logger.debug(f"User rules file exists: {rules_path}")
        return
    
    # If example doesn't exist either, that's okay - some deployments might not include it
    if not os.path.exists(rules_example_path):
        logger.debug(f"No default rules file found: {rules_example_path}")
        return
    
    # Copy the example to create the initial rules.json
    try:
        with open(rules_example_path, "r", encoding="utf-8") as src:
            content = src.read()
        with open(rules_path, "w", encoding="utf-8") as dst:
            dst.write(content)
        logger.info(f"Created default rules file: {rules_path}")
    except Exception as e:
        logger.warning(f"Could not create default rules file from {rules_example_path}: {e}")


def _resolve_rules_file_path() -> str:
    """Resolve the rules.json path used by the plugin."""
    global _config, _plugin_dir
    override = (_config.get("rules_path", "") if _config else "") or ""
    override = str(override).strip()
    if override:
        return override
    if _plugin_dir:
        return os.path.join(_plugin_dir, "rules.json")
    return os.path.join(os.getcwd(), "rules.json")


def _load_rules_file_for_ui() -> tuple[list[dict], bool, str]:
    """
    Load rule objects for UI editing.

    Returns:
        (rules, wrapped, rules_path)
        wrapped=True means file format is {"rules": [...]}
    """
    rules_path = _resolve_rules_file_path()
    if not os.path.exists(rules_path):
        return [], False, rules_path

    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load rules UI data from {rules_path}: {e}")
        return [], False, rules_path

    if isinstance(data, dict):
        rules = data.get("rules")
        if isinstance(rules, list):
            return [r for r in rules if isinstance(r, dict)], True, rules_path
        logger.warning(f"Rules file {rules_path} has object root but no 'rules' list")
        return [], True, rules_path

    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)], False, rules_path

    logger.warning(f"Rules file {rules_path} must contain a list or object with 'rules' list")
    return [], False, rules_path


def _save_rules_file_from_ui(rules: list[dict], wrapped: bool, rules_path: str) -> bool:
    """Persist edited rules back to rules.json."""
    try:
        parent = os.path.dirname(rules_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {"rules": rules} if wrapped else rules
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        return True
    except Exception as e:
        logger.error(f"Failed to write rules file {rules_path}: {e}")
        return False


def plugin_start3(plugin_dir: str) -> Optional[str]:
    """
    Start the plugin (called by EDMC 5.0+).
    
    Initializes the VKB connector with automatic reconnection on startup.
    Connection happens in a background thread to avoid blocking the UI.
    
    Args:
        plugin_dir: Directory where the plugin is installed.
        
    Returns:
        Plugin name as displayed in EDMC UI.
    """
    global _config, _event_handler, _event_recorder, _plugin_dir

    try:
        # Import here to avoid issues if EDMC modules aren't available during testing
        from edmcruleengine import Config, EventHandler
        from edmcruleengine.event_recorder import EventRecorder
        import threading

        logger.info(f"VKB Connector v{VERSION} starting")

        # Initialize configuration (uses EDMC's stored preferences)
        _config = Config()
        _plugin_dir = plugin_dir

        # Ensure default rules.json exists (from rules.json.example) if user hasn't created one
        _ensure_rules_file_exists(_plugin_dir)

        vkb_host = _config.get("vkb_host", "127.0.0.1")
        vkb_port = _config.get("vkb_port", 50995)
        logger.info(
            "Startup self-check: "
            f"plugin_dir={_plugin_dir}, "
            f"module_file={__file__}, "
            f"rules_path={_resolve_rules_file_path()}, "
            f"logger={plugin_logger_name}"
        )
        logger.info(
            f"VKB Connector v{VERSION} initialized. "
            f"Target: {vkb_host}:{vkb_port}"
        )

        # Initialize event handler with automatic reconnection
        _event_handler = EventHandler(_config, plugin_dir=_plugin_dir)
        _event_recorder = EventRecorder()
        _restore_test_shift_state_from_config()
        
        # On startup, refresh unregistered events against catalog
        # This removes any events that may have been added to the catalog since last run
        try:
            removed_count = _event_handler.refresh_unregistered_events_against_catalog()
            if removed_count > 0:
                logger.info(f"Startup: {removed_count} previously unregistered event(s) now in catalog")
        except Exception as e:
            logger.warning(f"Error refreshing unregistered events on startup: {e}")

        startup_ready = threading.Event()
        vkb_start_action = ["none"]

        def _start_vkb_link_if_needed() -> None:
            """Ensure VKB-Link app is running on startup (if not already running)."""
            global _vkb_link_started_by_plugin
            try:
                if not _event_handler or not _config:
                    logger.warning("Startup: VKB-Link check skipped (handler/config unavailable)")
                    return
                manager = getattr(_event_handler, "vkb_link_manager", None)
                if not manager:
                    logger.warning("Startup: VKB-Link manager unavailable")
                    return
                status = manager.get_status(check_running=True)
                logger.info(
                    "Startup: VKB-Link status: "
                    f"running={status.running} exe_path={status.exe_path or 'none'} "
                    f"install_dir={status.install_dir or 'none'} "
                    f"version={status.version or 'unknown'} managed={status.managed}"
                )
                if status.running:
                    logger.info("Startup: VKB-Link already running; no start required")
                    return
                logger.info("Startup: VKB-Link not running; starting now")
                result = manager.ensure_running(host=vkb_host, port=vkb_port, reason="startup")
                logger.info(f"Startup: VKB-Link ensure_running result: {result.message}")
                if result.success:
                    _vkb_link_started_by_plugin = True
                    vkb_start_action[0] = result.action_taken
                if result.status is not None:
                    logger.info(
                        "Startup: VKB-Link post-start status: "
                        f"running={result.status.running} "
                        f"exe_path={result.status.exe_path or 'none'} "
                        f"version={result.status.version or 'unknown'} "
                        f"managed={result.status.managed}"
                    )
                else:
                    logger.info("Startup: VKB-Link post-start status unavailable")
            except Exception as e:
                logger.error(f"Startup: VKB-Link start check failed: {e}", exc_info=True)
            finally:
                startup_ready.set()

        # Start VKB-Link check in background thread to avoid blocking UI
        vkb_link_thread = threading.Thread(target=_start_vkb_link_if_needed, daemon=True)
        vkb_link_thread.start()

        # Start connection attempt in background thread to avoid blocking UI
        def _connect_in_background() -> None:
            """Try to connect to VKB in background without blocking the UI."""
            try:
                if not startup_ready.wait(timeout=30):
                    logger.warning("Startup: VKB-Link start sequence timed out; continuing with connect")
                if _event_handler:
                    # Apply post-start delay if VKB-Link was started or restarted (no countdown)
                    _event_handler._apply_post_start_delay(vkb_start_action[0], countdown=False)
                    _event_handler._wait_for_vkb_listener_ready(vkb_host, vkb_port)
                if _event_handler:
                    _event_handler.set_connection_status_override("Connecting to VKB-Link...")
                if _event_handler.connect():
                    logger.info("Successfully connected to VKB hardware on startup")
                else:
                    logger.warning(
                        f"Initial connection to VKB hardware failed at {vkb_host}:{vkb_port}. "
                        "Automatic reconnection enabled (2s retry for 1 minute, then 10s fallback)."
                    )
            except Exception as e:
                logger.error(f"Error during background connection attempt: {e}", exc_info=True)
            finally:
                if _event_handler:
                    _event_handler.set_connection_status_override(None)

        # Start the connection attempt in a daemon thread so it doesn't block
        connect_thread = threading.Thread(target=_connect_in_background, daemon=True)
        connect_thread.start()

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
    global _event_handler, _event_recorder, _vkb_link_started_by_plugin

    try:
        logger.info("VKB Connector stopping")
        if _event_recorder and _event_recorder.is_recording:
            _event_recorder.stop()
        if _event_handler:
            _event_handler.disconnect()
            manager = getattr(_event_handler, "vkb_link_manager", None)
            if manager:
                try:
                    status_before_stop = manager.get_status(check_running=True)
                    logger.info(
                        "Shutdown: VKB-Link pre-stop status: "
                        f"running={status_before_stop.running} "
                        f"exe_path={status_before_stop.exe_path or 'none'} "
                        f"version={status_before_stop.version or 'unknown'} "
                        f"managed={status_before_stop.managed} "
                        f"started_by_plugin={_vkb_link_started_by_plugin}"
                    )
                except Exception:
                    logger.info("Shutdown: VKB-Link pre-stop status unavailable")
            if _vkb_link_started_by_plugin:
                if manager:
                    logger.info("Shutdown: stopping VKB-Link started by plugin")
                    result = manager.stop_running(reason="plugin_shutdown")
                    logger.info(f"Shutdown: VKB-Link stop result: {result.message}")
                    if result.status is not None:
                        logger.info(
                            "Shutdown: VKB-Link post-stop status: "
                            f"running={result.status.running} "
                            f"exe_path={result.status.exe_path or 'none'} "
                            f"version={result.status.version or 'unknown'} "
                            f"managed={result.status.managed}"
                        )
                    else:
                        logger.info("Shutdown: VKB-Link post-stop status unavailable")
                else:
                    logger.warning("Shutdown: VKB-Link manager unavailable for stop")
            else:
                logger.info("Shutdown: VKB-Link not started by plugin; leaving running")
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

    # Test shift/subshift persistence
    shift_bitmap, subshift_bitmap = _compute_test_shift_bitmaps_from_ui()
    if shift_bitmap is not None and subshift_bitmap is not None:
        _config.set("test_shift_bitmap", int(shift_bitmap) & 0x03)
        _config.set("test_subshift_bitmap", int(subshift_bitmap) & 0x7F)



def _apply_test_shift_from_ui() -> None:
    """Apply Shift/Subshift test toggles from preferences UI to VKB immediately."""
    global _event_handler, _prefs_vars

    if not _event_handler:
        logger.warning("Cannot apply test shift state: event handler not initialized")
        return

    shift_bitmap, subshift_bitmap = _compute_test_shift_bitmaps_from_ui()
    if shift_bitmap is None or subshift_bitmap is None:
        return

    _event_handler._shift_bitmap = shift_bitmap
    _event_handler._subshift_bitmap = subshift_bitmap
    _event_handler._send_shift_state_if_changed(force=True)


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
        
        # Refresh unregistered events against updated catalog
        _event_handler.refresh_unregistered_events_against_catalog()
        
    except Exception as e:
        logger.error(f"Error in prefs_changed: {e}", exc_info=True)


# Event handlers - called by EDMC for various game events
# Format: def journal_event_handler(cmdr: str, is_beta: bool, entry: dict)


def journal_entry(
    cmdr: str, is_beta: bool, system: str, station: str, entry: dict, state: dict
) -> Optional[str]:
    """
    Called when EDMC receives a journal event from Elite Dangerous.
    
    Forwards events to VKB hardware. If the connection is lost, the event handler
    will trigger automatic reconnection attempts.
    
    Args:
        cmdr: Commander name.
        is_beta: Whether running beta version.
        system: Current star system name (may be None).
        station: Current station name (may be None).
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

        # Record event if recorder is active
        if _event_recorder and _event_recorder.is_recording:
            _event_recorder.record("journal", event_type, entry)

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

    # Record event if recorder is active (even if handler is disabled)
    if _event_recorder and _event_recorder.is_recording:
        _event_recorder.record(source, event_type, payload)

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


def _capi_cmdr_dispatch(data: dict, is_beta: bool, source: str, event_type: str) -> Optional[str]:
    """Shared handler for cmdr_data and cmdr_data_legacy CAPI hooks."""
    try:
        cmdr_name = ""
        commander = data.get("commander")
        if isinstance(commander, dict):
            cmdr_name = str(commander.get("name") or "")
        _dispatch_notification(
            source=source,
            event_type=event_type,
            payload=data,
            cmdr=cmdr_name,
            is_beta=is_beta,
        )
    except Exception as e:
        logger.error(f"Error handling {event_type}: {e}", exc_info=True)
    return None


def cmdr_data(data: dict, is_beta: bool) -> Optional[str]:
    """
    Called when EDMC receives CAPI commander profile data.
    """
    return _capi_cmdr_dispatch(data, is_beta, source="capi", event_type="CmdrData")


def cmdr_data_legacy(data: dict, is_beta: bool) -> Optional[str]:
    """
    Called when EDMC receives Legacy CAPI commander profile data.
    """
    return _capi_cmdr_dispatch(data, is_beta, source="capi_legacy", event_type="CmdrDataLegacy")


# Note: capi_shipyard() and capi_outfitting() are NOT standard EDMC plugin hooks.
# EDMC only calls: journal_entry, dashboard_entry, cmdr_data, cmdr_data_legacy,
# capi_fleetcarrier, plugin_prefs, prefs_changed, plugin_app, plugin_stop.
# See: https://github.com/EDCD/EDMarketConnector/blob/main/PLUGINS.md


def capi_fleetcarrier(data: dict) -> Optional[str]:
    """
    Called when EDMC receives CAPI fleet carrier data.
    
    Note: Unlike cmdr_data(), this hook receives only `data` (no `is_beta`).
    Use data.source_host to determine galaxy (SERVER_LIVE, SERVER_BETA, SERVER_LEGACY).
    """
    try:
        _dispatch_notification(
            source="capi_fleetcarrier",
            event_type="CapiFleetCarrier",
            payload=data,
        )
    except Exception as e:
        logger.error(f"Error handling capi_fleetcarrier: {e}", exc_info=True)
    return None


def plugin_prefs(parent, cmdr: str, is_beta: bool):
    """
    Build the plugin preferences UI for EDMC.

    Delegates panel construction to edmcruleengine.prefs_panel.
    """
    global _prefs_vars, _event_recorder

    try:
        from edmcruleengine.prefs_panel import PrefsPanelDeps, build_plugin_prefs_panel
    except Exception as e:
        logger.error(f"Failed to load preferences panel module: {e}", exc_info=True)
        return None

    def _set_prefs_vars(next_vars: dict[str, Any]) -> None:
        global _prefs_vars
        _prefs_vars = next_vars

    def _set_event_recorder(recorder: Any) -> None:
        global _event_recorder
        _event_recorder = recorder

    deps = PrefsPanelDeps(
        logger=logger,
        get_config=lambda: _config,
        get_event_handler=lambda: _event_handler,
        get_event_recorder=lambda: _event_recorder,
        set_event_recorder=_set_event_recorder,
        get_plugin_dir=lambda: _plugin_dir,
        set_prefs_vars=_set_prefs_vars,
        compute_test_shift_bitmaps_from_ui=_compute_test_shift_bitmaps_from_ui,
        apply_test_shift_from_ui=_apply_test_shift_from_ui,
        resolve_rules_file_path=_resolve_rules_file_path,
        load_rules_file_for_ui=_load_rules_file_for_ui,
        save_rules_file_from_ui=_save_rules_file_from_ui,
        plugin_root=Path(__file__).parent,
    )

    return build_plugin_prefs_panel(parent, cmdr, is_beta, deps)
