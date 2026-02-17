# EDMCVKBConnector - Installation Guide

This guide will help you install and configure the EDMCVKBConnector plugin for Elite Dangerous Market Connector (EDMC).

## What is EDMCVKBConnector?

EDMCVKBConnector is an EDMC plugin that automatically controls your VKB HOTAS/HOSAS shift layers based on your in-game state in Elite Dangerous. It monitors game events and status, then sends commands to your VKB hardware via VKB-Link to activate different shift layers for different game situations.

**Example use cases:**
- Automatically activate different button mappings when docking vs. in combat
- Switch shift layers when entering the galaxy map or FSS mode
- Enable special bindings when landing gear is deployed
- Configure different controls for SRV vs. ship operations

## Prerequisites

Before installing EDMCVKBConnector, you need:

### Required Software

1. **Elite Dangerous** (with Horizons or Odyssey)
2. **Elite Dangerous Market Connector (EDMC)** version 5.0 or higher
   - Download from: https://github.com/EDCD/EDMarketConnector/releases
   - Version 5.13+ is recommended
3. **VKB-Link** version 0.8.2 or higher
   - Download from: https://www.njoy32.vkb-sim.pro/home
   - This is the VKB software that communicates with your hardware

### Required Hardware

- **VKB HOTAS/HOSAS device** with firmware version 2.21.3 or higher
  - Supported devices: VKB Gladiator NXT, Gunfighter series, STECS series, etc.
  - Your device must support shift/subshift layers

### Verify VKB Firmware Version

1. Open **VKBDevCfg** (comes with VKB-Link)
2. Connect your device
3. Check the firmware version in the device information
4. If needed, update firmware using VKBDevCfg

## Installation Steps

### Step 1: Download the Plugin

1. Go to the [Releases page](https://github.com/Audumla/EDMCVKBConnector/releases)
2. Download the latest `EDMCVKBConnector-vX.X.X.zip` file
3. Extract the ZIP file to a temporary location

### Step 2: Install the Plugin

1. **Open EDMC's plugins folder:**
   - In EDMC, go to **File > Settings**
   - Click the **Plugins** tab
   - Click the **Open** button next to "Plugins folder"

2. **Copy the plugin files:**
   - Copy the entire `EDMCVKBConnector` folder from the extracted ZIP
   - Paste it into the EDMC plugins folder
   
3. **Restart EDMC**
   - Close and reopen EDMC
   - The plugin should now appear in the Plugins tab

### Step 3: Configure VKB-Link

VKB-Link must be configured to listen for TCP connections from EDMC.

1. **Locate the VKB-Link configuration file:**
   - Windows: `C:\Users\<YourUsername>\AppData\Roaming\VKB\VKB-Link\vkb-link.ini`
   - Or check your VKB-Link installation folder

2. **Edit the `vkb-link.ini` file:**
   
   Find or add the `[TCP]` section:
   ```ini
   [TCP]
   Adress=127.0.0.1
   Port=50995
   ```
   
   **Note:** The spelling "Adress" (not "Address") is intentional - this is how VKB-Link expects it.

3. **Save the file and restart VKB-Link**

### Step 4: Configure the Plugin

1. **Open EDMC Settings:**
   - File > Settings > Plugins tab

2. **Find the VKB Connector section:**
   - You should see settings for VKB Connector

3. **Configure connection settings:**
   - **VKB Host:** `127.0.0.1` (default, uses local VKB-Link)
   - **VKB Port:** `50995` (default, must match VKB-Link configuration)
   - **Enabled:** Check this box to enable the plugin
   - **Debug:** Enable for troubleshooting (shows detailed logs)

4. **Click OK to save settings**

## Verifying Installation

### Check Plugin Status

1. Start Elite Dangerous and EDMC
2. In EDMC's main window, check for VKB Connector status
3. Look for connection messages in the EDMC log (File > Settings > Advanced > Show Log)

### Test Connection

You should see messages like:
```
INFO: VKBConnector: Connected to VKB-Link at 127.0.0.1:50995
INFO: VKBConnector: Sending shift state update
```

If you see connection errors:
- Verify VKB-Link is running
- Check the port configuration matches in both VKB-Link and EDMC
- Check Windows Firewall isn't blocking the connection

## Creating Your First Rule

The plugin uses **rules** to control when shift layers are activated. Rules are stored in a `rules.json` file.

### Option 1: Use the Rule Editor (Recommended)

1. **Open the Rule Editor:**
   - In EDMC: File > Settings > Plugins
   - Find VKB Connector section
   - Click **Open Rules Editor** button

2. **Create a simple rule:**
   - Click **New Rule**
   - Title: "Landing Gear Down"
   - In "When" section, click "Add condition"
     - Signal: "Docking: Landing gear"
     - Operator: "= Equals"
     - Value: "Deployed"
   - In "Then" section, click "Add action"
     - Action: `vkb_set_shift`
     - Check: `Shift1`
   - In "Else" section, click "Add action"
     - Action: `vkb_clear_shift`
     - Check: `Shift1`
   - Click **Save**

3. **Test the rule:**
   - Launch Elite Dangerous
   - Deploy your landing gear (L key by default)
   - Shift1 should now be activated on your VKB device
   - Retract landing gear - Shift1 should deactivate

### Option 2: Manual JSON Editing

1. **Locate the rules file:**
   - Default location: `<EDMC plugins folder>/EDMCVKBConnector/rules.json`
   - Or set a custom path in plugin settings

2. **Create `rules.json`:**
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
         ],
         "any": []
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

