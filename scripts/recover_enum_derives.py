#!/usr/bin/env python3
"""
Recover missing derive (source event) information for enum signals
Based on Elite Dangerous/EDMC event structure and signal naming patterns
"""

import json
from pathlib import Path


# Mapping of signal keys to their correct derive paths
ENUM_DERIVE_MAPPINGS = {
    # HUD enums - from dashboard
    "gui_focus": {"op": "path", "path": "dashboard.GuiFocus", "default": 0},
    "hud_mode": {"op": "path", "path": "dashboard.HudMode", "default": 0},
    "night_vision": {"op": "bitfield", "path": "dashboard.Flags", "bit": 28, "default": 0},
    
    # Commander transport
    "transport": {"op": "derive", "from": ["vehicle_type", "on_foot_state"], "default": 0},  # Derived signal
    
    # Commander ranks - from state
    "commander_ranks.empire": {"op": "path", "path": "state.Rank.Empire", "default": 0},
    "commander_ranks.federation": {"op": "path", "path": "state.Rank.Federation", "default": 0},
    
    # Commander promotions - derived from rank changes (journal events)
    "commander_promotion.combat": {"op": "journal_event", "event": "Rank", "field": "Combat", "default": 0},
    "commander_promotion.trade": {"op": "journal_event", "event": "Rank", "field": "Trade", "default": 0},
    "commander_promotion.explore": {"op": "journal_event", "event": "Rank", "field": "Explore", "default": 0},
    "commander_promotion.empire": {"op": "journal_event", "event": "Rank", "field": "Empire", "default": 0},
    "commander_promotion.federation": {"op": "journal_event", "event": "Rank", "field": "Federation", "default": 0},
    "commander_promotion.cqc": {"op": "journal_event", "event": "Rank", "field": "CQC", "default": 0},
    "commander_promotion.soldier": {"op": "journal_event", "event": "Rank", "field": "Soldier", "default": 0},
    "commander_promotion.exobiologist": {"op": "journal_event", "event": "Rank", "field": "Exobiologist", "default": 0},
    "commander_promotion.mercenary": {"op": "journal_event", "event": "Rank", "field": "Mercenary", "default": 0},
    
    # Ship docking states - derived from dashboard flags and events
    "docking_state": {"op": "derive", "from": ["flag_docked", "flag_landed", "landing_gear"], "default": 0},
    "has_lat_long": {"op": "bitfield", "path": "dashboard.Flags", "bit": 21, "default": 0},
    "docking_request_state": {"op": "derive", "from": ["docking_state", "journal_events"], "default": 0},
    
    # Location proximity
    "body_proximity": {"op": "derive", "from": ["flag_near_body", "supercruise_state"], "default": 0},
    
    # Travel states
    "supercruise_state": {"op": "derive", "from": ["flag_supercruise", "flag_fsd_jump"], "default": 0},
    "fsd_state": {"op": "derive", "from": ["flag_fsd_charging", "flag_fsd_cooldown", "flag_fsd_jump"], "default": 0},
    "jump_type": {"op": "journal_event", "event": "FSDJump", "field": "JumpType", "default": 0},
    "mass_locked": {"op": "bitfield", "path": "dashboard.Flags", "bit": 16, "default": 0},
    "flag_in_danger": {"op": "bitfield", "path": "dashboard.Flags", "bit": 22, "default": 0},
    "flag_hud_analysis_mode": {"op": "bitfield", "path": "dashboard.Flags", "bit": 27, "default": 0},
    "flag_altitude_from_avg_radius": {"op": "bitfield", "path": "dashboard.Flags", "bit": 29, "default": 0},
    "jet_cone_boost_state": {"op": "derive", "from": ["flag_scooping_fuel", "fsd_state"], "default": 0},
    
    # Ship flag states - from dashboard.Flags
    "landing_gear": {"op": "bitfield", "path": "dashboard.Flags", "bit": 2, "default": 0},
    "flag_shields_up": {"op": "bitfield", "path": "dashboard.Flags", "bit": 3, "default": 0},
    "flag_flight_assist_off": {"op": "bitfield", "path": "dashboard.Flags", "bit": 5, "default": 0},
    "flag_hardpoints_deployed": {"op": "bitfield", "path": "dashboard.Flags", "bit": 6, "default": 0},
    "flag_in_wing": {"op": "bitfield", "path": "dashboard.Flags", "bit": 7, "default": 0},
    "cargo_hatch": {"op": "bitfield", "path": "dashboard.Flags", "bit": 9, "default": 0},
    "lights": {"op": "bitfield", "path": "dashboard.Flags", "bit": 8, "default": 0},
    "silent_running": {"op": "bitfield", "path": "dashboard.Flags", "bit": 10, "default": 0},
    "flight_assist": {"op": "derive", "from": ["flag_flight_assist_off"], "default": 0},  # Inverted
    
    # Ship derived states
    "heat_status": {"op": "derive", "from": ["flag_overheating", "dashboard.Temperature"], "default": 0},
    "refuel_status": {"op": "derive", "from": ["flag_scooping_fuel", "dashboard.FuelMain"], "default": 0},
    "repair_status": {"op": "derive", "from": ["dashboard.Health"], "default": 0},
    "cockpit_status": {"op": "derive", "from": ["dashboard.CanopyStatus"], "default": 0},
    "cargo_activity": {"op": "derive", "from": ["cargo_hatch", "dashboard.Cargo"], "default": 0},
    "ship_status": {"op": "derive", "from": ["legal_state"], "default": 0},
    "hardpoints": {"op": "derive", "from": ["flag_hardpoints_deployed"], "default": 0},
    "shield_state": {"op": "derive", "from": ["flag_shields_up", "dashboard.ShieldsUp"], "default": 0},
    "hull_state": {"op": "derive", "from": ["dashboard.Health"], "default": 0},
    "combat_state": {"op": "derive", "from": ["flag_in_danger", "flag_being_interdicted"], "default": 0},
    "target_state": {"op": "derive", "from": ["dashboard.Target"], "default": 0},
    "power_distribution": {"op": "derive", "from": ["pips_sys", "pips_eng", "pips_wep"], "default": 0},
    
    # SRV states - from dashboard.Flags and Flags2
    "srv_deployed_state": {"op": "derive", "from": ["flag_in_srv", "flag_srv_under_ship"], "default": 0},
    "srv_handbrake": {"op": "bitfield", "path": "dashboard.Flags", "bit": 12, "default": 0},
    "flag_srv_turret": {"op": "bitfield", "path": "dashboard.Flags", "bit": 13, "default": 0},
    "srv_under_ship": {"op": "bitfield", "path": "dashboard.Flags", "bit": 14, "default": 0},
    "srv_drive_assist": {"op": "bitfield", "path": "dashboard.Flags", "bit": 15, "default": 0},
    "srv_high_beam": {"op": "bitfield", "path": "dashboard.Flags", "bit": 31, "default": 0},
    
    # On-foot states - from dashboard.Flags2
    "flag_on_foot": {"op": "bitfield", "path": "dashboard.Flags2", "bit": 0, "default": 0},
    "flag_aim_down_sight": {"op": "bitfield", "path": "dashboard.Flags2", "bit": 3, "default": 0},
    "flag_low_oxygen": {"op": "bitfield", "path": "dashboard.Flags2", "bit": 4, "default": 0},
    "flag_low_health": {"op": "bitfield", "path": "dashboard.Flags2", "bit": 5, "default": 0},
    "temperature": {"op": "derive", "from": ["dashboard.Temperature"], "default": 0},
    "on_foot_location": {"op": "derive", "from": ["flag_on_foot", "flag_in_taxi"], "default": 0},
    "aim": {"op": "derive", "from": ["flag_aim_down_sight"], "default": 0},
    "oxygen": {"op": "derive", "from": ["dashboard.Oxygen"], "default": 0},
    "health": {"op": "derive", "from": ["dashboard.Health"], "default": 0},
    "temperature_state": {"op": "derive", "from": ["dashboard.Temperature", "oxygen"], "default": 0},
    "breathable_atmosphere": {"op": "derive", "from": ["oxygen", "dashboard.Oxygen"], "default": 0},
    
    # State-based enums
    "powerplay_pledged": {"op": "path", "path": "state.PowerplayState", "default": 0},
    "in_squadron": {"op": "path", "path": "state.Squadron", "default": 0},
    "has_fleet_carrier": {"op": "path", "path": "state.FleetCarrier", "default": 0},
    
    # Game version
    "game_version": {"op": "path", "path": "state.GameVersion", "default": 0},
    
    # Passenger states
    "has_vip_passengers": {"op": "derive", "from": ["state.Passengers"], "default": 0},
    "has_wanted_passengers": {"op": "derive", "from": ["state.Passengers"], "default": 0},
    
    # Navigation
    "has_route": {"op": "path", "path": "state.Route", "default": 0},
    "target_locked": {"op": "derive", "from": ["dashboard.Target"], "default": 0},
    "has_npc_crew": {"op": "path", "path": "state.Crew", "default": 0},
    
    # Journal event enums (recent events)
    "system_event": {"op": "journal_event", "event": "*", "category": "Location", "default": 0},
    "travel_event": {"op": "journal_event", "event": "*", "category": "Travel", "default": 0},
    "combat_event": {"op": "journal_event", "event": "*", "category": "Combat", "default": 0},
    "exploration_event": {"op": "journal_event", "event": "*", "category": "Exploration", "default": 0},
    "trading_event": {"op": "journal_event", "event": "*", "category": "Trade", "default": 0},
    "mission_event": {"op": "journal_event", "event": "*", "category": "Missions", "default": 0},
    "ship_event": {"op": "journal_event", "event": "*", "category": "Ship", "default": 0},
    "engineering_event": {"op": "journal_event", "event": "*", "category": "Engineering", "default": 0},
    "carrier_event": {"op": "journal_event", "event": "*", "category": "FleetCarrier", "default": 0},
    "onfoot_event": {"op": "journal_event", "event": "*", "category": "OnFoot", "default": 0},
    "colonisation_event": {"op": "journal_event", "event": "*", "category": "Colonisation", "default": 0},
    "comms_event": {"op": "journal_event", "event": "*", "category": "Communications", "default": 0},
    
    # Activity enums (derived from recent journal events)
    "ship_purchase_activity": {"op": "derive", "from": ["journal_events"], "category": "ShipPurchase", "default": 0},
    "module_activity": {"op": "derive", "from": ["journal_events"], "category": "Modules", "default": 0},
    "srv": {"op": "derive", "from": ["srv_deployed_state", "journal_events"], "default": 0},
    "engineering_activity": {"op": "derive", "from": ["journal_events"], "category": "Engineering", "default": 0},
    "crew_activity": {"op": "derive", "from": ["journal_events"], "category": "Crew", "default": 0},
    "suit": {"op": "derive", "from": ["journal_events", "state.Suit"], "default": 0},
    "weapon": {"op": "derive", "from": ["dashboard.SelectedWeapon", "state.Loadout"], "default": 0},
    "financial_activity": {"op": "derive", "from": ["journal_events"], "category": "Financial", "default": 0},
    "powerplay_activity": {"op": "derive", "from": ["journal_events"], "category": "Powerplay", "default": 0},
    "squadron_activity": {"op": "derive", "from": ["journal_events"], "category": "Squadron", "default": 0},
    "limpets": {"op": "derive", "from": ["dashboard.Cargo", "journal_events"], "default": 0},
    "fuel": {"op": "derive", "from": ["dashboard.FuelMain", "dashboard.FuelReservoir"], "default": 0},
    "fighter": {"op": "derive", "from": ["flag_in_fighter", "journal_events"], "default": 0},
    "transport_activity": {"op": "derive", "from": ["transport", "journal_events"], "default": 0},
    "status": {"op": "derive", "from": ["ship_status", "dashboard"], "default": 0},
}


