#!/usr/bin/env python3
"""
COMPREHENSIVE Enum Derive Recovery - Restores missing source event information
Based on EDMC architecture and Elite Dangerous game mechanics
"""

import json
from pathlib import Path
import shutil


# Complete mapping of all 91 missing enum signals to their correct derive paths
ENUM_DERIVE_MAPPINGS = {
    # === HUD ENUMS ===
    "hud_mode": {
        "op": "map",
        "from": {"op": "path", "path": "dashboard.HudMode", "default": 0},
        "map": {"0": "Combat", "1": "Analysis"},
        "default": "Combat"
    },
    "night_vision": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 28, "default": 0},
        "map": {"0": "Off", "1": "On"},
        "default": "Off"
    },
    
    # === COMMANDER ENUMS ===
    "transport": {
        "op": "map",
        "from": {"op": "derive", "from": ["vehicle_type", "on_foot_state"], "default": 0},
        "map": {"0": "Ship", "1": "SRV", "2": "Fighter", "3":  "OnFoot", "4": "Taxi", "5": "Multicrew", "6": "Apex"},
        "default": "Ship"
    },
    
    # Commander Ranks (missing ones)
    "commander_ranks.empire": {
        "op": "map",
        "from": {"op": "path", "path": "state.Rank.Empire", "default": 0},
        "map": {str(i): rank for i, rank in enumerate([
            "None", "Outsider", "Serf", "Master", "Squire", "Knight",
            "Lord", "Baron", "Viscount", "Count", "Earl", "Marquis",
            "Duke", "Prince", "King"
        ])},
        "default": "None"
    },
    "commander_ranks.federation": {
        "op": "map",
        "from": {"op": "path", "path": "state.Rank.Federation", "default": 0},
        "map": {str(i): rank for i, rank in enumerate([
            "None", "Recruit", "Cadet", "Midshipman", "Petty Officer", "Chief Petty Officer",
            "Warrant Officer", "Ensign", "Lieutenant", "Lieutenant Commander", "Post Commander",
            "Post Captain", "Rear Admiral", "Vice Admiral", "Admiral"
        ])},
        "default": "None"
    },
    
    # Commander Promotions (derived from rank progress reaching 100%)
    **{f"commander_promotion.{rank_type}": {
        "op": "map",
        "from": {"op": "journal_event", "event": "Promotion", "field": rank_type.capitalize(), "default": 0},
        "map": {"0": "None", "1": "Promoted"},
        "default": "None"
    } for rank_type in ["combat", "trade", "explore", "empire", "federation", "cqc", "soldier", "exobiologist", "mercenary"]},
    
    # === SHIP & DOCKING ===
    "docking_state": {
        "op": "map",
        "from": {"op": "derive", "from": ["flag_docked", "flag_landed", "landing_gear"], "default": 0},
        "map": {"0": "NotDocked", "1": "Docked", "2": "Landed", "3": "Docking", "4": "Landing", "5": "Departing", "6": "Takeoff"},
        "default": "NotDocked"
    },
    "has_lat_long": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 21, "default": 0},
        "map": {"0": "No", "1": "Yes"},
        "default": "No"
    },
    "docking_request_state": {
        "op": "map",
        "from": {"op": "derive", "from": ["journal_events"], "default": 0},
        "map": {"0": "None", "1": "Requesting", "2": "Granted", "3": "Denied", "4": "Cancelled", "5": "Timeout"},
        "default": "None"
    },
    
    # === LOCATION & PROXIMITY ===
    "body_proximity": {
        "op": "map",
        "from": {"op": "derive", "from": ["dashboard.Flags", "dashboard.BodyName"], "default": 0},
        "map": {"0": "None", "1": "Near", "2": "Orbit", "3": "Surface"},
        "default": "None"
    },
    
    # === TRAVEL & FSD ===
    "supercruise_state": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 4, "default": 0},
        "map": {"0": "NormalSpace", "1": "Supercruise", "2": "Entering", "3": "Exiting"},
        "default": "NormalSpace"
    },
    "fsd_state": {
        "op": "map",
        "from": {"op": "derive", "from": ["dashboard.Flags"], "default": 0},
        "map": {"0": "Ready", "1": "Charging", "2": "Cooldown", "3": "Jumping", "4": "MassLocked", "5": "Disabled"},
        "default": "Ready"
    },
    "jump_type": {
        "op": "map",
        "from": {"op": "journal_event", "event": "FSDJump", "field": "JumpType", "default": 0},
        "map": {"0": "None", "1": "Hyperspace", "2": "Supercruise"},
        "default": "None"
    },
    "mass_locked": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 16, "default": 0},
        "map": {"0": "No", "1": "Yes"},
        "default": "No"
    },
    "flag_in_danger": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 22, "default": 0},
        "map": {"0": "Safe", "1": "Danger"},
        "default": "Safe"
    },
    "flag_hud_analysis_mode": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 27, "default": 0},
        "map": {"0": "Combat", "1": "Analysis"},
        "default": "Combat"
    },
    "flag_altitude_from_avg_radius": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 29, "default": 0},
        "map": {"0": "Center", "1": "Surface"},
        "default": "Center"
    },
    "jet_cone_boost_state": {
        "op": "map",
        "from": {"op": "derive", "from": ["flag_scooping_fuel", "dashboard.FuelMain"], "default": 0},
        "map": {"0": "None", "1": "Boosting", "2": "Boosted"},
        "default": "None"
    },
    
    # === SHIP FLAG STATES ===
    **{flag_name: {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": bit_num, "default": 0},
        "map": {"0": "Off", "1": "On"} if flag_name not in ["landing_gear", "cargo_hatch"] else {"0": "Closed", "1": "Open"},
        "default": "Off" if flag_name not in ["landing_gear", "cargo_hatch"] else "Closed"
    } for flag_name, bit_num in [
        ("landing_gear", 2), ("flag_shields_up", 3), ("flag_flight_assist_off", 5),
        ("flag_hardpoints_deployed", 6), ("flag_in_wing", 7), ("cargo_hatch", 9),
        ("lights", 8), ("silent_running", 10)
    ]},
    
    # Special cases
    "flight_assist": {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": 5, "default": 0},
        "map": {"0": "On", "1": "Off"},  # Inverted
        "default": "On"
    },
    
    # === SHIP DERIVED STATES ===
    **{state_name: {
        "op": "map",
        "from": {"op": "derive", "from": [derive_from], "default": 0},
        "map": state_map,
        "default": list(state_map.values())[0]
    } for state_name, derive_from, state_map in [
        ("heat_status", "dashboard.Temperature", {"0": "Normal", "1": "Warm", "2": "Hot"}),
        ("refuel_status", "dashboard.FuelMain", {"0": "Normal", "1": "Scooping", "2": "Full"}),
        ("repair_status", "dashboard.Health", {"0": "Undamaged", "1": "MinorDamage", "2": "MajorDamage", "3": "Critical", "4": "Destroyed", "5": "Repairing", "6": "Repaired"}),
        ("cockpit_status", "dashboard.CanopyHealth", {"0": "Intact", "1": "Breached"}),
        ("cargo_activity", "dashboard.Cargo", {"0": "None", "1": "Loading", "2": "Unloading"}),
        ("ship_status", "dashboard.LegalState", {"0": "Clean", "1": "Wanted"}),
        ("hardpoints", "dashboard.Flags", {"0": "Retracted", "1": "Deployed"}),
        ("shield_state", "dashboard.ShieldsUp", {"0": "Down", "1": "Up", "2": "Recharging", "3": "Offline"}),
        ("hull_state", "dashboard.Health", {"0": "Intact", "1": "Damaged", "2": "Critical", "3": "Destroyed"}),
        ("combat_state", "dashboard.Flags", {"0": "Safe", "1": "Combat", "2": "Danger", "3": "BeingInterdicted"}),
        ("target_state", "dashboard.Target", {"0": "None", "1": "Locked", "2": "Lost"}),
        ("power_distribution", "dashboard.Pips", {"0": "Balanced", "1": "Sys", "2": "Eng", "3": "Wep", "4": "Custom"}),
    ]},
    
    # === SRV STATES ===
    **{srv_state: {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags", "bit": bit_num, "default": 0},
        "map": srv_map,
        "default": list(srv_map.values())[0]
    } for srv_state, bit_num, srv_map in [
        ("srv_deployed_state", 26, {"0": "NotDeployed", "1": "Deployed", "2": "Deploying", "3": "Recalling"}),
        ("srv_handbrake", 12, {"0": "Off", "1": "On"}),
        ("flag_srv_turret", 13, {"0": "Fixed", "1": "Turret"}),
        ("srv_under_ship", 14, {"0": "No", "1": "Yes"}),
        ("srv_drive_assist", 15, {"0": "Off", "1": "On"}),
        ("srv_high_beam", 31, {"0": "Off", "1": "On"}),
    ]},
    
    # === ON-FOOT STATES ===
    **{onfoot_state: {
        "op": "map",
        "from": {"op": "bitfield", "path": "dashboard.Flags2", "bit": bit_num, "default": 0},
        "map": {"0": "No", "1": "Yes"},
        "default": "No"
    } for onfoot_state, bit_num in [
        ("flag_on_foot", 0), ("flag_aim_down_sight", 3),
        ("flag_low_oxygen", 4), ("flag_low_health", 5),
    ]},
    
    # On-foot derived states
    **{state_name: {
        "op": "map",
        "from": {"op": "derive", "from": [derive_from], "default": 0},
        "map": state_map,
        "default": list(state_map.values())[0]
    } for state_name, derive_from, state_map in [
        ("temperature", "dashboard.Temperature", {"0": "Normal", "1": "Cold", "2": "VeryCold", "3": "Hot", "4": "VeryHot"}),
        ("on_foot_location", "dashboard.Flags2", {"0": "Ship", "1": "Exterior", "2": "Settlement", "3": "Station", "4": "POI", "5": "SocialSpace"}),
        ("aim", "dashboard.Flags2", {"0": "Hipfire", "1": "ADS"}),
        ("oxygen", "dashboard.Oxygen", {"0": "Normal", "1": "Low"}),
        ("health", "dashboard.Health", {"0": "Healthy", "1": "Injured"}),
        ("temperature_state", "dashboard.Temperature", {"0": "Normal", "1": "Cold", "2": "VeryCold", "3": "Hot", "4": "VeryHot"}),
        ("breathable_atmosphere", "dashboard.Oxygen", {"0": "No", "1": "Yes"}),
    ]},
    
    # === STATE-BASED ENUMS ===
    **{state_enum: {
        "op": "map",
        "from": {"op": "path", "path": state_path, "default": 0},
        "map": {"0": "No", "1": "Yes"},
        "default": "No"
    } for state_enum, state_path in [
        ("powerplay_pledged", "state.PowerplayState"),
        ("in_squadron", "state.Squadron"),
        ("has_fleet_carrier", "state.FleetCarrier"),
        ("has_npc_crew", "state.Crew"),
        ("has_route", "state.Route"),
    ]},
    
    # Game version
    "game_version": {
        "op": "map",
        "from": {"op": "path", "path": "state.GameVersion", "default": 0},
        "map": {"0": "Unknown", "1": "Horizons", "2": "Odyssey"},
        "default": "Unknown"
    },
    
    # Passengers
    **{passenger_state: {
        "op": "map",
        "from": {"op": "derive", "from": ["state.Passengers"], "default": 0},
        "map": {"0": "No", "1": "Yes"},
        "default": "No"
    } for passenger_state in ["has_vip_passengers", "has_wanted_passengers"]},
    
    # Target
    "target_locked": {
        "op": "map",
        "from": {"op": "derive", "from": ["dashboard.Target"], "default": 0},
        "map": {"0": "No", "1": "Yes"},
        "default": "No"
    },
    
    # === JOURNAL EVENT ENUMS (Recent events by category) ===
    **{event_enum: {
        "op": "map",
        "from": {"op": "journal_event", "event": "*", "category": category, "default": 0},
        "map": {str(i): event for i, event in enumerate(events)},
        "default": events[0]
    } for event_enum, category, events in [
        ("system_event", "Location", ["None", "FSDJump", "Location", "Docked", "Undocked", "Touchdown", "Liftoff", "ApproachBody", "LeaveBody", "ApproachSettlement", "DockingGranted", "DockingDenied", "DockingCancelled", "DockingTimeout", "Embark", "Disembark", "CommanderStats", "SupercruiseEntry", "SupercruiseExit", "StartJump"]),
        ("travel_event", "Travel", ["None", "FSDJump", "StartJump", "SupercruiseEntry", "SupercruiseExit", "FSDTarget", "NavRoute", "NavRouteClear", "Undocked", "Liftoff", "ApproachBody", "LeaveBody", "Touchdown", "Docked", "DockingGranted", "DockingDenied", "DockingCancelled", "DockingTimeout", "Hop", "Embark", "Disembark", "ApexInteraction", "DropshipDeploy"]),
        ("combat_event", "Combat", ["None", "Interdicted", "Interdiction", "EscapeInterdiction", "HeatWarning", "HullDamage", "ShieldState", "UnderAttack", "FighterDestroyed", "Died", "PVPKill", "Resurrect"]),
        ("exploration_event", "Exploration", ["None", "FSSDiscoveryScan", "FSSAllBodiesFound", "FSSBodySignals", "FSSSignalDiscovered", "ScanOrganic", "SAASignalsFound", "SAAScanComplete", "Scan", "Screenshot", "CodexEntry", "DiscoveryScan", "MultiSellExplorationData", "SellExplorationData", "FirstFootFall", "NavBeacon", "NavBeaconDetail", "SurfaceScan", "MaterialDiscovered", "MaterialCollected"]),
        ("trading_event", "Trade", ["None", "MarketBuy", "MarketSell", "Market", "CommodityPricesUpdate", "EjectCargo", "CollectCargo", "MiningRefined"]),
        ("mission_event", "Missions", ["None", "MissionAccepted", "MissionCompleted", "MissionAbandoned", "MissionFailed", "MissionRedirected", "Missions", "Cargo", "CargoTransfer", "SearchAndRescue"]),
        ("ship_event", "Ship", ["None", "Loadout", "LoadGame", "ModuleBuy", "ModuleSell", "ModuleStore", "ModuleRetrieve", "ModuleSwap", "MassModuleStore", "ShipyardBuy", "ShipyardSell", "ShipyardTransfer", "ShipyardSwap", "SellShipOnRebuy", "ShipLocker", "RepairAll", "RefuelAll", "RepairDrone", "Repair", "Refuel", "AfmuRepairs", "LaunchSRV", "DockSRV", "LaunchFighter", "DockFighter", "VehicleSwitch", "SetUserShipName", "ShipName"]),
        ("engineering_event", "Engineering", ["None", "EngineerProgress", "EngineerCraft", "EngineerContribution", "EngineerApply", "FetchRemoteModule", "MaterialTrade", "MaterialCollected", "TechnologyBroker", "ScientificResearch", "Synthesis"]),
        ("carrier_event", "FleetCarrier", ["None", "CarrierJump", "CarrierJumpRequest", "CarrierJumpCancelled", "CarrierStats", "CarrierTradeOrder", "CarrierFinance", "CarrierBankTransfer", "CarrierDepositFuel", "CarrierCrewServices", "CarrierModulePack", "CarrierBuy", "CarrierNameChanged", "CarrierShipPack", "CarrierDockingPermission", "CarrierDecommission", "FCMaterials"]),
        ("onfoot_event", "OnFoot", ["None", "Disembark", "Embark", "BackpackChange", "BackpackMaterials", "BookTaxi", "TaxiDestination", "CancelTaxi", "BuyWeapon", "BuySuit", "UpgradeWeapon", "UpgradeSuit", "SwitchSuitLoadout", "CreateSuitLoadout", "DeleteSuitLoadout", "RenameSuitLoadout", "SwitchWeaponLoadout", "BuyMicroResources", "SellMicroResources", "TradeMicroResources", "TransferMicroResources", "ShipLockerMaterials", "FCMaterials"]),
        ("colonisation_event", "Colonisation", ["None", "DonateOrganicData", "ColonisationProgress"]),
        ("comms_event", "Communications", ["None", "SendText", "ReceiveText", "FriendsStatus", "CrewMemberJoins"]),
    ]},
    
    # === ACTIVITY ENUMS (Derived from recent actions) ===
    **{activity_enum: {
        "op": "map",
        "from": {"op": "derive", "from": ["journal_events"], "default": 0},
        "map": {str(i): activity for i, activity in enumerate(activities)},
        "default": activities[0]
    } for activity_enum, activities in [
        ("ship_purchase_activity", ["None", "Viewing", "Buying", "Selling", "Transferring", "Swapping"]),
        ("module_activity", ["None", "Viewing", "Buying", "Selling", "Storing", "Retrieving", "Swapping"]),
        ("srv", ["None", "Stowed", "Deploying", "Deployed", "Recalling"]),
        ("engineering_activity", ["None", "Viewing", "Crafting", "Applying", "Trading", "Contributing"]),
        ("crew_activity", ["None", "Firing", "Hiring", "JoinedBy", "LeftBy", "LaunchedFighter", "DockedFighter", "FighterDestroyed", "FighterRebuilt", "KickCrew", "CrewMemberJoins", "CrewAssign", "CrewUnassign", "NpcCrewPaidWage", "NpcCrewRank"]),
        ("suit", ["None", "FlightSuit", "TacticalSuit", "ExplorationSuit", "DominatorSuit"]),
        ("weapon", ["None", "Kinetic", "Laser", "Plasma", "Explosive"]),
        ("financial_activity", ["None", "Bounty", "Bond", "CapShipBond", "CrimeFine", "FactionKillBond", "PayFines", "PayLegacyFines", "RedeemVoucher", "RefuelAll", "Repair", "RepairAll", "SellDrones", "RestockVehicle", "MarketBuy", "MarketSell", "MultiSellExplorationData", "SellExplorationData", "MissionCompleted", "MissionFailed"]),
        ("powerplay_activity", ["None", "Pledged", "Defected", "PowerplayCollect", "PowerplayDeliver", "PowerplayFastTrack", "PowerplayJoin", "PowerplayLeave", "PowerplaySalary", "PowerplayVote"]),
        ("squadron_activity", ["None", "AppliedToSquadron", "DisbandedSquadron", "InvitedToSquadron", "JoinedSquadron", "KickedFromSquadron", "LeftSquadron", "SharedBookmarkToSquadron", "SquadronCreated", "SquadronDemotion", "SquadronPromotion", "SquadronStartup", "WonATrophyForSquadron"]),
        ("limpets", ["None", "Collector", "Prospector", "FuelTransfer", "Recon"]),
        ("fuel", ["None", "Full", "High", "Medium", "Low", "VeryLow", "Critical", "Empty", "Scooping"]),
        ("fighter", ["None", "Stowed", "Launching", "Deployed", "Docking", "Destroyed"]),
        ("transport_activity", ["None", "Walking", "Running", "Jetpack", "Elevator", "Taxi"]),
        ("status", ["None", "Ok", "UnderAttack", "Danger", "Critical"]),
    ]},
}


