# V3 Rule Editor UI - User Guide

## Overview

The v3 Rule Editor is a catalog-driven visual interface for creating and editing VKB shift rules in Elite Dangerous Market Connector. It provides an intuitive way to create complex rules without writing JSON manually.

## Key Features

### 🎯 Catalog-Driven
- All signals, operators, and enum values come from `signals_catalog.json`
- No hardcoded lists means automatic updates when catalog changes
- Type-safe value selection based on signal types

### 🎨 Two-Tier Signal Visibility
- **Common (🌟 Core)**: Most frequently used signals
- **Common + More**: Includes detailed/advanced signals
- Toggle between tiers to reduce clutter

### ⚡ Edge-Triggered Actions
- **Then**: Executes when condition becomes TRUE (false → true)
- **Else**: Executes when condition becomes FALSE (true → false)
- No repeated firing while condition state is stable

### ✅ Inline Validation
- Real-time validation of all fields
- Clear error messages before save
- Prevents creating invalid rules

## UI Structure

### Rules List View

The main view shows all your rules with:
- **Enable toggle**: Quickly enable/disable rules
- **Title**: Rule name in bold
- **Summary**: Shows condition count and action count
- **Actions**: Edit, Duplicate, Delete buttons

**Top Bar:**
- `➕ New Rule` button to create new rules

**Empty State:**
When no rules exist, helpful hints guide you to create your first rule.

### Rule Editor View

The editor has several sections:

#### 1. Basic Information
- **Title*** (required): Name your rule
- **Enabled**: Toggle to enable/disable this rule
- **ID** (read-only): Shows the rule's generated ID if it exists

#### 2. When (Conditions)
Build conditions that determine when your rule fires.

**Signal Visibility Toggle:**
- 🌟 Common only - Shows core signals (recommended for beginners)
- 🌟 Common + More - Shows all signals including advanced ones

**Two Condition Groups:**

**✓ All of these** (`when.all`)
- ALL conditions must be true for the rule to match
- Use for AND logic: "gear down AND docked"

**⚡ Any of these** (`when.any`)
- AT LEAST ONE condition must be true
- Use for OR logic: "in galaxy map OR in system map"

**If both groups have conditions:**
- Rule matches when (ALL conditions) AND (AT LEAST ONE any condition)

**Each Condition Row Has:**
1. **Signal dropdown**: Choose what to check
   - Organized by category (HUD, Docking, Combat, etc.)
   - Shows human-readable labels
   - Filter by tier with toggle above
   
2. **Operator dropdown**: How to compare
   - For bool signals: `=` Equals, `≠` Not equal
   - For enum signals: `=` Equals, `≠` Not equal, `∈` In list, `∉` Not in list
   
3. **Value control**: What to compare against
   - Bool signals: True/False dropdown
   - Enum signals: Dropdown with available values (e.g., "Up", "Down" for landing gear)
   
4. **🗑️ Remove button**: Delete this condition

**➕ Add condition button**: Add more conditions to the group

**Empty State Hint:**
"💡 Add conditions to control when this rule fires"

#### 3. Then (Actions when it becomes true)

**Label:** "Then (when it becomes true) - fires on false → true"

Actions to execute when the conditions transition from FALSE to TRUE.

**Each Action Row Has:**
1. **Action type dropdown**: Choose action type
   - `vkb_set_shift`: Activate VKB shift layers
   - `vkb_clear_shift`: Deactivate VKB shift layers
   - `log`: Write a log message

2. **Action-specific controls:**
   - For shift actions: Checkboxes for tokens (Shift1, Shift2, Subshift1-7)
   - For log actions: Text field for message

3. **🗑️ Remove button**: Delete this action

**➕ Add action button**: Add more actions

**Empty State Hint:**
"💡 Add actions to execute when conditions become true"

#### 4. Else (Actions when it becomes false)

**Label:** "Else (when it becomes false) - fires on true → false"

Actions to execute when the conditions transition from TRUE to FALSE.

Same structure as Then section, but fires on the opposite transition.

**Empty State Hint:**
"💡 Add actions to execute when conditions become false"

#### 5. Save/Cancel Buttons
- **💾 Save**: Validate and save the rule
- **Cancel**: Discard changes and return to list

## Common Workflows

### Creating a Simple Rule

**Example:** "Set Shift1 when landing gear is down"

1. Click `➕ New Rule`
2. Set title: "Landing Gear Down"
3. In "All of these":
   - Click `➕ Add condition`
   - Signal: "Docking: Landing gear"
   - Operator: "= Equals"
   - Value: "Down"
