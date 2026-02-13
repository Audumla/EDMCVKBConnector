# Testing Quick Reference Card

## 30-Second Quick Start

```powershell
# Run all tests
.\test.bat dev

# Expected: ✅ 19 tests pass in ~14 seconds
```

---

## Commands (One-Liners)

```powershell
# Development (recommended)
.\test.bat dev          # Unit + Integration + Mock Socket (~14s)

# Full suite
.\test.bat all          # Same as dev (14s)

# Specific layers
.\test.bat unit         # Unit only (<1s)
.\test.bat integration  # Integration only (~2s)
.\test.bat server       # Mock socket only (~11s)

# Real hardware (optional)
$env:TEST_VKB_ENABLED='1'; .\test.bat real
```

---

## Test Results

### Development Tests
```
Layer 1: Unit Tests           ✅ 5 tests  (<1 sec)
Layer 2: Integration Tests    ✅ 6 tests  (~2 sec)
Layer 3: Mock Socket Tests    ✅ 8 tests  (~11 sec)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                        ✅ 19 tests (~14 sec)
```

### Real Hardware Tests (Optional)
```
Layer 4: Real Hardware Tests  ⧐ 6 tests  (~12 sec, if enabled)
Status: Ready to run, disabled by default for safety
```

---

## Configuration (Real Hardware)

### Quick Setup
```powershell
# Enable real tests
$env:TEST_VKB_ENABLED = '1'

# Or use .env file
copy .env.example .env
# Edit: TEST_VKB_ENABLED=1
```

### Full Configuration
```powershell
$env:TEST_VKB_ENABLED = '1'
$env:TEST_VKB_HOST = '127.0.0.1'
$env:TEST_VKB_PORT = '50995'
```

---

## Documentation Map

| Need | Document | Time |
|------|----------|------|
| What tests exist? | [TEST_SUITE.md](TEST_SUITE.md) | 10 min |
| Quick start? | [TESTING.md](TESTING.md) | 2 min |
| Real VKB setup? | [REAL_SERVER_SETUP.md](REAL_SERVER_SETUP.md) | 3 min |
| Real VKB detailed? | [tests/REAL_SERVER_TESTS.md](tests/REAL_SERVER_TESTS.md) | 5 min |
| Full completion? | [COMPLETION_REPORT.md](COMPLETION_REPORT.md) | 10 min |

---

## Common Tasks

### Before Committing Code
```powershell
.\test.bat dev
# ↓ All pass? → OK to commit
# ↓ Fail? → Fix code
```

### Full Validation
```powershell
.\test.bat all
# ↓ All pass? → Ready for release
```

### Test with VKB Hardware
```powershell
# 1. Start VKB-Link (Windows software)
# 2. Enable for tests:
$env:TEST_VKB_ENABLED = '1'

# 3. Run:
.\test.bat real
```

### CI/CD Pipeline
```powershell
# Pipeline step:
.\test.bat all

# Optional hardware tests:
if ($env:HAS_VKB -eq 'true') {
    $env:TEST_VKB_ENABLED = '1'
    .\test.bat real
}
```

---

## Layer Details

### Layer 1: Unit Tests (Fastest)
- Config loading
- Component initialization
- ~0.5 seconds

### Layer 2: Integration Tests
- Event processing flows
- Rule engine evaluation
- ~2 seconds

### Layer 3: Mock Socket Tests
- TCP/IP operations
- Reconnection logic
- **Critical**: Server restart → reconnect
- ~11 seconds

### Layer 4: Real Hardware Tests
- VKB-Link connection
- Shift state changes
- Game event routing
- ~12 seconds (optional, needs hardware)

---

## Safety

✅ **Safe to run anytime**:
- Unit tests
- Integration tests
- Mock socket tests

⚠️ **Real hardware tests**:
- Disabled by default
- Must explicitly enable (TEST_VKB_ENABLED=1)
- Only safe shift commands sent
- LED changes visible but safe
- Safe to run while playing Elite Dangerous

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests fail | Run `.\test.bat dev` for details |
| Port in use | Kill process: `taskkill /FI "MEMUSAGE gt 1" /T` |
| Real server not found | Start VKB-Link, enable TCP/IP |
| Import errors | Install deps: `pip install -r requirements.txt` |
| Timeout | Check firewall, verify connections |

---

## Performance Expectations

```
Quick test:     .\test.bat unit           < 1 sec
Dev test:       .\test.bat dev            ~14 sec
Full test:      .\test.bat all            ~14 sec
With hardware:  .\test.bat real (enabled) ~12 sec
Total (all):    Everything               ~26 sec
```

---

## Test Files

- `tests/test_config.py` - Unit tests
- `tests/test_integration.py` - Integration tests
- `tests/test_vkb_server_integration.py` - Socket tests
- `tests/test_real_vkb_server.py` - Real hardware tests
- `tests/mock_vkb_server.py` - Mock VKB server

---

## Status: ✅ READY

All tests operational and passing.

Next step: `.\test.bat dev`

---

**Version**: 1.0  
**Last Updated**: Current session  
**Status**: Production Ready ✅
