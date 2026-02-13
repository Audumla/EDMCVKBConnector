# EDMCVKBConnector Rules Schema

This document describes the current rule format implemented in `src/edmcruleengine/rules_engine.py`.

## Rule Object

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | no | Auto-generated if missing. |
| `enabled` | bool | no | Defaults to `true`. |
| `when` | object | no | Match conditions and filters. |
| `then` | object | no | Actions when rule matches. |
| `else` | object | no | Actions when rule does not match. |

Example:

```json
{
  "id": "example",
  "enabled": true,
  "when": {},
  "then": {},
  "else": {}
}
```

## Rules File Shapes

| Shape | Example |
|---|---|
| Top-level array | `[{"id":"rule-1","enabled":true,"when":{},"then":{}}]` |
| Wrapped object | `{"rules":[{"id":"rule-1","enabled":true,"when":{},"then":{}}]}` |

## `when` Object

| Field | Type | Required | Notes |
|---|---|---|---|
| `source` | string or string[] | no | `journal`, `dashboard`, `capi`, `capi_fleetcarrier`, `any`. |
| `event` | string or string[] | no | Event name filter. |
| `all` | object[] | no | Every block must match. |
| `any` | object[] | no | At least one block must match. |

### Source Matching

| `source` value | Behavior |
|---|---|
| omitted | No source filter. |
| `"any"` | No source filter. |
| `"journal"` (or other string) | Match only that source. |
| `["journal","dashboard"]` | Match any listed source. |

### Event Matching

| Rule | Behavior |
|---|---|
| `event` omitted | No event filter. |
| `event` string | Exact string match. |
| `event` array | Exact match against any listed value. |

Important:
- Event names are plain string matches.
- The plugin does not enforce a hard allow-list for journal event names.
- If EDMC supplies an event name, you can match it.

## Condition Blocks

Each object in `when.all` / `when.any` must be exactly one of:

| Block | Purpose |
|---|---|
| `{ "flags": { ... } }` | Match `Flags` bit values by symbolic names. |
| `{ "flags2": { ... } }` | Match `Flags2` bit values by symbolic names. |
| `{ "gui_focus": { ... } }` | Match `GuiFocus` by name or int. |
| `{ "field": { ... } }` | Match arbitrary entry fields by dot-path. |

### `flags` and `flags2` Operators

| Operator | Type | Meaning |
|---|---|---|
| `all_of` | string[] | All listed flags are `true`. |
| `any_of` | string[] | At least one listed flag is `true`. |
| `none_of` | string[] | All listed flags are `false`. |
| `equals` | object | Exact boolean by flag name, e.g. `{ "FlagsLandingGearDown": true }`. |
| `changed_to_true` | string[] | Transition false -> true (requires previous state). |
| `changed_to_false` | string[] | Transition true -> false (requires previous state). |

### `gui_focus` Operators

| Operator | Type | Meaning |
|---|---|---|
| `equals` | string or int | Exact current focus. |
| `in` | (string or int)[] | Current focus is any listed value. |
| `changed_to` | string or int | Transition to target focus (requires previous state). |

### `field` Operators

| Operator | Type | Meaning |
|---|---|---|
| `name` | string | Required dot-path field name, e.g. `commander.name`. |
| `exists` | bool | Whether field must exist. |
| `equals` | any | Exact equality. |
| `in` | any[] | Value must be in list. |
| `not_in` | any[] | Value must not be in list. |
| `contains` | any | Membership for string/list/tuple/set or dict key presence. |
| `gt` | number | Greater than. |
| `gte` | number | Greater than or equal. |
| `lt` | number | Less than. |
| `lte` | number | Less than or equal. |
| `changed` | bool | Whether value changed from previous entry. |
| `changed_to` | any | Changed to this value from a different value. |

## Actions (`then` / `else`)

| Action key | Type | Meaning |
|---|---|---|
| `vkb_set_shift` | string[] | Set shift/subshift tokens. |
| `vkb_clear_shift` | string[] | Clear shift/subshift tokens. |
| `log` | string | Emit info log line. |

### Shift Token Format

| Token | Range | Bit mapping |
|---|---|---|
| `ShiftN` | `N = 1..2` | `Shift1 -> bit0`, `Shift2 -> bit1` |
| `SubshiftN` | `N = 1..7` | `Subshift1 -> bit0` ... `Subshift7 -> bit6` |

## Dashboard Value Sources

| Rule block | Source field |
|---|---|
| `flags` | Dashboard `Flags` |
| `flags2` | Dashboard `Flags2` |
| `gui_focus` | Dashboard `GuiFocus` |

Use symbolic names, e.g. `FlagsHardpointsDeployed` and `FlagsAnalysisMode`.

## Supported `Flags`

