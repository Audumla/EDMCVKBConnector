# Drag-and-Drop State Management Fix

## Problem

When collapsing or expanding categories in the signal catalog editor, the application would sometimes mistakenly trigger drag-and-drop operations, attempting to move items into the collapsed/expanded category.

### Root Cause

The drag state (`drag_data`) was being set on every mouse click (`<Button-1>`), including when clicking to collapse/expand a category. The state wasn't always properly cleared, leading to:

1. Click to expand/collapse → `drag_data` is set
2. No actual drag occurs (mouse doesn't move)
3. `drag_data` remains set
4. Next interaction could trigger an unintended move operation

## Solution

Implemented multiple safeguards to prevent false drag operations:

### 1. **Drag Distance Threshold** (5 pixels)
```python
self.drag_threshold = 5  # Minimum pixels to move before considering it a drag
```

The drag operation only activates if the mouse moves more than 5 pixels from the initial click position. This prevents collapse/expand clicks from being interpreted as drags.

### 2. **Proper State Clearing**
- `drag_data` is now **always** cleared in `on_tree_drop()`, even when the operation is invalid or cancelled
- State is cleared **before** early returns to prevent leaking state

### 3. **Tree Toggle Event Handling**
```python
self.tree.bind('<<TreeviewOpen>>', self.on_tree_toggle)
self.tree.bind('<<TreeviewClose>>', self.on_tree_toggle)
```

When a category is expanded or collapsed, the drag state is immediately cleared to prevent any pending drag operations.

### 4. **ESC Key Cancellation**
```python
self.root.bind('<Escape>', self.cancel_drag)
```

Users can now press ESC to cancel any ongoing drag operation, clearing all drag state and visual feedback.

## Changes Made

### Modified Files
- [scripts/signal_catalog_editor.py](../scripts/signal_catalog_editor.py)
  - Added `drag_threshold` attribute (5 pixels)
  - Enhanced `on_tree_drag()` to check distance threshold
  - Refactored `on_tree_drop()` to always clear state
  - Added `on_tree_toggle()` handler for expand/collapse events
  - Added `cancel_drag()` method for ESC key
  - Added event bindings for `<<TreeviewOpen>>` and `<<TreeviewClose>>`
  - Added ESC key binding

- [test/test_signal_catalog_editor.py](../test/test_signal_catalog_editor.py)
  - Added `TestDragAndDropState` test class
  - Added tests for drag threshold behavior
  - Added tests for state clearing

## How It Works

### Normal Click (Collapse/Expand)
1. User clicks category → `drag_data` set
2. Mouse doesn't move (or moves < 5px)
3. `on_tree_drop()` called
4. Distance check fails → treated as simple click
5. `drag_data` cleared
6. Tree expands/collapses normally ✓

### Actual Drag Operation
1. User clicks and holds → `drag_data` set
2. Mouse moves > 5px → drag starts
3. Visual feedback shows drop target
4. User releases mouse → `on_tree_drop()` called
5. Distance check passes → drag operation executed
6. `drag_data` cleared ✓

### ESC Key Cancellation
1. User starts dragging
2. User presses ESC
3. `cancel_drag()` called
4. All drag state and visual feedback cleared
5. Status bar shows "Drag cancelled" ✓

### Tree Toggle
1. User expands/collapses category
2. `<<TreeviewOpen>>` or `<<TreeviewClose>>` event fired
3. `on_tree_toggle()` called
4. All drag state immediately cleared ✓

## Testing

All 18 editor tests pass, including 3 new tests for drag-and-drop state management:
- `test_drag_threshold` - Verifies small movements don't trigger drags
- `test_drag_threshold_exceeded` - Verifies actual drags work
- `test_state_clearing` - Verifies state is properly cleared

## User Experience Improvements

✓ **No more accidental moves** when collapsing/expanding categories
✓ **Responsive feedback** - cursor changes only during actual drags
✓ **ESC to cancel** - users can abort drag operations
✓ **Predictable behavior** - consistent 5-pixel threshold
✓ **Visual clarity** - drop targets only highlight during valid drags

---

**Fixed**: 2026-02-17
**Status**: All tests passing ✓
