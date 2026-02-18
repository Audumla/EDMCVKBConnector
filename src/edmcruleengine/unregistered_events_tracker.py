"""
Unregistered Events Tracker for EDMC VKB Connector.

Tracks game events that are not registered in the signals catalog.
These events are logged and stored to a file so they can be reviewed and added
to the catalog as needed.

Features:
- Tracks unregistered events with complete metadata
- Stores events persistently to a JSON file
- Validates events against catalog and removes entries when they appear
- Provides list and clearing methods for UI integration
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from . import plugin_logger
from .signals_catalog import SignalsCatalog

logger = plugin_logger(__name__)


class UnregisteredEventsTracker:
    """
    Tracks and manages unregistered game events.
    
    Events not found in the catalog are logged both to the log file and
    persisted to a JSON file for later review and catalog updates.
    """
    
    TRACKER_FILE_NAME = "unregistered_events.json"
    
    def __init__(self, plugin_dir: Path | str, catalog: Optional[SignalsCatalog] = None) -> None:
        """
        Initialize the tracker.
        
        Args:
            plugin_dir: Plugin directory path where tracker file will be stored
            catalog: Optional SignalsCatalog to validate events against
        """
        self.plugin_dir = Path(plugin_dir)
        self.catalog = catalog
        self.tracker_file = self.plugin_dir / self.TRACKER_FILE_NAME
        self.unregistered_events: Dict[str, Dict[str, Any]] = {}
        self._known_events: Optional[Set[str]] = None
        
        # Load existing unregistered events from file
        self._load_from_file()
        self._refresh_known_events_cache()
    
    def set_catalog(self, catalog: Optional[SignalsCatalog]) -> None:
        """
        Set or update the catalog reference.
        
        Useful when the catalog is loaded after the tracker is initialized.
        Also refreshes the known events cache.
        
        Args:
            catalog: SignalsCatalog instance
        """
        self.catalog = catalog
        self._refresh_known_events_cache()
    
    def _refresh_known_events_cache(self) -> None:
        """Refresh the cached set of known events from the catalog."""
        if self.catalog:
            self._known_events = self.catalog.get_all_known_events()
        else:
            self._known_events = set()
    
    def track_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        source: str = "journal",
    ) -> None:
        """
        Track an unregistered event.
        
        The event is checked against the catalog. If not found, it's added
        to the tracking list and logged.
        
        Args:
            event_type: Type of the event (e.g., "Location", "FSDJump")
            event_data: Complete event data dictionary
            source: Source of the event ("journal", "dashboard", "capi", etc.)
        """
        # Skip if event is in catalog
        if self._is_event_known(event_type):
            # Event is registered, remove from tracker if present
            self.unregistered_events.pop(event_type, None)
            return
        
        # Check if event only contains timestamp fields - skip if it does
        if self._is_timestamp_only(event_data):
            return
        
        # Event not in catalog, track it
        if event_type not in self.unregistered_events:
            entry = {
                "event_type": event_type,
                "source": source,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "occurrences": 1,
                "sample_data": self._sanitize_event_data(event_data),
            }
            self.unregistered_events[event_type] = entry
            logger.warning(f"Unregistered event detected: {event_type} from {source}")
        else:
            # Update existing entry
            entry = self.unregistered_events[event_type]
            entry["last_seen"] = time.time()
            entry["occurrences"] = entry.get("occurrences", 0) + 1
            # Update sample data to latest occurrence
            entry["sample_data"] = self._sanitize_event_data(event_data)
        
        # Persist to file
        self._save_to_file()
    
    def _is_timestamp_only(self, event_data: Dict[str, Any]) -> bool:
        """
        Check if event data contains only timestamp fields.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if all non-empty fields are timestamp-related, False otherwise
        """
        if not isinstance(event_data, dict) or not event_data:
            return True
        
        # Keywords that indicate timestamp fields
        timestamp_keywords = ['time', 'timestamp', 'date', 'epoch']
        
        for key in event_data.keys():
            key_lower = str(key).lower()
            # If any field is NOT a timestamp field, return False
            if not any(kw in key_lower for kw in timestamp_keywords):
                return False
        
        # All fields are timestamp-related
        return True
    
    def _is_event_known(self, event_type: str) -> bool:
        """
        Check if an event type is known in the catalog.
        
        Args:
            event_type: Event type to check
            
        Returns:
            True if event is known, False otherwise
        """
        if self._known_events is None:
            self._refresh_known_events_cache()
        return event_type in self._known_events
    
    def refresh_against_catalog(self) -> int:
        """
        Check tracked events against the catalog.
        
        Removes any events that are now found in the catalog and updates
        the known events cache.
        
        Returns:
            Number of events removed from the tracker
        """
        self._refresh_known_events_cache()
        
        events_to_remove = []
        for event_type in list(self.unregistered_events.keys()):
            if self._is_event_known(event_type):
                events_to_remove.append(event_type)
                logger.info(f"Event now in catalog, removing from tracking: {event_type}")
        
        for event_type in events_to_remove:
            del self.unregistered_events[event_type]
        
        if events_to_remove:
            self._save_to_file()
        
        return len(events_to_remove)
    
    def get_unregistered_events(self) -> List[Dict[str, Any]]:
        """
        Get list of all tracked unregistered events.
        
        Returns:
            List of event entry dictionaries, sorted by last_seen (newest first)
        """
        events_list = list(self.unregistered_events.values())
        # Sort by last_seen timestamp (descending - newest first)
        events_list.sort(key=lambda e: e.get("last_seen", 0), reverse=True)
        return events_list
    
    def clear_event(self, event_type: str) -> bool:
        """
        Remove a specific event from tracking.
        
        Args:
            event_type: Event type to remove
            
        Returns:
            True if event was removed, False if not found
        """
        if event_type in self.unregistered_events:
            del self.unregistered_events[event_type]
            self._save_to_file()
            logger.info(f"Cleared tracked event: {event_type}")
            return True
        return False
    
    def clear_all_events(self) -> int:
        """
        Clear all tracked unregistered events.
        
        Returns:
            Number of events cleared
        """
        count = len(self.unregistered_events)
        if count > 0:
            self.unregistered_events.clear()
            self._save_to_file()
            logger.info(f"Cleared all {count} tracked unregistered events")
        return count
    
    def get_events_count(self) -> int:
        """Get the count of tracked unregistered events."""
        return len(self.unregistered_events)

    def _sanitize_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a sanitized copy of event data for storage.
        
        Removes potentially sensitive or very large fields.
        
        Args:
            event_data: Original event data
            
        Returns:
            Sanitized event data
        """
        sanitized = {}
        
        # Fields to skip (sensitive or too large)
        skip_keys = {"MarketID", "OutfittingID", "ShipyardID", "StationServices"}
        max_value_length = 1000
        
        for key, value in event_data.items():
            if key in skip_keys:
                continue
            
            # Keep simple types
            if isinstance(value, (str, int, float, bool, type(None))):
                # Limit string length
                if isinstance(value, str) and len(value) > max_value_length:
                    sanitized[key] = value[:max_value_length] + "..."
                else:
                    sanitized[key] = value
            elif isinstance(value, (list, dict)):
                # Keep lists and dicts but limit serialization depth
                try:
                    json.dumps(value)  # Test if serializable
                    sanitized[key] = value
                except (TypeError, ValueError):
                    sanitized[key] = str(value)[:max_value_length]
            else:
                # Convert other types to string with length limit
                sanitized[key] = str(value)[:max_value_length]
        
        return sanitized
    
    def _load_from_file(self) -> None:
        """Load tracked events from the tracker file."""
        if not self.tracker_file.exists():
            self.unregistered_events = {}
            return
        
        try:
            with open(self.tracker_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, dict) and "events" in data:
                self.unregistered_events = data.get("events", {})
            else:
                logger.warning(f"Invalid tracker file format: {self.tracker_file}")
                self.unregistered_events = {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tracker file: {e}")
            self.unregistered_events = {}
        except Exception as e:
            logger.error(f"Failed to load tracker file: {e}")
            self.unregistered_events = {}
    
    def _save_to_file(self) -> None:
        """Save tracked events to the tracker file."""
        try:
            # Ensure directory exists
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            
            # Write with new format for clarity
            data = {
                "metadata": {
                    "version": "1.0",
                    "description": "Tracked unregistered game events - these events were received but not found in signals_catalog.json",
                    "last_updated": time.time(),
                },
                "events": self.unregistered_events,
            }
            
            with open(self.tracker_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to save tracker file: {e}")

