# V3 Rules Schema Reference

Complete reference for the v3 signal-based rule schema.

## Overview

V3 rules use high-level **signals** defined in `signals_catalog.json`:
- Rules reference signals by name, not implementation details
- Signals automatically derive values from raw Elite Dangerous data
- Rules have descriptive `title` and auto-generated `id`
- Actions are arrays: `[{"vkb_set_shift": [...]}]`
- Edge-triggered evaluation prevents action spam

## Rule Structure

### Minimal Rule

```json
{
  "title": "My Rule"
}
```

This rule:
- Always matches (no conditions)
- Executes no actions
- Auto-generates ID from title

### Complete Rule

```json
{
  "id": "custom_id",
  "title": "Hardpoints Deployed",
  "enabled": true,
  "when": {
    "all": [
      {
        "signal": "hardpoints",
        "op": "eq",
        "value": "deployed"
      }
    ]
  },
  "then": [
    {"vkb_set_shift": ["Shift1"]},
    {"log": "Hardpoints deployed"}
  ],
  "else": [
    {"vkb_clear_shift": ["Shift1"]}
  ]
}
```

### Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | **Yes** | - | Human-readable rule name |
| `id` | string | No | auto-generated | Unique identifier (generated from title if omitted) |
| `enabled` | boolean | No | `true` | Enable/disable rule |
| `when` | object | No | `{"all": []}` | Conditions (see below) |
| `then` | array | No | `[]` | Actions when rule becomes true |
| `else` | array | No | `[]` | Actions when rule becomes false |

## Conditions (`when` clause)

### Boolean Logic

```json
{
  "when": {
    "all": [ /* all must match */ ],
    "any": [ /* at least one must match */ ]
  }
}
```

Logic:
- **`all` only**: All conditions must match
- **`any` only**: At least one condition must match
- **Both `all` and `any`**: (ALL) AND (ANY) logic
- **Neither**: Always matches (empty condition)

### Condition Structure

```json
{
  "signal": "signal_name",
  "op": "operator",
  "value": "expected_value"
}
```

Fields:
- `signal` (required): Signal name from catalog
- `op` (required): Operator (see below)
- `value` (required for most operators): Expected value

### Operators

| Operator | Description | Value Type | Example |
|----------|-------------|------------|---------|
| `eq` | Equals | any | `{"signal": "docked", "op": "eq", "value": true}` |
| `ne` | Not equal | any | `{"signal": "hud_mode", "op": "ne", "value": "combat"}` |
| `in` | In list | array | `{"signal": "gui_focus", "op": "in", "value": ["GalaxyMap", "SystemMap"]}` |
| `nin` | Not in list | array | `{"signal": "vehicle", "op": "nin", "value": ["srv", "fighter"]}` |
| `lt` | Less than | number | `{"signal": "fuel_level", "op": "lt", "value": 10}` |
| `lte` | Less than or equal | number | `{"signal": "hull", "op": "lte", "value": 50}` |
| `gt` | Greater than | number | `{"signal": "speed", "op": "gt", "value": 100}` |
| `gte` | Greater than or equal | number | `{"signal": "shields", "op": "gte", "value": 75}` |
| `contains` | Contains value | string/list | `{"signal": "cargo", "op": "contains", "value": "Gold"}` |
| `exists` | Signal exists | (none) | `{"signal": "target", "op": "exists"}` |

