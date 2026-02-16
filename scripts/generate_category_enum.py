"""
Generate category-based event enum definitions for signals_catalog.json Phase 4 consolidation.
Converts 178 individual event signals into 14 category-based enums.
"""

import json
from pathlib import Path

# Event categories mapping: category_name -> [(event_name, label), ...]
EVENT_CATEGORIES = {
    "travel_event": {
        "label": "Travel event",
        "category": "Travel",
        "events": [
            ("Location", "Location at startup"),
            ("FSDJump", "Jumped to new system"),
            ("Docked", "Docked at station"),
            ("Undocked", "Undocked from station"),
            ("Liftoff", "Took off from surface"),
            ("Touchdown", "Landed on surface"),
            ("SupercruiseEntry", "Entered supercruise"),
            ("SupercruiseExit", "Exited supercruise"),
            ("ApproachBody", "Approached body"),
            ("LeaveBody", "Left body orbit"),
            ("DockingRequested", "Docking requested"),
            ("DockingGranted", "Docking granted"),
            ("DockingDenied", "Docking denied"),
            ("DockingCancelled", "Docking cancelled"),
            ("DockingTimeout", "Docking timed out"),
            ("SupercruiseDestinationDrop", "Dropped at destination"),
            ("FSDTarget", "FSD target selected"),
            ("NavRoute", "Route plotted"),
            ("StartJump", "FSD charging"),
            ("JetConeBoost", "FSD boost"),
            ("USSDrop", "USS dropped at"),
            ("JetConeDamage", "Jet cone damage"),
        ]
    },
    "combat_event": {
        "label": "Combat event",
        "category": "Combat",
        "events": [
            ("Bounty", "Bounty awarded"),
            ("Died", "Ship destroyed"),
            ("Interdicted", "Was interdicted"),
            ("Interdiction", "Interdicted target"),
            ("PVPKill", "Killed player"),
            ("HullDamage", "Hull damaged"),
            ("ShieldState", "Shield state changed"),
            ("UnderAttack", "Under attack"),
            ("CapShipBond", "Capital ship reward"),
            ("FactionKillBond", "Combat zone reward"),
            ("HeatWarning", "Overheating warning"),
            ("HeatDamage", "Heat damage taken"),
            ("EscapeInterdiction", "Escaped interdiction"),
            ("ShipTargetted", "Target locked/unlocked"),
            ("CrimeVictim", "Crime victim"),
            ("Resurrect", "Resurrected"),
            ("SelfDestruct", "Self destruct"),
            ("CockpitBreached", "Cockpit breached"),
        ]
    },
    "exploration_event": {
        "label": "Exploration event",
        "category": "Exploration",
        "events": [
            ("Scan", "Body scanned"),
            ("FSSDiscoveryScan", "FSS honk performed"),
            ("FSSSignalDiscovered", "FSS signal found"),
            ("FSSAllBodiesFound", "All bodies discovered"),
            ("SAAScanComplete", "SAA scan complete"),
            ("SAASignalsFound", "SAA signals found"),
            ("CodexEntry", "Codex entry added"),
            ("Screenshot", "Screenshot taken"),
            ("SellExplorationData", "Sold exploration data"),
            ("DiscoveryScan", "Discovery scanner used"),
            ("NavBeaconScan", "Nav beacon scanned"),
            ("ScanBaryCentre", "Barycentre scanned"),
            ("MaterialDiscarded", "Material discarded"),
            ("MaterialDiscovered", "New material found"),
            ("BuyExplorationData", "Bought system data"),
            ("MultiSellExplorationData", "Sold multiple systems"),
            ("SellOrganicData", "Sold organic scan data"),
        ]
    },
    "trading_event": {
        "label": "Trading event",
        "category": "Trading",
        "events": [
            ("MarketBuy", "Bought commodity"),
            ("MarketSell", "Sold commodity"),
            ("CollectCargo", "Cargo collected"),
            ("EjectCargo", "Cargo ejected"),
            ("MiningRefined", "Material refined"),
            ("CargoDepot", "Wing mission cargo"),
            ("SearchAndRescue", "S&R delivery"),
            ("BuyTradeData", "Trade data purchased"),
            ("AsteroidCracked", "Motherlode cracked"),
            ("Market", "Market accessed"),
        ]
    },
    "mission_event": {
        "label": "Mission event",
        "category": "Missions",
        "events": [
            ("MissionAccepted", "Mission accepted"),
            ("MissionCompleted", "Mission completed"),
            ("MissionFailed", "Mission failed"),
            ("MissionAbandoned", "Mission abandoned"),
            ("CommunityGoal", "CG update"),
            ("MissionRedirected", "Mission redirected"),
            ("CommunityGoalJoin", "Joined community goal"),
            ("CommunityGoalDiscard", "Abandoned CG"),
            ("CommunityGoalReward", "CG reward received"),
        ]
    },
    "ship_event": {
        "label": "Ship event",
        "category": "Ship",
        "events": [
            ("ShipyardBuy", "Ship purchased"),
            ("ShipyardSell", "Ship sold"),
            ("ShipyardSwap", "Ship swapped"),
            ("Loadout", "Loadout changed"),
            ("ModuleBuy", "Module purchased"),
            ("ModuleSell", "Module sold"),
            ("ModuleSwap", "Module swapped"),
            ("RepairAll", "Full repair"),
            ("BuyAmmo", "Ammunition purchased"),
            ("RefuelPartial", "Partial refuel"),
            ("Repair", "Module repaired"),
            ("RestockVehicle", "SRV/Fighter restocked"),
            ("ModuleStore", "Module stored"),
            ("ModuleRetrieve", "Module retrieved"),
            ("ModuleSellRemote", "Remote module sold"),
            ("FetchRemoteModule", "Remote transfer"),
            ("MassModuleStore", "Multiple modules stored"),
            ("Outfitting", "Outfitting accessed"),
            ("Shipyard", "Shipyard accessed"),
            ("ShipyardTransfer", "Ship transfer"),
            ("SetUserShipName", "Ship renamed"),
            ("SellShipOnRebuy", "Ship sold for rebuy"),
            ("VehicleSwitch", "Switched vehicle"),
            ("SystemsShutdown", "Systems shut down"),
            ("AfmuRepairs", "AFMU repairing"),
            ("Shutdown", "Ship shutdown"),
            ("RebootRepair", "Emergency reboot"),
        ]
    },
    "engineering_event": {
        "label": "Engineering event",
        "category": "Engineering",
        "events": [
            ("EngineerCraft", "Module engineered"),
            ("EngineerProgress", "Engineer progress"),
            ("MaterialCollected", "Material collected"),
            ("MaterialTrade", "Materials traded"),
            ("Synthesis", "Synthesis crafted"),
            ("EngineerContribution", "Contribution to engineer"),
            ("EngineerLegacyConvert", "Legacy module converted"),
            ("TechnologyBroker", "Tech unlocked"),
            ("ScientificResearch", "Research contribution"),
        ]
    },
    "carrier_event": {
        "label": "Fleet Carrier event",
        "category": "Fleet Carrier",
        "events": [
            ("CarrierJump", "Carrier jumped"),
            ("CarrierBuy", "Carrier purchased"),
            ("CarrierStats", "Carrier stats updated"),
            ("CarrierJumpRequest", "Jump requested"),
            ("CarrierJumpCancelled", "Jump cancelled"),
            ("CarrierFinance", "Carrier finances"),
            ("CarrierBankTransfer", "Bank transfer"),
            ("CarrierDepositFuel", "Fuel deposited"),
            ("CarrierCrewServices", "Crew services"),
            ("CarrierTradeOrder", "Trade order"),
            ("CarrierDockingPermission", "Docking permissions"),
            ("CarrierNameChange", "Carrier renamed"),
            ("CarrierModulePack", "Module pack"),
            ("CarrierDecommission", "Carrier decommissioned"),
            ("CarrierCancelDecommission", "Decommission cancelled"),
            ("CarrierTransfer", "Carrier cargo transfer"),
        ]
   },
    "onfoot_event": {
        "label": "On-Foot event",
        "category": "On-Foot",
        "events": [
            ("Disembark", "Disembarked"),
            ("Embark", "Embarked"),
            ("ScanOrganic", "Organic scanned"),
            ("CommanderInTaxi", "In taxi"),
            ("Backpack", "Backpack contents"),
            ("BackpackChange", "Backpack changed"),
            ("DropShipDeploy", "Dropship deployed"),
            ("SuitLoadout", "Suit loadout"),
            ("CreateSuitLoadout", "Created suit loadout"),
            ("DeleteSuitLoadout", "Deleted suit loadout"),
            ("LoadoutEquipModule", "Equipped suit module"),
            ("SwitchSuitLoadout", "Switched suit loadout"),
            ("ApproachSettlement", "Approached settlement"),
            ("TradeMicroResources", "Traded micro resources"),
            ("FCMaterials", "FC materials"),
            ("UseConsumable", "Used consumable"),
            ("CollectItems", "Items collected"),
            ("DropItems", "Items dropped"),
            ("TransferMicroResources", "Transferred micro resources"),
            ("ShipLocker", "Ship locker"),
            ("DataScanned", "Data scanned"),
            ("DatalinkScan", "Datalink scanned"),
            ("DatalinkVoucher", "Datalink voucher"),
        ]
    },
    "colonisation_event": {
        "label": "Colonisation event",
        "category": "Colonisation",
        "events": [
            ("ColonisationConstructionDepot", "Construction depot"),
            ("ColonisationContribution", "Contribution made"),
        ]
    },
    "comms_event": {
        "label": "Communications event",
        "category": "Comms",
        "events": [
            ("ReceiveText", "Received text"),
            ("SendText", "Sent text"),
            ("Music", "Music changed"),
        ]
    },
    "progress_event": {
        "label": "Progress event",
        "category": "Progress",
        "events": [
            ("Promotion", "Rank promotion"),
        ]
    },
    "misc_event": {
        "label": "Miscellaneous event",
        "category": "Misc",
        "events": [
            ("Friends", "Friends list"),
        ]
    }
}


