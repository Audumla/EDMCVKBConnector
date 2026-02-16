"""
Generate mapping from old event signals to new category enum signals for test updates.
"""

import json
from pathlib import Path

# Load the catalog to get the category enums
catalog_path = Path("signals_catalog.json")
with open(catalog_path, 'r', encoding='utf-8') as f:
    catalog = json.load(f)

signals = catalog.get("signals", {})

# Build mapping: old_signal_id -> (category_enum_id, enum_value)
event_signal_mapping = {}

# Find all category event enums
category_enums = {
    "system_event": "System",
    "travel_event": "Travel",
    "combat_event": "Combat",
    "exploration_event": "Exploration",
    "trading_event": "Trading",
    "mission_event": "Missions",
    "ship_event": "Ship",
    "engineering_event": "Engineering",
    "carrier_event": "Fleet Carrier",
    "onfoot_event": "On-Foot",
    "colonisation_event": "Colonisation",
    "comms_event": "Comms",
    "progress_event": "Progress",
    "misc_event": "Misc"
}

for enum_id in category_enums:
    if enum_id not in signals:
        continue
    
    enum_def = signals[enum_id]
    values = enum_def.get("values", [])
    
    for value_def in values:
        if value_def.get("value") == "none":
            continue
        
        recent_event = value_def.get("recent_event")
        if not recent_event:
            continue
        
        # Generate old signal ID: event_{snake_case}
        # Convert PascalCase event name to snake_case
        event_name = recent_event
        snake_case = ""
        for i, char in enumerate(event_name):
            if char.isupper() and i > 0:
                snake_case += "_"
            snake_case += char.lower()
        
        old_signal_id = f"event_{snake_case}"
        enum_value = value_def.get("value")
        
        event_signal_mapping[old_signal_id] = (enum_id, enum_value)

# Print as Python dict for easy copy-paste
print("EVENT_SIGNAL_MAPPING = {")
for old_id in sorted(event_signal_mapping.keys()):
    enum_id, enum_value = event_signal_mapping[old_id]
    print(f'    "{old_id}": ("{enum_id}", "{enum_value}"),')
print("}")

print(f"\n# Total mappings: {len(event_signal_mapping)}")

# Also save as JSON
with open("scripts/event_signal_mapping.json", "w", encoding="utf-8") as f:
    json.dump(event_signal_mapping, f, indent=2)
print("\n✓ Saved to scripts/event_signal_mapping.json")
