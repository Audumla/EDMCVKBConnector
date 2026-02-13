"""
Real VKB Server Integration Tests

Tests against actual VKB hardware via VKB-Link TCP/IP server.
These tests are OPTIONAL and require VKB hardware + VKB-Link running.

Configuration:
  Environment variables (or create .env file):
    TEST_VKB_HOST - VKB server host (default: 127.0.0.1)
    TEST_VKB_PORT - VKB server port (default: 50995)
    TEST_VKB_ENABLED - Set to "1" to enable real server tests (default: 0)

Usage:
  pytest test_real_vkb_server.py -v                    # Run if configured
  TEST_VKB_ENABLED=1 pytest test_real_vkb_server.py   # Force run
  pytest test_real_vkb_server.py -v -k "not real"     # Skip real tests
"""

import sys
import os
import time
import socket
from pathlib import Path
from contextlib import contextmanager

# Load .env file if it exists
def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())

load_env_file()

from edmcvkbconnector.config import Config
from edmcvkbconnector.vkb_client import VKBClient
from edmcvkbconnector.event_handler import EventHandler


# Configuration
TEST_VKB_HOST = os.environ.get("TEST_VKB_HOST", "127.0.0.1")
TEST_VKB_PORT = int(os.environ.get("TEST_VKB_PORT", 50995))
TEST_VKB_ENABLED = os.environ.get("TEST_VKB_ENABLED", "0") == "1"