Value requirements:
- `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `contains`: **required**
- `in`, `nin`: **required** (must be array)
- `exists`: **optional** (ignored)

## Actions

Actions are executed in order when a rule's match state changes.

### Available Actions

#### Set VKB Shift Flags

```json
{"vkb_set_shift": ["Shift1", "Subshift3"]}
```

Valid shift tokens:
- Main shifts: `Shift1`, `Shift2`
- Subshifts: `Subshift1` through `Subshift8`

#### Clear VKB Shift Flags

```json
{"vkb_clear_shift": ["Shift1", "Subshift3"]}
```

#### Log Message

```json
{"log": "Hardpoints deployed"}
```

### Multiple Actions

```json
"then": [
  {"vkb_set_shift": ["Shift1"]},
  {"vkb_set_shift": ["Subshift2"]},
  {"log": "Combat mode activated"}
]
```

Actions execute in array order.

## Edge-Triggered Evaluation

Rules use **edge-triggered** evaluation:
- `then` actions execute when rule **transitions** from `false` to `true`
- `else` actions execute when rule **transitions** from `true` to `false`
- No actions execute while state remains unchanged

**Example:**
```
State:    false → true  → true  → false → false → true
Match:    no      yes     yes     no      no      yes
Actions:  -       THEN    -       ELSE    -       THEN
```

This prevents action spam (the "no spam" invariant).

## Signal Reference

See `signals_catalog.json` for the complete list of signals.

### Common Signals

#### Boolean Signals

| Signal | Description | Values |
|--------|-------------|--------|
| `docked` | Ship is docked | `true`, `false` |
| `landed` | Ship is landed | `true`, `false` |
| `gear_down` | Landing gear deployed | `true`, `false` |
| `shields_up` | Shields are up | `true`, `false` |
| `weapons_out` | Hardpoints deployed | `true`, `false` |
| `in_supercruise` | In supercruise | `true`, `false` |
| `in_danger` | In danger | `true`, `false` |
| `overheating` | Overheating | `true`, `false` |
| `on_foot` | Commander on foot | `true`, `false` |
| `low_health` | Low health | `true`, `false` |

#### Enum Signals

| Signal | Values | Description |
|--------|--------|-------------|
| `gui_focus` | `NoFocus`, `InternalPanel`, `ExternalPanel`, `CommsPanel`, `RolePanel`, `StationServices`, `GalaxyMap`, `SystemMap`, `Orrery`, `FSS`, `SAA`, `Codex` | Focused screen |
| `hardpoints` | `retracted`, `deployed` | Hardpoints state |
| `landing_gear` | `up`, `down` | Landing gear state |
| `cargo_scoop` | `retracted`, `deployed` | Cargo scoop state |
| `hud_mode` | `combat`, `analysis` | HUD mode |
| `docking_state` | `in_space`, `landed`, `docked` | Docking/landing state |
| `supercruise` | `off`, `on` | Supercruise state |
| `fsd_state` | `idle`, `charging`, `cooldown`, `jumping` | FSD state |
| `vehicle` | `ship`, `srv`, `fighter`, `unknown` | Current vehicle |
| `presence` | `vehicle`, `foot` | In vehicle or on foot |

### Enum vs Bool

Many game states have both enum and bool signals:
- `hardpoints` (enum) vs `weapons_out` (bool)
- `landing_gear` (enum) vs `gear_down` (bool)
- `cargo_scoop` (enum) vs `scoop_out` (bool)

**Use enum when:**
- Matching multiple states: `"op": "in", "value": ["deployed", "retracted"]`
- More readable: `hardpoints = deployed`
- Future expansion possible

**Use bool when:**
- Simple true/false check
- Matches mental model: `weapons_out = true`
- Simpler condition

Both are valid! Choose what reads better.

## File Format

### Array Format

```json
[
  {"title": "Rule 1", ...},
  {"title": "Rule 2", ...}
]
```

### Wrapped Format

```json
{
  "rules": [
    {"title": "Rule 1", ...},
    {"title": "Rule 2", ...}
  ]
}
```

Both formats work identically.

## Complete Examples

See `rules_v3.json.example` for complete working examples including:
- Simple enum condition
- Simple bool condition
- Any condition (multiple ORs)
- Combined all + any condition
- Multiple actions
- In operator with list

## Validation

The v3 engine validates:
- Signal names exist in catalog
- Operators exist in catalog
- Values match signal type (bool/enum)
- Enum values are in allowed list
- Required `title` field present
- Condition structure is valid

Invalid rules are skipped with clear error messages.

## Catalog Structure

Signals are defined in `signals_catalog.json`:

```json
{
  "version": 3,
  "ui_tiers": {
    "core": {"label": "Common", "icon": "star"},
    "detail": {"label": "More", "icon": "dots"}
  },
  "operators": { /* operator definitions */ },
  "bitfields": { /* internal field mappings */ },
  "signals": {
    "signal_name": {
      "type": "bool" | "enum",
      "title": "Display Title",
      "ui": {
        "label": "UI Label",
        "icon": "icon-name",
        "category": "Category",
        "tier": "core" | "detail"
      },
      "values": [ /* for enum type */ ],
      "derive": { /* derivation spec */ }
    }
  }
}
```

The catalog:
- Defines all available signals
- Specifies signal types and allowed values
- Provides UI metadata for future visual editor
- Contains derivation logic (hidden from users)

## Best Practices

1. **Use descriptive titles**: `"Hardpoints Deployed"` not `"rule1"`
2. **Prefer enum for multi-state**: `docking_state` over multiple bool checks
3. **Use `any` for OR logic**: Multiple danger conditions
4. **Keep conditions simple**: Break complex rules into multiple simpler rules
5. **Test edge triggering**: Verify actions fire only on transitions
6. **Document with log actions**: `{"log": "Rule fired"}` helps debugging
