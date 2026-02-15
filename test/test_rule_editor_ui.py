"""
Test the rule editor UI to ensure it can be instantiated.
"""

import sys
from pathlib import Path

import tkinter as tk

# Add source paths
plugin_root = Path(__file__).parent.parent
src_path = plugin_root / "src"
sys.path.insert(0, str(src_path))


def test_editor_instantiation():
    """Test that the editor dialog can be instantiated."""
    from edmcruleengine.rule_editor_ui import RuleEditorDialog, load_events_config
    from edmcruleengine.rules_engine import FLAGS, FLAGS2, GUI_FOCUS_NAME_TO_VALUE

    root = tk.Tk()
    root.withdraw()
    dialog = None

    sample_rule = {
        "id": "test_rule",
        "enabled": True,
        "when": {
            "source": "dashboard",
            "event": "Status",
            "all": [{"flags": {"all_of": ["FlagsLandingGearDown"]}}],
        },
        "then": {"vkb_set_shift": ["Subshift3"], "log": "Landing gear down"},
        "else": {"vkb_clear_shift": ["Subshift3"]},
    }

    try:
        events_config = load_events_config(plugin_root)
        dialog = RuleEditorDialog(
            root,
            sample_rule,
            events_config,
            FLAGS,
            FLAGS2,
            GUI_FOCUS_NAME_TO_VALUE,
        )

        built_rule = dialog._build_rule_from_ui()
        assert isinstance(built_rule, dict)
        assert built_rule.get("id") == "test_rule"
    finally:
        if dialog is not None:
            dialog.dialog.destroy()
        root.destroy()


def test_events_config_loading():
    """Test that events config loads correctly."""
    from edmcruleengine.rule_editor_ui import load_events_config

    events_config = load_events_config(plugin_root)

    assert isinstance(events_config, dict)
    assert isinstance(events_config.get("sources", []), list)
    assert isinstance(events_config.get("events", []), list)
    assert isinstance(events_config.get("condition_types", []), list)
    assert isinstance(events_config.get("shift_flags", []), list)
