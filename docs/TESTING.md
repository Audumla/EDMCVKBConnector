# Testing Guide for EDMCVKBConnector

## 📊 Complete Test Suite Overview

The project includes a comprehensive **4-layer test pyramid** with **25+ tests**:

```
Layer 4: Real Hardware Tests (6 tests)
         - VKB-Link TCP/IP connection
         - Shift state commands
         - Game event routing
         - [Optional, disabled by default]

Layer 3: Mock Socket Tests (8 tests)
         - TCP/IP operations simulation
         - Connection/reconnection logic
         - Data transmission validation

Layer 2: Integration Tests (6 tests)
         - Event processing flow
         - Rule engine evaluation
         - Error handling

Layer 1: Unit Tests (5 tests)
         - Config loading
         - Component initialization
```

**Duration**: ~14 seconds (unit + integration + mock server)  
**Real Hardware**: ~26 seconds (with Layer 4, if enabled)

### 📚 Documentation
- **[TEST_SUITE.md](TEST_SUITE.md)** - Complete test inventory (start here!)
- **[tests/REAL_SERVER_TESTS.md](tests/REAL_SERVER_TESTS.md)** - Real hardware setup
- **[REAL_SERVER_SETUP.md](REAL_SERVER_SETUP.md)** - Quick start guide

---

## Quick Start (TL;DR)

### Windows
```batch
REM Development tests (recommended)
test.bat dev

REM All tests except real hardware
test.bat all

REM Real hardware tests (requires VKB-Link)
set TEST_VKB_ENABLED=1
test.bat real

REM Specific suites
test.bat unit          # Layer 1 only
test.bat integration   # Layer 2 only
test.bat server        # Layer 3 only
test.bat real          # Layer 4 only
```

### macOS/Linux
```bash
# Run all tests
cd tests && python dev_test.py

# Or specific tests
python test_config.py                           # Unit tests
python test_integration.py                     # Integration tests
python test_vkb_server_integration.py         # Mock socket tests
TEST_VKB_ENABLED=1 python test_real_vkb_server.py  # Real hardware tests
```

---

## Detailed Testing Options

## Option 1: Unit Testing (No EDMC Required)

Test individual modules without EDMC installed.

### Setup
```bash
cd h:\development\projects\EDMCVKBConnector
python -m pytest tests/ -v
```

### Create a test file: `tests/test_config.py`
```python
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edmcvkbconnector.config import Config, DEFAULTS

def test_config_defaults():
    """Test that Config returns correct defaults."""
    config = Config()
    
    assert config.get("vkb_host", "127.0.0.1") == "127.0.0.1"
    assert config.get("vkb_port", 50995) == 50995
    assert config.get("initial_retry_interval", 2) == 2
    print("✓ Config defaults test passed")

def test_vkb_client():
    """Test VKBClient initialization."""
    from edmcvkbconnector.vkb_client import VKBClient
    
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
    assert not client.connected
    print("✓ VKBClient initialization test passed")

def test_event_handler():
    """Test EventHandler initialization."""
    from edmcvkbconnector.event_handler import EventHandler
    from edmcvkbconnector.config import Config
    
    config = Config()
    handler = EventHandler(config)
    
    assert handler.enabled == True
    assert handler.debug == False
    assert handler.vkb_client is not None
    print("✓ EventHandler initialization test passed")

if __name__ == "__main__":
    test_config_defaults()
    test_vkb_client()
    test_event_handler()
    print("\nAll tests passed! ✓")
```

### Run tests:
```bash
python tests/test_config.py
```

---

## Option 2: Mock Integration Testing

Test the plugin logic with mock EDMC.

### Create: `tests/test_integration.py`
```python
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edmcvkbconnector.config import Config
from edmcvkbconnector.event_handler import EventHandler

def test_event_flow():
    """Test event processing without real socket connection."""
    config = Config()
    handler = EventHandler(config)
    
    # Mock the VKB client to prevent actual connection attempts
    handler.vkb_client.send_event = Mock(return_value=True)
    
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
    
    # Verify send_event was called
    assert handler.vkb_client.send_event.called
    print("✓ Event flow test passed")

def test_shift_bitmap():
    """Test shift state management."""
    config = Config()
    handler = EventHandler(config)
    handler.vkb_client.send_event = Mock(return_value=True)
    
    # Test shift state manipulation
    handler._shift_bitmap = 0
    handler._shift_bitmap = handler._apply_bit(handler._shift_bitmap, 0, True)
    assert handler._shift_bitmap == 1
    
    handler._shift_bitmap = handler._apply_bit(handler._shift_bitmap, 0, False)
    assert handler._shift_bitmap == 0
    print("✓ Shift bitmap test passed")

if __name__ == "__main__":
    test_event_flow()
    test_shift_bitmap()
    print("\nAll integration tests passed! ✓")
```

### Run:
```bash
python tests/test_integration.py
```

---

## Option 3: Real EDMC Testing (Recommended for Final Testing)

