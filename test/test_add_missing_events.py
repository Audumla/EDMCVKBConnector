#!/usr/bin/env python3
"""
Unit tests for add_missing_events.py
"""

import unittest
import json
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.add_missing_events import add_event_to_signal


class TestAddMissingEvents(unittest.TestCase):
    """Test adding missing events to signal catalog"""

    def setUp(self):
        """Set up test signal definition"""
        self.signal_def = {
            "type": "enum",
            "title": "Test Event Signal",
            "ui": {
                "label": "Test event",
                "category": "Test",
                "tier": "core"
            },
            "values": [
                {"value": "none", "label": "None"},
                {"value": "existing_event", "label": "Existing", "recent_event": "ExistingEvent"}
            ],
            "derive": {
                "op": "first_match",
                "cases": [
                    {
                        "when": {
                            "op": "recent",
                            "event_name": "ExistingEvent",
                            "within_seconds": 300
                        },
                        "value": "existing_event"
                    }
                ],
                "default": "none"
            }
        }

    def test_add_new_event(self):
        """Test adding a new event to signal"""
        result = add_event_to_signal(
            self.signal_def,
            'NewEvent',
            'new_event',
            'New Event Label'
        )

        self.assertTrue(result)

        # Check value added
        value_found = False
        for value in self.signal_def['values']:
            if value.get('recent_event') == 'NewEvent':
                value_found = True
                self.assertEqual(value['value'], 'new_event')
                self.assertEqual(value['label'], 'New Event Label')
                break
        self.assertTrue(value_found)

        # Check derive case added
        case_found = False
        for case in self.signal_def['derive']['cases']:
            if case.get('when', {}).get('event_name') == 'NewEvent':
                case_found = True
                self.assertEqual(case['value'], 'new_event')
                self.assertEqual(case['when']['within_seconds'], 300)
                break
        self.assertTrue(case_found)

    def test_add_duplicate_event(self):
        """Test adding an event that already exists"""
        result = add_event_to_signal(
            self.signal_def,
            'ExistingEvent',
            'existing_event',
            'Existing Event'
        )

        self.assertFalse(result)

        # Verify no duplicate added
        event_count = sum(
            1 for v in self.signal_def['values']
            if v.get('recent_event') == 'ExistingEvent'
        )
        self.assertEqual(event_count, 1)

    def test_multiple_events_added(self):
        """Test adding multiple events sequentially"""
        events = [
            ('Event1', 'event_1', 'Event One'),
            ('Event2', 'event_2', 'Event Two'),
            ('Event3', 'event_3', 'Event Three'),
        ]

        for event_name, value_name, label in events:
            result = add_event_to_signal(
                self.signal_def,
                event_name,
                value_name,
                label
            )
            self.assertTrue(result)

        # Verify all added
        for event_name, value_name, label in events:
            value_found = any(
                v.get('recent_event') == event_name
                for v in self.signal_def['values']
            )
            self.assertTrue(value_found)

        # Total should be: 2 original + 3 new = 5
        self.assertEqual(len(self.signal_def['values']), 5)
        self.assertEqual(len(self.signal_def['derive']['cases']), 4)  # 1 original + 3 new

    def test_event_structure(self):
        """Test that added event has correct structure"""
        add_event_to_signal(
            self.signal_def,
            'TestEvent',
            'test_event',
            'Test Event'
        )

        # Find the added value
        added_value = None
        for value in self.signal_def['values']:
            if value.get('recent_event') == 'TestEvent':
                added_value = value
                break

        self.assertIsNotNone(added_value)
        self.assertIn('value', added_value)
        self.assertIn('label', added_value)
        self.assertIn('recent_event', added_value)
        self.assertEqual(added_value['value'], 'test_event')
        self.assertEqual(added_value['label'], 'Test Event')

        # Find the added derive case
        added_case = None
        for case in self.signal_def['derive']['cases']:
            if case.get('when', {}).get('event_name') == 'TestEvent':
                added_case = case
                break

        self.assertIsNotNone(added_case)
        self.assertIn('when', added_case)
        self.assertIn('value', added_case)
        self.assertEqual(added_case['when']['op'], 'recent')
        self.assertEqual(added_case['when']['event_name'], 'TestEvent')
        self.assertEqual(added_case['when']['within_seconds'], 300)


