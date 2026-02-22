#!/usr/bin/env python3
"""
Signal Catalog Editor - Interactive UI for editing signals_catalog.json

Features:
- Tree view of all categories, subcategories, and signals
- Move signals between categories/subcategories
- Move entire categories (with children) to become subcategories
- Promote subcategories to top-level
- Rename labels and signal identifiers
- Drag and drop support
- Visual hierarchy management
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import copy


class SignalCatalogEditor:
    """Interactive editor for signals_catalog.json"""
    
    def __init__(self, root: tk.Tk, catalog_path: Path):
        self.root = root
        self.catalog_path = catalog_path
        self.catalog_data = None
        self.modified = False
        self.drag_data = None
        self.drop_target = None
        self.drag_threshold = 5  # Minimum pixels to move before considering it a drag
        self.expanded_items = set()
        self.undo_stack = []  # Stack of previous catalog states
        self.undo_limit = 50  # Maximum undo history
        
        self.root.title("Signal Catalog Editor")
        self.root.geometry("1400x900")
        
        self.setup_ui()
        self.load_catalog()
        self.populate_tree()
        
    def setup_ui(self):
        """Create the UI layout"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", command=self.save_catalog, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_catalog_as)
        file_menu.add_command(label="Reload", command=self.reload_catalog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-s>', lambda e: self.save_catalog())
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Escape>', self.cancel_drag)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Left panel - Tree view
        tree_frame = ttk.LabelFrame(main_frame, text="Signal Hierarchy", padding="5")
        tree_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Scrollbars for tree
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Tree view with columns (multiselect enabled)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "signal_key", "category", "subcategory", "tier"),
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            selectmode="extended"  # Allow multiple selection
        )
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # Configure columns
        self.tree.heading("#0", text="Label / Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("signal_key", text="Signal Key")
        self.tree.heading("category", text="Category")
        self.tree.heading("subcategory", text="Subcategory")
        self.tree.heading("tier", text="Tier")
        
        self.tree.column("#0", width=300, minwidth=200)
        self.tree.column("type", width=80, minwidth=60)
        self.tree.column("signal_key", width=200, minwidth=150)
        self.tree.column("category", width=120, minwidth=100)
        self.tree.column("subcategory", width=120, minwidth=100)
        self.tree.column("tier", width=80, minwidth=60)
        
        # Grid tree components
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_scroll_x.grid(row=1, column=0, sticky=(tk.E, tk.W))
        
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Bind tree events
        self.tree.bind('<Button-1>', self.on_tree_click)
        self.tree.bind('<B1-Motion>', self.on_tree_drag)
        self.tree.bind('<ButtonRelease-1>', self.on_tree_drop)
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)
        self.tree.bind('<Button-3>', self.on_tree_right_click)

        # Bind tree open/close events to clear drag state
        self.tree.bind('<<TreeviewOpen>>', self.on_tree_toggle)
        self.tree.bind('<<TreeviewClose>>', self.on_tree_toggle)
        
        # Right panel - Actions and details
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.rowconfigure(1, weight=1)
        
        # Action buttons - 2 column layout
        action_frame = ttk.LabelFrame(right_frame, text="Actions", padding="3")
        action_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 5))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)

        row = 0
        
        # === Undo & Save ===
        ttk.Button(action_frame, text="⟲ Undo (Ctrl+Z)", command=self.undo, width=16).grid(row=row, column=0, pady=1, padx=2, sticky=tk.W+tk.E)
        ttk.Button(action_frame, text="💾 Save (Ctrl+S)", command=self.save_catalog, width=16).grid(row=row, column=1, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        
        ttk.Separator(action_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky=(tk.E, tk.W), pady=3)
        row += 1
        
        # === Editing ===
        ttk.Button(action_frame, text="Rename Label", command=self.rename_label, width=16).grid(row=row, column=0, pady=1, padx=2, sticky=tk.W+tk.E)
        ttk.Button(action_frame, text="Change Tier", command=self.change_tier, width=16).grid(row=row, column=1, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        ttk.Button(action_frame, text="Rename Signal Key", command=self.rename_signal_key, width=16).grid(row=row, column=0, pady=1, padx=2, sticky=tk.W+tk.E)
        ttk.Button(action_frame, text="🗑️ Delete Signal", command=self.delete_signal, width=16).grid(row=row, column=1, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        
        ttk.Separator(action_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky=(tk.E, tk.W), pady=3)
        row += 1
        
        # === Organization ===
        ttk.Button(action_frame, text="Move to Category", command=self.move_to_category, width=16).grid(row=row, column=0, pady=1, padx=2, sticky=tk.W+tk.E)
        ttk.Button(action_frame, text="Promote to Top", command=self.promote_to_top_level, width=16).grid(row=row, column=1, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        ttk.Button(action_frame, text="Move to SubCategory", command=self.move_to_subcategory, width=16).grid(row=row, column=0, columnspan=2, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        
        ttk.Separator(action_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky=(tk.E, tk.W), pady=3)
        row += 1
        
        # === Enum Editor ===
        ttk.Button(action_frame, text="📝 Edit Enum Values", command=self.edit_enum_values, width=16).grid(row=row, column=0, pady=1, padx=2, sticky=tk.W+tk.E)
        ttk.Button(action_frame, text="Edit Derive", command=self.edit_derive, width=16).grid(row=row, column=1, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        ttk.Button(action_frame, text="Merge Enums", command=self.merge_enums, width=16).grid(row=row, column=0, columnspan=2, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        
        ttk.Separator(action_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky=(tk.E, tk.W), pady=3)
        row += 1
        
        # === Signal Creation ===
        ttk.Button(action_frame, text="➕ Create New Signal", command=self.create_new_signal, width=16).grid(row=row, column=0, columnspan=2, pady=1, padx=2, sticky=tk.W+tk.E)
        row += 1
        
        ttk.Separator(action_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky=(tk.E, tk.W), pady=3)
        row += 1
        
        # === View ===
        ttk.Button(action_frame, text="Expand All", command=self.expand_all, width=16).grid(row=row, column=0, pady=1, padx=2, sticky=tk.W+tk.E)
        ttk.Button(action_frame, text="Collapse All", command=self.collapse_all, width=16).grid(row=row, column=1, pady=1, padx=2, sticky=tk.W+tk.E)
        
        # Details text area
        details_frame = ttk.LabelFrame(right_frame, text="Details", padding="5")
        details_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        
        self.details_text = tk.Text(details_frame, wrap=tk.WORD, width=40, height=20)
        details_scroll = ttk.Scrollbar(details_frame, orient="vertical", command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scroll.set)
        
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        self.modified_label = ttk.Label(status_frame, text="", foreground="red")
        self.modified_label.pack(side=tk.RIGHT)
        
        # Bind tree selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Rename Label", command=self.rename_label)
        self.context_menu.add_command(label="Rename Signal Key", command=self.rename_signal_key)
        self.context_menu.add_command(label="Delete Signal", command=self.delete_signal)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Move to Category", command=self.move_to_category)
        self.context_menu.add_command(label="Move to Subcategory", command=self.move_to_subcategory)
        self.context_menu.add_command(label="Promote to Top Level", command=self.promote_to_top_level)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Change Tier", command=self.change_tier)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Edit Enum Values", command=self.edit_enum_values)
        self.context_menu.add_command(label="Merge Enums", command=self.merge_enums)
        
        # Set closing protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def load_catalog(self):
        """Load the signals catalog from file"""
        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                self.catalog_data = json.load(f)
            self.set_status(f"Loaded: {self.catalog_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load catalog: {e}")
            self.root.destroy()
            
    def save_catalog(self):
        """Save the catalog back to file"""
        if not self.modified:
            messagebox.showinfo("Info", "No changes to save")
            return
            
        try:
            # Create backup
            backup_path = self.catalog_path.with_suffix('.json.backup')
            if self.catalog_path.exists():
                import shutil
                shutil.copy2(self.catalog_path, backup_path)
            
            # Save with pretty formatting
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog_data, f, indent=2, ensure_ascii=False)
            
            self.modified = False
            self.update_modified_indicator()
            self.set_status(f"Saved: {self.catalog_path}")
            messagebox.showinfo("Success", f"Catalog saved successfully!\nBackup: {backup_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save catalog: {e}")

    def save_catalog_silent(self):
        """Save the catalog back to file without popup confirmation"""
        if not self.modified:
            self.set_status("No changes to save")
            return

        try:
            # Create backup
            backup_path = self.catalog_path.with_suffix('.json.backup')
            if self.catalog_path.exists():
                import shutil
                shutil.copy2(self.catalog_path, backup_path)

            # Save with pretty formatting
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog_data, f, indent=2, ensure_ascii=False)

            self.modified = False
            self.update_modified_indicator()
            self.set_status(f"✓ Saved: {self.catalog_path.name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save catalog: {e}")

    def save_catalog_as(self):
        """Save catalog to a new file"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="signals_catalog.json"
        )
        if filepath:
            old_path = self.catalog_path
            self.catalog_path = Path(filepath)
            self.save_catalog()
            self.catalog_path = old_path  # Keep original for next save
            
    def reload_catalog(self):
        """Reload catalog from disk"""
        if self.modified:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before reloading?"
            )
            if result is None:  # Cancel
                return
            elif result:  # Yes
                self.save_catalog()
        
        self.load_catalog()
        self.populate_tree()
        self.set_status("Catalog reloaded")
        
    def populate_tree(self, restore_state=True):
        """Populate the tree view with catalog data"""
        # Save expanded state and selection before clearing
        if restore_state:
            self._save_tree_state()
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.catalog_data or 'signals' not in self.catalog_data:
            return
        
        # Build hierarchy: category -> subcategory -> signals
        hierarchy = {}
        signals = self.catalog_data['signals']
        
        # First pass: organize signals by category and subcategory
        for signal_key, signal_data in signals.items():
            if signal_key.startswith('_comment'):
                continue
                
            # Handle nested signals (like commander_ranks.combat)
            if isinstance(signal_data, dict) and 'ui' not in signal_data:
                # This is a parent grouping like commander_ranks
                for sub_key, sub_signal in signal_data.items():
                    if sub_key.startswith('_comment'):
                        continue
                    if isinstance(sub_signal, dict) and 'ui' in sub_signal:
                        full_key = f"{signal_key}.{sub_key}"
                        self._add_signal_to_hierarchy(hierarchy, full_key, sub_signal)
            elif isinstance(signal_data, dict) and 'ui' in signal_data:
                self._add_signal_to_hierarchy(hierarchy, signal_key, signal_data)
        
        # Second pass: build tree structure
        for category in sorted(hierarchy.keys()):
            cat_node = self.tree.insert(
                '',
                'end',
                text=category,
                values=('category', '', category, '', ''),
                tags=('category',)
            )
            
            category_data = hierarchy[category]
            
            # Add signals directly in category (no subcategory)
            if None in category_data:
                for signal_key, signal_data in sorted(category_data[None].items()):
                    self._insert_signal_node(cat_node, signal_key, signal_data)
            
            # Add subcategories
            for subcategory in sorted([k for k in category_data.keys() if k is not None]):
                subcat_node = self.tree.insert(
                    cat_node,
                    'end',
                    text=subcategory,
                    values=('subcategory', '', category, subcategory, ''),
                    tags=('subcategory',)
                )
                
                for signal_key, signal_data in sorted(category_data[subcategory].items()):
                    self._insert_signal_node(subcat_node, signal_key, signal_data)
        
        # Configure tags for visual distinction
        self.tree.tag_configure('category', foreground='#0066CC', font=('TkDefaultFont', 10, 'bold'))
        self.tree.tag_configure('subcategory', foreground='#006600', font=('TkDefaultFont', 9, 'bold'))
        self.tree.tag_configure('signal', foreground='#000000')
        self.tree.tag_configure('drop_target', background='#FFFF99')
        
        # Restore expanded state
        if restore_state:
            self._restore_tree_state()
        
    def _add_signal_to_hierarchy(self, hierarchy: dict, signal_key: str, signal_data: dict):
        """Add a signal to the hierarchy dictionary"""
        if 'ui' not in signal_data:
            return
            
        ui = signal_data['ui']
        category = ui.get('category', 'Uncategorized')
        subcategory = ui.get('subcategory')
        
        if category not in hierarchy:
            hierarchy[category] = {}
        if subcategory not in hierarchy[category]:
            hierarchy[category][subcategory] = {}
        
        hierarchy[category][subcategory][signal_key] = signal_data
        
    def _insert_signal_node(self, parent, signal_key: str, signal_data: dict):
        """Insert a signal node into the tree"""
        ui = signal_data.get('ui', {})
        label = ui.get('label', signal_key)
        category = ui.get('category', '')
        subcategory = ui.get('subcategory', '')
        tier = ui.get('tier', '')
        signal_type = signal_data.get('type', '')
        
        self.tree.insert(
            parent,
            'end',
            text=label,
            values=('signal', signal_key, category, subcategory, tier),
            tags=('signal',)
        )
        
    def _save_tree_state(self):
        """Save which items are expanded"""
        self.expanded_items.clear()
        
        def collect_expanded(item):
            if self.tree.item(item, 'open'):
                # Store a unique identifier for this item
                values = self.tree.item(item, 'values')
                text = self.tree.item(item, 'text')
                if values:
                    item_type = values[0]
                    if item_type == 'category':
                        self.expanded_items.add(('category', text))
                    elif item_type == 'subcategory':
                        category = values[2]
                        subcategory = values[3]
                        self.expanded_items.add(('subcategory', category, subcategory))
            
            for child in self.tree.get_children(item):
                collect_expanded(child)
        
        for item in self.tree.get_children():
            collect_expanded(item)
    
    def _restore_tree_state(self):
        """Restore which items should be expanded"""
        def restore_expanded(item):
            values = self.tree.item(item, 'values')
            text = self.tree.item(item, 'text')
            
            if values:
                item_type = values[0]
                should_expand = False
                
                if item_type == 'category':
                    should_expand = ('category', text) in self.expanded_items
                elif item_type == 'subcategory':
                    category = values[2]
                    subcategory = values[3]
                    should_expand = ('subcategory', category, subcategory) in self.expanded_items
                
                if should_expand:
                    self.tree.item(item, open=True)
            
            for child in self.tree.get_children(item):
                restore_expanded(child)
        
        for item in self.tree.get_children():
            restore_expanded(item)
        
    def on_tree_select(self, event):
        """Handle tree selection - update details pane"""
        selection = self.tree.selection()
        if not selection:
            self.details_text.delete('1.0', tk.END)
            return

        # If multiple selections, show summary
        if len(selection) > 1:
            self.details_text.delete('1.0', tk.END)
            signals_count = 0
            categories_count = 0
            subcategories_count = 0

            for item in selection:
                values = self.tree.item(item, 'values')
                if values:
                    item_type = values[0]
                    if item_type == 'signal':
                        signals_count += 1
                    elif item_type == 'category':
                        categories_count += 1
                    elif item_type == 'subcategory':
                        subcategories_count += 1

            details = f"MULTIPLE SELECTION ({len(selection)} items)\n\n"
            if signals_count:
                details += f"Signals: {signals_count}\n"
            if categories_count:
                details += f"Categories: {categories_count}\n"
            if subcategories_count:
                details += f"Subcategories: {subcategories_count}\n"
            details += "\nBulk operations available:\n"
            details += "- Move to Category\n"
            details += "- Move to Subcategory\n"
            details += "- Promote to Top Level\n"
            details += "- Change Tier\n"
            self.details_text.insert('1.0', details)
            return

        # Single selection - show full details
        item = selection[0]
        values = self.tree.item(item, 'values')

        if not values:
            return

        item_type = values[0]

        self.details_text.delete('1.0', tk.END)

        if item_type == 'signal':
            signal_key = values[1]
            signal_data = self._get_signal_data(signal_key)
            if signal_data:
                details = f"Signal: {signal_key}\n"
                details += f"Label: {signal_data.get('ui', {}).get('label', 'N/A')}\n"
                details += f"Type: {signal_data.get('type', 'N/A')}\n"
                details += f"Category: {signal_data.get('ui', {}).get('category', 'N/A')}\n"
                details += f"Subcategory: {signal_data.get('ui', {}).get('subcategory', 'N/A')}\n"
                details += f"Tier: {signal_data.get('ui', {}).get('tier', 'N/A')}\n\n"
                details += "Full Data:\n"
                details += json.dumps(signal_data, indent=2)
                self.details_text.insert('1.0', details)
        elif item_type == 'category':
            category = values[2]
            # Count signals in category
            count = self._count_items_in_category(item)
            details = f"Category: {category}\n"
            details += f"Total items: {count}\n"
            self.details_text.insert('1.0', details)
        elif item_type == 'subcategory':
            category = values[2]
            subcategory = values[3]
            count = self._count_items_in_category(item)
            details = f"Subcategory: {subcategory}\n"
            details += f"Parent Category: {category}\n"
            details += f"Total items: {count}\n"
            self.details_text.insert('1.0', details)
            
    def _count_items_in_category(self, parent_item):
        """Count all items (recursively) under a category/subcategory"""
        count = 0
        for child in self.tree.get_children(parent_item):
            count += 1
            count += self._count_items_in_category(child)
        return count
        
    def _get_signal_data(self, signal_key: str) -> Optional[dict]:
        """Get signal data from catalog by key (handles nested keys)"""
        if '.' in signal_key:
            parts = signal_key.split('.')
            data = self.catalog_data['signals']
            for part in parts:
                if part in data:
                    data = data[part]
                else:
                    return None
            return data
        else:
            return self.catalog_data['signals'].get(signal_key)
            
    def _set_signal_data(self, signal_key: str, signal_data: dict):
        """Set signal data in catalog by key (handles nested keys)"""
        if '.' in signal_key:
            parts = signal_key.split('.')
            data = self.catalog_data['signals']
            for part in parts[:-1]:
                if part not in data:
                    data[part] = {}
                data = data[part]
            data[parts[-1]] = signal_data
        else:
            self.catalog_data['signals'][signal_key] = signal_data
            
    def _delete_signal_data(self, signal_key: str):
        """Delete signal from catalog by key"""
        if '.' in signal_key:
            parts = signal_key.split('.')
            data = self.catalog_data['signals']
            for part in parts[:-1]:
                if part in data:
                    data = data[part]
                else:
                    return
            if parts[-1] in data:
                del data[parts[-1]]
        else:
            if signal_key in self.catalog_data['signals']:
                del self.catalog_data['signals'][signal_key]
                
    def on_tree_click(self, event):
        """Handle tree click - prepare for potential drag

        Note: This sets up drag_data but the actual drag only starts if the mouse
        moves beyond the threshold distance. This prevents collapse/expand clicks
        from being interpreted as drag operations.
        """
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_data = {
                'item': item,
                'start_x': event.x,
                'start_y': event.y,
                'text': self.tree.item(item, 'text')
            }
            self.tree.config(cursor='hand2')
            
    def on_tree_drag(self, event):
        """Handle tree drag - show visual feedback"""
        if self.drag_data:
            # Check if mouse has moved enough to be considered a drag
            dx = abs(event.x - self.drag_data['start_x'])
            dy = abs(event.y - self.drag_data['start_y'])

            if dx < self.drag_threshold and dy < self.drag_threshold:
                # Not enough movement yet, don't start drag
                return

            # Get current item under cursor
            current_item = self.tree.identify_row(event.y)
            
            # Clear previous drop target highlight
            if self.drop_target:
                # Remove drop_target tag
                tags = list(self.tree.item(self.drop_target, 'tags'))
                if 'drop_target' in tags:
                    tags.remove('drop_target')
                    self.tree.item(self.drop_target, tags=tags)
            
            # Highlight new drop target if valid
            if current_item and current_item != self.drag_data['item']:
                source_values = self.tree.item(self.drag_data['item'], 'values')
                target_values = self.tree.item(current_item, 'values')
                
                if source_values and target_values:
                    source_type = source_values[0]
                    target_type = target_values[0]
                    
                    # Check if drop is valid
                    is_valid = False
                    if source_type == 'signal' and target_type in ('category', 'subcategory'):
                        is_valid = True
                    elif source_type in ('category', 'subcategory') and target_type == 'category':
                        is_valid = True
                    
                    if is_valid:
                        tags = list(self.tree.item(current_item, 'tags'))
                        if 'drop_target' not in tags:
                            tags.append('drop_target')
                            self.tree.item(current_item, tags=tags)
                        self.drop_target = current_item
                        self.tree.config(cursor='plus')
                        return
            
            self.drop_target = None
            self.tree.config(cursor='hand2')
            
    def on_tree_drop(self, event):
        """Handle tree drop - move item"""
        # Clear visual feedback
        self.tree.config(cursor='')
        if self.drop_target:
            tags = list(self.tree.item(self.drop_target, 'tags'))
            if 'drop_target' in tags:
                tags.remove('drop_target')
                self.tree.item(self.drop_target, tags=tags)
            self.drop_target = None

        if not self.drag_data:
            return

        # Check if this was actually a drag (moved enough distance)
        dx = abs(event.x - self.drag_data['start_x'])
        dy = abs(event.y - self.drag_data['start_y'])

        # Clear drag state BEFORE returning (this is critical!)
        source_item = self.drag_data['item']
        self.drag_data = None

        # If didn't move enough, treat as a simple click, not a drag
        if dx < self.drag_threshold and dy < self.drag_threshold:
            return

        target_item = self.tree.identify_row(event.y)

        if not target_item or source_item == target_item:
            return

        # Get item types
        source_values = self.tree.item(source_item, 'values')
        target_values = self.tree.item(target_item, 'values')

        if not source_values or not target_values:
            return

        source_type = source_values[0]
        target_type = target_values[0]

        # Determine action based on types
        if source_type == 'signal' and target_type in ('category', 'subcategory'):
            self._move_signal_to_target(source_item, target_item, target_type, target_values)
        elif source_type in ('category', 'subcategory') and target_type == 'category':
            self._move_category_to_target(source_item, target_item, source_type)
        
    def on_tree_toggle(self, event):
        """Handle tree expand/collapse - clear drag state to prevent accidental moves"""
        # Clear any pending drag operation
        if self.drag_data:
            self.drag_data = None
            self.tree.config(cursor='')

        # Clear drop target highlight
        if self.drop_target:
            tags = list(self.tree.item(self.drop_target, 'tags'))
            if 'drop_target' in tags:
                tags.remove('drop_target')
                self.tree.item(self.drop_target, tags=tags)
            self.drop_target = None

    def cancel_drag(self, event=None):
        """Cancel any ongoing drag operation (ESC key)"""
        if self.drag_data or self.drop_target:
            # Clear drag state
            self.drag_data = None
            self.tree.config(cursor='')

            # Clear drop target highlight
            if self.drop_target:
                tags = list(self.tree.item(self.drop_target, 'tags'))
                if 'drop_target' in tags:
                    tags.remove('drop_target')
                    self.tree.item(self.drop_target, tags=tags)
                self.drop_target = None

            self.set_status("Drag cancelled")

    def _move_signal_to_target(self, source_item, target_item, target_type, target_values):
        """Move a signal to a category or subcategory"""
        source_values = self.tree.item(source_item, 'values')
        signal_key = source_values[1]
        signal_data = self._get_signal_data(signal_key)
        
        if not signal_data:
            return
        
        new_category = target_values[2]
        new_subcategory = target_values[3] if target_type == 'subcategory' else None
        
        # Save state for undo before making changes
        self.save_state_for_undo()
        
        # Update signal data
        signal_data['ui']['category'] = new_category
        if new_subcategory:
            signal_data['ui']['subcategory'] = new_subcategory
        elif 'subcategory' in signal_data['ui']:
            del signal_data['ui']['subcategory']
        
        self.mark_modified()
        self.populate_tree()
        self.set_status(f"Moved {signal_key} to {new_category}" + 
                       (f" > {new_subcategory}" if new_subcategory else ""))
        
    def _move_category_to_target(self, source_item, target_item, source_type):
        """Move a category/subcategory to become a subcategory of another"""
        source_values = self.tree.item(source_item, 'values')
        target_values = self.tree.item(target_item, 'values')
        
        source_category = source_values[2]
        source_subcategory = source_values[3] if source_type == 'subcategory' else None
        target_category = target_values[2]
        
        # Validate: Cannot move a top-level category to become a subcategory if it already has subcategories
        if source_type == 'category' and source_subcategory is None:
            # Check if this category has subcategories
            has_subcategories = False
            for sig_key, sig_data in self.catalog_data['signals'].items():
                if isinstance(sig_data, dict):
                    if 'ui' in sig_data:
                        if sig_data['ui'].get('category') == source_category and sig_data['ui'].get('subcategory'):
                            has_subcategories = True
                            break
                    else:
                        for sub_data in sig_data.values():
                            if isinstance(sub_data, dict) and 'ui' in sub_data:
                                if sub_data['ui'].get('category') == source_category and sub_data['ui'].get('subcategory'):
                                    has_subcategories = True
                                    break
                if has_subcategories:
                    break
            
            if has_subcategories:
                messagebox.showerror(
                    "Invalid Move",
                    f"Cannot move category '{source_category}' into '{target_category}'.\n\n"
                    f"The category contains subcategories, which would create too many nesting levels.\n"
                    f"Maximum nesting: Category > Subcategory > Signal\n\n"
                    f"Please move the signals individually or promote subcategories first."
                )
                return
        
        # Save state for undo before making changes
        self.save_state_for_undo()
        
        # Find all signals in source and update them
        count = 0
        for signal_key, signal_data in list(self.catalog_data['signals'].items()):
            if self._process_signal_for_category_move(
                signal_key, signal_data,
                source_category, source_subcategory, target_category
            ):
                count += 1
        
        if count > 0:
            self.mark_modified()
            self.populate_tree()
            self.set_status(f"Moved {count} signals to {target_category}")
            
    def _process_signal_for_category_move(self, signal_key, signal_data, 
                                          source_cat, source_subcat, target_cat):
        """Process a single signal for category move (handles nested)"""
        if isinstance(signal_data, dict):
            if 'ui' in signal_data:
                ui = signal_data['ui']
                if ui.get('category') == source_cat:
                    if source_subcat is None or ui.get('subcategory') == source_subcat:
                        ui['category'] = target_cat
                        ui['subcategory'] = source_cat if source_subcat is None else source_subcat
                        return True
            else:
                # Check nested signals
                for sub_key, sub_data in signal_data.items():
                    if isinstance(sub_data, dict) and 'ui' in sub_data:
                        if self._process_signal_for_category_move(
                            f"{signal_key}.{sub_key}", sub_data,
                            source_cat, source_subcat, target_cat
                        ):
                            return True
        return False
        
    def on_tree_double_click(self, event):
        """Handle double-click - edit label"""
        self.rename_label()
        
    def on_tree_right_click(self, event):
        """Handle right-click - show context menu"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
            
    def rename_label(self):
        """Rename the label of the selected item"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item first")
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        current_label = self.tree.item(item, 'text')
        
        new_label = simpledialog.askstring(
            "Rename Label",
            f"Enter new label:",
            initialvalue=current_label,
            parent=self.root
        )
        
        if new_label and new_label != current_label:
            item_type = values[0]
            
            if item_type == 'signal':
                signal_key = values[1]
                signal_data = self._get_signal_data(signal_key)
                if signal_data:
                    self.save_state_for_undo()
                    signal_data['ui']['label'] = new_label
                    self.mark_modified()
                    self.tree.item(item, text=new_label)
                    self.set_status(f"Renamed '{current_label}' to '{new_label}'")
            else:
                # For categories, we'd need to update the category name of all children
                # This is more complex, so show a message
                messagebox.showinfo(
                    "Info",
                    "Renaming categories requires changing the category field of all child signals.\n"
                    "Use 'Move to Category' to reorganize the structure instead."
                )
                
    def rename_signal_key(self):
        """Rename the signal key (identifier)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a signal first")
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        
        if values[0] != 'signal':
            messagebox.showwarning("Warning", "Only signals can have their keys renamed")
            return
        
        old_key = values[1]
        
        new_key = simpledialog.askstring(
            "Rename Signal Key",
            f"Enter new signal key for '{old_key}':",
            initialvalue=old_key,
            parent=self.root
        )
        
        if new_key and new_key != old_key:
            # Check if new key already exists
            if '.' not in new_key and new_key in self.catalog_data['signals']:
                messagebox.showerror("Error", f"Signal key '{new_key}' already exists")
                return
            
            # Get the signal data
            signal_data = self._get_signal_data(old_key)
            if signal_data:
                # Save state for undo
                self.save_state_for_undo()
                
                # Delete old key and add with new key
                self._delete_signal_data(old_key)
                self._set_signal_data(new_key, signal_data)
                
                self.mark_modified()
                self.populate_tree()
                self.set_status(f"Renamed signal key from '{old_key}' to '{new_key}'")

    def delete_signal(self):
        """Delete the selected signal(s)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select at least one signal to delete")
            return

        # Get all selected signals
        signals_to_delete = []
        for item in selection:
            values = self.tree.item(item, 'values')
            if values[0] == 'signal':
                signal_key = values[1]
                signals_to_delete.append((item, signal_key))

        if not signals_to_delete:
            messagebox.showwarning("Warning", "Please select signal(s) to delete")
            return

        # Confirm deletion
        if len(signals_to_delete) == 1:
            signal_key = signals_to_delete[0][1]
            message = f"Delete signal '{signal_key}'?\n\nThis action cannot be undone (except with Undo)."
        else:
            message = f"Delete {len(signals_to_delete)} signals?\n\nThis action cannot be undone (except with Undo)."

        result = messagebox.askyesno("Confirm Delete", message, icon='warning')

        if not result:
            return

        # Perform deletion
        self.save_state_for_undo()
        deleted_count = 0

        for item, signal_key in signals_to_delete:
            signal_data = self._get_signal_data(signal_key)
            if signal_data:
                self._delete_signal_data(signal_key)
                deleted_count += 1

        if deleted_count > 0:
            self.mark_modified()
            self.populate_tree()
            count_str = f"{deleted_count} signal{'s' if deleted_count > 1 else ''}"
            self.set_status(f"Deleted {count_str}")

    def move_to_category(self):
        """Move selected signal(s) to a different category"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select at least one signal")
            return

        # Get all signals to move
        signals_to_move = []
        for item in selection:
            values = self.tree.item(item, 'values')
            if values[0] == 'signal':
                signals_to_move.append((item, values[1]))

        if not signals_to_move:
            messagebox.showwarning("Warning", "Please select signal(s) to move")
            return

        # Get all categories
        categories = set()
        for signal_key, signal_data in self.catalog_data['signals'].items():
            if isinstance(signal_data, dict):
                if 'ui' in signal_data:
                    categories.add(signal_data['ui'].get('category', ''))
                else:
                    for sub_data in signal_data.values():
                        if isinstance(sub_data, dict) and 'ui' in sub_data:
                            categories.add(sub_data['ui'].get('category', ''))

        categories = sorted([c for c in categories if c])

        # Dialog to select category (allow new)
        dialog = CategorySelectDialog(self.root, "Select or Create Category", categories, allow_new=True)
        new_category = dialog.result

        if new_category:
            self.save_state_for_undo()
            moved_count = 0

            # Move all selected signals
            for item, signal_key in signals_to_move:
                signal_data = self._get_signal_data(signal_key)
                if signal_data:
                    signal_data['ui']['category'] = new_category
                    if 'subcategory' in signal_data['ui']:
                        del signal_data['ui']['subcategory']
                    moved_count += 1

            self.mark_modified()
            self.populate_tree()
            count_str = f"{moved_count} signal{'s' if moved_count > 1 else ''}"
            self.set_status(f"Moved {count_str} to category '{new_category}'")
                    
    def move_to_subcategory(self):
        """Move selected signal(s) to a subcategory"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select at least one signal")
            return

        # Get all selected signals
        signals_to_move = []
        for item in selection:
            values = self.tree.item(item, 'values')
            if values[0] == 'signal':
                signals_to_move.append((item, values[1]))

        if not signals_to_move:
            messagebox.showwarning("Warning", "Only signals can be moved to subcategories")
            return

        # Get category from first signal
        first_signal_key = signals_to_move[0][1]
        first_signal_data = self._get_signal_data(first_signal_key)
        if not first_signal_data:
            return

        current_category = first_signal_data['ui'].get('category', '')

        # Get all subcategories in this category
        subcategories = set()
        for sk, sd in self.catalog_data['signals'].items():
            if isinstance(sd, dict):
                if 'ui' in sd and sd['ui'].get('category') == current_category:
                    subcat = sd['ui'].get('subcategory')
                    if subcat:
                        subcategories.add(subcat)
                else:
                    for sub_data in sd.values():
                        if isinstance(sub_data, dict) and 'ui' in sub_data:
                            if sub_data['ui'].get('category') == current_category:
                                subcat = sub_data['ui'].get('subcategory')
                                if subcat:
                                    subcategories.add(subcat)

        subcategories = sorted(subcategories)

        # Use dialog (user can select from list or type new name)
        dialog = CategorySelectDialog(
            self.root,
            f"Select or Create Subcategory (in {current_category})",
            subcategories,
            allow_new=True
        )
        new_subcat = dialog.result

        if new_subcat:
            self.save_state_for_undo()
            moved_count = 0

            # Move all selected signals
            for item, signal_key in signals_to_move:
                signal_data = self._get_signal_data(signal_key)
                if signal_data:
                    signal_data['ui']['subcategory'] = new_subcat
                    moved_count += 1

            self.mark_modified()
            self.populate_tree()
            count_str = f"{moved_count} signal{'s' if moved_count > 1 else ''}"
            self.set_status(f"Moved {count_str} to subcategory '{new_subcat}'")
            
    def promote_to_top_level(self):
        """Remove subcategory from selected signal(s)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select at least one item")
            return

        self.save_state_for_undo()
        promoted_count = 0

        for item in selection:
            values = self.tree.item(item, 'values')
            item_type = values[0]

            if item_type == 'signal':
                signal_key = values[1]
                signal_data = self._get_signal_data(signal_key)
                if signal_data and 'subcategory' in signal_data['ui']:
                    del signal_data['ui']['subcategory']
                    promoted_count += 1

            elif item_type == 'subcategory':
                # Move all signals in this subcategory to top level of parent category
                category = values[2]
                subcategory = values[3]

                for signal_key, signal_data in list(self.catalog_data['signals'].items()):
                    promoted_count += self._promote_signals_in_subcategory(
                        signal_key, signal_data, category, subcategory
                    )

        if promoted_count > 0:
            self.mark_modified()
            self.populate_tree()
            count_str = f"{promoted_count} signal{'s' if promoted_count > 1 else ''}"
            self.set_status(f"Promoted {count_str} to top level of category")
        else:
            self.set_status("No signals to promote")
                
    def _promote_signals_in_subcategory(self, signal_key, signal_data, category, subcategory):
        """Promote all signals in a subcategory (handles nested)"""
        count = 0
        if isinstance(signal_data, dict):
            if 'ui' in signal_data:
                ui = signal_data['ui']
                if ui.get('category') == category and ui.get('subcategory') == subcategory:
                    del ui['subcategory']
                    count = 1
            else:
                for sub_key, sub_data in signal_data.items():
                    if isinstance(sub_data, dict) and 'ui' in sub_data:
                        ui = sub_data['ui']
                        if ui.get('category') == category and ui.get('subcategory') == subcategory:
                            del ui['subcategory']
                            count += 1
        return count
        
    def change_tier(self):
        """Change the tier of selected signal(s)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select at least one signal")
            return

        # Get all selected signals
        signals_to_change = []
        for item in selection:
            values = self.tree.item(item, 'values')
            if values[0] == 'signal':
                signals_to_change.append((item, values[1]))

        if not signals_to_change:
            messagebox.showwarning("Warning", "Only signals have tiers")
            return

        # Simple dialog for tier selection
        dialog = CategorySelectDialog(
            self.root,
            "Select Tier",
            ["core", "detail", "extended"],
            allow_new=False
        )
        new_tier = dialog.result

        if new_tier:
            self.save_state_for_undo()
            changed_count = 0

            # Change tier for all selected signals
            for item, signal_key in signals_to_change:
                signal_data = self._get_signal_data(signal_key)
                if signal_data:
                    current_tier = signal_data['ui'].get('tier', 'core')
                    if new_tier != current_tier:
                        signal_data['ui']['tier'] = new_tier
                        changed_count += 1

            if changed_count > 0:
                self.mark_modified()
                self.populate_tree()
                count_str = f"{changed_count} signal{'s' if changed_count > 1 else ''}"
                self.set_status(f"Changed tier of {count_str} to '{new_tier}'")
            else:
                self.set_status(f"All selected signals already at tier '{new_tier}'")

    def edit_enum_values(self):
        """Open enum editor dialog for the selected signal"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a signal first")
            return

        item = selection[0]
        values = self.tree.item(item, 'values')

        if values[0] != 'signal':
            messagebox.showwarning("Warning", "Please select a signal to edit its enum values")
            return

        signal_key = values[1]
        signal_data = self._get_signal_data(signal_key)

        if not signal_data:
            return

        # Check if it's an enum type
        if signal_data.get('type') != 'enum':
            messagebox.showwarning("Warning", f"Signal '{signal_key}' is not an enum type")
            return

        # Open enum editor dialog
        # Create refresh callback that updates both tree and details panel
        def refresh_after_edit():
            self.populate_tree()
            self.on_tree_select(None)  # Refresh details panel

        dialog = EnumEditorDialog(
            self.root,
            signal_key,
            signal_data,
            self.catalog_data['signals'],
            self.save_state_for_undo,
            self.mark_modified,
            refresh_after_edit,
            self.set_status
        )

        if dialog.modified:
            self.populate_tree()

    def create_new_signal(self):
        """Create a new signal in the catalog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Signal")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Signal key
        ttk.Label(dialog, text="Signal Key:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        signal_key_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=signal_key_var, width=30).grid(row=0, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # Label
        ttk.Label(dialog, text="Label:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        label_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=label_var, width=30).grid(row=1, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # Type
        ttk.Label(dialog, text="Type:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        type_var = tk.StringVar(value="enum")
        ttk.Combobox(dialog, textvariable=type_var, values=["enum", "path", "flag"], width=27).grid(row=2, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # Category
        ttk.Label(dialog, text="Category:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        category_var = tk.StringVar()
        categories = sorted(set(s.get('ui', {}).get('category', '') for s in self.catalog_data['signals'].values() if isinstance(s, dict) and 'ui' in s))
        ttk.Combobox(dialog, textvariable=category_var, values=categories, width=27).grid(row=3, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # Subcategory
        ttk.Label(dialog, text="Subcategory:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        subcategory_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=subcategory_var, width=30).grid(row=4, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # Tier
        ttk.Label(dialog, text="Tier:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        tier_var = tk.StringVar(value="core")
        ttk.Combobox(dialog, textvariable=tier_var, values=["core", "detail"], width=27).grid(row=5, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # Values (for enums)
        ttk.Label(dialog, text="Values (comma-separated):").grid(row=6, column=0, sticky=tk.W, padx=10, pady=5)
        values_text = tk.Text(dialog, height=5, width=32)
        values_text.grid(row=6, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
        
        dialog.columnconfigure(1, weight=1)
        
        def save_signal():
            signal_key = signal_key_var.get().strip()
            label = label_var.get().strip()
            signal_type = type_var.get()
            category = category_var.get().strip()
            tier = tier_var.get()
            
            if not signal_key or not label:
                messagebox.showwarning("Warning", "Signal key and label are required")
                return
            
            self.save_state_for_undo()
            
            # Create signal structure
            new_signal = {
                "type": signal_type,
                "title": label,
                "ui": {
                    "label": label,
                    "category": category,
                    "tier": tier
                }
            }
            
            # Add subcategory if provided
            if subcategory_var.get().strip():
                new_signal["ui"]["subcategory"] = subcategory_var.get().strip()
            
            # Add values for enum type
            if signal_type == "enum":
                values_str = values_text.get("1.0", tk.END).strip()
                new_signal["values"] = []
                if values_str:
                    for val in values_str.split(','):
                        val = val.strip()
                        if val:
                            new_signal["values"].append({"value": val, "label": val.replace('_', ' ').title()})
                new_signal["derive"] = {"op": "path", "path": ""}
            
            self.catalog_data['signals'][signal_key] = new_signal
            self.mark_modified()
            self.populate_tree()
            self.set_status(f"Created signal: {signal_key}")
            dialog.destroy()
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=7, column=0, columnspan=2, sticky=tk.W+tk.E, padx=10, pady=10)
        ttk.Button(button_frame, text="Create", command=save_signal).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def edit_derive(self):
        """Edit the derive block of a selected signal"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a signal first")
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        if values[0] != 'signal':
            messagebox.showwarning("Warning", "Please select a signal (not a category)")
            return
        
        signal_key = values[1]
        signal_data = self._get_signal_data(signal_key)
        
        if not signal_data or signal_data.get('type') != 'enum':
            messagebox.showwarning("Warning", "Only enum signals have derive blocks")
            return
        
        derive = signal_data.get('derive', {})
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Derive: {signal_key}")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # JSON editor for derive block
        ttk.Label(dialog, text="Derive Block (JSON):").pack(anchor=tk.W, padx=10, pady=5)
        
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        derive_text = tk.Text(text_frame, yscrollcommand=text_scroll.set, height=20)
        derive_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.config(command=derive_text.yview)
        
        # Load current derive as JSON
        import json as json_module
        derive_json = json_module.dumps(derive, indent=2)
        derive_text.insert("1.0", derive_json)
        
        def save_derive():
            try:
                new_derive = json_module.loads(derive_text.get("1.0", tk.END))
                self.save_state_for_undo()
                signal_data['derive'] = new_derive
                self.mark_modified()
                self.on_tree_select(None)  # Refresh details
                self.set_status(f"Updated derive for {signal_key}")
                dialog.destroy()
            except json_module.JSONDecodeError as e:
                messagebox.showerror("JSON Error", f"Invalid JSON: {e}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(anchor=tk.W, padx=10, pady=10)
        ttk.Button(button_frame, text="Save", command=save_derive).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def merge_enums(self):
        """Merge two enum signals together"""
        # Get all enum signals
        enum_signals = []
        for sig_key, sig_data in self.catalog_data['signals'].items():
            if isinstance(sig_data, dict) and sig_data.get('type') == 'enum':
                label = sig_data.get('ui', {}).get('label', sig_key)
                enum_signals.append((sig_key, label))

        if len(enum_signals) < 2:
            messagebox.showwarning("Warning", "Need at least 2 enum signals to merge")
            return

        # Sort by label for easier selection
        enum_signals.sort(key=lambda x: x[1])

        # Dialog to select source and target signals
        # Create refresh callback that updates both tree and details panel
        def refresh_after_merge():
            self.populate_tree()
            self.on_tree_select(None)  # Refresh details panel

        dialog = EnumMergeDialog(
            self.root,
            enum_signals,
            self.catalog_data['signals'],
            self.save_state_for_undo,
            self.mark_modified,
            refresh_after_merge,
            self.set_status
        )

        if dialog.result:
            self.populate_tree()

    def expand_all(self):
        """Expand all tree nodes"""
        def expand_recursive(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                expand_recursive(child)
        
        for item in self.tree.get_children():
            expand_recursive(item)
            
    def collapse_all(self):
        """Collapse all tree nodes"""
        def collapse_recursive(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                collapse_recursive(child)
        
        for item in self.tree.get_children():
            collapse_recursive(item)
            
    def save_state_for_undo(self):
        """Save the current catalog state to the undo stack"""
        # Deep copy the current state
        current_state = copy.deepcopy(self.catalog_data)
        self.undo_stack.append(current_state)
        
        # Limit undo stack size
        if len(self.undo_stack) > self.undo_limit:
            self.undo_stack.pop(0)
        
        self.set_status(f"Can undo (History: {len(self.undo_stack)})")
    
    def undo(self):
        """Undo the last change"""
        if not self.undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo")
            return
        
        # Pop the last state
        previous_state = self.undo_stack.pop()
        self.catalog_data = previous_state
        
        # Refresh the tree
        self.populate_tree()
        self.mark_modified()
        
        self.set_status(f"Undo successful (History: {len(self.undo_stack)})")
        
    def mark_modified(self):
        """Mark the catalog as modified"""
        self.modified = True
        self.update_modified_indicator()
        
    def update_modified_indicator(self):
        """Update the modified indicator in status bar"""
        if self.modified:
            self.modified_label.config(text="● Modified")
        else:
            self.modified_label.config(text="")
            
    def set_status(self, message: str):
        """Set status bar message"""
        self.status_label.config(text=message)
        self.root.after(5000, lambda: self.status_label.config(text="Ready"))
        
    def on_closing(self):
        """Handle window closing"""
        if self.modified:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?"
            )
            if result is None:  # Cancel
                return
            elif result:  # Yes
                self.save_catalog()
        
        self.root.destroy()


class CategorySelectDialog(simpledialog.Dialog):
    """Dialog for selecting from a list of categories or entering a new one"""

    def __init__(self, parent, title, options, allow_new=True):
        self.options = options
        self.allow_new = allow_new
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        label_text = "Select or type new:" if self.allow_new else "Select:"
        ttk.Label(master, text=label_text).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # Make combobox editable so users can type directly
        self.combo = ttk.Combobox(master, values=self.options, width=40)
        self.combo.grid(row=0, column=1, padx=5, pady=5)
        if self.options:
            self.combo.current(0)

        if self.allow_new:
            # Add helpful hint
            hint = ttk.Label(master, text="Tip: Type a new name or select from the dropdown",
                           font=('TkDefaultFont', 8), foreground='gray')
            hint.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))

        return self.combo

    def apply(self):
        self.result = self.combo.get().strip()


class EnumEditorDialog:
    """Dialog for editing enum values within a signal"""

    def __init__(self, parent, signal_key, signal_data, all_signals, save_state_callback, mark_modified_callback, refresh_callback, status_callback):
        self.parent = parent
        self.signal_key = signal_key
        self.signal_data = signal_data
        self.all_signals = all_signals
        self.save_state = save_state_callback
        self.mark_modified = mark_modified_callback
        self.refresh = refresh_callback
        self.set_status = status_callback
        self.modified = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Enum Values - {signal_key}")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.create_widgets()
        self.load_values()

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """Create dialog widgets"""
        # Info label
        info_frame = ttk.Frame(self.dialog, padding="10")
        info_frame.pack(fill=tk.X)

        ttk.Label(info_frame, text=f"Signal: {self.signal_key}", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Type: {self.signal_data.get('type', 'N/A')}", foreground='gray').pack(anchor=tk.W)

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Values list
        list_frame = ttk.LabelFrame(main_frame, text="Enum Values", padding="5")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)

        # Listbox for values
        self.values_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scroll.set,
            selectmode=tk.SINGLE,
            height=20
        )
        scroll.config(command=self.values_listbox.yview)

        self.values_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click to edit
        self.values_listbox.bind('<Double-Button-1>', lambda e: self.rename_value())

        # Button frame
        button_frame = ttk.Frame(main_frame, padding="5")
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(button_frame, text="Add Value", command=self.add_value, width=15).pack(pady=2)
        ttk.Button(button_frame, text="Rename Value", command=self.rename_value, width=15).pack(pady=2)
        ttk.Button(button_frame, text="Delete Value", command=self.delete_value, width=15).pack(pady=2)

        ttk.Separator(button_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Move Value To...", command=self.move_value_to_signal, width=15).pack(pady=2)

        ttk.Separator(button_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="▲ Move Up", command=self.move_value_up, width=15).pack(pady=2)
        ttk.Button(button_frame, text="▼ Move Down", command=self.move_value_down, width=15).pack(pady=2)

        # Close button
        close_frame = ttk.Frame(self.dialog, padding="10")
        close_frame.pack(fill=tk.X)

        ttk.Button(close_frame, text="Close", command=self.dialog.destroy, width=15).pack(side=tk.RIGHT)

    def load_values(self):
        """Load enum values into listbox"""
        self.values_listbox.delete(0, tk.END)

        values = self.signal_data.get('values', [])
        for value in values:
            value_id = value.get('value', '')
            label = value.get('label', '')
            recent_event = value.get('recent_event', '')

            display_text = f"{value_id}  →  {label}"
            if recent_event:
                display_text += f"  (event: {recent_event})"

            self.values_listbox.insert(tk.END, display_text)

    def add_value(self):
        """Add a new enum value"""
        # Dialog to get new value info
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Add Enum Value")
        dialog.geometry("400x150")
        dialog.transient(self.dialog)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Value ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        value_entry = ttk.Entry(frame, width=30)
        value_entry.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="Label:").grid(row=1, column=0, sticky=tk.W, pady=5)
        label_entry = ttk.Entry(frame, width=30)
        label_entry.grid(row=1, column=1, pady=5)

        def do_add():
            value_id = value_entry.get().strip()
            label = label_entry.get().strip()

            if not value_id or not label:
                messagebox.showwarning("Warning", "Both Value ID and Label are required", parent=dialog)
                return

            # Check for duplicates
            values = self.signal_data.get('values', [])
            if any(v.get('value') == value_id for v in values):
                messagebox.showwarning("Warning", f"Value '{value_id}' already exists", parent=dialog)
                return

            # Add the value
            self.save_state()
            new_value = {
                "value": value_id,
                "label": label
            }
            self.signal_data['values'].append(new_value)
            self.mark_modified()
            self.modified = True
            self.load_values()
            self.refresh()  # Refresh main window details panel
            self.set_status(f"Added enum value '{value_id}' to {self.signal_key}")
            dialog.destroy()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Add", command=do_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        value_entry.focus_set()

    def rename_value(self):
        """Rename the selected enum value"""
        selection = self.values_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a value to rename", parent=self.dialog)
            return

        idx = selection[0]
        value_data = self.signal_data['values'][idx]
        current_value_id = value_data.get('value', '')
        current_label = value_data.get('label', '')

        # Dialog to rename
        new_value_id = simpledialog.askstring(
            "Rename Value ID",
            f"Current: {current_value_id}\nEnter new value ID:",
            initialvalue=current_value_id,
            parent=self.dialog
        )

        if new_value_id and new_value_id != current_value_id:
            # Check for duplicates
            if any(v.get('value') == new_value_id for i, v in enumerate(self.signal_data['values']) if i != idx):
                messagebox.showwarning("Warning", f"Value '{new_value_id}' already exists", parent=self.dialog)
                return

            self.save_state()
            value_data['value'] = new_value_id
            self.mark_modified()
            self.modified = True
            self.load_values()
            self.refresh()  # Refresh main window details panel
            self.set_status(f"Renamed enum value to '{new_value_id}'")

        new_label = simpledialog.askstring(
            "Rename Label",
            f"Current: {current_label}\nEnter new label:",
            initialvalue=current_label,
            parent=self.dialog
        )

        if new_label and new_label != current_label:
            self.save_state()
            value_data['label'] = new_label
            self.mark_modified()
            self.modified = True
            self.load_values()
            self.refresh()  # Refresh main window details panel
            self.set_status(f"Renamed enum label to '{new_label}'")

    def delete_value(self):
        """Delete the selected enum value"""
        selection = self.values_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a value to delete", parent=self.dialog)
            return

        idx = selection[0]
        value_data = self.signal_data['values'][idx]
        value_id = value_data.get('value', '')

        result = messagebox.askyesno(
            "Confirm Delete",
            f"Delete enum value '{value_id}'?",
            parent=self.dialog
        )

        if result:
            self.save_state()
            del self.signal_data['values'][idx]
            self.mark_modified()
            self.modified = True
            self.load_values()
            self.refresh()  # Refresh main window details panel
            self.set_status(f"Deleted enum value '{value_id}'")

    def move_value_up(self):
        """Move selected value up in the list"""
        selection = self.values_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a value to move", parent=self.dialog)
            return

        idx = selection[0]
        if idx == 0:
            return  # Already at top

        self.save_state()
        values = self.signal_data['values']
        values[idx], values[idx - 1] = values[idx - 1], values[idx]
        self.mark_modified()
        self.modified = True
        self.load_values()
        self.refresh()  # Refresh main window details panel
        self.values_listbox.selection_set(idx - 1)
        self.set_status(f"Moved value up")

    def move_value_down(self):
        """Move selected value down in the list"""
        selection = self.values_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a value to move", parent=self.dialog)
            return

        idx = selection[0]
        if idx == len(self.signal_data['values']) - 1:
            return  # Already at bottom

        self.save_state()
        values = self.signal_data['values']
        values[idx], values[idx + 1] = values[idx + 1], values[idx]
        self.mark_modified()
        self.modified = True
        self.load_values()
        self.refresh()  # Refresh main window details panel
        self.values_listbox.selection_set(idx + 1)
        self.set_status(f"Moved value down")

    def move_value_to_signal(self):
        """Move the selected value to another enum signal"""
        selection = self.values_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a value to move", parent=self.dialog)
            return

        idx = selection[0]
        value_data = self.signal_data['values'][idx]

        # Get list of other enum signals
        enum_signals = []
        for sig_key, sig_data in self.all_signals.items():
            if sig_key != self.signal_key and isinstance(sig_data, dict) and sig_data.get('type') == 'enum':
                label = sig_data.get('ui', {}).get('label', sig_key)
                enum_signals.append((sig_key, label))

        if not enum_signals:
            messagebox.showwarning("Warning", "No other enum signals found", parent=self.dialog)
            return

        enum_signals.sort(key=lambda x: x[1])

        # Dialog to select target signal
        dialog = CategorySelectDialog(
            self.dialog,
            "Move Value To Signal",
            [f"{label} ({key})" for key, label in enum_signals],
            allow_new=False
        )

        if dialog.result:
            # Extract signal key from selection
            target_key = None
            for key, label in enum_signals:
                if dialog.result.startswith(label):
                    target_key = key
                    break

            if target_key and target_key in self.all_signals:
                self.save_state()

                # Remove from current signal
                moved_value = self.signal_data['values'].pop(idx)

                # Add to target signal
                target_signal = self.all_signals[target_key]
                if 'values' not in target_signal:
                    target_signal['values'] = []
                target_signal['values'].append(moved_value)

                self.mark_modified()
                self.modified = True
                self.load_values()
                self.refresh()  # Refresh main window details panel
                self.set_status(f"Moved value to signal '{target_key}'")


