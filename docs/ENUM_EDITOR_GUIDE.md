# Enum Editor Guide

The Signal Catalog Editor now includes comprehensive enum value editing capabilities, allowing you to manage enum values within signals and even merge entire enum signals together.

## Features

### 1. **Edit Enum Values Dialog** 📝

Opens a dedicated dialog for managing enum values within a signal.

**How to Open:**
- Select an enum signal in the tree
- Click **"📝 Edit Enum Values"** button
- OR right-click → **"Edit Enum Values"**

**Available Operations:**

#### Add New Value
- Click **"Add Value"**
- Enter value ID (e.g., `new_option`)
- Enter label (e.g., "New Option")
- Automatically detects duplicates

#### Rename Value
- Select a value in the list
- Click **"Rename Value"** or double-click
- Edit both the value ID and label

#### Delete Value
- Select a value in the list
- Click **"Delete Value"**
- Confirms before deletion

#### Reorder Values
- **Move Up** (▲) - Move selected value up in the list
- **Move Down** (▼) - Move selected value down in the list
- Useful for organizing enum options

#### Move Value to Another Signal
- Select a value
- Click **"Move Value To..."**
- Choose target enum signal
- Value is removed from source and added to target
- Great for reorganizing related options

---

### 2. **Merge Enum Signals** 🔀

Combine two enum signals into one by moving all values from a source signal to a target signal.

**How to Use:**
- Click **"Merge Enums"** button
- OR right-click → **"Merge Enums"**

**Merge Process:**
1. Select **source signal** (will be deleted after merge)
2. Select **target signal** (receives all values)
3. Click **"Merge"**
4. All values from source are moved to target
5. Duplicate values are automatically filtered
6. Source signal is deleted

**Use Cases:**
- Consolidating related enum signals
- Removing duplicate signals with similar values
- Reorganizing signal structure

---

## Example Workflows

### Workflow 1: Adding Values to Combat State

1. Select `combat_state` signal
2. Click **"Edit Enum Values"**
3. Click **"Add Value"**
4. Enter:
   - Value ID: `retreating`
   - Label: "Retreating from combat"
5. Value appears in list
6. Close dialog
7. Changes saved with Ctrl+S

### Workflow 2: Moving Values Between Signals

You have:
- `ship_status` with values: `clean`, `wanted`, `hostile`
- `legal_state` with values: `clean`, `illegal_cargo`

You want to move `wanted` and `hostile` to `legal_state`:

1. Select `ship_status`
2. Click **"Edit Enum Values"**
3. Select `wanted` value
4. Click **"Move Value To..."**
5. Select `legal_state`
6. Repeat for `hostile`
7. Both values now in `legal_state`

### Workflow 3: Merging Duplicate Signals

You have:
- `travel_state` with values: `docked`, `in_space`, `supercruise`
- `ship_location` with values: `station`, `space`, `hyperspace`

To merge them:

1. Click **"Merge Enums"**
2. Source: `ship_location` (will be deleted)
3. Target: `travel_state` (keeps all values)
4. Click **"Merge"**
5. `travel_state` now has all values
6. `ship_location` is deleted

---

## UI Elements

### Enum Editor Dialog

```
┌─────────────────────────────────────────┐
│  Signal: combat_state                   │
│  Type: enum                             │
├─────────────────────────────────────────┤
│  Enum Values                 Actions    │
│  ┌──────────────────┐       ┌────────┐ │
│  │ none → None      │       │  Add   │ │
│  │ peaceful → Peace │       │ Rename │ │
│  │ combat → Combat  │       │ Delete │ │
│  │ ...              │       ├────────┤ │
│  │                  │       │ Move   │ │
│  │                  │       │  To... │ │
│  │                  │       ├────────┤ │
│  └──────────────────┘       │   ▲    │ │
│                              │   ▼    │ │
│                              └────────┘ │
│                           [Close]       │
└─────────────────────────────────────────┘
```

### Merge Dialog

```
┌─────────────────────────────────────────┐
│  Merge Enum Signals                     │
├─────────────────────────────────────────┤
│  Merge two enum signals by moving all  │
│  values from source to target           │
│                                         │
│  Source Signal (will be deleted):      │
│  [Select signal...                  ▼] │
│                                         │
│  Target Signal (receives all values):  │
│  [Select signal...                  ▼] │
│                                         │
│          [Merge]     [Cancel]           │
└─────────────────────────────────────────┘
```

