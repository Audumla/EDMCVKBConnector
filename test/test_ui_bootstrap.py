"""
Manual UI bootstrap for the rule editor.

Run with: UI_BOOTSTRAP=1 pytest test/test_ui_bootstrap.py -s
"""

import os
import shutil
import tempfile
import json
from pathlib import Path

import pytest
import tkinter as tk
from unittest.mock import patch, MagicMock

from edmcruleengine.ui.rule_editor import RuleEditorUI


def test_rule_editor_ui_bootstrap(test_settings):
    if not test_settings.get("ui_bootstrap"):
        pytest.skip("Set ui_bootstrap: 1 in test/test_config.json to run the UI bootstrap test.")

    plugin_root = Path(__file__).parent.parent
    rules_file_setting = test_settings.get("ui_rules_file", "data/rules.json.example")
    rules_source = Path(rules_file_setting)
    if not rules_source.is_absolute():
        rules_source = plugin_root / rules_source

    if not rules_source.exists():
        pytest.skip(f"Rules file not found: {rules_source}")

    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "rules.json"
        shutil.copy(rules_source, rules_path)

        root = tk.Tk()
        # Keep it invisible during automated tests
        root.withdraw()

        # Mock blocking dialogs
        with patch("edmcruleengine.ui.rule_editor._centered_info"), \
             patch("edmcruleengine.ui.rule_editor._centered_yesno", return_value=True), \
             patch("edmcruleengine.ui.rule_editor._centered_error"):
            
            ui = RuleEditorUI(root, rules_path, plugin_root)

            def run_automated_test():
                """Perform a series of UI actions and then close."""
                try:
                    # 1. Edit an existing rule
                    if ui.rules:
                        ui.initial_rule_index = 0
                        ui._show_rule_editor()
                        root.update()
                        
                        if ui.active_editor:
                            # Change title
                            ui.active_editor.title_var.set("Automated Test Edit")
                            # Trigger save
                            ui.active_editor._save()
                            root.update()
                    
                    # 2. Create a new rule
                    # The current UI architecture is designed to edit one rule then close.
                    # We'll create a new UI instance for the 'new rule' case (-1)
                    new_rule_root = tk.Toplevel(root)
                    new_rule_root.withdraw()
                    ui_new = RuleEditorUI(new_rule_root, rules_path, plugin_root, initial_rule_index=-1)
                    root.update()
                    
                    if ui_new.active_editor:
                        ui_new.active_editor.title_var.set("New Automated Rule")
                        ui_new.active_editor._save()
                        root.update()
                    
                    # 3. Verify changes were written to disk
                    with open(rules_path, "r", encoding="utf-8") as f:
                        saved_data = json.load(f)
                        titles = [r.get("title") for r in saved_data]
                        assert "Automated Test Edit" in titles
                        assert "New Automated Rule" in titles

                finally:
                    # Always close and exit the loop
                    try:
                        ui._on_close()
                    except Exception:
                        pass
                    root.quit()
                    root.destroy()

            # Schedule the automated test to run once the mainloop starts
            root.after(100, run_automated_test)
            root.mainloop()
