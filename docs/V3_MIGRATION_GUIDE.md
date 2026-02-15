# V3 Schema Migration Guide

This guide explains how to migrate from the old (v2) rule schema to the new (v3) signal-based schema.

## Overview of Changes

### V2 (Old Schema)
- Rules directly reference internal implementation details:
  - `when.flags`, `when.flags2`, `when.gui_focus`
  - Raw bitfield names like `FlagsHardpointsDeployed`
- Rules have `id` (required) but no `title`
- Actions are objects: `{"vkb_set_shift": [...]}`

### V3 (New Schema)
- Rules use high-level **signals** defined in the catalog
- Signals hide implementation details (flags, bitfields)
- Rules have `title` (required) and auto-generated `id`
- Actions are arrays of objects: `[{"vkb_set_shift": [...]}]`
- Edge-triggered evaluation (actions only fire on state transitions)

## Key Concepts

### Signals
Signals are user-facing abstractions of game state. Each signal:
- Has a **type** (`bool` or `enum`)
- Has **UI metadata** (label, icon, category, tier)
- Has **derive specification** that maps raw data to signal value
- Is defined in `signals_catalog.json`

Examples:
- `hardpoints` (enum): `"retracted"` or `"deployed"`
- `weapons_out` (bool): `true` or `false`
- `gui_focus` (enum): `"GalaxyMap"`, `"NoFocus"`, etc.

### Operators
All operators are defined in the catalog:
- `eq`: equals
- `ne`: not equal
- `in`: value in list
- `nin`: value not in list
- `lt`, `lte`, `gt`, `gte`: comparisons
- `contains`: contains value
- `exists`: signal exists (always true for catalog signals)

## Migration Patterns

### Pattern 1: Simple Flag Check

**V2:**
```json
{
  "id": "hardpoints_deployed",
  "when": {
    "source": "dashboard",
    "all": [
      {
        "flags": {
          "all_of": ["FlagsHardpointsDeployed"]
        }
      }
    ]
  },
  "then": {"vkb_set_shift": ["Shift1"]},
  "else": {"vkb_clear_shift": ["Shift1"]}
}
```

**V3 (using enum signal):**
```json
{
  "title": "Hardpoints Deployed",
  "when": {
    "all": [
      {
        "signal": "hardpoints",
        "op": "eq",
        "value": "deployed"
      }
    ]
  },
  "then": [{"vkb_set_shift": ["Shift1"]}],
  "else": [{"vkb_clear_shift": ["Shift1"]}]
}
```

**V3 (using bool signal):**
```json
{
  "title": "Hardpoints Deployed",
  "when": {
    "all": [
      {
        "signal": "weapons_out",
        "op": "eq",
        "value": true
      }
    ]
  },
  "then": [{"vkb_set_shift": ["Shift1"]}],
  "else": [{"vkb_clear_shift": ["Shift1"]}]
}
```

### Pattern 2: GuiFocus Check

**V2:**
```json
{
  "id": "galaxy_map",
  "when": {
    "source": "dashboard",
    "all": [
      {
        "gui_focus": {
          "equals": "GuiFocusGalaxyMap"
        }
      }
    ]
  },
  "then": {"vkb_set_shift": ["Shift2"]}
}
```

**V3:**
```json
{
  "title": "Galaxy Map",
  "when": {
    "all": [
      {
        "signal": "gui_focus",
        "op": "eq",
        "value": "GalaxyMap"
      }
    ]
  },
  "then": [{"vkb_set_shift": ["Shift2"]}]
}
```

### Pattern 3: Multiple Flag Check

**V2:**
```json
{
  "id": "combat_ready",
  "when": {
    "source": "dashboard",
    "all": [
      {
        "flags": {
          "all_of": ["FlagsHardpointsDeployed", "FlagsShieldsUp", "FlagsInMainShip"]
        }
      },
      {
        "flags2": {
          "none_of": ["Flags2OnFoot"]
        }
      }
    ]
  },
  "then": {"vkb_set_shift": ["Shift1", "Subshift6"]}
}
```

**V3:**
```json
{
  "title": "Combat Ready",
  "when": {
    "all": [
      {
        "signal": "weapons_out",
        "op": "eq",
        "value": true
      },
      {
        "signal": "shields_up",
        "op": "eq",
        "value": true
      },
      {
        "signal": "in_ship",
        "op": "eq",
        "value": true
      },
      {
        "signal": "on_foot",
        "op": "eq",
        "value": false
      }
    ]
  },
  "then": [{"vkb_set_shift": ["Shift1", "Subshift6"]}]
}
```

### Pattern 4: Any Condition

**V2:**
```json
{
  "id": "emergency",
  "when": {
    "source": "dashboard",
    "any": [
      {
        "flags": {"all_of": ["FlagsIsInDanger"]}
      },
      {
        "flags2": {"all_of": ["Flags2LowHealth"]}
      }
    ]
  },
  "then": {"vkb_set_shift": ["Subshift3"]}
}
```

**V3:**
```json
{
  "title": "Emergency",
  "when": {
    "any": [
      {
        "signal": "in_danger",
        "op": "eq",
        "value": true
      },
      {
        "signal": "low_health",
        "op": "eq",
        "value": true
      }
    ]
  },
  "then": [{"vkb_set_shift": ["Subshift3"]}]
}
```

