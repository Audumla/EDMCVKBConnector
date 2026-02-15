"""Manual UI bootstrap runner for the rule editor."""

import shutil
import sys
import tempfile
from pathlib import Path

import tkinter as tk

PLUGIN_ROOT = Path(__file__).parent.parent
SRC_PATH = str(PLUGIN_ROOT / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from edmcruleengine.rule_editor import RuleEditorUI


def main() -> int:
    plugin_root = PLUGIN_ROOT
    rules_source = Path(plugin_root / "rules.json.example")

    if not rules_source.exists():
        print(f"Rules file not found: {rules_source}")
        return 1

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

    return 0


if __name__ == "__main__":
    sys.exit(main())
