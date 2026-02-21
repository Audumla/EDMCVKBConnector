# VKB-Link Setup

This guide covers the practical setup flow for using VKB-Link with this plugin.

## Decide Your Mode

- If you already use VKB-Link manually, you can keep that workflow.
- If you are not already using VKB-Link, use plugin-managed mode by leaving **Auto-manage** enabled.

Plugin-managed mode can download, start, restart, and update VKB-Link.  
If VKB-Link was already running before plugin startup, plugin shutdown leaves it running.

## One-Time VKBDevCfg Setup (Master Device)

VKB-Link applies shift/subshift updates to one selected *master* device.

1. Open **VKBDevCfg** (v0.93.96+).
2. Connect to the device you want to be the master.
3. Open the tab where the **Slave** settings are shown.
4. Enable **Global SHIFT**.
5. Enable **Global SubSHIFTs**.
6. Write the configuration to the device.

Also keep your device firmware current (v2.21.3+ recommended).

## Configure VKB-Link Once It Is Running

1. Launch VKB-Link.
2. In the VKB-Link device list, select the same master device configured above.
3. Enable the TCP server.
4. Set TCP endpoint to match plugin settings (default `127.0.0.1:50995`).

## Plugin-Managed Workflow (Recommended for New Users)

1. Open `File -> Settings -> Plugins -> VKB Connector`.
2. In the **VKB-Link** section, keep **Auto-manage** enabled.
3. Set `Host` and `Port` (defaults are fine unless you changed VKB-Link TCP settings).
4. If no VKB-Link executable is known and no process is running, the plugin will download/install VKB-Link and start it.
5. Use **Locate...** only if you want to point the plugin at an existing install.
6. Use **Check Version** to update managed VKB-Link.

Operational behavior in managed mode:

- The plugin enforces a single `VKB-Link.exe` process.
- Host/port changes trigger stop -> INI update -> start when managed mode is active.
- On shutdown, the plugin sends a blank shift/subshift state before disconnect.
- The plugin stops VKB-Link on exit only if this plugin instance started it.

## Existing Manual Workflow (If You Already Use VKB-Link)

1. Start VKB-Link yourself.
2. Select your master device and enable TCP in VKB-Link.
3. Match plugin `Host`/`Port` to VKB-Link TCP settings.
4. If you do not want plugin process control, turn off **Auto-manage**.
5. Optional: use **Locate...** so the plugin can detect version/location consistently.

## Troubleshooting Basics

- If status is disconnected, verify host/port match on both sides.
- Ensure only one `VKB-Link.exe` is running.
- Re-check VKBDevCfg master-device settings (`Global SHIFT` and `Global SubSHIFTs`).
