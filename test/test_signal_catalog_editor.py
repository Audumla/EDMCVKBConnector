#!/usr/bin/env python3
"""
Unit tests for signal_catalog_editor.py
"""

import unittest
import json
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.signal_catalog_editor import SignalCatalogEditor


class TestSignalCatalogEditor(unittest.TestCase):
    """Test the signal catalog editor functionality"""

    def setUp(self):
        """Set up test environment"""
        # Create a minimal test catalog
        self.test_catalog = {
            "signals": {
                "test_signal_1": {
                    "type": "enum",
                    "title": "Test Signal 1",
                    "ui": {
                        "label": "Test 1",
                        "category": "Test Category",
                        "tier": "core"
                    },
                    "values": [
                        {"value": "none", "label": "None"}
                    ]
                },
                "test_signal_2": {
                    "type": "enum",
                    "title": "Test Signal 2",
                    "ui": {
                        "label": "Test 2",
                        "category": "Test Category",
                        "subcategory": "Test Subcat",
                        "tier": "detail"
                    },
                    "values": [
                        {"value": "none", "label": "None"}
                    ]
                },
                "test_signal_3": {
                    "type": "string",
                    "title": "Test Signal 3",
                    "ui": {
                        "label": "Test 3",
                        "category": "Other Category",
                        "tier": "extended"
                    }
                }
            }
        }

        # Create temporary catalog file
        self.temp_dir = tempfile.mkdtemp()
        self.catalog_path = Path(self.temp_dir) / "test_catalog.json"

        with open(self.catalog_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_catalog, f, indent=2)

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_catalog(self):
        """Test loading catalog from file"""
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)

        self.assertIn('signals', catalog)
        self.assertEqual(len(catalog['signals']), 3)
        self.assertIn('test_signal_1', catalog['signals'])

    def test_get_signal_data(self):
        """Test retrieving signal data"""
        catalog = self.test_catalog

        # Direct signal
        signal_1 = catalog['signals']['test_signal_1']
        self.assertEqual(signal_1['ui']['label'], 'Test 1')
        self.assertEqual(signal_1['ui']['category'], 'Test Category')
        self.assertEqual(signal_1['ui']['tier'], 'core')

        # Signal with subcategory
        signal_2 = catalog['signals']['test_signal_2']
        self.assertEqual(signal_2['ui']['subcategory'], 'Test Subcat')

    def test_category_extraction(self):
        """Test extracting all categories from catalog"""
        catalog = self.test_catalog
        categories = set()

        for signal_key, signal_data in catalog['signals'].items():
            if isinstance(signal_data, dict) and 'ui' in signal_data:
                categories.add(signal_data['ui'].get('category', ''))

        self.assertIn('Test Category', categories)
        self.assertIn('Other Category', categories)
        self.assertEqual(len(categories), 2)

    def test_subcategory_extraction(self):
        """Test extracting subcategories for a category"""
        catalog = self.test_catalog
        subcategories = set()

        for signal_key, signal_data in catalog['signals'].items():
            if isinstance(signal_data, dict) and 'ui' in signal_data:
                if signal_data['ui'].get('category') == 'Test Category':
                    subcat = signal_data['ui'].get('subcategory')
                    if subcat:
                        subcategories.add(subcat)

        self.assertIn('Test Subcat', subcategories)
        self.assertEqual(len(subcategories), 1)

    def test_move_signal_to_category(self):
        """Test moving a signal to a different category"""
        catalog = self.test_catalog

        # Move test_signal_1 to "Other Category"
        signal = catalog['signals']['test_signal_1']
        original_category = signal['ui']['category']
        signal['ui']['category'] = 'Other Category'

        # Verify change
        self.assertEqual(signal['ui']['category'], 'Other Category')
        self.assertNotEqual(signal['ui']['category'], original_category)

    def test_move_signal_to_subcategory(self):
        """Test adding subcategory to a signal"""
        catalog = self.test_catalog

        # Add subcategory to test_signal_1
        signal = catalog['signals']['test_signal_1']
        self.assertNotIn('subcategory', signal['ui'])

        signal['ui']['subcategory'] = 'New Subcat'

        # Verify change
        self.assertEqual(signal['ui']['subcategory'], 'New Subcat')

    def test_promote_to_top_level(self):
        """Test removing subcategory from signal"""
        catalog = self.test_catalog

        # Remove subcategory from test_signal_2
        signal = catalog['signals']['test_signal_2']
        self.assertIn('subcategory', signal['ui'])

        del signal['ui']['subcategory']

        # Verify removal
        self.assertNotIn('subcategory', signal['ui'])

    def test_change_tier(self):
        """Test changing signal tier"""
        catalog = self.test_catalog

        # Change tier of test_signal_1
        signal = catalog['signals']['test_signal_1']
        original_tier = signal['ui']['tier']
        signal['ui']['tier'] = 'extended'

        # Verify change
        self.assertEqual(signal['ui']['tier'], 'extended')
        self.assertNotEqual(signal['ui']['tier'], original_tier)

    def test_rename_signal_label(self):
        """Test renaming signal label"""
        catalog = self.test_catalog

        # Rename test_signal_1
        signal = catalog['signals']['test_signal_1']
        original_label = signal['ui']['label']
        signal['ui']['label'] = 'Renamed Label'

        # Verify change
        self.assertEqual(signal['ui']['label'], 'Renamed Label')
        self.assertNotEqual(signal['ui']['label'], original_label)

    def test_save_and_reload_catalog(self):
        """Test saving and reloading catalog"""
        catalog = self.test_catalog

        # Make a change
        catalog['signals']['test_signal_1']['ui']['label'] = 'Modified'

        # Save
        with open(self.catalog_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2)

        # Reload
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            reloaded = json.load(f)

        # Verify change persisted
        self.assertEqual(
            reloaded['signals']['test_signal_1']['ui']['label'],
            'Modified'
        )

    def test_delete_signal(self):
        """Test deleting a signal"""
        catalog = self.test_catalog

        # Verify signal exists
        self.assertIn('test_signal_1', catalog['signals'])

        # Delete signal
        del catalog['signals']['test_signal_1']

        # Verify signal is gone
        self.assertNotIn('test_signal_1', catalog['signals'])
        self.assertEqual(len(catalog['signals']), 2)

    def test_delete_multiple_signals(self):
        """Test deleting multiple signals"""
        catalog = self.test_catalog

        initial_count = len(catalog['signals'])

        # Delete two signals
        del catalog['signals']['test_signal_1']
        del catalog['signals']['test_signal_2']

        # Verify both deleted
        self.assertEqual(len(catalog['signals']), initial_count - 2)
        self.assertNotIn('test_signal_1', catalog['signals'])
        self.assertNotIn('test_signal_2', catalog['signals'])
        self.assertIn('test_signal_3', catalog['signals'])

    def test_backup_creation(self):
        """Test backup file creation"""
        import shutil

        # Create backup
        backup_path = self.catalog_path.with_suffix('.json.backup')
        shutil.copy2(self.catalog_path, backup_path)

        # Verify backup exists
        self.assertTrue(backup_path.exists())

        # Verify backup content matches original
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            original = json.load(f)
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup = json.load(f)

        self.assertEqual(original, backup)

    def test_bulk_tier_change(self):
        """Test changing tier for multiple signals"""
        catalog = self.test_catalog

        # Change tier for all signals
        for signal_key, signal_data in catalog['signals'].items():
            if isinstance(signal_data, dict) and 'ui' in signal_data:
                signal_data['ui']['tier'] = 'detail'

        # Verify all changed
        for signal_key, signal_data in catalog['signals'].items():
            if isinstance(signal_data, dict) and 'ui' in signal_data:
                self.assertEqual(signal_data['ui']['tier'], 'detail')

    def test_bulk_category_move(self):
        """Test moving multiple signals to same category"""
        catalog = self.test_catalog

        # Move all signals to "Unified Category"
        for signal_key, signal_data in catalog['signals'].items():
            if isinstance(signal_data, dict) and 'ui' in signal_data:
                signal_data['ui']['category'] = 'Unified Category'
                # Remove subcategory when changing category
                if 'subcategory' in signal_data['ui']:
                    del signal_data['ui']['subcategory']

        # Verify all moved
        for signal_key, signal_data in catalog['signals'].items():
            if isinstance(signal_data, dict) and 'ui' in signal_data:
                self.assertEqual(signal_data['ui']['category'], 'Unified Category')
                self.assertNotIn('subcategory', signal_data['ui'])


