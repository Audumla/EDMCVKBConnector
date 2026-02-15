# Visual Rule Editor Guide

The EDMC VKB Connector now includes a visual rule editor that provides a user-friendly interface for creating and editing rules without manually writing JSON.

## Overview

The visual rule editor is accessible from the EDMC preferences window under the VKB Connector plugin settings. It replaces the previous text-based JSON editor with structured forms for:

- When conditions (source, event, condition blocks)
- Then actions (shift flags, log statements)
- Else actions (shift flags, log statements)

## Opening the Visual Editor

1. Open EDMC and go to **File > Settings** (or press `F10`)
2. Navigate to the **Plugins** tab
3. Find the **VKB Connector** section
4. In the **Rules Editor** section, select a rule from the list
5. Click the **Visual Editor** button

## Rule Editor Interface

The visual editor dialog contains:

### Header Section
- **Rule ID**: A unique identifier for the rule
- **Enabled**: Checkbox to enable/disable the rule

### When Conditions Tab

Configure when the rule should match:

#### Source Filter
- Select the data source: `journal`, `dashboard`, `capi`, `capi_fleetcarrier`, or `any`
- Leave empty for no source filtering

#### Event Filter
- Select the specific event to match (filtered by source)
- Examples: `Status`, `FSDJump`, `Docked`
- Leave empty for no event filtering

#### Condition Blocks
- **ALL Blocks**: Every condition must match (AND logic)
- **ANY Blocks**: At least one condition must match (OR logic)

Each condition block can be one of:

1. **Flags**: Match dashboard status flags
   - Operators: `all_of`, `any_of`, `none_of`, `equals`
   - Example: Match when landing gear is down

2. **Flags2**: Match extended dashboard flags
   - Operators: same as Flags
   - Example: Match when on foot

3. **GUI Focus**: Match current UI panel focus
   - Operators: `equals`, `in`, `changed_to`
   - Example: Match when galaxy map is open

4. **Field**: Match arbitrary event fields
   - Operators: `exists`, `equals`, `in`, `contains`, `gt`, `gte`, `lt`, `lte`, `changed`, `changed_to`
   - Example: Match when fuel level is low

### Then Actions Tab

Configure actions when the rule matches:

#### Log Statement
- Enter a message to log (optional)
- Only one log statement per Then block

#### VKB Shift Flags
For each shift flag (Shift1, Shift2, Subshift1-7):
- **Set**: Enable the flag
- **Clear**: Disable the flag
- **Unchanged**: Don't modify the flag

### Else Actions Tab

Configure actions when the rule does NOT match:
- Same structure as Then Actions
- Useful for toggling flags on/off

### JSON Preview Tab

View the generated JSON for the rule:
- Click **Refresh Preview** to update after making changes
- Useful for understanding the rule structure
- Can be copied for manual editing if needed

## Event Configuration

The editor uses `events_config.json` which contains:

### Sources
- `journal`: Events from Elite Dangerous journal files
- `dashboard`: Real-time status updates
- `capi`: Commander API data
- `capi_fleetcarrier`: Fleet carrier data

### Events
54 pre-configured events including:
- **Travel**: Location, FSDJump, Docked, Undocked
- **Ship**: Loadout, LaunchSRV, DockSRV
- **Combat**: Bounty, HullDamage, ShieldState
- **Trading**: MarketBuy, MarketSell, MaterialCollected
- **Missions**: MissionAccepted, MissionCompleted
- **Odyssey**: Embark, Disembark, BookTaxi
- **Exploration**: Scan, FSSDiscoveryScan, CodexEntry

### Condition Types
- **Flags**: Dashboard status flags (32 flags)
- **Flags2**: Extended flags (17 flags)
- **GUI Focus**: UI panel states (12 states)
- **Field**: Generic field matching

## Example: Creating a "Landing Gear Down" Rule

1. Click **New Rule** to create a new rule
2. Click **Visual Editor**
3. Set **Rule ID** to `landing_gear_down`
4. In **When Conditions**:
   - Set **Source** to `dashboard`
   - Set **Event** to `Status Update (Status)`
   - Click **+ Add ALL Block**
   - Select **Condition Type**: `flags`
   - Select **Operator**: `all_of`
   - Select `FlagsLandingGearDown` from the list
5. In **Then Actions**:
   - Set **Subshift3** to `Set`
6. In **Else Actions**:
   - Set **Subshift3** to `Clear`
7. Click **Save**

This rule will:
- Monitor dashboard status updates
- Set Subshift3 when landing gear is down
- Clear Subshift3 when landing gear is up

## Tips

- Use **ALL blocks** when you need multiple conditions to be true simultaneously
- Use **ANY blocks** when you want to match if any condition is true
- Combine ALL and ANY blocks for complex logic
- Use the JSON preview to verify your rule structure
- Test rules by enabling/disabling them with the checkbox
- Use descriptive Rule IDs to easily identify rules

## Fallback to JSON Editor

The text-based JSON editor is still available:
1. Select a rule
2. Edit the JSON in the text area
3. Click **Save JSON**

This is useful for:
- Advanced rule patterns not yet supported by the visual editor
- Bulk editing rules
- Copying rules from documentation

## Updating Events Configuration

To add new events or modify existing ones, edit `events_config.json` in the plugin directory. The file structure is:

```json
{
  "sources": [...],
  "events": [
    {
      "source": "journal",
      "event": "EventName",
      "title": "Human Readable Title",
      "description": "Description of the event",
      "category": "Category"
    }
  ],
  "condition_types": [...],
  "shift_flags": [...]
}
```

After editing, restart EDMC for changes to take effect.
