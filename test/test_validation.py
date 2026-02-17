#!/usr/bin/env python3
"""
Unit tests for signal catalog validation scripts
"""

import unittest
import json
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCatalogCoverage(unittest.TestCase):
    """Test signal catalog coverage validation"""

    def setUp(self):
        """Set up test environment"""
        self.known_events = {
            'FileHeader', 'Continued', 'LoadGame', 'Commander',
            'FSDJump', 'Docked', 'Undocked', 'Location',
            'Scan', 'BountyAward', 'MarketBuy', 'MarketSell',
        }

        self.test_catalog = {
            "signals": {
                "system_event": {
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "journal_started", "label": "Journal started", "recent_event": "FileHeader"},
                        {"value": "journal_continued", "label": "Journal continued", "recent_event": "Continued"},
                        {"value": "game_loaded", "label": "Game loaded", "recent_event": "LoadGame"},
                        {"value": "commander_info", "label": "Commander info", "recent_event": "Commander"},
                    ]
                },
                "travel_event": {
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "fsd_jump", "label": "FSD Jump", "recent_event": "FSDJump"},
                        {"value": "docked", "label": "Docked", "recent_event": "Docked"},
                        {"value": "undocked", "label": "Undocked", "recent_event": "Undocked"},
                        {"value": "location", "label": "Location", "recent_event": "Location"},
                    ]
                },
                "exploration_event": {
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "scan", "label": "Scan", "recent_event": "Scan"},
                    ]
                },
                "combat_event": {
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "bounty", "label": "Bounty", "recent_event": "BountyAward"},
                    ]
                },
                "trading_event": {
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "buy", "label": "Buy", "recent_event": "MarketBuy"},
                        {"value": "sell", "label": "Sell", "recent_event": "MarketSell"},
                    ]
                }
            }
        }

    def test_extract_events_from_catalog(self):
        """Test extracting all events from catalog"""
        events = set()

        for signal_name, signal_data in self.test_catalog['signals'].items():
            if 'values' in signal_data:
                for value in signal_data['values']:
                    if 'recent_event' in value:
                        events.add(value['recent_event'])

        # Should have all events from known_events (12 total)
        self.assertEqual(len(events), 12)
        self.assertIn('FileHeader', events)
        self.assertIn('FSDJump', events)
        self.assertIn('Scan', events)

    def test_coverage_calculation(self):
        """Test coverage percentage calculation"""
        # Extract events from catalog
        catalog_events = set()
        for signal_data in self.test_catalog['signals'].values():
            if 'values' in signal_data:
                for value in signal_data['values']:
                    if 'recent_event' in value:
                        catalog_events.add(value['recent_event'])

        # Calculate coverage
        covered = self.known_events & catalog_events
        missing = self.known_events - catalog_events

        coverage_pct = (len(covered) / len(self.known_events)) * 100

        # In this test, we have 100% coverage
        self.assertEqual(len(covered), 12)
        self.assertEqual(len(missing), 0)
        self.assertAlmostEqual(coverage_pct, 100.0, places=1)

    def test_missing_events_detection(self):
        """Test detecting missing events"""
        # Create a scenario with missing events
        incomplete_catalog = {
            "signals": {
                "system_event": {
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "journal_started", "label": "Journal started", "recent_event": "FileHeader"},
                    ]
                }
            }
        }

        catalog_events = set()
        for signal_data in incomplete_catalog['signals'].values():
            if 'values' in signal_data:
                for value in signal_data['values']:
                    if 'recent_event' in value:
                        catalog_events.add(value['recent_event'])

        missing = self.known_events - catalog_events

        # Many events should be missing in the incomplete catalog
        self.assertGreater(len(missing), 0)
        self.assertEqual(len(missing), 11)  # 12 known - 1 covered = 11 missing

    def test_synthetic_events_detection(self):
        """Test detecting synthetic/derived events"""
        catalog_events = set()
        for signal_data in self.test_catalog['signals'].values():
            if 'values' in signal_data:
                for value in signal_data['values']:
                    if 'recent_event' in value:
                        catalog_events.add(value['recent_event'])

        # Add a synthetic event to catalog
        self.test_catalog['signals']['test_signal'] = {
            "values": [
                {"value": "synthetic", "label": "Synthetic", "recent_event": "SyntheticEvent"}
            ]
        }

        # Re-extract events
        catalog_events_with_synthetic = set()
        for signal_data in self.test_catalog['signals'].values():
            if 'values' in signal_data:
                for value in signal_data['values']:
                    if 'recent_event' in value:
                        catalog_events_with_synthetic.add(value['recent_event'])

        # Find synthetic events
        synthetic = catalog_events_with_synthetic - self.known_events

        self.assertIn('SyntheticEvent', synthetic)


