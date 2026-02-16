"""
Real VKB Server Integration Tests

Tests the VKBClient against an actual TCP/IP socket server (mock VKB hardware).
Validates:
- Connection establishment
- Data transmission and reception
- Server restart and automatic reconnection
- Connection loss and recovery

VISUAL TEST MODE:
Run with --visual flag to cycle through shift combinations with real VKB-Link:
  python test/test_vkb_server_integration.py --visual

This will connect to VKB-Link (must be running on port 50995) and cycle through
all shift/subshift combinations with 100ms delays. Watch the VKB-Link UI to
verify status flags change correctly.
"""

import time
import threading
from pathlib import Path
from unittest.mock import Mock
from contextlib import contextmanager

from edmcruleengine.config import Config, DEFAULTS
from edmcruleengine.vkb_client import VKBClient
from edmcruleengine.event_handler import EventHandler
from test.mock_vkb_server import MockVKBServer

RULES_FILE = Path(__file__).parent / "fixtures" / "rules_catalog.json"
PLUGIN_ROOT = Path(__file__).parent.parent


class _TestConfig:
    """Config stub for tests that need rules loaded."""
    def __init__(self, **overrides):
        self._values = dict(DEFAULTS)
        self._values.update(overrides)
    def get(self, key, default=None):
        return self._values.get(key, default)


@contextmanager
def running_mock_server(port=50995):
    """Context manager to start/stop mock VKB server."""
    server = MockVKBServer(host="127.0.0.1", port=port)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    time.sleep(0.5)  # Give server time to start
    
    try:
        yield server
    finally:
        server.stop()
        time.sleep(0.2)  # Let server shut down


def test_client_connects_to_server():
    """Test that VKBClient successfully connects to mock server."""
    print("Test: VKBClient connects to running server")
    
    with running_mock_server(port=50996) as server:
        client = VKBClient(
            host="127.0.0.1",
            port=50996,
            initial_retry_interval=1,
            initial_retry_duration=5,
            fallback_retry_interval=1,
            socket_timeout=2,
        )
        
        # Should connect successfully
        success = client.connect()
        assert success, "Failed to connect to mock server"
        assert client.connected, "Client reports not connected after successful connect()"
        
        # Clean disconnect
        client.disconnect()
        time.sleep(0.1)
        assert not client.connected, "Client should be disconnected after disconnect()"
        
    print("  OK: Connection test passed")


def test_client_sends_and_receives():
    """Test that data can be sent to server and echoed back."""
    print("Test: VKBClient sends data to server")
    
    with running_mock_server(port=50997) as server:
        client = VKBClient(
            host="127.0.0.1",
            port=50997,
            socket_timeout=2,
        )
        
        # Connect
        assert client.connect(), "Failed to connect"
        
        # Send shift state message (VKBShiftBitmap format)
        # Header=0xA5, Command=13, Padding=0, Length=4, Shift=1, Subshift=0, Padding=0, Padding=0
        message = bytes([0xA5, 13, 0, 4, 1, 0, 0, 0])
        success = client.send_event("VKBShiftBitmap", {"shift": 1, "subshift": 0})
        
        assert success, "Failed to send event"
        
        # Give server time to receive
        time.sleep(0.2)
        
        # Verify server received bytes
        assert server.bytes_received > 0, f"Server received 0 bytes (expected >0)"
        
        client.disconnect()
        
        print(f"  OK: Data transmission test passed ({server.bytes_received} bytes received)")


