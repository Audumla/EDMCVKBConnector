"""
Catalog-Driven Rule Editor UI for EDMC VKB Connector.

Provides a visual editor for creating and editing rules using the schema:
- Catalog-driven signals, operators, and enum values
- Two-tier signal visibility (core/detail)
- When builder with all/any conditions
- Then/Else actions with edge-triggered semantics
- Inline validation and error handling
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from . import plugin_logger
from .signals_catalog import SignalsCatalog, CatalogError, generate_id_from_title

logger = plugin_logger(__name__)

# Shift tokens for VKB actions
SHIFT_TOKENS = ["Shift1", "Shift2"]
SUBSHIFT_TOKENS = [f"Subshift{i}" for i in range(1, 8)]
ALL_SHIFT_TOKENS = SHIFT_TOKENS + SUBSHIFT_TOKENS


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
        self.catalog_path = Path(plugin_dir) / "signals_catalog.json"
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
        
        # Current view state
        self.current_view = "list"  # "list" or "editor"
        self.editing_rule_index: Optional[int] = None
        self.active_editor: Optional["RuleEditor"] = None
        
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("VKB Rule Editor")
        self.window.geometry("1000x700")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Build UI
        self._build_ui()

        if initial_rule_index is not None and not self.catalog_error:
            if 0 <= initial_rule_index < len(self.rules):
                self._edit_rule(initial_rule_index)

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
            messagebox.showerror("Error", f"Failed to load rules:\n{e}")
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
            messagebox.showerror("Error", f"Failed to save rules:\n{e}")
            raise
    
    def _build_ui(self):
        """Build the main UI."""
        # Check for catalog error first
        if self.catalog_error:
            self._show_catalog_error()
            return
        
        # Create container for swappable views
        self.view_container = ttk.Frame(self.window)
        self.view_container.pack(fill=tk.BOTH, expand=True)
        
        # Show rules list by default
        self._show_rules_list()

    def _reload_catalog(self):
        """Reload the signals catalog and refresh the UI."""
        if self.current_view == "editor" and self.active_editor and self.active_editor.has_changes:
            if not messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes. Reloading the catalog will discard them. Continue?"
            ):
                return
        try:
            self.catalog = SignalsCatalog.from_plugin_dir(str(self.plugin_dir))
            self.catalog_error = None
            logger.info("Reloaded signals catalog")
            if self.current_view == "editor" and self.editing_rule_index is not None:
                self._show_rule_editor()
            else:
                self._show_rules_list()
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
            text="❌ Catalog Error",
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
        
        ttk.Button(error_frame, text="Close", command=self.window.destroy).pack()
    
    def _show_rules_list(self):
        """Show the rules list view."""
        # Clear container
        for widget in self.view_container.winfo_children():
            widget.destroy()
        
        self.current_view = "list"
        
        # Create list view
        list_frame = ttk.Frame(self.view_container)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Header with New Rule button
        header_frame = ttk.Frame(list_frame)
        header_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(header_frame, text="Rules", font=("TkDefaultFont", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(header_frame, text="➕ New Rule", command=self._new_rule).pack(side=tk.RIGHT)
        ttk.Button(header_frame, text="⟲ Reload catalog", command=self._reload_catalog).pack(side=tk.RIGHT, padx=5)
        
        # Rules list with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=canvas.yview)
        rules_frame = ttk.Frame(canvas)
        
        canvas_window = canvas.create_window((0, 0), window=rules_frame, anchor="nw")
        
        def _on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def _on_canvas_configure(event):
            canvas.itemconfigure(canvas_window, width=event.width)
        
        rules_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add rules
        if not self.rules:
            # Empty state
            empty_frame = ttk.Frame(rules_frame)
            empty_frame.pack(pady=30)
            ttk.Label(
                empty_frame,
                text="No rules yet",
                font=("TkDefaultFont", 12)
            ).pack()
            ttk.Label(
                empty_frame,
                text='Click "➕ New Rule" to create your first rule',
                foreground="gray"
            ).pack()
        else:
            for idx, rule in enumerate(self.rules):
                self._create_rule_list_item(rules_frame, idx, rule)

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
        if self.current_view == "editor" and self.active_editor and self.active_editor.has_changes:
            if not self.pending_catalog_reload:
                self.pending_catalog_reload = True
                messagebox.showinfo(
                    "Catalog Changed",
                    "Signals catalog changed on disk. Save or cancel your edits to reload."
                )
            return

        self.pending_catalog_reload = False
        self._reload_catalog()
    
    def _create_rule_list_item(self, parent, idx: int, rule: Dict[str, Any]):
        """Create a single rule list item."""
        item_frame = ttk.Frame(parent)
        item_frame.pack(fill=tk.X, pady=3)
        
        # Top row: title (with ID and enabled status) + actions
        top_row = ttk.Frame(item_frame)
        top_row.pack(fill=tk.X)
        
        # Title with ID and enabled status indicator
        title = rule.get("title", rule.get("id", "Untitled"))
        rule_id = rule.get("id", "")
        enabled = rule.get("enabled", True)
        
        # Build title label with ID and status
        title_parts = [title]
        if rule_id:
            title_parts.append(f"[{rule_id}]")
        enabled_marker = "●" if enabled else "○"
        title_text = f"{enabled_marker} {' '.join(title_parts)}"
        
        ttk.Label(
            top_row,
            text=title_text,
            font=("TkDefaultFont", 10, "bold")
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Actions (compact)
        ttk.Button(top_row, text="Edit", width=6, command=lambda: self._edit_rule(idx)).pack(side=tk.RIGHT, padx=1)
        ttk.Button(top_row, text="Dup", width=4, command=lambda: self._duplicate_rule(idx)).pack(side=tk.RIGHT, padx=1)
        ttk.Button(top_row, text="Del", width=4, command=lambda: self._delete_rule(idx)).pack(side=tk.RIGHT, padx=1)
        
        # Summary row - readable prose format
        summary = self._generate_rule_summary(rule)
        if summary:
            summary_label = ttk.Label(item_frame, text=summary, foreground="gray", font=("TkDefaultFont", 9), wraplength=900, justify=tk.LEFT)
            summary_label.pack(fill=tk.X, padx=30, pady=(0, 2))
    
    def _generate_rule_summary(self, rule: Dict[str, Any]) -> str:
        """Generate a readable summary of the rule."""
        parts = []
        
        # When conditions
        when = rule.get("when", {})
        all_conds = when.get("all", [])
        any_conds = when.get("any", [])
        
        if all_conds or any_conds:
            cond_descriptions = []
            
            # Add ALL conditions
            for cond in all_conds:
                desc = self._describe_condition(cond)
                if desc:
                    cond_descriptions.append(desc)
            
            # Add ANY conditions
            if any_conds:
                any_descs = []
                for cond in any_conds:
                    desc = self._describe_condition(cond)
                    if desc:
                        any_descs.append(desc)
                if any_descs:
                    cond_descriptions.append(f"({' OR '.join(any_descs)})")
            
            if cond_descriptions:
                parts.append(f"When: {' AND '.join(cond_descriptions)}")
            else:
                parts.append("When: (always)")
        else:
            parts.append("When: (always)")
        
        # Then actions
        then_actions = rule.get("then", [])
        if then_actions:
            action_parts = []
            for action in then_actions:
                for action_type, value in action.items():
                    if action_type == "vkb_set_shift":
                        tokens = value if isinstance(value, list) else [value]
                        action_parts.append(f"Set {', '.join(tokens)}")
                    elif action_type == "vkb_clear_shift":
                        tokens = value if isinstance(value, list) else [value]
                        action_parts.append(f"Clear {', '.join(tokens)}")
                    elif action_type == "log":
                        action_parts.append(f'Log "{value}"')
            if action_parts:
                parts.append(f"Then: {'; '.join(action_parts)}")
        
        # Else actions
        else_actions = rule.get("else", [])
        if else_actions:
            action_parts = []
            for action in else_actions:
                for action_type, value in action.items():
                    if action_type == "vkb_set_shift":
                        tokens = value if isinstance(value, list) else [value]
                        action_parts.append(f"Set {', '.join(tokens)}")
                    elif action_type == "vkb_clear_shift":
                        tokens = value if isinstance(value, list) else [value]
                        action_parts.append(f"Clear {', '.join(tokens)}")
                    elif action_type == "log":
                        action_parts.append(f'Log "{value}"')
            if action_parts:
                parts.append(f"Else: {'; '.join(action_parts)}")
        
        return " | ".join(parts)
    
    def _describe_condition(self, condition: Dict[str, Any]) -> Optional[str]:
        """Generate a readable description of a single condition."""
        signal_id = condition.get("signal")
        op_token = condition.get("op")
        value = condition.get("value")
        
        if not signal_id or not self.catalog:
            return None
        
        # Get signal name
        signal_def = self.catalog.signals.get(signal_id)
        if not signal_def:
            return None
        
        signal_name = signal_def.get("ui", {}).get("label", signal_id)
        
        # Get operator symbol
        op_def = self.catalog.operators.get(op_token)
        op_symbol = op_def.get("symbol", op_token) if op_def else op_token
        
        # Format value
        if isinstance(value, bool):
            value_str = str(value).lower()
        elif isinstance(value, list):
            # Look up enum display values
            signal_type = signal_def.get("type", "text")
            if signal_type == "enum":
                displays = []
                for v in value:
                    for item in signal_def.get("values", []):
                        if item.get("value") == v:
                            label = item.get("label", v)
                            displays.append(label)
                            break
                    else:
                        displays.append(str(v))
                value_str = ", ".join(displays)
            else:
                value_str = ", ".join(str(v) for v in value)
        else:
            # Single value - check if it's an enum
            signal_type = signal_def.get("type", "text")
            if signal_type == "enum":
                for item in signal_def.get("values", []):
                    if item.get("value") == value:
                        value_str = item.get("label", value)
                        break
                else:
                    value_str = str(value)
            else:
                value_str = str(value)
        
        return f"{signal_name} {op_symbol} {value_str}"
    
    def _new_rule(self):
        """Create a new rule."""
        new_rule = {
            "title": "New Rule",
            "enabled": True,
            "when": {"all": [], "any": []},
            "then": [],
            "else": []
        }
        self.rules.append(new_rule)
        self.unsaved_changes = True
        self._edit_rule(len(self.rules) - 1)
    
    def _edit_rule(self, idx: int):
        """Edit a rule."""
        self.editing_rule_index = idx
        self._show_rule_editor()
    
    def _duplicate_rule(self, idx: int):
        """Duplicate a rule."""
        original = self.rules[idx]
        duplicate = dict(original)
        
        # Modify title to indicate copy
        title = duplicate.get("title", "Rule")
        duplicate["title"] = f"{title} (copy)"
        
        # Remove ID so it gets regenerated
        if "id" in duplicate:
            del duplicate["id"]
        
        self.rules.insert(idx + 1, duplicate)
        self.unsaved_changes = True
        self._save_rules()
        self._show_rules_list()
        messagebox.showinfo("Duplicated", f'Rule "{title}" duplicated')
    
    def _delete_rule(self, idx: int):
        """Delete a rule with confirmation."""
        rule = self.rules[idx]
        title = rule.get("title", rule.get("id", "this rule"))
        
        if messagebox.askyesno("Confirm Delete", f'Delete rule "{title}"?'):
            del self.rules[idx]
            self.unsaved_changes = True
            self._save_rules()
            self._show_rules_list()
    
    def _show_rule_editor(self):
        """Show the rule editor view."""
        # Clear container
        for widget in self.view_container.winfo_children():
            widget.destroy()
        
        self.current_view = "editor"
        
        if self.editing_rule_index is None:
            logger.error("No rule index set for editing")
            return
        
        # Create editor (will be implemented in next phase)
        self.active_editor = RuleEditor(
            self.view_container,
            self.rules[self.editing_rule_index],
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
                    if r.get("id") and i != self.editing_rule_index
                }
                updated_rule["id"] = generate_id_from_title(updated_rule.get("title", ""), used_ids)
            self.rules[self.editing_rule_index] = updated_rule
            self.unsaved_changes = True
            self._save_rules()
            self.editing_rule_index = None
            self.active_editor = None
            self._show_rules_list()
            messagebox.showinfo("Saved", "Rule saved successfully")
            if self.pending_catalog_reload:
                self.pending_catalog_reload = False
                self._reload_catalog()
    
    def _on_cancel_edit(self):
        """Callback when edit is cancelled."""
        self.editing_rule_index = None
        self.active_editor = None
        self._show_rules_list()
        if self.pending_catalog_reload:
            self.pending_catalog_reload = False
            self._reload_catalog()
    
    def _on_close(self):
        """Handle window close."""
        if self.current_view == "editor" and self.active_editor and self.active_editor.has_changes:
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Close anyway?"):
                return
        if self.unsaved_changes:
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Close anyway?"):
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
        self.original_rule = dict(rule)
        self.rule = dict(rule)  # Working copy
        self.catalog = catalog
        self.on_save_callback = on_save
        self.on_cancel_callback = on_cancel
        
        # Track changes
        self.has_changes = False
        
        # Load icon mapping
        self._load_icon_map()
        
        # Build signal lookup tables from catalog
        self._build_lookup_tables()
        
        # Tier filter state - always show both tiers
        self.show_detail_tier = tk.BooleanVar(value=True)
        
        # Build UI
        self._build_ui()
    
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
        """Load icon name to character mapping from icon_map.json and ansi_icon_map.json."""
        self.icon_map: Dict[str, str] = {}
        self.ansi_icon_map: Dict[str, str] = {}
        try:
            icon_map_path = Path(__file__).parent.parent.parent / "icon_map.json"
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
        
        # Load ANSI icon map
        try:
            ansi_icon_path = Path(__file__).parent.parent.parent / "ansi_icon_map.json"
            if ansi_icon_path.exists():
                with open(ansi_icon_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.ansi_icon_map = data.get("icons", {})
                logger.debug(f"Loaded {len(self.ansi_icon_map)} ANSI icon mappings")
            else:
                logger.debug(f"ANSI icon map not found at {ansi_icon_path}")
        except Exception as e:
            logger.error(f"Failed to load ANSI icon map: {e}")

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
        
        # Header with back button
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(header_frame, text="← Back", command=self._on_back).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Edit Rule", font=("TkDefaultFont", 14, "bold")).pack(side=tk.LEFT, padx=10)
        
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

        # Save/Cancel buttons at bottom, right aligned under panels
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="💾 Save", command=self._save, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_back, width=15).pack(side=tk.RIGHT)
    
    def _build_basic_fields(self, parent):
        """Build basic fields (title, id)."""
        basic_frame = ttk.LabelFrame(parent, text="Basic Information", padding=10)
        basic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title (required)
        title_row = ttk.Frame(basic_frame)
        title_row.pack(fill=tk.X, pady=5)
        ttk.Label(title_row, text="Title:*", width=15).pack(side=tk.LEFT)
        self.title_var = tk.StringVar(value=self.rule.get("title", ""))
        self.title_var.trace_add("write", lambda *args: self._on_title_changed())
        ttk.Entry(title_row, textvariable=self.title_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Rule ID (always shown, read-only)
        self.id_preview_var = tk.StringVar(value="")
        id_row = ttk.Frame(basic_frame)
        id_row.pack(fill=tk.X, pady=5)
        ttk.Label(id_row, text="ID:", width=15, foreground="gray").pack(side=tk.LEFT)
        ttk.Label(id_row, textvariable=self.id_preview_var, foreground="gray").pack(side=tk.LEFT)
        self._update_id_preview()
        
        # Enabled state (always tracked internally, not shown in UI)
        self.enabled_var = tk.BooleanVar(value=self.rule.get("enabled", True))
        self.enabled_var.trace_add("write", lambda *args: self._mark_changed())
    
    def _build_when_section(self, parent):
        """Build the When condition builder section."""
        when_frame = ttk.LabelFrame(parent, text="When (Conditions) - Define when this rule activates", padding=8)
        when_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # All of these (all)
        self.all_frame = ttk.LabelFrame(when_frame, text="✓ All of these (AND logic)", padding=8)
        self.all_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.all_add_button = ttk.Button(self.all_frame, text="+ Add condition", command=lambda: self._add_condition("all"))
        self.all_add_button.pack(anchor=tk.W, pady=(3, 0))
        self.all_conditions = []
        self._load_conditions("all")
        
        # Any of these (any)
        self.any_frame = ttk.LabelFrame(when_frame, text="⚡ Any of these (OR logic)", padding=8)
        self.any_frame.pack(fill=tk.X)
        
        self.any_add_button = ttk.Button(self.any_frame, text="+ Add condition", command=lambda: self._add_condition("any"))
        self.any_add_button.pack(anchor=tk.W, pady=(3, 0))
        self.any_conditions = []
        self._load_conditions("any")

        # Empty state hints
        self.when_hint_label = ttk.Label(when_frame, text="💡 Add a condition to start", foreground="gray")
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
        cond_container.pack(fill=tk.X, pady=2, before=add_button)
        row_frame = ttk.Frame(cond_container)
        row_frame.pack(fill=tk.X)
        
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
        
        ttk.Button(row_frame, text="⧉", width=3, command=duplicate_row).pack(side=tk.RIGHT, padx=1)
        ttk.Button(row_frame, text="↓", width=3, command=move_down).pack(side=tk.RIGHT, padx=1)
        ttk.Button(row_frame, text="↑", width=3, command=move_up).pack(side=tk.RIGHT, padx=1)
        ttk.Button(row_frame, text="🗑️", width=3, command=remove_cond).pack(side=tk.RIGHT, padx=1)

        # Inline error label
        error_label = ttk.Label(cond_container, text="", foreground="red")
        error_label.pack(fill=tk.X, padx=4)
        
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
        cond_data["error_label"].configure(text=message)

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
        """Build the Combined Actions section (replaces separate Then/Else)."""
        actions_frame = ttk.LabelFrame(parent, text="Then (when rule becomes TRUE)", padding=8)
        actions_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Clear actions - inline with icon
        clear_row = ttk.Frame(actions_frame)
        clear_row.pack(fill=tk.X, pady=(0, 6))
        
        # Get clear icon from map
        clear_icon = self.icon_map.get("minus", "➖")
        ttk.Label(clear_row, text=clear_icon, font=("TkDefaultFont", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        # Find existing clear shifts
        existing_clear_shifts = []
        for action in self.rule.get("then", []):
            if "vkb_clear_shift" in action:
                shifts = action["vkb_clear_shift"]
                existing_clear_shifts = shifts if isinstance(shifts, list) else [shifts]
                break

        clear_shift_vars = self._build_shift_checkbox_row(clear_row, existing_clear_shifts)

        self.clear_shift_vars = clear_shift_vars
        
        # Set actions - inline with icon
        set_row = ttk.Frame(actions_frame)
        set_row.pack(fill=tk.X, pady=(0, 6))
        
        # Get set icon from map
        set_icon = self.icon_map.get("plus", "➕")
        ttk.Label(set_row, text=set_icon, font=("TkDefaultFont", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        # Find existing set shifts
        existing_set_shifts = []
        for action in self.rule.get("then", []):
            if "vkb_set_shift" in action:
                shifts = action["vkb_set_shift"]
                existing_set_shifts = shifts if isinstance(shifts, list) else [shifts]
                break

        set_shift_vars = self._build_shift_checkbox_row(set_row, existing_set_shifts)

        self.set_shift_vars = set_shift_vars
        
        # Log message - inline with icon
        log_row = ttk.Frame(actions_frame)
        log_row.pack(fill=tk.X)
        
        log_icon = self.icon_map.get("message", "💬")
        ttk.Label(log_row, text=log_icon, font=("TkDefaultFont", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        # Get existing log message
        log_message = ""
        for action in self.rule.get("then", []):
            if "log" in action:
                log_message = action["log"]
                break
        
        log_var = tk.StringVar(value=log_message)
        entry = ttk.Entry(log_row, textvariable=log_var, width=60)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.log_var = log_var
        log_var.trace_add("write", lambda *args: self._mark_changed())
    

    def _build_else_section(self, parent):
        """Build the Else Actions section."""
        else_frame = ttk.LabelFrame(parent, text="Else (when rule becomes FALSE)", padding=8)
        else_frame.pack(fill=tk.X)
        
        # Clear actions - inline with icon
        clear_row = ttk.Frame(else_frame)
        clear_row.pack(fill=tk.X, pady=(0, 6))
        
        # Get clear icon from map
        clear_icon = self.icon_map.get("minus", "➖")
        ttk.Label(clear_row, text=clear_icon, font=("TkDefaultFont", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        # Find existing clear shifts in else
        existing_clear_shifts = []
        for action in self.rule.get("else", []):
            if "vkb_clear_shift" in action:
                shifts = action["vkb_clear_shift"]
                existing_clear_shifts = shifts if isinstance(shifts, list) else [shifts]
                break

        else_clear_shift_vars = self._build_shift_checkbox_row(clear_row, existing_clear_shifts)

        self.else_clear_shift_vars = else_clear_shift_vars
        
        # Set actions - inline with icon
        set_row = ttk.Frame(else_frame)
        set_row.pack(fill=tk.X, pady=(0, 6))
        
        # Get set icon from map
        set_icon = self.icon_map.get("plus", "➕")
        ttk.Label(set_row, text=set_icon, font=("TkDefaultFont", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        # Find existing set shifts in else
        existing_set_shifts = []
        for action in self.rule.get("else", []):
            if "vkb_set_shift" in action:
                shifts = action["vkb_set_shift"]
                existing_set_shifts = shifts if isinstance(shifts, list) else [shifts]
                break

        else_set_shift_vars = self._build_shift_checkbox_row(set_row, existing_set_shifts)

        self.else_set_shift_vars = else_set_shift_vars
        
        # Log message - inline with icon
        log_row = ttk.Frame(else_frame)
        log_row.pack(fill=tk.X)
        
        log_icon = self.icon_map.get("message", "💬")
        ttk.Label(log_row, text=log_icon, font=("TkDefaultFont", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        # Get existing log message
        log_message = ""
        for action in self.rule.get("else", []):
            if "log" in action:
                log_message = action["log"]
                break
        
        else_log_var = tk.StringVar(value=log_message)
        entry = ttk.Entry(log_row, textvariable=else_log_var, width=60)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.else_log_var = else_log_var
        else_log_var.trace_add("write", lambda *args: self._mark_changed())

    def _build_shift_checkbox_row(self, parent, existing_tokens: List[str]) -> List[Tuple[str, tk.BooleanVar]]:
        """Build Shift/SubShift checkboxes on one line with labels."""
        shift_vars: List[Tuple[str, tk.BooleanVar]] = []

        def token_label(token: str) -> str:
            digits = "".join(ch for ch in token if ch.isdigit())
            return digits or token

        ttk.Label(parent, text="Shift:").pack(side=tk.LEFT, padx=(0, 6))
        for token in SHIFT_TOKENS:
            var = tk.BooleanVar(value=token in existing_tokens)
            cb = ttk.Checkbutton(parent, text=token_label(token), variable=var, command=lambda: self._mark_changed())
            cb.pack(side=tk.LEFT, padx=2)
            shift_vars.append((token, var))

        ttk.Label(parent, text="SubShift:").pack(side=tk.LEFT, padx=(8, 6))
        for token in SUBSHIFT_TOKENS:
            var = tk.BooleanVar(value=token in existing_tokens)
            cb = ttk.Checkbutton(parent, text=token_label(token), variable=var, command=lambda: self._mark_changed())
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
        """Mark that the rule has been modified."""
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
        
        # Build Then actions
        if hasattr(self, "clear_shift_vars"):
            clear_shift = [token for token, var in self.clear_shift_vars if var.get()]
            if clear_shift:
                rule["then"].append({"vkb_clear_shift": clear_shift})

        if hasattr(self, "set_shift_vars"):
            set_shift = [token for token, var in self.set_shift_vars if var.get()]
            if set_shift:
                rule["then"].append({"vkb_set_shift": set_shift})
        
        if hasattr(self, "log_var"):
            log_msg = self.log_var.get().strip()
            if log_msg:
                rule["then"].append({"log": log_msg})
        
        # Build Else actions
        if hasattr(self, "else_clear_shift_vars"):
            else_clear_shift = [token for token, var in self.else_clear_shift_vars if var.get()]
            if else_clear_shift:
                rule["else"].append({"vkb_clear_shift": else_clear_shift})

        if hasattr(self, "else_set_shift_vars"):
            else_set_shift = [token for token, var in self.else_set_shift_vars if var.get()]
            if else_set_shift:
                rule["else"].append({"vkb_set_shift": else_set_shift})
        
        if hasattr(self, "else_log_var"):
            else_log_msg = self.else_log_var.get().strip()
            if else_log_msg:
                rule["else"].append({"log": else_log_msg})
        
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
            messagebox.showerror("Validation Error", error_msg)
            return
        
        # Build rule from UI
        updated_rule = self._build_rule_from_ui()
        
        # Call save callback
        self.on_save_callback(updated_rule)
    
    def _on_back(self):
        """Handle back button."""
        if self.has_changes:
            if messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Discard them?"):
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
        messagebox.showerror("Error", f"Failed to open rule editor:\n{e}")
        return None