4. In "Then" section:
   - Click `➕ Add action`
   - Type: `vkb_set_shift`
   - Check: `Shift1`
5. In "Else" section:
   - Click `➕ Add action`
   - Type: `vkb_clear_shift`
   - Check: `Shift1`
6. Click `💾 Save`

### Creating a Complex Rule

**Example:** "Set Subshift3 when in galaxy map OR system map, but only if docked"

1. Create new rule
2. Title: "Map Views While Docked"
3. In "All of these":
   - Add: "Docking: Docking state" = "Docked"
4. In "Any of these":
   - Add: "HUD: Focused screen" = "Galaxy map"
   - Add: "HUD: Focused screen" = "System map"
5. In "Then":
   - Add `vkb_set_shift` with `Subshift3`
6. In "Else":
   - Add `vkb_clear_shift` with `Subshift3`
7. Save

### Duplicating a Rule

1. In rules list, find the rule you want to copy
2. Click `📋 Duplicate`
3. A copy is created with "(copy)" appended to title
4. Click `✏️ Edit` on the copy to modify it
5. Change title and adjust conditions/actions as needed
6. Save

### Editing an Existing Rule

1. Click `✏️ Edit` on the rule
2. Make your changes
3. Click `💾 Save` to keep changes
4. Or `Cancel` to discard changes

### Deleting a Rule

1. Click `🗑️ Delete` on the rule
2. Confirm in the dialog
3. Rule is permanently removed

## Signal Types

### Boolean Signals
Simple true/false values.

**Examples:**
- `gear_down`: Is landing gear deployed?
- `weapons_out`: Are hardpoints deployed?
- `docked`: Is ship docked?

**Operators:** Equals, Not equal

**Values:** True, False

### Enum Signals
Multi-value states with human-readable labels.

**Examples:**
- `gui_focus`: Which screen is focused (NoFocus, InternalPanel, GalaxyMap, etc.)
- `landing_gear`: Gear state (Up, Down)
- `hardpoints`: Hardpoint state (Retracted, Deployed)

**Operators:** 
- Equals: Value matches exactly
- Not equal: Value doesn't match
- In list: Value is one of several (use for OR conditions)
- Not in list: Value is not any of several

**Values:** Dropdown of available states with labels

## Action Types

### vkb_set_shift
Activates VKB shift layers.

**Available Tokens:**
- **Shift1, Shift2**: Main shift layers (bits 0-1)
- **Subshift1-7**: Sub-shift layers (bits 0-6)

**Use Case:** Turn on shift layers when conditions are met.

**Example:** Set Shift1 when hardpoints are deployed.

### vkb_clear_shift
Deactivates VKB shift layers.

**Available Tokens:** Same as vkb_set_shift

**Use Case:** Turn off shift layers when conditions are no longer met.

**Example:** Clear Shift1 when hardpoints are retracted.

### log
Writes a message to the EDMC log.

**Use Case:** Debug rules or track when they fire.

**Example:** Log "Entered combat mode" when HUD changes to combat.

## Validation Rules

The editor validates your rules before saving:

### Title
- ❌ Cannot be empty
- ✅ Must have at least one character

### Conditions
- ❌ All conditions must have a signal selected
- ❌ All conditions must have an operator selected
- ❌ All conditions must have a value

### Actions
- ❌ All actions must have a type selected
- ❌ Shift actions must have at least one token checked
- ❌ Log actions must have a non-empty message

**If validation fails:**
A dialog shows all errors. Fix them and try saving again.

## Understanding Edge-Triggered Behavior

Rules use **edge-triggered** evaluation to prevent spam:

### What is Edge-Triggering?

Actions only execute when the condition **changes state**, not while it stays stable.

**Example Timeline:**
```
State:    false → true → true → true → false → false → true
Actions:  -      THEN    -      -      ELSE     -      THEN
```

### Why This Matters

**Without edge-triggering:**
- Actions would fire repeatedly every check
- VKB would receive constant updates
- Log would fill with duplicate messages

**With edge-triggering:**
- Actions fire only on transitions
- VKB gets clean state changes
- Log shows clear event boundaries

### Practical Example

**Rule:** "Set Shift1 when docked"

**Without edge-triggering:**
```
Docking...
→ Set Shift1
→ Set Shift1 (again)
→ Set Shift1 (again)
→ Set Shift1 (again)
...hundreds more times...
```

