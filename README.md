# EDMCVKBConnector

**Automatically control your VKB HOTAS/HOSAS shift layers based on Elite Dangerous game state.**

EDMCVKBConnector is a plugin for Elite Dangerous Market Connector (EDMC) that monitors your in-game status and automatically activates different shift layers on your VKB hardware. Create rules to switch button mappings based on what you're doing - docking, fighting, exploring, or anything else!

## Features

✨ **Automatic Shift Control** - VKB shift layers activate based on game state  
🎯 **700+ Game Signals** - Monitor almost any aspect of Elite Dangerous  
📝 **Visual Rule Editor** - Create complex rules without writing JSON  
🔄 **Auto-Reconnect** - Handles VKB-Link restarts gracefully  
⚡ **Edge-Triggered** - Actions fire on state changes, not repeatedly  
🛠️ **Highly Configurable** - Create rules as simple or complex as you need

## Example Use Cases

- **Combat Mode**: Activate Shift1 when hardpoints are deployed
- **Docking Assist**: Enable special bindings when landing gear is down
- **Exploration**: Switch to exploration controls in FSS/SAA modes
- **SRV Operations**: Different controls when driving the SRV
- **Galaxy Map**: Custom bindings when the galaxy map is open
- **Station Services**: Auto-switch when docked at a station

## Quick Start

### For Users

1. **Install the plugin** - See [INSTALLATION.md](INSTALLATION.md) for complete instructions
2. **Configure VKB-Link** - Set up TCP connection (port 50995)
3. **Create rules** - Use the built-in Rule Editor or edit `rules.json`
4. **Launch Elite Dangerous** - Shifts activate automatically!

**📖 Read the full [Installation Guide](INSTALLATION.md)**

### For Developers

1. **Set up development environment:**
   ```bash
   python scripts/bootstrap_dev_env.py
   ```

2. **Run EDMC in development mode:**
   ```bash
   python scripts/run_edmc_from_dev.py
   ```

3. **Make changes and test** - Plugin loads directly from source

**📖 Read the full [Development Guide](DEVELOPMENT.md)**

## Compatibility

- **Python**: 3.9 or higher
- **EDMC**: 5.0+ (5.13+ recommended)
- **VKB-Link**: v0.8.2 or higher
- **VKB Firmware**: 2.21.3 or higher
- **Elite Dangerous**: Base game, Horizons, or Odyssey

## Documentation

### User Guides
- **[Installation Guide](INSTALLATION.md)** - Complete installation and setup instructions
- **[Rule Editor Guide](docs/RULE_EDITOR_GUIDE.md)** - How to create and edit rules visually
- **[Signals Reference](SIGNALS_CATALOG_REFERENCE.md)** - Complete list of all 700+ available signals
- **[VKB-Link Setup](docs/REAL_SERVER_SETUP.md)** - Configuring VKB-Link for the plugin

### Developer Documentation
- **[Development Guide](DEVELOPMENT.md)** - Setting up dev environment and contributing
- **[Architecture](docs/ARCHITECTURE.md)** - How the plugin works internally
- **[Rules Schema](docs/RULES_SCHEMA.md)** - Technical reference for rule JSON format
- **[Protocol Implementation](docs/PROTOCOL_IMPLEMENTATION.md)** - VKB-Link protocol details

## Configuration

Basic configuration is done through EDMC settings (File > Settings > Plugins):

- **VKB Host**: IP address of VKB-Link (default: `127.0.0.1`)
- **VKB Port**: TCP port for VKB-Link (default: `50995`)
- **Enabled**: Enable/disable the plugin
- **Debug**: Enable detailed logging for troubleshooting

VKB-Link must be configured to match:
```ini
[TCP]
Adress=127.0.0.1
Port=50995
```

## Creating Rules

### Using the Rule Editor (Recommended)

1. In EDMC: **File > Settings > Plugins**
2. Find **VKB Connector** section
3. Click **Open Rules Editor**
4. Click **New Rule** to create your first rule

The editor guides you through:
- Selecting signals to monitor
- Choosing comparison operators
- Setting conditions (when/if)
- Defining actions (then/else)

**See the [Rule Editor Guide](docs/RULE_EDITOR_GUIDE.md) for complete instructions.**

### Manual Rule Editing

Rules are stored in `rules.json` in the plugin directory:

```json
[
  {
    "id": "landing-gear",
    "title": "Landing Gear Down",
    "enabled": true,
    "when": {
      "all": [
        {
          "signal": "landing_gear",
          "op": "eq",
          "value": "deployed"
        }
      ]
    },
    "then": [
      {
        "vkb_set_shift": ["Shift1"]
      }
    ],
    "else": [
      {
        "vkb_clear_shift": ["Shift1"]
      }
    ]
  }
]
```

**See the [Rules Schema](docs/RULES_SCHEMA.md) for technical details.**

## Support

- **Documentation**: Check the guides in [docs/](docs/)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/Audumla/EDMCVKBConnector/issues)
- **Installation Help**: See [INSTALLATION.md](INSTALLATION.md)
- **Development**: See [DEVELOPMENT.md](DEVELOPMENT.md)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Elite Dangerous Market Connector team
- VKB Sim for their excellent hardware and VKB-Link software
- Elite Dangerous community
