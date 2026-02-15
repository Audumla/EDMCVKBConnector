# Rules Schema (v3)

This plugin now uses a catalog-backed rule schema. Rules only reference catalog
`signals` and catalog `operators`.

## Rule file shape

Both shapes are supported:

1. Top-level array:
```json
[{ "...": "..." }]
```
2. Wrapped object:
```json
{ "rules": [{ "...": "..." }] }
```

## Rule object

```json
{
  "id": "optional-stable-id",
  "title": "Required title",
  "enabled": true,
  "when": {
    "all": [{ "signal": "gear_down", "op": "eq", "value": true }],
    "any": [{ "signal": "gui_focus", "op": "in", "value": ["GalaxyMap", "SystemMap"] }]
  },
  "then": [
    { "type": "vkb_set_shift", "tokens": ["Shift1"] },
    { "type": "log", "message": "Matched" }
  ],
  "else": [
    { "type": "vkb_clear_shift", "tokens": ["Shift1"] }
  ]
}
```

## Defaults

- `enabled`: defaults to `true`
- `when`: defaults to `{ "all": [] }`
- `then`: defaults to `[]`
- `else`: defaults to `[]`
- If `id` is omitted, it is deterministically generated from `title`
  - Collisions are suffixed (`-2`, `-3`, ...)

## Condition semantics

- `when.all`: every condition must match
- `when.any`: at least one condition must match
- If both are present: `(ALL) AND (ANY)`
- Missing `when` behaves like `{ "all": [] }` (always true)

## Operators and values

Operators come from `signals_catalog.json`:
`eq`, `ne`, `in`, `nin`, `lt`, `lte`, `gt`, `gte`, `contains`, `exists`.

Validation is catalog-driven:

- `signal` must exist in `catalog.signals`
- `op` must exist in `catalog.operators`
- `value` required for all operators except `exists`
- `bool` signals:
  - `eq`/`ne` require boolean
  - `in`/`nin` require list of booleans
- `enum` signals:
  - `eq`/`ne` require one allowed enum value
  - `in`/`nin` require a list of allowed enum values

## Actions

Actions are ordered and executed in list order.

Supported action types:

- `{ "type": "log", "message": "..." }`
- `{ "type": "vkb_set_shift", "tokens": ["Shift1", "Subshift3"] }`
- `{ "type": "vkb_clear_shift", "tokens": ["Shift1", "Subshift3"] }`

Shift tokens must be exact string tokens (`Shift1`, `Shift2`, `Subshift1`..`Subshift7`).

## Edge-triggered execution

Each rule tracks previous match state per commander/beta session:

- `false -> true`: execute `then`
- `true -> false`: execute `else`
- otherwise: no action

This enforces the no-spam invariant for repeated identical input states.