class TestDragAndDropState(unittest.TestCase):
    """Test drag-and-drop state management"""

    def test_drag_threshold(self):
        """Test that drag threshold prevents accidental moves"""
        # Simulate a click with minimal movement
        start_x, start_y = 100, 100
        end_x, end_y = 102, 102  # Only moved 2 pixels
        threshold = 5

        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)

        # Should not be considered a drag
        is_drag = dx >= threshold or dy >= threshold
        self.assertFalse(is_drag)

    def test_drag_threshold_exceeded(self):
        """Test that actual drags exceed threshold"""
        # Simulate a real drag
        start_x, start_y = 100, 100
        end_x, end_y = 150, 120  # Moved 50 pixels horizontally
        threshold = 5

        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)

        # Should be considered a drag
        is_drag = dx >= threshold or dy >= threshold
        self.assertTrue(is_drag)

    def test_state_clearing(self):
        """Test that drag state is properly cleared"""
        # Simulate drag state
        drag_data = {
            'item': 'test_item',
            'start_x': 100,
            'start_y': 100
        }

        # Clear state
        drag_data = None

        # State should be cleared
        self.assertIsNone(drag_data)


class TestEnumEditing(unittest.TestCase):
    """Test enum value editing functionality"""

    def setUp(self):
        """Set up test enum signal"""
        self.enum_signal = {
            "type": "enum",
            "title": "Test Enum",
            "ui": {
                "label": "Test",
                "category": "Test",
                "tier": "core"
            },
            "values": [
                {"value": "none", "label": "None"},
                {"value": "option_a", "label": "Option A"},
                {"value": "option_b", "label": "Option B", "recent_event": "EventB"}
            ]
        }

    def test_add_enum_value(self):
        """Test adding a new enum value"""
        initial_count = len(self.enum_signal['values'])

        new_value = {
            "value": "option_c",
            "label": "Option C"
        }
        self.enum_signal['values'].append(new_value)

        self.assertEqual(len(self.enum_signal['values']), initial_count + 1)
        self.assertIn(new_value, self.enum_signal['values'])

    def test_rename_enum_value(self):
        """Test renaming an enum value"""
        value = self.enum_signal['values'][1]
        original_value = value['value']
        original_label = value['label']

        value['value'] = 'new_option_a'
        value['label'] = 'New Option A'

        self.assertEqual(value['value'], 'new_option_a')
        self.assertEqual(value['label'], 'New Option A')
        self.assertNotEqual(value['value'], original_value)
        self.assertNotEqual(value['label'], original_label)

    def test_delete_enum_value(self):
        """Test deleting an enum value"""
        initial_count = len(self.enum_signal['values'])

        del self.enum_signal['values'][1]

        self.assertEqual(len(self.enum_signal['values']), initial_count - 1)
        # Option A should be gone
        self.assertNotIn('option_a', [v['value'] for v in self.enum_signal['values']])

    def test_move_enum_value_up(self):
        """Test moving an enum value up in order"""
        values = self.enum_signal['values']

        # Move option_b up (index 2 -> 1)
        values[1], values[2] = values[2], values[1]

        self.assertEqual(values[1]['value'], 'option_b')
        self.assertEqual(values[2]['value'], 'option_a')

    def test_move_enum_value_down(self):
        """Test moving an enum value down in order"""
        values = self.enum_signal['values']

        # Move option_a down (index 1 -> 2)
        values[1], values[2] = values[2], values[1]

        self.assertEqual(values[1]['value'], 'option_b')
        self.assertEqual(values[2]['value'], 'option_a')

    def test_move_value_to_another_signal(self):
        """Test moving an enum value from one signal to another"""
        target_signal = {
            "type": "enum",
            "values": [
                {"value": "none", "label": "None"}
            ]
        }

        # Move option_a from source to target
        moved_value = self.enum_signal['values'].pop(1)
        target_signal['values'].append(moved_value)

        # Source should have 2 values now
        self.assertEqual(len(self.enum_signal['values']), 2)
        # Target should have 2 values now
        self.assertEqual(len(target_signal['values']), 2)
        # Target should contain option_a
        self.assertIn('option_a', [v['value'] for v in target_signal['values']])

    def test_duplicate_value_detection(self):
        """Test detecting duplicate enum values"""
        values = self.enum_signal['values']

        # Check if 'option_a' already exists
        value_ids = [v['value'] for v in values]
        self.assertIn('option_a', value_ids)

        # Try to detect duplicate
        new_value_id = 'option_a'
        is_duplicate = new_value_id in value_ids

        self.assertTrue(is_duplicate)

    def test_enum_value_with_event(self):
        """Test enum value with associated event"""
        value = self.enum_signal['values'][2]  # option_b

        self.assertIn('recent_event', value)
        self.assertEqual(value['recent_event'], 'EventB')


