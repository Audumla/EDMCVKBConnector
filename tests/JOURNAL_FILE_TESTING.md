# Journal File Testing

## Overview

The journal file testing feature validates the plugin's behavior with real Elite Dangerous journal events. This ensures the plugin correctly processes authentic game data and communicates with VKB hardware as expected.

## Test Journal File

**Location**: `tests/fixtures/Journal.2026-02-13T120000.01.log`

The test journal file contains 34 authentic Elite Dangerous events covering a complete gameplay session:

### Gameplay Sequence

1. **Game Startup**
   - `Fileheader`: Game version and build information
   - `LoadGame`: Commander "Test Commander" in ship "Wanderer" (Cobra Mk III)
   - `Location`: Starting location in Shinrarta Dezhra system

2. **Hyperspace Travel**
   - `StartJump`: Initiating hyperspace jump
   - `FSDJump`: Jump to Deciat system (10.503 LY, 0.826552t fuel used)
   - `SupercruiseEntry`: Enter supercruise mode

3. **Station Docking**
   - `SupercruiseExit`: Exit supercruise
   - `DockingRequested`: Request docking permission
   - `DockingGranted`: Permission granted (pad 10)
   - `Docked`: Docked at Darnielle's Progress (Coriolis station)

4. **Station Services**
   - Multiple `Status` events with `GuiFocus: 5` (station services menu active)

5. **Undocking & Combat Readiness**
   - `Undocked`: Leave station
   - `Status` events showing hardpoints deployed, cargo scoop deployed, shields active

6. **Fighter Operations**
   - `LaunchFighter`: Deploy fighter with loadout "fighter_loadout_1"
   - `DockFighter`: Recall fighter to hangar

7. **Exploration Activities**
   - `FSSDiscoveryScan`: Full Spectrum System scan (bodies found: 12)
   - `SAAScanComplete`: Detailed surface scan of planet "Deciat 5 a"

8. **Continuous Status Updates**
   - 19 `Status` events throughout, tracking ship state changes:
     - Flags: Ship state (docked, supercruise, hardpoints, etc.)
     - GuiFocus: Active UI panel (0=none, 5=station services, 7=FSS, 8=SAA)

### Key Event Types in Fixture

| Event Type | Count | Description |
|------------|-------|-------------|
| Status | 19 | Ship status/dashboard updates |
| FSDJump | 1 | Hyperspace jump |
| Docked/Undocked | 1 each | Station docking operations |
| LaunchFighter/DockFighter | 1 each | Fighter bay operations |
| FSSDiscoveryScan | 1 | System scanning |
| SAAScanComplete | 1 | Surface scanning |
| DockingRequested/Granted | 1 each | Docking sequence |
| SupercruiseEntry/Exit | 1 each | Supercruise transitions |
| StartJump | 1 | Jump initiation |
| Fileheader, LoadGame, Location | 1 each | Session startup |

## Test Suite

**File**: `tests/test_journal_files.py`

### Test 1: Journal File Parsing

Validates that journal files can be parsed correctly:
- Reads JSON Lines format
- Extracts event dictionaries
- Verifies expected event types are present
- Reports event counts and types

```python
events = parse_journal_file(journal_path)
# Result: 34 events parsed with 16 different event types
```

### Test 2: Plugin Processes Journal Events

Tests that the plugin correctly processes journal events and forwards them to VKB:
- Initializes EventHandler with mock VKB server
- Processes all relevant events from journal
- Validates VKB messages are sent
- Counts different event categories (Status, FSDJump, Docked)

**Results**:
- Processed 5 journal events (FSDJump, Docked, Undocked, LaunchFighter, DockFighter)
- Processed 19 Status events
- Server received 7 VKB messages (191 total bytes)

**Sample VKB Messages**:
```
[1] a50d000400000000  # Initial state
[2] 5374617475730a    # "Status\n"
[3] 5374617475730a    # "Status\n"
[4] 4653444a756d700a  # "FSDJump\n"
[5] 5374617475730a    # "Status\n"
```

### Test 3: Specific Journal Scenarios

Tests individual gameplay scenarios with detailed validation:

**Scenario 1: FSD Jump**
- Event: FSDJump to Deciat system
- Distance: 10.503 ly
- Result: 1 VKB message generated

**Scenario 2: Docking**
- Event: Docked at Darnielle's Progress (Coriolis station)
- Result: 1 VKB message generated

**Scenario 3: Fighter Operations**
- Events: LaunchFighter, DockFighter
- Result: 1 message per event (2 total)

**Scenario 4: Dashboard Status Changes**
- Events: 5 Status events with different flags
- Result: 5 VKB messages (1 per status change)

### Test 4: Journal Event Filtering

Validates that only configured events are forwarded to VKB:
- Lists all event types in journal
- Processes all events
- Verifies filtering is working (not all 34 events forwarded)
- Result: 8 VKB messages from 34 journal events

## Journal File Format

