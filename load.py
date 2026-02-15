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

# Plugin metadata
VERSION = "0.1.0"  # Required by EDMC standards for semantic versioning

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
        from edmcruleengine import Config, EventHandler

        logger.info(f"VKB Connector v{VERSION} starting")

        # Initialize configuration (uses EDMC's stored preferences)
        _config = Config()
        _plugin_dir = plugin_dir

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
    global _prefs_vars, _config

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

    ttk.Label(frame, text="VKB Host:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(frame, textvariable=host_var, width=24).grid(row=0, column=1, sticky="w", padx=4, pady=2)

    ttk.Label(frame, text="VKB Port:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(frame, textvariable=port_var, width=10).grid(row=1, column=1, sticky="w", padx=4, pady=2)

    ttk.Separator(frame, orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 6))

    test_frame = ttk.Frame(frame)
    test_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=2)

    ttk.Label(test_frame, text="Shift:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
    for i, shift_code in enumerate((1, 2)):
        ttk.Checkbutton(
            test_frame,
            text=f"{shift_code}",
            variable=shift_vars[i],
            command=_apply_test_shift_from_ui,
        ).grid(row=0, column=1 + i, sticky="w", padx=2, pady=2)

    ttk.Label(test_frame, text="SubShift:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
    for i in range(7):
        ttk.Checkbutton(
            test_frame,
            text=f"{i + 1}",
            variable=subshift_vars[i],
            command=_apply_test_shift_from_ui,
        ).grid(row=1, column=1 + i, sticky="w", padx=2, pady=2)

    # Rules editor UI
    ttk.Separator(frame, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 6))
    ttk.Label(frame, text="Rules Editor:").grid(row=5, column=0, sticky="w", padx=4, pady=(0, 4))

    rules_frame = ttk.Frame(frame)
    rules_frame.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=4, pady=(0, 4))
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(6, weight=1)
    rules_frame.columnconfigure(1, weight=1)

    rules_list_canvas = tk.Canvas(rules_frame, height=180, width=280, highlightthickness=0)
    rules_list_canvas.grid(row=0, column=0, sticky="nsw")
    rules_scroll = ttk.Scrollbar(rules_frame, orient="vertical", command=rules_list_canvas.yview)
    rules_scroll.grid(row=0, column=0, sticky="nse")
    rules_list_canvas.configure(yscrollcommand=rules_scroll.set)
    rules_list_inner = ttk.Frame(rules_list_canvas)
    rules_list_window = rules_list_canvas.create_window((0, 0), window=rules_list_inner, anchor="nw")

    editor_frame = ttk.Frame(rules_frame)
    editor_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    editor_frame.columnconfigure(0, weight=1)
    editor_frame.rowconfigure(1, weight=1)

    rules_text = tk.Text(editor_frame, height=12, width=64, wrap="none")
    rules_text.grid(row=0, column=0, sticky="nsew")
    rules_text_scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=rules_text.yview)
    rules_text_scroll.grid(row=0, column=1, sticky="ns")
    rules_text.configure(yscrollcommand=rules_text_scroll.set)

    rules_status_var = tk.StringVar(value="")
    ttk.Label(editor_frame, textvariable=rules_status_var).grid(row=1, column=0, sticky="w", pady=(4, 0))

    rules_buttons = ttk.Frame(editor_frame)
    rules_buttons.grid(row=2, column=0, sticky="w", pady=(6, 0))

    rules_data, rules_wrapped, rules_path = _load_rules_file_for_ui()
    rules_state = {
        "rules": rules_data,
        "wrapped": rules_wrapped,
        "path": rules_path,
        "selected": None,
        "selected_var": tk.IntVar(value=-1),
        "enabled_vars": [],
    }

    def _rule_label(rule: dict, idx: int) -> str:
        return str(rule.get("id", f"<rule-{idx}>"))

    def _build_rule_summary(rule: dict) -> str:
        """Build human-readable summary of rule."""
        summary_lines = []
        
        # WHEN section
        when = rule.get("when", {})
        when_parts = []
        
        if isinstance(when, dict):
            source = when.get("source", "")
            event = when.get("event", "")
            
            if source:
                when_parts.append(f"source={source}")
            if event:
                when_parts.append(f"event={event}")
            
            all_blocks = when.get("all", [])
            if all_blocks:
                when_parts.append(f"{len(all_blocks)} ALL condition(s)")
            
            any_blocks = when.get("any", [])
            if any_blocks:
                when_parts.append(f"{len(any_blocks)} ANY condition(s)")
        
        if when_parts:
            summary_lines.append(f"WHEN: {', '.join(when_parts)}")
        else:
            summary_lines.append("WHEN: (no conditions)")
        
        # THEN section
        then = rule.get("then", {})
        then_parts = []
        
        if isinstance(then, dict):
            if "log" in then:
                then_parts.append(f"log: {then['log']}")
            if "vkb_set_shift" in then:
                flags = then["vkb_set_shift"]
                if isinstance(flags, list):
                    then_parts.append(f"set: {', '.join(flags)}")
            if "vkb_clear_shift" in then:
                flags = then["vkb_clear_shift"]
                if isinstance(flags, list):
                    then_parts.append(f"clear: {', '.join(flags)}")
        
        if then_parts:
            summary_lines.append(f"THEN: {'; '.join(then_parts)}")
        else:
            summary_lines.append("THEN: (no actions)")
        
        # ELSE section
        else_block = rule.get("else", {})
        else_parts = []
        
        if isinstance(else_block, dict):
            if "log" in else_block:
                else_parts.append(f"log: {else_block['log']}")
            if "vkb_set_shift" in else_block:
                flags = else_block["vkb_set_shift"]
                if isinstance(flags, list):
                    else_parts.append(f"set: {', '.join(flags)}")
            if "vkb_clear_shift" in else_block:
                flags = else_block["vkb_clear_shift"]
                if isinstance(flags, list):
                    else_parts.append(f"clear: {', '.join(flags)}")
        
        if else_parts:
            summary_lines.append(f"ELSE: {'; '.join(else_parts)}")
        
        return "\n".join(summary_lines)

    def _on_rules_inner_configure(event=None) -> None:
        rules_list_canvas.configure(scrollregion=rules_list_canvas.bbox("all"))

    def _on_rules_canvas_configure(event) -> None:
        rules_list_canvas.itemconfigure(rules_list_window, width=event.width)

    def _set_rule_enabled(idx: int, var) -> None:
        if idx < 0 or idx >= len(rules_state["rules"]):
            return
        rule = dict(rules_state["rules"][idx])
        rule["enabled"] = bool(var.get())
        rules_state["rules"][idx] = rule
        _persist_rules_with_reload("Saved enabled state")

    def _refresh_rules_list(select_idx: Optional[int] = None) -> None:
        for child in rules_list_inner.winfo_children():
            child.destroy()
        rules_state["enabled_vars"] = []

        for i, rule in enumerate(rules_state["rules"]):
            enabled_var = tk.BooleanVar(value=bool(rule.get("enabled", True)))
            rules_state["enabled_vars"].append(enabled_var)
            ttk.Checkbutton(
                rules_list_inner,
                variable=enabled_var,
                command=lambda idx=i, v=enabled_var: _set_rule_enabled(idx, v),
            ).grid(row=i, column=0, sticky="w", padx=(0, 4), pady=1)
            ttk.Radiobutton(
                rules_list_inner,
                text=_rule_label(rule, i),
                value=i,
                variable=rules_state["selected_var"],
                command=lambda idx=i: _load_selected_rule(idx),
            ).grid(row=i, column=1, sticky="w", pady=1)

        if not rules_state["rules"]:
            rules_state["selected"] = None
            rules_state["selected_var"].set(-1)
            _clear_rules_text()
            _on_rules_inner_configure()
            return

        if select_idx is None:
            select_idx = rules_state["selected"] if isinstance(rules_state["selected"], int) else 0
        select_idx = max(0, min(int(select_idx), len(rules_state["rules"]) - 1))
        rules_state["selected_var"].set(select_idx)
        _load_selected_rule(select_idx)
        _on_rules_inner_configure()

    def _clear_rules_text() -> None:
        """Clear the rules text widget (handles read-only state)."""
        rules_text.configure(state="normal")
        rules_text.delete("1.0", tk.END)
        rules_text.configure(state="disabled")

    def _load_selected_rule(idx: int) -> None:
        if idx < 0 or idx >= len(rules_state["rules"]):
            return
        rules_state["selected"] = idx
        rule = rules_state["rules"][idx]
        
        # Enable editing temporarily to update content
        rules_text.configure(state="normal")
        rules_text.delete("1.0", tk.END)
        
        # Show human-readable summary instead of raw JSON
        summary = _build_rule_summary(rule)
        rules_text.insert("1.0", summary)
        
        # Make text read-only
        rules_text.configure(state="disabled")

    def _persist_rules_with_reload(success_msg: str) -> None:
        ok = _save_rules_file_from_ui(
            rules_state["rules"], bool(rules_state["wrapped"]), str(rules_state["path"])
        )
        if not ok:
            rules_status_var.set(f"Failed to save: {rules_state['path']}")
            return
        rules_status_var.set(success_msg)
        if _event_handler:
            _event_handler.reload_rules()

    def _reload_rules_file() -> None:
        data, wrapped, path = _load_rules_file_for_ui()
        rules_state["rules"] = data
        rules_state["wrapped"] = wrapped
        rules_state["path"] = path
        rules_state["selected"] = None
        _refresh_rules_list()
        rules_status_var.set("Reloaded rules from file")
        if _event_handler:
            _event_handler.reload_rules()

    def _next_rule_id() -> str:
        used_ids = {
            str(rule.get("id", "")).strip()
            for rule in rules_state["rules"]
            if isinstance(rule, dict)
        }
        n = 1
        while True:
            candidate = f"rule-{n}"
            if candidate not in used_ids:
                return candidate
            n += 1

    def _new_rule() -> None:
        new_rule = {
            "id": _next_rule_id(),
            "enabled": True,
            "when": {},
            "then": {},
        }
        rules_state["rules"].append(new_rule)
        new_idx = len(rules_state["rules"]) - 1
        _refresh_rules_list(select_idx=new_idx)
        _persist_rules_with_reload("Created new rule")

    def _delete_selected_rule() -> None:
        idx = rules_state["selected"]
        if idx is None or idx < 0 or idx >= len(rules_state["rules"]):
            rules_status_var.set("No rule selected")
            return
        del rules_state["rules"][idx]
        if not rules_state["rules"]:
            rules_state["selected"] = None
            _refresh_rules_list()
        else:
            _refresh_rules_list(select_idx=min(idx, len(rules_state["rules"]) - 1))
        _persist_rules_with_reload("Deleted selected rule")

    def _edit_selected_rule_visual() -> None:
        """Open visual editor for selected rule."""
        idx = rules_state["selected"]
        if idx is None or idx < 0 or idx >= len(rules_state["rules"]):
            rules_status_var.set("No rule selected")
            return
        
        try:
            from edmcruleengine.rule_editor_ui import RuleEditorDialog, load_events_config
            from edmcruleengine.rules_engine import FLAGS, FLAGS2, GUI_FOCUS_NAME_TO_VALUE
            
            # Determine plugin directory for events config
            if _plugin_dir:
                plugin_dir = Path(_plugin_dir)
            else:
                # Fallback: try to determine from this file's location
                plugin_dir = Path(__file__).parent
                logger.warning(f"Plugin dir not set, using file parent: {plugin_dir}")
            
            events_config = load_events_config(plugin_dir)
            
            rule = rules_state["rules"][idx]
            dialog = RuleEditorDialog(frame, rule, events_config, FLAGS, FLAGS2, GUI_FOCUS_NAME_TO_VALUE)
            result = dialog.show()
            
            if result is not None:
                rules_state["rules"][idx] = result
                _refresh_rules_list(select_idx=idx)
                _persist_rules_with_reload("Saved rule via visual editor")
        except Exception as e:
            logger.error(f"Failed to open visual editor: {e}", exc_info=True)
            rules_status_var.set(f"Visual editor error: {e}")

    rules_list_inner.bind("<Configure>", _on_rules_inner_configure)
    rules_list_canvas.bind("<Configure>", _on_rules_canvas_configure)
    ttk.Button(rules_buttons, text="Visual Editor", command=_edit_selected_rule_visual).grid(
        row=0, column=0, sticky="w"
    )
    ttk.Button(rules_buttons, text="New Rule", command=_new_rule).grid(
        row=0, column=1, sticky="w", padx=(6, 0)
    )
    ttk.Button(rules_buttons, text="Delete Rule", command=_delete_selected_rule).grid(
        row=0, column=2, sticky="w", padx=(6, 0)
    )
    ttk.Button(rules_buttons, text="Reload File", command=_reload_rules_file).grid(
        row=0, column=3, sticky="w", padx=(6, 0)
    )

    _refresh_rules_list()

    return frame

