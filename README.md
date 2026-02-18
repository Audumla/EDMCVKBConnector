# EDMCVKBConnector

EDMC plugin that turns Elite Dangerous state into VKB-Link `VKBShiftBitmap` actions using rule-based automation.

## Quick Start

### 1. Prepare Your VKB Hardware

Before installing the plugin you need compatible firmware, software, and a one-time device configuration.

#### Firmware
Update all VKB devices that will participate to firmware **v2.21.3 or newer** using VKBDevCfg.

#### VKB-Link
Download and install **VKB-Link v0.8.2 or newer** from the VKB software page:
<https://www.njoy32.vkb-sim.pro/home> → **Software**

#### Configure the master device in VKBDevCfg (v0.93.96 or newer)

VKB-Link works with a *master* device — the one that receives and applies the shift states sent by this plugin.

1. Open **VKBDevCfg** and connect to the device you want to use as the master.
2. Go to the **Slave** settings tab for that device.
3. Enable **Global SHIFT**.
4. Enable **Global SubSHIFTs**.
5. Write the configuration to the device.

#### Start VKB-Link
1. Launch VKB-Link.
2. In the device list, select your master device.
3. Enable the TCP server. The default address is `127.0.0.1`, port `50995`.

VKB-Link must be running whenever you play Elite Dangerous for the plugin to send shift states.

---

### 2. Install the Plugin
1. Close EDMC.
2. Download the latest plugin release ZIP.
3. Extract the `EDMCVKBConnector` folder into your EDMC `plugins` directory.
4. Start EDMC.

### 3. Connect to VKB-Link
1. Open `File -> Settings -> Plugins`.
2. Select **VKB Connector**.
3. Confirm `Host` and `Port` match your VKB-Link TCP settings (defaults: `127.0.0.1` / `50995`).
4. The status line under the host/port fields shows **Connected** when the link is active.

#### Linking the VKB-Link INI file (recommended)

The plugin can write your Host and Port directly into the VKB-Link INI configuration file so both are always in sync:

1. When the status shows **Disconnected**, a **Configure INI…** button appears next to the status line.
2. Click **Configure INI…** and browse to your VKB-Link INI file (typically in the VKB-Link installation folder, e.g. `C:\Program Files\VKBcontroller\VKB-Sim\VKBLink\VKBLink.ini`).
3. The plugin writes the current Host and Port into the `[TCP]` section of the file and saves the path.
4. After saving, restart VKB-Link if it was already running so it picks up the new settings.

Once the INI path is saved, **any future change to Host or Port in the plugin automatically updates the INI file** — you never need to edit it by hand again.

### 4. Add Your First Rule
1. In **VKB Connector**, open the **Rules** section.
2. Click **New Rule**.
3. Add a condition and `then` action.
4. Save and verify the rule is enabled.

## Documentation

- [docs/RULE_EDITOR_TUTORIAL.md](docs/RULE_EDITOR_TUTORIAL.md): step-by-step UI guide for creating and managing rules through the plugin settings panel.
- [docs/RULES_GUIDE.md](docs/RULES_GUIDE.md): complete `rules.json` file format reference (fields, operators, actions, validation).
- [docs/SIGNALS_REFERENCE.md](docs/SIGNALS_REFERENCE.md): complete signal catalog with source and trigger mapping.
- [docs/EDMC_EVENTS_CATALOG.md](docs/EDMC_EVENTS_CATALOG.md): raw EDMC/Journal event reference and status flags.
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): contributor workflow, runtime architecture, and test commands.
