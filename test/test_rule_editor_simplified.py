"""Test simplified rule editor functionality."""

import pytest
from pathlib import Path

pytestmark = pytest.mark.skip_all_by_default

def test_rule_editor_imports():
    """Test that rule editor modules can be imported."""
    from edmcruleengine.rule_editor import RuleEditorUI, RuleEditor, show_rule_editor
    from edmcruleengine.signals_catalog import SignalsCatalog
    
    assert RuleEditorUI is not None
    assert RuleEditor is not None
    assert show_rule_editor is not None
    assert SignalsCatalog is not None


def test_catalog_loads_with_comments():
    """Test that the catalog loads correctly even with comment entries."""
    from edmcruleengine.signals_catalog import SignalsCatalog
    
    plugin_dir = Path(__file__).parent.parent
    catalog = SignalsCatalog.from_plugin_dir(str(plugin_dir))
    
    # Verify catalog loaded
    assert catalog.signals is not None
    
    # Count real signals (not comments)
    real_signals = [s for s in catalog.signals.keys() if not s.startswith("_")]
    assert len(real_signals) > 100  # Should have many signals
    
    # Verify core signals exist
    core_signals = catalog.get_core_signals()
    assert len(core_signals) > 0
    
    # Verify detail signals exist
    detail_signals = catalog.get_detail_signals()
    assert len(detail_signals) > 0


def test_rule_editor_handles_catalog_comments():
    """Test that RuleEditor correctly filters out catalog comments."""
    import tempfile
    import json
    from edmcruleengine.rule_editor import RuleEditor
    from edmcruleengine.signals_catalog import SignalsCatalog
    import tkinter as tk
    
    plugin_dir = Path(__file__).parent.parent
    catalog = SignalsCatalog.from_plugin_dir(str(plugin_dir))
    
    # Create a test rule
    test_rule = {
        "title": "Test Rule",
        "enabled": True,
        "when": {"all": [], "any": []},
        "then": [],
        "else": []
    }
    
    # Create temporary file for rules
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump([test_rule], f)
        rules_file = Path(f.name)
    
    try:
        # Create tkinter root (hidden)
        root = tk.Tk()
        root.withdraw()
        
        # Create editor
        editor = RuleEditor(
            root,
            test_rule,
            catalog,
            on_save=lambda r: None,
            on_cancel=lambda: None
        )
        
        # Verify editor built lookup tables without errors
        assert editor.all_signals is not None
        assert len(editor.all_signals) > 0
        
        # Verify no comment entries leaked through
        for signal_id in editor.all_signals.keys():
            assert not signal_id.startswith("_"), f"Comment entry {signal_id} should be filtered"
        
        # Clean up
        root.destroy()
        
    finally:
        rules_file.unlink(missing_ok=True)


if __name__ == "__main__":
    # Run the tests
    test_rule_editor_imports()
    print("✓ Import test passed")
    
    test_catalog_loads_with_comments()
    print("✓ Catalog test passed")
    
    test_rule_editor_handles_catalog_comments()
    print("✓ Editor test passed")
    
    print("\nAll tests passed!")
