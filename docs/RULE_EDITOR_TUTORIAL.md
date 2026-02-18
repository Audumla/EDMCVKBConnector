# Rule Editor Tutorial

This tutorial walks through the built-in **VKB Connector** rule editor in EDMC from first open to troubleshooting.

For complete rule syntax details, see `docs/RULES_GUIDE.md`.

## Before You Start

- EDMC is running with the `EDMCVKBConnector` plugin loaded.
- VKB-Link is running and reachable from the plugin `Host`/`Port`.
- You can open `File -> Settings -> Plugins -> VKB Connector`.

## Rule Editor Basics

From `File -> Settings -> Plugins -> VKB Connector`, the **Rules** section lets you:
- Create rules (`New Rule`)
- Modify existing rules (`Edit`)
- Copy rules (`Duplicate`)
- Remove rules (`Delete`)
- Enable/disable rules quickly (toggle)

Each rule has:
- `title`: name shown in the list.
- `enabled`: whether the rule participates in evaluation.
- `when`: one or more conditions.
- `then`: actions on false -> true transition.
- `else`: actions on true -> false transition.

## Build Rule 1: Hardpoints Profile Toggle

Goal: set `Shift1` while hardpoints are deployed, clear it when retracted.

1. Open **Rules** and click **New Rule**.
2. Set `title` to `Combat Hardpoints`.
3. Add one condition:
   - `signal`: `hardpoints`
   - `op`: `eq`
   - `value`: `deployed`
4. Add a `then` action:
   - `vkb_set_shift`: `Shift1`
5. Add an `else` action:
   - `vkb_clear_shift`: `Shift1`
6. Save.
7. Deploy/retract hardpoints in-game and confirm the shift changes as expected.

Equivalent JSON:

```json
{
  "title": "Combat Hardpoints",
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

## Build Rule 2: Multi-Condition Flight State

Goal: enable `Shift2` only when in supercruise and flight assist is off.

1. Create a new rule named `SC + FA Off`.
2. Add condition block `all` with:
   - `fsd_status` `eq` `supercruise`
   - `flight_assist` `eq` `off`
3. Add `then` action: `vkb_set_shift` -> `Shift2`.
4. Add `else` action: `vkb_clear_shift` -> `Shift2`.
5. Save and test by toggling flight assist in supercruise.

## Build Rule 3: Any-Of Event Trigger

Goal: use one rule to react to either docking success or landing success.

1. Create a rule named `Dock Or Land`.
2. Add condition block `any` with:
   - `docking_state` `eq` `just_docked`
   - `docking_state` `eq` `just_landed`
3. Add `then` action:
   - `log`: `Docking or landing event detected`
4. Optional: add an `else` cleanup shift action if you set a shift in `then`.

Use `any` when one of several independent signals should activate the rule.

## Condition Design Patterns

- Use `all` for strict profiles (combat + target locked + shields up).
- Use `any` for catch-all triggers (multiple event variants).
- Use `in` when matching one signal against several accepted values.
- Prefer core-tier signals first; add detail-tier signals only when needed.

Signal details and value sets are in `docs/SIGNALS_REFERENCE.md`.

## Action Design Patterns

- Pair set/clear actions:
  - `then`: `vkb_set_shift`
  - `else`: `vkb_clear_shift`
- Keep one responsibility per rule title.
- Use `log` while building to validate condition timing.
- Avoid overlapping rules that fight over the same shift unless intentional.

## Safe Editing Workflow

1. Duplicate a working rule.
2. Rename the copy with `- test`.
3. Edit the duplicate.
4. Validate behavior.
5. Replace the original only after confirming transitions are correct.

This avoids accidental loss of known-good behavior.

## Troubleshooting

### Rule never triggers
- Confirm the rule is enabled.
- Confirm selected signal/operator/value are valid.
- Add a `log` action to verify transitions.
- Check whether the required signal is currently `unknown`.

### Rule triggers once but not again
- Remember rules are edge-triggered, not level-triggered.
- Ensure the condition returns to false before expecting another true transition.

### Shift state seems to stick
- Add a matching `else` action to clear the shift.
- Check for another rule that also sets the same shift.

### Value/operator not accepted
- Operator availability depends on signal type.
- Verify allowed values and type in `docs/SIGNALS_REFERENCE.md`.

## Final Checklist

- Rule title is descriptive.
- Rule is enabled.
- Condition logic matches intended `all`/`any` behavior.
- `then` and `else` actions are intentionally paired.
- In-game test confirms both transition directions.

## Related Docs

- `README.md`
- `docs/RULES_GUIDE.md`
- `docs/SIGNALS_REFERENCE.md`
- `docs/EDMC_EVENTS_CATALOG.md`
