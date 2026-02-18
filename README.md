# EDMCVKBConnector

EDMC plugin that turns Elite Dangerous state into VKB-Link `VKBShiftBitmap` actions using rule-based automation.

## Quick Start

### 1. Install
1. Close EDMC.
2. Download the latest plugin release ZIP.
3. Extract the `EDMCVKBConnector` folder into your EDMC `plugins` directory.
4. Start EDMC.

### 2. Connect to VKB-Link
1. Open `File -> Settings -> Plugins`.
2. Select **VKB Connector**.
3. Set `Host` and `Port` to match your VKB-Link TCP settings.

Example VKB-Link config:

```ini
[TCP]
Adress=127.0.0.1
Port=50995
```

### 3. Add Your First Rule
1. In **VKB Connector**, open the **Rules** section.
2. Click **New Rule**.
3. Add a condition and `then` action.
4. Save and verify the rule is enabled.

Rules are edge-triggered:
- `then` runs when condition changes from false to true.
- `else` runs when condition changes from true to false.

## Documentation

- `docs/RULE_EDITOR_TUTORIAL.md`: full step-by-step tutorial for the built-in rule editor.
- `docs/RULES_GUIDE.md`: rule format reference (conditions, operators, actions, validation).
- `docs/SIGNALS_REFERENCE.md`: complete signal catalog with source and trigger mapping.
- `docs/EDMC_EVENTS_CATALOG.md`: raw EDMC/Journal event reference and status flags.
- `docs/DEVELOPMENT.md`: contributor workflow, runtime architecture, and test commands.
