"""
Test the events configuration loading (no tkinter required).
"""

import sys
import os
from pathlib import Path

# Add source paths
plugin_root = Path(__file__).parent.parent
src_path = plugin_root / "src"
sys.path.insert(0, str(src_path))

import json

def test_events_config_file():
    """Test that events_config.json is valid and well-formed."""
    config_path = plugin_root / "events_config.json"
    
    print(f"Loading events config from: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        print("✓ events_config.json is valid JSON")
        
        # Validate structure
        required_keys = ["sources", "events", "condition_types", "shift_flags"]
        for key in required_keys:
            if key not in config:
                print(f"✗ Missing required key: {key}")
                return False
            print(f"✓ Has key: {key}")
        
        # Check sources
        sources = config["sources"]
        print(f"\n  Sources ({len(sources)}):")
        for source in sources:
            print(f"    - {source.get('id')}: {source.get('name')}")
        
        # Check events
        events = config["events"]
        print(f"\n  Events ({len(events)}):")
        
        # Group by source
        by_source = {}
        for event in events:
            source = event.get("source", "unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(event)
        
        for source, events_list in sorted(by_source.items()):
            print(f"    {source}: {len(events_list)} events")
        
        # Check condition types
        condition_types = config["condition_types"]
        print(f"\n  Condition Types ({len(condition_types)}):")
        for ct in condition_types:
            print(f"    - {ct.get('id')}: {ct.get('name')}")
        
        # Check shift flags
        shift_flags = config["shift_flags"]
        print(f"\n  Shift Flags ({len(shift_flags)}):")
        print(f"    {', '.join(shift_flags)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rules_engine_imports():
    """Test that we can import FLAGS and other dicts from rules_engine."""
    try:
        from edmcruleengine.rules_engine import FLAGS, FLAGS2, GUI_FOCUS_NAME_TO_VALUE
        
        print("\n✓ Successfully imported from rules_engine")
        print(f"  FLAGS: {len(FLAGS)} flags")
        print(f"  FLAGS2: {len(FLAGS2)} flags")
        print(f"  GUI_FOCUS_NAME_TO_VALUE: {len(GUI_FOCUS_NAME_TO_VALUE)} focus states")
        
        return True
    except Exception as e:
        print(f"✗ Error importing from rules_engine: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sample_rule_structure():
    """Test that sample rules have the expected structure."""
    rules_path = plugin_root / "rules.json.example"
    
    if not rules_path.exists():
        print(f"Note: {rules_path} does not exist, skipping")
        return True
    
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        rules = data if isinstance(data, list) else data.get("rules", [])
        
        print(f"\n✓ Sample rules file loaded ({len(rules)} rules)")
        
        for i, rule in enumerate(rules):
            rule_id = rule.get("id", f"<rule-{i}>")
            print(f"\n  Rule: {rule_id}")
            print(f"    Enabled: {rule.get('enabled', True)}")
            
            when = rule.get("when", {})
            if when:
                print(f"    When:")
                if "source" in when:
                    print(f"      source: {when['source']}")
                if "event" in when:
                    print(f"      event: {when['event']}")
                if "all" in when:
                    print(f"      all blocks: {len(when['all'])}")
                if "any" in when:
                    print(f"      any blocks: {len(when['any'])}")
            
            then_actions = rule.get("then", {})
            if then_actions:
                print(f"    Then: {list(then_actions.keys())}")
            
            else_actions = rule.get("else", {})
            if else_actions:
                print(f"    Else: {list(else_actions.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading sample rules: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Rule Editor Components (No UI)...")
    print(f"Plugin root: {plugin_root}\n")
    
    all_passed = True
    
    print("=== Test 1: Events Config File ===")
    all_passed &= test_events_config_file()
    
    print("\n=== Test 2: Rules Engine Imports ===")
    all_passed &= test_rules_engine_imports()
    
    print("\n=== Test 3: Sample Rules Structure ===")
    all_passed &= test_sample_rule_structure()
    
    if all_passed:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