### Prerequisites
1. Install EDMC 5.0+ from https://github.com/EDCD/EDMarketConnector
2. Locate your EDMC plugins directory:
   - **Windows:** `%APPDATA%\EDMarketConnector\plugins`
   - **macOS:** `~/Library/Application Support/EDMarketConnector/plugins`
   - **Linux:** `~/.local/share/EDMarketConnector/plugins`

### Installation
```bash
# Create symlink or copy to plugins directory
mklink /D "%APPDATA%\EDMarketConnector\plugins\edmcvkbconnector" "h:\development\projects\EDMCVKBConnector"
```

Or manually copy the `src/edmcvkbconnector` folder to your plugins directory.

### Testing Within EDMC
1. Start EDMC
2. Check the **Log** window for VKB Connector startup messages
3. Open **Settings → VKB Connector** to configure host/port
4. Monitor **Log** for event processing

### Verify Installation
Look for these log lines:
```
VKB Connector v0.1.0 starting
VKB Connector v0.1.0 initialized. Target: 127.0.0.1:50995
Connected to VKB device at 127.0.0.1:50995
```

---

## Option 4: Mock VKB Hardware for Testing

Create a simple echo server to test without real VKB hardware.

### Create: `tests/mock_vkb_server.py`
```python
import socket
import threading
import time

def run_mock_vkb_server(host="127.0.0.1", port=50995, duration=10):
    """
    Simple mock VKB server for testing.
    Runs for specified duration, echoing received bytes.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    
    print(f"Mock VKB server listening on {host}:{port}")
    print(f"Will run for {duration} seconds...")
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        try:
            server.settimeout(1.0)
            client, addr = server.accept()
            print(f"Client connected: {addr}")
            
            while True:
                data = client.recv(1024)
                if not data:
                    break
                print(f"Received {len(data)} bytes: {data.hex()}")
                client.send(b"ACK")
            
            client.close()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
    
    server.close()
    print("Mock VKB server stopped")

def start_mock_server_in_thread(duration=30):
    """Start mock server in background thread."""
    thread = threading.Thread(
        target=run_mock_vkb_server,
        kwargs={"duration": duration},
        daemon=True,
    )
    thread.start()
    time.sleep(0.5)  # Give server time to start
    return thread

if __name__ == "__main__":
    run_mock_vkb_server(duration=60)
```

### Test with Mock Server
```bash
# Terminal 1: Start mock VKB server
python tests/mock_vkb_server.py

# Terminal 2: Run tests
python tests/test_integration.py
```

---

## Option 5: End-to-End Testing Checklist

### Manual Testing Flow
```
1. Start mock VKB server
   python tests/mock_vkb_server.py

2. In Python shell, test connection:
   from edmcvkbconnector.vkb_client import VKBClient
   client = VKBClient("127.0.0.1", 50995)
   success = client.connect()
   print(f"Connected: {success}")
   
3. Send a test event:
   client.send_event("FSDJump", {"StarSystem": "Sol"})
   
4. Check mock server output for received data

5. Test reconnection:
   - Kill mock server
   - Watch for reconnection attempts in logs
   - Restart mock server
   - Verify reconnection succeeds
```

---

## Option 6: Running Without EDMC (Development Mode)

```python
# test_standalone.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from edmcvkbconnector import Config, EventHandler

# Test in development mode (no EDMC required)
config = Config()
handler = EventHandler(config)

print(f"✓ Config initialized")
print(f"✓ Event handler initialized")
print(f"✓ Ready for testing")

# Simulate events
handler.handle_event(
    "Location",
    {"SystemAddress": 10477373803},
    cmdr="TestCmdr",
    source="journal",
)
print(f"✓ Location event processed")
```

### Run:
```bash
python test_standalone.py
```

---

## Debugging Tips

### Enable Debug Logging
```python
handler.set_debug(True)
```

### Check Log Messages
- EDMC logs appear in: **Help → Open Log**
- Look for patterns:
  - `Connected to VKB device` → Connection OK
  - `Failed to connect` → Connection problems
  - `Rule engine error` → Rule processing issues

### Test Rule Engine
```python
# Test with rules file
config = Config()
handler = EventHandler(config, plugin_dir="./")
# Place rules.json in current directory
handler.reload_rules()
print(f"Loaded {len(handler.rule_engine.rules) if handler.rule_engine else 0} rules")
```

---

## Environment Setup

### EDMarketConnector Location

Your EDMarketConnector is cloned at:
```
h:\development\projects\EDMarketConnector
```

This is `../EDMarketConnector` relative to the plugin workspace.

### Using EDMarketConnector for Testing

The `dev_test.py` script automatically:
1. ✓ Detects the EDMarketConnector installation
2. ✓ Configures Python path correctly
3. ✓ Runs all tests with proper EDMC environment
4. ✓ Reports any missing dependencies

**Run it with:**
```bash
cd tests
python dev_test.py
```

Or on Windows:
```batch
test.bat dev
```

### If EDMarketConnector Not Found

Clone it in the parent directory:
```bash
cd h:\development\projects
git clone https://github.com/EDCD/EDMarketConnector.git
```