| Name | Bit |
|---|---|
| `FlagsDocked` | 0 |
| `FlagsLanded` | 1 |
| `FlagsLandingGearDown` | 2 |
| `FlagsShieldsUp` | 3 |
| `FlagsSupercruise` | 4 |
| `FlagsFlightAssistOff` | 5 |
| `FlagsHardpointsDeployed` | 6 |
| `FlagsInWing` | 7 |
| `FlagsLightsOn` | 8 |
| `FlagsCargoScoopDeployed` | 9 |
| `FlagsSilentRunning` | 10 |
| `FlagsScoopingFuel` | 11 |
| `FlagsSrvHandbrake` | 12 |
| `FlagsSrvTurret` | 13 |
| `FlagsSrvUnderShip` | 14 |
| `FlagsSrvDriveAssist` | 15 |
| `FlagsFsdMassLocked` | 16 |
| `FlagsFsdCharging` | 17 |
| `FlagsFsdCooldown` | 18 |
| `FlagsLowFuel` | 19 |
| `FlagsOverHeating` | 20 |
| `FlagsHasLatLong` | 21 |
| `FlagsIsInDanger` | 22 |
| `FlagsBeingInterdicted` | 23 |
| `FlagsInMainShip` | 24 |
| `FlagsInFighter` | 25 |
| `FlagsInSRV` | 26 |
| `FlagsAnalysisMode` | 27 |
| `FlagsNightVision` | 28 |
| `FlagsAverageAltitude` | 29 |
| `FlagsFsdJump` | 30 |
| `FlagsSrvHighBeam` | 31 |

## Supported `Flags2`

| Name | Bit |
|---|---|
| `Flags2OnFoot` | 0 |
| `Flags2InTaxi` | 1 |
| `Flags2InMulticrew` | 2 |
| `Flags2OnFootInStation` | 3 |
| `Flags2OnFootOnPlanet` | 4 |
| `Flags2AimDownSight` | 5 |
| `Flags2LowOxygen` | 6 |
| `Flags2LowHealth` | 7 |
| `Flags2Cold` | 8 |
| `Flags2Hot` | 9 |
| `Flags2VeryCold` | 10 |
| `Flags2VeryHot` | 11 |
| `Flags2GlideMode` | 12 |
| `Flags2OnFootInHangar` | 13 |
| `Flags2OnFootSocialSpace` | 14 |
| `Flags2OnFootExterior` | 15 |
| `Flags2BreathableAtmosphere` | 16 |

## Supported `GuiFocus`

| Name | Value |
|---|---|
| `GuiFocusNoFocus` | 0 |
| `GuiFocusInternalPanel` | 1 |
| `GuiFocusExternalPanel` | 2 |
| `GuiFocusCommsPanel` | 3 |
| `GuiFocusRolePanel` | 4 |
| `GuiFocusStationServices` | 5 |
| `GuiFocusGalaxyMap` | 6 |
| `GuiFocusSystemMap` | 7 |
| `GuiFocusOrrery` | 8 |
| `GuiFocusFSS` | 9 |
| `GuiFocusSAA` | 10 |
| `GuiFocusCodex` | 11 |

## Journal Event Reference (Expanded)

The plugin does not hard-limit journal event names, but these are common and useful.

| Category | Example event names |
|---|---|
| Session/Commander | `Fileheader`, `Commander`, `LoadGame`, `NewCommander`, `Music`, `Statistics`, `Progress`, `Promotion` |
| Travel/Docking | `Location`, `StartJump`, `FSDJump`, `SupercruiseEntry`, `SupercruiseExit`, `DockingGranted`, `Docked`, `Undocked`, `Interdicted`, `Touchdown`, `Liftoff` |
| Ship/SRV/Fighter | `Loadout`, `VehicleSwitch`, `LaunchSRV`, `DockSRV`, `LaunchFighter`, `DockFighter`, `FuelScoop`, `Synthesis` |
| Combat/Security | `Bounty`, `CombatBond`, `FactionKillBond`, `HullDamage`, `ShieldState`, `PVPKill`, `SelfDestruct` |
| Trading/Economy | `MarketBuy`, `MarketSell`, `CargoTransfer`, `MiningRefined`, `MaterialCollected`, `MaterialTrade`, `TechnologyBroker` |
| Missions/Crew | `MissionAccepted`, `MissionCompleted`, `MissionFailed`, `Passengers`, `CrewAssign`, `CrewHire`, `CrewFire` |
| Odyssey/On-Foot | `Embark`, `Disembark`, `BookTaxi`, `BookDropship`, `Backpack`, `UpgradeSuit`, `UpgradeWeapon`, `SellOrganicData` |
| Exploration | `DiscoveryScan`, `FSSDiscoveryScan`, `FSSSignalDiscovered`, `SAAScanComplete`, `Scan`, `CodexEntry` |

## Example Rule

```json
[
  {
    "id": "combat_or_map",
    "enabled": true,
    "when": {
      "source": "dashboard",
      "event": "Status",
      "any": [
        {
          "flags": {
            "all_of": ["FlagsHardpointsDeployed", "FlagsAnalysisMode"]
          }
        },
        {
          "gui_focus": {
            "equals": "GuiFocusGalaxyMap"
          }
        }
      ]
    },
    "then": {
      "vkb_set_shift": ["Shift1", "Subshift3"]
    },
    "else": {
      "vkb_clear_shift": ["Shift1", "Subshift3"]
    }
  }
]
```
