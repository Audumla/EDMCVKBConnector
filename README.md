# EDMCVKBConnector

EDMC plugin that converts Elite Dangerous state into VKB-Link `VKBShiftBitmap` actions using catalog-driven rules.

## Install
1. Close EDMC.
2. Download the latest plugin release ZIP.
3. Extract the `EDMCVKBConnector` folder into your EDMC `plugins` directory.
4. Start EDMC and open `File -> Settings -> Plugins`.

## Required Configuration
In the **VKB Connector** plugin settings:
- Set `Host` and `Port` to match VKB-Link TCP settings.
- Create or edit automation rules in the built-in **Rules** section.
- If needed, set a custom `rules_path` (otherwise `<plugin_dir>/rules.json` is used).

VKB-Link TCP settings must match the plugin target:

```ini
[TCP]
Adress=127.0.0.1
Port=50995
```

## Rule Setup
- Open `File -> Settings -> Plugins -> VKB Connector`.
- Use **New Rule** / **Edit** to manage rule logic.
- Rules are edge-triggered (`then` on false->true, `else` on true->false).

Rule authoring guide: `docs/RULES_GUIDE.md`  
Signal reference: `docs/SIGNALS_REFERENCE.md`

## Development Docs
Developer workflows are documented in `docs/DEVELOPMENT.md`.
