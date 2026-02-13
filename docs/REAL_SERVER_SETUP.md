# VKB-Link Integration Setup

This guide covers running the plugin and tests against a real VKB-Link endpoint.

## Compatibility

- VKB-Link `v0.8.2+`
- VKB firmware `2.21.3+`
- Verified with `VKBDevCfg v0.93.96`
- VKB software/firmware source: https://www.njoy32.vkb-sim.pro/home

## Prerequisites

- EDMC plugin installed
- VKB-Link running with TCP enabled
- VKB-Link host/port known (default `127.0.0.1:50995`)

## VKB-Link INI TCP Settings

The plugin standard/default endpoint is `127.0.0.1:50995`.
Set VKB-Link's `ini` file TCP section to match:

```ini
[TCP]
Adress=127.0.0.1
Port=50995
```

## Configure

Use environment variables or `.env`:

```ini
TEST_VKB_ENABLED=1
TEST_VKB_HOST=127.0.0.1
TEST_VKB_PORT=50995
```

PowerShell example:

```powershell
$env:TEST_VKB_ENABLED = '1'
$env:TEST_VKB_HOST = '127.0.0.1'
$env:TEST_VKB_PORT = '50995'
```

## Run Integration Tests

From repository root:

```powershell
python test/test_real_vkb_server.py
```

Or run the full test runner:

```powershell
python test/run_all_tests.py
```

## What The Tests Verify

- VKB-Link connection and clean disconnect
- Shift/subshift packet sends
- EventHandler -> VKB-Link integration
- Repeated sends and stability behavior

## Troubleshooting

- `TEST_VKB_ENABLED` not set: tests skip by design
- Connection refused/timeouts:
  - Verify VKB-Link is running
  - Confirm host/port
  - Check firewall rules
- No visible response in VKB tools:
  - Verify firmware/tool versions
  - Confirm VKB-Link is attached to the intended device profile

## Safety Notes

Integration tests send VKB-Link shift/subshift state changes only.
They do not issue movement commands.
