# Rules — File Format Reference

This document is the authoritative reference for the `rules.json` file format.

For the step-by-step UI walkthrough, see [`docs/RULE_EDITOR_TUTORIAL.md`](RULE_EDITOR_TUTORIAL.md).

---

## File Location

By default the plugin reads `rules.json` from the plugin directory (the folder containing `load.py`). An override path can be set with the `rules_path` config key.

A starter file is created automatically on first run from `rules.json.example`.

---

## Top-Level Format

The file may use either an **array root** or a **wrapped-object root**; both are accepted.

**Array root** (preferred):
```json
[
  { "title": "Rule A", ... },
  { "title": "Rule B", ... }
]
```

**Wrapped root**:
```json
{
  "rules": [
    { "title": "Rule A", ... }
  ]
}
```

The UI always saves in array-root format.

---

## Rule Object Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `title` | string | **yes** | — | Human-readable name shown in the rule list. Must be non-empty. |
| `id` | string | no | auto-generated from title | Stable identifier used for edge-trigger state tracking. Changing an `id` resets the rule's previous state. |
| `enabled` | boolean | no | `true` | When `false` the rule is loaded but never evaluated. |
| `when` | object | no | `{}` (always true) | Condition block. Omit or leave empty to create an always-on rule. |
| `then` | array | no | `[]` | Actions executed when the rule transitions **false → true**. |
| `else` | array | no | `[]` | Actions executed when the rule transitions **true → false**. |

### ID generation

If `id` is absent, the engine slugifies the `title` (lowercase, spaces → hyphens, non-alphanumeric removed) and appends a numeric suffix if needed to ensure uniqueness. The generated ID is **not** written back to the file.

---

## Edge Triggering

Rules are **edge-triggered**, not level-triggered.

- `then` runs **once** when the condition result changes from `false` to `true`.
- `else` runs **once** when the condition result changes from `true` to `false`.
- No actions run while the condition result stays the same between events.
- On the very first evaluation of a rule, whichever branch matches runs once to establish an initial state.

Edge state is tracked per `(commander, is_beta, rule_id)` tuple, so switching commanders or beta mode resets state independently.

---

## The `when` Block

```json
"when": {
  "all": [ <condition>, ... ],
  "any": [ <condition>, ... ]
}
```

Evaluation logic:

| Blocks present | Evaluates to true when |
|---|---|
| `all` only | every condition in `all` is true |
| `any` only | at least one condition in `any` is true |
| `all` **and** `any` | every `all` condition is true **AND** at least one `any` condition is true |
| neither | always true (unconditional rule) |

Either block may be an empty list `[]`; an empty block is ignored, not treated as false.

---

## Condition Object

```json
{ "signal": "<signal_name>", "op": "<operator>", "value": <value> }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `signal` | string | **yes** | Signal name from `signals_catalog.json`. |
| `op` | string | **yes** | Operator identifier (see table below). |
| `value` | any | depends on op | The comparison value. Required for all operators except `exists`. |

If a signal cannot be derived from the current event (data not present), its value is `unknown`. **Rules whose required signals are `unknown` are skipped entirely** — they do not fire and do not update edge state. This means conditions only fire with conclusive data.

### Operators

| Operator | Meaning | Applicable signal types | `value` type |
|---|---|---|---|
| `eq` | equal | enum, bool, number, string | scalar matching the signal type |
| `ne` | not equal | enum, bool, number, string | scalar matching the signal type |
| `in` | signal value is in list | enum, string | JSON array of scalars |
| `nin` | signal value is not in list | enum, string | JSON array of scalars |
| `lt` | less than | number | number |
| `lte` | less than or equal | number | number |
| `gt` | greater than | number | number |
| `gte` | greater than or equal | number | number |
| `contains` | list/string contains value | array, string | scalar |
| `exists` | signal was derived (always true if reached) | any | omit or `null` |

**Bool signals** only accept `eq` and `ne`; the value must be a JSON boolean (`true`/`false`).

**Enum signals** only accept string values that appear in the catalog's `values` list for that signal; non-catalog values are rejected at load time.

---

## Action Object

Each item in `then` or `else` is an object with exactly one action key.

### `vkb_set_shift`

Sets one or more VKB shift/subshift flags:

```json
{ "vkb_set_shift": ["Shift1", "Subshift3"] }
```

A single token may be given as a string instead of a one-element array:

```json
{ "vkb_set_shift": "Shift1" }
```

### `vkb_clear_shift`

Clears one or more flags. Same token format as `vkb_set_shift`:

```json
{ "vkb_clear_shift": ["Shift1", "Subshift3"] }
```

### `log`

Writes a message to the plugin log at INFO level:

```json
{ "log": "Combat profile activated" }
```

### Shift Token Reference

| Token | VKB resource |
|---|---|
| `Shift1` | Main shift 1 |
| `Shift2` | Main shift 2 |
| `Subshift1` … `Subshift7` | Sub-shifts 1–7 |

Multiple actions may appear in the same list and are executed in order:

```json
"then": [
  { "vkb_set_shift": ["Shift1", "Subshift2"] },
  { "log": "Combat mode on" }
]
```

---

## Validation

At load time the engine validates every rule before adding it to the active set:

- `title` is present and a non-empty string.
- `when`, if present, is an object.
- `when.all` and `when.any`, if present, are arrays.
- Each condition has `signal` (exists in catalog), `op` (exists in catalog), and a `value` compatible with the signal type.
- `then` and `else`, if present, are arrays of non-empty dicts.

**Invalid rules are skipped with an error log entry; all other rules continue to load.** The rule list in the UI flags rules that failed validation.

---

## Annotated Example

```json
[
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
      { "vkb_set_shift": ["Shift1"] },
      { "log": "Entered combat HUD" }
    ],
    "else": [
      { "vkb_clear_shift": ["Shift1"] }
    ]
  },
  {
    "title": "Docked or Landed",
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
  },
  {
    "title": "SC and FA Off",
    "enabled": true,
    "when": {
      "all": [
        { "signal": "fsd_status",    "op": "eq", "value": "supercruise" },
        { "signal": "flight_assist", "op": "eq", "value": "off" }
      ]
    },
    "then": [
      { "vkb_set_shift": ["Subshift1"] }
    ],
    "else": [
      { "vkb_clear_shift": ["Subshift1"] }
    ]
  }
]
```

---

## Related Docs

- [`docs/RULE_EDITOR_TUTORIAL.md`](RULE_EDITOR_TUTORIAL.md) — Create and manage rules through the plugin UI.
- [`docs/SIGNALS_REFERENCE.md`](SIGNALS_REFERENCE.md) — Full signal catalog with types and allowed values.
- [`docs/EDMC_EVENTS_CATALOG.md`](EDMC_EVENTS_CATALOG.md) — Raw journal/dashboard event reference.