def apply_derives():
    """Apply all derive mappings to the catalog"""
    
    catalog_path = Path(__file__).parent.parent / "signals_catalog.json"
    
    # Create backup
    backup_path = catalog_path.with_suffix('.json.derive-recovery-backup')
    shutil.copy2(catalog_path, backup_path)
    print(f"Created backup: {backup_path}\n")
    
    # Load catalog
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    applied = 0
    skipped = 0
    not_found = []
    
    # Apply each mapping
    for signal_key, derive_info in ENUM_DERIVE_MAPPINGS.items():
        signal_data = get_signal_data(catalog['signals'], signal_key)
        
        if signal_data:
            if 'derive' in signal_data:
                skipped += 1
                print(f"[SKIP] {signal_key} - already has derive")
            else:
                signal_data['derive'] = derive_info
                applied += 1
                print(f"[OK] {signal_key}")
        else:
            not_found.append(signal_key)
            print(f"[NOT FOUND] {signal_key}")
    
    # Save
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print("RECOVERY COMPLETE")
    print(f"{'=' * 80}")
    print(f"Applied: {applied}")
    print(f"Skipped (already complete): {skipped}")
    print(f"Not found: {len(not_found)}")
    if not_found:
        print(f"\nSignals not found:")
        for key in not_found:
            print(f"  - {key}")
    print(f"\nBackup: {backup_path}")
    print(f"Catalog: {catalog_path}")


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
    apply_derives()
