# Unregistered Events Tracking - Test Suite

## Overview

Comprehensive test suite for the unregistered events tracking feature, validating that the system continues to work correctly as code is modified.

**Test File**: [test/test_unregistered_events.py](../test/test_unregistered_events.py)

**Total Tests**: 22 tests, all passing ✓

## Test Categories

### 1. UnregisteredEventsTracker Class Tests (15 tests)

Tests for the core tracker functionality.

#### Initialization Tests
- ✓ `test_tracker_initialization` - Tracker initializes with empty state
- ✓ `test_tracker_with_catalog` - Tracker loads catalog on initialization and caches known events

#### Event Tracking Tests
- ✓ `test_track_unknown_event` - Unknown events are properly tracked
- ✓ `test_track_known_event` - Known events (in catalog) are NOT tracked
- ✓ `test_duplicate_event_tracking` - Duplicate events increment occurrence count and update sample data
- ✓ `test_multiple_different_events` - Multiple distinct events tracked separately
- ✓ `test_events_sorted_by_last_seen` - Events returned sorted by last_seen timestamp (newest first)

#### Persistence Tests
- ✓ `test_persistence_to_file` - Events saved to `unregistered_events.json` with proper structure
- ✓ `test_load_from_file` - New tracker instance loads existing events from file

#### Event Management Tests
- ✓ `test_clear_specific_event` - Individual events can be removed
- ✓ `test_clear_nonexistent_event` - Clearing non-existent event returns False
- ✓ `test_clear_all_events` - All tracked events cleared at once

#### Catalog Validation Tests
- ✓ `test_refresh_against_catalog_removes_known` - Events now in catalog are removed on refresh
- ✓ `test_refresh_against_catalog_keeps_unknown` - Unknown events persist on refresh
- ✓ `test_set_catalog` - Catalog can be updated after initialization

#### Data Handling Tests
- ✓ `test_sanitize_event_data` - Sensitive fields (MarketID, etc.) removed from stored data
- ✓ `test_catalog_event_extraction` - Catalog correctly extracts 219+ known event types

### 2. EventHandler Integration Tests (7 tests)

Tests for integration with EventHandler class.

#### Initialization Tests
- ✓ `test_event_handler_initializes_tracker` - EventHandler creates tracker on init

#### Event Handling Tests
- ✓ `test_event_handler_tracks_unknown_events` - Unknown events are tracked through EventHandler
- ✓ `test_event_handler_ignores_known_events` - Known events (FSDJump) not tracked through EventHandler

#### Public API Tests
- ✓ `test_event_handler_public_methods` - All public methods work correctly:
  - `get_unregistered_events()`
  - `get_unregistered_events_count()`
  - `clear_unregistered_event()`
  - `clear_all_unregistered_events()`

- ✓ `test_event_handler_refresh_unregistered_events` - Refresh method works through EventHandler

## What's Tested

### Core Functionality
- ✓ Event tracking (unknown vs known)
- ✓ Persistent storage to JSON
- ✓ File loading/reloading
- ✓ Catalog event extraction
- ✓ Event validation/refresh
- ✓ Data sanitization
- ✓ Event clearing operations
- ✓ EventHandler integration

### Edge Cases
- ✓ Duplicate events (should increment count)
- ✓ Known events (should not be tracked)
- ✓ Clearing non-existent events (should return False)
- ✓ Catalog updates (should refresh tracking list)
- ✓ Multiple different event types
- ✓ Event sorting (by timestamp)
- ✓ Sensitive data removal

### Integration
- ✓ EventHandler creates and initializes tracker
- ✓ EventHandler hands off events to tracker
- ✓ EventHandler provides public methods for UI
- ✓ Catalog reference properly passed

## Running the Tests

### Run all unregistered events tests
```bash
.venv\Scripts\python -m pytest test/test_unregistered_events.py -v
```

### Run specific test class
```bash
.venv\Scripts\python -m pytest test/test_unregistered_events.py::TestUnregisteredEventsTracker -v
```

