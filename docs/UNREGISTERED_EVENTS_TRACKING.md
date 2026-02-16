# Unregistered Events Tracking

## Overview

The EDMC VKB Connector now includes a comprehensive system for tracking and managing unregistered game events. This feature helps identify events that are received by the plugin but are not yet registered in the signals catalog.

## What Gets Tracked

Events are automatically tracked when they meet these criteria:

1. **Event is received** - EDMC sends the event to the plugin through any source (journal, dashboard, CAPI, etc.)
2. **Event is NOT in the catalog** - The event type is not found in the signals_catalog.json
3. **Event type matches** - The event_type field is checked against all known events in the catalog

This helps identify:
- New game events that should be added to the catalog
- Events that may be renamed in newer Elite Dangerous patches
- Typos or inconsistencies in event naming

## Architecture

### Core Components

#### 1. UnregisteredEventsTracker (`unregistered_events_tracker.py`)

Manages the lifecycle of unregistered event tracking:

- **Initialization**: Creates or loads the tracker from disk
- **Event Tracking**: Records events not found in the catalog with full metadata
- **Persistence**: Saves all tracked events to `unregistered_events.json`
- **Catalog Validation**: Checks tracked events against the catalog periodically
- **Data Sanitization**: Removes sensitive fields (MarketID, etc.) before storage

**Key Methods**:
- `track_event(event_type, event_data, source)` - Record an unregistered event
- `refresh_against_catalog()` - Remove events now in catalog (returns count removed)
- `get_unregistered_events()` - Get sorted list of tracked events
- `clear_event(event_type)` - Remove specific event from tracking
- `clear_all_events()` - Clear entire tracking list

#### 2. SignalsCatalog Enhancements (`signals_catalog.py`)

Added new methods to extract all known events from the catalog:

- `get_all_known_events()` - Returns set of all event types mentioned in the catalog
  - Extracts from signal `derive` operations (op: "event")
  - Extracts from `sources.journal.events` lists
  - Extracts from enum value `recent_event` references
  - Extracts from `derive.cases[].when.event_name` references

- `has_signal(name)` - Alias for `signal_exists()` for consistency

#### 3. EventHandler Integration (`event_handler.py`)

The event handler now:

- Creates an `UnregisteredEventsTracker` instance during initialization
- Tracks every received event automatically
- Provides public methods to access and manage the tracker
- Updates the tracker's catalog reference when the catalog is reloaded

**New Methods**:
- `get_unregistered_events()` - Get list of all tracked events
- `get_unregistered_events_count()` - Get count of tracked events
- `refresh_unregistered_events_against_catalog()` - Refresh against catalog (removes matches)
- `clear_unregistered_event(event_type)` - Clear specific event
- `clear_all_unregistered_events()` - Clear all tracked events

#### 4. Plugin UI Integration (`load.py`)

Added "Unregistered Events" tab in EDMC preferences with:

- **Event Count Display** - Shows number of currently tracked events
- **View Details Button** - Opens detailed list of unregistered events
  - Shows event name, source, first/last seen timestamps, occurrence count
  - Displays complete sample event data in formatted JSON
  - Scrollable, readable list format
  
- **Refresh Button** - Manually check catalog for new matches
  - Removes events now found in catalog
  - Shows count of events removed
  
- **Clear All Button** - Delete entire tracking list
  - Prompts for confirmation before clearing
  - Cannot be undone (data goes to trash only if saved)

- **Auto-Refresh on Startup** - On plugin launch:
  - Automatically refreshes tracked events against the catalog
  - Removes any events that were added to the catalog since last run
  - Logs count of events removed

## File Format

Tracked events are stored in `unregistered_events.json` in the plugin directory:

```json
{
  "metadata": {
    "version": "1.0",
    "description": "Tracked unregistered game events - these events were received but not found in signals_catalog.json",
    "last_updated": 1631234567.89
  },
  "events": {
    "UnknownEvent": {
      "event_type": "UnknownEvent",
      "source": "journal",
      "first_seen": 1631234567.89,
      "last_seen": 1631234890.12,
      "occurrences": 3,
      "sample_data": {
        "event": "UnknownEvent",
        "timestamp": "2026-02-16T12:00:00Z",
        "field1": "value1"
      }
    }
  }
}
```

## Event Data Sanitization

To protect privacy and reduce file size, the following fields are removed from event data before storage:

