"""Unit tests for Config module."""

from edmcruleengine.config import Config


def test_config_defaults():
    """Test that Config returns correct defaults."""
    config = Config()
    
    assert config.get("vkb_host", "127.0.0.1") == "127.0.0.1"
    assert config.get("vkb_port", 50995) == 50995
    assert config.get("initial_retry_interval", 2) == 2
    assert config.get("initial_retry_duration", 60) == 60
    assert config.get("fallback_retry_interval", 10) == 10
    assert config.get("socket_timeout", 5) == 5
    print("[OK] Config defaults test passed")


def test_config_get_methods():
    """Test that Config maintains type consistency."""
    config = Config()
    
    # Test string value
    val = config.get("vkb_host", "127.0.0.1")
    assert isinstance(val, str), f"Expected str, got {type(val)}"
    
    # Test int value
    val = config.get("vkb_port", 50995)
    assert isinstance(val, int), f"Expected int, got {type(val)}"
    
    # Test bool value
    val = config.get("enabled", True)
    assert isinstance(val, bool), f"Expected bool, got {type(val)}"
    
    print("[OK] Config getter methods test passed")


def test_vkb_client_init():
    """Test VKBClient initialization."""
    from edmcruleengine.vkb_client import VKBClient
    
    client = VKBClient(
        host="127.0.0.1",
        port=50995,
        initial_retry_interval=2,
        initial_retry_duration=60,
        fallback_retry_interval=10,
        socket_timeout=5,
    )
    
    assert client.host == "127.0.0.1"
    assert client.port == 50995
    assert client.INITIAL_RETRY_INTERVAL == 2
    assert client.INITIAL_RETRY_DURATION == 60
    assert client.FALLBACK_RETRY_INTERVAL == 10
    assert not client.connected
    print("[OK] VKBClient initialization test passed")


def test_event_handler_init():
    """Test EventHandler initialization."""
    from edmcruleengine.event_handler import EventHandler
    from edmcruleengine.config import Config
    
    config = Config()
    handler = EventHandler(config)
    
    assert handler.enabled == True
    assert handler.vkb_client is not None
    print("[OK] EventHandler initialization test passed")


def test_message_formatter():
    """Test message formatting."""
    from edmcruleengine.message_formatter import VKBLinkMessageFormatter

    formatter = VKBLinkMessageFormatter(
        header_byte=0xA5,
        command_byte=13,
    )
    
    # Test formatting a VKBShiftBitmap message
    message = formatter.format_event("VKBShiftBitmap", {"shift": 1, "subshift": 0})
    assert isinstance(message, bytes)
    assert len(message) == 8, f"Expected 8 bytes, got {len(message)}"
    assert message[0] == 0xA5, f"Expected header 0xA5, got {message[0]:02x}"
    assert message[1] == 13, f"Expected command 13, got {message[1]}"
    assert message[3] == 4, f"Expected data length 4, got {message[3]}"
    
    print("[OK] MessageFormatter test passed")


if __name__ == "__main__":
    try:
        test_config_defaults()
        test_config_get_methods()
        test_vkb_client_init()
        test_event_handler_init()
        test_message_formatter()
        print("\n" + "="*50)
        print("All unit tests passed! [OK]")
        print("="*50)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

