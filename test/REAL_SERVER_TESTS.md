# Real VKB Server Integration Tests

## Overview

These tests validate EDMCVKBConnector against **actual VKB hardware running VKB-Link**.

Unlike mock server tests, these tests:
- ✅ Connect to real VKB hardware
- ✅ Send actual shift state commands
- ✅ Verify hardware responds correctly
- ✅ Test practical scenarios (rapid messages, persistence, etc.)
- ✅ Validate end-to-end integration

## Prerequisites

### Hardware Required
- VKB HOTAS/HOSAS controller
- VKB-Link software installed and running with TCP/IP enabled

### Software Setup
1. **Start VKB-Link** with TCP/IP server mode enabled
2. **Note the IP and port** (typically 127.0.0.1:50995 or 192.168.x.x:50995)
3. **Configure tests** (see Configuration section below)

## Configuration

### Option 1: Environment Variables (PowerShell)

```powershell
$env:TEST_VKB_ENABLED = '1'
$env:TEST_VKB_HOST = '127.0.0.1'      # Or your VKB-Link IP
$env:TEST_VKB_PORT = '50995'           # Or your VKB-Link port
python test_real_vkb_server.py
```

### Option 2: Windows Batch

```batch
set TEST_VKB_ENABLED=1
set TEST_VKB_HOST=127.0.0.1
set TEST_VKB_PORT=50995
python test_real_vkb_server.py
```

### Option 3: .env File (Recommended)

1. Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```

2. Edit `.env`:
```ini
TEST_VKB_ENABLED=1
TEST_VKB_HOST=127.0.0.1
TEST_VKB_PORT=50995
```

3. Run tests:
```bash
python test_real_vkb_server.py
```

Or via batch script:
```batch
test.bat real
```

## Running Tests

### Quick Start
```bash
# Check if server is available (won't connect if disabled)
test.bat real

# Or directly
cd tests
python test_real_vkb_server.py
```

### With Specific Configuration
```powershell
$env:TEST_VKB_ENABLED = '1'
$env:TEST_VKB_HOST = '192.168.1.100'
$env:TEST_VKB_PORT = '50995'
test.bat real
```

### Full Test Suite (including real tests)
```bash
# Test all: unit + integration + mock server + real server
TEST_VKB_ENABLED=1 python tests/dev_test.py
```

## Test Coverage

### 1. Real Server Connection
- Connects to actual VKB hardware
- Validates connection state
- Graceful disconnection

### 2. Send Shift State
- Sends shift=1, shift=2, shift=0 commands
- Validates hardware accepts commands
- No errors or crashes

### 3. Multiple Shift States
- Tests all shift combinations (shifts 0-7, subshifts 0-1)
- Ensures hardware handles all transitions
- Timing validation

### 4. EventHandler Integration
- Routes game events through VKBClient to hardware
- Tests FSDJump and Location events
- End-to-end validation

### 5. Connection Persistence
- Multiple operations without disconnection
- Connection remains stable
- No data loss

### 6. Rapid Message Transmission
- 10 messages sent rapidly
- Hardware keeps up with input
- All messages reach hardware

## Example Output

### Disabled (Default)
```
============================================================
Real VKB Server Integration Tests
============================================================

Configuration:
  Host: 127.0.0.1
  Port: 50995
  Enabled: False

Real VKB server tests are DISABLED.
To enable, set environment variable: TEST_VKB_ENABLED=1

Example:
  $env:TEST_VKB_ENABLED = '1'; python test_real_vkb_server.py
```

### Enabled but Server Not Available
```
============================================================
Real VKB Server Integration Tests
============================================================

VKB server NOT FOUND at 127.0.0.1:50995

To test with real VKB hardware:
  1. Start VKB-Link with TCP/IP enabled
  2. Verify it's accessible at the configured host/port
  3. Run tests again
```

### Running Successfully
```
============================================================
Real VKB Server Integration Tests
============================================================

Configuration:
  Host: 127.0.0.1
  Port: 50995
  Enabled: True

VKB server FOUND at 127.0.0.1:50995
Running real hardware tests...

Real server connection:
  ✓ Connected to 127.0.0.1:50995
  ✓ Disconnected cleanly
  PASS

Real server shift state:
  ✓ Sent shift=1 to hardware
  ✓ Sent shift=2 to hardware
  ✓ Reset shift to 0
  PASS

Real server multiple shifts:
  ✓ Shift=0, SubShift=0
  ✓ Shift=0, SubShift=1
  ...
  ✓ Sent 16 shift combinations
  PASS

