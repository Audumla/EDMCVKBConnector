# Rule Patterns

Use these templates when drafting rules. Replace signal names and values with catalog-valid entries.

## 1) Mode Toggle (single condition)

```json
{
  "title": "Combat Mode",
  "id": "combat-mode",
  "enabled": true,
  "when": {
    "all": [
      { "signal": "hud_mode", "op": "eq", "value": "combat" }
    ]
  },
  "then": [
    { "vkb_set_shift": ["Shift1"] }
  ],
  "else": [
    { "vkb_clear_shift": ["Shift1"] }
  ]
}
```

## 2) Composite State (all + any)

```json
{
  "title": "Supercruise With Assist Off",
  "id": "supercruise-assist-off",
  "enabled": true,
  "when": {
    "all": [
      { "signal": "fsd_status", "op": "eq", "value": "supercruise" }
    ],
    "any": [
      { "signal": "flight_assist", "op": "eq", "value": "off" },
      { "signal": "night_vision", "op": "eq", "value": "on" }
    ]
  },
  "then": [
    { "vkb_set_shift": ["Subshift1"] },
    { "log": "Supercruise profile active" }
  ],
  "else": [
    { "vkb_clear_shift": ["Subshift1"] }
  ]
}
```

## 3) List Membership (enum in)

```json
{
  "title": "Docked Or Landed",
  "id": "docked-or-landed",
  "enabled": true,
  "when": {
    "all": [
      { "signal": "docking_state", "op": "in", "value": ["docked", "landed"] }
    ]
  },
  "then": [
    { "vkb_set_shift": ["Subshift3"] }
  ],
  "else": [
    { "vkb_clear_shift": ["Subshift3"] }
  ]
}
```

## Quick Debug Checklist

- Confirm each `signal` exists in `data/signals_catalog.json`.
- Confirm enum values exactly match catalog entries.
- Confirm bool values are `true`/`false` (not strings).
- Confirm every set action has a matching clear path when needed.
- Confirm `id` stability if edge history should be preserved.
