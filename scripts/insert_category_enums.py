"""
Insert generated category enums into signals_catalog.json after system_event.
"""

import json
from pathlib import Path

def main():
    # Read the generated enums
    generated_path = Path("scripts/generated_category_enums.json")
    with open(generated_path, 'r', encoding='utf-8') as f:
        generated_enums = json.load(f)
    
    # Read the signals catalog
    catalog_path = Path("signals_catalog.json")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    # Find the position after system_event
    signals = catalog.get("signals", {})
    signal_keys = list(signals.keys())
    
    try:
        system_event_idx = signal_keys.index("system_event")
        insert_after_idx = system_event_idx + 1
    except ValueError:
        print("ERROR: system_event not found in catalog!")
        return
    
    # Create new signals dict with enums inserted
    new_signals = {}
    for i, key in enumerate(signal_keys):
        new_signals[key] = signals[key]
        
        # After system_event, insert all generated enums
        if i == system_event_idx:
            for enum_id, enum_def in generated_enums.items():
                new_signals[enum_id] = enum_def
    
    # Update catalog
    catalog["signals"] = new_signals
    
    # Write back to file
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Inserted {len(generated_enums)} category enums after system_event")
    print(f"✓ Total signals: {len(new_signals)}")


if __name__ == "__main__":
    main()
