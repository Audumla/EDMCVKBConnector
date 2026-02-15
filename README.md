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

## Quick Start (Windows)

1. Build the plugin zip:
   ```powershell
   python scripts/package_plugin.py
   ```
2. Extract `dist/EDMCVKBConnector-<version>.zip` into:
   `%APPDATA%\EDMarketConnector\plugins\`
3. Restart EDMC.
4. Open `File -> Settings -> Plugins`, configure host/port, and enable rules if needed.

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

```bash
git clone https://github.com/Audumla/EDMCVKBConnector.git
cd EDMCVKBConnector
python -m venv venv
```

Windows:
```powershell
venv\Scripts\activate
pip install -r requirements.txt -e .[dev]
```

Run tests (Windows):
```powershell
python test/run_all_tests.py
```

## License

MIT. See [LICENSE](LICENSE).
