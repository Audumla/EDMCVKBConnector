# EDMCVKBConnector

Forward Elite Dangerous game events to VKB HOTAS/HOSAS hardware via TCP/IP socket connection.

## Overview

EDMCVKBConnector is an [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector) plugin that captures game events from Elite Dangerous and forwards them to VKB HOTAS/HOSAS hardware via TCP/IP socket connection.

**Important Note**: The exact TCP protocol format for VKB-Link is currently under development. This plugin is designed with an abstracted message formatter that can be easily updated once VKB-Link's final protocol specification is available. Currently, it uses a placeholder formatter.

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
- **Configuration File Support**: Customize behavior via `config.json`
- **Debug Logging**: Optional debug mode for troubleshooting

## Installation

1. Download or clone this repository
2. Place the plugin folder in your EDMC plugins directory:
   - Windows: `%APPDATA%\EDMarketConnector\plugins\`
   - macOS: `~/Library/Application Support/EDMarketConnector/plugins/`
   - Linux: `~/.local/share/EDMarketConnector/plugins/`
3. Restart EDMC

## Configuration

Create a `config.json` file in the plugin directory:

```json
{
  "vkb_host": "192.168.1.100",
  "vkb_port": 12345,
  "enabled": true,
  "debug": false,
  "event_types": [
    "Location",
    "FSDJump",
    "DockingGranted",
    "Undocked",
    "LaunchSRV",
    "DockSRV",
    "Supercruise",
    "Docked"
  ]
```
}
```

### Configuration Options

- **vkb_host**: IP address of your VKB device (default: `127.0.0.1`)
- **vkb_port**: Port number for VKB communication (default: `12345`)
- **enabled**: Toggle plugin on/off (default: `true`)
- **debug**: Enable debug logging (default: `false`)
- **event_types**: List of game events to forward (omit to forward all events)

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

- Python 3.8 or higher
- EDMC 5.0 or higher

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/EDMCVKBConnector.git
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

```bash
pytest
```

### Code Style

This project uses Black for code formatting:

```bash
black src/ tests/
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
  - `PlaceholderMessageFormatter`: Current implementation (format TBD)
  - Easy to extend with custom formatters when protocol is finalized
- **EventHandler**: EDMC event processing and filtering
- **Config**: Configuration management and loading from JSON
- **load.py**: EDMC plugin entry point and event handlers

### Event Flow

```
EDMC Game Event
    ↓
load.py (journal_entry)
    ↓
EventHandler (handle_event)
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
3. **Protocol Conversion**: VKBClient delegates formatting to MessageFormatter
4. **Network Transmission**: Formatted bytes sent over TCP/IP

This separation ensures the event handling and network logic remains independent of the final wire format used by VKB-Link.

## Communication Protocol

**Status**: Protocol format TBD pending VKB-Link development

The plugin is designed with an abstracted message formatter to support the final VKB protocol once it's specified. Currently:

- Messages are abstracted through the `MessageFormatter` interface
- A `PlaceholderMessageFormatter` is used for development
- Once VKB-Link's final protocol is documented (expected to be compact binary with bitmap format), implement a custom `MessageFormatter` subclass

### Implementation Example

When VKB-Link's protocol is finalized, create a custom formatter:

```python
from edmcvkbconnector import MessageFormatter

class VKBProtocolFormatter(MessageFormatter):
    def format_event(self, event_type: str, event_data: dict) -> bytes:
        # Implement the actual VKB protocol format here
        # Expected: compact binary with bitmap for message content
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

1. Verify VKB device IP and port in `config.json`
2. Check firewall rules allow connection on specified port
3. Enable debug mode and check EDMC logs
4. Verify VKB device is running and accepting TCP connections

### Events Not Forwarding

1. Check `enabled` setting in config
2. Verify event type is in `event_types` list (if configured)
3. Enable debug mode for detailed logging
4. Check EDMC log file for error messages

### Debugging

Enable debug logging in `config.json`:

```json
{
  "debug": true
}
```

Then check EDMC log file for detailed output.

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
