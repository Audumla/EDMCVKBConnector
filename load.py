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
_plugin_dir = None
_prefs_vars = {}


class _ToolTip:
    """Simple tooltip helper for tkinter widgets."""

    def __init__(self, widget, text: str, delay_ms: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip_window = None

        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._tip_window = tk.Toplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self._tip_window, text=self.text, relief="solid", borderwidth=1)
        label.pack(ipadx=6, ipady=3)

    def _hide(self, event=None) -> None:
        self._cancel()
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None


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
    rules_example_path = os.path.join(plugin_dir, "rules.json.example")
    
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


def _update_ini_file(ini_path: str, host: str, port: str) -> bool:
    """
    Update VKB-Link INI file with TCP configuration.
    
    Creates or updates the [TCP] section with:
    - Adress={host}  (note: typo is deliberate per VKB-Link requirements)
    - Port={port}
    
    Args:
        ini_path: Path to the INI file
        host: VKB-Link host address
        port: VKB-Link port number
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import configparser
        
        # Read existing INI file or create new one
        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case
        
        if os.path.exists(ini_path):
            config.read(ini_path, encoding='utf-8')
        
        # Ensure [TCP] section exists
        if not config.has_section('TCP'):
            config.add_section('TCP')
        
        # Set values (note: "Adress" typo is deliberate per VKB-Link spec)
        config.set('TCP', 'Adress', host)
        config.set('TCP', 'Port', port)
        
        # Write back to file
        with open(ini_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        logger.info(f"Updated VKB-Link INI file: {ini_path} with host={host}, port={port}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update INI file {ini_path}: {e}", exc_info=True)
        return False


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
    global _config, _event_handler, _plugin_dir

    try:
        # Import here to avoid issues if EDMC modules aren't available during testing
        from edmcruleengine import Config, EventHandler
        import threading

        logger.info(f"VKB Connector v{VERSION} starting")

        # Initialize configuration (uses EDMC's stored preferences)
        _config = Config()
        _plugin_dir = plugin_dir

        # Ensure default rules.json exists (from rules.json.example) if user hasn't created one
        _ensure_rules_file_exists(_plugin_dir)

        vkb_host = _config.get("vkb_host", "127.0.0.1")
        vkb_port = _config.get("vkb_port", 50995)
        rules_override = (_config.get("rules_path", "") or "").strip()
        rules_path = rules_override if rules_override else os.path.join(_plugin_dir, "rules.json")
        logger.info(
            "Startup self-check: "
            f"plugin_dir={_plugin_dir}, "
            f"module_file={__file__}, "
            f"rules_path={rules_path}, "
            f"logger={plugin_logger_name}"
        )
        logger.info(
            f"VKB Connector v{VERSION} initialized. "
            f"Target: {vkb_host}:{vkb_port}"
        )

        # Initialize event handler with automatic reconnection
        _event_handler = EventHandler(_config, plugin_dir=_plugin_dir)
        _restore_test_shift_state_from_config()
        
        # On startup, refresh unregistered events against catalog
        # This removes any events that may have been added to the catalog since last run
        try:
            removed_count = _event_handler.refresh_unregistered_events_against_catalog()
            if removed_count > 0:
                logger.info(f"Startup: {removed_count} previously unregistered event(s) now in catalog")
        except Exception as e:
            logger.warning(f"Error refreshing unregistered events on startup: {e}")

        # Start connection attempt in background thread to avoid blocking UI
        def _connect_in_background() -> None:
            """Try to connect to VKB in background without blocking the UI."""
            try:
                if _event_handler.connect():
                    logger.info("Successfully connected to VKB hardware on startup")
                else:
                    logger.warning(
                        f"Initial connection to VKB hardware failed at {vkb_host}:{vkb_port}. "
                        "Automatic reconnection enabled (2s retry for 1 minute, then 10s fallback)."
                    )
            except Exception as e:
                logger.error(f"Error during background connection attempt: {e}", exc_info=True)

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

    # Test shift/subshift persistence
    shift_bitmap, subshift_bitmap = _compute_test_shift_bitmaps_from_ui()
    if shift_bitmap is not None and subshift_bitmap is not None:
        _config.set("test_shift_bitmap", int(shift_bitmap) & 0x03)
        _config.set("test_subshift_bitmap", int(subshift_bitmap) & 0x7F)
    
    # Anonymization settings
    anonymize_var = _prefs_vars.get("anonymize_events")
    if anonymize_var is not None:
        _config.set("anonymize_events", bool(anonymize_var.get()))
    
    mock_cmdr_var = _prefs_vars.get("mock_commander_name")
    if mock_cmdr_var is not None:
        _config.set("mock_commander_name", mock_cmdr_var.get().strip())
    
    mock_ship_var = _prefs_vars.get("mock_ship_name")
    if mock_ship_var is not None:
        _config.set("mock_ship_name", mock_ship_var.get().strip())
    
    mock_ident_var = _prefs_vars.get("mock_ship_ident")
    if mock_ident_var is not None:
        _config.set("mock_ship_ident", mock_ident_var.get().strip())


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


def cmdr_data_legacy(data: dict, is_beta: bool) -> Optional[str]:
    """
    Called when EDMC receives Legacy CAPI commander profile data.
    """
    try:
        cmdr_name = ""
        commander = data.get("commander")
        if isinstance(commander, dict):
            cmdr_name = str(commander.get("name") or "")

        _dispatch_notification(
            source="capi_legacy",
            event_type="CmdrDataLegacy",
            payload=data,
            cmdr=cmdr_name,
            is_beta=is_beta,
        )
    except Exception as e:
        logger.error(f"Error handling cmdr_data_legacy: {e}", exc_info=True)
    return None


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
    
    Uses EDMC's myNotebook widgets when available.
    """
    global _prefs_vars, _config, tk, ttk

    try:
        import tkinter as tk
        from tkinter import ttk
        import myNotebook as nb
    except Exception as e:
        # Fallback for local testing outside EDMC where myNotebook may not exist.
        try:
            import tkinter as tk
            from tkinter import ttk

            class _NotebookCompat:
                Frame = ttk.Frame

            nb = _NotebookCompat()
        except Exception as inner_e:
            logger.error(f"Failed to load tkinter for preferences UI: {inner_e}")
            return None

    frame = nb.Frame(parent)

    notebook = ttk.Notebook(frame)
    notebook.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    settings_tab = ttk.Frame(notebook)
    events_tab = ttk.Frame(notebook)
    notebook.add(settings_tab, text="Settings")
    notebook.add(events_tab, text="Unregistered Events")

    settings_tab.columnconfigure(0, weight=1)
    settings_tab.columnconfigure(1, weight=1)

    vkb_host = _config.get("vkb_host", "127.0.0.1") if _config else "127.0.0.1"
    vkb_port = _config.get("vkb_port", 50995) if _config else 50995
    host_var = tk.StringVar(value=str(vkb_host))
    port_var = tk.StringVar(value=str(vkb_port))
    if _event_handler:
        current_shift = int(_event_handler._shift_bitmap)
        current_subshift = int(_event_handler._subshift_bitmap)
    else:
        current_shift = int(_config.get("test_shift_bitmap", 0)) if _config else 0
        current_subshift = int(_config.get("test_subshift_bitmap", 0)) if _config else 0

    shift_vars = [tk.BooleanVar(value=bool(current_shift & (1 << (code - 1)))) for code in (1, 2)]
    subshift_vars = [tk.BooleanVar(value=bool(current_subshift & (1 << i))) for i in range(7)]

    _prefs_vars = {
        "vkb_host": host_var,
        "vkb_port": port_var,
        "test_shift_vars": shift_vars,
        "test_subshift_vars": subshift_vars,
    }

    vkb_link_frame = ttk.LabelFrame(settings_tab, text="VKB-Link", padding=6)
    vkb_link_frame.grid(row=0, column=0, sticky="nsew", padx=(4, 6), pady=2)
    vkb_link_frame.columnconfigure(1, weight=1)

    ttk.Label(vkb_link_frame, text="VKB Host:").grid(row=0, column=0, sticky="w", padx=4, pady=(2, 6))
    ttk.Entry(vkb_link_frame, textvariable=host_var, width=24).grid(row=0, column=1, sticky="ew", padx=4, pady=(2, 6))

    ttk.Label(vkb_link_frame, text="VKB Port:").grid(row=1, column=0, sticky="w", padx=4, pady=(0, 2))
    ttk.Entry(vkb_link_frame, textvariable=port_var, width=10).grid(row=1, column=1, sticky="w", padx=4, pady=(0, 2))

    # Connection status display
    status_var = tk.StringVar(value="Checking connection...")
    status_label = ttk.Label(vkb_link_frame, textvariable=status_var, foreground="gray")
    status_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))

    # Button to configure VKB-Link INI file (shown when not connected)
    ini_button_frame = ttk.Frame(vkb_link_frame)
    ini_button_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 2))
    
    def _update_vkb_ini():
        """Open file dialog to select and update vkb-link INI file."""
        try:
            from tkinter import filedialog, messagebox
            
            # Ask user to locate the VKB-Link INI file
            ini_path = filedialog.askopenfilename(
                title="Select VKB-Link Configuration File",
                filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
                initialdir=os.path.expanduser("~")
            )
            
            if not ini_path:
                return
            
            # Get current host and port values
            host = host_var.get().strip()
            port = port_var.get().strip()
            
            # Update the INI file
            if _update_ini_file(ini_path, host, port):
                messagebox.showinfo(
                    "Success",
                    f"VKB-Link configuration updated:\n{ini_path}\n\n[TCP]\nAdress={host}\nPort={port}"
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"Failed to update VKB-Link configuration file:\n{ini_path}"
                )
        except Exception as e:
            logger.error(f"Error updating VKB-Link INI: {e}", exc_info=True)
            try:
                from tkinter import messagebox
                messagebox.showerror("Error", f"Failed to update INI file: {e}")
            except Exception:
                pass
    
    ini_button = ttk.Button(ini_button_frame, text="Configure VKB-Link INI File", command=_update_vkb_ini)
    ini_button.pack(side=tk.LEFT)
    
    # Initially hide the INI button (will be shown if not connected)
    ini_button_frame.grid_remove()
    
    # Store references for status updates
    _prefs_vars["status_var"] = status_var
    _prefs_vars["status_label"] = status_label
    _prefs_vars["ini_button_frame"] = ini_button_frame
    
    def _update_connection_status():
        """Update connection status display periodically."""
        if not frame.winfo_exists():
            return
        
        try:
            if _event_handler and _event_handler.vkb_client:
                if _event_handler.vkb_client.connected:
                    status_var.set("✓ Connected to VKB-Link")
                    status_label.config(foreground="green")
                    ini_button_frame.grid_remove()
                else:
                    status_var.set("✗ Not connected to VKB-Link")
                    status_label.config(foreground="red")
                    ini_button_frame.grid()
            else:
                status_var.set("Initializing...")
                status_label.config(foreground="gray")
                ini_button_frame.grid_remove()
        except Exception as e:
            logger.debug(f"Error updating connection status: {e}")
        
        # Schedule next update in 1 second
        frame.after(1000, _update_connection_status)
    
    # Start periodic status updates
    frame.after(500, _update_connection_status)

    static_shift_frame = ttk.LabelFrame(settings_tab, text="Static Shift Flags", padding=6)
    static_shift_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 4), pady=2)

    ttk.Label(static_shift_frame, text="Shift:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
    for i, shift_code in enumerate((1, 2)):
        ttk.Checkbutton(
            static_shift_frame,
            text=f"{shift_code}",
            variable=shift_vars[i],
            command=_apply_test_shift_from_ui,
        ).grid(row=0, column=1 + i, sticky="w", padx=2, pady=2)

    ttk.Label(static_shift_frame, text="SubShift:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
    for i in range(7):
        ttk.Checkbutton(
            static_shift_frame,
            text=f"{i + 1}",
            variable=subshift_vars[i],
            command=_apply_test_shift_from_ui,
        ).grid(row=1, column=1 + i, sticky="w", padx=2, pady=2)

    # Event Anonymization Settings
    anonymize_frame = ttk.LabelFrame(settings_tab, text="Event Anonymization", padding=6)
    anonymize_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=(6, 2))
    anonymize_frame.columnconfigure(1, weight=1)
    
    anonymize_enabled = _config.get("anonymize_events", False) if _config else False
    mock_cmdr_name = _config.get("mock_commander_name", "TestCommander") if _config else "TestCommander"
    mock_ship = _config.get("mock_ship_name", "TestShip") if _config else "TestShip"
    mock_ident = _config.get("mock_ship_ident", "TEST-01") if _config else "TEST-01"
    
    anonymize_var = tk.BooleanVar(value=anonymize_enabled)
    mock_cmdr_var = tk.StringVar(value=str(mock_cmdr_name))
    mock_ship_var = tk.StringVar(value=str(mock_ship))
    mock_ident_var = tk.StringVar(value=str(mock_ident))
    
    _prefs_vars["anonymize_events"] = anonymize_var
    _prefs_vars["mock_commander_name"] = mock_cmdr_var
    _prefs_vars["mock_ship_name"] = mock_ship_var
    _prefs_vars["mock_ship_ident"] = mock_ident_var
    
    ttk.Checkbutton(
        anonymize_frame,
        text="Enable event anonymization (replaces identifying information with mock data)",
        variable=anonymize_var,
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 6))
    
    ttk.Label(anonymize_frame, text="Mock Commander Name:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(anonymize_frame, textvariable=mock_cmdr_var, width=24).grid(row=1, column=1, sticky="w", padx=4, pady=2)
    
    ttk.Label(anonymize_frame, text="Mock Ship Name:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(anonymize_frame, textvariable=mock_ship_var, width=24).grid(row=2, column=1, sticky="w", padx=4, pady=2)
    
    ttk.Label(anonymize_frame, text="Mock Ship Ident:").grid(row=3, column=0, sticky="w", padx=4, pady=(2, 2))
    ttk.Entry(anonymize_frame, textvariable=mock_ident_var, width=24).grid(row=3, column=1, sticky="w", padx=4, pady=(2, 2))
    
    settings_tab.rowconfigure(2, weight=1)

    # Rules summary panel
    rules_path_var = tk.StringVar(value="")
    rules_cache: list[dict] = []
    rules_wrapped = False
    rules_path = ""
    rules_mtime: Optional[float] = None
    rules_poll_ms = 1500

    def _refresh_rules_path() -> None:
        rules_path_var.set(_resolve_rules_file_path())

    def _open_rules_editor(initial_rule_index: Optional[int] = None) -> None:
        try:
            from edmcruleengine.rule_editor import show_rule_editor

            _refresh_rules_path()
            rules_file = Path(rules_path_var.get())
            plugin_dir = Path(_plugin_dir) if _plugin_dir else Path(__file__).parent
            window = show_rule_editor(
                frame,
                rules_file,
                plugin_dir,
                initial_rule_index=initial_rule_index,
            )
            if window is not None:
                def _on_editor_closed(event):
                    if event.widget is window:
                        _refresh_rules_summary()
                window.bind("<Destroy>", _on_editor_closed)
        except Exception as e:
            logger.error(f"Failed to open rule editor: {e}", exc_info=True)
            return

    def _edit_rule(index: int) -> None:
        _open_rules_editor(initial_rule_index=index)

    def _save_rules_summary(next_rules: list[dict], wrapped: bool, path: str) -> bool:
        if not _save_rules_file_from_ui(next_rules, wrapped, path):
            return False

        if _event_handler:
            _event_handler.reload_rules()
        return True

    def _toggle_rule_enabled(index: int, enabled_var: tk.BooleanVar) -> None:
        nonlocal rules_cache
        if index < 0 or index >= len(rules_cache):
            return
        rules_cache[index]["enabled"] = bool(enabled_var.get())
        _save_rules_summary(rules_cache, rules_wrapped, rules_path)

    def _duplicate_rule(index: int) -> None:
        nonlocal rules_cache
        if index < 0 or index >= len(rules_cache):
            return
        original = rules_cache[index]
        duplicate = json.loads(json.dumps(original))
        title = duplicate.get("title", "Rule")
        duplicate["title"] = f"{title} (copy)"
        duplicate.pop("id", None)
        rules_cache.insert(index + 1, duplicate)
        if _save_rules_summary(rules_cache, rules_wrapped, rules_path):
            _refresh_rules_summary()

    def _delete_rule(index: int) -> None:
        nonlocal rules_cache
        if index < 0 or index >= len(rules_cache):
            return
        from tkinter import messagebox

        rule = rules_cache[index]
        title = rule.get("title", rule.get("id", "this rule"))
        if not messagebox.askyesno("Confirm Delete", f'Delete rule "{title}"?'):
            return
        del rules_cache[index]
        if _save_rules_summary(rules_cache, rules_wrapped, rules_path):
            _refresh_rules_summary()

    def _get_rules_mtime() -> Optional[float]:
        try:
            return Path(_resolve_rules_file_path()).stat().st_mtime
        except FileNotFoundError:
            return None
        except OSError as e:
            logger.debug(f"Failed to stat rules file: {e}")
            return None

    def _refresh_rules_summary() -> None:
        nonlocal rules_cache, rules_wrapped, rules_path
        for widget in rules_list_frame.winfo_children():
            widget.destroy()

        rules_cache, rules_wrapped, rules_path = _load_rules_file_for_ui()
        rules_path_var.set(rules_path)

        if not rules_cache:
            empty_label = ttk.Label(rules_list_frame, text="No rules found", foreground="gray")
            empty_label.pack(anchor="w", padx=4, pady=4)
            return

        def _format_rule_summary(rule: dict) -> str:
            op_map = {
                "eq": "=",
                "ne": "!=",
                "in": "in",
                "nin": "not in",
                "lt": "<",
                "lte": "<=",
                "gt": ">",
                "gte": ">=",
                "contains": "contains",
                "exists": "exists",
            }

            def _format_value(val: Any) -> str:
                if isinstance(val, bool):
                    return "true" if val else "false"
                if isinstance(val, list):
                    return ", ".join(str(v) for v in val)
                return str(val)

            when = rule.get("when", {})
            all_conds = when.get("all", []) if isinstance(when, dict) else []
            any_conds = when.get("any", []) if isinstance(when, dict) else []

            cond_parts = []
            for cond in all_conds:
                if not isinstance(cond, dict):
                    continue
                signal = cond.get("signal", "")
                op = op_map.get(cond.get("op"), cond.get("op", ""))
                value = _format_value(cond.get("value"))
                if signal and op:
                    cond_parts.append(f"{signal} {op} {value}")

            if any_conds:
                any_parts = []
                for cond in any_conds:
                    if not isinstance(cond, dict):
                        continue
                    signal = cond.get("signal", "")
                    op = op_map.get(cond.get("op"), cond.get("op", ""))
                    value = _format_value(cond.get("value"))
                    if signal and op:
                        any_parts.append(f"{signal} {op} {value}")
                if any_parts:
                    cond_parts.append("(" + " OR ".join(any_parts) + ")")

            if cond_parts:
                when_text = "When: " + " AND ".join(cond_parts)
            else:
                when_text = "When: (always)"

            def _format_actions(actions: list[dict]) -> str:
                parts = []
                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    if "vkb_set_shift" in action:
                        tokens = action["vkb_set_shift"]
                        tokens = tokens if isinstance(tokens, list) else [tokens]
                        parts.append("Set " + ", ".join(str(t) for t in tokens))
                    elif "vkb_clear_shift" in action:
                        tokens = action["vkb_clear_shift"]
                        tokens = tokens if isinstance(tokens, list) else [tokens]
                        parts.append("Clear " + ", ".join(str(t) for t in tokens))
                    elif "log" in action:
                        parts.append(f"Log '{action['log']}'")
                return "; ".join(parts)

            then_text = "Then: " + _format_actions(rule.get("then", []))
            else_text = "Else: " + _format_actions(rule.get("else", []))

            summary = " | ".join(
                part for part in [when_text, then_text, else_text] if part and not part.endswith(": ")
            )
            if len(summary) > 160:
                summary = summary[:157].rstrip() + "..."
            return summary

        for idx, rule in enumerate(rules_cache):
            item_frame = ttk.Frame(rules_list_frame)
            item_frame.pack(fill=tk.X, pady=2)

            actions_frame = ttk.Frame(item_frame)
            actions_frame.pack(side=tk.LEFT, padx=(0, 6))

            edit_button = ttk.Button(actions_frame, text="✎", width=3, command=lambda i=idx: _edit_rule(i))
            edit_button.pack(side=tk.LEFT, padx=1)
            _ToolTip(edit_button, "Edit rule")

            dup_button = ttk.Button(actions_frame, text="⎘", width=3, command=lambda i=idx: _duplicate_rule(i))
            dup_button.pack(side=tk.LEFT, padx=1)
            _ToolTip(dup_button, "Duplicate rule")

            del_button = ttk.Button(actions_frame, text="🗑", width=3, command=lambda i=idx: _delete_rule(i))
            del_button.pack(side=tk.LEFT, padx=1)
            _ToolTip(del_button, "Delete rule")

            enabled_var = tk.BooleanVar(value=rule.get("enabled", True))
            enabled_button = ttk.Checkbutton(
                item_frame,
                variable=enabled_var,
                command=lambda i=idx, var=enabled_var: _toggle_rule_enabled(i, var),
            )
            enabled_button.pack(side=tk.LEFT, padx=(0, 4))
            _ToolTip(enabled_button, "Enable or disable rule")

            title = rule.get("title", rule.get("id", "Untitled"))
            rule_id = rule.get("id", "")
            title_text = f"{title} [{rule_id}]" if rule_id else title
            summary = _format_rule_summary(rule)
            title_label = ttk.Label(item_frame, text=f"{title_text} - {summary}" if summary else title_text)
            title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    rules_frame = ttk.LabelFrame(settings_tab, text="Rules", padding=6)
    rules_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=(6, 4))
    rules_frame.columnconfigure(0, weight=1)
    rules_frame.rowconfigure(1, weight=1)

    rules_header = ttk.Frame(rules_frame)
    rules_header.grid(row=0, column=0, sticky="ew")
    rules_header.columnconfigure(1, weight=1)

    ttk.Label(rules_header, text="Rules file:").grid(row=0, column=0, sticky="w", padx=(0, 6))
    _refresh_rules_path()
    ttk.Label(rules_header, textvariable=rules_path_var, foreground="gray").grid(
        row=0, column=1, sticky="w"
    )

    list_container = ttk.Frame(rules_frame)
    list_container.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

    list_canvas = tk.Canvas(list_container, highlightthickness=0, height=180)
    list_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=list_canvas.yview)
    rules_list_frame = ttk.Frame(list_canvas)

    list_window = list_canvas.create_window((0, 0), window=rules_list_frame, anchor="nw")

    def _on_rules_frame_configure(event=None):
        list_canvas.configure(scrollregion=list_canvas.bbox("all"))

    def _on_rules_canvas_configure(event):
        list_canvas.itemconfigure(list_window, width=event.width)

    rules_list_frame.bind("<Configure>", _on_rules_frame_configure)
    list_canvas.bind("<Configure>", _on_rules_canvas_configure)

    list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    list_canvas.configure(yscrollcommand=list_scrollbar.set)

    _refresh_rules_summary()

    def _poll_rules_changes() -> None:
        nonlocal rules_mtime
        if not frame.winfo_exists():
            return
        current_mtime = _get_rules_mtime()
        if current_mtime != rules_mtime:
            rules_mtime = current_mtime
            _refresh_rules_summary()
        frame.after(rules_poll_ms, _poll_rules_changes)

    rules_mtime = _get_rules_mtime()
    frame.after(rules_poll_ms, _poll_rules_changes)

    # Events Tab - Unregistered Events Tracker
    events_tab.columnconfigure(0, weight=1)
    events_tab.rowconfigure(3, weight=1)

    ttk.Label(events_tab, text="Unregistered Events", font=("TkDefaultFont", 12, "bold")).grid(
        row=0, column=0, sticky="w", padx=8, pady=(8, 4)
    )
    ttk.Label(
        events_tab,
        text="Events received that are not registered in signals_catalog.json\nThese may need to be added to the catalog for future use."
    ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

    # Variables for events display
    events_status_var = tk.StringVar(value="")
    events_count_var = tk.StringVar(value="No unregistered events")

    def _refresh_unregistered_events() -> None:
        """Refresh the unregistered events list."""
        if not _event_handler:
            events_count_var.set("Event handler not initialized")
            return

        try:
            # Refresh against catalog
            removed_count = _event_handler.refresh_unregistered_events_against_catalog()
            total_count = _event_handler.get_unregistered_events_count()

            if removed_count > 0:
                events_status_var.set(f"Refreshed: {removed_count} event(s) now in catalog removed")
            else:
                events_status_var.set("Catalog check complete")

            if total_count == 0:
                events_count_var.set("No unregistered events tracked")
            elif total_count == 1:
                events_count_var.set("1 unregistered event tracked")
            else:
                events_count_var.set(f"{total_count} unregistered events tracked")
        except Exception as e:
            logger.error(f"Error refreshing unregistered events: {e}", exc_info=True)
            events_status_var.set(f"Error: {e}")

    def _clear_all_unregistered_events() -> None:
        """Clear all unregistered events."""
        if not _event_handler:
            events_status_var.set("Event handler not initialized")
            return

        try:
            from tkinter import messagebox

            if messagebox.askyesno(
                "Clear All Unregistered Events",
                "Are you sure you want to clear all tracked unregistered events?\nThis cannot be undone.",
            ):
                count = _event_handler.clear_all_unregistered_events()
                events_status_var.set(f"Cleared {count} event(s)")
                _refresh_unregistered_events()
        except Exception as e:
            logger.error(f"Error clearing unregistered events: {e}", exc_info=True)
            events_status_var.set(f"Error: {e}")

    def _show_unregistered_events_list() -> None:
        """Display detailed list of unregistered events."""
        if not _event_handler:
            from tkinter import messagebox

            messagebox.showwarning("Not Ready", "Event handler not initialized")
            return

        try:
            events = _event_handler.get_unregistered_events()

            if not events:
                from tkinter import messagebox

                messagebox.showinfo("No Events", "No unregistered events currently tracked")
                return

            # Create a new window to display events
            details_window = tk.Toplevel(frame)
            details_window.title("Unregistered Events Details")
            details_window.geometry("800x500")

            # Create frame with scrollbar
            canvas_frame = ttk.Frame(details_window)
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

            canvas = tk.Canvas(canvas_frame)
            scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Add events to the scrollable frame
            for i, event in enumerate(events):
                event_frame = ttk.LabelFrame(
                    scrollable_frame,
                    text=f"{event['event_type']} (from {event['source']})",
                    padding=6,
                )
                event_frame.pack(fill=tk.X, padx=4, pady=4)

                # Event details
                info_text = f"First seen: {event.get('first_seen', 'unknown')}\n"
                info_text += f"Last seen: {event.get('last_seen', 'unknown')}\n"
                info_text += f"Occurrences: {event.get('occurrences', 0)}"

                ttk.Label(event_frame, text=info_text, justify=tk.LEFT).pack(anchor="w", pady=(0, 4))

                # Sample data preview
                ttk.Label(event_frame, text="Sample data:", font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
                sample_text = tk.Text(event_frame, height=4, width=80, wrap=tk.WORD)
                sample_text.pack(anchor="w", fill=tk.BOTH, expand=True)

                sample_data = event.get("sample_data", {})
                sample_str = json.dumps(sample_data, indent=2)
                sample_text.insert("1.0", sample_str)
                sample_text.config(state=tk.DISABLED)

            canvas.pack(side="left", fill=tk.BOTH, expand=True)
            scrollbar.pack(side="right", fill="y")

        except Exception as e:
            logger.error(f"Error showing unregistered events details: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Error", f"Failed to display events: {e}")

    # Events tab content
    ttk.Label(events_tab, textvariable=events_count_var, font=("TkDefaultFont", 10, "bold")).grid(
        row=2, column=0, sticky="w", padx=8, pady=(6, 4)
    )

    events_buttons = ttk.Frame(events_tab)
    events_buttons.grid(row=3, column=0, sticky="nw", padx=8, pady=(0, 6))

    ttk.Button(events_buttons, text="View Details", command=_show_unregistered_events_list).grid(
        row=0, column=0, sticky="w", padx=(0, 6)
    )
    ttk.Button(events_buttons, text="Refresh", command=_refresh_unregistered_events).grid(
        row=0, column=1, sticky="w", padx=(0, 6)
    )
    ttk.Button(events_buttons, text="Clear All", command=_clear_all_unregistered_events).grid(
        row=0, column=2, sticky="w"
    )

    ttk.Label(events_tab, textvariable=events_status_var, foreground="gray").grid(
        row=4, column=0, sticky="w", padx=8, pady=(0, 6)
    )

    # Initial population of event counts
    _refresh_unregistered_events()

    return frame