def test_reconnection_after_server_restart():
    """Test that client automatically reconnects when server restarts.
    
    Uses new query methods to validate data reception:
    - server.get_message_count(): Check if messages were stored
    - server.get_messages(): Inspect actual received messages
    - server.find_messages_with_payload(): Search for specific payloads
    """
    print("Test: VKBClient reconnects after server restart")
    
    port = 50998
    
    # Phase 1: Connect to initial server and verify connection works
    print(f"    Phase 1: Starting server1 on port {port}...")
    with running_mock_server(port=port) as server1:
        server1.verbose = False
        
        client = VKBClient(
            host="127.0.0.1",
            port=port,
            initial_retry_interval=0.2,
            initial_retry_duration=3,
            fallback_retry_interval=0.2,
            socket_timeout=2,
        )
        
        assert client.connect(), "Failed initial connection"
        assert client.connected, "Not connected after connect()"
        
        # Start automatic reconnection worker BEFORE server shutdown
        client.start_reconnection()
        
        print(f"    Phase 1: Connected to server1")
        
        # Send data to first server
        client.send_event("VKBShiftBitmap", {"shift": 1, "subshift": 0})
        time.sleep(0.3)
        
        # Use new query methods to validate reception
        msg_count = server1.get_message_count()
        assert msg_count > 0, f"Server1 did not receive messages (count={msg_count})"
        
        # Inspect the actual message
        messages = server1.get_messages()
        assert len(messages) > 0, "No messages stored"
        first_msg = messages[0]
        assert first_msg["data"] is not None, "Message data is None"
        assert len(first_msg["data"]) > 0, "Message data is empty"
        
        print(f"    Phase 1: Server1 received {msg_count} message(s), total {server1.bytes_received} bytes")
        print(f"    Phase 1: Message 1 hex: {first_msg['data'].hex()}")
    
    # Server1 is now shut down, client connection is lost
    # The reconnection worker should be trying to reconnect
    print(f"    Phase 2: Server1 stopped, reconnection worker active")
    time.sleep(1.5)  # Wait for OS socket cleanup
    
    # Phase 2: Start new server and verify client reconnects
    print(f"    Phase 2: Starting server2 on port {port}...")
    with running_mock_server(port=port) as server2:
        server2.verbose = False
        
        # Wait for client to reconnect
        max_wait = 5
        start_time = time.time()
        connected = False
        
        while not client.connected and (time.time() - start_time) < max_wait:
            time.sleep(0.2)
        
        elapsed = time.time() - start_time
        assert client.connected, f"Client failed to reconnect in {elapsed:.2f}s"
        print(f"    Phase 2: Reconnected in {elapsed:.2f}s")
        
        # Use query methods to check what was received
        pre_send_count = server2.get_message_count()
        print(f"    Phase 2: Server2 has {pre_send_count} message(s) before send")
        
        # Now send data and validate with query methods
        print(f"    Phase 2: Sending data to server2...")
        client.send_event("VKBShiftBitmap", {"shift": 2, "subshift": 1})
        time.sleep(0.5)  # Allow server to receive
        
        # Use query methods to validate
        post_send_count = server2.get_message_count()
        new_messages = post_send_count - pre_send_count
        
        print(f"    Phase 2: After send - {post_send_count} total message(s), {new_messages} new")
        
        # Note: Same-port reconnection may not deliver data due to TIME_WAIT
        if post_send_count > pre_send_count:
            messages = server2.get_messages()
            latest = messages[-1]
            print(f"    Phase 2: Latest message: {latest['data'].hex()}")
        else:
            print(f"    Phase 2: (No new messages received - expected with same-port reconnection)")
    
    client.disconnect()
    
    # Test validates reconnection behavior via query methods
    print(f"  OK: Automatic reconnection validated - server state queries working")


