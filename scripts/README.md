# Development Scripts

This directory contains scripts to streamline development and packaging of the EDMCVKBConnector plugin.

## Quick Start

### 1. Initial Setup (One-time)

```bash
python scripts/bootstrap_dev_env.py
```

This will:
- Clone the EDMC repository to `../EDMarketConnector` (if not already present)
- Create a virtual environment at `.venv`
- Install all development dependencies
- Install EDMC dependencies
- Link the plugin into the EDMC plugins directory

### 2. Run EDMC in Development Mode

```bash
python scripts/run_edmc_from_dev.py
```

This will:
- Launch EDMC from the cloned dev repository
- Use an **isolated dev configuration** (stored in `.edmc_dev_config/`)
- Your installed EDMC settings will remain untouched
- The plugin is loaded directly from this repository (via symlink)

### 3. Package Plugin for Distribution

```bash
python scripts/package_plugin.py
```

This creates a distributable ZIP file in the `dist/` directory that users can extract into their EDMC plugins folder.

---

## Detailed Usage

### bootstrap_dev_env.py

**Purpose:** Set up the complete development environment from scratch.

**What it does:**
1. Clones EDMC repository (if needed) or updates it
2. Creates Python virtual environment
3. Installs plugin development dependencies
4. Installs EDMC runtime dependencies
5. Links the plugin directory into EDMC plugins folder

**Options:**
```bash
# Basic usage (recommended)
python scripts/bootstrap_dev_env.py

# Skip EDMC repository update
python scripts/bootstrap_dev_env.py --no-edmc-update

# Skip EDMC Python dependencies
python scripts/bootstrap_dev_env.py --no-edmc-python-deps

# Run tests after bootstrap
python scripts/bootstrap_dev_env.py --run-tests

# Custom EDMC location
python scripts/bootstrap_dev_env.py --edmc-root /path/to/EDMarketConnector

# Custom virtual environment location
python scripts/bootstrap_dev_env.py --venv-dir /path/to/venv
```

---

### run_edmc_from_dev.py

**Purpose:** Launch EDMC from the dev repository with isolated configuration.

**What it does:**
1. Verifies EDMC dev repository and plugin are properly set up
2. Creates isolated dev config directory (`.edmc_dev_config/`)
3. Creates a minimal `config.toml` file in the dev config directory
4. Passes `--config .edmc_dev_config/config.toml` to EDMC
5. Launches EDMC with the plugin loaded directly from your working directory
6. Checks if EDMC dependencies are installed and installs them if needed

**How isolation works:**
EDMC accepts a `--config` command-line parameter that specifies a custom config file. This parameter is passed directly to EDMC, which reads all settings from that file instead of the system's EDMC configuration, achieving complete isolation.

**Benefits:**
- Your installed EDMC settings remain completely untouched
- Settings, plugins, and cache all stored in `.edmc_dev_config/`
- Plugin uses linked directory, no copying needed
- No risk of corrupting your production EDMC setup
- Easy to reset: just delete `.edmc_dev_config/` folder
- Clean, simple approach using EDMC's built-in parameter

**Options:**
```bash
# Basic usage (isolated config)
python scripts/run_edmc_from_dev.py

# Use your real EDMC config (for testing with actual commanders/credentials)
python scripts/run_edmc_from_dev.py --use-system-config

# Skip dependency check
python scripts/run_edmc_from_dev.py --no-ensure-deps

# Custom EDMC location
python scripts/run_edmc_from_dev.py --edmc-root /path/to/EDMarketConnector

# Custom Python executable
python scripts/run_edmc_from_dev.py --python /path/to/python

# Pass arguments to EDMC
python scripts/run_edmc_from_dev.py -- --trace --debug
```

---

### package_plugin.py

**Purpose:** Create a distributable ZIP file of the plugin.

**What it does:**
1. Reads version from `pyproject.toml` or `PLUGIN_REGISTRY.py`
2. Packages all necessary plugin files into a ZIP
3. Creates `dist/EDMCVKBConnector-<version>.zip`
4. Includes `rules.json` and `config.json` (falls back to `.example` files if not present)

**Output structure:**
```
EDMCVKBConnector-X.Y.Z.zip
└── EDMCVKBConnector/
    ├── load.py
    ├── PLUGIN_REGISTRY.py
    ├── LICENSE
    ├── README.md
    ├── rules.json
    ├── config.json
    ├── rules.json.example
    ├── config.json.example
    └── edmcruleengine/
        ├── __init__.py
        ├── config.py
        ├── event_handler.py
        ├── message_formatter.py
        ├── rules_engine.py
        └── vkb_client.py
```