Real server EventHandler:
  ✓ Sent FSDJump event
  ✓ Sent Location event
  PASS

Real server persistence:
  ✓ Connection remained stable across 5 operations
  PASS

Real server rapid messages:
  ✓ Sent 10/10 rapid messages
  PASS

============================================================
Results: 6 passed, 0 failed
============================================================
```

## Troubleshooting

### "VKB server NOT FOUND"
**Problem:** VKB-Link not running or wrong IP/port
**Solutions:**
1. Verify VKB-Link is running with TCP/IP enabled
2. Check IP with: `ipconfig` (Windows) or `ifconfig` (Linux)
3. Verify port with: `netstat -an | findstr :50995`
4. Update TEST_VKB_HOST and TEST_VKB_PORT in .env

### "Real VKB server tests are DISABLED"
**Problem:** TEST_VKB_ENABLED not set
**Solution:**
```powershell
$env:TEST_VKB_ENABLED = '1'
test.bat real
```

### Tests Pass but Hardware Doesn't Respond
**Problem:** Hardware not connected or VKB-Link not configured correctly
**Solutions:**
1. Verify VKB HOTAS/HOSAS is connected via USB
2. Open VKB-Link GUI, check device status
3. Enable TCP/IP in VKB-Link settings
4. Check firewall isn't blocking port

### Connection Timeout
**Problem:** Network connectivity issue
**Solutions:**
1. Ping VKB-Link host: `ping 127.0.0.1` (for local)
2. Test port: `telnet 127.0.0.1 50995`
3. Check network cables and switches
4. Check firewall rules

## VKB-Link Configuration

### Typical VKB-Link Setup

1. **Open VKB-Link**
2. **Settings → Network**
3. **Enable TCP/IP Server**
4. **Set Port** (default 50995)
5. **Accept** and restart VKB-Link

### For Remote Testing
If testing from different machine:
1. Note VKB-Link machine IP (e.g., 192.168.1.100)
2. Update TEST_VKB_HOST in .env
3. Ensure network connectivity (ping the IP)
4. Update firewall if needed

## CI/CD Integration

### GitHub Actions
```yaml
- name: Test Against Real VKB (if available)
  env:
    TEST_VKB_ENABLED: '1'
    TEST_VKB_HOST: '127.0.0.1'
    TEST_VKB_PORT: '50995'
  run: |
    cd tests
    python test_real_vkb_server.py || true
  continue-on-error: true  # Don't fail pipeline if hardware unavailable
```

## Performance Benchmarks

Expected timing for each test:
| Test | Duration | Notes |
|------|----------|-------|
| Connection | 0.5s | Connect + disconnect |
| Send shift | 2.0s | 3 shift changes with delays |
| Multiple shifts | 4.0s | 16 combinations with delays |
| EventHandler | 2.0s | 2 events with delays |
| Persistence | 2.0s | 5 operations |
| Rapid messages | 1.0s | 10 rapid sends |
| **Total** | **~12s** | Varies by hardware |

## Related Files

- [test_real_vkb_server.py](test_real_vkb_server.py) - Real server tests
- [.env.example](../.env.example) - Configuration template
- [TESTING.md](../TESTING.md) - General testing guide
- [VKB_SERVER_TESTS.md](VKB_SERVER_TESTS.md) - Mock server tests

## Next Steps

1. **Get VKB-Link Running**:
   - Download from VKB website
   - Install and configure TCP/IP
   - Note the IP and port

2. **Configure Tests**:
   - Copy .env.example to .env
   - Update with your VKB-Link details
   - Verify TEST_VKB_ENABLED=1

3. **Run Tests**:
   ```bash
   test.bat real
   ```

4. **Monitor Hardware**:
   - Watch for LED changes on HOTAS
   - Verify shift state changes
   - Check for any errors

5. **Troubleshoot as Needed**:
   - Check logs
   - Verify network connectivity
   - Adjust timing if hardware slow to respond

## Safety Notes

⚠️ **Important**: These tests send real commands to your VKB hardware!

- **Shift state changes** will be visible on your HOTAS
- **LEDs will blink** during tests
- **This is safe** - only shift states are changed, no dangerous commands
- **No flight stick movement** is triggered
- **Safe to run** while game is running or not

## Support

If tests fail:
1. Check troubleshooting section above
2. Verify VKB-Link is actually running
3. Try manual connection test:
   ```bash
   python tests/test_real_vkb_server.py
   ```
4. Check connection logs for details
