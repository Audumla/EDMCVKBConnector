# Signal Catalog Editor - UI Layout

## Action Buttons (2-Column Layout)

The action buttons are organized in 2 columns with logical grouping:

```
┌─────────────────────────────────────────────────────────┐
│                      Actions                            │
├───────────────────────────┬─────────────────────────────┤
│  LEFT COLUMN              │  RIGHT COLUMN               │
├───────────────────────────┼─────────────────────────────┤
│  💾 Save (Ctrl+S)         │                             │
│  ⟲ Undo (Ctrl+Z)          │                             │
├───────────────────────────┴─────────────────────────────┤
│  ═══════════════════════════════════════════════════    │
├───────────────────────────┬─────────────────────────────┤
│  Rename Label             │  Change Tier                │
│  Rename Signal Key        │                             │
│  🗑️ Delete Signal          │                             │
├───────────────────────────┴─────────────────────────────┤
│  ═══════════════════════════════════════════════════    │
├───────────────────────────┬─────────────────────────────┤
│  Move to Category         │  📝 Edit Enum Values         │
│  Move to Subcategory      │  Merge Enums                │
│  Promote to Top Level     │                             │
│                           │  ──────────────────────     │
│                           │  Expand All                 │
│                           │  Collapse All               │
└───────────────────────────┴─────────────────────────────┘
```

## Button Groups

### File Operations (Top Row - Both Columns)
**Location:** Row 1-2, spans both columns
**Buttons:**
- **💾 Save (Ctrl+S)** - Save changes without popup
- **⟲ Undo (Ctrl+Z)** - Undo last operation

### Signal Editing (Left Column)
**Location:** Left column, rows 3-5
**Buttons:**
- **Rename Label** - Change signal display name
- **Rename Signal Key** - Change signal identifier
- **🗑️ Delete Signal** - Remove signal(s) from catalog

### Organization (Left Column)
**Location:** Left column, rows 6-8
**Buttons:**
- **Move to Category** - Assign to different category
- **Move to Subcategory** - Assign to subcategory
- **Promote to Top Level** - Remove from subcategory

### Tier Management (Right Column)
**Location:** Right column, row 3
**Buttons:**
- **Change Tier** - Change signal tier (core/detail/extended)

### Enum Operations (Right Column)
**Location:** Right column, rows 6-7
**Buttons:**
- **📝 Edit Enum Values** - Open enum editor dialog
- **Merge Enums** - Merge two enum signals

### View Operations (Right Column)
**Location:** Right column, rows 8-9
**Buttons:**
- **Expand All** - Expand all tree nodes
- **Collapse All** - Collapse all tree nodes

---

## Context Menu (Right-Click)

Right-click on any signal to access:

```
┌─────────────────────────┐
│  Rename Label           │
│  Rename Signal Key      │
│  Delete Signal          │
├─────────────────────────┤
│  Move to Category       │
│  Move to Subcategory    │
│  Promote to Top Level   │
├─────────────────────────┤
│  Change Tier            │
├─────────────────────────┤
│  Edit Enum Values       │
│  Merge Enums            │
└─────────────────────────┘
```

---

## Key Changes from Previous Version

### Added Features ✨
1. **💾 Save Button** - Quick save without popup confirmation
2. **🗑️ Delete Signal** - Remove unwanted signals with confirmation
3. **2-Column Layout** - Better space utilization
4. **Logical Grouping** - Operations grouped by function

### Layout Improvements 📐
- **Before:** Single column, 13 buttons stacked vertically
- **After:** Two columns, ~9 rows, better visual balance
- **Spacing:** Related operations grouped together
- **Width:** Each button expands to fill column (18 chars wide)

### Button Behavior 🎯

#### Save Button (💾)
- **No popup** on successful save
- Status bar shows: "✓ Saved: signals_catalog.json"
- Only shows error popup if save fails
- Still shows "No changes to save" in status bar

#### Delete Button (🗑️)
- **Confirmation dialog** before deletion
- Supports **multi-select** deletion
- Undoable with Ctrl+Z
- Shows count of deleted signals

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Save | **Ctrl+S** |
| Undo | **Ctrl+Z** |
| Cancel drag | **Escape** |
| Rename label | **Double-click** |

---

## Complete Feature List

### File Operations
✓ Save (with/without popup)
✓ Save As
✓ Undo (50-level stack)
✓ Auto-backup on save

### Signal Operations
✓ Rename label
✓ Rename signal key
✓ Delete signal(s) ← NEW!
✓ Move to category
✓ Move to subcategory
✓ Promote to top level
✓ Change tier
✓ Multi-select support

### Enum Operations
✓ Edit enum values dialog
✓ Add/rename/delete values
✓ Reorder values
✓ Move values between signals
✓ Merge enum signals

### View Operations
✓ Expand/collapse all
✓ Drag & drop (with threshold)
✓ Tree navigation
✓ Details pane
✓ Status bar feedback

---

## Design Principles

### Grouping Logic
1. **Most frequent operations** at the top
2. **Related operations** grouped together
3. **Destructive operations** (delete) have confirmation
4. **File operations** always accessible

### Visual Balance
- **2 columns** = better space utilization
- **Even distribution** = no wasted space
- **Logical flow** = left (signal ops) → right (view/enum ops)
- **Separators** = clear visual grouping

### User Experience
- **No unnecessary popups** (save is silent)
- **Clear feedback** (status bar messages)
- **Safety features** (confirmations, undo)
- **Consistent spacing** (2px padding)

---

## Comparison

### Before (Single Column)
```
Width: 20 chars
Height: ~27 rows (with separators)
Wasted space: Right side empty
Scroll: Required on smaller screens
```

### After (Two Columns)
```
Width: 18+18 = 36 chars (with padding)
Height: ~9 rows
Wasted space: Minimal
Scroll: Not needed on most screens
Visual balance: Much better
```

---

## Testing

**All 31 tests passing** ✓

New tests added:
- `test_delete_signal` - Single deletion
- `test_delete_multiple_signals` - Bulk deletion

```bash
python -m pytest test/test_signal_catalog_editor.py -v
# 31 passed in 0.09s ✓
```

---

**Last Updated:** 2026-02-17
**Layout Version:** 2.0
