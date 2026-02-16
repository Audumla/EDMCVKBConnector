"""
Remove individual event signals from signals_catalog.json (Phase 4 cleanup).
Removes all signals with signal_id starting with "event_" and type "event".
"""

import json
from pathlib import Path

def main():
    # Read the signals catalog
    catalog_path = Path("signals_catalog.json")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    signals = catalog.get("signals", {})
    
    # Find all event signals to remove
    to_remove = []
    for signal_id, signal_def in signals.items():
        if signal_id.startswith("event_") and signal_def.get("type") == "event":
            to_remove.append(signal_id)
    
    print(f"Found {len(to_remove)} individual event signals to remove:")
    for signal_id in sorted(to_remove):
        print(f"  - {signal_id}")
    
    # Remove them
    for signal_id in to_remove:
        del signals[signal_id]
    
    # Also remove the comment markers for event sections
    comment_keys = [k for k in signals.keys() if k.startswith("_comment_events_")]
    for key in comment_keys:
        del signals[key]
    
    print(f"\nRemoved {len(comment_keys)} event section comment markers")
    
    # Update catalog
    catalog["signals"] = signals
    
    # Write back to file
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Removed {len(to_remove)} individual event signals")
    print(f"✓ Removed {len(comment_keys)} comment markers")
    print(f"✓ Total signals remaining: {len(signals)}")
    print(f"\nPhase 4 consolidation complete:")
    print(f"  Before: {len(to_remove) + len(signals)} signals")
    print(f"  After: {len(signals)} signals")
    print(f"  Reduction: {len(to_remove)} signals (-{100*len(to_remove)/(len(to_remove)+len(signals)):.1f}%)")


if __name__ == "__main__":
    main()
