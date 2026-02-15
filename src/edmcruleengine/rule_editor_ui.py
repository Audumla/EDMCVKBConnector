"""
Visual rule editor UI for EDMC VKB Connector.

Provides a structured editor for creating and editing rules with:
- When condition editor (source, event, all/any blocks)
- Then/Else action editor (shift flags, log statements)
- Event configuration from events_config.json
"""

import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .rule_validation import validate_rule

logger = logging.getLogger(__name__)

# Default shift flags if not found in config
DEFAULT_SHIFT_FLAGS = [
    "Shift1", "Shift2", "Subshift1", "Subshift2", "Subshift3",
    "Subshift4", "Subshift5", "Subshift6", "Subshift7"
]


class RuleEditorDialog:
    """Visual editor dialog for a single rule."""
    
    def __init__(self, parent, rule: Dict[str, Any], events_config: Dict[str, Any], 
                 flags_dict: Dict[str, int], flags2_dict: Dict[str, int], 
                 gui_focus_dict: Dict[str, int]):
        """
        Initialize rule editor dialog.
        
        Args:
            parent: Parent tkinter widget
            rule: Rule dictionary to edit
            events_config: Events configuration from events_config.json
            flags_dict: FLAGS dictionary from rules_engine
            flags2_dict: FLAGS2 dictionary from rules_engine
            gui_focus_dict: GUI_FOCUS_NAME_TO_VALUE dictionary from rules_engine
        """
        self.parent = parent
        self.original_rule = rule
        self.rule = dict(rule)  # Work with a copy
        self.events_config = events_config
        self.flags_dict = flags_dict
        self.flags2_dict = flags2_dict
        self.gui_focus_dict = gui_focus_dict
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Rule: {rule.get('id', 'New Rule')}")
        self.dialog.geometry("900x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._build_ui()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
    def _build_ui(self):
        """Build the complete UI."""
        # Main container with scrollbar
        main_canvas = tk.Canvas(self.dialog, highlightthickness=0)
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.dialog, orient=tk.VERTICAL, command=main_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame inside canvas
        main_frame = ttk.Frame(main_canvas)
        canvas_window = main_canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        def _on_frame_configure(event=None):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
            
        def _on_canvas_configure(event):
            main_canvas.itemconfigure(canvas_window, width=event.width)
            
        main_frame.bind("<Configure>", _on_frame_configure)
        main_canvas.bind("<Configure>", _on_canvas_configure)
        
        # Rule ID
        id_frame = ttk.Frame(main_frame)
        id_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(id_frame, text="Rule ID:").pack(side=tk.LEFT, padx=(0, 5))
        self.id_var = tk.StringVar(value=self.rule.get("id", ""))
        ttk.Entry(id_frame, textvariable=self.id_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Enabled checkbox
        self.enabled_var = tk.BooleanVar(value=self.rule.get("enabled", True))
        ttk.Checkbutton(id_frame, text="Enabled", variable=self.enabled_var).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Notebook for When/Then/Else tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # When tab
        when_frame = ttk.Frame(notebook)
        notebook.add(when_frame, text="When Conditions")
        self._build_when_tab(when_frame)
        
        # Then tab
        then_frame = ttk.Frame(notebook)
        notebook.add(then_frame, text="Then Actions")
        self._build_then_tab(then_frame)
        
        # Else tab
        else_frame = ttk.Frame(notebook)
        notebook.add(else_frame, text="Else Actions")
        self._build_else_tab(else_frame)
        
        # JSON Preview tab
        json_frame = ttk.Frame(notebook)
        notebook.add(json_frame, text="JSON Preview")
        self._build_json_tab(json_frame)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)
        
    def _build_when_tab(self, parent):
        """Build When conditions tab."""
        # Source filter
        source_frame = ttk.LabelFrame(parent, text="Source Filter", padding=10)
        source_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        when = self.rule.get("when", {})
        source_filter = when.get("source", "")
        
        self.source_var = tk.StringVar(value=source_filter if isinstance(source_filter, str) else "")
        ttk.Label(source_frame, text="Source:").pack(side=tk.LEFT, padx=(0, 5))
        source_combo = ttk.Combobox(source_frame, textvariable=self.source_var, width=20, state="readonly")
        source_combo["values"] = ["", "any"] + [s["id"] for s in self.events_config.get("sources", [])]
        source_combo.pack(side=tk.LEFT)
        source_combo.bind("<<ComboboxSelected>>", lambda e: self._update_event_list())
        
        # Event filter
        event_frame = ttk.LabelFrame(parent, text="Event Filter", padding=10)
        event_frame.pack(fill=tk.X, padx=10, pady=5)
        
        event_filter = when.get("event", "")
        self.event_var = tk.StringVar(value=event_filter if isinstance(event_filter, str) else "")
        ttk.Label(event_frame, text="Event:").pack(side=tk.LEFT, padx=(0, 5))
        self.event_combo = ttk.Combobox(event_frame, textvariable=self.event_var, width=30)
        self.event_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._update_event_list()
        
        # Condition blocks
        conditions_frame = ttk.LabelFrame(parent, text="Condition Blocks", padding=10)
        conditions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # All blocks
        all_label_frame = ttk.Frame(conditions_frame)
        all_label_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(all_label_frame, text="ALL blocks (every condition must match):", 
                 font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT)
        ttk.Button(all_label_frame, text="+ Add ALL Block", 
                  command=lambda: self._add_condition_block("all")).pack(side=tk.RIGHT)
        
        self.all_blocks_frame = ttk.Frame(conditions_frame)
        self.all_blocks_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Any blocks
        any_label_frame = ttk.Frame(conditions_frame)
        any_label_frame.pack(fill=tk.X, pady=(10, 5))
        ttk.Label(any_label_frame, text="ANY blocks (at least one condition must match):", 
                 font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT)
        ttk.Button(any_label_frame, text="+ Add ANY Block", 
                  command=lambda: self._add_condition_block("any")).pack(side=tk.RIGHT)
        
        self.any_blocks_frame = ttk.Frame(conditions_frame)
        self.any_blocks_frame.pack(fill=tk.BOTH, expand=True)
        
        # Load existing blocks
        self._load_condition_blocks()
        
    def _build_then_tab(self, parent):
        """Build Then actions tab."""
        self._build_actions_tab(parent, "then")
        
    def _build_else_tab(self, parent):
        """Build Else actions tab."""
        self._build_actions_tab(parent, "else")
        
    def _build_actions_tab(self, parent, action_type: str):
        """Build Then or Else actions tab."""
        actions = self.rule.get(action_type, {})
        
        # Log statement
        log_frame = ttk.LabelFrame(parent, text="Log Statement", padding=10)
        log_frame.pack(fill=tk.X, padx=10, pady=10)
        
        log_var = tk.StringVar(value=actions.get("log", ""))
        if action_type == "then":
            self.then_log_var = log_var
        else:
            self.else_log_var = log_var
            
        ttk.Label(log_frame, text="Message:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(log_frame, textvariable=log_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Shift flags
        shift_frame = ttk.LabelFrame(parent, text="VKB Shift Flags", padding=10)
        shift_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Get current set/clear lists
        set_shifts = actions.get("vkb_set_shift", [])
        clear_shifts = actions.get("vkb_clear_shift", [])
        
        # Get shift flags from config (supports both old and new format)
        shift_flags_config = self.events_config.get("shift_flags", [])
        shift_flags = []
        
        for flag in shift_flags_config:
            if isinstance(flag, dict):
                # New format with id/name/description
                shift_flags.append({
                    "id": flag.get("id", ""),
                    "name": flag.get("name", flag.get("id", "")),
                    "description": flag.get("description", "")
                })
            else:
                # Old format (just string)
                shift_flags.append({
                    "id": flag,
                    "name": flag,
                    "description": ""
                })
        
        # Fallback if no config
        if not shift_flags:
            for flag_id in DEFAULT_SHIFT_FLAGS:
                shift_flags.append({
                    "id": flag_id,
                    "name": flag_id,
                    "description": ""
                })
        
        # Calculate max width for consistent alignment
        max_name_len = max(len(f["name"]) for f in shift_flags) if shift_flags else 15
        label_width = max(15, max_name_len + 2)
        
        shift_vars = {}
        for flag_info in shift_flags:
            flag_id = flag_info["id"]
            flag_name = flag_info["name"]
            
            flag_frame = ttk.Frame(shift_frame)
            flag_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(flag_frame, text=f"{flag_name}:", width=label_width).pack(side=tk.LEFT)
            
            # State: Set, Clear, or Unchanged
            state_var = tk.StringVar(value="unchanged")
            if flag_id in set_shifts:
                state_var.set("set")
            elif flag_id in clear_shifts:
                state_var.set("clear")
                
            ttk.Radiobutton(flag_frame, text="Set", variable=state_var, 
                           value="set").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(flag_frame, text="Clear", variable=state_var, 
                           value="clear").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(flag_frame, text="Unchanged", variable=state_var, 
                           value="unchanged").pack(side=tk.LEFT, padx=5)
            
            # Store by flag_id (not name) for proper serialization
            shift_vars[flag_id] = state_var
            
        if action_type == "then":
            self.then_shift_vars = shift_vars
        else:
            self.else_shift_vars = shift_vars
            
    def _build_json_tab(self, parent):
        """Build JSON preview tab."""
        self.json_text = tk.Text(parent, wrap="none", width=80, height=30)
        self.json_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        json_scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.json_text.yview)
        json_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.json_text.configure(yscrollcommand=json_scroll_y.set)
        
        json_scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.json_text.xview)
        json_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.json_text.configure(xscrollcommand=json_scroll_x.set)
        
        refresh_btn = ttk.Button(parent, text="Refresh Preview", command=self._update_json_preview)
        refresh_btn.pack(pady=(0, 10))
        
        self._update_json_preview()
        
    def _update_event_list(self):
        """Update event dropdown based on selected source."""
        source = self.source_var.get()
        events = []
        
        for event in self.events_config.get("events", []):
            if not source or source == "any" or event.get("source") == source:
                title = event.get("title", event.get("event", ""))
                event_id = event.get("event", "")
                events.append(f"{title} ({event_id})")
                
        self.event_combo["values"] = [""] + events
        
    def _load_condition_blocks(self):
        """Load existing condition blocks into UI."""
        when = self.rule.get("when", {})
        
        # Load ALL blocks
        for block in when.get("all", []):
            self._add_condition_block("all", block)
            
        # Load ANY blocks
        for block in when.get("any", []):
            self._add_condition_block("any", block)
            
    def _add_condition_block(self, block_type: str, block_data: Optional[Dict] = None):
        """Add a new condition block to UI."""
        parent_frame = self.all_blocks_frame if block_type == "all" else self.any_blocks_frame
        
        # Create frame for this block
        block_frame = ttk.LabelFrame(parent_frame, text=f"{block_type.upper()} Condition Block", padding=5)
        block_frame.pack(fill=tk.X, pady=5)
        
        # Condition type selector with description
        type_frame = ttk.Frame(block_frame)
        type_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(type_frame, text="What to check:").pack(side=tk.LEFT, padx=(0, 5))
        
        cond_type_var = tk.StringVar(value="flags")
        if block_data:
            # Detect type from block data
            if "flags" in block_data:
                cond_type_var.set("flags")
            elif "flags2" in block_data:
                cond_type_var.set("flags2")
            elif "gui_focus" in block_data:
                cond_type_var.set("gui_focus")
            elif "field" in block_data:
                cond_type_var.set("field")
        
        # Build condition type dropdown with descriptions
        condition_types = self.events_config.get("condition_types", [])
        type_display_names = []
        type_map = {}
        
        for ct in condition_types:
            ct_id = ct["id"]
            ct_name = ct.get("name", ct_id)
            type_display_names.append(ct_name)
            type_map[ct_name] = ct_id
            
        type_combo = ttk.Combobox(type_frame, textvariable=cond_type_var, width=20, state="readonly")
        type_combo["values"] = [ct["id"] for ct in condition_types]
        type_combo.pack(side=tk.LEFT)
        
        # Add help text for selected type
        help_label = ttk.Label(type_frame, text="", foreground="gray")
        help_label.pack(side=tk.LEFT, padx=(10, 0))
        
        def update_help_text(event=None):
            selected = cond_type_var.get()
            for ct in condition_types:
                if ct["id"] == selected:
                    help_label.configure(text=f"({ct.get('description', '')})")
                    break
        
        type_combo.bind("<<ComboboxSelected>>", update_help_text)
        update_help_text()  # Set initial help text
        
        # Details frame (changes based on type)
        details_frame = ttk.Frame(block_frame)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Store for JSON conversion
        block_frame.condition_type_var = cond_type_var
        block_frame.details_frame = details_frame
        block_frame.block_data = block_data or {}
        
        # Build initial details
        self._build_condition_details(block_frame)
        
        # Update details when type changes
        def on_type_change(event):
            self._build_condition_details(block_frame)
        type_combo.bind("<<ComboboxSelected>>", on_type_change)
        
        # Remove button
        remove_btn = ttk.Button(block_frame, text="Remove Block", 
                               command=lambda: self._remove_condition_block(block_frame))
        remove_btn.pack(side=tk.RIGHT, pady=(5, 0))
        
    def _build_condition_details(self, block_frame):
        """Build condition details based on type."""
        # Clear existing details
        for widget in block_frame.details_frame.winfo_children():
            widget.destroy()
            
        cond_type = block_frame.condition_type_var.get()
        block_data = block_frame.block_data
        details_frame = block_frame.details_frame
        
        if cond_type in ("flags", "flags2"):
            self._build_flags_details(details_frame, cond_type, block_data.get(cond_type, {}))
        elif cond_type == "gui_focus":
            self._build_gui_focus_details(details_frame, block_data.get("gui_focus", {}))
        elif cond_type == "field":
            self._build_field_details(details_frame, block_data.get("field", {}))
            
        # Store a reference to easily reconstruct
        block_frame.details_widgets = details_frame.winfo_children()
        
    def _build_flags_details(self, parent, flags_type: str, flags_data: Dict):
        """Build flags/flags2 condition details."""
        flags_dict = self.flags_dict if flags_type == "flags" else self.flags2_dict
        
        # Operator selector with descriptions
        op_frame = ttk.Frame(parent)
        op_frame.pack(fill=tk.X, pady=2)
        ttk.Label(op_frame, text="Match type:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Determine current operator
        current_op = "all_of"
        if "all_of" in flags_data:
            current_op = "all_of"
        elif "any_of" in flags_data:
            current_op = "any_of"
        elif "none_of" in flags_data:
            current_op = "none_of"
        elif "equals" in flags_data:
            current_op = "equals"
            
        op_var = tk.StringVar(value=current_op)
        parent.operator_var = op_var
        
        # Create operator descriptions
        op_descriptions = {
            "all_of": "All selected flags must be set",
            "any_of": "At least one selected flag must be set",
            "none_of": "None of the selected flags can be set",
            "equals": "Flags must exactly match selected"
        }
        
        op_combo = ttk.Combobox(op_frame, textvariable=op_var, width=15, state="readonly")
        op_combo["values"] = ["all_of", "any_of", "none_of", "equals"]
        op_combo.pack(side=tk.LEFT)
        
        # Add help text for operator
        op_help = ttk.Label(op_frame, text="", foreground="gray")
        op_help.pack(side=tk.LEFT, padx=(10, 0))
        
        def update_op_help(event=None):
            selected = op_var.get()
            op_help.configure(text=f"({op_descriptions.get(selected, '')})")
        
        op_combo.bind("<<ComboboxSelected>>", update_op_help)
        update_op_help()  # Set initial help text
        
        # Flags listbox for selection
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(list_frame, text="Select flags:").pack(anchor=tk.W)
        
        # Scrollable listbox
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, 
                            yscrollcommand=scrollbar.set, height=8)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Populate with flags
        flag_names = sorted(flags_dict.keys())
        for flag in flag_names:
            listbox.insert(tk.END, flag)
            
        # Select currently selected flags
        if current_op in ("all_of", "any_of", "none_of"):
            selected_flags = flags_data.get(current_op, [])
            for i, flag in enumerate(flag_names):
                if flag in selected_flags:
                    listbox.selection_set(i)
        elif current_op == "equals":
            equals_dict = flags_data.get("equals", {})
            for i, flag in enumerate(flag_names):
                if flag in equals_dict:
                    listbox.selection_set(i)
                    
        parent.flags_listbox = listbox
        
    def _build_gui_focus_details(self, parent, gui_focus_data: Dict):
        """Build GUI focus condition details."""
        # Operator selector
        op_frame = ttk.Frame(parent)
        op_frame.pack(fill=tk.X, pady=2)
        ttk.Label(op_frame, text="Operator:").pack(side=tk.LEFT, padx=(0, 5))
        
        current_op = "equals"
        if "equals" in gui_focus_data:
            current_op = "equals"
        elif "in" in gui_focus_data:
            current_op = "in"
        elif "changed_to" in gui_focus_data:
            current_op = "changed_to"
            
        op_var = tk.StringVar(value=current_op)
        parent.operator_var = op_var
        
        op_combo = ttk.Combobox(op_frame, textvariable=op_var, width=15, state="readonly")
        op_combo["values"] = ["equals", "in", "changed_to"]
        op_combo.pack(side=tk.LEFT)
        
        # GUI focus selector
        focus_frame = ttk.Frame(parent)
        focus_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(focus_frame, text="Select GUI focus:").pack(anchor=tk.W)
        
        listbox_frame = ttk.Frame(focus_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, 
                            yscrollcommand=scrollbar.set, height=8)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Populate with GUI focus options
        focus_names = sorted(self.gui_focus_dict.keys())
        for focus in focus_names:
            listbox.insert(tk.END, focus)
            
        # Select current value
        if current_op == "equals":
            current_val = gui_focus_data.get("equals", "")
            if isinstance(current_val, str) and current_val in focus_names:
                idx = focus_names.index(current_val)
                listbox.selection_set(idx)
        elif current_op in ("in", "changed_to"):
            current_vals = gui_focus_data.get(current_op, [])
            if not isinstance(current_vals, list):
                current_vals = [current_vals]
            for val in current_vals:
                if isinstance(val, str) and val in focus_names:
                    idx = focus_names.index(val)
                    listbox.selection_set(idx)
                    
        parent.focus_listbox = listbox
        
    def _build_field_details(self, parent, field_data: Dict):
        """Build field condition details."""
        # Field name
        name_frame = ttk.Frame(parent)
        name_frame.pack(fill=tk.X, pady=2)
        ttk.Label(name_frame, text="Field Path:").pack(side=tk.LEFT, padx=(0, 5))
        
        name_var = tk.StringVar(value=field_data.get("name", ""))
        parent.field_name_var = name_var
        ttk.Entry(name_frame, textvariable=name_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Operator selector
        op_frame = ttk.Frame(parent)
        op_frame.pack(fill=tk.X, pady=2)
        ttk.Label(op_frame, text="Operator:").pack(side=tk.LEFT, padx=(0, 5))
        
        current_op = "equals"
        for op in ["exists", "equals", "in", "not_in", "contains", "gt", "gte", "lt", "lte"]:
            if op in field_data:
                current_op = op
                break
                
        op_var = tk.StringVar(value=current_op)
        parent.operator_var = op_var
        
        op_combo = ttk.Combobox(op_frame, textvariable=op_var, width=15, state="readonly")
        op_combo["values"] = ["exists", "equals", "in", "not_in", "contains", "gt", "gte", "lt", "lte", "changed", "changed_to"]
        op_combo.pack(side=tk.LEFT)
        
        # Value entry
        val_frame = ttk.Frame(parent)
        val_frame.pack(fill=tk.X, pady=2)
        ttk.Label(val_frame, text="Value:").pack(side=tk.LEFT, padx=(0, 5))
        
        current_val = field_data.get(current_op, "")
        val_var = tk.StringVar(value=str(current_val) if current_val is not None else "")
        parent.field_value_var = val_var
        ttk.Entry(val_frame, textvariable=val_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
    def _remove_condition_block(self, block_frame):
        """Remove a condition block."""
        block_frame.destroy()
        
    def _update_json_preview(self):
        """Update JSON preview with current rule state."""
        try:
            rule = self._build_rule_from_ui()
            json_str = json.dumps(rule, indent=2)
            self.json_text.delete("1.0", tk.END)
            self.json_text.insert("1.0", json_str)
        except Exception as e:
            self.json_text.delete("1.0", tk.END)
            self.json_text.insert("1.0", f"Error building rule: {e}")
            
    def _build_rule_from_ui(self) -> Dict[str, Any]:
        """Build rule dictionary from current UI state."""
        rule = {
            "id": self.id_var.get().strip() or "unnamed",
            "enabled": self.enabled_var.get(),
        }
        
        # Build when conditions
        when = {}
        
        # Source filter
        source = self.source_var.get().strip()
        if source and source != "any":
            when["source"] = source
            
        # Event filter
        event = self.event_var.get().strip()
        if event:
            # Extract event ID from "Title (EventID)" format
            if "(" in event and event.endswith(")"):
                event = event.split("(")[-1].rstrip(")")
            when["event"] = event
            
        # Condition blocks
        all_blocks = []
        for block_frame in self.all_blocks_frame.winfo_children():
            if isinstance(block_frame, ttk.LabelFrame):
                block = self._build_condition_block_from_ui(block_frame)
                if block:
                    all_blocks.append(block)
                    
        any_blocks = []
        for block_frame in self.any_blocks_frame.winfo_children():
            if isinstance(block_frame, ttk.LabelFrame):
                block = self._build_condition_block_from_ui(block_frame)
                if block:
                    any_blocks.append(block)
                    
        if all_blocks:
            when["all"] = all_blocks
        if any_blocks:
            when["any"] = any_blocks
            
        rule["when"] = when
        
        # Build then actions
        then_actions = self._build_actions_from_ui("then")
        if then_actions:
            rule["then"] = then_actions
            
        # Build else actions
        else_actions = self._build_actions_from_ui("else")
        if else_actions:
            rule["else"] = else_actions
            
        return rule
        
    def _build_condition_block_from_ui(self, block_frame) -> Optional[Dict[str, Any]]:
        """Build a condition block dictionary from UI."""
        try:
            cond_type = block_frame.condition_type_var.get()
            details_frame = block_frame.details_frame
            
            if cond_type in ("flags", "flags2"):
                operator = details_frame.operator_var.get()
                listbox = details_frame.flags_listbox
                
                selected_indices = listbox.curselection()
                selected_flags = [listbox.get(i) for i in selected_indices]
                
                if not selected_flags:
                    return None
                    
                if operator in ("all_of", "any_of", "none_of"):
                    return {cond_type: {operator: selected_flags}}
                elif operator == "equals":
                    # For equals, create dict with flag: true for each selected
                    equals_dict = {flag: True for flag in selected_flags}
                    return {cond_type: {operator: equals_dict}}
                    
            elif cond_type == "gui_focus":
                operator = details_frame.operator_var.get()
                listbox = details_frame.focus_listbox
                
                selected_indices = listbox.curselection()
                selected_focus = [listbox.get(i) for i in selected_indices]
                
                if not selected_focus:
                    return None
                    
                if operator == "equals":
                    return {cond_type: {operator: selected_focus[0]}}
                elif operator in ("in", "changed_to"):
                    if operator == "changed_to":
                        return {cond_type: {operator: selected_focus[0]}}
                    else:
                        return {cond_type: {operator: selected_focus}}
                        
            elif cond_type == "field":
                field_name = details_frame.field_name_var.get().strip()
                if not field_name:
                    return None
                    
                operator = details_frame.operator_var.get()
                value_str = details_frame.field_value_var.get().strip()
                
                # Try to parse value as JSON
                try:
                    value = json.loads(value_str)
                except (json.JSONDecodeError, ValueError, TypeError):
                    value = value_str
                    
                field_block = {"name": field_name}
                if operator and value_str:
                    field_block[operator] = value
                    
                return {cond_type: field_block}
                
        except Exception as e:
            logger.warning(f"Error building condition block: {e}")
            return None
            
        return None
        
    def _build_actions_from_ui(self, action_type: str) -> Dict[str, Any]:
        """Build actions dictionary from UI."""
        actions = {}
        
        # Log statement
        log_var = self.then_log_var if action_type == "then" else self.else_log_var
        log_msg = log_var.get().strip()
        if log_msg:
            actions["log"] = log_msg
            
        # Shift flags
        shift_vars = self.then_shift_vars if action_type == "then" else self.else_shift_vars
        set_flags = []
        clear_flags = []
        
        for flag, state_var in shift_vars.items():
            state = state_var.get()
            if state == "set":
                set_flags.append(flag)
            elif state == "clear":
                clear_flags.append(flag)
                
        if set_flags:
            actions["vkb_set_shift"] = set_flags
        if clear_flags:
            actions["vkb_clear_shift"] = clear_flags
            
        return actions
        
    def _save(self):
        """Save and close dialog."""
        try:
            rule = self._build_rule_from_ui()
            
            # Validate the rule
            is_valid, error_msg = validate_rule(rule)
            if not is_valid:
                messagebox.showerror("Validation Error", f"Invalid rule: {error_msg}")
                return
            
            self.result = rule
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save rule: {e}")
            
    def _cancel(self):
        """Cancel and close dialog."""
        self.result = None
        self.dialog.destroy()
        
    def show(self) -> Optional[Dict[str, Any]]:
        """Show dialog and return result."""
        self.dialog.wait_window()
        return self.result


def load_events_config(plugin_dir: Path) -> Dict[str, Any]:
    """Load events configuration from events_config.json."""
    config_path = plugin_dir / "events_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load events config from {config_path}: {e}")
        return {
            "sources": [],
            "events": [],
            "condition_types": [],
            "shift_flags": DEFAULT_SHIFT_FLAGS
        }
