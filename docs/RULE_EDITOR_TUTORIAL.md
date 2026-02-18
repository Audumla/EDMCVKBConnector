# Rule Editor — UI Guide

This guide walks through creating and managing rules using the built-in editor in the VKB Connector plugin settings panel.

For the complete JSON file format reference, see [`docs/RULES_GUIDE.md`](RULES_GUIDE.md).

---

## Prerequisites

- EDMC is running with **EDMCVKBConnector** loaded.
- VKB-Link is running and the plugin **Settings** tab shows **Connected**.
- You can open `File → Settings → Plugins → VKB Connector`.

---

## The Rules Section

Open `File → Settings → Plugins → VKB Connector`. The **Settings** tab contains a **Rules** panel at the bottom. This is where all rule management happens.

The panel has two parts:

- **Header row** — the **New Rule** button and the current rules file path on the right.
- **Scrollable rule list** — one row per rule.

### Rule list row controls

Each rule row contains (left to right):

| Control | Action |
|---|---|
| ✏ edit icon | Open the rule editor for this rule |
| ⧉ duplicate icon | Copy the rule and append it below |
| 🗑 delete icon | Delete the rule (confirmation required) |
| Checkbox | Enable or disable the rule without deleting it |
| Rule title + summary | Shows title, condition summary, and actions |

Changes to the enable checkbox and duplications save immediately. The editor window has its own Save button.

---

## Creating a Rule

1. Click **New Rule** in the Rules header.
2. The rule editor window opens with an empty rule.
3. Fill in the **Title** field — this is the only required field.
4. Build the **When** (conditions), **Then** (activate actions), and **Else** (deactivate actions) sections.
5. Click **Save Rule**.

The new rule appears at the bottom of the rule list and is active immediately.

---

## The Rule Editor Window

The editor is divided into four sections: **Rule Info**, **When**, **Then**, and **Else**.

### Rule Info

| Field | Required | Notes |
|---|---|---|
| Title | **yes** | Shown in the rule list. Keep it descriptive. |
| Enabled | no | Unchecked rules are loaded but never evaluated. |

---

### When — Building Conditions

The **When** section defines when the rule is considered *active*. Leave it empty for a rule that is always active.

There are two condition groups:

| Group | Meaning |
|---|---|
| **All of these** | Every condition in the group must be true |
| **Any of these** | At least one condition in the group must be true |

When both groups contain conditions, the rule is active when **All** passes **AND** **Any** passes.

#### Adding a condition

1. Click **+ Add condition** under the relevant group (**All** or **Any**).
2. A condition row appears with three dropdowns: **Signal**, **Operator**, **Value**.
3. Select a signal. The signal dropdown is grouped into **Core** (most-used) and **Detail** tiers.
4. The operator dropdown updates automatically to show only operators valid for that signal type.
5. For enum signals, the value dropdown shows all allowed values from the catalog. For number signals, type a number into the value field.
6. Add more conditions with **+ Add condition** as needed.
7. Remove a condition with the **×** button on its row.

#### Choosing All vs Any

Use **All** when every condition must hold simultaneously (e.g. in supercruise *and* FA off).

Use **Any** when any one of several variants should activate the rule (e.g. docked *or* landed).

You can use both groups together: put mandatory conditions in **All** and variant conditions in **Any**.

---

### Then and Else — Building Actions

**Then** runs when the rule transitions from inactive → active.  
**Else** runs when the rule transitions from active → inactive.

Each section lists action rows. Add one with **+ Add action**, remove one with **×**.

Each action row has an **Action type** dropdown:

| Action type | What it does |
|---|---|
| `vkb_set_shift` | Sets the selected VKB shift and/or subshift flags |
| `vkb_clear_shift` | Clears the selected flags |
| `log` | Writes a message to the EDMC plugin log |

#### Shift/subshift checkboxes

For `vkb_set_shift` and `vkb_clear_shift`, a row of checkboxes appears:

- **Shift 1, Shift 2** — main shift states
- **Subshift 1–7** — sub-shift states

Each checkbox has three states:

| State | Appearance | Meaning |
|---|---|---|
| Off | red ✗ | This token is explicitly excluded from the action |
| On | green ✓ | This token is included in the action |
| Ignored | grey (blank) | This token is not mentioned in the action |

Check at least one token to **On** for the action to do anything.

#### Log action

For `log`, type the message text into the field that appears. The message is written at INFO level and visible in EDMC's log output.

#### Pairing set and clear

For shift control, pair every `vkb_set_shift` in **Then** with a matching `vkb_clear_shift` in **Else** covering the same tokens. If you omit the **Else** clear, the shift stays set after the rule deactivates.

Multiple actions can appear in the same section and are executed in order.

---

## Editing an Existing Rule

1. Click the ✏ edit icon on the rule's row in the list.
2. The editor opens pre-populated with the rule's current values.
3. Make changes and click **Save Rule**.
4. The rule list updates immediately and the engine reloads.