def check_server_available(host=TEST_VKB_HOST, port=TEST_VKB_PORT) -> bool:
    """Check if VKB server is accessible."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def skip_if_no_real_server(func):
    """Decorator to skip test if real VKB server not available."""
    def wrapper():
        if not TEST_VKB_ENABLED:
            print(f"\nSKIP: Real VKB server tests disabled")
            print(f"      To enable: set TEST_VKB_ENABLED=1")
            return
        
        if not check_server_available():
            print(f"\nSKIP: VKB server not available at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
            print(f"      Start VKB-Link and try again")
            return
        
        print(f"\nRUNNING: Real VKB server test at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
        return func()
    
    return wrapper


@skip_if_no_real_server
def test_real_server_connection():
    """Test connection to actual VKB hardware."""
    print(f"Test: Connect to real VKB server at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
    
    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        initial_retry_interval=1,
        initial_retry_duration=5,
        fallback_retry_interval=1,
        socket_timeout=5,
    )
    
    try:
        success = client.connect()
        assert success, f"Failed to connect to {TEST_VKB_HOST}:{TEST_VKB_PORT}"
        assert client.connected, "Client reports not connected"
        
        print(f"  [OK] Connected to {TEST_VKB_HOST}:{TEST_VKB_PORT}")
        
        # Give hardware time to respond
        time.sleep(0.5)
        
    finally:
        client.disconnect()
        assert not client.connected, "Client should be disconnected"
        print(f"  [OK] Disconnected cleanly")


@skip_if_no_real_server
def test_real_server_send_shift_state():
    """Send shift state to real VKB hardware and verify."""
    print(f"Test: Send shift state to real VKB hardware")
    
    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )
    
    try:
        assert client.connect(), "Failed to connect"
        
        # Send shift state 1
        success = client.send_event(
            "VKBShiftBitmap",
            {"shift": 1, "subshift": 0}
        )
        assert success, "Failed to send shift=1"
        print(f"  [OK] Sent shift=1 to hardware")
        
        time.sleep(0.5)
        
        # Send shift state 2
        success = client.send_event(
            "VKBShiftBitmap",
            {"shift": 2, "subshift": 0}
        )
        assert success, "Failed to send shift=2"
        print(f"  [OK] Sent shift=2 to hardware")
        
        time.sleep(0.5)
        
        # Reset shift state 0
        success = client.send_event(
            "VKBShiftBitmap",
            {"shift": 0, "subshift": 0}
        )
        assert success, "Failed to reset shift"
        print(f"  [OK] Reset shift to 0")
        
    finally:
        client.disconnect()


@skip_if_no_real_server
def test_real_server_multiple_shifts():
    """Test all shift states on real hardware."""
    print(f"Test: Send all shift states to hardware")
    
    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )
    
    try:
        assert client.connect(), "Failed to connect"
        
        messages_sent = 0
        for shift in range(8):
            for subshift in range(2):
                success = client.send_event(
                    "VKBShiftBitmap",
                    {"shift": shift, "subshift": subshift}
                )
                if success:
                    messages_sent += 1
                    print(f"  [OK] Shift={shift}, SubShift={subshift}")
                    time.sleep(0.2)  # Brief pause between inputs
        
        print(f"  [OK] Sent {messages_sent} shift combinations")
        assert messages_sent > 0, "No messages sent successfully"
        
    finally:
        # Reset
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        client.disconnect()


@skip_if_no_real_server
def test_real_server_event_handler():
    """Test EventHandler with real VKB hardware."""
    print(f"Test: EventHandler with real VKB hardware")
    
    config = Config()
    handler = EventHandler(config)
    
    # Override connection settings
    handler.vkb_client.host = TEST_VKB_HOST
    handler.vkb_client.port = TEST_VKB_PORT
    
    try:
        success = handler.connect()
        assert success, f"EventHandler failed to connect"
        
        # Send some journal events
        handler.handle_event(
            "FSDJump",
            {
                "event": "FSDJump",
                "StarSystem": "Test System",
                "JumpDist": 10.5,
            },
            source="journal",
            cmdr="TestCmdr",
            is_beta=False,
        )
        print(f"  [OK] Sent FSDJump event")
        time.sleep(0.5)
        
        # Send location event
        handler.handle_event(
            "Location",
            {
                "event": "Location",
                "StarSystem": "Test System",
            },
            source="journal",
            cmdr="TestCmdr",
            is_beta=False,
        )
        print(f"  [OK] Sent Location event")
        time.sleep(0.5)
        
    finally:
        handler.disconnect()


@skip_if_no_real_server
def test_real_server_persistence():
    """Test connection persistence across multiple operations."""
    print(f"Test: Connection persistence on real hardware")
    
    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )
    
    try:
        assert client.connect(), "Failed to connect"
        
        # Perform multiple operations
        operations = 0
        for i in range(5):
            success = client.send_event(
                "VKBShiftBitmap",
                {"shift": i % 8, "subshift": 0}
            )
            if success:
                operations += 1
            time.sleep(0.3)
        
        assert client.connected, "Connection lost during operations"
        assert operations == 5, f"Only {operations}/5 operations succeeded"
        print(f"  [OK] Connection remained stable across {operations} operations")
        
    finally:
        client.disconnect()


@skip_if_no_real_server
def test_real_server_rapid_messages():
    """Test rapid message transmission to real hardware."""
    print(f"Test: Rapid message transmission to hardware")
    
    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )
    
    try:
        assert client.connect(), "Failed to connect"
        
        # Send messages rapidly
        sent = 0
        for i in range(10):
            success = client.send_event(
                "VKBShiftBitmap",
                {"shift": i % 8, "subshift": (i // 8) % 2}
            )
            if success:
                sent += 1
        
        print(f"  [OK] Sent {sent}/10 rapid messages")
        assert sent > 0, "No messages sent"
        
    finally:
        # Reset
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        client.disconnect()


def main():
    """Run real VKB server tests if configured."""
    print("\n" + "="*60)
    print("Real VKB Server Integration Tests")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Host: {TEST_VKB_HOST}")
    print(f"  Port: {TEST_VKB_PORT}")
    print(f"  Enabled: {TEST_VKB_ENABLED}")
    print()
    
    if not TEST_VKB_ENABLED:
        print("Real VKB server tests are DISABLED.")
        print("To enable, set environment variable: TEST_VKB_ENABLED=1")
        print("\nExample:")
        print("  $env:TEST_VKB_ENABLED = '1'; python test_real_vkb_server.py")
        print("\nOr configure in .env file:")
        print("  TEST_VKB_ENABLED=1")
        print("  TEST_VKB_HOST=127.0.0.1")
        print("  TEST_VKB_PORT=50995")
        return 0
    
    if not check_server_available():
        print(f"ERROR: VKB server not available at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
        print("\nTo test with real VKB hardware:")
        print("  1. Start VKB-Link with TCP/IP enabled")
        print("  2. Verify it's accessible at the configured host/port")
        print("  3. Run tests again")
        return 1
    
    print(f"VKB server FOUND at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
    print("Running real hardware tests...\n")
    
    tests = [
        ("Real server connection", test_real_server_connection),
        ("Real server shift state", test_real_server_send_shift_state),
        ("Real server multiple shifts", test_real_server_multiple_shifts),
        ("Real server EventHandler", test_real_server_event_handler),
        ("Real server persistence", test_real_server_persistence),
        ("Real server rapid messages", test_real_server_rapid_messages),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{test_name}:")
            test_func()
            print(f"  PASS")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
