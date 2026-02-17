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

### For Users

Users should follow the complete [INSTALLATION.md](../INSTALLATION.md) guide which covers:
- Prerequisites and compatibility
- Downloading and installing the plugin
- Configuring VKB-Link
- Creating rules

### For Developers

Developers should follow the [DEVELOPMENT.md](../DEVELOPMENT.md) guide which covers:
- Setting up the development environment
- Running EDMC in development mode
- Making changes and testing
- Packaging for distribution

Quick start for development:
1. **Bootstrap** - Set up development environment:
   ```bash
   python scripts/bootstrap_dev_env.py
   ```

2. **Run EDMC** - Launch EDMC with isolated dev config:
   ```bash
   python scripts/run_edmc_from_dev.py
   ```

3. **Package** - Create distributable ZIP:
   ```bash
   python scripts/package_plugin.py
   ```

Compatibility baseline:
- Python: `3.9+`
- EDMC: `5.0+` (5.13+ recommended)
- VKB-Link: `v0.8.2+`
- VKB firmware: `2.21.3+`
- VKB software/firmware: https://www.njoy32.vkb-sim.pro/home

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

Use the provided packaging script:

```bash
python scripts/package_plugin.py
```

This creates `dist/EDMCVKBConnector-<version>.zip` with the correct structure for distribution.

To manually create a release archive:

```bash
# Create deployment package
mkdir -p build/EDMCVKBConnector

# Copy necessary files
cp -r src/edmcruleengine build/EDMCVKBConnector/
cp load.py build/EDMCVKBConnector/
cp PLUGIN_REGISTRY.py build/EDMCVKBConnector/
cp README.md build/EDMCVKBConnector/
cp LICENSE build/EDMCVKBConnector/
cp rules.json.example build/EDMCVKBConnector/
cp config.json.example build/EDMCVKBConnector/
cp signals_catalog.json build/EDMCVKBConnector/

# Create archive
cd build
zip -r EDMCVKBConnector-X.Y.Z.zip EDMCVKBConnector/

# Calculate SHA256 for registry
sha256sum EDMCVKBConnector-X.Y.Z.zip

# Upload to GitHub releases
```

## Testing the Deployment

1. **Verify File Structure**:
   ```bash
   ls -la <EDMC Plugins>/EDMCVKBConnector/
   # Should see: load.py, edmcruleengine/, PLUGIN_REGISTRY.py, README.md, etc.
   ```

2. **Check EDMC Output**:
   - Open EDMC log: File > Settings > Advanced > Show Log
   - Look for VKB Connector messages

3. **Look for Plugin Message**:
   ```
   VKB Connector v0.1.0 starting
   Successfully connected to VKB hardware on startup
   ```

4. **Test Event Forwarding**:
   - Start Elite Dangerous
   - Perform in-game actions (jump systems, dock, etc.)
   - Check VKB hardware responds
   - Enable debug mode in EDMC settings for more logging

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

For more information, see:
- [INSTALLATION.md](../INSTALLATION.md) - User installation guide
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Development guide
- [README.md](../README.md) - Project overview
