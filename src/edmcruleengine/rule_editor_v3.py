"""
V3 Catalog-Driven Rule Editor UI for EDMC VKB Connector.

Provides a visual editor for creating and editing rules using the v3 schema:
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


class V3RuleEditorUI:
    """
    Main UI for v3 catalog-driven rule editor.
    
    Provides rules list view and rule editor with catalog-driven controls.
    """
    
    def __init__(self, parent, rules_file: Path, plugin_dir: Path):
        """
        Initialize the v3 rule editor UI.
        
        Args:
            parent: Parent tkinter widget
            rules_file: Path to rules.json file
            plugin_dir: Plugin directory path for catalog
        """
        self.parent = parent
        self.rules_file = rules_file
        self.plugin_dir = plugin_dir
        
        # Try to load catalog
        self.catalog: Optional[SignalsCatalog] = None
        self.catalog_error: Optional[str] = None
        try:
            self.catalog = SignalsCatalog.from_plugin_dir(str(plugin_dir))
            logger.info(f"Loaded signals catalog v{self.catalog.version}")
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
        
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("VKB Rule Editor (v3)")
        self.window.geometry("1000x700")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Build UI
        self._build_ui()
        
        # Center window
        self.window.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.window.winfo_height()) // 2
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
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header with New Rule button
        header_frame = ttk.Frame(list_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Rules", font=("TkDefaultFont", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(header_frame, text="➕ New Rule", command=self._new_rule).pack(side=tk.RIGHT)
        
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
            empty_frame.pack(pady=50)
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
    
    def _create_rule_list_item(self, parent, idx: int, rule: Dict[str, Any]):
        """Create a single rule list item."""
        item_frame = ttk.LabelFrame(parent, text="", padding=10)
        item_frame.pack(fill=tk.X, pady=5)
        
        # Top row: enabled toggle, title, actions
        top_row = ttk.Frame(item_frame)
        top_row.pack(fill=tk.X)
        
        # Enabled toggle
        enabled_var = tk.BooleanVar(value=rule.get("enabled", True))
        def toggle_enabled():
            self.rules[idx]["enabled"] = enabled_var.get()
            self.unsaved_changes = True
            self._save_rules()
        
        ttk.Checkbutton(
            top_row,
            text="",
            variable=enabled_var,
            command=toggle_enabled
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Title
        title = rule.get("title", rule.get("id", "Untitled"))
        ttk.Label(
            top_row,
            text=title,
            font=("TkDefaultFont", 11, "bold")
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Actions
        ttk.Button(top_row, text="✏️ Edit", width=8, command=lambda: self._edit_rule(idx)).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_row, text="📋 Duplicate", width=12, command=lambda: self._duplicate_rule(idx)).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_row, text="🗑️ Delete", width=10, command=lambda: self._delete_rule(idx)).pack(side=tk.RIGHT, padx=2)
        
        # Summary row
        summary = self._generate_rule_summary(rule)
        if summary:
            summary_label = ttk.Label(item_frame, text=summary, foreground="gray")
            summary_label.pack(fill=tk.X, pady=(5, 0))
    
    def _generate_rule_summary(self, rule: Dict[str, Any]) -> str:
        """Generate a short summary of the rule."""
        parts = []
        
        # When conditions
        when = rule.get("when", {})
        all_conds = when.get("all", [])
        any_conds = when.get("any", [])
        
        if all_conds or any_conds:
            cond_parts = []
            if all_conds:
                cond_parts.append(f"{len(all_conds)} ALL")
            if any_conds:
                cond_parts.append(f"{len(any_conds)} ANY")
            parts.append(f"When: {' and '.join(cond_parts)}")
        else:
            parts.append("When: (always)")
        
        # Then actions
        then_actions = rule.get("then", [])
        if then_actions:
            parts.append(f"Then: {len(then_actions)} action(s)")
        
        # Else actions
        else_actions = rule.get("else", [])
        if else_actions:
            parts.append(f"Else: {len(else_actions)} action(s)")
        
        return " • ".join(parts)
    
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
        editor = V3RuleEditor(
            self.view_container,
            self.rules[self.editing_rule_index],
            self.catalog,
            self._on_save_rule,
            self._on_cancel_edit
        )
    
    def _on_save_rule(self, updated_rule: Dict[str, Any]):
        """Callback when rule is saved from editor."""
        if self.editing_rule_index is not None:
            self.rules[self.editing_rule_index] = updated_rule
            self.unsaved_changes = True
            self._save_rules()
            self.editing_rule_index = None
            self._show_rules_list()
            messagebox.showinfo("Saved", "Rule saved successfully")
    
    def _on_cancel_edit(self):
        """Callback when edit is cancelled."""
        self.editing_rule_index = None
        self._show_rules_list()
    
    def _on_close(self):
        """Handle window close."""
        if self.unsaved_changes:
            if messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Close anyway?"):
                self.window.destroy()
        else:
            self.window.destroy()


class V3RuleEditor:
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
        
        # Build signal lookup tables from catalog
        self._build_lookup_tables()
        
        # Tier filter state
        self.show_detail_tier = tk.BooleanVar(value=False)
        
        # Build UI
        self._build_ui()
    
    def _build_lookup_tables(self):
        """Build lookup tables from catalog for efficient access."""
        # Get all signals organized by category
        self.signals_by_category: Dict[str, List[Tuple[str, Dict]]] = {}
        self.all_signals: Dict[str, Dict] = {}
        
        for signal_id, signal_def in self.catalog.get_signals().items():
            self.all_signals[signal_id] = signal_def
            category = signal_def.get("ui", {}).get("category", "Other")
            if category not in self.signals_by_category:
                self.signals_by_category[category] = []
            self.signals_by_category[category].append((signal_id, signal_def))
        
        # Get operators
        self.operators = self.catalog.get_operators()
        
        # Get tiers
        self.tiers = self.catalog.get_tiers()
    
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
        
        # Save/Cancel buttons at bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="💾 Save", command=self._save, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_back, width=15).pack(side=tk.RIGHT)
    
    def _build_basic_fields(self, parent):
        """Build basic fields (title, enabled, id)."""
        basic_frame = ttk.LabelFrame(parent, text="Basic Information", padding=10)
        basic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title (required)
        title_row = ttk.Frame(basic_frame)
        title_row.pack(fill=tk.X, pady=5)
        ttk.Label(title_row, text="Title:*", width=15).pack(side=tk.LEFT)
        self.title_var = tk.StringVar(value=self.rule.get("title", ""))
        self.title_var.trace_add("write", lambda *args: self._mark_changed())
        ttk.Entry(title_row, textvariable=self.title_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Enabled toggle
        enabled_row = ttk.Frame(basic_frame)
        enabled_row.pack(fill=tk.X, pady=5)
        ttk.Label(enabled_row, text="Enabled:", width=15).pack(side=tk.LEFT)
        self.enabled_var = tk.BooleanVar(value=self.rule.get("enabled", True))
        self.enabled_var.trace_add("write", lambda *args: self._mark_changed())
        ttk.Checkbutton(enabled_row, variable=self.enabled_var).pack(side=tk.LEFT)
        
        # Optional ID display (read-only, hidden by default)
        if self.rule.get("id"):
            id_row = ttk.Frame(basic_frame)
            id_row.pack(fill=tk.X, pady=5)
            ttk.Label(id_row, text="ID:", width=15, foreground="gray").pack(side=tk.LEFT)
            ttk.Label(id_row, text=self.rule.get("id"), foreground="gray").pack(side=tk.LEFT)
    
    def _build_when_section(self, parent):
        """Build the When condition builder section."""
        when_frame = ttk.LabelFrame(parent, text="When (Conditions)", padding=10)
        when_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Tier toggle
        tier_frame = ttk.Frame(when_frame)
        tier_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(tier_frame, text="Signals:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            tier_frame,
            text=f"🌟 {self.tiers['core']['label']} only",
            variable=self.show_detail_tier,
            value=False,
            command=self._on_tier_changed
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            tier_frame,
            text=f"🌟 {self.tiers['core']['label']} + {self.tiers['detail']['label']}",
            variable=self.show_detail_tier,
            value=True,
            command=self._on_tier_changed
        ).pack(side=tk.LEFT, padx=5)
        
        # All of these (all)
        self.all_frame = ttk.LabelFrame(when_frame, text="✓ All of these", padding=10)
        self.all_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.all_conditions = []
        self._load_conditions("all")
        
        ttk.Button(self.all_frame, text="➕ Add condition", command=lambda: self._add_condition("all")).pack(pady=(5, 0))
        
        # Any of these (any)
        self.any_frame = ttk.LabelFrame(when_frame, text="⚡ Any of these", padding=10)
        self.any_frame.pack(fill=tk.X)
        
        self.any_conditions = []
        self._load_conditions("any")
        
        ttk.Button(self.any_frame, text="➕ Add condition", command=lambda: self._add_condition("any")).pack(pady=(5, 0))
        
        # Empty state hints
        if not self.all_conditions and not self.any_conditions:
            hint_label = ttk.Label(when_frame, text="💡 Add conditions to control when this rule fires", foreground="gray")
            hint_label.pack(pady=10)
    
    def _load_conditions(self, group: str):
        """Load existing conditions for a group."""
        conditions = self.rule.get("when", {}).get(group, [])
        for cond in conditions:
            self._add_condition(group, cond)
    
    def _add_condition(self, group: str, condition: Optional[Dict] = None):
        """Add a condition row to the specified group."""
        target_frame = self.all_frame if group == "all" else self.any_frame
        target_list = self.all_conditions if group == "all" else self.any_conditions
        
        # Condition row frame
        cond_frame = ttk.Frame(target_frame)
        cond_frame.pack(fill=tk.X, pady=2, before=target_frame.winfo_children()[-1])  # Insert before Add button
        
        # Signal dropdown
        signal_var = tk.StringVar(value=condition.get("signal", "") if condition else "")
        signal_combo = ttk.Combobox(cond_frame, textvariable=signal_var, state="readonly", width=25)
        signal_combo.pack(side=tk.LEFT, padx=2)
        
        # Operator dropdown
        op_var = tk.StringVar(value=condition.get("op", "") if condition else "")
        op_combo = ttk.Combobox(cond_frame, textvariable=op_var, state="readonly", width=12)
        op_combo.pack(side=tk.LEFT, padx=2)
        
        # Value control (dynamic based on signal type)
        value_var = tk.StringVar(value=str(condition.get("value", "")) if condition else "")
        value_widget_frame = ttk.Frame(cond_frame)
        value_widget_frame.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Remove button
        def remove_cond():
            cond_frame.destroy()
            target_list.remove(cond_data)
            self._mark_changed()
        
        ttk.Button(cond_frame, text="🗑️", width=3, command=remove_cond).pack(side=tk.RIGHT, padx=2)
        
        # Store condition data
        cond_data = {
            "frame": cond_frame,
            "group": group,
            "signal_var": signal_var,
            "signal_combo": signal_combo,
            "op_var": op_var,
            "op_combo": op_combo,
            "value_var": value_var,
            "value_widget_frame": value_widget_frame,
            "value_widget": None
        }
        target_list.append(cond_data)
        
        # Populate signal dropdown
        self._populate_signal_dropdown(signal_combo)
        
        # Setup signal change handler
        def on_signal_change(event=None):
            self._on_condition_signal_changed(cond_data)
            self._mark_changed()
        
        signal_combo.bind("<<ComboboxSelected>>", on_signal_change)
        
        # If loading existing condition, trigger signal change to populate operator and value
        if condition:
            on_signal_change()
            # Set value after widget is created
            self._set_condition_value(cond_data, condition.get("value"))
        
        # Setup operator change handler
        op_combo.bind("<<ComboboxSelected>>", lambda e: self._mark_changed())
    
    def _populate_signal_dropdown(self, combo: ttk.Combobox):
        """Populate signal dropdown with filtered signals."""
        signals = []
        show_detail = self.show_detail_tier.get()
        
        for category in sorted(self.signals_by_category.keys()):
            for signal_id, signal_def in self.signals_by_category[category]:
                tier = signal_def.get("ui", {}).get("tier", "core")
                if tier == "core" or show_detail:
                    label = signal_def.get("ui", {}).get("label", signal_id)
                    signals.append(f"{category}: {label}")
        
        combo['values'] = signals
    
    def _on_tier_changed(self):
        """Handle tier filter toggle."""
        # Repopulate all signal dropdowns
        for cond_data in self.all_conditions + self.any_conditions:
            self._populate_signal_dropdown(cond_data["signal_combo"])
    
    def _on_condition_signal_changed(self, cond_data: Dict):
        """Handle signal selection change in a condition."""
        signal_text = cond_data["signal_var"].get()
        if not signal_text or ": " not in signal_text:
            return
        
        # Extract signal ID from "Category: Label" format
        signal_label = signal_text.split(": ", 1)[1]
        signal_id = None
        
        # Find signal ID by label
        for sid, sdef in self.all_signals.items():
            if sdef.get("ui", {}).get("label") == signal_label:
                signal_id = sid
                break
        
        if not signal_id:
            return
        
        signal_def = self.all_signals[signal_id]
        signal_type = signal_def.get("type", "bool")
        
        # Update operator dropdown based on signal type
        if signal_type == "bool":
            ops = ["eq", "ne"]
        elif signal_type == "enum":
            ops = ["eq", "ne", "in", "nin"]
        else:
            ops = list(self.operators.keys())
        
        op_labels = [f"{self.operators[op]['symbol']} {self.operators[op]['label']}" for op in ops]
        cond_data["op_combo"]['values'] = op_labels
        
        # Set default operator if not set
        if not cond_data["op_var"].get():
            cond_data["op_combo"].current(0)
        
        # Update value widget based on signal type
        self._update_condition_value_widget(cond_data, signal_id, signal_def)
    
    def _update_condition_value_widget(self, cond_data: Dict, signal_id: str, signal_def: Dict):
        """Update the value widget for a condition based on signal type."""
        # Clear existing value widget
        for widget in cond_data["value_widget_frame"].winfo_children():
            widget.destroy()
        
        signal_type = signal_def.get("type", "bool")
        
        if signal_type == "bool":
            # Boolean dropdown
            value_combo = ttk.Combobox(
                cond_data["value_widget_frame"],
                textvariable=cond_data["value_var"],
                values=["true", "false"],
                state="readonly",
                width=10
            )
            value_combo.pack(fill=tk.X, expand=True)
            cond_data["value_widget"] = value_combo
            
            # Set default if empty
            if not cond_data["value_var"].get():
                value_combo.current(0)
        
        elif signal_type == "enum":
            # Get enum values
            enum_values = signal_def.get("values", [])
            value_labels = [v.get("label", v.get("value")) for v in enum_values]
            
            # Check if operator uses multi-select (in/nin)
            op_text = cond_data["op_var"].get()
            is_multi = "In list" in op_text or "Not in list" in op_text
            
            if is_multi:
                # Multi-select listbox (simplified - would need more complex widget in production)
                value_label = ttk.Label(
                    cond_data["value_widget_frame"],
                    text="(Multi-select: click items)",
                    foreground="gray"
                )
                value_label.pack()
                cond_data["value_widget"] = value_label
            else:
                # Single-select dropdown
                value_combo = ttk.Combobox(
                    cond_data["value_widget_frame"],
                    textvariable=cond_data["value_var"],
                    values=value_labels,
                    state="readonly",
                    width=20
                )
                value_combo.pack(fill=tk.X, expand=True)
                cond_data["value_widget"] = value_combo
                
                # Set default if empty
                if not cond_data["value_var"].get() and value_labels:
                    value_combo.current(0)
    
    def _set_condition_value(self, cond_data: Dict, value: Any):
        """Set the value for a condition after widget is created."""
        if value is None:
            return
        
        if isinstance(value, bool):
            cond_data["value_var"].set(str(value).lower())
        elif isinstance(value, list):
            # Multi-select values (simplified representation)
            cond_data["value_var"].set(", ".join(str(v) for v in value))
        else:
            cond_data["value_var"].set(str(value))
    
    def _build_then_section(self, parent):
        """Build the Then actions section."""
        then_frame = ttk.LabelFrame(
            parent,
            text="Then (when it becomes true) - fires on false → true",
            padding=10
        )
        then_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.then_actions = []
        self._load_actions("then", then_frame)
        
        ttk.Button(then_frame, text="➕ Add action", command=lambda: self._add_action("then", then_frame)).pack(pady=(5, 0))
        
        if not self.then_actions:
            hint_label = ttk.Label(then_frame, text="💡 Add actions to execute when conditions become true", foreground="gray")
            hint_label.pack(pady=5)
    
    def _build_else_section(self, parent):
        """Build the Else actions section."""
        else_frame = ttk.LabelFrame(
            parent,
            text="Else (when it becomes false) - fires on true → false",
            padding=10
        )
        else_frame.pack(fill=tk.X)
        
        self.else_actions = []
        self._load_actions("else", else_frame)
        
        ttk.Button(else_frame, text="➕ Add action", command=lambda: self._add_action("else", else_frame)).pack(pady=(5, 0))
        
        if not self.else_actions:
            hint_label = ttk.Label(else_frame, text="💡 Add actions to execute when conditions become false", foreground="gray")
            hint_label.pack(pady=5)
    
    def _load_actions(self, group: str, parent_frame):
        """Load existing actions for a group."""
        actions = self.rule.get(group, [])
        for action in actions:
            self._add_action(group, parent_frame, action)
    
    def _add_action(self, group: str, parent_frame, action: Optional[Dict] = None):
        """Add an action row to the specified group."""
        target_list = self.then_actions if group == "then" else self.else_actions
        
        # Action frame
        action_frame = ttk.Frame(parent_frame)
        action_frame.pack(fill=tk.X, pady=2, before=parent_frame.winfo_children()[-1])  # Insert before Add button
        
        # Action type dropdown
        action_type_var = tk.StringVar(value="")
        if action:
            if "vkb_set_shift" in action:
                action_type_var.set("vkb_set_shift")
            elif "vkb_clear_shift" in action:
                action_type_var.set("vkb_clear_shift")
            elif "log" in action:
                action_type_var.set("log")
        
        type_combo = ttk.Combobox(
            action_frame,
            textvariable=action_type_var,
            values=["vkb_set_shift", "vkb_clear_shift", "log"],
            state="readonly",
            width=20
        )
        type_combo.pack(side=tk.LEFT, padx=2)
        
        # Value frame (dynamic based on action type)
        value_frame = ttk.Frame(action_frame)
        value_frame.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Remove button
        def remove_action():
            action_frame.destroy()
            target_list.remove(action_data)
            self._mark_changed()
        
        ttk.Button(action_frame, text="🗑️", width=3, command=remove_action).pack(side=tk.RIGHT, padx=2)
        
        # Store action data
        action_data = {
            "frame": action_frame,
            "group": group,
            "type_var": action_type_var,
            "type_combo": type_combo,
            "value_frame": value_frame,
            "value_widgets": []
        }
        target_list.append(action_data)
        
        # Setup type change handler
        def on_type_change(event=None):
            self._update_action_value_widget(action_data, action)
            self._mark_changed()
        
        type_combo.bind("<<ComboboxSelected>>", on_type_change)
        
        # If loading existing action, populate value widget
        if action:
            on_type_change()
    
    def _update_action_value_widget(self, action_data: Dict, initial_action: Optional[Dict] = None):
        """Update the value widget for an action based on type."""
        # Clear existing widgets
        for widget in action_data["value_frame"].winfo_children():
            widget.destroy()
        action_data["value_widgets"] = []
        
        action_type = action_data["type_var"].get()
        
        if action_type in ["vkb_set_shift", "vkb_clear_shift"]:
            # Shift token multi-select
            ttk.Label(action_data["value_frame"], text="Tokens:").pack(side=tk.LEFT, padx=(0, 5))
            
            # Get initial tokens
            initial_tokens = []
            if initial_action and action_type in initial_action:
                initial_tokens = initial_action[action_type]
            
            # Create checkbuttons for each token
            for token in ALL_SHIFT_TOKENS:
                var = tk.BooleanVar(value=token in initial_tokens)
                cb = ttk.Checkbutton(action_data["value_frame"], text=token, variable=var)
                cb.pack(side=tk.LEFT, padx=2)
                action_data["value_widgets"].append((token, var))
        
        elif action_type == "log":
            # Log message text entry
            ttk.Label(action_data["value_frame"], text="Message:").pack(side=tk.LEFT, padx=(0, 5))
            
            initial_message = ""
            if initial_action and "log" in initial_action:
                initial_message = initial_action["log"]
            
            message_var = tk.StringVar(value=initial_message)
            entry = ttk.Entry(action_data["value_frame"], textvariable=message_var, width=40)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            action_data["value_widgets"].append(("message", message_var))
    
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
            signal = cond_data["signal_var"].get()
            op = cond_data["op_var"].get()
            value = cond_data["value_var"].get()
            
            if not signal:
                errors.append("All conditions must have a signal selected")
            if not op:
                errors.append("All conditions must have an operator selected")
            if not value:
                errors.append("All conditions must have a value")
        
        # Validate actions
        for action_data in self.then_actions + self.else_actions:
            action_type = action_data["type_var"].get()
            
            if not action_type:
                errors.append("All actions must have a type selected")
                continue
            
            if action_type in ["vkb_set_shift", "vkb_clear_shift"]:
                # Check that at least one token is selected
                selected = [token for token, var in action_data["value_widgets"] if var.get()]
                if not selected:
                    errors.append(f"{action_type} must have at least one token selected")
            
            elif action_type == "log":
                # Check that message is not empty
                message = next((var.get() for name, var in action_data["value_widgets"] if name == "message"), "")
                if not message.strip():
                    errors.append("Log action must have a non-empty message")
        
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
        
        # Build actions
        for action_data in self.then_actions:
            action = self._build_action_from_ui(action_data)
            if action:
                rule["then"].append(action)
        
        for action_data in self.else_actions:
            action = self._build_action_from_ui(action_data)
            if action:
                rule["else"].append(action)
        
        return rule
    
    def _build_condition_from_ui(self, cond_data: Dict) -> Optional[Dict[str, Any]]:
        """Build a condition dictionary from UI state."""
        signal_text = cond_data["signal_var"].get()
        op_text = cond_data["op_var"].get()
        value_text = cond_data["value_var"].get()
        
        if not signal_text or not op_text:
            return None
        
        # Extract signal ID from "Category: Label"
        signal_label = signal_text.split(": ", 1)[1] if ": " in signal_text else signal_text
        signal_id = None
        for sid, sdef in self.all_signals.items():
            if sdef.get("ui", {}).get("label") == signal_label:
                signal_id = sid
                break
        
        if not signal_id:
            return None
        
        # Extract operator token from "symbol label"
        op_token = None
        for token, op_def in self.operators.items():
            if f"{op_def['symbol']} {op_def['label']}" == op_text:
                op_token = token
                break
        
        if not op_token:
            return None
        
        # Parse value based on signal type
        signal_def = self.all_signals[signal_id]
        signal_type = signal_def.get("type", "bool")
        
        if signal_type == "bool":
            value = value_text.lower() == "true"
        elif signal_type == "enum":
            # Find enum value by label
            enum_value = None
            for v in signal_def.get("values", []):
                if v.get("label") == value_text:
                    enum_value = v.get("value")
                    break
            value = enum_value if enum_value else value_text
        else:
            value = value_text
        
        return {
            "signal": signal_id,
            "op": op_token,
            "value": value
        }
    
    def _build_action_from_ui(self, action_data: Dict) -> Optional[Dict[str, Any]]:
        """Build an action dictionary from UI state."""
        action_type = action_data["type_var"].get()
        
        if not action_type:
            return None
        
        if action_type in ["vkb_set_shift", "vkb_clear_shift"]:
            # Collect selected tokens
            tokens = [token for token, var in action_data["value_widgets"] if var.get()]
            if not tokens:
                return None
            return {action_type: tokens}
        
        elif action_type == "log":
            # Get log message
            message = next((var.get() for name, var in action_data["value_widgets"] if name == "message"), "")
            if not message.strip():
                return None
            return {"log": message.strip()}
        
        return None
    
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


def show_v3_rule_editor(parent, rules_file: Path, plugin_dir: Path):
    """
    Show the v3 rule editor UI.
    
    Args:
        parent: Parent tkinter widget
        rules_file: Path to rules.json file
        plugin_dir: Plugin directory path
    """
    try:
        editor = V3RuleEditorUI(parent, rules_file, plugin_dir)
        return editor.window
    except Exception as e:
        logger.error(f"Failed to open rule editor: {e}", exc_info=True)
        messagebox.showerror("Error", f"Failed to open rule editor:\n{e}")
        return None
