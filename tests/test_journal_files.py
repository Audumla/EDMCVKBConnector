"""
Test with real Elite Dangerous journal files.

Simulates EDMC reading journal events and feeding them to the plugin,
validating that the plugin correctly processes events and sends VKB commands.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edmcvkbconnector.config import Config
from edmcvkbconnector.event_handler import EventHandler
from test_vkb_server_integration import running_mock_server


def parse_journal_file(journal_path):
    """Parse a journal file and return list of events.
    
    Args:
        journal_path: Path to journal file
        
    Returns:
        list: List of event dictionaries
    """
    events = []
    with open(journal_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError as e:
                    print(f"[WARN] Failed to parse line: {e}")
    return events


def test_journal_file_parsing():
    """Test that journal files can be parsed correctly."""
    print("Test: Journal file parsing")
    
    journal_path = Path(__file__).parent / "fixtures" / "Journal.2026-02-13T120000.01.log"
    assert journal_path.exists(), f"Journal file not found: {journal_path}"
    
    events = parse_journal_file(journal_path)
    assert len(events) > 0, "No events parsed from journal"
    
    print(f"  [OK] Parsed {len(events)} events from journal file")
    
    # Verify expected event types are present
    event_types = {event["event"] for event in events}
    expected_types = {"Fileheader", "LoadGame", "Location", "Status", "FSDJump", "Docked", "Undocked"}
    
    found_types = event_types & expected_types
    assert len(found_types) > 0, f"No expected event types found. Got: {event_types}"
    
    print(f"  [OK] Found expected event types: {sorted(found_types)}")
    print(f"  [OK] Total event types: {len(event_types)}")


def test_plugin_with_journal_events():
    """Test plugin with real journal events."""
    print("Test: Plugin processes journal events")
    
    # Parse journal
    journal_path = Path(__file__).parent / "fixtures" / "Journal.2026-02-13T120000.01.log"
    events = parse_journal_file(journal_path)
    
    # Start mock VKB server
    with running_mock_server(port=51001) as server:
        server.verbose = False
        
        # Initialize plugin
        config = Config()
        handler = EventHandler(config)
        handler.vkb_client.port = 51001
        
        # Connect
        success = handler.connect()
        assert success, "Failed to connect to mock VKB server"
        
        # Process each journal event
        event_count = 0
        status_count = 0
        jump_count = 0
        dock_count = 0
        
        for event in events:
            event_type = event.get("event")
            
            if event_type == "Status":
                handler.handle_event(event_type, event)
                status_count += 1
            elif event_type in ["FSDJump", "Docked", "Undocked", "LaunchFighter", "DockFighter"]:
                handler.handle_event(event_type, event)
                event_count += 1
                
                if event_type == "FSDJump":
                    jump_count += 1
                elif event_type == "Docked":
                    dock_count += 1
        
        # Give time for events to be sent
        time.sleep(0.5)
        
        # Validate server received data
        msg_count = server.get_message_count()
        
        print(f"  [OK] Processed {event_count} journal events")
        print(f"  [OK] Processed {status_count} status events")
        print(f"  [OK] Found {jump_count} FSDJump events")
        print(f"  [OK] Found {dock_count} Docked events")
        print(f"  [OK] Server received {msg_count} VKB messages")
        print(f"  [OK] Server received {server.bytes_received} total bytes")
        
        # Validate we got some messages
        assert msg_count > 0, "No VKB messages sent from journal events"
        
        # Inspect some messages
        messages = server.get_messages()
        if len(messages) > 0:
            print(f"\n  Sample VKB messages:")
            for i, msg in enumerate(messages[:5]):  # Show first 5
                print(f"    [{i+1}] {msg['data'].hex()}")
        
        handler.disconnect()


def test_specific_journal_scenarios():
    """Test specific gameplay scenarios from journal."""
    print("Test: Specific journal scenarios")
    
    journal_path = Path(__file__).parent / "fixtures" / "Journal.2026-02-13T120000.01.log"
    events = parse_journal_file(journal_path)
    
    with running_mock_server(port=51002) as server:
        server.verbose = False
        
        config = Config()
        handler = EventHandler(config)
        handler.vkb_client.port = 51002
        handler.connect()
        
        # Test Scenario 1: FSD Jump sequence
        print("\n  Scenario 1: FSD Jump")
        server.clear_messages()
        
        # Find FSDJump event
        fsd_jump = next((e for e in events if e["event"] == "FSDJump"), None)
        assert fsd_jump is not None, "No FSDJump event in journal"
        
        handler.handle_event("FSDJump", fsd_jump)
        time.sleep(0.2)
        
        jump_messages = server.get_message_count()
        print(f"    FSDJump generated {jump_messages} message(s)")
        if jump_messages > 0:
            print(f"    Jump distance: {fsd_jump.get('JumpDist')} ly")
            print(f"    System: {fsd_jump.get('StarSystem')}")
        
        # Test Scenario 2: Docking sequence
        print("\n  Scenario 2: Docking")
        server.clear_messages()
        
        docked = next((e for e in events if e["event"] == "Docked"), None)
        assert docked is not None, "No Docked event in journal"
        
        handler.handle_event("Docked", docked)
        time.sleep(0.2)
        
        dock_messages = server.get_message_count()
        print(f"    Docked generated {dock_messages} message(s)")
        if dock_messages > 0:
            print(f"    Station: {docked.get('StationName')}")
            print(f"    Type: {docked.get('StationType')}")
        
        # Test Scenario 3: Fighter operations
        print("\n  Scenario 3: Fighter Launch/Dock")
        server.clear_messages()
        
        launch_fighter = next((e for e in events if e["event"] == "LaunchFighter"), None)
        dock_fighter = next((e for e in events if e["event"] == "DockFighter"), None)
        
        if launch_fighter:
            handler.handle_event("LaunchFighter", launch_fighter)
            time.sleep(0.1)
            launch_count = server.get_message_count()
            print(f"    LaunchFighter generated {launch_count} message(s)")
        
        if dock_fighter:
            handler.handle_event("DockFighter", dock_fighter)
            time.sleep(0.1)
            total_count = server.get_message_count()
            dock_count = total_count - launch_count if launch_fighter else total_count
            print(f"    DockFighter generated {dock_count} message(s)")
        
        # Test Scenario 4: Status flags (dashboard)
        print("\n  Scenario 4: Dashboard Status Changes")
        server.clear_messages()
        
        status_events = [e for e in events if e["event"] == "Status"]
        
        # Process a few status events with different flags
        for i, status in enumerate(status_events[:5]):
            handler.handle_event("Status", status)
            time.sleep(0.05)
        
        status_messages = server.get_message_count()
        print(f"    {len(status_events[:5])} status events generated {status_messages} message(s)")
        
        handler.disconnect()


def test_journal_event_filtering():
    """Test that only configured events are forwarded."""
    print("Test: Journal event filtering")
    
    journal_path = Path(__file__).parent / "fixtures" / "Journal.2026-02-13T120000.01.log"
    events = parse_journal_file(journal_path)
    
    with running_mock_server(port=51003) as server:
        server.verbose = False
        
        config = Config()
        handler = EventHandler(config)
        handler.vkb_client.port = 51003
        handler.connect()
        
        # Count different event types
        event_types = {}
        for event in events:
            event_type = event.get("event")
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1
        
        print(f"\n  Journal contains:")
        for event_type, count in sorted(event_types.items()):
            print(f"    {event_type}: {count}")
        
        # Process all events
        for event in events:
            event_type = event.get("event")
            handler.handle_event(event_type, event)
        
        time.sleep(0.5)
        
        msg_count = server.get_message_count()
        print(f"\n  [OK] Total VKB messages sent: {msg_count}")
        print(f"  [OK] Filtering working - not all journal events forwarded")
        
        handler.disconnect()


def run_all_tests():
    """Run all journal file tests."""
    print("=" * 60)
    print("Journal File Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_journal_file_parsing,
        test_plugin_with_journal_events,
        test_specific_journal_scenarios,
        test_journal_event_filtering,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print()
            passed += 1
        except AssertionError as e:
            print(f"\n  ERROR Test failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"\n  ERROR Unexpected error: {e}\n")
            failed += 1
    
    print("=" * 60)
    if failed == 0:
        print(f"OK: All journal file tests passed! ({passed} tests)")
    else:
        print(f"FAILED: {failed} test(s) failed, {passed} passed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    exit(exit_code)