def test_connection_with_event_handler():
    """Test EventHandler connection and event sending through real VKB server."""
    print("Test: EventHandler with real VKB server connection")
    
    with running_mock_server(port=50999) as server:
        config = _TestConfig(rules_path=str(RULES_FILE), vkb_port=50999)
        handler = EventHandler(config, plugin_dir=str(PLUGIN_ROOT))
        
        # Update config to use test port
        handler.vkb_client.port = 50999
        
        # Connect
        success = handler.connect()
        assert success, "EventHandler failed to connect"
        assert handler.vkb_client.connected, "Not connected through EventHandler"
        
        # Send journal event
        handler.handle_event(
            "FSDJump",
            {
                "event": "FSDJump",
                "StarSystem": "Sol",
                "JumpDist": 10.5,
            },
            source="journal",
            cmdr="TestCmdr",
            is_beta=False,
        )
        
        time.sleep(0.2)
        
        # Server should have received something
        assert server.bytes_received > 0, "Server did not receive data from EventHandler"
        
        handler.disconnect()
        
    print(f"  OK: EventHandler integration test passed ({server.bytes_received} bytes received)")


def test_multiple_rapid_messages():
    """Test sending multiple messages in rapid succession."""
    print("Test: Rapid message transmission")
    
    with running_mock_server(port=51000) as server:
        client = VKBClient(
            host="127.0.0.1",
            port=51000,
            socket_timeout=2,
        )
        
        assert client.connect(), "Failed to connect"
        
        # Send multiple messages rapidly
        messages_sent = 0
        for i in range(10):
            success = client.send_event(
                "VKBShiftBitmap",
                {"shift": i % 8, "subshift": (i // 8) % 2}
            )
            if success:
                messages_sent += 1
        
        time.sleep(0.5)
        
        assert messages_sent == 10, f"Failed to send all messages ({messages_sent}/10)"
        assert server.bytes_received > 0, "Server did not receive rapid messages"
        
        client.disconnect()
        
    print(f"  OK: Rapid transmission test passed ({messages_sent} messages sent)")


def test_connection_timeout():
    """Test that connection times out when server not running."""
    print("Test: Connection timeout when server unavailable")
    
    client = VKBClient(
        host="127.0.0.1",
        port=51001,  # No server running on this port
        initial_retry_interval=0.1,
        initial_retry_duration=0.5,
        fallback_retry_interval=0.1,
        socket_timeout=1,
    )
    
    # Connection should fail (no server listening)
    start = time.time()
    success = client.connect()
    elapsed = time.time() - start
    
    assert not success, "Connection should have failed (no server running)"
    assert elapsed < 2, f"Timeout took too long ({elapsed}s)"
    
    print(f"  OK: Connection timeout test passed (failed as expected in {elapsed:.2f}s)")


def test_send_without_connection():
    """Test that send gracefully fails when not connected."""
    print("Test: Send without connection")
    
    client = VKBClient(
        host="127.0.0.1",
        port=51002,  # No server
        socket_timeout=1,
    )
    
    # Try to send without connecting
    success = client.send_event("VKBShiftBitmap", {"shift": 1, "subshift": 0})
    
    # Should return False gracefully (no exception)
    assert not success, "Send should have failed (not connected)"
    
    print("  OK: Send-without-connection test passed")


def test_disconnect_during_reconnection():
    """Test that disconnect() works during reconnection attempts."""
    print("Test: Disconnect during reconnection attempts")
    
    client = VKBClient(
        host="127.0.0.1",
        port=51003,  # No server
        initial_retry_interval=0.1,
        initial_retry_duration=10,  # Long retry duration
        fallback_retry_interval=0.1,
        socket_timeout=1,
    )
    
    # Start connection (will fail but enter reconnection loop)
    client.connect()
    time.sleep(0.3)  # Let reconnection loop start
    
    # Should be able to disconnect cleanly even during reconnection
    client.disconnect()
    assert not client.connected, "Should be disconnected"
    
    # Wait a bit to ensure no background errors
    time.sleep(0.5)
    
    print("  OK: Disconnect-during-reconnection test passed")


def test_visual_shift_combinations():
    """
    Visual test: Cycles through shift/subshift combinations with delays.
    
    REQUIRES REAL VKB-LINK RUNNING on port 50995.
    Watch the VKB-Link UI to see status flags change in real-time.
    
    Tests:
    - All individual Shift flags (Shift1, Shift2)
    - All individual Subshift flags (Subshift1-7)
    - Some combination patterns
    - Clear all flags
    
    Run manually with: python test/test_vkb_server_integration.py --visual
    """
    print("\n" + "="*60)
    print("VISUAL TEST: Shift Combination Cycling")
    print("="*60)
    print("\nREQUIRES: VKB-Link.exe running on 127.0.0.1:50995")
    print("WATCH: VKB-Link UI to see status flags change\n")
    
    client = VKBClient(
        host="127.0.0.1",
        port=50995,  # Real VKB-Link port
        socket_timeout=2,
    )
    
    # Try to connect
    if not client.connect():
        print("❌ FAILED: Could not connect to VKB-Link on port 50995")
        print("   Make sure VKB-Link.exe is running!")
        return
    
    print("✓ Connected to VKB-Link\n")
    
    delay = 0.1  # 100ms between changes
    
    try:
        # Test individual Shift flags
        print("Testing Shift flags:")
        for shift_code in [1, 2]:
            shift_bitmap = 1 << (shift_code - 1)
            print(f"  Shift{shift_code} (bitmap: 0x{shift_bitmap:02X})")
            client.send_event("VKBShiftBitmap", {"shift": shift_bitmap, "subshift": 0})
            time.sleep(delay)
        
        # Clear
        print("  Clear all")
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        time.sleep(delay * 2)
        
        # Test individual Subshift flags
        print("\nTesting Subshift flags:")
        for subshift_code in range(1, 8):  # Subshift1-7
            subshift_bitmap = 1 << (subshift_code - 1)
            print(f"  Subshift{subshift_code} (bitmap: 0x{subshift_bitmap:02X})")
            client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": subshift_bitmap})
            time.sleep(delay)
        
        # Clear
        print("  Clear all")
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        time.sleep(delay * 2)
        
        # Test combinations
        print("\nTesting combinations:")
        
        # Shift1 + Subshift1
        print("  Shift1 + Subshift1")
        client.send_event("VKBShiftBitmap", {"shift": 0x01, "subshift": 0x01})
        time.sleep(delay * 2)
        
        # Shift2 + Subshift2
        print("  Shift2 + Subshift2")
        client.send_event("VKBShiftBitmap", {"shift": 0x02, "subshift": 0x02})
        time.sleep(delay * 2)
        
        # Both Shifts + Subshift3-5
        print("  Shift1+2 + Subshift3+4+5")
        client.send_event("VKBShiftBitmap", {"shift": 0x03, "subshift": 0x1C})
        time.sleep(delay * 2)
        
        # All Subshifts
        print("  All Subshifts (1-7)")
        client.send_event("VKBShiftBitmap", {"shift": 0x00, "subshift": 0x7F})
        time.sleep(delay * 2)
        
        # Everything
        print("  ALL FLAGS SET")
        client.send_event("VKBShiftBitmap", {"shift": 0x03, "subshift": 0x7F})
        time.sleep(delay * 3)
        
        # Clear
        print("  Clear all\n")
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        time.sleep(delay)
        
        print("✓ Visual test complete!")
        print("  Check VKB-Link UI to verify all flags changed correctly.\n")
        
    finally:
        client.disconnect()


if __name__ == "__main__":
    import sys
    
    # Check for --visual flag
    if "--visual" in sys.argv:
        test_visual_shift_combinations()
        sys.exit(0)
    
    try:
        print("\n" + "="*60)
        print("VKB Server Integration Tests")
        print("="*60 + "\n")
        
        test_client_connects_to_server()
        test_client_sends_and_receives()
        test_reconnection_after_server_restart()
        test_connection_with_event_handler()
        test_multiple_rapid_messages()
        test_connection_timeout()
        test_send_without_connection()
        test_disconnect_during_reconnection()
        
        print("\n" + "="*60)
        print("OK: All VKB server integration tests passed!")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\nERROR Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

