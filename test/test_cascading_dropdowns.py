"""
Test to verify three-level cascading dropdown support for rule editor.
Demonstrates: Category -> Subcategory -> Signal structure
"""

import json
from pathlib import Path
from src.edmcruleengine.signals_catalog import SignalsCatalog


def test_cascading_dropdown_structure():
    """Verify the catalog supports three-level hierarchy with optional subcategories."""
    plugin_dir = Path(".")
    catalog = SignalsCatalog.from_plugin_dir(str(plugin_dir))
    
    # Organize signals by category and subcategory as the UI will
    category_subcategory_signals = {}
    
    for signal_id, signal_def in catalog.signals.items():
        if signal_id.startswith("_") or not isinstance(signal_def, dict):
            continue
        
        ui = signal_def.get("ui", {})
        category = ui.get("category", "Other")
        subcategory = ui.get("subcategory")  # None if not present
        
        if category not in category_subcategory_signals:
            category_subcategory_signals[category] = {}
        
        # Use empty string for signals without subcategory
        subcat_key = subcategory if subcategory else ""
        if subcat_key not in category_subcategory_signals[category]:
            category_subcategory_signals[category][subcat_key] = []
        
        category_subcategory_signals[category][subcat_key].append({
            "id": signal_id,
            "label": ui.get("label", signal_id)
        })
    
    # Verify Commander category has the expected structure
    assert "Commander" in category_subcategory_signals, "Commander category should exist"
    commander_sigs = category_subcategory_signals["Commander"]
    
    # Should have signals with subcategories
    has_subcats = any(key for key in commander_sigs.keys() if key)
    assert has_subcats, "Commander category should have signals with subcategories"
    
    # Check specific subcategories exist
    expected_subcats = {"Rank", "Rank Progress", "Faction Progress"}
    actual_subcats = set(key for key in commander_sigs.keys() if key)
    assert expected_subcats.issubset(actual_subcats), f"Expected subcategories {expected_subcats}, got {actual_subcats}"
    
    # Verify structure matches three-level cascade
    print("\nPerfect! Three-level hierarchy confirmed:")
    print("\nCommander -> Subcategory -> Signals:")
    for subcat in sorted(actual_subcats):
        signals = commander_sigs[subcat]
        print(f"  {subcat}: {len(signals)} signals")
        for sig in sorted(signals, key=lambda s: s['label'])[:2]:
            print(f"    - {sig['label']} ({sig['id']})")
        if len(signals) > 2:
            print(f"    ... and {len(signals)-2} more")
    
    # Also show signals without subcategory (if any)
    no_subcat = commander_sigs.get("", [])
    if no_subcat:
        print(f"  (no subcategory): {len(no_subcat)} signals")
        for sig in sorted(no_subcat, key=lambda s: s['label'])[:2]:
            print(f"    - {sig['label']} ({sig['id']})")
    
    print("\nUI will display as:")
    print("  1. Category dropdown (e.g., 'Commander')")
    print("  2. Subcategory dropdown (shows only if category has subcategories)")
    print("  3. Signal dropdown (filtered by category AND subcategory)")


if __name__ == "__main__":
    test_cascading_dropdown_structure()
    print("\nTest passed!")
