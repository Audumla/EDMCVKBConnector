# EDMCVKBConnector

Forward Elite Dangerous game events to VKB HOTAS/HOSAS hardware via TCP/IP socket connection.

## Overview

EDMCVKBConnector is an [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector) plugin that captures game events from Elite Dangerous and forwards them to VKB HOTAS/HOSAS hardware via TCP/IP socket connection.

**Important Note**: The VKB-Link shift/subshift payload is implemented for `VKBShiftBitmap` packets. Other event formats remain abstracted behind a message formatter for future expansion.

This allows for real-time hardware state updates based on in-game events, enabling dynamic configuration and feedback on your VKB equipment.

## Requirements

- **Python**: 3.9 or higher (per latest EDMC standards)
- **EDMC**: 5.0 or higher (5.13.0+ recommended for full feature compatibility)
- **VKB-Link**: Compatible version with TCP/IP socket support

## Features

- **Event Forwarding**: Automatically captures and forwards Elite Dangerous game events
- **Configurable Event Types**: Filter which events get forwarded to VKB hardware
- **TCP/IP Communication**: Communicates with VKB hardware via standard network sockets
- **Fault-Tolerant Reconnection**: Automatically reconnects if VKB-Link stops or restarts
  - Aggressive retry every 2 seconds for the first minute
  - Fallback to 10-second retry intervals indefinitely
  - Transparent reconnection while EDMC continues running
- **Protocol Abstraction**: Pluggable message formatter design for future VKB protocol implementation
- **Proper Logging**: Integrates with EDMC's logging system for troubleshooting
- **EDMC Preferences Support**: Core settings stored via EDMC's config API
- **Rules File Support**: Define dynamic behavior in `rules.json`
- **Debug Logging**: Optional debug mode for troubleshooting
- **Comprehensive Testing**: 25+ tests across unit, integration, mock socket, and real hardware layers

## Installation

1. Download or clone this repository
2. Place the plugin folder in your EDMC plugins directory:
   - Windows: `%APPDATA%\EDMarketConnector\plugins\`
   - macOS: `~/Library/Application Support/EDMarketConnector/plugins/`
   - Linux: `~/.local/share/EDMarketConnector/plugins/`
3. Restart EDMC

## Configuration

Configuration is stored by EDMC in the system-appropriate location:
- **Windows**: Registry (HKEY_CURRENT_USER)
- **macOS**: User defaults (`com.frontier.edmc.`)
- **Linux**: User config directory

Settings are automatically persisted and shared with EDMC's preferences system. The plugin includes a preferences UI panel for VKB host/port.
Rules are stored in a `rules.json` file in the plugin directory (override path supported via `VKBConnector_rules_path`).

### Configuration Options

- **vkb_host**: IP address of your VKB device (default: `127.0.0.1`)
- **vkb_port**: Port number for VKB communication (default: `50995`)
- **vkb_header_byte**: VKB message header byte (default: `0xA5`)
- **vkb_command_byte**: VKB message command byte (default: `13`)
- **enabled**: Toggle plugin on/off (default: `true`)
- **debug**: Enable debug logging (default: `false`)
- **event_types**: List of game events to forward (default: Location, FSDJump, DockingGranted, etc.)
- **rules_path**: Optional override path to a `rules.json` file

### Rules File

Rules live in `rules.json` in the plugin directory and are evaluated against dashboard/status data
(`Flags`, `Flags2`, `GuiFocus`). Rules can apply shift/subshift updates or log messages.
If required fields are missing, a rule is indeterminate and no actions run. `else` only runs
when all fields are present and the rule evaluates false.

Example:
```json
[
  {
    "id": "hardpoints_deployed",
    "enabled": true,
    "when": {
      "source": "dashboard",
      "all": [
        { "flags": { "all_of": ["FlagsHardpointsDeployed"] } }
      ]
    },
    "then": {
      "vkb_set_shift": ["Shift1", "Subshift3"],
      "log": "Hard points deployed"
    },
    "else": {
      "vkb_clear_shift": ["Shift1", "Subshift3"]
    }
  }
]
```

### How to Set Configuration

Settings can be modified by:
1. **EDMC Preferences UI**: Open EDMC Settings and configure the VKB host/port
2. **Directly** (advanced users):
   - Windows: Use Registry Editor to add entries under `HKEY_CURRENT_USER\Software\Frontier Developments\EDMarketConnector` with prefix `VKBConnector_`
   - macOS/Linux: Modify EDMC's config files directly (consult EDMC documentation)

Example (Windows Registry):
```
HKEY_CURRENT_USER\Software\Frontier Developments\EDMarketConnector
  VKBConnector_vkb_host: "192.168.1.100"
  VKBConnector_vkb_port: 50995