Then tests will automatically use it.

---

## Testing in Isolation vs With EDMC

| Scenario | Command | Environment |
|----------|---------|-------------|
| **Quick syntax check** | `test.bat unit` | Python only |
| **Event handling logic** | `test.bat integration` | Python + mocks |
| **Full integration** | `test.bat dev` | Python + actual EDMC |
| **Network simulation** | `test.bat mock` | Socket server |
| **Real game testing** | EDMC plugin directory | Full EDMC + Elite Dangerous |

---

## Test Project Structure

```
EDMCVKBConnector/
├── test.bat                    # Windows quick runner
├── TESTING.md                  # This file
├── tests/
│   ├── README.md              # Detailed test docs
│   ├── test_config.py         # Unit tests
│   ├── test_integration.py    # Integration tests
│   ├── mock_vkb_server.py     # Mock TCP/IP server
│   ├── dev_test.py            # Full dev test
│   ├── run_all_tests.py       # Test summary runner
│   └── (test outputs)
└── src/edmcvkbconnector/
    ├── config.py              # Config management
    ├── vkb_client.py          # Socket client
    ├── event_handler.py       # Event processing
    ├── message_formatter.py    # Protocol formatting
    ├── rules_engine.py        # Dashboard rule matching
    └── __init__.py
```

---

## What Each Test Does

### `test_config.py` - Unit Tests
- Config key defaults
- VKBClient initialization
- EventHandler creation
- MessageFormatter message creation
- **Duration:** <1 second
- **Dependencies:** Python only

### `test_integration.py` - Integration Tests
- Event flow (journal, dashboard, CAPI)
- Shift state bitmap manipulation
- Error handling
- Commander isolation
- **Duration:** <2 seconds
- **Dependencies:** Python + unittest.mock

### `dev_test.py` - Full Development Test
- Detects EDMarketConnector
- Runs unit tests
- Runs integration tests
- Shows summary and next steps
- **Duration:** <5 seconds
- **Dependencies:** Python + EDMarketConnector

### `mock_vkb_server.py` - Mock VKB Hardware
- Listens on 127.0.0.1:50995 (configurable)
- Accepts TCP connections
- Echoes received bytes with hex dump
- Useful for network-level testing
- **Duration:** Custom (Ctrl+C to stop)
- **Dependencies:** Python socket library

---

## Typical Test Workflow

```
1. Write code
   ↓
2. Run unit tests: test.bat unit
   (Fast feedback - <1s)
   ↓
3. If unit tests pass, run integration: test.bat integration
   (Logic validation - <2s)
   ↓
4. If integration passes, run full dev: test.bat dev
   (EDMC environment check - <5s)
   ↓
5. If all pass, test in real EDMC
   (Final validation)
```

---

## Common Test Scenarios

### Scenario: Quick Syntax Check (During Development)
```batch
test.bat unit
```
Fast feedback loop (< 1 second)

### Scenario: Validate Event Processing Logic
```batch
test.bat integration
```
Tests event flow, shift state, error handling (< 2 seconds)

### Scenario: Full Integration Before EDMC Deployment
```batch
test.bat dev
```
Runs all tests with actual EDMC modules (< 5 seconds)

### Scenario: Test Network Communication
```batch
# Terminal 1
test.bat mock

# Terminal 2
test.bat integration
```
Simulates actual socket communication

### Scenario: Before Committing Code
```batch
test.bat dev  && echo ✓ All tests passed!
```
Full validation before git commit

---

## Troubleshooting Tests

### Tests Fail with "config' object has no attribute 'get_str'"
**Problem:** Using fallback Config instead of real EDMC
**Solution:** Run `test.bat dev` or `python dev_test.py` to use actual EDMC

### Mock Server Shows "could not bind port"
**Problem:** Port 50995 already in use
**Solution:** Kill other processes or specify different port:
```bash
python mock_vkb_server.py --port 50996
```

### "EDMarketConnector not found at ../EDMarketConnector"
**Problem:** Repository not cloned
**Solution:** Clone it:
```bash
cd ..
git clone https://github.com/EDCD/EDMarketConnector.git
cd EDMCVKBConnector
test.bat dev
```

### Tests Pass But EDMC Shows "Import config Failed"
**Problem:** Missing EDMC environment in actual EDMC run
**Solution:** Verify plugin is in correct location:
```batch
%APPDATA%\EDMarketConnector\plugins\edmcvkbconnector\
```

---

## Next Steps After Tests Pass

1. **Install to EDMC** (Windows):
   ```powershell
   mklink /D "%APPDATA%\EDMarketConnector\plugins\edmcvkbconnector" "h:\development\projects\EDMCVKBConnector"
   ```

2. **Restart EDMC** and check log

3. **Configure in preferences**: Settings → VKB Connector

4. **Play Elite Dangerous** and monitor logs

5. **For real VKB hardware**: Connect VKB-Link TCP/IP and test shift state changes

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: python tests/test_config.py
      - run: python tests/test_integration.py
```

### Local Pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
cd tests
python dev_test.py || exit 1
```