**With edge-triggering:**
```
Docking...
→ Set Shift1 (once)
...
Undocking...
→ Clear Shift1 (once)
```

### Designing Rules for Edge-Triggering

**Good Practices:**
- Use Then for "entering a state"
- Use Else for "leaving a state"
- Don't rely on repeated execution
- Think in transitions, not states

**Example:**
```
Rule: "Galaxy Map Active"

Then (becomes true):
  - Set Subshift5
  - Log "Opened galaxy map"

Else (becomes false):
  - Clear Subshift5
  - Log "Closed galaxy map"
```

## Tips & Best Practices

### Organization

**Use Clear Titles:**
- ✅ "Combat Mode - Hardpoints & Shields"
- ❌ "Rule 3"

**Group Related Rules:**
Use prefixes: "Combat -", "Docking -", "Travel -"

### Signal Selection

**Start with Core Signals:**
- Core tier has the most common signals
- Reduces dropdown clutter
- Switch to "More" only when needed

**Check Multiple Signals:**
Sometimes multiple signals describe the same state:
- Bool: `gear_down` = true
- Enum: `landing_gear` = "Down"

Choose the one that reads better in your context.

### Condition Logic

**All vs Any:**
- **All**: Use for AND logic (must satisfy everything)
- **Any**: Use for OR logic (one of several options)
- **Both**: Complex logic: (A AND B) AND (C OR D)

**Keep It Simple:**
- Start with one or two conditions
- Add more only if needed
- Complex rules are harder to debug

### Action Design

**Shift Layer Planning:**
- Reserve Shift1-2 for major modes
- Use Subshift1-7 for specific states
- Document your layer assignments

**Complementary Actions:**
- If Then sets a shift, Else should clear it
- Maintain symmetry for clean state management

**Logging:**
- Add log actions to debug rules
- Remove them once the rule works correctly

### Testing Rules

1. **Save and reload:** Ensure rule persists correctly
2. **Check the log:** Verify actions fire as expected
3. **Test edge cases:** What happens at boundaries?
4. **Verify VKB:** Check that correct shifts activate

### Troubleshooting

**Rule doesn't fire:**
- Check all conditions are correct
- Verify signal values in log
- Ensure rule is enabled
- Check for typos in condition values

**Rule fires too often:**
- Edge-triggering should prevent this
- Check for multiple rules with overlapping conditions
- Verify you're using Then/Else correctly

**Validation errors:**
- Read all error messages carefully
- Fix each issue one by one
- Common: Missing signal, operator, or value

**Catalog errors:**
- Ensure `signals_catalog.json` exists in plugin directory
- Check JSON is valid
- Verify catalog version is 3
- See EDMC log for detailed error

## Advanced Topics

### Collision Handling

When two rules have the same title, IDs are generated differently:
- First: `landing-gear`
- Second: `landing-gear-2`
- Third: `landing-gear-3`

This ensures unique IDs even with duplicate titles.

### Round-Tripping Unknown Items

If a rule references signals/operators not in the current catalog:
- They are preserved in the rule
- Shown as "Unknown signal" in UI
- You must fix them before saving changes

This prevents accidental data loss when catalog is incomplete.

### File Format

Rules are saved in v3 JSON format:

```json
[
  {
    "id": "landing-gear-down",
    "title": "Landing Gear Down",
    "enabled": true,
    "when": {
      "all": [
        {
          "signal": "landing_gear",
          "op": "eq",
          "value": "down"
        }
      ],
      "any": []
    },
    "then": [
      {
        "vkb_set_shift": ["Shift1"]
      }
    ],
    "else": [
      {
        "vkb_clear_shift": ["Shift1"]
      }
    ]
  }
]
```

## Keyboard Shortcuts

Currently, the editor doesn't have keyboard shortcuts. Use mouse/trackpad to navigate.

## Accessibility

The editor uses standard tkinter widgets which should work with screen readers, but full accessibility testing has not been performed.

## Getting Help

**In EDMC:**
- Check the log for error messages
- Enable debug mode for verbose logging

**Documentation:**
- See `V3_SCHEMA_REFERENCE.md` for technical details
- See `IMPLEMENTATION_COMPLETE_V3.md` for implementation info

**Support:**
- Report issues on GitHub
- Include EDMC log excerpt
- Describe steps to reproduce

---

**Version:** 3.0  
**Last Updated:** 2026-02-15  
**Compatible with:** signals_catalog.json version 3
