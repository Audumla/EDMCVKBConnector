# EDMCVKBConnector Rules Schema

This document describes the current rule format implemented in `src/edmcvkbconnector/rules_engine.py`.

## Top-level rule object

```json
{
  "id": "string (optional, auto-generated if missing)",
  "enabled": true,
  "when": { },
  "then": { },
  "else": { }
}
```

## `when` object

```json
{
  "source": "journal | dashboard | capi | capi_fleetcarrier | any | [..]",
  "event": "EventName | [EventName, ...]",
  "all": [ { /* condition block */ } ],
  "any": [ { /* condition block */ } ]
}
```

- `source`: string or list of strings.
- `event`: string or list of strings.
- `all`: all blocks must match.
- `any`: at least one block must match.

## Condition block types

Each object in `all`/`any` must be exactly one of:

- `{ "flags": { ... } }`
- `{ "flags2": { ... } }`
- `{ "gui_focus": { ... } }`
- `{ "field": { ... } }`

### `flags` / `flags2` operators

```json
{
  "all_of": ["FlagName"],
  "any_of": ["FlagName"],
  "none_of": ["FlagName"],
  "equals": { "FlagName": true },
  "changed_to_true": ["FlagName"],
  "changed_to_false": ["FlagName"]
}
```

### `gui_focus` operators

```json
{
  "equals": "GuiFocusGalaxyMap",
  "in": ["GuiFocusGalaxyMap", "GuiFocusSystemMap"],
  "changed_to": "GuiFocusFSS"
}
```

`gui_focus` values may be names (preferred) or ints.

### `field` operators

```json
{
  "name": "dot.path.to.field",
  "exists": true,
  "equals": "value",
  "in": ["a", "b"],
  "not_in": ["x", "y"],
  "contains": "substring-or-key",
  "gt": 1,
  "gte": 1,
  "lt": 10,
  "lte": 10,
  "changed": true,
  "changed_to": "target"
}
```

- `name` is required.
- Dot-path access is supported (`commander.name`).

## Where values like HardpointsDeployed and AnalysisMode come from

They come from EDMC dashboard/status notifications, specifically the bitfield integer fields:

- `Flags` (mapped to `Flags*` names)
- `Flags2` (mapped to `Flags2*` names)
- `GuiFocus` (mapped to `GuiFocus*` names)

In rules, you must use the mapped names from this plugin (for example `FlagsHardpointsDeployed`, not `HardpointsDeployed`).

## Supported `Flags` names

- `FlagsDocked`
- `FlagsLanded`
- `FlagsLandingGearDown`
- `FlagsShieldsUp`
- `FlagsSupercruise`
- `FlagsFlightAssistOff`
- `FlagsHardpointsDeployed`
- `FlagsInWing`
- `FlagsLightsOn`
- `FlagsCargoScoopDeployed`
- `FlagsSilentRunning`
- `FlagsScoopingFuel`
- `FlagsSrvHandbrake`
- `FlagsSrvTurret`
- `FlagsSrvUnderShip`
- `FlagsSrvDriveAssist`
- `FlagsFsdMassLocked`
- `FlagsFsdCharging`
- `FlagsFsdCooldown`
- `FlagsLowFuel`
- `FlagsOverHeating`
- `FlagsHasLatLong`
- `FlagsIsInDanger`
- `FlagsBeingInterdicted`
- `FlagsInMainShip`
- `FlagsInFighter`
- `FlagsInSRV`
- `FlagsAnalysisMode`
- `FlagsNightVision`
- `FlagsAverageAltitude`
- `FlagsFsdJump`
- `FlagsSrvHighBeam`

## Supported `Flags2` names

- `Flags2OnFoot`
- `Flags2InTaxi`
- `Flags2InMulticrew`
- `Flags2OnFootInStation`
- `Flags2OnFootOnPlanet`
- `Flags2AimDownSight`
- `Flags2LowOxygen`
- `Flags2LowHealth`
- `Flags2Cold`
- `Flags2Hot`
- `Flags2VeryCold`
- `Flags2VeryHot`
- `Flags2GlideMode`
- `Flags2OnFootInHangar`
- `Flags2OnFootSocialSpace`
- `Flags2OnFootExterior`
- `Flags2BreathableAtmosphere`

## Supported `GuiFocus` names

- `GuiFocusNoFocus` (0)
- `GuiFocusInternalPanel` (1)
- `GuiFocusExternalPanel` (2)
- `GuiFocusCommsPanel` (3)
- `GuiFocusRolePanel` (4)
- `GuiFocusStationServices` (5)
- `GuiFocusGalaxyMap` (6)
- `GuiFocusSystemMap` (7)
- `GuiFocusOrrery` (8)
- `GuiFocusFSS` (9)
- `GuiFocusSAA` (10)
- `GuiFocusCodex` (11)

## Example

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

