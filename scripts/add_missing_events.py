#!/usr/bin/env python3
"""
Add missing EDMC events to signals_catalog.json

This script adds the 11 unregistered events identified in the coverage validation:
- HIGH: EngineerApply, NavRouteClear, StartUp
- MEDIUM: CommitCrime, Squadron
- LOW: ShutDown, UpgradeSuit, UpgradeWeapon, WeaponLoadout, Loadouts, OnFootLoadout
"""

import json
from pathlib import Path
from typing import Dict, List

def add_event_to_signal(signal_def: dict, event_name: str, value_name: str, label: str) -> bool:
    """
    Add an event to a signal's values and derive cases.

    Returns True if added, False if already exists.
    """
    # Check if value already exists
    for value in signal_def.get('values', []):
        if value.get('recent_event') == event_name:
            print(f"  [!] Event {event_name} already exists in signal")
            return False

    # Add to values (insert before last item to keep "none" at start)
    new_value = {
        "value": value_name,
        "label": label,
        "recent_event": event_name
    }
    signal_def['values'].append(new_value)

    # Add to derive cases (before default case)
    new_case = {
        "when": {
            "op": "recent",
            "event_name": event_name,
            "within_seconds": 300
        },
        "value": value_name
    }
    signal_def['derive']['cases'].append(new_case)

    print(f"  [+] Added {event_name} -> {value_name}")
    return True

def main():
    print("=" * 70)
    print("Adding Missing Events to Signals Catalog")
    print("=" * 70)

    # Load catalog
    project_root = Path(__file__).parent.parent
    catalog_path = project_root / "signals_catalog.json"

    print(f"\nLoading catalog from: {catalog_path}")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    signals = catalog['signals']
    changes_made = 0

    # 1. Add to system_event
    print("\n1. Adding to system_event signal...")
    if 'system_event' in signals:
        if add_event_to_signal(signals['system_event'], 'StartUp', 'startup', 'Game startup'):
            changes_made += 1
        if add_event_to_signal(signals['system_event'], 'Shutdown', 'shutdown', 'Game shutdown'):
            changes_made += 1
        if add_event_to_signal(signals['system_event'], 'Squadron', 'squadron_loaded', 'Squadron loaded'):
            changes_made += 1
        if add_event_to_signal(signals['system_event'], 'Loadouts', 'loadouts_loaded', 'Loadouts loaded'):
            changes_made += 1

    # 2. Add to travel_event
    print("\n2. Adding to travel_event signal...")
    if 'travel_event' in signals:
        if add_event_to_signal(signals['travel_event'], 'NavRouteClear', 'nav_route_clear', 'Route cleared'):
            changes_made += 1

    # 3. Add to engineering_event
    print("\n3. Adding to engineering_event signal...")
    if 'engineering_event' in signals:
        if add_event_to_signal(signals['engineering_event'], 'EngineerApply', 'engineer_apply', 'Engineer unlock applied'):
            changes_made += 1

    # 4. Add to combat_event (CommitCrime fits here as crime activity)
    print("\n4. Adding to combat_event signal...")
    if 'combat_event' in signals:
        if add_event_to_signal(signals['combat_event'], 'CommitCrime', 'commit_crime', 'Crime committed'):
            changes_made += 1

    # 5. Check if on_foot_event exists, if not use ship_event for Odyssey events
    print("\n5. Adding Odyssey events...")
    on_foot_event_exists = 'on_foot_event' in signals

    if on_foot_event_exists:
        if add_event_to_signal(signals['on_foot_event'], 'OnFootLoadout', 'on_foot_loadout', 'On-foot loadout'):
            changes_made += 1
        if add_event_to_signal(signals['on_foot_event'], 'UpgradeSuit', 'upgrade_suit', 'Suit upgraded'):
            changes_made += 1
        if add_event_to_signal(signals['on_foot_event'], 'UpgradeWeapon', 'upgrade_weapon', 'Weapon upgraded'):
            changes_made += 1
        if add_event_to_signal(signals['on_foot_event'], 'WeaponLoadout', 'weapon_loadout', 'Weapon loadout'):
            changes_made += 1
    else:
        # Add to ship_event as fallback
        print("  [!] No on_foot_event signal found, adding to ship_event instead")
        if 'ship_event' in signals:
            if add_event_to_signal(signals['ship_event'], 'OnFootLoadout', 'on_foot_loadout', 'On-foot loadout'):
                changes_made += 1
            if add_event_to_signal(signals['ship_event'], 'UpgradeSuit', 'upgrade_suit', 'Suit upgraded'):
                changes_made += 1
            if add_event_to_signal(signals['ship_event'], 'UpgradeWeapon', 'upgrade_weapon', 'Weapon upgraded'):
                changes_made += 1
            if add_event_to_signal(signals['ship_event'], 'WeaponLoadout', 'weapon_loadout', 'Weapon loadout'):
                changes_made += 1

    # Save if changes were made
    if changes_made > 0:
        # Create backup
        backup_path = catalog_path.with_suffix('.json.backup')
        print(f"\n[BACKUP] Creating backup: {backup_path}")
        import shutil
        shutil.copy2(catalog_path, backup_path)

        # Save updated catalog
        print(f"[SAVE] Saving updated catalog...")
        with open(catalog_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] Added {changes_made} events to the catalog!")
        print(f"          Backup saved to: {backup_path}")
    else:
        print(f"\n[INFO] No changes made - all events already exist")

    print("\n" + "=" * 70)
    return changes_made > 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
