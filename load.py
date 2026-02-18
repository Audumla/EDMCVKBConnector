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

# UI Icon constants for consistent, pretty buttons across all panels
ICON_EDIT = "✎"       # Edit icon (pencil)
ICON_DELETE = "✕"     # Delete/X icon
ICON_DUPLICATE = "↻"   # Duplicate/circular arrow icon
ICON_ADD = "⊕"        # Add icon (circled plus)
ICON_UP = "▲"         # Move up icon (triangle)
ICON_DOWN = "▼"       # Move down icon (triangle)

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
_event_recorder = None
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
    global _event_handler, _event_recorder

    try:
        logger.info("VKB Connector stopping")
        if _event_recorder and _event_recorder.is_recording:
            _event_recorder.stop()
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

    # Define TwoStateCheckbutton class here so it has access to tk
    class TwoStateCheckbutton(tk.Canvas):
        """A 2-state checkbox widget with states: OFF (empty square) and ON (checkmark)."""
        
        def __init__(self, parent, text="", variable=None, command=None, **kwargs):
            """
            Initialize 2-state checkbox.
            
            Args:
                parent: Parent widget
                text: Label text
                variable: tk.BooleanVar to track state (True=on, False=off)
                command: Callback when state changes
            """
            super().__init__(parent, width=20, height=20, highlightthickness=0, bg="white", **kwargs)
            self.text = text
            self.variable = variable if variable else tk.BooleanVar(value=False)
            self.command = command
            self.label_font = ("TkDefaultFont", 10)
            
            self.bind("<Button-1>", self._on_click)
            self._draw()
        
        def _on_click(self, event=None):
            """Toggle state on click."""
            self.variable.set(not self.variable.get())
            self._draw()
            if self.command:
                self.command()
        
        def _draw(self):
            """Draw the checkbox in current state."""
            self.delete("all")
            is_checked = self.variable.get()
            
            # Box outline
            box_color = "#333"
            if is_checked:
                box_fill = "#27ae60"
                symbol = "✓"
                symbol_color = "white"
            else:
                box_fill = "white"
                symbol = ""
                symbol_color = "#333"
            
            # Draw box
            self.create_rectangle(2, 2, 16, 16, fill=box_fill, outline=box_color, width=1)
            
            # Draw symbol
            if symbol:
                self.create_text(9, 9, text=symbol, font=self.label_font, fill=symbol_color)
            
            # Draw label
            if self.text:
                self.create_text(22, 9, text=self.text, anchor="w", font=self.label_font)

    frame = nb.Frame(parent)

    notebook = ttk.Notebook(frame)
    notebook.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    settings_tab = ttk.Frame(notebook)
    events_tab = ttk.Frame(notebook)
    notebook.add(settings_tab, text="Settings")
    notebook.add(events_tab, text="Unregistered Events")

    settings_tab.columnconfigure(0, weight=0)  # Don't expand VKB-Link
    settings_tab.columnconfigure(1, weight=1)  # Expand shift flags box

    # Helper to create small colored icon buttons for rules list
    def _make_small_icon_button(parent, icon_text, color_key, command, tooltip_text=""):
        """Create a small colored button with consistent sizing."""
        colors = {
            "edit": {"bg": "#3498db", "fg": "white"},
            "duplicate": {"bg": "#8e44ad", "fg": "white"},
            "delete": {"bg": "#e74c3c", "fg": "white"},
        }
        colors_dict = colors.get(color_key, {"bg": "#95a5a6", "fg": "white"})
        btn = tk.Button(
            parent,
            text=icon_text,
            command=command,
            bg=colors_dict["bg"],
            fg=colors_dict["fg"],
            width=2,
            height=1,
            padx=2,
            pady=2,
            font=("TkDefaultFont", 8),
            relief=tk.FLAT,
            bd=0,
            activebackground=colors_dict["bg"],
            activeforeground=colors_dict["fg"],
        )
        if tooltip_text:
            _ToolTip(btn, tooltip_text)
        return btn

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

    # Track initial values for change detection
    initial_host = host_var.get()
    initial_port = port_var.get()
    initial_shift_bitmap = current_shift
    initial_subshift_bitmap = current_subshift
    changes_made_var = tk.BooleanVar(value=False)

    def _check_prefs_changed(*args):
        """Check if any preferences have changed and update status indicator."""
        current_host = host_var.get()
        current_port = port_var.get()
        current_shift, current_subshift = _compute_test_shift_bitmaps_from_ui()
        
        has_changes = (
            current_host != initial_host or
            current_port != initial_port or
            current_shift != initial_shift_bitmap or
            current_subshift != initial_subshift_bitmap
        )
        
        changes_made_var.set(has_changes)
        if has_changes:
            unsaved_status_var.set("✚ Changes made")
        else:
            unsaved_status_var.set("")
    
    # Trace all preference changes
    host_var.trace_add("write", _check_prefs_changed)
    port_var.trace_add("write", _check_prefs_changed)
    for var in shift_vars + subshift_vars:
        var.trace_add("write", _check_prefs_changed)

    _prefs_vars = {
        "vkb_host": host_var,
        "vkb_port": port_var,
        "test_shift_vars": shift_vars,
        "test_subshift_vars": subshift_vars,
    }

    # Status variable for unsaved changes indicator
    unsaved_status_var = tk.StringVar(value="")

    vkb_link_frame = ttk.LabelFrame(settings_tab, text="VKB-Link", padding=6)
    vkb_link_frame.grid(row=0, column=0, sticky="w", padx=(4, 6), pady=2)
    vkb_link_frame.columnconfigure(1, weight=0)

    ttk.Label(vkb_link_frame, text="Host:").grid(row=0, column=0, sticky="w", padx=(4, 4), pady=2)
    ttk.Entry(vkb_link_frame, textvariable=host_var, width=12).grid(row=0, column=1, sticky="w", padx=(0, 12), pady=2)

    ttk.Label(vkb_link_frame, text="Port:").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=2)
    ttk.Entry(vkb_link_frame, textvariable=port_var, width=6).grid(row=0, column=3, sticky="w", padx=4, pady=2)

    # --- Connection status row ---
    vkb_status_var = tk.StringVar(value="Checking...")
    vkb_status_label = tk.Label(vkb_link_frame, textvariable=vkb_status_var, foreground="gray",
                                font=("TkDefaultFont", 8))
    vkb_status_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=(4, 4), pady=(2, 0))

    vkb_ini_path_saved = _config.get("vkb_ini_path", "") if _config else ""

    def _configure_vkb_ini():
        """Open file dialog to locate VKB-Link INI and write TCP section."""
        nonlocal vkb_ini_path_saved
        from tkinter import filedialog
        import configparser

        initial_dir = ""
        if vkb_ini_path_saved:
            ini_p = Path(vkb_ini_path_saved)
            if ini_p.parent.exists():
                initial_dir = str(ini_p.parent)

        ini_path = filedialog.askopenfilename(
            title="Select VKB-Link INI file",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            initialdir=initial_dir or None,
        )
        if not ini_path:
            return

        try:
            cp = configparser.ConfigParser()
            cp.read(ini_path, encoding="utf-8")

            if "TCP" not in cp:
                cp.add_section("TCP")
            cp.set("TCP", "Adress", host_var.get())
            cp.set("TCP", "Port", port_var.get())

            with open(ini_path, "w", encoding="utf-8") as f:
                cp.write(f)

            vkb_ini_path_saved = ini_path
            if _config:
                _config.set("vkb_ini_path", ini_path)
            vkb_status_var.set(f"INI updated: {Path(ini_path).name}")
            vkb_status_label.configure(foreground="#27ae60")
            logger.info(f"Updated VKB-Link INI: {ini_path}")
        except Exception as e:
            vkb_status_var.set(f"INI error: {e}")
            vkb_status_label.configure(foreground="#e74c3c")
            logger.error(f"Failed to update VKB-Link INI: {e}")

    ini_btn = tk.Button(
        vkb_link_frame,
        text="Configure INI...",
        command=_configure_vkb_ini,
        bg="#3498db",
        fg="white",
        padx=6,
        pady=4,
        font=("TkDefaultFont", 8, "bold"),
        relief=tk.RAISED,
        bd=1,
    )
    # Initially hidden; shown when disconnected
    ini_btn_visible = [False]

    def _poll_vkb_status():
        """Poll VKB-Link connection status and update UI."""
        if not frame.winfo_exists():
            return
        connected = False
        if _event_handler:
            try:
                connected = _event_handler.vkb_client.connected
            except Exception:
                pass

        if connected:
            vkb_status_var.set("Connected")
            vkb_status_label.configure(foreground="#27ae60")
            if ini_btn_visible[0]:
                ini_btn.grid_forget()
                ini_btn_visible[0] = False
        else:
            vkb_status_var.set("Disconnected - retrying...")
            vkb_status_label.configure(foreground="#e74c3c")
            if not ini_btn_visible[0]:
                ini_btn.grid(row=1, column=2, columnspan=2, sticky="e", padx=(4, 4), pady=(2, 0))
                ini_btn_visible[0] = True

        frame.after(2000, _poll_vkb_status)

    # Start polling
    frame.after(500, _poll_vkb_status)

    static_shift_frame = ttk.LabelFrame(settings_tab, text="Static Shift Flags", padding=8)
    static_shift_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 4), pady=2, rowspan=2)
    
    # Configure columns for shift flags
    static_shift_frame.columnconfigure(0, weight=0)  # Shift label
    for col in range(1, 11):
        static_shift_frame.columnconfigure(col, weight=0)

    # All shift flags on one row
    ttk.Label(static_shift_frame, text="Shift:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
    for i, shift_code in enumerate((1, 2)):
        cb = TwoStateCheckbutton(
            static_shift_frame,
            text=f"{shift_code}",
            variable=shift_vars[i],
            command=_apply_test_shift_from_ui,
        )
        cb.grid(row=0, column=1 + i, sticky="w", padx=2, pady=2)
    
    # SubShift label and checkboxes on same row
    ttk.Label(static_shift_frame, text="SubShift:").grid(row=0, column=3, sticky="w", padx=(8, 4), pady=2)
    for i in range(7):
        cb = TwoStateCheckbutton(
            static_shift_frame,
            text=f"{i + 1}",
            variable=subshift_vars[i],
            command=_apply_test_shift_from_ui,
        )
        cb.grid(row=0, column=4 + i, sticky="w", padx=2, pady=2)

    settings_tab.rowconfigure(2, weight=1)

    # --- Event Recording section ---
    recording_frame = ttk.LabelFrame(settings_tab, text="Event Recording", padding=6)
    recording_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2))
    recording_frame.columnconfigure(1, weight=1)

    rec_status_var = tk.StringVar(value="Idle")
    rec_count_var = tk.StringVar(value="Events: 0")
    rec_poll_id = [None]  # mutable ref for after() cancel

    def _open_recorded_file():
        """Open the recorded events file with default application."""
        if _event_recorder and _event_recorder.output_path:
            try:
                file_path = _event_recorder.output_path
                if sys.platform == "win32":
                    import subprocess
                    subprocess.Popen(["explorer", "/select,", str(file_path)])
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.Popen(["open", "-R", str(file_path)])
                else:  # Linux
                    import subprocess
                    subprocess.Popen(["xdg-open", str(file_path.parent)])
            except Exception as e:
                logger.error(f"Failed to open recorded file: {e}")

    def _toggle_recording():
        global _event_recorder
        if _event_recorder and _event_recorder.is_recording:
            # Stop
            _event_recorder.stop()
            rec_btn.configure(text="Start Recording", bg="#27ae60")
            if _event_recorder.output_path:
                full_path = str(_event_recorder.output_path)
                rec_status_var.set(f"Stopped. File: {full_path}")
            else:
                rec_status_var.set("Stopped.")
            _cancel_rec_poll()
        else:
            # Start
            if not _event_recorder:
                from edmcruleengine.event_recorder import EventRecorder
                _event_recorder = EventRecorder()
            # Sync anonymization settings before starting
            _event_recorder.anonymize = anon_enabled_var.get()
            _event_recorder.mock_commander = mock_cmdr_var.get() or "CMDR_Redacted"
            _event_recorder.mock_fid = mock_fid_var.get() or "F0000000"
            output_dir = Path(_plugin_dir) if _plugin_dir else Path(__file__).parent
            output_file = output_dir / "recorded_events.jsonl"
            try:
                _event_recorder.start(output_file)
                rec_btn.configure(text="Stop Recording", bg="#e74c3c")
                rec_status_var.set("Recording...")
                rec_count_var.set("Events: 0")
                _schedule_rec_poll()
            except Exception as e:
                rec_status_var.set(f"Error: {e}")

    def _update_rec_status():
        if _event_recorder and _event_recorder.is_recording:
            last = _event_recorder.last_event_type
            status = f"Recording... (last: {last})" if last else "Recording..."
            rec_status_var.set(status)
            rec_count_var.set(f"Events: {_event_recorder.event_count}")
            _schedule_rec_poll()

    def _schedule_rec_poll():
        if frame.winfo_exists():
            rec_poll_id[0] = frame.after(500, _update_rec_status)

    def _cancel_rec_poll():
        if rec_poll_id[0] is not None:
            try:
                frame.after_cancel(rec_poll_id[0])
            except Exception:
                pass
            rec_poll_id[0] = None

    # Button: green Start, toggles to red Stop
    rec_btn = tk.Button(
        recording_frame,
        text="Start Recording",
        command=_toggle_recording,
        bg="#27ae60",
        fg="white",
        padx=10,
        pady=4,
        font=("TkDefaultFont", 9),
        relief=tk.RAISED,
        bd=1,
    )
    rec_btn.grid(row=0, column=0, sticky="w", padx=(0, 8))

    # Status label (middle, expands) - clickable when showing file path
    status_label = tk.Label(recording_frame, textvariable=rec_status_var, foreground="gray")
    status_label.grid(row=0, column=1, sticky="w", padx=(0, 8))

    # Make clickable: change cursor and color on hover
    def _on_status_enter(event):
        if _event_recorder and _event_recorder.is_recording:
            return  # Don't change appearance while recording
        if "File:" in rec_status_var.get():
            status_label.configure(foreground="#0066cc", cursor="hand2", font=("TkDefaultFont", 9, "underline"))

    def _on_status_leave(event):
        if _event_recorder and _event_recorder.is_recording:
            status_label.configure(foreground="gray", cursor="arrow", font=("TkDefaultFont", 9))
        else:
            status_label.configure(foreground="gray", cursor="arrow", font=("TkDefaultFont", 9))

    status_label.bind("<Enter>", _on_status_enter)
    status_label.bind("<Leave>", _on_status_leave)
    status_label.bind("<Button-1>", lambda e: _open_recorded_file())

    # Event count (right-aligned)
    ttk.Label(recording_frame, textvariable=rec_count_var, foreground="gray").grid(
        row=0, column=2, sticky="e"
    )

    # --- Anonymization controls (row 1 of recording frame) ---
    anon_enabled_var = tk.BooleanVar(value=_config.get("recorder_anonymize", True) if _config else True)
    mock_cmdr_var = tk.StringVar(value=_config.get("recorder_mock_commander", "CMDR_Redacted") if _config else "CMDR_Redacted")
    mock_fid_var = tk.StringVar(value=_config.get("recorder_mock_fid", "F0000000") if _config else "F0000000")

    ttk.Checkbutton(recording_frame, text="Anonymize", variable=anon_enabled_var).grid(
        row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0)
    )

    anon_fields = ttk.Frame(recording_frame)
    anon_fields.grid(row=1, column=1, columnspan=2, sticky="w", pady=(4, 0))

    ttk.Label(anon_fields, text="Mock CMDR:").pack(side=tk.LEFT, padx=(0, 4))
    ttk.Entry(anon_fields, textvariable=mock_cmdr_var, width=14).pack(side=tk.LEFT, padx=(0, 10))
    ttk.Label(anon_fields, text="Mock FID:").pack(side=tk.LEFT, padx=(0, 4))
    ttk.Entry(anon_fields, textvariable=mock_fid_var, width=10).pack(side=tk.LEFT)

    def _sync_recorder_anon_settings():
        """Push current anonymization UI values to the recorder instance."""
        if _event_recorder:
            _event_recorder.anonymize = anon_enabled_var.get()
            _event_recorder.mock_commander = mock_cmdr_var.get() or "CMDR_Redacted"
            _event_recorder.mock_fid = mock_fid_var.get() or "F0000000"
        if _config:
            _config.set("recorder_anonymize", anon_enabled_var.get())
            _config.set("recorder_mock_commander", mock_cmdr_var.get())
            _config.set("recorder_mock_fid", mock_fid_var.get())

    anon_enabled_var.trace_add("write", lambda *a: _sync_recorder_anon_settings())
    mock_cmdr_var.trace_add("write", lambda *a: _sync_recorder_anon_settings())
    mock_fid_var.trace_add("write", lambda *a: _sync_recorder_anon_settings())

    # Apply saved settings to recorder if it exists
    _sync_recorder_anon_settings()

    # If recorder was already running (e.g. prefs reopened), reflect state
    if _event_recorder and _event_recorder.is_recording:
        rec_btn.configure(text="Stop Recording", bg="#e74c3c")
        _update_rec_status()

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

            edit_button = _make_small_icon_button(actions_frame, ICON_EDIT, "edit", lambda i=idx: _edit_rule(i), "Edit rule")
            edit_button.pack(side=tk.LEFT, padx=1)

            dup_button = _make_small_icon_button(actions_frame, ICON_DUPLICATE, "duplicate", lambda i=idx: _duplicate_rule(i), "Duplicate rule")
            dup_button.pack(side=tk.LEFT, padx=1)

            del_button = _make_small_icon_button(actions_frame, ICON_DELETE, "delete", lambda i=idx: _delete_rule(i), "Delete rule")
            del_button.pack(side=tk.LEFT, padx=1)

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

    # Add "New Rule" button on the left
    new_rule_btn = tk.Button(
        rules_header,
        text=f"{ICON_ADD} New Rule",
        command=lambda: _open_rules_editor(initial_rule_index=None),
        bg="#27ae60",
        fg="white",
        padx=10,
        pady=4,
        font=("TkDefaultFont", 9, "bold"),
        relief=tk.RAISED,
        bd=1
    )
    new_rule_btn.grid(row=0, column=0, sticky="w", padx=(0, 8))
    _ToolTip(new_rule_btn, "Create a new rule")
    
    # Rules file path on the right
    ttk.Label(rules_header, text="Rules file:").grid(row=0, column=2, sticky="e", padx=(0, 6))
    _refresh_rules_path()
    ttk.Label(rules_header, textvariable=rules_path_var, foreground="gray").grid(
        row=0, column=3, sticky="e"
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

    # Status indicator for unsaved changes in preferences
    ttk.Label(settings_tab, textvariable=unsaved_status_var, foreground="#e74c3c", font=("TkDefaultFont", 9)).grid(
        row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0)
    )

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
        """Display detailed list of unregistered events with collapsible JSON."""
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
            details_window.geometry("900x600")

            # Create frame with scrollbar
            canvas_frame = ttk.Frame(details_window)
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

            canvas = tk.Canvas(canvas_frame, highlightthickness=0)
            scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Add events to the scrollable frame
            for event in events:
                event_type = event.get('event_type', 'Unknown')
                source = event.get('source', 'unknown')
                first_seen = event.get('first_seen')
                last_seen = event.get('last_seen')
                sample_data = event.get('sample_data', {})
                occurrences = event.get('occurrences', 0)
                
                # Determine what kind of data is missing
                data_info = ""
                if source == 'journal':
                    # For journal events, show the event data structure hint
                    if isinstance(sample_data, dict):
                        # Get key fields that might be notable
                        keys = list(sample_data.keys())
                        if keys:
                            # Show first few important-looking keys
                            important_keys = [k for k in keys if not k.startswith('_')][:2]
                            if important_keys:
                                data_info = f"Fields: {', '.join(important_keys)}"
                    if not data_info:
                        data_info = "Journal event"
                elif source == 'flags':
                    # For flags, show bit info
                    if isinstance(sample_data, dict) and 'bit' in sample_data:
                        data_info = f"Bit {sample_data['bit']}"
                    else:
                        data_info = "Flags value"
                elif source == 'dashboard':
                    # For dashboard, show the field name if available
                    if isinstance(sample_data, dict):
                        keys = list(sample_data.keys())
                        if keys:
                            data_info = f"Field: {keys[0]}"
                    if not data_info:
                        data_info = "Dashboard field"
                
                # Create event frame with title section
                event_frame = ttk.LabelFrame(
                    scrollable_frame,
                    padding=8,
                )
                event_frame.pack(fill=tk.X, padx=4, pady=4)
                
                # Title with event name, summary info, and right-aligned occurrences + details button
                title_frame = ttk.Frame(event_frame)
                title_frame.pack(fill=tk.X, pady=(0, 6))
                
                # Left side: event name and data info
                left_frame = ttk.Frame(title_frame)
                left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                ttk.Label(
                    left_frame,
                    text=event_type,
                    font=("TkDefaultFont", 11, "bold"),
                    foreground="#e74c3c"
                ).pack(side=tk.LEFT, padx=(0, 6))
                
                if data_info:
                    ttk.Label(
                        left_frame,
                        text=data_info,
                        foreground="#27ae60",
                        font=("TkDefaultFont", 10)
                    ).pack(side=tk.LEFT, padx=(0, 6))
                
                ttk.Label(
                    left_frame,
                    text=f"[{source}]",
                    foreground="gray"
                ).pack(side=tk.LEFT)
                
                # Right side: occurrences count + details button (both on same line)
                right_frame = ttk.Frame(title_frame)
                right_frame.pack(side=tk.RIGHT)
                
                ttk.Label(
                    right_frame,
                    text=f"Occurrences: {occurrences}",
                    foreground="navy",
                    font=("TkDefaultFont", 9)
                ).pack(side=tk.LEFT, padx=(0, 8))
                
                # Use a container to hold details and make it toggleable
                details_visible_var = tk.BooleanVar(value=False)
                details_container = ttk.Frame(event_frame)
                details_container.pack(fill=tk.BOTH, expand=True)
                
                toggle_btn_text_var = tk.StringVar(value="Show Details ▼")
                
                def create_toggle_callback(visible_var, btn_text_var, details_frame):
                    def toggle_details():
                        if visible_var.get():
                            details_frame.pack_forget()
                            visible_var.set(False)
                            btn_text_var.set("Show Details ▼")
                        else:
                            details_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
                            visible_var.set(True)
                            btn_text_var.set("Hide Details ▲")
                    return toggle_details
                
                # Create button and add to right frame
                toggle_btn = tk.Button(
                    right_frame,
                    textvariable=toggle_btn_text_var,
                    command=None,  # Will be set after details frame is created
                    bg="#3498db",
                    fg="white",
                    padx=10,
                    pady=4,
                    font=("TkDefaultFont", 9),
                    relief=tk.RAISED,
                    bd=1
                )
                toggle_btn.pack(side=tk.LEFT)
                
                # Details container (initially hidden)
                details_frame = ttk.Frame(event_frame)
                
                # Collapsible JSON tree view
                tree_frame = ttk.Frame(details_frame)
                tree_frame.pack(fill=tk.BOTH, expand=True)
                
                tree = ttk.Treeview(tree_frame, height=8, show="tree")
                tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=tree_scrollbar.set)
                
                # Check if a key is a timestamp field
                def is_timestamp_field(key):
                    """Check if a field name indicates it's a timestamp."""
                    key_lower = str(key).lower()
                    timestamp_keywords = ['time', 'timestamp', 'date', 'epoch']
                    return any(kw in key_lower for kw in timestamp_keywords)
                
                # Populate tree with JSON data (excluding timestamps)
                def populate_tree(parent_node, data, max_depth=10):
                    """Recursively populate tree with JSON data, excluding timestamp fields."""
                    if max_depth <= 0:
                        return
                    
                    if isinstance(data, dict):
                        for key, value in data.items():
                            # Skip timestamp fields
                            if is_timestamp_field(key):
                                continue
                            
                            if isinstance(value, (dict, list)):
                                node = tree.insert(parent_node, "end", text=f"{key}: {{...}}", open=False)
                                populate_tree(node, value, max_depth - 1)
                            else:
                                value_str = str(value)[:50]  # Limit display length
                                if len(str(value)) > 50:
                                    value_str += "..."
                                tree.insert(parent_node, "end", text=f"{key}: {value_str}")
                    elif isinstance(data, list):
                        for i, item in enumerate(data):
                            if isinstance(item, (dict, list)):
                                node = tree.insert(parent_node, "end", text=f"[{i}]: {{...}}", open=False)
                                populate_tree(node, item, max_depth - 1)
                            else:
                                item_str = str(item)[:50]
                                if len(str(item)) > 50:
                                    item_str += "..."
                                tree.insert(parent_node, "end", text=f"[{i}]: {item_str}")
                
                # Populate tree with root-level items (parent_node = "")
                populate_tree("", sample_data)
                
                tree.pack(side="left", fill=tk.BOTH, expand=True)
                tree_scrollbar.pack(side="right", fill="y")
                
                # Now set the toggle callback
                toggle_btn.config(command=create_toggle_callback(details_visible_var, toggle_btn_text_var, details_frame))

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