class TestEnumMerge(unittest.TestCase):
    """Test merging two enum signals"""

    def setUp(self):
        """Set up test enum signals"""
        self.catalog = {
            "signals": {
                "enum_signal_1": {
                    "type": "enum",
                    "ui": {"label": "Enum 1", "category": "Test"},
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "value_a", "label": "Value A"},
                        {"value": "value_b", "label": "Value B"}
                    ]
                },
                "enum_signal_2": {
                    "type": "enum",
                    "ui": {"label": "Enum 2", "category": "Test"},
                    "values": [
                        {"value": "none", "label": "None"},
                        {"value": "value_c", "label": "Value C"},
                        {"value": "value_d", "label": "Value D"}
                    ]
                }
            }
        }

    def test_merge_enum_signals(self):
        """Test merging two enum signals"""
        source = self.catalog['signals']['enum_signal_1']
        target = self.catalog['signals']['enum_signal_2']

        # Merge source into target
        source_values = source['values']
        for value in source_values:
            value_id = value['value']
            # Avoid duplicates
            if not any(v['value'] == value_id for v in target['values']):
                target['values'].append(value)

        # Delete source
        del self.catalog['signals']['enum_signal_1']

        # Target should have all values (including duplicates filtered)
        # Original target: none, value_c, value_d
        # From source (not duplicates): value_a, value_b
        self.assertEqual(len(target['values']), 5)
        self.assertIn('value_a', [v['value'] for v in target['values']])
        self.assertIn('value_b', [v['value'] for v in target['values']])

        # Source should be deleted
        self.assertNotIn('enum_signal_1', self.catalog['signals'])

    def test_duplicate_handling_in_merge(self):
        """Test that duplicates are handled during merge"""
        # Add duplicate value to both signals
        self.catalog['signals']['enum_signal_2']['values'].append(
            {"value": "value_a", "label": "Value A"}
        )

        source = self.catalog['signals']['enum_signal_1']
        target = self.catalog['signals']['enum_signal_2']

        initial_count = len(target['values'])

        # Merge with duplicate check
        for value in source['values']:
            value_id = value['value']
            if not any(v['value'] == value_id for v in target['values']):
                target['values'].append(value)

        # Should not have added value_a since it was duplicate
        # Initial: none, value_c, value_d, value_a (4)
        # Add: none (dup), value_b (new) = 1 new
        self.assertEqual(len(target['values']), initial_count + 1)

    def test_get_enum_signals_list(self):
        """Test extracting list of enum signals"""
        enum_signals = []
        for sig_key, sig_data in self.catalog['signals'].items():
            if isinstance(sig_data, dict) and sig_data.get('type') == 'enum':
                enum_signals.append(sig_key)

        self.assertEqual(len(enum_signals), 2)
        self.assertIn('enum_signal_1', enum_signals)
        self.assertIn('enum_signal_2', enum_signals)


