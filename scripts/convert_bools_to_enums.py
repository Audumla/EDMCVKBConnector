"""
Convert all boolean signals to 2-value enums with meaningful states.

Phase 5: Boolean Flag Consolidation
Converts 35 boolean flags to enums for consistency and better UX.
"""

import json
from pathlib import Path


# Mapping of boolean signals to their enum value pairs
# Format: signal_name -> (false_value, false_label, true_value, true_label)
BOOL_TO_ENUM = {
    # Equipment States
    "night_vision": ("off", "Off", "on", "On"),
    "flag_landing_gear_down": ("up", "Up", "down", "Down"),
    "flag_shields_up": ("down", "Down", "up", "Up"),
    "flag_hardpoints_deployed": ("retracted", "Retracted", "deployed", "Deployed"),
    "flag_cargo_scoop_deployed": ("retracted", "Retracted", "deployed", "Deployed"),
    "flag_flight_assist_off": ("on", "On", "off", "Off"),
    "flag_srv_turret": ("retracted", "Retracted", "deployed", "Deployed"),
    
    # Warning Flags
    "flag_low_fuel": ("normal", "Normal", "low", "Low"),
    "flag_overheating": ("normal", "Normal", "overheating", "Overheating"),
    "flag_in_danger": ("safe", "Safe", "danger", "Danger"),
    "flag_low_oxygen": ("normal", "Normal", "low", "Low"),
    "flag_low_health": ("normal", "Normal", "low", "Low"),
    
    # Gameplay States - simple yes/no
    "in_taxi": ("no", "No", "yes", "Yes"),
    "in_multicrew": ("no", "No", "yes", "Yes"),
    "in_wing": ("no", "No", "yes", "Yes"),
    "mass_locked": ("no", "No", "yes", "Yes"),
    "interdicted": ("no", "No", "yes", "Yes"),
    "target_locked": ("no", "No", "yes", "Yes"),
    "breathable_atmosphere": ("no", "No", "yes", "Yes"),
    "glide_mode": ("no", "No", "yes", "Yes"),
    "flag_on_foot": ("no", "No", "yes", "Yes"),
    "flag_aim_down_sight": ("no", "No", "yes", "Yes"),
    "flag_supercruise": ("no", "No", "yes", "Yes"),
    "flag_in_wing": ("no", "No", "yes", "Yes"),
    "flag_hud_analysis_mode": ("no", "No", "yes", "Yes"),
    "flag_altitude_from_avg_radius": ("no", "No", "yes", "Yes"),
    
    # Commander Status
    "has_route": ("no", "No", "yes", "Yes"),
    "has_vip_passengers": ("no", "No", "yes", "Yes"),
    "has_wanted_passengers": ("no", "No", "yes", "Yes"),
    "has_fleet_carrier": ("no", "No", "yes", "Yes"),
    "has_npc_crew": ("no", "No", "yes", "Yes"),
    "powerplay_pledged": ("no", "No", "yes", "Yes"),
    "in_squadron": ("no", "No", "yes", "Yes"),
    "has_lat_long": ("no", "No", "yes", "Yes"),
    "srv_under_ship": ("no", "No", "yes", "Yes"),
}


def convert_bool_to_enum(signal_def, false_val, false_label, true_val, true_label):
    """Convert a boolean signal definition to enum."""
    # Keep existing fields
    result = {
        "type": "enum",
        "title": signal_def.get("title"),
        "ui": signal_def.get("ui").copy() if "ui" in signal_def else {}
    }
    
    # Create enum values
    result["values"] = [
        {"value": false_val, "label": false_label},
        {"value": true_val, "label": true_label}
    ]
    
    # Update derivation to map boolean to enum value
    if "derive" in signal_def:
        result["derive"] = {
            "op": "map",
            "from": signal_def["derive"],
            "map": {
                "false": false_val,
                "true": true_val
            },
            "default": false_val
        }
    
    return result


def main():
    """Convert all boolean signals in catalog to enums."""
    catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
    
    # Load catalog
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    signals = catalog.get("signals", {})
    converted_count = 0
    
    # Convert each boolean signal
    for signal_name, enum_values in BOOL_TO_ENUM.items():
        if signal_name in signals:
            signal_def = signals[signal_name]
            
            # Verify it's actually a boolean
            if signal_def.get("type") != "bool":
                print(f"⚠ {signal_name}: Not a boolean (type={signal_def.get('type')}), skipping")
                continue
            
            # Convert to enum
            false_val, false_label, true_val, true_label = enum_values
            new_def = convert_bool_to_enum(signal_def, false_val, false_label, true_val, true_label)
            signals[signal_name] = new_def
            
            converted_count += 1
            print(f"✓ {signal_name}: bool → enum ({false_val}/{true_val})")
        else:
            print(f"⚠ {signal_name}: Not found in catalog")
    
    # Save updated catalog
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"✓ Converted {converted_count} boolean signals to enums")
    print(f"✓ Catalog updated: {catalog_path}")


if __name__ == "__main__":
    main()
