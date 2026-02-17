# Development Testing Quick Start

Your EDMarketConnector is located at `../EDMarketConnector` relative to this workspace.

## Quick Setup

### 1. Run All Tests with EDMC Environment
```bash
cd tests
python dev_test.py
```

This script will:
- ✓ Find and configure EDMC (DEV)
- ✓ Run unit tests  
- ✓ Run integration tests
- ✓ Show next steps

### 2. Run Individual Tests

**Unit tests only** (config, vkb_client, event_handler):
```bash
python test_config.py
```

**Integration tests** (event flow, mock VKB client):
```bash
python test_integration.py
```

**With mock VKB hardware**:
```bash
# Terminal 1: Start the mock VKB server
python mock_vkb_server.py 60

# Terminal 2: Run integration tests
python test_integration.py
```

### 3. Test with EDMC (DEV)

The plugin is automatically linked during development setup:
```bash
python ../scripts/bootstrap_dev_env.py
```

Then run EDMC in development mode:
```bash
python ../scripts/run_edmc_from_dev.py
```

To test:
1. Start EDMC in dev mode
2. Open plugin preferences: Settings → VKB Connector
3. Set VKB Host and Port (default: 127.0.0.1:50995)
4. Check logs: File → Settings → Advanced → Show Log

## Testing Matrix

| Method | Requires | Time | Best For |
|--------|----------|------|----------|
| `test_config.py` | Python | <1s | Quick syntax check |
| `test_integration.py` | Python | <2s | Logic validation |
| `test_rules_comprehensive.py` | Python | <1s | Rules engine scenarios |
| `test_vkb_server_integration.py` | Python | ~10s | Network protocol |
| `dev_test.py` | EDMC source | ~20s | Full integration (all layers) |
| `mock_vkb_server.py` | Python | custom | Network testing |
| Real EDMC | EDMC + VKB | custom | Final validation |

## Environment Setup Details

### What `dev_test.py` Does

1. **Locates EDMarketConnector** at `../EDMarketConnector`
2. **Adds to Python path** so EDMC modules can be imported
3. **Tests EDMC imports**: config, stats, l10n
4. **Runs unit tests** with properly configured environment
5. **Runs integration tests** 
6. **Reports status** and next steps

### If EDMarketConnector Not Found

Clone it first:
```bash
cd h:\development\projects
git clone https://github.com/EDCD/EDMarketConnector.git EDMarketConnector
```

Then run:
```bash
cd EDMCVKBConnector\tests
python dev_test.py
```

## Testing Flow Chart

```
┌─ test_config.py ─────────────────┐
│ Config/VKBClient/EventHandler    │
│ Basic initialization tests        │
└──────────────────────────────────┘
         ↓ (if passing)
┌─ test_integration.py ─────────────┐
│ Mock VKB client + event handling  │
│ Logic + state management          │
└──────────────────────────────────┘
         ↓ (if passing)
┌─ mock_vkb_server.py ──────────────┐
│ Real socket simulation            │
│ Network protocol validation       │
└──────────────────────────────────┘
         ↓ (if passing)
┌─ Real EDMC Testing ───────────────┐
│ Actual EDMC environment           │
│ Final validation with ED game     │
└──────────────────────────────────┘
```

## Troubleshooting

### "Config' object has no attribute 'get_str'"
This means the test is using the mock Config. Run with EDMC environment:
```bash
python dev_test.py
```

### "send_event() takes no arguments"
Likely schema mismatch. Check that test is mocking correctly:
```python
handler.vkb_client.send_event = Mock(return_value=True)
```

### "EDMarketConnector not found"
Clone it first:
```bash
cd ..
git clone https://github.com/EDCD/EDMarketConnector.git
cd EDMCVKBConnector\tests
python dev_test.py
```

### "Import 'config' could not be resolved"
This is expected - the `config` module is from EDMC. It only matters when running inside EDMC itself. Use `dev_test.py` to test with real EDMC modules available.

## File Structure

```
tests/
├── test_config.py              # Unit tests (5 tests)
├── test_integration.py         # Integration tests (6 tests)
├── test_rules_comprehensive.py # Rules engine tests (23 tests)
├── test_vkb_server_integration.py # VKB socket tests (8 tests)
├── mock_vkb_server.py          # Mock VKB for network testing
├── run_all_tests.py            # Run all tests with summary
├── dev_test.py                 # Full dev test with EDMC env
├── RULES_TESTS.md              # Detailed rules test documentation
├── VKB_SERVER_TESTS.md         # VKB socket protocol docs
├── REAL_SERVER_TESTS.md        # Real hardware testing guide
└── README.md                   # This file
└── README.md                   # This file
```

## Next Steps After Tests Pass

1. **Set up dev environment** (if not already done):
   ```bash
   python ../scripts/bootstrap_dev_env.py
   ```

2. **Run EDMC in dev mode**:
   ```bash
   python ../scripts/run_edmc_from_dev.py
   ```

3. **Check EDMC logs** for plugin initialization

4. **Play Elite Dangerous** and monitor:
   - FSD jumps → shift state changes
   - Docking → shift state changes
   - Status/flags → rule matching

5. **Monitor mock server output** for received shift state packets

For complete development workflow, see [DEVELOPMENT.md](../DEVELOPMENT.md).

## Real VKB Hardware Testing

Once you have actual VKB hardware with the VKB-Link TCP/IP interface:

1. Ensure VKB-Link is running on network
2. Update VKB Host/Port in EDMC preferences
3. Play Elite Dangerous normally
4. Hardware should respond to shift state changes

**For automated testing against real hardware:**
See [REAL_SERVER_TESTS.md](REAL_SERVER_TESTS.md) for detailed instructions on:
- Configuring real VKB server tests
- Running automated tests against actual hardware
- Troubleshooting VKB-Link connectivity
- CI/CD integration

Quick start:
```bash
test.bat real
```