```

## Supported Events

The plugin can forward any Elite Dangerous journal event. Common events include:

- `Location` - Commander location changed
- `FSDJump` - Hyperjump to another system
- `DockingGranted` - Docking permission granted
- `Undocked` - Ship undocked from station
- `LaunchSRV` - Launched SRV (buggy)
- `DockSRV` - Docked SRV
- `Supercruise` - Entered supercruise
- `Docked` - Docked at station
- `CombatBond` - Combat bond earned
- `Died` - Commander died

## Development

### Prerequisites

- Python 3.9 or higher (per latest EDMC standards)
- EDMC 5.0 or higher

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Audumla/EDMCVKBConnector.git
cd EDMCVKBConnector

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix/macOS:
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt -e .[dev]
```

### Running Tests

The project includes a comprehensive **4-layer test suite** with 25+ tests covering unit, integration, mock server, and real hardware levels.

**Quick Start**:
```bash
# Run development tests (unit + integration + mock server)
test.bat dev

# Run all tests except real hardware
test.bat all

# Run real hardware tests (requires VKB hardware)
$env:TEST_VKB_ENABLED = '1'
test.bat real
```

**Available Test Commands**:
```bash
test.bat unit          # Unit tests only
test.bat integration   # Integration tests only
test.bat server        # Mock VKB server tests
test.bat real          # Real VKB hardware tests
test.bat dev           # Unit + integration + server (~10s)
test.bat mock          # Mock server tests
test.bat all           # All except real (default)
```

**Test Suites**:
- **Unit Tests** (5 tests): Config and VKBClient initialization
- **Integration Tests** (6 tests): Event processing with mocked components
- **Mock Socket Tests** (8 tests): TCP/IP operations with simulated VKB server
- **Real Hardware Tests** (6 tests): Integration with actual VKB hardware via VKB-Link

**Documentation**:
- [Complete Test Suite Documentation](docs/TEST_SUITE.md) - Overview of all 25+ tests
- [Real Hardware Testing Guide](test/REAL_SERVER_TESTS.md) - Setup and troubleshooting for VKB hardware tests
- [Real Server Quick Start](docs/REAL_SERVER_SETUP.md) - Quick configuration guide

**Note**: Real hardware tests are disabled by default for safety. See [REAL_SERVER_SETUP.md](docs/REAL_SERVER_SETUP.md) for configuration instructions.

### Code Style

This project uses Black for code formatting:

```bash
black src/ test/
```

And Pylint for code linting:

```bash
pylint src/edmcvkbconnector/
```

## Architecture

### Main Components

- **VKBClient**: TCP/IP socket client for communicating with VKB hardware
  - Handles connection management with automatic reconnection
  - Abstracts message format through MessageFormatter interface
- **MessageFormatter**: Abstraction for VKB protocol serialization
  - `MessageFormatter`: Abstract base class defining the interface
  - `PlaceholderMessageFormatter`: Current implementation (VKBShiftBitmap supported)
  - Easy to extend with custom formatters when protocol is finalized
