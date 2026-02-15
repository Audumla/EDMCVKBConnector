# Migration Guide: Legacy Rules -> v3 Catalog Rules

## Backward compatibility strategy

This release uses a **hard break** for match conditions:

- Legacy condition blocks (`flags`, `flags2`, `gui_focus`, `field`, `source`, `event`) are not valid in v3 rules.
- Rules must be rewritten to catalog `signal` + `op` + `value`.
- On invalid rules/catalog, loading fails clearly and the rule engine is disabled.

Action dictionaries are still accepted and normalized into ordered action arrays.

## Mapping patterns

## 1) Remove source/event filters

Legacy:
```json
{ "when": { "source": "dashboard", "event": "Status", ... } }
```

v3:
- Remove `source` and `event` from rules.
- Express intent only through signal conditions.

## 2) Flags/Flags2 to bool or enum signals

Legacy:
```json
{ "flags": { "equals": { "FlagsLandingGearDown": true } } }
```

v3 (bool):
```json
{ "signal": "gear_down", "op": "eq", "value": true }
```

v3 (enum preferred when available):
```json
{ "signal": "landing_gear", "op": "eq", "value": "down" }
```

## 3) GuiFocus to gui_focus enum

Legacy:
```json
{ "gui_focus": { "equals": "GuiFocusGalaxyMap" } }
```

v3:
```json
{ "signal": "gui_focus", "op": "eq", "value": "GalaxyMap" }
```

## 4) Field conditions

Legacy:
```json
{ "field": { "name": "Some.Path", "gt": 5 } }
```

v3:
- Not directly supported unless that field is exposed as a catalog signal.
- Add/extend catalog signal definitions first, then reference the new signal.

## Enum vs bool choice

When both exist:

- Prefer enum style when state is naturally multi-state
  - Example: `landing_gear = down`
- Bool style is still valid when simpler/clearer
  - Example: `gear_down = true`

## Validation outcomes

v3 loader now reports per-rule errors for:

- unknown signal
- unknown operator
- missing required value
- invalid value type/enum
- invalid shift tokens
