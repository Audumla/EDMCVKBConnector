"""
Catalog-Driven Rule Editor UI for EDMC VKB Connector.

Provides a visual editor for creating and editing rules using the schema:
- Catalog-driven signals, operators, and enum values
- Two-tier signal visibility (core/detail)
- When builder with all/any conditions
- Then/Else actions with edge-triggered semantics
- Inline validation and error handling
"""

import copy
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from . import plugin_logger
from .signals_catalog import SignalsCatalog, CatalogError, generate_id_from_title
from .ui_components import IconButton, create_colored_button
from .paths import data_path

logger = plugin_logger(__name__)

# Shift tokens for VKB actions
SHIFT_TOKENS = ["Shift1", "Shift2"]
SUBSHIFT_TOKENS = [f"Subshift{i}" for i in range(1, 8)]
ALL_SHIFT_TOKENS = SHIFT_TOKENS + SUBSHIFT_TOKENS



def _centered_yesno(parent, title, message):
    """Show a yes/no dialog centered on the parent window."""
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()

    result = [False]

    ttk.Label(dlg, text=message, wraplength=350, padding=15).pack()

    btn_frame = ttk.Frame(dlg, padding=(10, 0, 10, 10))
    btn_frame.pack()

    def on_yes():
        result[0] = True
        dlg.destroy()

    def on_no():
        dlg.destroy()

    create_colored_button(btn_frame, text="Yes", command=on_yes, style="success", width=8).pack(side=tk.LEFT, padx=5)
    create_colored_button(btn_frame, text="No", command=on_no, style="danger", width=8).pack(side=tk.LEFT, padx=5)

    dlg.update_idletasks()
    # Center on parent
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    dw = dlg.winfo_width()
    dh = dlg.winfo_height()
    x = max(0, px + (pw - dw) // 2)
    y = max(0, py + (ph - dh) // 2)
    dlg.geometry(f"+{x}+{y}")
    dlg.protocol("WM_DELETE_WINDOW", on_no)
    dlg.wait_window()
    return result[0]


def _centered_info(parent, title, message):
    """Show an info dialog centered on the parent window."""
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()

    ttk.Label(dlg, text=message, wraplength=350, padding=15).pack()

    btn_frame = ttk.Frame(dlg, padding=(10, 0, 10, 10))
    btn_frame.pack()
    create_colored_button(btn_frame, text="OK", command=dlg.destroy, style="info", width=8).pack()

    dlg.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    dw = dlg.winfo_width()
    dh = dlg.winfo_height()
    x = max(0, px + (pw - dw) // 2)
    y = max(0, py + (ph - dh) // 2)
    dlg.geometry(f"+{x}+{y}")
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
    dlg.wait_window()


def _centered_error(parent, title, message):
    """Show an error dialog centered on the parent window."""
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()

    ttk.Label(dlg, text=message, wraplength=400, padding=15, foreground="red").pack()

    btn_frame = ttk.Frame(dlg, padding=(10, 0, 10, 10))
    btn_frame.pack()
    create_colored_button(btn_frame, text="OK", command=dlg.destroy, style="danger", width=8).pack()

    dlg.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    dw = dlg.winfo_width()
    dh = dlg.winfo_height()
    x = max(0, px + (pw - dw) // 2)
    y = max(0, py + (ph - dh) // 2)
    dlg.geometry(f"+{x}+{y}")
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
    dlg.wait_window()


class ThreeStateCheckbutton(tk.Canvas):
    """
    A 3-state checkbox widget with states: OFF (0), ON (1), IGNORED (2).
    
    States cycle through: OFF → ON → IGNORED → OFF
    - OFF: Shift is cleared/disabled
    - ON: Shift is set/enabled  
    - IGNORED: Shift state is not changed
    """
    
    def __init__(self, parent, text="", variable=None, command=None, **kwargs):
        """
        Initialize 3-state checkbox.
        
        Args:
            parent: Parent widget
            text: Label text
            variable: tk.StringVar to track state ('off', 'on', 'ignored')
            command: Callback when state changes
        """
        super().__init__(parent, width=20, height=20, highlightthickness=0, bg="white", **kwargs)
        self.text = text
        self.variable = variable if variable else tk.StringVar(value='off')
        self.command = command
        self.size = 14  # Checkbox size
        self.label_font = ("TkDefaultFont", 10)
        
        # Bind click and display initial state
        self.bind("<Button-1>", self._on_click)
        self._draw()
    
    def _on_click(self, event=None):
        """Cycle to next state on click."""
        current = self.variable.get()
        states = ['off', 'on', 'ignored']
        current_idx = states.index(current) if current in states else 0
        next_idx = (current_idx + 1) % 3
        self.variable.set(states[next_idx])
        self._draw()
        if self.command:
            self.command()
    
    def _draw(self):
        """Draw the checkbox in current state."""
        self.delete("all")
        state = self.variable.get()
        
        # Box outline
        box_color = "#333"
        if state == 'off':
            box_fill = "#e74c3c"
            symbol = "✗"
            symbol_color = "white"
        elif state == 'on':
            box_fill = "#27ae60"
            symbol = "✓"
            symbol_color = "white"
        else:  # ignored
            box_fill = "#ecf0f1"
            symbol = ""
            symbol_color = "#333"
        
        # Draw box
        self.create_rectangle(2, 2, 16, 16, fill=box_fill, outline=box_color, width=1)
        
        # Draw symbol (empty for ignored)
        if symbol:
            self.create_text(9, 9, text=symbol, font=self.label_font, fill=symbol_color)
        
        # Draw label
        if self.text:
            self.create_text(22, 9, text=self.text, anchor="w", font=self.label_font)


class RuleEditorUI:
    """
    Main UI for catalog-driven rule editor.
    
    Provides rules list view and rule editor with catalog-driven controls.
    """
    
    def __init__(self, parent, rules_file: Path, plugin_dir: Path, initial_rule_index: Optional[int] = None):
        """
        Initialize the rule editor UI.
        
        Args:
            parent: Parent tkinter widget
            rules_file: Path to rules.json file
            plugin_dir: Plugin directory path for catalog
        """
        self.parent = parent
        self.rules_file = rules_file
        self.plugin_dir = plugin_dir
        self.catalog_path = data_path(plugin_dir, "signals_catalog.json")
        self.catalog_mtime = self._get_catalog_mtime()
        self.pending_catalog_reload = False
        self.catalog_poll_ms = 1500
        
        # Try to load catalog
        self.catalog: Optional[SignalsCatalog] = None
        self.catalog_error: Optional[str] = None
        try:
            self.catalog = SignalsCatalog.from_plugin_dir(str(plugin_dir))
            logger.info("Loaded signals catalog")
        except CatalogError as e:
            self.catalog_error = str(e)
            logger.error(f"Failed to load catalog: {e}")
        except Exception as e:
            self.catalog_error = f"Unexpected error: {e}"
            logger.error(f"Unexpected catalog error: {e}")
        
        # Load rules
        self.rules: List[Dict[str, Any]] = []
        self._load_rules()
        
        # Track unsaved changes
        self.unsaved_changes = False
        
        # Active editor state
        self.editing_rule_index: Optional[int] = None
        self.active_editor: Optional["RuleEditor"] = None
        
        # If opening directly to edit a specific rule, set that now
        if initial_rule_index is not None and not self.catalog_error:
            if 0 <= initial_rule_index < len(self.rules):
                self.editing_rule_index = initial_rule_index
        
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("VKB Rule Editor")
        self.window.geometry("1000x700")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Build UI (will show editor if editing_rule_index is set)
        self._build_ui()

        # Start catalog change watcher
        self._schedule_catalog_poll()
        
        # Center window on screen (handle withdrawn parent)
        self.window.update_idletasks()
        
        # Try to center relative to parent if visible
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        if parent_width > 1 and parent_height > 1:
            # Parent is visible, center relative to it
            x = parent.winfo_rootx() + (parent_width - self.window.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent_height - self.window.winfo_height()) // 2
        else:
            # Parent is withdrawn, center on screen
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            window_width = self.window.winfo_width()
            window_height = self.window.winfo_height()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        
        # Ensure window is not off-screen (negative coordinates)
        x = max(0, x)
        y = max(0, y)
        self.window.geometry(f"+{x}+{y}")
    
    def _load_rules(self):
        """Load rules from the rules file."""
        if not self.rules_file.exists():
            logger.info(f"No rules file found at {self.rules_file}")
            self.rules = []
            return
        
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Support both array and wrapped format
            if isinstance(data, list):
                self.rules = data
            elif isinstance(data, dict) and 'rules' in data:
                self.rules = data['rules']
            else:
                logger.error("Invalid rules file format")
                self.rules = []
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            _centered_error(self.window, "Error", f"Failed to load rules:\n{e}")
            self.rules = []
    
    def _save_rules(self):
        """Save rules to the rules file."""
        try:
            # Save as array format
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, indent=2)
            self.unsaved_changes = False
            logger.info(f"Saved {len(self.rules)} rules to {self.rules_file}")
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
            _centered_error(self.window, "Error", f"Failed to save rules:\n{e}")
            raise
    
    def _build_ui(self):
        """Build the main UI."""
        # Check for catalog error first
        if self.catalog_error:
            self._show_catalog_error()
            return
        
        # Create container for editor view
        self.view_container = ttk.Frame(self.window)
        self.view_container.pack(fill=tk.BOTH, expand=True)
        
        # Show editor (either for existing rule or new rule)
        if self.editing_rule_index is not None:
            self._show_rule_editor()
        else:
            # Create new empty rule
            self.editing_rule_index = -1  # Special marker for new rule
            self._show_rule_editor()

    def _reload_catalog(self):
        """Reload the signals catalog and refresh the editor."""
        if self.active_editor and self.active_editor.has_changes:
            if not _centered_yesno(
                self.window,
                "Unsaved Changes",
                "You have unsaved changes. Reloading the catalog will discard them. Continue?"
            ):
                return
        try:
            self.catalog = SignalsCatalog.from_plugin_dir(str(self.plugin_dir))
            self.catalog_error = None
            logger.info("Reloaded signals catalog")
            if self.editing_rule_index is not None:
                self._show_rule_editor()
            else:
                # No rule being edited, close window
                self.window.destroy()
        except CatalogError as e:
            self.catalog_error = str(e)
            logger.error(f"Failed to reload catalog: {e}")
            self._show_catalog_error()
        except Exception as e:
            self.catalog_error = f"Unexpected error: {e}"
            logger.error(f"Unexpected catalog error on reload: {e}")
            self._show_catalog_error()
    
    def _show_catalog_error(self):
        """Show blocking catalog error message."""
        error_frame = ttk.Frame(self.window, padding=20)
        error_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            error_frame,
            text="Catalog Error",
            font=("TkDefaultFont", 16, "bold"),
            foreground="red"
        ).pack(pady=(0, 10))
        
        ttk.Label(
            error_frame,
            text="The signals catalog could not be loaded:",
            wraplength=400
        ).pack(pady=(0, 5))
        
        error_text = scrolledtext.ScrolledText(error_frame, height=10, width=60, wrap=tk.WORD)
        error_text.pack(pady=(0, 10))
        error_text.insert("1.0", self.catalog_error)
        error_text.configure(state='disabled')
        
        ttk.Label(
            error_frame,
            text="Rule editing is disabled until the catalog is fixed.",
            wraplength=400,
            foreground="red"
        ).pack(pady=(0, 10))
        
        create_colored_button(error_frame, text="Close", command=self.window.destroy, style="info").pack()
    
    def _get_catalog_mtime(self) -> Optional[float]:
        """Return the catalog file mtime or None if unavailable."""
        try:
            return self.catalog_path.stat().st_mtime
        except FileNotFoundError:
            return None
        except OSError as e:
            logger.debug(f"Failed to stat catalog file: {e}")
            return None

    def _schedule_catalog_poll(self):
        """Schedule polling for catalog changes."""
        if not self.window.winfo_exists():
            return
        self.window.after(self.catalog_poll_ms, self._poll_catalog_changes)

    def _poll_catalog_changes(self):
        """Poll for catalog file changes and refresh UI when needed."""
        if not self.window.winfo_exists():
            return

        current_mtime = self._get_catalog_mtime()
        if current_mtime != self.catalog_mtime:
            self.catalog_mtime = current_mtime
            self._on_catalog_file_changed()

        self.window.after(self.catalog_poll_ms, self._poll_catalog_changes)

    def _on_catalog_file_changed(self):
        """Handle catalog changes without clobbering active edits."""
        if self.active_editor and self.active_editor.has_changes:
            if not self.pending_catalog_reload:
                self.pending_catalog_reload = True
                _centered_info(
                    self.window,
                    "Catalog Changed",
                    "Signals catalog changed on disk. Save or cancel your edits to reload."
                )
            return

        self.pending_catalog_reload = False
        self._reload_catalog()
    
    def _show_rule_editor(self):
        """Show the rule editor view."""
        # Clear container
        for widget in self.view_container.winfo_children():
            widget.destroy()
        
        self.current_view = "editor"
        
        if self.editing_rule_index is None:
            logger.error("No rule index set for editing")
            return
        
        # For new rules (index = -1), create an empty rule
        if self.editing_rule_index == -1:
            rule_to_edit = {
                "title": "",
                "enabled": True,
                "when": {"all": [], "any": []},
                "then": [],
                "else": []
            }
        else:
            rule_to_edit = self.rules[self.editing_rule_index]
        
        # Create editor
        self.active_editor = RuleEditor(
            self.view_container,
            rule_to_edit,
            self.catalog,
            self._on_save_rule,
            self._on_cancel_edit
        )
    
    def _on_save_rule(self, updated_rule: Dict[str, Any]):
        """Callback when rule is saved from editor."""
        if self.editing_rule_index is not None:
            if not updated_rule.get("id"):
                used_ids = {
                    r.get("id") for i, r in enumerate(self.rules)
                    if r.get("id") and i != self.editing_rule_index and self.editing_rule_index != -1
                }
                updated_rule["id"] = generate_id_from_title(updated_rule.get("title", ""), used_ids)
            
            # For new rules (index = -1), append to rules list
            if self.editing_rule_index == -1:
                self.rules.append(updated_rule)
            else:
                self.rules[self.editing_rule_index] = updated_rule
            
            self.unsaved_changes = True
            self._save_rules()
            _centered_info(self.window, "Saved", "Rule saved successfully")
            # Close window after successful save
            self.window.destroy()
    
    def _on_cancel_edit(self):
        """Callback when edit is cancelled."""
        # Close window when edit is cancelled
        self.window.destroy()
    
    def _on_close(self):
        """Handle window close."""
        # Only check the active editor's changes, not the window's overall unsaved status
        if self.active_editor and self.active_editor.has_changes:
            if not _centered_yesno(self.window, "Unsaved Changes", "You have unsaved changes. Close anyway?"):
                return
        self.window.destroy()


class RuleEditor:
    """
    Rule editor component for editing a single rule.
    
    Provides catalog-driven when/then/else builders with inline validation.
    """
    
    def __init__(
        self,
        parent,
        rule: Dict[str, Any],
        catalog: SignalsCatalog,
        on_save,
        on_cancel
    ):
        """
        Initialize rule editor.
        
        Args:
            parent: Parent widget
            rule: Rule dictionary to edit
            catalog: Signals catalog
            on_save: Callback when saved (takes updated rule dict)
            on_cancel: Callback when cancelled
        """
        self.parent = parent
        self.original_rule = copy.deepcopy(rule)
        self.rule = copy.deepcopy(rule)  # Working copy
        self.catalog = catalog
        self.on_save_callback = on_save
        self.on_cancel_callback = on_cancel

        # Track changes - suppress during initial load
        self.has_changes = False
        self._loading = True

        # Load icon mapping
        self._load_icon_map()

        # Build signal lookup tables from catalog
        self._build_lookup_tables()

        # Tier filter state - always show both tiers
        self.show_detail_tier = tk.BooleanVar(value=True)

        # Build UI
        self._build_ui()

        # Done loading - enable change tracking
        self._loading = False
        self.has_changes = False
    
    def _build_lookup_tables(self):
        """Build lookup tables from catalog for efficient access."""
        # Get all signals organized by category
        self.signals_by_category: Dict[str, List[Tuple[str, Dict]]] = {}
        # Hierarchical structure: category -> items (groups or signals)
        # Each item is either a signal (leaf) or a group (branch with children)
        self.hierarchy_by_category: Dict[str, Dict[str, Any]] = {}
        
        self.all_signals: Dict[str, Dict] = {}
        self.signal_display_to_id: Dict[str, str] = {}
        self.signal_id_to_display: Dict[str, str] = {}
        self.signal_id_to_simple_display: Dict[str, str] = {}  # Without category prefix
        
        # First pass: collect all signals and organize by category and subcategory
        signals_by_category_and_subcategory: Dict[str, Dict[str, List[tuple]]] = {}
        
        for signal_id, signal_def in self.catalog.signals.items():
            # Skip comment entries (start with underscore and are strings)
            if signal_id.startswith("_") or not isinstance(signal_def, dict):
                continue
            
            self.all_signals[signal_id] = signal_def
            category = signal_def.get("ui", {}).get("category", "Other")
            subcategory = signal_def.get("ui", {}).get("subcategory", "")  # Empty string if no subcategory
            
            # Add to flat category list
            if category not in self.signals_by_category:
                self.signals_by_category[category] = []
            self.signals_by_category[category].append((signal_id, signal_def))
            
            # Organize by category and subcategory for hierarchy building
            if category not in signals_by_category_and_subcategory:
                signals_by_category_and_subcategory[category] = {}
            if subcategory not in signals_by_category_and_subcategory[category]:
                signals_by_category_and_subcategory[category][subcategory] = []
            signals_by_category_and_subcategory[category][subcategory].append((signal_id, signal_def))
        
        # Second pass: build hierarchy from subcategory organization
        for category, subcategory_dict in signals_by_category_and_subcategory.items():
            if category not in self.hierarchy_by_category:
                self.hierarchy_by_category[category] = {}
            
            for subcategory, signals_list in subcategory_dict.items():
                if subcategory:
                    # This is a group (has subcategory) - create a group item
                    group_key = f"_group_{subcategory.replace(' ', '_').lower()}"
                    if group_key not in self.hierarchy_by_category[category]:
                        self.hierarchy_by_category[category][group_key] = {
                            "is_group": True,
                            "group_id": group_key,
                            "group_label": subcategory,
                            "children": {}
                        }
                    
                    # Add signals to this group
                    for signal_id, signal_def in signals_list:
                        child_key = signal_id.split(".")[-1]  # Use last part of signal_id as key
                        self.hierarchy_by_category[category][group_key]["children"][child_key] = {
                            "signal_id": signal_id,
                            "signal_def": signal_def
                        }
                else:
                    # No subcategory - add as direct signal items
                    for signal_id, signal_def in signals_list:
                        item_key = signal_id.split(".")[-1]  # Use last part of signal_id as key
                        self.hierarchy_by_category[category][item_key] = {
                            "is_signal": True,
                            "signal_id": signal_id,
                            "signal_def": signal_def
                        }
        
        self._build_signal_display_maps()
        
        # Get operators
        self.operators = self.catalog.operators
        # Use only operator symbols for display (cleaner UI)
        self.operator_display_to_token = {
            op_def['symbol']: token
            for token, op_def in self.operators.items()
        }
        self.operator_token_to_display = {
            token: op_def['symbol'] for token, op_def in self.operators.items()
        }
        
        # Get tiers
        self.tiers = self.catalog.ui_tiers

    def _load_icon_map(self):
        """Load icon name to character mapping from icon_map.json."""
        self.icon_map: Dict[str, str] = {}

        try:
            icon_map_path = data_path(self.plugin_dir, "icon_map.json")
            if icon_map_path.exists():
                with open(icon_map_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.icon_map = data.get("icons", {})
                logger.debug(f"Loaded {len(self.icon_map)} icon mappings")
            else:
                logger.warning(f"Icon map not found at {icon_map_path}")
                # Provide basic icons as fallback
                self.icon_map = {
                    "shift": "⇧",
                    "screen": "🖥️",
                    "ship": "🚀",
                    "walk": "🚶"
                }
        except Exception as e:
            logger.error(f"Failed to load icon map: {e}")
            self.icon_map = {}
        
    def _build_signal_display_maps(self):
        """Build display labels for signals and ensure uniqueness."""
        display_counts: Dict[str, int] = {}

        for category in sorted(self.signals_by_category.keys(), key=str.casefold):
            for signal_id, signal_def in self.signals_by_category[category]:
                ui = signal_def.get("ui", {})
                label = ui.get("label", signal_id)
                base_display = f"{category}: {label}"
                display_counts[base_display] = display_counts.get(base_display, 0) + 1

        for category in sorted(self.signals_by_category.keys(), key=str.casefold):
            for signal_id, signal_def in self.signals_by_category[category]:
                ui = signal_def.get("ui", {})
                label = ui.get("label", signal_id)
                base_display = f"{category}: {label}"
                if display_counts.get(base_display, 0) > 1:
                    display = f"{base_display} ({signal_id})"
                else:
                    display = base_display

                self.signal_display_to_id[display] = signal_id
                self.signal_id_to_display[signal_id] = display

                # Also store simple display (without category) for category-specific dropdowns
                if signal_id not in self.signal_id_to_simple_display:
                    self.signal_id_to_simple_display[signal_id] = label
    
    def _build_ui(self):
        """Build the editor UI."""
        # Main frame with padding
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with title and action buttons on right
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Edit Rule", font=("TkDefaultFont", 14, "bold")).pack(side=tk.LEFT)
        
        # Action buttons on the right (Cancel then Save)
        button_frame_right = ttk.Frame(header_frame)
        button_frame_right.pack(side=tk.RIGHT, fill=tk.X)
        
        # Create styled buttons with colors
        cancel_btn = create_colored_button(
            button_frame_right,
            text="Cancel",
            command=self._on_back,
            style="danger",
            padx=12,
            pady=6,
            font=("TkDefaultFont", 10),
            bd=2,
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = create_colored_button(
            button_frame_right,
            text="Save",
            command=self._save,
            style="success",
            padx=12,
            pady=6,
            font=("TkDefaultFont", 10),
            bd=2,
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Scrollable content area
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        content_frame = ttk.Frame(canvas)
        
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        
        def _on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def _on_canvas_configure(event):
            canvas.itemconfigure(canvas_window, width=event.width)
        
        content_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Build editor sections
        self._build_basic_fields(content_frame)
        self._build_when_section(content_frame)
        self._build_then_section(content_frame)
        self._build_else_section(content_frame)
    
    def _build_basic_fields(self, parent):
        """Build basic fields (title, id)."""
        basic_frame = ttk.LabelFrame(parent, text="Basic Information", padding=10)
        basic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title and ID on same row - title left (editable), ID right (read-only)
        header_row = ttk.Frame(basic_frame)
        header_row.pack(fill=tk.X, pady=5)
        header_row.columnconfigure(1, weight=1)  # Make title entry expand
        
        # Left side: Title label and entry
        ttk.Label(header_row, text="Title:*").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.title_var = tk.StringVar(value=self.rule.get("title", ""))
        self.title_var.trace_add("write", lambda *args: self._on_title_changed())
        ttk.Entry(header_row, textvariable=self.title_var).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        
        # Right side: ID label (read-only)
        ttk.Label(header_row, text="ID:", foreground="gray").grid(row=0, column=2, sticky="e", padx=(0, 4))
        self.id_preview_var = tk.StringVar(value="")
        ttk.Label(header_row, textvariable=self.id_preview_var, foreground="gray").grid(row=0, column=3, sticky="e")
        self._update_id_preview()
        
        # Enabled state (always tracked internally, not shown in UI)
        self.enabled_var = tk.BooleanVar(value=self.rule.get("enabled", True))
        self.enabled_var.trace_add("write", lambda *args: self._mark_changed())
    
    def _build_when_section(self, parent):
        """Build the When condition builder section."""
        when_frame = ttk.LabelFrame(parent, text="When (Conditions) - Define when this rule activates", padding=4)
        when_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        # All of these (all)
        self.all_frame = ttk.LabelFrame(when_frame, text="All of these (AND logic)", padding=2)
        self.all_frame.pack(fill=tk.X, pady=(0, 2))
        
        self.all_add_frame = ttk.Frame(self.all_frame)
        self.all_add_frame.pack(anchor=tk.W, pady=(2, 0))
        self.all_add_button = self.all_add_frame  # used as pack reference in _add_condition
        IconButton(self.all_add_frame, "add", command=lambda: self._add_condition("all") ).pack(side=tk.LEFT)
        ttk.Label(self.all_add_frame, text="Add condition", foreground="#27ae60",
                  font=("TkDefaultFont", 9)).pack(side=tk.LEFT, padx=(4, 0))
        self.all_conditions = []
        self._load_conditions("all")
        
        # Any of these (any)
        self.any_frame = ttk.LabelFrame(when_frame, text="Any of these (OR logic)", padding=2)
        self.any_frame.pack(fill=tk.X)
        
        self.any_add_frame = ttk.Frame(self.any_frame)
        self.any_add_frame.pack(anchor=tk.W, pady=(2, 0))
        self.any_add_button = self.any_add_frame  # used as pack reference in _add_condition
        IconButton(self.any_add_frame, "add", command=lambda: self._add_condition("any"), tooltip="Add condition").pack(side=tk.LEFT)
        ttk.Label(self.any_add_frame, text="Add condition", foreground="#27ae60",
                  font=("TkDefaultFont", 9)).pack(side=tk.LEFT, padx=(4, 0))
        self.any_conditions = []
        self._load_conditions("any")

        # Empty state hints
        self.when_hint_label = ttk.Label(when_frame, text="Add a condition to start", foreground="gray")
        self.when_hint_label.pack(pady=8)
        self._update_when_hint()
    
    def _load_conditions(self, group: str):
        """Load existing conditions for a group."""
        conditions = self.rule.get("when", {}).get(group, [])
        for cond in conditions:
            self._add_condition(group, cond)
    
    def _add_condition(self, group: str, condition: Optional[Dict] = None):
        """Add a condition row to the specified group."""
        target_frame = self.all_frame if group == "all" else self.any_frame
        target_list = self.all_conditions if group == "all" else self.any_conditions
        add_button = self.all_add_button if group == "all" else self.any_add_button
        
        # Condition container (row + error)
        cond_container = ttk.Frame(target_frame)
        cond_container.pack(fill=tk.X, pady=(2, 2), before=add_button)
        row_frame = ttk.Frame(cond_container)
        row_frame.pack(fill=tk.X, pady=0, ipady=0)
        
        # Category dropdown (first step)
        category_var = tk.StringVar(value="")
        category_combo = ttk.Combobox(row_frame, textvariable=category_var, state="readonly", width=15)
        category_combo.pack(side=tk.LEFT, padx=1)
        
        # Item dropdown (second step - shows groups and signals)
        item_var = tk.StringVar(value="")
        item_combo = ttk.Combobox(row_frame, textvariable=item_var, state="readonly", width=22)
        item_combo.pack(side=tk.LEFT, padx=1)
        
        # Child dropdown (optional third step - only shown if item is a group)
        child_var = tk.StringVar(value="")
        child_combo = ttk.Combobox(row_frame, textvariable=child_var, state="readonly", width=18)
        # Don't pack initially - will be inserted dynamically after item when needed
        
        # Operator dropdown
        op_var = tk.StringVar(value=condition.get("op", "") if condition else "")
        op_combo = ttk.Combobox(row_frame, textvariable=op_var, state="readonly", width=4)
        op_combo.pack(side=tk.LEFT, padx=1)
        
        # Value control (dynamic based on signal type)
        value_var = tk.StringVar(value=str(condition.get("value", "")) if condition else "")
        value_widget_frame = ttk.Frame(row_frame)
        value_widget_frame.pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)
        
        # Row action buttons
        def remove_cond():
            cond_container.destroy()
            target_list.remove(cond_data)
            self._mark_changed()
            self._update_when_hint()
        
        def move_up():
            self._move_condition(cond_data, -1)
        
        def move_down():
            self._move_condition(cond_data, 1)
        
        def duplicate_row():
            self._duplicate_condition(cond_data)
        
        IconButton(row_frame, "duplicate", command=duplicate_row, tooltip="Duplicate").pack(side=tk.RIGHT, padx=1)
        IconButton(row_frame, "down", command=move_down, tooltip="Move down").pack(side=tk.RIGHT, padx=1)
        IconButton(row_frame, "up", command=move_up, tooltip="Move up").pack(side=tk.RIGHT, padx=1)
        IconButton(row_frame, "delete", command=remove_cond, tooltip="Remove").pack(side=tk.RIGHT, padx=1)

        # Inline error label (hidden until error occurs)
        error_label = ttk.Label(cond_container, text="", foreground="red")
        
        # Store condition data
        cond_data = {
            "frame": cond_container,
            "row_frame": row_frame,
            "group": group,
            "category_var": category_var,
            "category_combo": category_combo,
            "item_var": item_var,
            "item_combo": item_combo,
            "child_var": child_var,
            "child_combo": child_combo,
            "op_var": op_var,
            "op_combo": op_combo,
            "value_var": value_var,
            "value_widget_frame": value_widget_frame,
            "value_widget": None,
            "value_listbox": None,
            "value_kind": None,
            "value_selected_label": None,
            "signal_id": None,
            "selected_item_key": None,  # Track which item (group/signal) is selected
            "is_group": False,  # Track if selected item is a group
            "unknown_signal": False,
            "unknown_operator": False,
            "unknown_value": False,
            "enum_display_to_value": {},
            "enum_value_to_display": {},
            "enum_sections": {},
            "enum_section_var": None,
            "error_label": error_label,
            "raw_condition": condition
        }
        target_list.append(cond_data)
        
        # Populate category dropdown
        self._populate_category_dropdown(category_combo, cond_data)
        
        # Setup category change handler
        def on_category_change(event=None):
            selected_category = category_var.get()
            child_var.set("")
            cond_data["signal_id"] = None
            cond_data["selected_item_key"] = None
            cond_data["is_group"] = False
            
            # Populate items (groups and signals) for this category
            self._populate_items_for_category(item_combo, selected_category, cond_data)
            item_var.set("")
            self._update_condition_value_widget(cond_data, None, None)
            self._mark_changed()
        
        category_combo.bind("<<ComboboxSelected>>", on_category_change)
        
        # Setup item change handler
        def on_item_change(event=None):
            selected_category = category_var.get()
            selected_item = item_var.get()
            
            # Check if selected item is a group or signal
            self._handle_item_selection(cond_data, selected_category, selected_item)
            self._mark_changed()
        
        item_combo.bind("<<ComboboxSelected>>", on_item_change)
        
        # Setup child change handler (for groups)
        def on_child_change(event=None):
            selected_child = child_var.get()
            
            # Identify the signal from the group + child selection
            self._handle_child_selection(cond_data, selected_child)
            self._mark_changed()
        
        child_combo.bind("<<ComboboxSelected>>", on_child_change)

        # Setup operator change handler
        def on_operator_change(event=None):
            self._on_condition_operator_changed(cond_data)
            self._mark_changed()
            self._set_condition_error(cond_data, "")

        op_combo.bind("<<ComboboxSelected>>", on_operator_change)

        # Load existing condition
        if condition:
            self._apply_condition_from_rule(cond_data, condition)
        else:
            self._update_when_hint()
    
    def _populate_category_dropdown(self, combo: ttk.Combobox, cond_data: Dict):
        """Populate category dropdown."""
        show_detail = self.show_detail_tier.get()
        categories = []
        
        for category, sigs in self.signals_by_category.items():
            # Check if category has any visible signals
            has_visible = False
            for signal_id, signal_def in sigs:
                tier = signal_def.get("ui", {}).get("tier", "core")
                if tier == "core" or show_detail:
                    has_visible = True
                    break
            if has_visible:
                categories.append(category)
        
        combo["values"] = sorted(categories, key=str.casefold)
        
        # Pre-select category if loading existing condition
        if cond_data.get("signal_id"):
            signal_id = cond_data["signal_id"]
            signal_def = self.all_signals.get(signal_id)
            if signal_def:
                category = signal_def.get("ui", {}).get("category", "Other")
                combo.set(category)
    
    def _populate_signal_dropdown_for_category(self, combo: ttk.Combobox, category: str):
        """Populate signal dropdown for a specific category with simple labels (no category prefix)."""
        signals = []
        show_detail = self.show_detail_tier.get()
        
        if category in self.signals_by_category:
            for signal_id, signal_def in self.signals_by_category[category]:
                tier = signal_def.get("ui", {}).get("tier", "core")
                if tier == "core" or show_detail:
                    simple_display = self.signal_id_to_simple_display.get(signal_id, signal_id)
                    if simple_display:
                        signals.append(simple_display)
        
        combo["values"] = sorted(signals, key=str.casefold)
    
    def _populate_signal_dropdown(self, combo: ttk.Combobox):
        """Populate signal dropdown with filtered signals."""
        signals = []
        show_detail = self.show_detail_tier.get()

        for category in sorted(self.signals_by_category.keys(), key=str.casefold):
            for signal_id, signal_def in self.signals_by_category[category]:
                tier = signal_def.get("ui", {}).get("tier", "core")
                if tier == "core" or show_detail:
                    display = self.signal_id_to_display.get(signal_id)
                    if display:
                        signals.append(display)

        combo["values"] = sorted(signals, key=str.casefold)
    
    def _populate_items_for_category(self, combo: ttk.Combobox, category: str, cond_data: Dict):
        """Populate item dropdown with groups and signals for a category."""
        items = []
        show_detail = self.show_detail_tier.get()
        
        if category not in self.hierarchy_by_category:
            combo["values"] = []
            return
        
        # Get all items (groups and signals) for this category
        for item_key, item_data in self.hierarchy_by_category[category].items():
            if item_data.get("is_group"):
                # This is a group - show the group label
                group_label = item_data.get("group_label", item_key.replace("_", " ").title())
                items.append((item_key, group_label, True))  # (key, display, is_group)
            elif item_data.get("is_signal"):
                # This is a direct signal - check tier visibility
                signal_def = item_data.get("signal_def", {})
                tier = signal_def.get("ui", {}).get("tier", "core")
                if tier == "core" or show_detail:
                    signal_id = item_data.get("signal_id")
                    simple_display = self.signal_id_to_simple_display.get(signal_id, item_key)
                    items.append((item_key, simple_display, False))  # (key, display, is_group)
        
        # Sort by display name and populate combo
        items.sort(key=lambda x: x[1].casefold())
        combo["values"] = [display for key, display, is_group in items]
        
        # Store mapping for lookups
        cond_data["item_key_to_display"] = {key: display for key, display, is_group in items}
        cond_data["item_display_to_key"] = {display: key for key, display, is_group in items}
        cond_data["item_is_group"] = {key: is_group for key, display, is_group in items}
    
    def _handle_item_selection(self, cond_data: Dict, category: str, item_display: str):
        """Handle item selection - show child dropdown if group, or finalize signal if leaf."""
        if not item_display or category not in self.hierarchy_by_category:
            cond_data["child_combo"].pack_forget()
            cond_data["child_var"].set("")
            cond_data["signal_id"] = None
            cond_data["is_group"] = False
            cond_data["selected_item_key"] = None
            self._update_condition_value_widget(cond_data, None, None)
            return
        
        # Map display back to key
        item_key = cond_data.get("item_display_to_key", {}).get(item_display)
        if not item_key:
            return
        
        cond_data["selected_item_key"] = item_key
        item_data = self.hierarchy_by_category[category].get(item_key, {})
        
        if item_data.get("is_group"):
            # This is a group - show child dropdown
            cond_data["is_group"] = True
            cond_data["signal_id"] = None
            self._populate_children_for_group(cond_data, category, item_key)
            self._update_condition_value_widget(cond_data, None, None)
        else:
            # This is a direct signal - hide child dropdown and proceed
            cond_data["is_group"] = False
            cond_data["child_combo"].pack_forget()
            cond_data["child_var"].set("")
            signal_id = item_data.get("signal_id")
            cond_data["signal_id"] = signal_id
            self._on_condition_signal_changed(cond_data)
    
    def _populate_children_for_group(self, cond_data: Dict, category: str, item_key: str):
        """Populate child dropdown with children of the selected group."""
        child_combo = cond_data["child_combo"]
        item_combo = cond_data["item_combo"]
        op_combo = cond_data["op_combo"]
        show_detail = self.show_detail_tier.get()
        
        children = []
        
        item_data = self.hierarchy_by_category[category].get(item_key, {})
        if not item_data.get("is_group"):
            child_combo.pack_forget()
            return
        
        # Get children of this group
        children_dict = item_data.get("children", {})
        for child_key, child_data in children_dict.items():
            signal_def = child_data.get("signal_def", {})
            tier = signal_def.get("ui", {}).get("tier", "core")
            if tier == "core" or show_detail:
                signal_id = child_data.get("signal_id")
                simple_display = self.signal_id_to_simple_display.get(signal_id, child_key)
                children.append((child_key, simple_display, signal_id))
        
        if children:
            # Sort and populate
            children.sort(key=lambda x: x[1].casefold())
            child_combo["values"] = [display for child_key, display, signal_id in children]
            # Store mapping
            cond_data["child_display_to_signal_id"] = {display: signal_id for child_key, display, signal_id in children}
            # Show child dropdown between item and operator
            child_combo.pack(side=tk.LEFT, padx=1, before=op_combo)
        else:
            child_combo.pack_forget()
    
    def _handle_child_selection(self, cond_data: Dict, child_display: str):
        """Handle child selection - identify the final signal."""
        if not child_display:
            cond_data["signal_id"] = None
            self._update_condition_value_widget(cond_data, None, None)
            return
        
        # Map child display to signal_id
        signal_id = cond_data.get("child_display_to_signal_id", {}).get(child_display)
        if signal_id:
            cond_data["signal_id"] = signal_id
            self._on_condition_signal_changed(cond_data)
    
    def _on_tier_changed(self):
        """Handle tier filter toggle."""
        # Repopulate all category and item dropdowns
        for cond_data in self.all_conditions + self.any_conditions:
            self._populate_category_dropdown(cond_data["category_combo"], cond_data)
            category = cond_data["category_var"].get()
            if category:
                self._populate_items_for_category(cond_data["item_combo"], category, cond_data)
                # Re-handle item selection if one was selected
                item_display = cond_data["item_var"].get()
                if item_display:
                    self._handle_item_selection(cond_data, category, item_display)
            self._ensure_combo_value(cond_data["item_combo"], cond_data["item_var"].get())

    def _ensure_combo_value(self, combo: ttk.Combobox, value: str):
        """Ensure the combobox list includes the provided value."""
        if not value:
            return
        values = list(combo["values"])
        if value not in values:
            values.insert(0, value)
            combo["values"] = values
    
    def _on_condition_signal_changed(self, cond_data: Dict, initial_condition: Optional[Dict] = None):
        """Handle signal selection change in a condition."""
        cond_data["unknown_signal"] = False
        cond_data["unknown_operator"] = False
        cond_data["unknown_value"] = False
        
        # Preserve signal_id if already set (e.g., when loading from rule)
        signal_id = cond_data.get("signal_id")

        if not signal_id:
            cond_data["signal_id"] = None
            self._update_condition_value_widget(cond_data, None, None)
            return
        
        # signal_id is already known (set by item/child selection), get its definition
        signal_def = self.all_signals.get(signal_id)

        if signal_def:
            signal_type = signal_def.get("type", "bool")
            allowed_ops = self._get_allowed_ops_for_signal(signal_type)
            op_values = [self.operator_token_to_display[op] for op in allowed_ops if op in self.operator_token_to_display]
            cond_data["op_combo"]["values"] = op_values

            if initial_condition is None:
                cond_data["op_var"].set("")
                cond_data["value_var"].set("")
                default_op = "eq" if "eq" in allowed_ops else (allowed_ops[0] if allowed_ops else "")
                if default_op and default_op in self.operator_token_to_display:
                    cond_data["op_var"].set(self.operator_token_to_display[default_op])
        else:
            cond_data["op_combo"]["values"] = list(self.operator_display_to_token.keys())
            self._ensure_combo_value(cond_data["op_combo"], cond_data["op_var"].get())

        op_token = self._get_operator_token(cond_data["op_var"].get())
        self._update_condition_value_widget(cond_data, signal_def, op_token)

    def _on_condition_operator_changed(self, cond_data: Dict, initial_condition: Optional[Dict] = None):
        """Handle operator changes to update value control."""
        op_text = cond_data["op_var"].get()
        op_token = self._get_operator_token(op_text)
        if op_text and not op_token:
            cond_data["unknown_operator"] = True
            self._ensure_combo_value(cond_data["op_combo"], op_text)
        else:
            cond_data["unknown_operator"] = False

        signal_id = cond_data.get("signal_id")
        signal_def = self.all_signals.get(signal_id) if signal_id else None
        self._update_condition_value_widget(cond_data, signal_def, op_token)

        if initial_condition is None:
            if cond_data["value_kind"] == "enum_multi" and cond_data["value_listbox"]:
                cond_data["value_listbox"].selection_clear(0, tk.END)
            else:
                cond_data["value_var"].set("")

    def _get_allowed_ops_for_signal(self, signal_type: str) -> List[str]:
        """Return allowed operator tokens for a signal type."""
        if signal_type == "bool":
            return [op for op in ["eq", "ne"] if op in self.operators]
        if signal_type == "enum":
            return [op for op in ["eq", "ne", "in", "nin"] if op in self.operators]
        return list(self.operators.keys())

    def _get_operator_token(self, display: str) -> Optional[str]:
        """Resolve operator token from its display text."""
        return self.operator_display_to_token.get(display)
    
    def _update_condition_value_widget(self, cond_data: Dict, signal_def: Optional[Dict], op_token: Optional[str]):
        """Update the value widget for a condition based on signal type."""
        # Clear existing value widget
        for widget in cond_data["value_widget_frame"].winfo_children():
            widget.destroy()
        cond_data["value_widget"] = None
        cond_data["value_listbox"] = None
        cond_data["value_selected_label"] = None
        cond_data["enum_display_to_value"] = {}
        cond_data["enum_value_to_display"] = {}
        cond_data["enum_sections"] = {}
        cond_data["enum_section_var"] = None
        cond_data["value_kind"] = None
        
        if not signal_def or cond_data.get("unknown_signal") or cond_data.get("unknown_operator"):
            entry = ttk.Entry(cond_data["value_widget_frame"], textvariable=cond_data["value_var"], width=15)
            entry.pack(fill=tk.X, expand=True)
            cond_data["value_widget"] = entry
            cond_data["value_kind"] = "text"
            cond_data["value_var"].trace_add("write", lambda *args: self._mark_changed())
            return

        signal_type = signal_def.get("type", "bool")
        
        if signal_type == "bool":
            # Boolean dropdown
            value_combo = ttk.Combobox(
                cond_data["value_widget_frame"],
                textvariable=cond_data["value_var"],
                values=["true", "false"],
                state="readonly",
                width=8
            )
            value_combo.pack(fill=tk.X, expand=True)
            cond_data["value_widget"] = value_combo
            cond_data["value_kind"] = "bool"
            cond_data["value_var"].trace_add("write", lambda *args: self._mark_changed())
            
            # Set default if empty
            if not cond_data["value_var"].get():
                value_combo.current(0)
        
        elif signal_type == "enum":
            # Get enum values
            value_labels, display_to_value, value_to_display = self._get_enum_display_maps(signal_def)
            cond_data["enum_display_to_value"] = display_to_value
            cond_data["enum_value_to_display"] = value_to_display
            signal_id = cond_data.get("signal_id")
            enum_sections = self._get_enum_hierarchy(signal_id, signal_def, value_to_display)
            cond_data["enum_sections"] = enum_sections or {}

            is_multi = op_token in ["in", "nin"]

            if is_multi and enum_sections:
                section_row = ttk.Frame(cond_data["value_widget_frame"])
                section_row.pack(fill=tk.X, expand=True)
                ttk.Label(section_row, text="Group:", width=6).pack(side=tk.LEFT, padx=(0, 4))
                section_names = sorted(enum_sections.keys(), key=str.casefold)
                section_var = tk.StringVar(value=section_names[0] if section_names else "")
                section_combo = ttk.Combobox(
                    section_row,
                    textvariable=section_var,
                    values=section_names,
                    state="readonly",
                    width=20
                )
                section_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
                cond_data["enum_section_var"] = section_var

                list_frame = ttk.Frame(cond_data["value_widget_frame"])
                list_frame.pack(fill=tk.X, expand=True)

                listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=6)
                listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

                cond_data["value_listbox"] = listbox
                cond_data["value_kind"] = "enum_multi"

                selected_label = ttk.Label(cond_data["value_widget_frame"], text="", foreground="gray")
                selected_label.pack(fill=tk.X, pady=(2, 0))
                cond_data["value_selected_label"] = selected_label

                def refresh_listbox():
                    selected_values = {
                        cond_data["enum_display_to_value"].get(listbox.get(i), listbox.get(i))
                        for i in listbox.curselection()
                    }
                    listbox.delete(0, tk.END)
                    labels = sorted(enum_sections.get(section_var.get(), []), key=str.casefold)
                    for label in labels:
                        listbox.insert(tk.END, label)
                    for idx, label in enumerate(listbox.get(0, tk.END)):
                        raw = cond_data["enum_display_to_value"].get(label, label)
                        if raw in selected_values:
                            listbox.selection_set(idx)
                    on_select()

                def on_select(event=None):
                    selections = [listbox.get(i) for i in listbox.curselection()]
                    if selections:
                        selected_label.configure(text="Selected: " + ", ".join(selections))
                    else:
                        selected_label.configure(text="")
                    self._mark_changed()

                section_combo.bind("<<ComboboxSelected>>", lambda event=None: refresh_listbox())
                listbox.bind("<<ListboxSelect>>", on_select)
                refresh_listbox()
                cond_data["value_widget"] = listbox
            elif is_multi:
                list_frame = ttk.Frame(cond_data["value_widget_frame"])
                list_frame.pack(fill=tk.X, expand=True)

                sorted_labels = sorted(value_labels, key=str.casefold)
                listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=min(4, max(1, len(sorted_labels))))
                for label in sorted_labels:
                    listbox.insert(tk.END, label)
                listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

                cond_data["value_listbox"] = listbox
                cond_data["value_kind"] = "enum_multi"

                selected_label = ttk.Label(cond_data["value_widget_frame"], text="", foreground="gray")
                selected_label.pack(fill=tk.X, pady=(2, 0))
                cond_data["value_selected_label"] = selected_label

                def on_select(event=None):
                    selections = [listbox.get(i) for i in listbox.curselection()]
                    if selections:
                        selected_label.configure(text="Selected: " + ", ".join(selections))
                    else:
                        selected_label.configure(text="")
                    self._mark_changed()

                listbox.bind("<<ListboxSelect>>", on_select)
                cond_data["value_widget"] = listbox
            elif enum_sections:
                section_row = ttk.Frame(cond_data["value_widget_frame"])
                section_row.pack(fill=tk.X, expand=True)

                ttk.Label(section_row, text="Group:", width=6).pack(side=tk.LEFT, padx=(0, 4))
                section_names = sorted(enum_sections.keys(), key=str.casefold)
                section_var = tk.StringVar(value=section_names[0] if section_names else "")
                section_combo = ttk.Combobox(
                    section_row,
                    textvariable=section_var,
                    values=section_names,
                    state="readonly",
                    width=20
                )
                section_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
                cond_data["enum_section_var"] = section_var

                value_combo = ttk.Combobox(
                    cond_data["value_widget_frame"],
                    textvariable=cond_data["value_var"],
                    values=[],
                    state="readonly",
                    width=22
                )
                value_combo.pack(fill=tk.X, expand=True, pady=(2, 0))
                cond_data["value_widget"] = value_combo
                cond_data["value_kind"] = "enum_single"
                cond_data["value_var"].trace_add("write", lambda *args: self._mark_changed())

                def refresh_values():
                    labels = sorted(enum_sections.get(section_var.get(), []), key=str.casefold)
                    value_combo["values"] = labels
                    current = cond_data["value_var"].get()
                    if current not in labels:
                        cond_data["value_var"].set(labels[0] if labels else "")

                section_combo.bind("<<ComboboxSelected>>", lambda event=None: refresh_values())
                refresh_values()
            else:
                value_combo = ttk.Combobox(
                    cond_data["value_widget_frame"],
                    textvariable=cond_data["value_var"],
                    values=sorted(value_labels, key=str.casefold),
                    state="readonly",
                    width=15
                )
                value_combo.pack(fill=tk.X, expand=True)
                cond_data["value_widget"] = value_combo
                cond_data["value_kind"] = "enum_single"
                cond_data["value_var"].trace_add("write", lambda *args: self._mark_changed())

                if not cond_data["value_var"].get() and value_labels:
                    value_combo.current(0)

        else:
            # Handle numeric, string, and other types with a text entry
            entry = ttk.Entry(cond_data["value_widget_frame"], textvariable=cond_data["value_var"], width=15)
            entry.pack(fill=tk.X, expand=True)
            cond_data["value_widget"] = entry
            cond_data["value_kind"] = "text"
            cond_data["value_var"].trace_add("write", lambda *args: self._mark_changed())

    def _get_enum_hierarchy(
        self,
        signal_id: Optional[str],
        signal_def: Dict[str, Any],
        value_to_display: Dict[Any, str],
    ) -> Optional[Dict[str, List[str]]]:
        """Return grouped enum labels for hierarchical selection when available."""
        if not signal_id:
            return None

        source_mapping = signal_def.get("source_mapping", {})
        category_id = source_mapping.get("category_id")
        is_journal_event = signal_id == "journal_event" or category_id == "all-journal"
        is_edmc_event = signal_id == "edmc_event" or category_id == "all-events"
        if not is_journal_event and not is_edmc_event:
            return None

        source_taxonomy = getattr(self.catalog, "_data", {}).get("source_taxonomy", {})
        inventory = source_taxonomy.get("inventory", {})
        journal_inventory = inventory.get("journal", {})
        by_section = journal_inventory.get("by_section", [])
        if not isinstance(by_section, list) or not by_section:
            return None

        grouped: Dict[str, List[str]] = {}
        all_labels: List[str] = []
        for section_data in by_section:
            section_name = section_data.get("section")
            if not section_name:
                continue
            labels: List[str] = []
            for event_data in section_data.get("events", []):
                event_name = event_data.get("name")
                if event_name in value_to_display:
                    display = value_to_display[event_name]
                    labels.append(display)
                    if display not in all_labels:
                        all_labels.append(display)
            if labels:
                labels.sort(key=str.casefold)
                prefix = "Journal / " if is_edmc_event else ""
                grouped[f"{prefix}{section_name}"] = labels

        if is_edmc_event:
            dashboard_events = inventory.get("notifications", {}).get("events", [])
            dashboard_labels: List[str] = []
            for event_data in dashboard_events:
                event_name = event_data.get("name")
                if event_name in value_to_display:
                    label = value_to_display[event_name]
                    dashboard_labels.append(label)
                    if label not in all_labels:
                        all_labels.append(label)
            if dashboard_labels:
                dashboard_labels.sort(key=str.casefold)
                grouped["Dashboard"] = dashboard_labels

            capi_events = inventory.get("capi", {}).get("events", [])
            capi_groups: Dict[str, List[str]] = {}
            source_group_label = {
                "capi": "CAPI / Live",
                "capi_legacy": "CAPI / Legacy",
                "capi_fleetcarrier": "CAPI / Fleet Carrier",
            }
            for event_data in capi_events:
                event_name = event_data.get("name")
                source_name = event_data.get("source", "capi")
                if event_name in value_to_display:
                    label = value_to_display[event_name]
                    group_name = source_group_label.get(source_name, "CAPI")
                    capi_groups.setdefault(group_name, []).append(label)
                    if label not in all_labels:
                        all_labels.append(label)
            for group_name, labels in capi_groups.items():
                grouped[group_name] = sorted(labels, key=str.casefold)

        if not grouped:
            return None

        if len(grouped) > 1:
            all_labels.sort(key=str.casefold)
            grouped = {"All": all_labels, **grouped}
        return grouped
    
    def _set_condition_value(self, cond_data: Dict, value: Any):
        """Set the value for a condition after widget is created."""
        if value is None:
            return

        if cond_data.get("value_kind") == "enum_multi" and cond_data.get("value_listbox"):
            listbox = cond_data["value_listbox"]
            values = value if isinstance(value, list) else [value]
            for val in values:
                display = cond_data["enum_value_to_display"].get(val)
                if display is None:
                    display = f"Unknown value: {val}"
                    listbox.insert(tk.END, display)
                    cond_data["unknown_value"] = True
                idx = listbox.get(0, tk.END).index(display)
                listbox.selection_set(idx)
            if cond_data.get("value_selected_label"):
                selections = [listbox.get(i) for i in listbox.curselection()]
                if selections:
                    cond_data["value_selected_label"].configure(text="Selected: " + ", ".join(selections))
        elif isinstance(value, bool):
            cond_data["value_var"].set(str(value).lower())
        elif isinstance(value, list):
            cond_data["value_var"].set(", ".join(str(v) for v in value))
        else:
            display = cond_data["enum_value_to_display"].get(value)
            if display is None and cond_data.get("value_kind") in ["enum_single", "enum_multi"]:
                display = f"Unknown value: {value}"
                cond_data["unknown_value"] = True
                if cond_data.get("value_widget") and isinstance(cond_data["value_widget"], ttk.Combobox):
                    values = list(cond_data["value_widget"]["values"])
                    if display not in values:
                        values.insert(0, display)
                        cond_data["value_widget"]["values"] = values
            section_var = cond_data.get("enum_section_var")
            enum_sections = cond_data.get("enum_sections", {})
            if section_var and enum_sections and display:
                for section_name, labels in enum_sections.items():
                    if display in labels:
                        section_var.set(section_name)
                        widget = cond_data.get("value_widget")
                        if widget and isinstance(widget, ttk.Combobox):
                            widget["values"] = labels
                        break
            cond_data["value_var"].set(str(display) if display else str(value))

    def _get_enum_display_maps(self, signal_def: Dict) -> Tuple[List[str], Dict[str, Any], Dict[Any, str]]:
        """Build enum display mappings from a signal definition."""
        display_to_value: Dict[str, Any] = {}
        value_to_display: Dict[Any, str] = {}
        display_values: List[str] = []

        for item in signal_def.get("values", []):
            value = item.get("value")
            label = item.get("label", value)
            display_values.append(label)
            display_to_value[label] = value
            value_to_display[value] = label

        display_values = sorted(display_values, key=str.casefold)
        return display_values, display_to_value, value_to_display

    def _apply_condition_from_rule(self, cond_data: Dict, condition: Dict[str, Any]):
        """Populate condition row from a rule condition dict."""
        signal_id = condition.get("signal")
        if signal_id:
            signal_def = self.all_signals.get(signal_id)
            if signal_def:
                # Set category first
                category = signal_def.get("ui", {}).get("category", "Other")
                cond_data["category_var"].set(category)
                
                # Populate items for this category
                self._populate_items_for_category(cond_data["item_combo"], category, cond_data)
                
                # Find which item (group or signal) contains this signal_id
                item_key, child_key = self._find_item_for_signal(category, signal_id)
                
                if item_key:
                    # Get the display name for this item
                    item_display = cond_data.get("item_key_to_display", {}).get(item_key, item_key)
                    cond_data["item_var"].set(item_display)
                    cond_data["selected_item_key"] = item_key
                    
                    if child_key:
                        # This signal is in a group - set up the child dropdown
                        cond_data["is_group"] = True
                        self._populate_children_for_group(cond_data, category, item_key)
                        # Set the child
                        child_display = self.signal_id_to_simple_display.get(signal_id, child_key)
                        cond_data["child_var"].set(child_display)
                    else:
                        # This is a direct signal
                        cond_data["is_group"] = False
                        cond_data["child_combo"].pack_forget()
                    
                    cond_data["signal_id"] = signal_id
                else:
                    # Couldn't find in hierarchy - show as unknown
                    simple_display = self.signal_id_to_simple_display.get(signal_id, signal_id)
                    cond_data["item_var"].set(simple_display)
                    cond_data["signal_id"] = signal_id
            else:
                unknown_display = f"Unknown signal: {signal_id}"
                cond_data["unknown_signal"] = True
                cond_data["signal_id"] = signal_id
                self._ensure_combo_value(cond_data["item_combo"], unknown_display)
                cond_data["item_var"].set(unknown_display)

        self._on_condition_signal_changed(cond_data, initial_condition=condition)

        op_token = condition.get("op")
        if op_token:
            display = self.operator_token_to_display.get(op_token)
            if display:
                cond_data["op_var"].set(display)
            else:
                unknown_op = f"Unknown operator: {op_token}"
                cond_data["unknown_operator"] = True
                self._ensure_combo_value(cond_data["op_combo"], unknown_op)
                cond_data["op_var"].set(unknown_op)

        self._on_condition_operator_changed(cond_data, initial_condition=condition)
        self._set_condition_value(cond_data, condition.get("value"))
        self._update_when_hint()
    
    def _find_item_for_signal(self, category: str, signal_id: str) -> tuple:
        """Find which item (and optionally child) contains the given signal_id.
        
        Returns:
            (item_key, child_key) where child_key is None if it's a direct signal
        """
        if category not in self.hierarchy_by_category:
            return (None, None)
        
        for item_key, item_data in self.hierarchy_by_category[category].items():
            if item_data.get("is_signal"):
                # Check if this direct signal matches
                if item_data.get("signal_id") == signal_id:
                    return (item_key, None)
            elif item_data.get("is_group"):
                # Check children of this group
                children = item_data.get("children", {})
                for child_key, child_data in children.items():
                    if child_data.get("signal_id") == signal_id:
                        return (item_key, child_key)
        
        return (None, None)

    def _set_condition_error(self, cond_data: Dict, message: str):
        """Set inline error message for a condition row."""
        error_label = cond_data["error_label"]
        if message:
            error_label.configure(text=message)
            if not error_label.winfo_ismapped():
                error_label.pack(fill=tk.X, padx=4, pady=0)
        else:
            error_label.configure(text="")
            error_label.pack_forget()

    def _update_when_hint(self):
        """Show or hide the empty-state hint for conditions."""
        if not hasattr(self, "when_hint_label"):
            return
        if self.all_conditions or self.any_conditions:
            self.when_hint_label.pack_forget()
        else:
            self.when_hint_label.pack(pady=10)

    def _refresh_condition_order(self, group: str):
        """Repack condition rows in their current list order."""
        target_list = self.all_conditions if group == "all" else self.any_conditions
        add_button = self.all_add_button if group == "all" else self.any_add_button

        for cond_data in target_list:
            cond_data["frame"].pack_forget()
            cond_data["frame"].pack(fill=tk.X, pady=2, before=add_button)

    def _move_condition(self, cond_data: Dict, direction: int):
        """Move a condition row up or down within its group."""
        target_list = self.all_conditions if cond_data["group"] == "all" else self.any_conditions
        index = target_list.index(cond_data)
        new_index = index + direction
        if new_index < 0 or new_index >= len(target_list):
            return
        target_list.insert(new_index, target_list.pop(index))
        self._refresh_condition_order(cond_data["group"])
        self._mark_changed()

    def _duplicate_condition(self, cond_data: Dict):
        """Duplicate an existing condition row."""
        condition = self._build_condition_from_ui(cond_data, allow_unknown=True)
        if not condition and cond_data.get("raw_condition"):
            condition = dict(cond_data["raw_condition"])
        if not condition:
            return

        self._add_condition(cond_data["group"], condition)
        self._mark_changed()
    
    def _build_then_section(self, parent):
        """Build the Then Actions section."""
        actions_frame = ttk.LabelFrame(parent, text="Then (when rule becomes TRUE)", padding=4)
        actions_frame.pack(fill=tk.X, pady=(0, 4))
        
        # Shifts (unified 3-state selector)
        shifts_row = ttk.Frame(actions_frame)
        shifts_row.pack(fill=tk.X)
        
        # Find existing shifts
        existing_set_shifts = []
        existing_clear_shifts = []
        for action in self.rule.get("then", []):
            if "vkb_set_shift" in action:
                shifts = action["vkb_set_shift"]
                existing_set_shifts = shifts if isinstance(shifts, list) else [shifts]
            elif "vkb_clear_shift" in action:
                shifts = action["vkb_clear_shift"]
                existing_clear_shifts = shifts if isinstance(shifts, list) else [shifts]

        shift_vars = self._build_shift_checkbox_row(shifts_row, existing_set_shifts, existing_clear_shifts)
        self.shift_vars = shift_vars
    

    def _build_else_section(self, parent):
        """Build the Else Actions section."""
        else_frame = ttk.LabelFrame(parent, text="Else (when rule becomes FALSE)", padding=4)
        else_frame.pack(fill=tk.X)
        
        # Shifts (unified 3-state selector)
        shifts_row = ttk.Frame(else_frame)
        shifts_row.pack(fill=tk.X)
        
        # Find existing shifts
        existing_set_shifts = []
        existing_clear_shifts = []
        for action in self.rule.get("else", []):
            if "vkb_set_shift" in action:
                shifts = action["vkb_set_shift"]
                existing_set_shifts = shifts if isinstance(shifts, list) else [shifts]
            elif "vkb_clear_shift" in action:
                shifts = action["vkb_clear_shift"]
                existing_clear_shifts = shifts if isinstance(shifts, list) else [shifts]
        
        else_shift_vars = self._build_shift_checkbox_row(shifts_row, existing_set_shifts, existing_clear_shifts)
        self.else_shift_vars = else_shift_vars

    def _build_shift_checkbox_row(self, parent, existing_tokens_for_set: List[str], existing_tokens_for_clear: List[str] = None) -> List[Tuple[str, tk.StringVar]]:
        """Build Shift/SubShift 3-state checkboxes on one line with labels.
        
        Args:
            parent: Parent widget
            existing_tokens_for_set: Tokens that should be in "on" state
            existing_tokens_for_clear: Tokens that should be in "off" state (optional)
        
        Returns:
            List of (token, StringVar) tuples where StringVar is 'off', 'on', or 'ignored'
        """
        if existing_tokens_for_clear is None:
            existing_tokens_for_clear = []
        
        shift_vars: List[Tuple[str, tk.StringVar]] = []

        def token_label(token: str) -> str:
            digits = "".join(ch for ch in token if ch.isdigit())
            return digits or token

        ttk.Label(parent, text="Shift:").pack(side=tk.LEFT, padx=(0, 6))
        for token in SHIFT_TOKENS:
            # Determine initial state
            if token in existing_tokens_for_set:
                state = 'on'
            elif token in existing_tokens_for_clear:
                state = 'off'
            else:
                state = 'ignored'
            
            var = tk.StringVar(value=state)
            cb = ThreeStateCheckbutton(
                parent, 
                text=token_label(token), 
                variable=var, 
                command=lambda: self._mark_changed()
            )
            cb.pack(side=tk.LEFT, padx=2)
            shift_vars.append((token, var))

        ttk.Label(parent, text="SubShift:").pack(side=tk.LEFT, padx=(8, 6))
        for token in SUBSHIFT_TOKENS:
            # Determine initial state
            if token in existing_tokens_for_set:
                state = 'on'
            elif token in existing_tokens_for_clear:
                state = 'off'
            else:
                state = 'ignored'
            
            var = tk.StringVar(value=state)
            cb = ThreeStateCheckbutton(
                parent, 
                text=token_label(token), 
                variable=var, 
                command=lambda: self._mark_changed()
            )
            cb.pack(side=tk.LEFT, padx=2)
            shift_vars.append((token, var))

        return shift_vars
    


    def _on_title_changed(self):
        """Handle title changes for change tracking and ID preview."""
        self._mark_changed()
        self._update_id_preview()

    def _update_id_preview(self):
        """Update the displayed ID preview."""
        if self.rule.get("id"):
            self.id_preview_var.set(self.rule.get("id"))
        else:
            preview = generate_id_from_title(self.title_var.get().strip() or "rule")
            self.id_preview_var.set(f"{preview} (generated on save)")
    
    def _mark_changed(self):
        """Mark that the rule has been modified by comparing current state to original."""
        # Skip during initial load to avoid false positives
        if getattr(self, '_loading', True):
            return
        # Build the current rule from UI and compare with original
        try:
            current_rule = self._build_rule_from_ui()
            # Deep comparison of the rule structure
            self.has_changes = (json.dumps(current_rule, sort_keys=True) !=
                               json.dumps(self.original_rule, sort_keys=True))
        except Exception:
            # If we can't build/compare, assume there are changes to be safe
            self.has_changes = True
    
    def _validate_rule(self) -> Tuple[bool, List[str]]:
        """
        Validate the current rule.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Title is required
        if not self.title_var.get().strip():
            errors.append("Title is required")
        
        # Validate conditions
        for cond_data in self.all_conditions + self.any_conditions:
            row_errors = []
            signal_id = cond_data.get("signal_id")
            op = cond_data["op_var"].get()

            if not signal_id:
                row_errors.append("Select a signal")
            elif cond_data.get("unknown_signal"):
                row_errors.append("Unknown signal")

            if not op:
                row_errors.append("Select an operator")
            elif cond_data.get("unknown_operator"):
                row_errors.append("Unknown operator")

            if cond_data.get("unknown_value"):
                row_errors.append("Unknown value")

            value_kind = cond_data.get("value_kind")
            if value_kind == "enum_multi":
                listbox = cond_data.get("value_listbox")
                if not listbox or not listbox.curselection():
                    row_errors.append("Select one or more values")
            elif value_kind in ["bool", "enum_single", "text"]:
                if not cond_data["value_var"].get().strip():
                    row_errors.append("Select a value")

            if row_errors:
                self._set_condition_error(cond_data, "; ".join(row_errors))
                errors.extend(row_errors)
            else:
                self._set_condition_error(cond_data, "")
        
        # Actions are optional and simplified - no specific validation needed
        
        return (len(errors) == 0, errors)
    
    def _build_rule_from_ui(self) -> Dict[str, Any]:
        """Build the rule dictionary from UI state."""
        # Basic fields
        rule = {
            "title": self.title_var.get().strip(),
            "enabled": self.enabled_var.get(),
            "when": {"all": [], "any": []},
            "then": [],
            "else": []
        }
        
        # Generate ID if not present
        if self.rule.get("id"):
            rule["id"] = self.rule["id"]
        # ID will be generated by rules engine if needed
        
        # Build conditions
        for cond_data in self.all_conditions:
            cond = self._build_condition_from_ui(cond_data)
            if cond:
                rule["when"]["all"].append(cond)
        
        for cond_data in self.any_conditions:
            cond = self._build_condition_from_ui(cond_data)
            if cond:
                rule["when"]["any"].append(cond)
        
        # Build Then actions from 3-state checkboxes
        if hasattr(self, "shift_vars"):
            set_shifts = [token for token, var in self.shift_vars if var.get() == 'on']
            clear_shifts = [token for token, var in self.shift_vars if var.get() == 'off']
            
            if set_shifts:
                rule["then"].append({"vkb_set_shift": set_shifts})
            if clear_shifts:
                rule["then"].append({"vkb_clear_shift": clear_shifts})
        
        # Build Else actions from 3-state checkboxes
        if hasattr(self, "else_shift_vars"):
            set_shifts = [token for token, var in self.else_shift_vars if var.get() == 'on']
            clear_shifts = [token for token, var in self.else_shift_vars if var.get() == 'off']
            
            if set_shifts:
                rule["else"].append({"vkb_set_shift": set_shifts})
            if clear_shifts:
                rule["else"].append({"vkb_clear_shift": clear_shifts})
        
        return rule
    
    def _build_condition_from_ui(self, cond_data: Dict, allow_unknown: bool = False) -> Optional[Dict[str, Any]]:
        """Build a condition dictionary from UI state."""
        if cond_data.get("unknown_signal") or cond_data.get("unknown_operator") or cond_data.get("unknown_value"):
            if allow_unknown and cond_data.get("raw_condition"):
                return dict(cond_data["raw_condition"])
            return None

        signal_id = cond_data.get("signal_id")
        op_token = self._get_operator_token(cond_data["op_var"].get())

        if not signal_id or not op_token:
            if allow_unknown and cond_data.get("raw_condition"):
                return dict(cond_data["raw_condition"])
            return None

        signal_def = self.all_signals.get(signal_id)
        signal_type = signal_def.get("type", "bool") if signal_def else "text"

        if signal_type == "bool":
            value = cond_data["value_var"].get().lower() == "true"
        elif signal_type == "enum":
            if cond_data.get("value_kind") == "enum_multi":
                listbox = cond_data.get("value_listbox")
                if not listbox:
                    return None
                selected = [listbox.get(i) for i in listbox.curselection()]
                value = [cond_data["enum_display_to_value"].get(v, v) for v in selected]
            else:
                display = cond_data["value_var"].get()
                value = cond_data["enum_display_to_value"].get(display, display)
        else:
            value = cond_data["value_var"].get()

        return {
            "signal": signal_id,
            "op": op_token,
            "value": value
        }
    
    def _save(self):
        """Save the rule."""
        # Validate
        is_valid, errors = self._validate_rule()
        
        if not is_valid:
            error_msg = "Cannot save rule:\n\n" + "\n".join(f"• {err}" for err in errors)
            _centered_error(self.parent.winfo_toplevel(), "Validation Error", error_msg)
            return
        
        # Build rule from UI
        updated_rule = self._build_rule_from_ui()
        
        # Call save callback
        self.on_save_callback(updated_rule)
    
    def _on_back(self):
        """Handle back button."""
        if self.has_changes:
            if _centered_yesno(self.parent.winfo_toplevel(), "Unsaved Changes", "You have unsaved changes. Discard them?"):
                self.on_cancel_callback()
        else:
            self.on_cancel_callback()


def show_rule_editor(parent, rules_file: Path, plugin_dir: Path, initial_rule_index: Optional[int] = None):
    """
    Show the rule editor UI.
    
    Args:
        parent: Parent tkinter widget
        rules_file: Path to rules.json file
        plugin_dir: Plugin directory path
    """
    try:
        editor = RuleEditorUI(parent, rules_file, plugin_dir, initial_rule_index=initial_rule_index)
        return editor.window
    except Exception as e:
        logger.error(f"Failed to open rule editor: {e}", exc_info=True)
        messagebox.showerror("Error", f"Failed to open rule editor:\n{e}", parent=parent)
        return None