- **EventHandler**: EDMC event processing, rule evaluation, and shift/subshift updates
- **Config**: Configuration management via EDMC preferences
- **Rules Engine**: Evaluates dashboard/status rules and applies shift/subshift updates
- **load.py**: EDMC plugin entry point and event handlers

### Event Flow

```
EDMC Game Event
    ↓
load.py (journal_entry)
    ↓
EventHandler (handle_event)
    ↓
Rules Engine (match rules.json)
    ↓
VKBClient (send_event)
    ↓
MessageFormatter (format_event)
    ↓
TCP/IP Socket
    ↓
VKB Hardware (VKB-Link)
```

### Design Philosophy

The plugin is designed with **protocol abstraction** in mind:

1. **Event Reception**: EDMC natively provides events
2. **Event Processing**: EventHandler filters events based on configuration
3. **Rule Processing**: Rules in `rules.json` determine shift/subshift updates and logs
4. **Protocol Conversion**: VKBClient delegates formatting to MessageFormatter
4. **Network Transmission**: Formatted bytes sent over TCP/IP

This separation ensures the event handling and network logic remains independent of the final wire format used by VKB-Link.

## Communication Protocol

**Status**: Shift/subshift payload implemented for `VKBShiftBitmap`

The plugin uses an abstracted message formatter to support other VKB protocol messages in the future. Currently:

- `VKBShiftBitmap` is sent as an 8-byte packet:
  - `0xA5`, `CMD`, `0`, `4`, `SHIFTs`, `subSHIFTs`, `0`, `0`
- Other event types fall back to a simple text payload for debugging

### Implementation Example

When VKB-Link's protocol expands, create a custom formatter:

```python
from edmcvkbconnector import MessageFormatter

class VKBProtocolFormatter(MessageFormatter):
    def format_event(self, event_type: str, event_data: dict) -> bytes:
        # Implement the actual VKB protocol format here
        # Implement the VKB protocol format here
        pass

# Use custom formatter
from edmcvkbconnector import VKBClient
client = VKBClient(formatter=VKBProtocolFormatter())
```

### Expected Format Characteristics

Based on VKB-Link requirements, the final protocol is likely to:
- Use compact binary format to minimize message size
- Include bitmaps for message content flags
- Include status indicators for hardware state
- Be efficient for high-frequency event forwarding

## Troubleshooting

### Connection Issues

1. Verify VKB device IP and port in EDMC preferences or config store
2. Check firewall rules allow connection on specified port
3. Enable debug mode and check EDMC logs
4. Verify VKB device is running and accepting TCP connections

### Events Not Forwarding

1. Check `enabled` setting in config
2. Verify event type is in `event_types` list (if configured)
3. Enable debug mode for detailed logging
4. Check EDMC log file for error messages

### Debugging

Enable debug logging via EDMC config (`VKBConnector_debug = true`), then check EDMC log file for detailed output.

## License

This plugin is licensed under the **MIT License**.

EDMC is licensed under GNU GPL v2 or later. This plugin, as a derivative work, complies with GPL v2+ requirements. The MIT license is fully compatible with GNU GPL v2+.

See [LICENSE](LICENSE) file for full details.

## Standards Compliance

This plugin follows the [EDMC Plugin Browser Standards](https://github.com/EDCD/EDMC-Plugin-Registry/blob/main/docs/STANDARDS.md):

- ✅ **Semantic Versioning**: Version format is `MAJOR.MINOR.PATCH` (e.g., 0.1.0)
- ✅ **Compatibility**: Maintains compatibility with EDMC 5.0+ and updates with new versions
- ✅ **Open Source**: Licensed under MIT, compatible with GPL v2+
- ✅ **Ecosystem Respect**: No malicious content, proper naming, respects Elite Dangerous EULA
- ✅ **Least Privilege**: Uses only built-in Python modules, requests only network access
- ✅ **Code Quality**: PEP8 compliant, well-documented with type hints

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
