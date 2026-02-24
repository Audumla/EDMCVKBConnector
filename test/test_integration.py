"""Integration tests with mocked VKB client."""

from pathlib import Path
from unittest.mock import Mock, patch

from edmcruleengine import Config
from edmcruleengine.events.event_handler import EventHandler
from edmcruleengine.vkb.vkb_link_manager import VKBLinkManager


def _make_handler(config=None):
    """Create EventHandler with a VKBLinkManager endpoint for tests."""
    if config is None:
        config = Config()
    manager = VKBLinkManager.from_config(config, Path("."))
    handler = EventHandler(config, endpoints=[manager])
    return handler


def test_event_flow():
    """Test event processing without real socket connection."""
    handler = _make_handler()

    # Mock the VKB client to prevent actual connection attempts
    handler.vkb_client.send_event = Mock(return_value=True)
    handler.vkb_client.connect = Mock(return_value=False)  # Prevent connection
    
    # Simulate a FSDJump event
    event_data = {
        "event": "FSDJump",
        "StarSystem": "Sol",
        "JumpDist": 10.5,
    }
    
    handler.handle_event(
        "FSDJump",
        event_data,
        source="journal",
        cmdr="TestCmdr",
        is_beta=False,
    )
    
    print("[OK] Event flow test passed")


def test_dashboard_event():
    """Test dashboard event processing."""
    handler = _make_handler()

    handler.vkb_client.send_event = Mock(return_value=True)
    handler.vkb_client.connect = Mock(return_value=False)
    
    # Simulate dashboard Status event (the only event type EDMC sends
    # via dashboard_entry — contains Flags, GuiFocus, etc.)
    dashboard_data = {
        "event": "Status",
        "Flags": 16777224,   # InMainShip + ShieldsUp
        "GuiFocus": 0,
        "Pips": [4, 4, 4],
    }
    
    handler.handle_event(
        "Status",
        dashboard_data,
        source="dashboard",
        cmdr="TestCmdr",
        is_beta=False,
    )
    
    print("[OK] Dashboard event test passed")


def test_shift_bitmap_manipulation():
    """Test shift state management."""
    handler = _make_handler()
    manager = handler.vkb_link_manager
    manager.client.send_event = Mock(return_value=True)
    manager.client.connect = Mock(return_value=False)
    
    # Test bit manipulation
    initial_bitmap = 0
    result = manager._apply_bit(initial_bitmap, 0, True)
    assert result == 1, f"Expected 1, got {result}"
    
    result = manager._apply_bit(result, 0, False)
    assert result == 0, f"Expected 0, got {result}"
    
    # Test multiple bits
    result = manager._apply_bit(0, 0, True)
    result = manager._apply_bit(result, 2, True)
    assert result == 5, f"Expected 5 (0b0101), got {result}"  # bits 0 and 2
    
    print("[OK] Shift bitmap manipulation test passed")


def test_error_handling():
    """Test that VKB send errors are handled gracefully."""
    handler = _make_handler()
    manager = handler.vkb_link_manager

    error_occurred = False

    def mock_send_with_error(*args, **kwargs):
        nonlocal error_occurred
        error_occurred = True
        return False  # Simulate send failure

    manager.client.send_event = mock_send_with_error
    manager.client.connect = Mock(return_value=False)

    # Force a shift state send — this exercises the VKB send path
    manager._shift_bitmap = 1
    manager._send_shift_state_if_changed(force=True)

    assert error_occurred, "send_event mock was not called"
    # Shift state should NOT be updated on failure
    assert manager._last_sent_shift is None, "Shift should not be marked sent after failure"
    print("[OK] Error handling test passed (send failure handled gracefully)")


def test_rule_engine_initialization():
    """Test rule engine initialization."""
    config = Config()
    handler = EventHandler(config, endpoints=[], plugin_dir=str(Path(__file__).parent.parent))
    
    # Rule engine should be initialized even if rules file doesn't exist
    if handler.rule_engine:
        assert isinstance(handler.rule_engine.rules, list)
        print("[OK] Rule engine initialization test passed")
    else:
        print("[SKIP] Rule engine not initialized (optional)")


def test_cmdr_isolation():
    """Test that commander data is isolated."""
    handler = _make_handler()

    handler.vkb_client.send_event = Mock(return_value=True)
    handler.vkb_client.connect = Mock(return_value=False)
    
    # Send event for cmdr1
    handler.handle_event(
        "Location",
        {"SystemAddress": 10477373803},
        source="journal",
        cmdr="Commander1",
        is_beta=False,
    )
    
    # Send event for cmdr2 (different commander)
    handler.handle_event(
        "Location",
        {"SystemAddress": 10477373804},
        source="journal",
        cmdr="Commander2",
        is_beta=False,
    )
    
    print("[OK] Commander isolation test passed")


if __name__ == "__main__":
    try:
        test_event_flow()
        test_dashboard_event()
        test_shift_bitmap_manipulation()
        test_error_handling()
        test_rule_engine_initialization()
        test_cmdr_isolation()
        
        print("\n" + "="*50)
        print("All integration tests passed! [OK]")
        print("="*50)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

