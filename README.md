# EDMCVKBConnector

EDMC plugin that turns Elite Dangerous state into VKB-Link `VKBShiftBitmap` actions using rule-based automation.

## Quick Start

1. Prepare your VKB master device once in VKBDevCfg.
2. Install the plugin into your EDMC `plugins` folder.
3. Open `File -> Settings -> Plugins -> VKB Connector`.
4. Decide VKB-Link mode:
   - If you are not already using VKB-Link, leave **Auto-manage** enabled (recommended). The plugin can download, start, and update VKB-Link for you.
   - If you already run VKB-Link yourself, keep your existing setup and just match host/port.
5. Confirm `Host`/`Port` and check status shows connected.
6. Create rules in the **Rules** section.

Latest VKB Software and Firmware can be found here [https://www.njoy32.vkb-sim.pro/home]

For the full VKB-Link setup process (including master-device setup, managed mode, and manual mode), see:
[`docs/VKB_LINK_SETUP.md`](docs/VKB_LINK_SETUP.md)

## Documentation

- [docs/VKB_LINK_SETUP.md](docs/VKB_LINK_SETUP.md): VKBDevCfg master-device setup, VKB-Link TCP setup, and plugin-managed/manual workflows.
- [docs/RULE_EDITOR_TUTORIAL.md](docs/RULE_EDITOR_TUTORIAL.md): step-by-step UI guide for creating and managing rules through the plugin settings panel.
- [docs/RULES_GUIDE.md](docs/RULES_GUIDE.md): complete `rules.json` file format reference (fields, operators, actions, validation).
- [docs/SIGNALS_REFERENCE.md](docs/SIGNALS_REFERENCE.md): complete signal catalog with source and trigger mapping.
- [docs/EDMC_EVENTS_CATALOG.md](docs/EDMC_EVENTS_CATALOG.md): raw EDMC/Journal event reference and status flags.
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): contributor workflow, runtime architecture, and test commands.
