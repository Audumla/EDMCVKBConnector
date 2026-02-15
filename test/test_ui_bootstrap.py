"""
Manual UI bootstrap for the rule editor.

Run with: UI_BOOTSTRAP=1 pytest test/test_ui_bootstrap.py -s
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
import tkinter as tk

from edmcruleengine.rule_editor import RuleEditorUI


def test_rule_editor_ui_bootstrap():
    if os.environ.get("UI_BOOTSTRAP") != "1":
        pytest.skip("Set UI_BOOTSTRAP=1 to run the UI bootstrap test.")

    plugin_root = Path(__file__).parent.parent
    rules_source = Path(os.environ.get("UI_RULES_FILE", plugin_root / "rules.json.example"))

    if not rules_source.exists():
        pytest.skip(f"Rules file not found: {rules_source}")

    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "rules.json"
        shutil.copy(rules_source, rules_path)

        root = tk.Tk()
        root.withdraw()

        ui = RuleEditorUI(root, rules_path, plugin_root)

        if ui.rules:
            ui._edit_rule(0)
            if ui.active_editor:
                current = ui.active_editor.title_var.get().strip()
                ui.active_editor.title_var.set(f"Bootstrap Edit - {current or 'New Rule'}")

        def _close():
            ui._on_close()
            root.quit()

        ui.window.protocol("WM_DELETE_WINDOW", _close)
        ui.window.deiconify()
        ui.window.lift()
        ui.window.focus_force()

        root.mainloop()