## V2 to V3 Signal Mapping

### Common Flag Mappings

| V2 Flag | V3 Bool Signal | V3 Enum Signal | Enum Values |
|---------|----------------|----------------|-------------|
| `FlagsHardpointsDeployed` | `weapons_out` | `hardpoints` | `retracted`, `deployed` |
| `FlagsLandingGearDown` | `gear_down` | `landing_gear` | `up`, `down` |
| `FlagsCargoScoopDeployed` | `scoop_out` | `cargo_scoop` | `retracted`, `deployed` |
| `FlagsDocked` | `docked` | `docking_state` | `in_space`, `landed`, `docked` |
| `FlagsLanded` | `landed` | `docking_state` | `in_space`, `landed`, `docked` |
| `FlagsSupercruise` | `in_supercruise` | `supercruise` | `off`, `on` |
| `FlagsAnalysisMode` | `analysis_mode` | `hud_mode` | `combat`, `analysis` |
| `FlagsInMainShip` | `in_ship` | `vehicle` | `ship`, `srv`, `fighter`, `unknown` |
| `FlagsInSRV` | `in_srv` | `vehicle` | `ship`, `srv`, `fighter`, `unknown` |
| `FlagsInFighter` | `in_fighter` | `vehicle` | `ship`, `srv`, `fighter`, `unknown` |
| `Flags2OnFoot` | `on_foot` | `presence` | `vehicle`, `foot` |

See `signals_catalog.json` for the complete list of signals.

### GuiFocus Mappings

| V2 GuiFocus | V3 gui_focus Value |
|-------------|-------------------|
| `GuiFocusNoFocus` | `NoFocus` |
| `GuiFocusInternalPanel` | `InternalPanel` |
| `GuiFocusExternalPanel` | `ExternalPanel` |
| `GuiFocusCommsPanel` | `CommsPanel` |
| `GuiFocusRolePanel` | `RolePanel` |
| `GuiFocusStationServices` | `StationServices` |
| `GuiFocusGalaxyMap` | `GalaxyMap` |
| `GuiFocusSystemMap` | `SystemMap` |
| `GuiFocusOrrery` | `Orrery` |
| `GuiFocusFSS` | `FSS` |
| `GuiFocusSAA` | `SAA` |
| `GuiFocusCodex` | `Codex` |

## Enum vs Bool: Which to Use?

When both exist (e.g., `hardpoints` enum vs `weapons_out` bool):

**Prefer enum when:**
- You want to match multiple states: `"op": "in", "value": ["deployed", "retracted"]`
- The rule reads more naturally: "hardpoints = deployed"
- You might add more states in the future

**Use bool when:**
- You only care about true/false
- It matches your mental model: "weapons_out = true"
- The rule is simpler: one less level of indirection

Both are valid! Choose what reads better for your use case.

## Edge Triggering

V3 rules use **edge-triggered evaluation**:
- Actions only execute when the rule's match state **changes**
- Prevents repeated execution while state is stable
- Implements "no spam" invariant

**Example:**
```
State:       false -> true  -> true  -> false -> false
Match:       no       yes      yes      no       no
Actions:     none     THEN     none     ELSE     none
```

## File Format

V3 supports two file formats:

**Array format** (same as v2):
```json
[
  { "title": "Rule 1", ... },
  { "title": "Rule 2", ... }
]
```

**Wrapped format** (new):
```json
{
  "rules": [
    { "title": "Rule 1", ... },
    { "title": "Rule 2", ... }
  ]
}
```

Both formats work identically. Wrapped format is recommended for forward compatibility.

## Backward Compatibility

The system can **auto-detect** schema version by inspecting rule structure:
- v2 rules have `when.flags`, `when.source`, no `title`
- v3 rules have `when.all`/`when.any` with `signal`, has `title`

**Recommendation:** Migrate to v3 for:
- Better validation and error messages
- Signal abstraction (easier to maintain)
- Future UI support
- Edge-triggered behavior

## Migration Checklist

1. ✅ Read this guide
2. ✅ Review `signals_catalog.json` for available signals
3. ✅ For each rule:
   - Add `title` field (descriptive name)
   - Remove `id` field (will be auto-generated)
   - Replace `when.source` / `when.event` (no longer needed)
   - Replace `when.flags` / `when.flags2` with signal conditions
   - Replace `when.gui_focus` with `gui_focus` signal
   - Convert actions to array format: `{"vkb_set_shift": [...]}` → `[{"vkb_set_shift": [...]}]`
4. ✅ Test with EDMC
5. ✅ Verify edge-triggered behavior (actions don't spam)

## Example Complete Migration

See `rules_v3.json.example` for a complete example ruleset demonstrating:
- All condition
- Any condition
- Combined (all + any) condition
- Bool signal conditions
- Enum signal conditions
- In operator with list
- Multiple actions in then/else
- Edge-triggered behavior

## Questions?

See the signals catalog (`signals_catalog.json`) for:
- All available signals and their types
- Enum value options
- UI metadata (for future visual editor)
- Derivation specifications (how signals map to raw data)