- `MarketID`
- `OutfittingID`
- `ShipyardID`
- `StationServices`

All other fields are kept, with string values truncated to 1000 characters max.

## Integration with Rules

When a rule triggers on an event, the event is still potentially tracked by the unregistered events tracker:

- If the event is in the catalog → **Not tracked** (known event)
- If the event is NOT in the catalog → **Tracked** (unregistered event)

The rule matching doesn't affect tracking. Tracking is purely about catalog completeness.

## Workflow

### On Event Reception

```
Event Received → Filter by configured types → Track in event handler
                                           ↓
                                    Rule Engine (optional)
                                           ↓
                           Unregistered Events Tracker
                                           ↓
                           Is event in catalog? →
                              YES: Skip tracking
                              NO: Add to tracking list
```

### On Refresh

```
User clicks "Refresh" or app starts
                ↓
          Tracker.refresh_against_catalog()
                ↓
    For each tracked event:
      Is event now in catalog? →
        YES: Remove from tracking
        NO: Keep tracking
                ↓
          Update tracking file
          Display results
```

## Logging

The system produces logs at these levels:

- **WARNING**: When a new unregistered event is first detected
  - Example: `"Unregistered event detected: NewEvent from journal"`

- **INFO**: When events are removed after catalog refresh
  - Example: `"Event now in catalog, removing from tracking: NewEvent"`

- **INFO**: On startup, if events were removed during refresh
  - Example: `"Startup: 2 previously unregistered event(s) now in catalog"`

## Usage Examples

### From Python Code

```python
# In event handler or other code:
if event_handler:
    # Get unregistered event count
    count = event_handler.get_unregistered_events_count()
    
    # Get detailed list
    events = event_handler.get_unregistered_events()
    for event in events:
        print(f"{event['event_type']}: {event['occurrences']} occurrences")
    
    # Refresh against catalog
    removed = event_handler.refresh_unregistered_events_against_catalog()
    
    # Clear specific event
    event_handler.clear_unregistered_event("OldEvent")
    
    # Clear all
    event_handler.clear_all_unregistered_events()
```

### From UI

Users interact through the "Unregistered Events" tab in EDMC preferences:

1. **View Details** - See what events are being tracked and when they were seen
2. **Refresh** - Check if any tracked events have been added to the catalog
3. **Clear All** - Start fresh with a clean tracking list

## Technical Details

### Catalog Event Extraction

The implementation extracts event names from multiple places in the catalog:

1. **Signal Derivation**: `signal.derive.op == "event"` → `derive.event_name`
2. **Journal Sources**: `signal.sources.journal.events` → list of event types
3. **Enum Recent Events**: `signal.values[].recent_event` → event references
4. **Enum Derivation Cases**: `signal.derive.cases[].when.event_name` → event references in conditional logic

Example: The "docking_request_state" signal extracts events:
- DockingRequested (from enum values)
- DockingGranted (from enum values)
- DockingDenied (from enum values)
- DockingCancelled (from enum values)
- DockingTimeout (from enum values)

### Performance Considerations

- **Event Tracking**: O(1) per event (hash table lookup)
- **Catalog Refresh**: O(n) where n = number of tracked events
- **File I/O**: Only when events are added/removed/cleared
- **Memory**: Minimal - only tracked events stored in memory
- **Startup**: On startup, reads JSON file once and refreshes against catalog in parallel background thread

## Future Enhancements

Potential improvements to the tracking system:

1. **Export/Import** - Allow users to export tracked events for sharing
2. **Filtering** - Filter events by source, date range, or pattern
3. **Statistics** - Show trends in unregistered events over time
4. **Batch Operations** - Bulk clear or manage multiple events
5. **Web Interface** - Remote monitoring of unregistered events
6. **Notification** - Alert users when new unregistered events appear

## Troubleshooting

### Events not being tracked?

1. Check if event is already in the catalog:
   - Use "View Details" to see what's being tracked
   - Search signals_catalog.json for event type

2. Check if event is being filtered:
   - Look at `event_types` config - if set, only those events are processed
   - Check logs for filter rejections

3. Look for errors in logs:
   - Check EDMC log file for errors in tracking code

### Tracker file not found?

- File is created on first tracked event
- Until then, no tracking file exists
- This is normal behavior

### Events disappearing from list?

- Events are removed when they're added to the catalog and you refresh
- Check "Unregistered Events" tab for refresh results
- Use "Clear All" to intentionally clear tracking
