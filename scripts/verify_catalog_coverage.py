#!/usr/bin/env python3
"""
Verify signals catalog coverage against known EDMC events.

This script checks that all common Elite Dangerous journal/CAPI events
are properly referenced in the signals catalog.
"""

from pathlib import Path
from edmcruleengine.signals_catalog import SignalsCatalog

# Known Elite Dangerous event types from official documentation
KNOWN_EVENTS = {
    # Game state
    "FileHeader", "Continued", "ClearSavedGame", "NewCommander", "LoadGame", "Commander",
    "Materials", "Cargo", "Missions", "Passengers", "Powerplay", "Progress", "Rank", "Reputation", "Statistics",
    
    # Travel & Navigation
    "Location", "FSDJump", "Docked", "Undocked", "Liftoff", "Touchdown", 
    "SupercruiseEntry", "SupercruiseExit", "ApproachBody", "LeaveBody",
    "DockingRequested", "DockingGranted", "DockingDenied", "DockingCancelled", "DockingTimeout",
    "SupercruiseDestinationDrop", "FSDTarget", "NavRoute", "StartJump", "FSDCancelWarp",
    "HyperspaceCountdown",
    
    # Combat
    "UnderAttack", "ShipTargetted", "Bounty", "PVPKill", "Died", "Interdicted", "Interdiction",
    "EscapeInterdiction", "CrimeVictim",
    
    # Damage & Repair
    "HullDamage", "ShieldState", "HeatDamage", "CockpitBreached",
    "Repair", "RepairAll", "RebootRepair", "SetUserShipName",
    
    # Refuel & Engineering
    "RefuelPartial", "RefuelAll", "Synthesis", "Engineer", "EngineerProgress", "Modification",
    
    # Exploration & Scanning
    "Scan", "FSSDiscoveryScan", "FSSSignalDiscovered", "FSSAllBodiesFound",
    "SAAScanComplete", "SAASignalsFound", "CodexEntry", "Screenshot", 
    "DiscoveryScan", "SellExplorationData",
    
    # Missions & Activities
    "MissionAccepted", "MissionCompleted", "MissionFailed", "MissionAbandoned", "MissionRedirected", "MissionWarning",
    "DatalinkScanned",
    
    # Cargo
    "CollectCargo", "EjectCargo", "CargoDepot",
    
    # Trading & Market
    "MarketBuy", "MarketSell", "EconomyData",
    
    # SRV & Vehicles
    "LaunchSRV", "DockSRV",
    
    # Crew & Passengers
    "CrewLaunchFighter", "CrewAssign", "JoinACrew", "KickCrewMember", "EndCrewSession",
    "PassengerMission", "PassengerAccepted", "PassengerCompleted",
    
    # Fleet Carrier
    "CarrierJump", "CarrierStats", "CarrierBankTransfer", "CarrierDockingPermission",
    "CarrierDecommission", "CarrierCancelDecommission", "CarrierBuy", "CarrierModulePack",
    "CarrierTradeOrder", "CarrierFinance", "CarrierShipPack", "Shipyard",
    
    # Ship Management
    "ShipyardNew", "Loadout", "Jettisonable", "JettisonCargoModule", "SetUserShipName",
    "ShipyardBuy", "ShipyardSell", "ShipyardSwap", "ModuleInfo", "ShipyardTransfer",
    
    # Engineering & Module Events
    "EngineerContribution", "UpgradeSuit", "UpgradeWeapon", "UpgradeModule",
    "Module",
    
    # Powerplay
    "PowerplayExpand", "PowerplayDefect", "PowerplayFastTrack", "PowerplayJoin", "PowerplayLeave",
    "PowerplaySalaries", "PowerplayVote",
    
    # Rank & Progression
    "PromotionFighter", "PromotionMulti", "PromotionRank",
    
    # Codex & Discovery
    "ApproachSettlement", "Rescan",
    
    # Settlement & POI
    "SettlementApproached",
    
    # Squadrons
    "SquadronCreated", "SquadronDisbanded", "SquadronCrewJoined", "SquadronCrewLeft",
    "SquadronFaction", "SquadronRank", "SquadronStatus",
    
    # Social Features
    "SocialFeatures", "Friends",
    
    # Miscellaneous
    "USSDrop", "JetConeBoost", "JetConeDamage", "SelfDestruct",
    "Resurrect", "PayBounties", "PayFines",
}

def main():
    """Verify catalog coverage."""
    print("=" * 70)
    print("EDMC Signals Catalog Coverage Verification")
    print("=" * 70)
    
    # Load catalog
    try:
        plugin_dir = Path(__file__).parent.parent
        catalog = SignalsCatalog.from_plugin_dir(str(plugin_dir))
    except Exception as e:
        print(f"[ERROR] Failed to load catalog: {e}")
        return False
    
    # Get known events from catalog
    known_in_catalog = catalog.get_all_known_events()
    
    # Check coverage
    missing_events = []
    covered_events = []
    
    print(f"\nChecking {len(KNOWN_EVENTS)} known EDMC events...")
    print(f"Catalog contains {len(known_in_catalog)} known events\n")
    
    for event in sorted(KNOWN_EVENTS):
        if event in known_in_catalog:
            covered_events.append(event)
            print(f"[OK] {event:<30} covered")
        else:
            missing_events.append(event)
            print(f"[!!] {event:<30} MISSING")
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Coverage Summary:")
    print(f"  Covered:  {len(covered_events)}/{len(KNOWN_EVENTS)} ({100*len(covered_events)/len(KNOWN_EVENTS):.1f}%)")
    print(f"  Missing:  {len(missing_events)}/{len(KNOWN_EVENTS)}")
    print("=" * 70)
    
    if missing_events:
        print(f"\n[WARNING] Missing events ({len(missing_events)}):")
        for event in sorted(missing_events):
            print(f"  - {event}")
        print("\nThese events should be added to signals_catalog.json if they occur in gameplay.")
        return False
    else:
        print("\n[SUCCESS] All known EDMC events are covered in the catalog!")
        return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