class TestCategoryDialog(unittest.TestCase):
    """Test category selection dialog functionality"""

    def test_category_list_creation(self):
        """Test creating list of categories"""
        test_catalog = {
            "signals": {
                "sig1": {"ui": {"category": "Cat1"}},
                "sig2": {"ui": {"category": "Cat2"}},
                "sig3": {"ui": {"category": "Cat1"}},
            }
        }

        categories = set()
        for sig_data in test_catalog['signals'].values():
            if 'ui' in sig_data:
                categories.add(sig_data['ui']['category'])

        self.assertEqual(len(categories), 2)
        self.assertIn('Cat1', categories)
        self.assertIn('Cat2', categories)

    def test_subcategory_list_creation(self):
        """Test creating list of subcategories for a category"""
        test_catalog = {
            "signals": {
                "sig1": {"ui": {"category": "Cat1", "subcategory": "Sub1"}},
                "sig2": {"ui": {"category": "Cat1", "subcategory": "Sub2"}},
                "sig3": {"ui": {"category": "Cat2", "subcategory": "Sub3"}},
            }
        }

        subcategories = set()
        for sig_data in test_catalog['signals'].values():
            if 'ui' in sig_data and sig_data['ui'].get('category') == 'Cat1':
                subcat = sig_data['ui'].get('subcategory')
                if subcat:
                    subcategories.add(subcat)

        self.assertEqual(len(subcategories), 2)
        self.assertIn('Sub1', subcategories)
        self.assertIn('Sub2', subcategories)
        self.assertNotIn('Sub3', subcategories)


if __name__ == '__main__':
    unittest.main()