class EnumMergeDialog:
    """Dialog for merging two enum signals"""

    def __init__(self, parent, enum_signals, all_signals, save_state_callback, mark_modified_callback, refresh_callback, status_callback):
        self.parent = parent
        self.enum_signals = enum_signals
        self.all_signals = all_signals
        self.save_state = save_state_callback
        self.mark_modified = mark_modified_callback
        self.refresh = refresh_callback
        self.set_status = status_callback
        self.result = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Merge Enum Signals")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.create_widgets()

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """Create dialog widgets"""
        frame = ttk.Frame(self.dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Merge two enum signals by moving all values from source to target", wraplength=450).pack(pady=10)

        # Source signal
        ttk.Label(frame, text="Source Signal (will be deleted):").pack(anchor=tk.W, pady=(10, 0))
        self.source_combo = ttk.Combobox(
            frame,
            values=[f"{label} ({key})" for key, label in self.enum_signals],
            state="readonly",
            width=50
        )
        self.source_combo.pack(fill=tk.X, pady=5)

        # Target signal
        ttk.Label(frame, text="Target Signal (receives all values):").pack(anchor=tk.W, pady=(10, 0))
        self.target_combo = ttk.Combobox(
            frame,
            values=[f"{label} ({key})" for key, label in self.enum_signals],
            state="readonly",
            width=50
        )
        self.target_combo.pack(fill=tk.X, pady=5)

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="Merge", command=self.do_merge, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def do_merge(self):
        """Perform the merge operation"""
        source_selection = self.source_combo.get()
        target_selection = self.target_combo.get()

        if not source_selection or not target_selection:
            messagebox.showwarning("Warning", "Please select both source and target signals", parent=self.dialog)
            return

        if source_selection == target_selection:
            messagebox.showwarning("Warning", "Source and target must be different", parent=self.dialog)
            return

        # Extract signal keys
        source_key = None
        target_key = None

        for key, label in self.enum_signals:
            if source_selection.startswith(label):
                source_key = key
            if target_selection.startswith(label):
                target_key = key

        if not source_key or not target_key:
            messagebox.showerror("Error", "Could not identify signals", parent=self.dialog)
            return

        # Confirm
        result = messagebox.askyesno(
            "Confirm Merge",
            f"Merge '{source_key}' into '{target_key}'?\n\n"
            f"• All values will be moved to target\n"
            f"• If target lacks derive info, source's derive will be copied\n"
            f"• Source signal will be kept (with empty values list)\n"
            f"• No merge metadata will be created",
            parent=self.dialog
        )

        if not result:
            return

        # Perform merge
        self.save_state()

        source_signal = self.all_signals[source_key]
        target_signal = self.all_signals[target_key]

        source_values = source_signal.get('values', [])
        source_derive = source_signal.get('derive')
        
        if 'values' not in target_signal:
            target_signal['values'] = []

        # Move values from source to target
        for value in source_values:
            # Check for duplicates
            value_id = value.get('value')
            if not any(v.get('value') == value_id for v in target_signal['values']):
                target_signal['values'].append(value)
        
        # Preserve source event information - consolidate derive data
        if source_derive and 'derive' not in target_signal:
            # If target doesn't have derive, copy from source
            target_signal['derive'] = source_derive
        # Note: If both have derive, target's derive takes precedence
        # We don't create _merged_from metadata anymore

        # Keep source signal but clear its values (no metadata tags)
        source_signal['values'] = []

        self.mark_modified()
        self.result = True
        self.set_status(f"Merged values from '{source_key}' into '{target_key}' (source preserved)")
        self.refresh()

        messagebox.showinfo("Success", f"Successfully merged '{source_key}' into '{target_key}'", parent=self.dialog)
        self.dialog.destroy()


class EnumValidationDialog:
    """Dialog for validating enum signals and recovering missing derive information"""

    def __init__(self, parent, missing_derive, has_merged_from, all_signals, save_state_callback, mark_modified_callback, refresh_callback, status_callback):
        self.parent = parent
        self.missing_derive = missing_derive
        self.has_merged_from = has_merged_from
        self.all_signals = all_signals
        self.save_state = save_state_callback
        self.mark_modified = mark_modified_callback
        self.refresh = refresh_callback
        self.set_status = status_callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Enum Validation & Recovery")
        self.dialog.geometry("700x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.create_widgets()

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """Create dialog widgets"""
        frame = ttk.Frame(self.dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(frame, text="Enum Signal Validation Report", font=('TkDefaultFont', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        # Report text
        report_frame = ttk.LabelFrame(frame, text="Status", padding="5")
        report_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        report_text = tk.Text(report_frame, wrap=tk.WORD, height=20, width=80, bg='#f0f0f0')
        report_scroll = ttk.Scrollbar(report_frame, orient="vertical", command=report_text.yview)
        report_text.configure(yscrollcommand=report_scroll.set)

        report_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        report_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))

        report_frame.columnconfigure(0, weight=1)
        report_frame.rowconfigure(0, weight=1)

        # Generate and display report
        report = self._generate_report()
        report_text.insert('1.0', report)
        report_text.config(state=tk.DISABLED)

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Recover from Merged Signals", command=self._recover_from_merged).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(button_frame, text="Manual Recovery", command=self._manual_recovery).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5, pady=5)

    def _generate_report(self):
        """Generate validation report"""
        report = "ENUM VALIDATION REPORT\n"
        report += "=" * 80 + "\n\n"

        # Missing derive information
        if self.missing_derive:
            report += f"❌ MISSING DERIVE (Source Event) - {len(self.missing_derive)} enums:\n"
            report += "-" * 80 + "\n"
            for key in sorted(self.missing_derive):
                report += f"  • {key}\n"
            report += "\nThese enums are missing source event information (derive field).\n"
            report += "They may have lost this data during merging or import.\n\n"
        else:
            report += "✅ All enums have derive information\n\n"

        # Has merged_from metadata
        if self.has_merged_from:
            report += f"📋 RECOVERY METADATA - {len(self.has_merged_from)} enums with merge history:\n"
            report += "-" * 80 + "\n"
            for key, merges in self.has_merged_from:
                report += f"  • {key}\n"
                for merge_info in merges:
                    source = merge_info.get('source_key', 'unknown')
                    derive = merge_info.get('derive', {})
                    report += f"    └─ From: {source}\n"
                    report += f"       Path: {derive.get('path', 'unknown')}\n"
            report += "\nThese enums have metadata from merged signals.\n"
            report += "You can recover the source events using 'Recover from Merged Signals'.\n\n"
        else:
            report += "ℹ️  No merge history available\n\n"

        report += "=" * 80 + "\n"
        report += "NEXT STEPS:\n"
        if self.missing_derive:
            report += "1. Click 'Recover from Merged Signals' to automatically restore from history\n"
            report += "2. For any remaining missing data, use 'Manual Recovery' to add it manually\n"
        else:
            report += "✅ All enums are complete!\n"

        return report

    def _recover_from_merged(self):
        """Recover derive information from merged_from metadata"""
        if not self.has_merged_from:
            messagebox.showinfo("Info", "No merge history metadata available to recover from", parent=self.dialog)
            return

        self.save_state()
        recovered = 0

        for key, merges in self.has_merged_from:
            signal_data = self._get_signal_data(key)
            if signal_data and 'derive' not in signal_data:
                # Use first merge's derive information
                if merges and merges[0].get('derive'):
                    signal_data['derive'] = merges[0]['derive']
                    recovered += 1

        if recovered > 0:
            self.mark_modified()
            self.refresh()
            self.set_status(f"Recovered {recovered} enum(s) from merge history")
            messagebox.showinfo("Recovery Complete", f"Successfully recovered {recovered} enum(s) from merge history", parent=self.dialog)
        else:
            messagebox.showinfo("Info", "No additional enums could be recovered", parent=self.dialog)

    def _manual_recovery(self):
        """Open dialog to manually add derive information to missing enums"""
        if not self.missing_derive:
            messagebox.showinfo("Info", "All enums have derive information", parent=self.dialog)
            return

        dialog = tk.Toplevel(self.dialog)
        dialog.title("Manual Enum Recovery")
        dialog.geometry("600x400")
        dialog.transient(self.dialog)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Select enum to add source event information:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        # Enum selection
        ttk.Label(frame, text="Enum Signal:").pack(anchor=tk.W)
        combo = ttk.Combobox(frame, values=sorted(self.missing_derive), state="readonly", width=50)
        combo.pack(fill=tk.X, pady=(0, 10))

        # Derive path input
        ttk.Label(frame, text="Source Event Path (e.g., 'dashboard.GuiFocus' or 'state.Rank.Combat'):").pack(anchor=tk.W, pady=(10, 0))
        path_entry = ttk.Entry(frame, width=50)
        path_entry.pack(fill=tk.X, pady=(0, 10))

        # Derive operation
        ttk.Label(frame, text="Operation (usually 'path'):").pack(anchor=tk.W)
        op_entry = ttk.Entry(frame, width=50)
        op_entry.insert(0, "path")
        op_entry.pack(fill=tk.X, pady=(0, 20))

        def save_manual():
            if not combo.get() or not path_entry.get():
                messagebox.showwarning("Warning", "Please select enum and enter path", parent=dialog)
                return

            self.save_state()
            signal_data = self._get_signal_data(combo.get())
            if signal_data:
                signal_data['derive'] = {
                    'op': op_entry.get() or 'path',
                    'path': path_entry.get(),
                    'default': 0
                }
                self.mark_modified()
                self.refresh()
                self.set_status(f"Added source event to {combo.get()}")
                messagebox.showinfo("Success", f"Added source event to {combo.get()}", parent=dialog)
                dialog.destroy()

        ttk.Button(frame, text="Save", command=save_manual, width=20).pack(pady=10)

        # Center
        dialog.update_idletasks()
        x = self.dialog.winfo_x() + (self.dialog.winfo_width() - dialog.winfo_width()) // 2
        y = self.dialog.winfo_y() + (self.dialog.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def _get_signal_data(self, signal_key):
        """Get signal data by key (handles nested keys)"""
        if '.' in signal_key:
            parts = signal_key.split('.')
            data = self.all_signals
            for part in parts:
                if part in data:
                    data = data[part]
                else:
                    return None
            return data
        else:
            return self.all_signals.get(signal_key)


def main():
    """Main entry point"""
    # Find catalog file
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    catalog_path = project_root / "data" / "signals_catalog.json"
    
    if not catalog_path.exists():
        print(f"Error: signals_catalog.json not found at {catalog_path}")
        return 1
    
    # Create and run UI
    root = tk.Tk()
    app = SignalCatalogEditor(root, catalog_path)
    root.mainloop()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