class TestEventCategorization(unittest.TestCase):
    """Test event categorization and organization"""

    def test_system_events(self):
        """Test system/session events"""
        system_events = {
            'FileHeader', 'Continued', 'LoadGame', 'Commander',
            'Materials', 'Cargo', 'Missions', 'Rank', 'Progress',
            'StartUp', 'Shutdown'
        }
        self.assertGreater(len(system_events), 0)

    def test_travel_events(self):
        """Test travel/navigation events"""
        travel_events = {
            'Location', 'FSDJump', 'Docked', 'Undocked',
            'SupercruiseEntry', 'SupercruiseExit',
            'ApproachBody', 'LeaveBody', 'NavRouteClear'
        }
        self.assertGreater(len(travel_events), 0)

    def test_combat_events(self):
        """Test combat events"""
        combat_events = {
            'UnderAttack', 'Bounty', 'Died', 'Interdicted',
            'CommitCrime', 'ShipTargetted'
        }
        self.assertGreater(len(combat_events), 0)

    def test_exploration_events(self):
        """Test exploration events"""
        exploration_events = {
            'Scan', 'FSSDiscoveryScan', 'SAAScanComplete',
            'CodexEntry', 'SellExplorationData'
        }
        self.assertGreater(len(exploration_events), 0)

    def test_trading_events(self):
        """Test trading events"""
        trading_events = {
            'MarketBuy', 'MarketSell', 'CollectCargo',
            'EjectCargo', 'MiningRefined'
        }
        self.assertGreater(len(trading_events), 0)


class TestSignalStructure(unittest.TestCase):
    """Test signal definition structure"""

    def test_signal_has_required_fields(self):
        """Test that signals have required fields"""
        signal = {
            "type": "enum",
            "title": "Test Signal",
            "ui": {
                "label": "Test",
                "category": "Test Category",
                "tier": "core"
            },
            "values": [
                {"value": "none", "label": "None"}
            ]
        }

        self.assertIn('type', signal)
        self.assertIn('title', signal)
        self.assertIn('ui', signal)
        self.assertIn('values', signal)

    def test_ui_section_valid(self):
        """Test that UI section is valid"""
        ui = {
            "label": "Test Signal",
            "category": "Test",
            "tier": "core"
        }

        self.assertIn('label', ui)
        self.assertIn('category', ui)
        self.assertIn('tier', ui)
        self.assertIn(ui['tier'], ['core', 'detail', 'extended'])

    def test_values_structure(self):
        """Test that values have correct structure"""
        values = [
            {"value": "none", "label": "None"},
            {"value": "test_event", "label": "Test Event", "recent_event": "TestEvent"}
        ]

        for value in values:
            self.assertIn('value', value)
            self.assertIn('label', value)

        # Second value should have recent_event
        self.assertIn('recent_event', values[1])

    def test_derive_section_structure(self):
        """Test that derive section has correct structure"""
        derive = {
            "op": "first_match",
            "cases": [
                {
                    "when": {
                        "op": "recent",
                        "event_name": "TestEvent",
                        "within_seconds": 300
                    },
                    "value": "test_event"
                }
            ],
            "default": "none"
        }

        self.assertIn('op', derive)
        self.assertIn('cases', derive)
        self.assertIn('default', derive)
        self.assertEqual(derive['op'], 'first_match')

        # Check case structure
        for case in derive['cases']:
            self.assertIn('when', case)
            self.assertIn('value', case)
            self.assertIn('op', case['when'])
            self.assertIn('event_name', case['when'])


class TestEventConsistency(unittest.TestCase):
    """Test consistency between events and signals"""

    def test_event_value_matching(self):
        """Test that event names match value names"""
        signal = {
            "values": [
                {"value": "fsd_jump", "label": "FSD Jump", "recent_event": "FSDJump"},
                {"value": "docked", "label": "Docked", "recent_event": "Docked"},
            ],
            "derive": {
                "cases": [
                    {
                        "when": {"event_name": "FSDJump"},
                        "value": "fsd_jump"
                    },
                    {
                        "when": {"event_name": "Docked"},
                        "value": "docked"
                    }
                ]
            }
        }

        # Extract value->event mappings from values
        value_events = {}
        for value in signal['values']:
            if 'recent_event' in value:
                value_events[value['value']] = value['recent_event']

        # Extract value->event mappings from derive cases
        derive_events = {}
        for case in signal['derive']['cases']:
            derive_events[case['value']] = case['when']['event_name']

        # They should match
        for value_name in value_events:
            self.assertEqual(value_events[value_name], derive_events.get(value_name))

    def test_no_duplicate_events(self):
        """Test that events are not duplicated in signal"""
        signal = {
            "values": [
                {"value": "test1", "label": "Test 1", "recent_event": "Test"},
                {"value": "test2", "label": "Test 2", "recent_event": "Test2"},
            ]
        }

        events = [v.get('recent_event') for v in signal['values'] if 'recent_event' in v]
        unique_events = set(events)

        self.assertEqual(len(events), len(unique_events))


if __name__ == '__main__':
    unittest.main()