Elite Dangerous journal files use **JSON Lines** format:
- One JSON object per line
- Each line is a complete event
- UTF-8 encoding

### Example Events

**Fileheader** (startup):
```json
{"timestamp":"2026-02-13T12:00:00Z", "event":"Fileheader", "part":1, "language":"English/UK", "Odyssey":true, "gameversion":"4.0.0.1550", "build":"r299346/r0 "}
```

**FSDJump** (hyperspace):
```json
{"timestamp":"2026-02-13T12:05:00Z", "event":"FSDJump", "StarSystem":"Deciat", "SystemAddress":3932277478106, "StarPos":[129.59375,-0.03125,-68.90625], "SystemAllegiance":"Independent", "SystemEconomy":"$economy_HighTech;", "SystemGovernment":"$government_Democracy;", "SystemSecurity":"$SYSTEM_SECURITY_medium;", "Population":44000000, "JumpDist":10.503, "FuelUsed":0.826552, "FuelLevel":7.173448}
```

**Status** (dashboard):
```json
{"timestamp":"2026-02-13T12:10:30Z", "event":"Status", "Flags":16777216, "Pips":[4,4,4], "FireGroup":0, "GuiFocus":0, "Fuel":{"FuelMain":8.0,"FuelReservoir":0.37}, "Cargo":0.0}
```

**Status Flags** (bitfield encoding ship state):
- `16777216`: Normal flight
- `83886080`: In hyperspace
- `17301504`: Docked at station
- `150994944`: Fighter deployed
- Many other states...

**GuiFocus** (active UI panel):
- `0`: No focus
- `5`: Station services
- `7`: FSS scanner
- `8`: SAA scanner

## Running the Tests

### Run Journal Tests Only

```powershell
python tests\test_journal_files.py
```

### Run All Tests

```powershell
python tests\test_vkb_server_integration.py
python tests\test_journal_files.py
```

### Using dev_test.py

```powershell
python scripts\run_plugin_dev.py
```

## Creating Additional Journal Fixtures

To create more journal fixtures for different scenarios:

1. **Locate Real Journals**:
   - Windows: `%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous\`
   - Look for files named: `Journal.YYYY-MM-DDTHHMMSS.##.log`

2. **Extract Event Sequences**:
   - Copy relevant lines from real journal files
   - Ensure complete sequences (e.g., StartJump + FSDJump)
   - Include Status events before/after major events

3. **Anonymize Data** (optional):
   - Change commander name: `"Name": "Test Commander"`
   - Change ship name: `"ShipName": "Wanderer"`
   - Keep realistic system/station names or use test data

4. **Save to Fixtures**:
   - Location: `tests/fixtures/`
   - Naming: `Journal.YYYY-MM-DDTHHMMSS.##.log`

### Useful Event Sequences to Test

- **Combat**: Interdiction, shields down, hull damage, hardpoints
- **SRV Operations**: Touchdown, SRV deploy/dock, on-foot (Odyssey)
- **Carrier Operations**: Carrier jump, carrier services
- **Multi-crew**: CrewMemberJoins, CrewMemberRoleChange
- **Emergency**: HullDamage, FuelScoop, Repair, Reboot
- **Powerplay**: PowerplayVote, PowerplayCollect
- **Engineers**: EngineerProgress, ModuleInfo
- **Communities**: CommunityGoalJoin, CommunityGoalReward
- **Exploration**: Scan (stars/planets), FSS, SAA, CodexEntry

## Benefits

1. **Realistic Testing**: Uses actual game event data
2. **Regression Prevention**: Validates behavior doesn't break with new changes
3. **Event Coverage**: Ensures all major gameplay scenarios are handled
4. **VKB Protocol Validation**: Verifies correct messages are sent
5. **Status Flag Testing**: Validates complex bitfield decoding
6. **Documentation**: Provides examples of event structure and timing

## Integration with Mock Server

Journal tests use the enhanced MockVKBServer with query methods:

```python
# Check message counts
count = server.get_message_count()

# Inspect messages
messages = server.get_messages()
for msg in messages:
    print(f"Data: {msg['data'].hex()}")
    print(f"Address: {msg['addr']}")
    print(f"Time: {msg['timestamp']}")

# Search for specific events
fsd_msgs = server.find_messages_with_payload("FSDJump")

# Clear between scenarios
server.clear_messages()
```

See [MOCK_SERVER_QUERIES.md](MOCK_SERVER_QUERIES.md) for complete query method documentation.

## Future Enhancements

Potential improvements to journal testing:

1. **Rules Engine Testing**: Test rules.json against journal events
2. **Performance Testing**: Large journal files with 1000+ events
3. **Timing Validation**: Test rate limiting and throttling
4. **State Machine Testing**: Validate VKB shift state transitions
5. **Error Scenarios**: Malformed events, missing fields
6. **Multi-Commander**: Test with different commander profiles
7. **Beta vs Live**: Test with is_beta flag variations
