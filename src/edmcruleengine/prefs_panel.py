"""
Preferences panel construction for the EDMC VKB Connector plugin.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .ui_components import (
    apply_colored_button_style,
    ToolTip,
    TwoStateCheckbutton,
    create_colored_button,
    create_icon_action_button,
)


@dataclass(frozen=True)
class PrefsPanelDeps:
    """Runtime dependencies for building the plugin preferences panel."""

    logger: Any
    get_config: Callable[[], Any]
    get_event_handler: Callable[[], Any]
    get_event_recorder: Callable[[], Any]
    set_event_recorder: Callable[[Any], None]
    get_plugin_dir: Callable[[], Optional[str]]
    set_prefs_vars: Callable[[dict[str, Any]], None]
    compute_test_shift_bitmaps_from_ui: Callable[[], tuple[Optional[int], Optional[int]]]
    apply_test_shift_from_ui: Callable[[], None]
    resolve_rules_file_path: Callable[[], str]
    load_rules_file_for_ui: Callable[[], tuple[list[dict], bool, str]]
    save_rules_file_from_ui: Callable[[list[dict], bool, str], bool]
    plugin_root: Path


_config: Any = None
_event_handler: Any = None
_event_recorder: Any = None
_plugin_dir: Optional[str] = None
logger: Any = None


def build_plugin_prefs_panel(parent, cmdr: str, is_beta: bool, deps: PrefsPanelDeps):
    """
    Build the plugin preferences UI for EDMC.

    Uses EDMC's myNotebook widgets when available.
    """
    _ = (cmdr, is_beta)
    global _config, _event_handler, _event_recorder, _plugin_dir, logger
    logger = deps.logger
    _config = deps.get_config()
    _event_handler = deps.get_event_handler()
    _event_recorder = deps.get_event_recorder()
    _plugin_dir = deps.get_plugin_dir()

    # Alias deps callbacks as locals for concise use inside closures
    _compute_test_shift_bitmaps_from_ui = deps.compute_test_shift_bitmaps_from_ui
    _apply_test_shift_from_ui = deps.apply_test_shift_from_ui
    _resolve_rules_file_path = deps.resolve_rules_file_path
    _load_rules_file_for_ui = deps.load_rules_file_for_ui
    _save_rules_file_from_ui = deps.save_rules_file_from_ui

    try:
        import tkinter as tk
        from tkinter import ttk
        import myNotebook as nb
    except Exception:
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
    notebook.add(events_tab, text="Events")

    settings_tab.columnconfigure(0, weight=0)  # Don't expand VKB-Link
    settings_tab.columnconfigure(1, weight=1)  # Expand shift flags box

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

    prefs_vars = {
        "vkb_host": host_var,
        "vkb_port": port_var,
        "test_shift_vars": shift_vars,
        "test_subshift_vars": subshift_vars,
    }
    deps.set_prefs_vars(prefs_vars)

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

    ini_btn = create_colored_button(
        vkb_link_frame,
        text="Configure INI...",
        command=_configure_vkb_ini,
        style="info",
        padx=6,
        pady=4,
        font=("TkDefaultFont", 8, "bold"),
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
    static_shift_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 4), pady=2)
    
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

    settings_tab.rowconfigure(1, weight=1)

    # --- Event Recording section (lives in events_tab, built here for code locality) ---
    recording_frame = ttk.LabelFrame(events_tab, text="Event Recording", padding=6)
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
            rec_btn.configure(text="Start Recording")
            apply_colored_button_style(rec_btn, "success")
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
                deps.set_event_recorder(_event_recorder)
            output_dir = (Path(_plugin_dir) if _plugin_dir else deps.plugin_root) / "recordings"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"recorded_events_{timestamp}.jsonl"
            suffix = 1
            while output_file.exists():
                output_file = output_dir / f"recorded_events_{timestamp}_{suffix:02d}.jsonl"
                suffix += 1
            try:
                _event_recorder.start(output_file)
                rec_btn.configure(text="Stop Recording")
                apply_colored_button_style(rec_btn, "danger")
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
    rec_btn = create_colored_button(
        recording_frame,
        text="Start Recording",
        command=_toggle_recording,
        style="success",
        padx=10,
        pady=4,
        font=("TkDefaultFont", 9),
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

    def _on_status_leave(_event):
        status_label.configure(foreground="gray", cursor="arrow", font=("TkDefaultFont", 9))

    status_label.bind("<Enter>", _on_status_enter)
    status_label.bind("<Leave>", _on_status_leave)
    status_label.bind("<Button-1>", lambda e: _open_recorded_file())

    # Event count (right-aligned)
    ttk.Label(recording_frame, textvariable=rec_count_var, foreground="gray").grid(
        row=0, column=2, sticky="e"
    )

    # Recording frame complete - no anonymization UI (always on with fixed values)


    # If recorder was already running (e.g. prefs reopened), reflect state
    if _event_recorder and _event_recorder.is_recording:
        rec_btn.configure(text="Stop Recording")
        apply_colored_button_style(rec_btn, "danger")
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
            plugin_dir = Path(_plugin_dir) if _plugin_dir else deps.plugin_root
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

            edit_button = create_icon_action_button(
                actions_frame, action="edit", command=lambda i=idx: _edit_rule(i), tooltip_text="Edit rule"
            )
            edit_button.pack(side=tk.LEFT, padx=1)

            dup_button = create_icon_action_button(
                actions_frame,
                action="duplicate",
                command=lambda i=idx: _duplicate_rule(i),
                tooltip_text="Duplicate rule",
            )
            dup_button.pack(side=tk.LEFT, padx=1)

            del_button = create_icon_action_button(
                actions_frame, action="delete", command=lambda i=idx: _delete_rule(i), tooltip_text="Delete rule"
            )
            del_button.pack(side=tk.LEFT, padx=1)

            enabled_var = tk.BooleanVar(value=rule.get("enabled", True))
            enabled_button = ttk.Checkbutton(
                item_frame,
                variable=enabled_var,
                command=lambda i=idx, var=enabled_var: _toggle_rule_enabled(i, var),
            )
            enabled_button.pack(side=tk.LEFT, padx=(0, 4))
            ToolTip(enabled_button, "Enable or disable rule")

            title = rule.get("title", rule.get("id", "Untitled"))
            rule_id = rule.get("id", "")
            title_text = f"{title} [{rule_id}]" if rule_id else title
            summary = _format_rule_summary(rule)
            title_label = ttk.Label(item_frame, text=f"{title_text} - {summary}" if summary else title_text)
            title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    rules_frame = ttk.LabelFrame(settings_tab, text="Rules", padding=6)
    rules_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=(6, 4))
    rules_frame.columnconfigure(0, weight=1)
    rules_frame.rowconfigure(1, weight=1)

    rules_header = ttk.Frame(rules_frame)
    rules_header.grid(row=0, column=0, sticky="ew")
    rules_header.columnconfigure(1, weight=1)

    # Add "New Rule" control on the left: shared add icon + shared text button
    def _open_new_rule_editor() -> None:
        _open_rules_editor(initial_rule_index=None)

    new_rule_action = ttk.Frame(rules_header)
    new_rule_action.grid(row=0, column=0, sticky="w", padx=(0, 8))
    create_icon_action_button(
        new_rule_action,
        action="add",
        command=_open_new_rule_editor,
        tooltip_text="Create a new rule",
    ).pack(side=tk.LEFT, padx=(0, 4))
    new_rule_btn = create_colored_button(
        new_rule_action,
        text="New Rule",
        command=_open_new_rule_editor,
        style="success",
        padx=10,
        pady=4,
        font=("TkDefaultFont", 9, "bold"),
    )
    new_rule_btn.pack(side=tk.LEFT)
    
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
        row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0)
    )

    # Events Tab
    events_tab.columnconfigure(0, weight=1)
    events_tab.rowconfigure(4, weight=1)

    # --- Record section (moved from settings_tab) ---
    recording_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=(6, 2))

    # --- Track unregistered events checkbox ---
    track_unregistered_var = tk.BooleanVar(
        value=bool(_config.get("track_unregistered_events", False)) if _config else False
    )
    if _event_handler:
        _event_handler.track_unregistered_events = track_unregistered_var.get()

    def _on_track_unregistered_changed(*_args):
        enabled = track_unregistered_var.get()
        if _event_handler:
            _event_handler.track_unregistered_events = enabled
        if _config:
            _config.set("track_unregistered_events", enabled)

    track_unregistered_var.trace_add("write", _on_track_unregistered_changed)

    ttk.Checkbutton(
        events_tab,
        text="Capture missed events (track events not in catalog)",
        variable=track_unregistered_var,
    ).grid(row=1, column=0, sticky="w", padx=8, pady=(8, 0))

    ttk.Label(
        events_tab,
        text="Unregistered Events",
        font=("TkDefaultFont", 11, "bold"),
    ).grid(row=2, column=0, sticky="w", padx=8, pady=(8, 2))

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
                toggle_btn = create_colored_button(
                    right_frame,
                    textvariable=toggle_btn_text_var,
                    command=None,  # Will be set after details frame is created
                    style="info",
                    padx=10,
                    pady=4,
                    font=("TkDefaultFont", 9),
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
        row=3, column=0, sticky="w", padx=8, pady=(6, 4)
    )

    events_buttons = ttk.Frame(events_tab)
    events_buttons.grid(row=4, column=0, sticky="nw", padx=8, pady=(0, 6))

    create_colored_button(events_buttons, text="View Details", command=_show_unregistered_events_list, style="info").grid(
        row=0, column=0, sticky="w", padx=(0, 6)
    )
    create_colored_button(events_buttons, text="Refresh", command=_refresh_unregistered_events, style="info").grid(
        row=0, column=1, sticky="w", padx=(0, 6)
    )
    create_colored_button(events_buttons, text="Clear All", command=_clear_all_unregistered_events, style="danger").grid(
        row=0, column=2, sticky="w"
    )

    ttk.Label(events_tab, textvariable=events_status_var, foreground="gray").grid(
        row=5, column=0, sticky="w", padx=8, pady=(0, 6)
    )

    # Initial population of event counts
    _refresh_unregistered_events()

    return frame

