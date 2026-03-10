# EDMCVKBConnector

EDMC plugin that turns Elite Dangerous state into VKB-Link `VKBShiftBitmap` actions using rule-based automation.

## Quick Start

1. Extract the plugin into your EDMC `plugins` folder.
2. Open `File -> Settings -> Plugins -> VKB Connector`.
3. Decide to let the plugin manage VKB-Link:
   - If you are not already using VKB-Link, leave **Auto-manage** enabled (recommended). The plugin can download, start, and update VKB-Link for you.
   - If you already run VKB-Link yourself, you can keep your existing setup and locate the ini file so the plugin can match it up.
4. Ensure your VKB setup meets the minimum supported versions:
   - **VKB-Link:** **0.8.2** or newer
   - **VKB device firmware:** **2.21.3** or newer
   - **VKBDevCfg used for device configuration:** **0.93.96**
5. In **VKB-Link**, make sure the selected **master device** has these enabled (**required**):
   - **Global SHIFTs**
   - **Global SubSHIFTs**

   These checkboxes are in the master device settings (shown under **Slave Settings** in VKBDevcfg).
6. `Host`/`Port` values will be written to the VKB-Link ini file once you point the plugin to your VKB-Link location or just let the plugin auto manage it all for you
7. Create rules in the **Rules** section.

Latest VKB Software and Firmware can be found here [https://www.njoy32.vkb-sim.pro/home]

For the full VKB-Link setup process (including master-device setup, managed mode, and manual mode), see:
[`docs/VKB_LINK_SETUP.md`](docs/VKB_LINK_SETUP.md)

## Documentation

- [docs/VKB_LINK_SETUP.md](docs/VKB_LINK_SETUP.md): VKBDevCfg master-device setup, VKB-Link TCP setup, minimum supported versions (VKB-Link **0.8.2+**, firmware **2.21.3+**, VKBDevCfg **0.93.96**), and plugin-managed/manual workflows.
- [docs/RULE_EDITOR_TUTORIAL.md](docs/RULE_EDITOR_TUTORIAL.md): step-by-step UI guide for creating and managing rules through the plugin settings panel.
- [docs/RULES_GUIDE.md](docs/RULES_GUIDE.md): complete `rules.json` file format reference (fields, operators, actions, validation).
- [docs/SIGNALS_REFERENCE.md](docs/SIGNALS_REFERENCE.md): complete signal catalog with source and trigger mapping.
- [docs/EDMC_EVENTS_CATALOG.md](docs/EDMC_EVENTS_CATALOG.md): raw EDMC/Journal event reference and status flags.
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): contributor workflow, runtime architecture, and test commands.
