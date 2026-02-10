# EDMCVKBConnector

Forward Elite Dangerous game events to VKB HOTAS/HOSAS hardware via TCP/IP socket connection.

## Overview

EDMCVKBConnector is an [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector) plugin that captures game events from Elite Dangerous and forwards them to VKB-Link to set the status of shift codes.

This allows for real-time hardware state updates based on in-game events, enabling dynamic configuration and feedback on your VKB equipment.

## Features

- **Event Forwarding**: Automatically captures and forwards Elite Dangerous game events
- **Configurable Event Types**: Filter which events get forwarded to VKB hardware
- **TCP/IP Communication**: Communicates with VKB hardware via standard network sockets
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
- **Config**: Configuration management and loading from JSON
- **EventHandler**: EDMC event processing and filtering
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
VKB Hardware (TCP/IP socket)
```

## Communication Protocol

Events are sent to VKB hardware as JSON-formatted messages over TCP/IP:

```json
{
  "event": "FSDJump",
  "data": {
    "timestamp": "2025-02-10T12:34:56Z",
    "event": "FSDJump",
    "StarSystem": "Sol",
    "SystemAddress": 10477373803,
    "StarPos": [0, 0, 0],
    "SystemAllegiance": "Federation"
  }
}
```

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

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
