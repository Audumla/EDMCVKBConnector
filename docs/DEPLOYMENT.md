# Plugin Deployment Guide

This document explains how to properly deploy EDMCVKBConnector as an EDMC plugin.

## Development vs. Deployment Structure

### Development Structure (This Repository)
```
EDMCVKBConnector/
  src/
    edmcruleengine/
      __init__.py
      config.py
      vkb_client.py
      event_handler.py
  load.py                    # EDMC entry point
  pyproject.toml
  requirements.txt
  README.md
  LICENSE
  ...
```

### Deployment Structure (EDMC Plugins Directory)
```
<EDMC Plugins>/
  EDMCVKBConnector/
    load.py                  # EDMC entry point
    edmcruleengine/
      __init__.py
      config.py
      vkb_client.py
      event_handler.py
    README.md
    rules.json.example
    ...
```

## Installation

### For Users (From Release)

1. **Download** the latest release archive from GitHub
2. **Extract** the archive to your EDMC plugins directory:
   - **Windows**: `%APPDATA%\EDMarketConnector\plugins\`
   - **macOS**: `~/Library/Application Support/EDMarketConnector/plugins/`
   - **Linux**: `~/.local/share/EDMarketConnector/plugins/`
3. **Restart** EDMC
4. **Configure** in EDMC preferences (VKB host/port) and optionally create `rules.json`

Compatibility baseline:
- VKB-Link `v0.8.2+`
- VKB firmware `2.21.3+`
- VKB software/firmware source: https://www.njoy32.vkb-sim.pro/home

### For Developers (From Source)

The repository includes a `src/` directory for development organization. When deploying:

1. **Option A**: Install in editable mode in EDMC plugins directory:
   ```bash
   cd <EDMC Plugins>
   git clone https://github.com/Audumla/EDMCVKBConnector.git
   cd EDMCVKBConnector
   pip install -e .
   ```

2. **Option B**: Copy the deployment structure manually:
   ```bash
   # Copy only the necessary files
   cp -r src/edmcruleengine <EDMC Plugins>/EDMCVKBConnector/
   cp load.py <EDMC Plugins>/EDMCVKBConnector/
   cp README.md <EDMC Plugins>/EDMCVKBConnector/
   cp rules.json.example <EDMC Plugins>/EDMCVKBConnector/
   ```

## EDMC Plugin Entry Point

EDMC loads plugins by:
1. Reading `load.py` from the plugin directory
2. Calling `plugin_start3(plugin_dir)` function
3. Calling `journal_entry(cmdr, is_beta, system, station, entry, state)` for journal events
4. Calling other supported notification hooks (`dashboard_entry`, `cmdr_data`, `capi_fleetcarrier`)
5. Calling `plugin_stop()` on shutdown

The `load.py` module in the deployment root:
- Imports from the internal `edmcruleengine` package
- Registers event handlers
- Manages plugin lifecycle
- Handles configuration loading

## Configuration

Core settings (host/port/debug/etc.) are stored via EDMC preferences.
Open EDMC Settings and edit the VKB host/port. Advanced users can edit
the EDMC config store directly with the `VKBConnector_` prefix.

Default plugin endpoint is `127.0.0.1:50995`. Ensure VKB-Link is set to the same
address/port in its `ini` file:

```ini
[TCP]
Adress=127.0.0.1
Port=50995
```

Rules are defined in `rules.json` in the plugin directory (or via
`VKBConnector_rules_path` override).

## Import Path Resolution

The plugin uses relative imports:
```python
from edmcruleengine import Config, EventHandler
```

When EDMC loads the plugin:
1. The plugin directory becomes part of `sys.path`
2. `load.py` can directly import from `edmcruleengine/`
3. `edmcruleengine/__init__.py` imports submodules

This works because:
- `load.py` is in the deployment root
- `edmcruleengine/` package is adjacent to `load.py`
- EDMC adds the plugin directory to the Python path

## Building a Release

To create a release archive for users:

```bash
# Create deployment package
mkdir -p build/EDMCVKBConnector

# Copy necessary files
cp -r src/edmcruleengine build/EDMCVKBConnector/
cp load.py build/EDMCVKBConnector/
cp README.md build/EDMCVKBConnector/
cp LICENSE build/EDMCVKBConnector/
cp rules.json.example build/EDMCVKBConnector/
cp pyproject.toml build/EDMCVKBConnector/

# Create archive
cd build
zip -r EDMCVKBConnector-0.1.0.zip EDMCVKBConnector/

# Calculate SHA256 for registry
sha256sum EDMCVKBConnector-0.1.0.zip

# Upload to GitHub releases
```

## Testing the Deployment

1. **Verify File Structure**:
   ```bash
   ls -la <EDMC Plugins>/EDMCVKBConnector/
   # Should see: load.py, edmcruleengine/, README.md, etc.
   ```

2. **Check EDMC Log**:
   EDMC logs to:
   - **Windows**: `%TEMP%\EDMarketConnector.log`
   - **macOS**: `~/Library/Logs/EDMarketConnector.log`
   - **Linux**: `~/.local/share/EDMarketConnector/EDMC.log`

3. **Look for Plugin Message**:
   ```
   VKB Connector v0.1.0 starting
   Successfully connected to VKB hardware on startup
   ```

4. **Test Event Forwarding**:
   - Start Elite Dangerous
   - Perform in-game actions (jump systems, dock, etc.)
   - Check VKB hardware responds
   - Enable debug mode in EDMC config for more logging

## Troubleshooting Deployment

### Plugin Not Loading

- **Check File Structure**: Ensure `load.py` is in the plugin directory root
- **Check Log File**: Look for error messages in EDMC log
- **Verify Python**: Ensure EDMC is using Python 3.9+
- **Restart EDMC**: Changes to plugins require EDMC restart

### Import Errors

- **Module Not Found**: Verify `edmcruleengine/` directory exists
- **Check Permissions**: Ensure plugin directory is readable
- **Path Issues**: Verify directory structure matches deployment structure

### Connection Issues

- **VKB Not Starting**: Ensure VKB-Link is running before EDMC
- **Wrong IP/Port**: Check EDMC preferences
- **Firewall**: Verify firewall allows TCP connection
- **Enable Debug**: Set `"debug": true` in EDMC config for detailed logs

## Uninstallation

To remove the plugin:
1. Delete the `EDMCVKBConnector` directory from your EDMC plugins folder
2. Restart EDMC

The plugin is completely self-contained and leaves no residual files.

---

For more information, see the main [README.md](../README.md) or [STANDARDS_COMPLIANCE.md](STANDARDS_COMPLIANCE.md).