---

## Data Structure

### Enum Value Format

Each enum value in the catalog follows this structure:

```json
{
  "value": "option_name",
  "label": "Display Label",
  "recent_event": "OptionalEventName"
}
```

**Fields:**
- `value` (required) - Internal identifier, must be unique within signal
- `label` (required) - User-friendly display text
- `recent_event` (optional) - Associated EDMC event that triggers this value

### Example Enum Signal

```json
{
  "combat_state": {
    "type": "enum",
    "title": "Combat State",
    "ui": {
      "label": "Combat status",
      "category": "Combat",
      "tier": "core"
    },
    "values": [
      {"value": "none", "label": "None"},
      {"value": "peaceful", "label": "Peaceful"},
      {"value": "under_attack", "label": "Under Attack", "recent_event": "UnderAttack"},
      {"value": "got_bounty", "label": "Bounty Received", "recent_event": "Bounty"}
    ]
  }
}
```

---

## Best Practices

### Value Naming Conventions

**Value IDs:**
- Use snake_case: `option_name` ✓
- Be descriptive: `landing_gear_deployed` ✓
- Avoid abbreviations unless common: `fsd_charging` ✓
- No spaces or special chars: `option name` ✗

**Labels:**
- Use Title Case: "Option Name" ✓
- Be concise but clear: "Landing Gear Deployed" ✓
- Include context if needed: "FSD Charging" ✓

### When to Merge Signals

**Good candidates for merging:**
- Signals with overlapping meanings
- Duplicate signals created by mistake
- Signals that track the same game state differently

**Keep separate if:**
- Signals serve different purposes
- Used by different rule sets
- Values have semantic differences

### Organizing Values

**Order values logically:**
1. `none` or default state first
2. Common states next
3. Rare/special states last
4. Group related states together

**Example:**
```
✓ Good Order:
  - none
  - docked
  - landed
  - in_space
  - supercruise
  - hyperspace

✗ Poor Order:
  - hyperspace
  - none
  - docked
  - supercruise
  - in_space
  - landed
```

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Save changes | Ctrl+S |
| Undo | Ctrl+Z |
| Close dialog | Escape |
| Double-click value | Edit/Rename |

---

## Safety Features

### Undo Support ✓
All enum operations are undoable with Ctrl+Z (up to 50 operations)

### Duplicate Detection ✓
- Automatically prevents adding duplicate value IDs
- Warns when attempting to create duplicates
- Filters duplicates during merge operations

### Confirmation Dialogs ✓
- Delete operations require confirmation
- Merge operations show warning before deleting source
- Prevents accidental data loss

### Auto-Backup ✓
- Every save creates a `.json.backup` file
- Previous version always preserved
- Recovery possible if needed

---

## Testing

**29 comprehensive tests** cover enum editing:
- Adding/renaming/deleting values
- Moving values between signals
- Reordering values
- Merging signals
- Duplicate handling
- Edge cases

Run tests:
```bash
python -m pytest test/test_signal_catalog_editor.py::TestEnumEditing -v
python -m pytest test/test_signal_catalog_editor.py::TestEnumMerge -v
```

---

## Troubleshooting

### "Signal is not an enum type"
- Selected signal must have `"type": "enum"`
- Check signal definition in JSON
- Only enum signals can use enum editor

### "No other enum signals found"
- Need at least 2 enum signals to move values
- Create additional enum signals first
- Or use the main editor to change signal type

### Changes not saving
- Click "Close" on enum dialog first
- Then use Ctrl+S or "Save" button in main editor
- Check for unsaved changes indicator

### Merge not working
- Ensure source and target are different
- Both must be enum type signals
- Confirm the merge operation when prompted

---

## Advanced Tips

### Bulk Reorganization
1. Export values to text editor
2. Rearrange as needed
3. Use Add/Delete to recreate structure
4. Or edit JSON directly (advanced users)

### Template Creation
Create a "template" enum signal with common values, then copy values to new signals using the move operation.

### Version Control
Before major restructuring:
1. Save current catalog
2. Commit to git (if using)
3. Make changes
4. Test thoroughly
5. Rollback if needed using backup

---

**Need Help?**
- Check tooltips in the dialog
- Status bar shows operation results
- Undo with Ctrl+Z if something goes wrong
- Backup file always available for recovery

---

**Last Updated:** 2026-02-17
**Feature Version:** 2.0
