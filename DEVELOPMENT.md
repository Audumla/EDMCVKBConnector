# EDMCVKBConnector - Development Guide

This guide covers setting up a development environment and contributing to EDMCVKBConnector.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Packaging](#packaging)
6. [Architecture](#architecture)
7. [Contributing](#contributing)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Virtual environment support (venv)

### Quick Setup

The bootstrap script handles the complete development environment setup:

```bash
python scripts/bootstrap_dev_env.py
```

This script will:
1. Clone the EDMC repository to `../EDMarketConnector`
2. Create a Python virtual environment at `.venv`
3. Install all dependencies (including development tools)
4. Create a symbolic link from EDMC's plugins directory to your source code

### Manual Setup

If you prefer manual setup or need to troubleshoot:

1. **Clone EDMC:**
   ```bash
   cd ..
   git clone https://github.com/EDCD/EDMarketConnector.git
   cd EDMCVKBConnector
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e ../EDMarketConnector  # Install EDMC in editable mode
   ```

4. **Link plugin to EDMC:**
   - On Linux/Mac:
     ```bash
     ln -s "$(pwd)/src/edmcruleengine" "../EDMarketConnector/plugins/EDMCVKBConnector"
     ```
   - On Windows (as Administrator):
     ```cmd
     mklink /D "..\EDMarketConnector\plugins\EDMCVKBConnector" "%CD%\src\edmcruleengine"
     ```

## Project Structure

```
EDMCVKBConnector/
├── src/
│   └── edmcruleengine/       # Main plugin source code
│       ├── __init__.py       # Plugin entry point
│       ├── config.py         # Configuration management
│       ├── event_handler.py  # EDMC event processing
│       ├── rule_engine.py    # Rule evaluation engine
│       ├── rule_editor.py    # Visual rule editor GUI
│       ├── signal_derivation.py  # Signal catalog processing
│       └── vkb_client.py     # VKB-Link TCP client
├── test/                     # Test suite
│   ├── test_rule_engine.py
│   ├── test_signals.py
│   └── ...
├── scripts/                  # Development tools
│   ├── bootstrap_dev_env.py
│   ├── run_edmc_from_dev.py
│   └── package_plugin.py
├── docs/                     # Documentation
├── signals_catalog.json      # Complete signal definitions
├── rules.json.example        # Example rules
├── config.json.example       # Example configuration
├── load.py                   # EDMC plugin loader
├── PLUGIN_REGISTRY.py        # Plugin metadata
└── README.md
```

### Key Files

- **`load.py`**: EDMC plugin entry point, defines hooks
- **`PLUGIN_REGISTRY.py`**: Plugin metadata for EDMC plugin browser
- **`signals_catalog.json`**: Master signal definitions (700+ signals)
- **`src/edmcruleengine/`**: Main plugin code
- **`test/`**: Comprehensive test suite

## Development Workflow

### Running EDMC in Development Mode

#### Option 1: Isolated Development Config (Recommended)

Use a completely isolated EDMC configuration that won't affect your real EDMC setup:

```bash
python scripts/run_edmc_from_dev.py
```

This creates an isolated config in `.edmc_dev_config/` and runs EDMC with it.

**Benefits:**
- Your installed EDMC configuration is untouched
- Clean slate for testing
- Easy to reset (just delete `.edmc_dev_config/`)
- Plugin loads directly from source via symlink

#### Option 2: Use Real EDMC Config

Test with your actual EDMC configuration and commander data:

```bash
python scripts/run_edmc_from_dev.py --use-system-config
```

**Use when:**
- Testing with real commander data
- Verifying compatibility with your actual setup
- Final testing before release

### Development Iteration Loop

1. **Make code changes** in `src/edmcruleengine/`
2. **Run EDMC** with `run_edmc_from_dev.py`
3. **Test changes** in-game or with test data
4. **Check logs** in EDMC (File > Settings > Advanced > Show Log)
5. **Repeat**

### VS Code Integration

The project includes VS Code tasks (Terminal > Run Task):

- **EDMC: Bootstrap Dev Environment** - Initial setup
- **EDMC: Bootstrap + Run Tests** - Setup and run tests
- **EDMC: Run EDMC (DEV)** - Launch with isolated config
- **EDMC: Run EDMC (DEV - System Config)** - Launch with real config
- **EDMC: Package Plugin** - Create distribution ZIP

## Testing

### Running Tests

The project uses pytest for testing:

```bash
# Activate virtual environment first
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Run all tests
pytest

# Run specific test file
pytest test/test_rule_engine.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=edmcruleengine
```

### Test Structure

- **`test/test_rule_engine.py`**: Rule evaluation logic
- **`test/test_signals.py`**: Signal derivation and catalog
- **`test/test_vkb_client.py`**: VKB-Link communication
- **`test/test_unregistered_events.py`**: Unregistered event tracking
- **`test/test_config.py`**: Configuration management

### Writing Tests

Follow existing test patterns:

```python
import pytest
from edmcruleengine import signal_derivation

def test_signal_derivation():
    """Test that a signal derives correctly from game data."""
    state = {
        'dashboard': {'GuiFocus': 6}  # Galaxy map
    }
    result = signal_derivation.derive_signal('gui_focus', state)
    assert result == 'GalaxyMap'
```

## Packaging

### Creating a Distribution

Package the plugin for distribution:

```bash
python scripts/package_plugin.py
```

This creates `EDMCVKBConnector-vX.X.X.zip` in the `dist/` folder containing:
- All plugin files
- Example configuration files
- Documentation
- LICENSE

### Package Contents

The distribution includes:
- `load.py` - Plugin loader
- `PLUGIN_REGISTRY.py` - Plugin metadata
- `src/edmcruleengine/` - Plugin source
- `signals_catalog.json` - Signal definitions
- `rules.json.example` - Example rules
- `config.json.example` - Example config
- `README.md` - User documentation
- `LICENSE` - MIT license

## Architecture

### Plugin Lifecycle

```text
EDMC Start
  ↓
load.py: plugin_start()
  ↓
Initialize EventHandler
  ↓
Load signals catalog
  ↓
Load rules.json
  ↓
Connect to VKB-Link
  ↓
EDMC Event Loop
  ↓
journal_entry() / dashboard_entry() / ...
  ↓
EventHandler.process_*()
  ↓
Update state dictionary
  ↓
Derive signals from state
  ↓
Evaluate rules
  ↓
Send VKBShiftBitmap to VKB-Link
  ↓
Repeat...
```

### Key Components

#### Signal Derivation (`signal_derivation.py`)

Converts raw Elite Dangerous data into high-level signals:
- Reads `signals_catalog.json` for signal definitions
- Processes dashboard, journal, and CAPI data
- Derives 700+ signals from game state
- Handles temporal signals (e.g., "just_docked", "under_attack")

#### Rule Engine (`rule_engine.py`)

Evaluates rules and executes actions:
- Edge-triggered evaluation (fires on state transitions only)
- Supports `all` (AND) and `any` (OR) condition groups
- Actions: `vkb_set_shift`, `vkb_clear_shift`, `log`
- Maintains condition history to detect edges

#### VKB Client (`vkb_client.py`)

Manages VKB-Link TCP connection:
- Sends `VKBShiftBitmap` packets
- Auto-reconnection on disconnect
- Shift state management (Shift1-2, Subshift1-7)
- Thread-safe operation

#### Event Handler (`event_handler.py`)

EDMC integration layer:
- Implements EDMC callback hooks
- Maintains unified game state dictionary
- Coordinates signal derivation and rule evaluation
- Handles configuration updates

### Logging

All modules use EDMC-compatible logging:

```python
from . import plugin_logger
logger = plugin_logger(__name__)

logger.info("Important information")
logger.debug("Detailed debug info")
logger.error("Error occurred")
```

Logs appear in EDMC's log (File > Settings > Advanced > Show Log).

### State Management

The plugin maintains a unified state dictionary:

```python
{
    'dashboard': {  # From Status.json
        'GuiFocus': 6,
        'Flags': 123456,
        'Pips': [2, 8, 2],
        ...
    },
    'state': {  # From journal events
        'Commander': 'CMDR Name',
        'ShipType': 'sidewinder',
        'Location': {...},
        ...
    },
    'last_events': {  # Recent journal events
        'Location': {...},
        'FSDJump': {...},
        ...
    }
}
```

Signals derive from this state using paths and operations defined in `signals_catalog.json`.

## Contributing

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where practical
- Write docstrings for public functions
- Keep functions focused and small

### Commit Messages

Use conventional commit format:

```
feat: add new signal for cargo scoop status
fix: correct fuel level calculation
docs: update installation guide
test: add tests for rule edge triggering
refactor: simplify signal derivation logic
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add/update tests
5. Run the test suite
6. Update documentation
7. Commit your changes
8. Push to your fork
9. Open a Pull Request

### Testing Requirements

- All new features must include tests
- Tests must pass before PR is merged
- Aim for high code coverage
- Test edge cases and error conditions

### Documentation Requirements

- Update relevant documentation for any changes
- Add docstrings to new functions/classes
- Update CHANGELOG.md with notable changes
- Include examples for new features

## Debugging Tips

### Enable Debug Mode

In EDMC settings, enable VKB Connector debug mode for verbose logging.

### Common Issues

**Plugin not loading:**
- Check EDMC log for Python errors
- Verify symlink is correct
- Check `load.py` is present

**Rules not evaluating:**
- Enable debug mode
- Check signal values in log
- Verify rules.json syntax
- Test with simple rules first

**VKB connection issues:**
- Verify VKB-Link is running
- Check port configuration
- Test TCP connection: `telnet 127.0.0.1 50995`
- Check firewall settings

### Interactive Debugging

Use Python's debugger:

```python
import pdb; pdb.set_trace()  # Add to code where you want to break
```

Or use VS Code's debugger with EDMC launch configuration.

## Additional Resources

- **EDMC Plugin Development:** https://github.com/EDCD/EDMarketConnector/wiki/Plugins
- **VKB-Link Protocol:** See [docs/PROTOCOL_IMPLEMENTATION.md](docs/PROTOCOL_IMPLEMENTATION.md)
- **Elite Dangerous Journal:** https://elite-journal.readthedocs.io/
- **Project Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
