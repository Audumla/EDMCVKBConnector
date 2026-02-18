# Rules Guide

This guide covers creating and editing rules for EDMCVKBConnector.

## Rule Model
Each rule has:
- `title`: required display name.
- `enabled`: optional, defaults to `true`.
- `when`: optional condition block using `all` and/or `any`.
- `then`: actions when rule transitions from false to true.
- `else`: actions when rule transitions from true to false.

Rules are edge-triggered, so actions run on state transitions, not every update.

If a signal cannot be derived due to missing data, its value is set to `unknown`.
Rules do not trigger when any required signal is `unknown`, so conditions only
fire with conclusive data.

## Creating Rules in the UI
1. Open `File -> Settings -> Plugins`.
2. Find **VKB Connector**.
3. In the **Rules** panel, click **New Rule**.
4. Set title, conditions, and actions.
5. Save and confirm the rule appears in the rules list.

You can also edit, duplicate, delete, and toggle rule enablement from the same panel.

## Condition Format
Conditions are objects:

```json
{ "signal": "hardpoints", "op": "eq", "value": "deployed" }
```

`when` supports both blocks:
- `all`: every condition must match.
- `any`: at least one condition must match.

If both are present, evaluation is `(ALL) AND (ANY)`.

## Supported Operators
- `eq`, `ne`
- `in`, `nin`
- `lt`, `lte`, `gt`, `gte`
- `contains`
- `exists`

Operator availability depends on signal type (enum/string/number/array).

## Actions
Supported action keys:
- `vkb_set_shift`: set VKB flags.
- `vkb_clear_shift`: clear VKB flags.
- `log`: write a message to plugin logs.

Shift token format:
- Main shifts: `Shift1`, `Shift2`
- Subshifts: `Subshift1` through `Subshift7`

Example action list:

```json
[
  { "vkb_set_shift": ["Shift1", "Subshift2"] },
  { "log": "Combat profile active" }
]
```

## Full Example
```json
{
  "title": "Hardpoints Deployed",
  "enabled": true,
  "when": {
    "all": [
      { "signal": "hardpoints", "op": "eq", "value": "deployed" }
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

## File Format
`rules.json` may be either:
- array root:
```json
[{ "title": "Rule A" }]
```
- wrapped root:
```json
{ "rules": [{ "title": "Rule A" }] }
```

Both formats are supported by the loader and UI.

## Rule Validation Notes
At load time, the engine validates:
- signal exists in catalog,
- operator exists,
- enum values are valid,
- condition and action structure.

Invalid rules are skipped with log errors; valid rules continue to load.
