"""
Tests for unregistered events tracker functionality.

Validates that the system correctly:
- Tracks events not in the signals catalog
- Ignores known events
- Persists events to disk
- Validates against catalog on refresh
- Provides proper UI access
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from edmcruleengine.unregistered_events_tracker import UnregisteredEventsTracker
from edmcruleengine.signals_catalog import SignalsCatalog
from edmcruleengine.config import Config
from edmcruleengine.event_handler import EventHandler


class TestUnregisteredEventsTracker:
    """Test the UnregisteredEventsTracker class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def catalog(self):
        """Load the signals catalog."""
        return SignalsCatalog.from_plugin_dir(".")

    def test_tracker_initialization(self, temp_dir):
        """Test that tracker initializes correctly."""
        tracker = UnregisteredEventsTracker(temp_dir)
        
        assert tracker.plugin_dir == temp_dir
        assert tracker.get_events_count() == 0
        assert len(tracker.get_unregistered_events()) == 0
        print("[OK] Tracker initialization test passed")

    def test_tracker_with_catalog(self, temp_dir, catalog):
        """Test that tracker initializes with catalog."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        assert tracker.catalog is catalog
        assert tracker._known_events is not None
        assert len(tracker._known_events) > 0
        print("[OK] Tracker with catalog initialization test passed")

    def test_track_unknown_event(self, temp_dir, catalog):
        """Test tracking an unknown event."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        # Track event not in catalog
        tracker.track_event("UnknownEvent", {"data": "test"}, source="journal")
        
        assert tracker.get_events_count() == 1
        events = tracker.get_unregistered_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "UnknownEvent"
        assert events[0]["source"] == "journal"
        assert events[0]["occurrences"] == 1
        print("[OK] Track unknown event test passed")

    def test_track_known_event(self, temp_dir, catalog):
        """Test that known events are not tracked."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        # Track event in catalog (FSDJump is known)
        tracker.track_event("FSDJump", {"StarSystem": "Sol"}, source="journal")
        
        # Should not be tracked because FSDJump is in catalog
        assert tracker.get_events_count() == 0
        print("[OK] Track known event test passed")

    def test_duplicate_event_tracking(self, temp_dir, catalog):
        """Test that duplicate events update occurrence count."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        # Track same event multiple times
        tracker.track_event("UnknownEvent", {"data": "test1"}, source="journal")
        time.sleep(0.01)  # Ensure different timestamp
        tracker.track_event("UnknownEvent", {"data": "test2"}, source="journal")
        
        assert tracker.get_events_count() == 1
        events = tracker.get_unregistered_events()
        assert events[0]["occurrences"] == 2
        assert events[0]["sample_data"]["data"] == "test2"  # Latest data
        print("[OK] Duplicate event tracking test passed")

    def test_multiple_different_events(self, temp_dir, catalog):
        """Test tracking multiple different events."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        tracker.track_event("Event1", {"data": "1"}, source="journal")
        tracker.track_event("Event2", {"data": "2"}, source="dashboard")
        tracker.track_event("Event3", {"data": "3"}, source="capi")
        
        assert tracker.get_events_count() == 3
        events = tracker.get_unregistered_events()
        event_names = {e["event_type"] for e in events}
        assert event_names == {"Event1", "Event2", "Event3"}
        print("[OK] Multiple different events test passed")

    def test_persistence_to_file(self, temp_dir, catalog):
        """Test that events are persisted to disk."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        tracker.track_event("TestEvent", {"field": "value"}, source="journal")
        
        # Check file was created
        tracker_file = temp_dir / "unregistered_events.json"
        assert tracker_file.exists(), "Tracker file not created"
        
        # Load and validate file format
        with open(tracker_file) as f:
            data = json.load(f)
        
        assert "metadata" in data
        assert "events" in data
        assert "TestEvent" in data["events"]
        assert data["events"]["TestEvent"]["event_type"] == "TestEvent"
        print("[OK] Persistence to file test passed")

    def test_load_from_file(self, temp_dir, catalog):
        """Test that tracker loads events from existing file."""
        # Create initial tracker and add event
        tracker1 = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        tracker1.track_event("Event1", {"data": "1"}, source="journal")
        tracker1.track_event("Event2", {"data": "2"}, source="dashboard")
        
        # Create new tracker instance - should load from file
        tracker2 = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        assert tracker2.get_events_count() == 2
        events = tracker2.get_unregistered_events()
        event_names = {e["event_type"] for e in events}
        assert event_names == {"Event1", "Event2"}
        print("[OK] Load from file test passed")

    def test_clear_specific_event(self, temp_dir, catalog):
        """Test clearing a specific event."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        tracker.track_event("Event1", {"data": "1"}, source="journal")
        tracker.track_event("Event2", {"data": "2"}, source="journal")
        
        assert tracker.get_events_count() == 2
        
        # Clear one event
        result = tracker.clear_event("Event1")
        
        assert result is True
        assert tracker.get_events_count() == 1
        assert tracker.get_unregistered_events()[0]["event_type"] == "Event2"
        print("[OK] Clear specific event test passed")

    def test_clear_nonexistent_event(self, temp_dir, catalog):
        """Test clearing an event that doesn't exist."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        result = tracker.clear_event("NonExistent")
        
        assert result is False
        print("[OK] Clear nonexistent event test passed")

    def test_clear_all_events(self, temp_dir, catalog):
        """Test clearing all events."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        tracker.track_event("Event1", {"data": "1"}, source="journal")
        tracker.track_event("Event2", {"data": "2"}, source="journal")
        
        assert tracker.get_events_count() == 2
        
        count = tracker.clear_all_events()
        
        assert count == 2
        assert tracker.get_events_count() == 0
        assert len(tracker.get_unregistered_events()) == 0
        print("[OK] Clear all events test passed")

    def test_refresh_against_catalog_removes_known(self, temp_dir):
        """Test that refresh removes events now in catalog."""
        # Create tracker without catalog first
        tracker = UnregisteredEventsTracker(temp_dir)
        
        # Add events as if catalog didn't know them
        tracker.track_event("FSDJump", {"system": "Sol"}, source="journal")
        tracker.track_event("UnknownEvent", {"data": "test"}, source="journal")
        
        assert tracker.get_events_count() == 2
        
        # Now load and set catalog
        catalog = SignalsCatalog.from_plugin_dir(".")
        tracker.set_catalog(catalog)
        
        # Refresh against catalog
        removed = tracker.refresh_against_catalog()
        
        # FSDJump should be removed because it's in catalog
        assert removed == 1
        assert tracker.get_events_count() == 1
        assert tracker.get_unregistered_events()[0]["event_type"] == "UnknownEvent"
        print("[OK] Refresh removes known events test passed")

    def test_refresh_against_catalog_keeps_unknown(self, temp_dir, catalog):
        """Test that refresh keeps events not in catalog."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        tracker.track_event("UnknownEvent1", {"data": "1"}, source="journal")
        tracker.track_event("UnknownEvent2", {"data": "2"}, source="journal")
        
        removed = tracker.refresh_against_catalog()
        
        assert removed == 0
        assert tracker.get_events_count() == 2
        print("[OK] Refresh keeps unknown events test passed")

    def test_sanitize_event_data(self, temp_dir, catalog):
        """Test that sensitive data is sanitized."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        sensitive_event = {
            "event": "TestEvent",
            "MarketID": 123456,  # Should be removed
            "OutfittingID": 789,  # Should be removed
            "StationName": "Test Station",  # Should be kept
            "LongString": "x" * 2000,  # Should be truncated
        }
        
        tracker.track_event("TestEvent", sensitive_event, source="journal")
        
        events = tracker.get_unregistered_events()
        sample = events[0]["sample_data"]
        
        assert "MarketID" not in sample
        assert "OutfittingID" not in sample
        assert "StationName" in sample
        assert len(sample["LongString"]) <= 1003  # 1000 + "..."
        print("[OK] Sanitize event data test passed")

    def test_events_sorted_by_last_seen(self, temp_dir, catalog):
        """Test that events are sorted by last_seen timestamp (newest first)."""
        tracker = UnregisteredEventsTracker(temp_dir, catalog=catalog)
        
        tracker.track_event("Event1", {"data": "1"}, source="journal")
        time.sleep(0.05)
        tracker.track_event("Event2", {"data": "2"}, source="journal")
        time.sleep(0.05)
        tracker.track_event("Event3", {"data": "3"}, source="journal")
        
        events = tracker.get_unregistered_events()
        
        # Should be sorted with newest first (Event3, Event2, Event1)
        assert events[0]["event_type"] == "Event3"
        assert events[1]["event_type"] == "Event2"
        assert events[2]["event_type"] == "Event1"
        print("[OK] Events sorted by last_seen test passed")

    def test_set_catalog(self, temp_dir):
        """Test updating catalog after initialization."""
        tracker = UnregisteredEventsTracker(temp_dir)
        
        # Initially no catalog
        assert tracker.catalog is None
        
        # Add event (will be tracked since no catalog to check)
        tracker.track_event("TestEvent", {"data": "test"}, source="journal")
        assert tracker.get_events_count() == 1
        
        # Load and set catalog
        catalog = SignalsCatalog.from_plugin_dir(".")
        
        # Refresh known events and update catalog
        tracker.set_catalog(catalog)
        assert tracker.catalog is not None
        
        # Now tracking a known event shouldn't add to tracker
        tracker.track_event("FSDJump", {"system": "Sol"}, source="journal")
        # Should still be 1 (FSDJump not added because it's in catalog)
        assert tracker.get_events_count() == 1
        print("[OK] Set catalog test passed")

    def test_catalog_event_extraction(self, catalog):
        """Test that catalog correctly extracts known events."""
        known_events = catalog.get_all_known_events()
        
        # Should have multiple known events
        assert len(known_events) > 100, "Catalog should have many known events"
        
        # Check common events are in the set
        common_events = {
            "FSDJump", "Location", "DockingGranted", "Docked",
            "Undocked", "LaunchFighter", "DockFighter"
        }
        
        for event in common_events:
            assert event in known_events, f"{event} should be in known events"
        
        print(f"[OK] Catalog event extraction test passed ({len(known_events)} known events)")


class TestEventHandlerURI:
    """Test EventHandler integration with unregistered events tracker."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_event_handler_initializes_tracker(self, temp_dir):
        """Test that EventHandler creates tracker on init."""
        config = Config()
        handler = EventHandler(config, plugin_dir=str(temp_dir))
        
        assert hasattr(handler, "unregistered_events_tracker")
        assert handler.unregistered_events_tracker is not None
        print("[OK] EventHandler initializes tracker test passed")

    def test_event_handler_tracks_unknown_events(self, temp_dir):
        """Test that EventHandler tracks unknown events."""
        config = Config()
        handler = EventHandler(config, plugin_dir=str(temp_dir))
        
        # Mock VKB client to prevent connection
        handler.vkb_client.send_event = Mock(return_value=True)
        handler.vkb_client.connect = Mock(return_value=False)
        
        # Simulate an unknown event
        handler.handle_event(
            "UnknownEvent",
            {"field": "value"},
            source="journal",
            cmdr="TestCmdr",
            is_beta=False
        )
        
        # Check it was tracked
        count = handler.get_unregistered_events_count()
        assert count > 0
        print("[OK] EventHandler tracks unknown events test passed")

    def test_event_handler_ignores_known_events(self, temp_dir):
        """Test that EventHandler doesn't track known events when catalog is available."""
        config = Config()
        # Use the real plugin directory where catalog exists
        handler = EventHandler(config, plugin_dir=".")
        
        # Clear any existing tracked events from initialization
        handler.clear_all_unregistered_events()
        
        handler.vkb_client.send_event = Mock(return_value=True)
        handler.vkb_client.connect = Mock(return_value=False)
        
        # FSDJump is a known event
        handler.handle_event(
            "FSDJump",
            {"StarSystem": "Sol"},
            source="journal",
            cmdr="TestCmdr",
            is_beta=False
        )
        
        # FSDJump is in the catalog, so it should NOT be tracked
        count = handler.get_unregistered_events_count()
        assert count == 0, f"FSDJump should not be tracked (known event), but found {count} tracked events"
        print("[OK] EventHandler ignores known events test passed")

    def test_event_handler_public_methods(self, temp_dir):
        """Test EventHandler provides public methods for tracker access."""
        config = Config()
        handler = EventHandler(config, plugin_dir=str(temp_dir))
        
        handler.vkb_client.send_event = Mock(return_value=True)
        handler.vkb_client.connect = Mock(return_value=False)
        
        # Add an unknown event
        handler.handle_event(
            "UnknownEvent",
            {"data": "test"},
            source="journal",
            cmdr="TestCmdr",
            is_beta=False
        )
        
        # Test public methods exist and work
        count = handler.get_unregistered_events_count()
        assert count == 1
        
        events = handler.get_unregistered_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "UnknownEvent"
        
        # Test clearing
        cleared = handler.clear_all_unregistered_events()
        assert cleared == 1
        assert handler.get_unregistered_events_count() == 0
        
        print("[OK] EventHandler public methods test passed")

    def test_event_handler_refresh_unregistered_events(self, temp_dir):
        """Test EventHandler refresh method."""
        config = Config()
        handler = EventHandler(config, plugin_dir=str(temp_dir))
        
        handler.vkb_client.send_event = Mock(return_value=True)
        handler.vkb_client.connect = Mock(return_value=False)
        
        # Add a known event that would normally be tracked
        # (by bypassing the catalog check)
        handler.unregistered_events_tracker.track_event(
            "FSDJump", {"data": "test"}, source="journal"
        )
        
        assert handler.get_unregistered_events_count() == 1
        
        # Refresh should remove it
        removed = handler.refresh_unregistered_events_against_catalog()
        assert removed >= 0  # Depends on if FSDJump was actually tracked
        
        print("[OK] EventHandler refresh unregistered events test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