def recover_enum_derives():
    """Recover missing derive information for all enums"""
    
    catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
    
    # Create backup
    backup_path = catalog_path.with_suffix('.json.pre-recovery-backup')
    import shutil
    shutil.copy2(catalog_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    # Load catalog
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    recovered = 0
    already_complete = 0
    not_found = []
    
    # Process each enum mapping
    for signal_key, derive_info in ENUM_DERIVE_MAPPINGS.items():
        signal_data = get_signal_data(catalog['signals'], signal_key)
        
        if signal_data:
            if 'derive' in signal_data:
                already_complete += 1
            else:
                # Add the derive information
                signal_data['derive'] = derive_info
                recovered += 1
                print(f"✅ Recovered: {signal_key} -> {derive_info.get('path', derive_info.get('op'))}")
        else:
            not_found.append(signal_key)
    
    # Save updated catalog
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("RECOVERY COMPLETE")
    print("=" * 80)
    print(f"✅ Recovered: {recovered} enum(s)")
    print(f"ℹ️  Already complete: {already_complete} enum(s)")
    if not_found:
        print(f"⚠️  Not found in catalog: {len(not_found)} enum(s)")
        for key in not_found:
            print(f"   - {key}")
    print(f"\n📁 Backup saved to: {backup_path}")
    print(f"📁 Updated catalog: {catalog_path}")


def get_signal_data(signals, signal_key):
    """Get signal data by key (handles nested keys)"""
    if '.' in signal_key:
        parts = signal_key.split('.')
        data = signals
        for part in parts:
            if part in data:
                data = data[part]
            else:
                return None
        return data
    else:
        return signals.get(signal_key)


if __name__ == '__main__':
    recover_enum_derives()