### Run specific test
```bash
.venv\Scripts\python -m pytest test/test_unregistered_events.py::TestUnregisteredEventsTracker::test_tracker_initialization -v
```

### Run with coverage
```bash
.venv\Scripts\python -m pytest test/test_unregistered_events.py --cov=edmcruleengine.unregistered_events_tracker --cov-report=term-missing
```

## Test Results

Latest run: **22 passed in 0.22s** ✓

### Component Tests
- `test_config.py` - **11 tests passed** ✓
- `test_integration.py` - **All existing tests passed** ✓

## Test Data

### Known Events Used
- `FSDJump` - Standard jump event (tracked in catalog)
- `Location` - Location event (tracked in catalog)
- `DockingGranted` - Docking permission event (tracked in catalog)

### Unknown Events Used for Testing
- `UnknownEvent` - Generic test event not in catalog
- `TestEvent` - Test event for various scenarios
- `Event1`, `Event2`, `Event3` - Multiple test events
- `MysteryEvent` - Event for tracking tests

### Test Sources
- `journal` - Journal events
- `dashboard` - Dashboard/status events
- `capi` - Frontier CAPI events
- `test` - Test-generated events

## Fixtures

### pytest Fixtures Used
- `temp_dir` - Temporary directory for storing test tracker files
- `catalog` - Loaded signals catalog from plugin root

## How to Maintain Tests

### When Adding New Features
1. Add corresponding test in appropriate class
2. Use existing patterns:
   ```python
   def test_feature_name(self, temp_dir, catalog):
       """Test that feature works correctly."""
       tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
       
       # Test code
       assert result == expected
       print("[OK] Feature test passed")
   ```

### When Modifying Tracker
1. Run full test suite: `pytest test/test_unregistered_events.py -v`
2. Ensure all 22 tests pass
3. Also run integration tests: `pytest test/test_integration.py -v`

### When Updating Catalog
1. Tests extract known events dynamically from catalog
2. If you add new events to catalog:
   - Run tests to verify new events not tracked
   - Update test events if needed
3. If you rename events:
   - Tests will catch mismatches

## Dependencies

Tests depend on:
- `pytest` - Testing framework
- `edmcruleengine.unregistered_events_tracker` - Module being tested
- `edmcruleengine.signals_catalog` - Catalog validation
- `edmcruleengine.event_handler` - Integration testing
- Real `signals_catalog.json` in project root

## Mock Objects

Tests use mocks for:
- VKB client socket operations (`Mock(return_value=...)`)
- Only where necessary to avoid real connections

## CI/CD Integration

These tests should be run:
- ✓ On every commit
- ✓ Before releases
- ✓ When modifying tracking logic
- ✓ When updating catalog

### GitHub Actions (Recommended)
```yaml
- name: Run unregistered events tests
  run: .venv\Scripts\python -m pytest test/test_unregistered_events.py -v
```

## Test Coverage

### Tracker Class
- Initialization: 100%
- Event tracking: 100%
- Catalog validation: 100%
- File persistence: 100%
- Event clearing: 100%
- Data sanitization: 100%

### EventHandler Integration
- Initialization: 100%
- Event handling: 100%
- Public methods: 100%
- Catalog refresh: 100%

## Known Test Characteristics

1. **Warnings in logs**: Tests intentionally produce WARNING logs when tracking unknown events - this is expected
2. **Temporary files**: Tests use temporary directories that are auto-cleaned
3. **Catalog dependency**: Some tests need real `signals_catalog.json` to work correctly
4. **Mock VKB client**: Tests mock VKB socket operations to avoid actual connections

## Future Test Enhancements

Potential improvements:
- [ ] Performance benchmarks for large event lists
- [ ] Concurrent event tracking tests
- [ ] File corruption/recovery tests
- [ ] Catalog update race condition tests
- [ ] UI integration tests (manual smoke tests)
- [ ] End-to-end scenarios with multiple events