3. **Restart EDMC** to load the new rules

## Next Steps

Now that the plugin is installed and working:

1. **Read the [Rule Editor Guide](docs/RULE_EDITOR_GUIDE.md)** to learn how to create complex rules
2. **Check the [Signals Reference](docs/SIGNALS_REFERENCE.md)** for a complete list of available signals
3. **Review example rules** in `rules.json.example`
4. **Configure your VKB profiles** to use the shift layers being controlled by the plugin

## Troubleshooting

### Plugin Not Appearing in EDMC

- Check that you copied the entire plugin folder, not just individual files
- Verify the folder name is exactly `EDMCVKBConnector`
- Check EDMC's log for error messages
- Ensure you're using EDMC 5.0 or higher

### Cannot Connect to VKB-Link

- Verify VKB-Link is running
- Check the `vkb-link.ini` file has correct TCP settings
- Try restarting VKB-Link after configuration changes
- Check Windows Firewall settings
- Verify the port is not being used by another application

### Rules Not Working

- Check the rules file syntax (use a JSON validator)
- Enable debug mode in plugin settings to see detailed logs
- Verify signal names match the catalog (case-sensitive)
- Test with a simple rule first before adding complexity
- Check EDMC log for rule evaluation messages

### Shift Layers Not Changing on Device

- Verify your VKB device firmware supports shift layers
- Check VKB-Link is properly connected to your device
- Use VKBDevCfg to verify the device responds to shift commands
- Ensure your VKB profile is configured to use the shift layers
- Check that shift tokens match your device configuration (Shift1, Shift2, Subshift1-7)

### Getting Debug Information

1. Enable debug mode in plugin settings
2. Restart EDMC
3. Perform the action that should trigger a rule
4. Open EDMC log (File > Settings > Advanced > Show Log)
5. Look for messages starting with "VKBConnector"

## Support

For help and support:

- **Documentation:** See the [docs](docs/) folder for detailed guides
- **Issues:** Report bugs on [GitHub Issues](https://github.com/Audumla/EDMCVKBConnector/issues)
- **Questions:** Check existing issues or create a new discussion

## Uninstallation

To remove the plugin:

1. Close EDMC
2. Navigate to EDMC's plugins folder
3. Delete the `EDMCVKBConnector` folder
4. Restart EDMC

The plugin does not modify Elite Dangerous or your VKB device settings.