def snake_to_value(name):
    """Convert PascalCase event name to snake_case enum value."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append('_')
        result.append(char.lower())
    return ''.join(result)


def generate_enum_definition(enum_id, data):
    """Generate a complete enum signal definition."""
    values = [{"value": "none", "label": "None"}]
    cases = []
    
    for event_name, label in data["events"]:
        value_id = snake_to_value(event_name)
        values.append({
            "value": value_id,
            "label": label,
            "recent_event": event_name
        })
        cases.append({
            "when": {
                "op": "recent",
                "event_name": event_name,
                "within_seconds": 300
            },
            "value": value_id
        })
    
    return {
        "type": "enum",
        "title": data["label"].title(),
        "ui": {
            "label": data["label"],
            "category": data["category"],
            "tier": "core"
        },
        "values": values,
        "derive": {
            "op": "first_match",
            "cases": cases,
            "default": "none"
        }
    }


def main():
    """Generate all category enum definitions and print as JSON."""
    enums = {}
    for enum_id, data in EVENT_CATEGORIES.items():
        enums[enum_id] = generate_enum_definition(enum_id, data)
    
    # Print formatted JSON
    print(json.dumps(enums, indent=2))
    
    print("\n\n=== SUMMARY ===", file=__import__('sys').stderr)
    total_events = sum(len(data["events"]) for data in EVENT_CATEGORIES.values())
    print(f"Generated {len(enums)} category enums", file=__import__('sys').stderr)
    print(f"Covering {total_events} event types", file=__import__('sys').stderr)
    for enum_id, data in EVENT_CATEGORIES.items():
        print(f"  - {enum_id}: {len(data['events'])} events", file=__import__('sys').stderr)


if __name__ == "__main__":
    main()