Users can extract this directly into their EDMC plugins folder.

**Options:**
```bash
# Basic usage
python scripts/package_plugin.py
```

---

### dev_paths.py

**Purpose:** Centralized configuration helper for all development scripts.

**Configuration precedence** (highest to lowest):
1. Command-line arguments (e.g., `--edmc-root`)
2. Environment variables (e.g., `EDMC_DEV_ROOT`)
3. `dev_paths.json` file (create from `dev_paths.json.example`)
4. Default values (EDMC at `../EDMarketConnector`, venv at `.venv`)

**Supported environment variables:**
- `EDMC_DEV_ROOT` - EDMC repository location
- `EDMC_PLUGIN_DIR` - Plugin directory location
- `EDMC_DEV_PYTHON` - Python executable to use
- `EDMC_DEV_VENV` - Virtual environment location

**Example `dev_paths.json`:**
```json
{
  "edmc_root": "C:/dev/EDMarketConnector",
  "python_exec": "C:/Python311/python.exe",
  "venv_dir": ".venv"
}
```

---

## Development Workflow

### Daily Development

1. Make changes to plugin code in `src/edmcruleengine/` or `load.py`
2. Run `python scripts/run_edmc_from_dev.py` to test
3. EDMC will load your changes directly (no copying/packaging needed)
4. Restart EDMC to reload the plugin after code changes

### Testing with Fresh Config

```bash
# Remove dev config and restart
Remove-Item .edmc_dev_config -Recurse -Force
python scripts/run_edmc_from_dev.py
```

### Testing with Real Config

```bash
# Use your actual EDMC settings
python scripts/run_edmc_from_dev.py --use-system-config
```

### Release Process

1. Update version in `pyproject.toml` or `PLUGIN_REGISTRY.py`
2. Test thoroughly with `python scripts/run_edmc_from_dev.py`
3. Run tests: `python test/run_all_tests.py`
4. Package: `python scripts/package_plugin.py`
5. Distribute: Upload `dist/EDMCVKBConnector-X.Y.Z.zip`

---

## Troubleshooting

### Plugin not loading in EDMC

```bash
# Re-run bootstrap to re-link the plugin
python scripts/bootstrap_dev_env.py
```

### EDMC still uses my installed settings/plugins

The isolated config approach uses EDMC's `--config` parameter to specify a custom config file. Check:

```bash
# Delete the dev config directory and start fresh
Remove-Item .edmc_dev_config -Recurse -Force

# Run again - should see in console output
python scripts/run_edmc_from_dev.py
```

Console output should show:
```
[INFO] Using isolated dev config: ...\EDMCVKBConnector\.edmc_dev_config\config.toml
```

If EDMC loads your real config instead:
1. Verify the script passes `--config` to EDMC (check console output)
2. Delete `.edmc_dev_config/` and try again
3. Check that the plugin is linked: `ls ..\EDMarketConnector\plugins\EDMCVKBConnector`

See console output for exact config path being used. If it shows your system EDMC path instead of `.edmc_dev_config`, report the issue.

### EDMC crashes on startup

```bash
# Check dependencies are installed
python scripts/run_edmc_from_dev.py

# If that fails, reinstall EDMC deps
python scripts/bootstrap_dev_env.py --no-edmc-update
```

### Changes not appearing

- EDMC caches plugin imports - restart EDMC to reload
- Check you're running from dev repo: `python scripts/run_edmc_from_dev.py`
- Verify plugin is linked: Check `../EDMarketConnector/plugins/EDMCVKBConnector` exists

### Using different EDMC location

```bash
# Set via environment variable
$env:EDMC_DEV_ROOT = "D:\MyCustomLocation\EDMarketConnector"
python scripts/run_edmc_from_dev.py

# Or use command-line flag
python scripts/run_edmc_from_dev.py --edmc-root D:\MyCustomLocation\EDMarketConnector
```

---

## File Structure

```
scripts/
├── README.md                  # This file
├── bootstrap_dev_env.py       # Initial setup + linking
├── run_edmc_from_dev.py       # Run EDMC with isolated config
├── package_plugin.py          # Create distributable ZIP
└── dev_paths.py               # Configuration helper
```

## Notes

- The `.edmc_dev_config/` directory is git-ignored and safe to delete
- Plugin linking uses symlinks on Unix/Mac and junctions on Windows
- All scripts support `dev_paths.json` for custom configuration
- Scripts are designed to be idempotent (safe to run multiple times)