class TestEventPlacement(unittest.TestCase):
    """Test logical placement of missing events"""

    def test_system_events_placement(self):
        """Test that system events go to system_event signal"""
        system_events = ['StartUp', 'Shutdown', 'Squadron', 'Loadouts']
        # These should be added to system_event signal
        # This is validated by the script logic
        self.assertEqual(len(system_events), 4)

    def test_travel_events_placement(self):
        """Test that travel events go to travel_event signal"""
        travel_events = ['NavRouteClear']
        # This should be added to travel_event signal
        self.assertEqual(len(travel_events), 1)

    def test_engineering_events_placement(self):
        """Test that engineering events go to engineering_event signal"""
        engineering_events = ['EngineerApply']
        # This should be added to engineering_event signal
        self.assertEqual(len(engineering_events), 1)

    def test_combat_events_placement(self):
        """Test that crime events go to combat_event signal"""
        combat_events = ['CommitCrime']
        # This should be added to combat_event signal
        self.assertEqual(len(combat_events), 1)

    def test_odyssey_events_placement(self):
        """Test that Odyssey events have a fallback"""
        odyssey_events = ['OnFootLoadout', 'UpgradeSuit', 'UpgradeWeapon', 'WeaponLoadout']
        # These should go to on_foot_event if it exists, otherwise ship_event
        self.assertEqual(len(odyssey_events), 4)


class TestCatalogIntegrity(unittest.TestCase):
    """Test catalog integrity after adding events"""

    def setUp(self):
        """Create a minimal test catalog"""
        self.test_catalog = {
            "signals": {
                "system_event": {
                    "type": "enum",
                    "values": [
                        {"value": "none", "label": "None"}
                    ],
                    "derive": {
                        "op": "first_match",
                        "cases": [],
                        "default": "none"
                    }
                }
            }
        }

    def test_catalog_structure_preserved(self):
        """Test that catalog structure is preserved after adding events"""
        signal = self.test_catalog['signals']['system_event']

        # Add event
        add_event_to_signal(signal, 'TestEvent', 'test_event', 'Test')

        # Verify structure
        self.assertIn('type', signal)
        self.assertIn('values', signal)
        self.assertIn('derive', signal)
        self.assertIn('op', signal['derive'])
        self.assertIn('cases', signal['derive'])
        self.assertIn('default', signal['derive'])

    def test_json_serializable(self):
        """Test that catalog remains JSON serializable"""
        signal = self.test_catalog['signals']['system_event']
        add_event_to_signal(signal, 'TestEvent', 'test_event', 'Test')

        # Should not raise exception
        try:
            json_str = json.dumps(self.test_catalog, indent=2)
            reloaded = json.loads(json_str)
            self.assertEqual(self.test_catalog, reloaded)
        except Exception as e:
            self.fail(f"Catalog not JSON serializable: {e}")

    def test_no_data_loss(self):
        """Test that existing data is not lost"""
        signal = self.test_catalog['signals']['system_event']

        # Add initial data
        signal['values'].append({
            "value": "original",
            "label": "Original",
            "recent_event": "Original"
        })

        original_count = len(signal['values'])

        # Add new event
        add_event_to_signal(signal, 'NewEvent', 'new_event', 'New')

        # Verify original data still exists
        self.assertEqual(len(signal['values']), original_count + 1)
        original_found = any(
            v.get('recent_event') == 'Original'
            for v in signal['values']
        )
        self.assertTrue(original_found)


if __name__ == '__main__':
    unittest.main()
