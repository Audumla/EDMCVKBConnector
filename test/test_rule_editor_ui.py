"""
Test the rule editor UI to ensure it can be instantiated.
"""

import sys
import os
from pathlib import Path

# Add source paths
plugin_root = Path(__file__).parent.parent
src_path = plugin_root / "src"
sys.path.insert(0, str(src_path))

import json
import tkinter as tk
from tkinter import ttk

def test_editor_instantiation():
    """Test that the editor dialog can be instantiated."""
    from edmcruleengine.rule_editor_ui import RuleEditorDialog, load_events_config
    from edmcruleengine.rules_engine import FLAGS, FLAGS2, GUI_FOCUS_NAME_TO_VALUE
    
    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide root window
    
    # Load events config
    events_config = load_events_config(plugin_root)
    
    # Test with a sample rule
    sample_rule = {
        "id": "test_rule",
        "enabled": True,
        "when": {
            "source": "dashboard",
            "event": "Status",
            "all": [
                {
                    "flags": {
                        "all_of": ["FlagsLandingGearDown"]
                    }
                }
            ]
        },
        "then": {
            "vkb_set_shift": ["Subshift3"],
            "log": "Landing gear down"
        },
        "else": {
            "vkb_clear_shift": ["Subshift3"]
        }
    }
    
    try:
        # Create dialog (don't show it)
        dialog = RuleEditorDialog(root, sample_rule, events_config, FLAGS, FLAGS2, GUI_FOCUS_NAME_TO_VALUE)
        
        # Don't show, just verify it was created
        print("✓ RuleEditorDialog instantiated successfully")
        
        # Build rule from UI to test that functionality
        built_rule = dialog._build_rule_from_ui()
        print("✓ _build_rule_from_ui() executed successfully")
        print(f"  Built rule ID: {built_rule.get('id')}")
        
        # Close dialog
        dialog.dialog.destroy()
        root.destroy()
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        root.destroy()
        return False

def test_events_config_loading():
    """Test that events config loads correctly."""
    from edmcruleengine.rule_editor_ui import load_events_config
    
    events_config = load_events_config(plugin_root)
    
    print("\n Events Config:")
    print(f"  Sources: {len(events_config.get('sources', []))}")
    print(f"  Events: {len(events_config.get('events', []))}")
    print(f"  Condition types: {len(events_config.get('condition_types', []))}")
    print(f"  Shift flags: {len(events_config.get('shift_flags', []))}")
    
    # Print first few events
    events = events_config.get('events', [])
    if events:
        print("\n  First 5 events:")
        for event in events[:5]:
            print(f"    - {event.get('title')} ({event.get('source')}/{event.get('event')})")
    
    return True

if __name__ == "__main__":
    print("Testing Rule Editor UI...")
    print(f"Plugin root: {plugin_root}")
    
    print("\n=== Test 1: Events Config Loading ===")
    test_events_config_loading()
    
    print("\n=== Test 2: Editor Instantiation ===")
    success = test_editor_instantiation()
    
    if success:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
