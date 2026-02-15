# EDMCVKBConnector

EDMC plugin that maps Elite Dangerous events and status state to VKB shift/subshift bitmaps over TCP.

## What This Plugin Does

- Receives EDMC notifications (`journal`, `dashboard`, `capi`, `capi_fleetcarrier`)
- Evaluates optional rules in `rules.json`
- Sends `VKBShiftBitmap` packets to VKB-Link
- Reconnects automatically if VKB-Link restarts

## Compatibility

- Python: `3.9+`
- EDMC: `5.0+` (5.13+ recommended)
- VKB-Link: `v0.8.2+`
- VKB firmware: `2.21.3+`
- Verified test tool: `VKBDevCfg v0.93.96`
- VKB software/firmware downloads: https://www.njoy32.vkb-sim.pro/home

## Quick Start (Development)

1. **Bootstrap** - Set up development environment (one-time):
   ```bash
   python scripts/bootstrap_dev_env.py
   ```
   This will:
   - Clone EDMC repository to `../EDMarketConnector`
   - Create virtual environment at `.venv`
   - Install all dependencies
   - Link the plugin into EDMC plugins directory

2. **Run EDMC** - Launch EDMC with isolated dev config:
   ```bash
   python scripts/run_edmc_from_dev.py
   ```
   This uses an isolated configuration that won't touch your installed EDMC settings.

3. **Package** - Create distributable ZIP:
   ```bash
   python scripts/package_plugin.py
   ```

See [scripts/README.md](scripts/README.md) for detailed documentation.

## Configuration

Settings are stored via EDMC config with `VKBConnector_` prefix.

Main keys:
- `vkb_host` (default `127.0.0.1`)
- `vkb_port` (default `50995`)
- `enabled` (default `true`)
- `debug` (default `false`)
- `event_types` (empty list means no event-type filtering)
- `rules_path` (optional override, otherwise `<plugin_dir>/rules.json`)

### Event Type Filter

- `event_types = []` -> no filtering
- non-empty list -> only listed event names are processed

### VKB-Link TCP Configuration

The plugin default is `127.0.0.1:50995`.  
VKB-Link must be configured to use the same TCP endpoint in its `ini` file:

```ini
[TCP]
Adress=127.0.0.1
Port=50995
```

## Rules

Rules are read from `rules.json` and can set/clear shift tokens:
- `vkb_set_shift`: `["Shift1", "Subshift3"]`
- `vkb_clear_shift`: `["Shift1", "Subshift3"]`

### Visual Rule Editor

The plugin includes a visual rule editor accessible from EDMC preferences:
1. Open **File > Settings > Plugins**
2. Find the **VKB Connector** section
3. Select a rule and click **Visual Editor**

The visual editor provides a structured interface for:
- Configuring when conditions (source, event, condition blocks)
- Setting then/else actions (shift flags, log statements)
- Browsing available EDMC events and flags
- Real-time JSON preview

See [Visual Rule Editor Guide](docs/VISUAL_RULE_EDITOR.md) for details.

### Manual Rule Editing

Full schema and examples for manual JSON editing:
- [Rules Schema](docs/RULES_SCHEMA.md)

## Documentation

- [Visual Rule Editor Guide](docs/VISUAL_RULE_EDITOR.md) - **NEW**: User-friendly rule editor
- [Deployment Guide](docs/DEPLOYMENT.md)
- [VKB-Link Setup](docs/REAL_SERVER_SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Protocol Implementation](docs/PROTOCOL_IMPLEMENTATION.md)
- [Rules Schema](docs/RULES_SCHEMA.md)
- [Standards Compliance](docs/STANDARDS_COMPLIANCE.md)

## Development

See [scripts/README.md](scripts/README.md) for complete development workflow documentation.

### Quick Reference

**Initial setup:**
```bash
python scripts/bootstrap_dev_env.py
```
Sets up: EDMC clone, venv, dependencies, and links the plugin.

**Run EDMC with isolated dev config (recommended):**
```bash
python scripts/run_edmc_from_dev.py
```
Uses a completely isolated configuration that won't touch your installed EDMC settings.

**Run EDMC with your actual config (for testing with real commanders):**
```bash
python scripts/run_edmc_from_dev.py --use-system-config
```

**Package for distribution:**
```bash
python scripts/package_plugin.py
```

### Isolated Development Configuration

By default, `python scripts/run_edmc_from_dev.py` uses completely isolated EDMC configuration. This works by:

1. Creating isolated config directory in `.edmc_dev_config/`
2. Creating minimal config file: `.edmc_dev_config/config.toml`
3. Passing `--config .edmc_dev_config/config.toml` to EDMC at launch
4. EDMC reads all settings from that file instead of system configuration

**Benefits:**
- Your installed EDMC remains completely untouched
- Clean environment for testing
- Easy to reset: delete `.edmc_dev_config/` and start fresh
- Plugin loads directly from source via symlink (no copying)

### VS Code Tasks

Available tasks (Terminal > Run Task):
- **EDMC: Bootstrap Dev Environment** - Initial setup
- **EDMC: Bootstrap + Run Tests** - Setup + test suite
- **EDMC: Run EDMC (DEV)** - Run with isolated config
- **EDMC: Run EDMC (DEV - System Config)** - Run with real EDMC config  
- **EDMC: Package Plugin** - Create dist ZIP

## License

MIT. See [LICENSE](LICENSE).