---

## Duplicating a Rule

1. Click the ⧉ duplicate icon.
2. A copy named `<original title> (copy)` appears below the original.
3. Click ✏ to edit the copy.

Duplicate before experimenting with a working rule to preserve the original.

---

## Deleting a Rule

1. Click the 🗑 delete icon.
2. Confirm the deletion in the dialog.

Deletion is immediate and cannot be undone from the UI. If you have `rules.json` in version control, you can recover from there.

---

## Enabling and Disabling Rules

The checkbox at the start of each rule row toggles `enabled`. Disabled rules remain in the file but are never evaluated. Use this to suppress a rule temporarily without losing its configuration.

---

## Worked Examples

### Example 1 — Hardpoints toggle

**Goal:** Set `Shift1` when hardpoints deploy; clear it when they retract.

1. Click **New Rule**. Title: `Combat Hardpoints`.
2. Under **All of these**, add a condition:
   - Signal: `hardpoints` → Operator: `eq` → Value: `deployed`
3. Under **Then**, add action `vkb_set_shift`, check **Shift 1** to On.
4. Under **Else**, add action `vkb_clear_shift`, check **Shift 1** to On.
5. Save.

Equivalent JSON:
```json
{
  "title": "Combat Hardpoints",
  "when": { "all": [{ "signal": "hardpoints", "op": "eq", "value": "deployed" }] },
  "then": [{ "vkb_set_shift": ["Shift1"] }],
  "else": [{ "vkb_clear_shift": ["Shift1"] }]
}
```

---

### Example 2 — Multi-condition flight state

**Goal:** Set `Subshift1` only when in supercruise *and* flight assist is off.

1. Title: `SC + FA Off`.
2. Under **All of these**, add two conditions:
   - `fsd_status` `eq` `supercruise`
   - `flight_assist` `eq` `off`
3. Then: `vkb_set_shift` → Subshift 1 On.
4. Else: `vkb_clear_shift` → Subshift 1 On.
5. Save.

Both conditions must be true simultaneously. Either one becoming false triggers Else.

---

### Example 3 — Any-of with a log

**Goal:** Log a message when the ship is docked *or* landed.

1. Title: `Docked or Landed`.
2. Under **Any of these**, add:
   - `docking_state` `eq` `docked`
   - `docking_state` `eq` `landed`
3. Under **Then**, add `log`: `Ship is docked or landed`.
4. Optionally add `vkb_set_shift` / `vkb_clear_shift` for a shift signal too.
5. Save.

Alternatively, use the `in` operator in a single **All** condition:
- `docking_state` `in` `["docked", "landed"]`

That's equivalent and needs only one condition row.

---

## Design Patterns

- **Always pair set and clear.** A `vkb_set_shift` in **Then** without a matching `vkb_clear_shift` in **Else** leaves the shift permanently set once activated.
- **One responsibility per rule.** Split complex intentions into separate rules with meaningful titles.
- **Use `in` to reduce rows.** When a signal can be one of several values, `in` with a list is cleaner than multiple `any` conditions.
- **Use `log` while debugging.** Add a `log` action to confirm whether and when a rule is triggering, then remove it once satisfied.
- **Use `All` for strict profiles.** Combine multiple signals in `All` for precise compound states.
- **Disable before deleting.** Uncheck a rule first and test without it. Delete only when certain it is no longer needed.

---

## Troubleshooting

### Rule never triggers

- Confirm the enable checkbox is checked.
- Check that the signal, operator, and value are a valid combination (signal type must support the operator; enum value must exist in the catalog).
- Add a `log` action to verify the transition fires at all.
- The signal may be `unknown` — this happens when the required data is not present in the current event payload. Check `docs/SIGNALS_REFERENCE.md` for which events populate which signals.

### Rule triggers once and then stops

- Rules are **edge-triggered**. The `then` branch only fires on the false→true transition, not while the condition is continuously true.
- For the rule to fire again, the condition must return to false first.

### Shift state sticks after the condition clears

- Add a `vkb_clear_shift` action in **Else** for every token set in **Then**.
- Check for another rule that also sets the same shift and may not be clearing it.

### Saving does nothing / editor shows an error

- **Title is empty** — title is required.
- **Invalid condition** — the signal, operator, or value may be incompatible (e.g. a numeric operator on an enum signal). The editor shows an inline error.

### Rules file on disk doesn't match the editor

- The rules file is polled every ~1.5 seconds. If you edited `rules.json` directly while the panel was open, click the refresh/reload or reopen the preferences panel.

---

## Related Docs

- [`docs/RULES_GUIDE.md`](RULES_GUIDE.md) — Complete JSON file format reference.
- [`docs/SIGNALS_REFERENCE.md`](SIGNALS_REFERENCE.md) — All signals with types and allowed values.
- [`docs/EDMC_EVENTS_CATALOG.md`](EDMC_EVENTS_CATALOG.md) — Raw event reference.
