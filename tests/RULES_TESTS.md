# Comprehensive Rules Engine Tests - Documentation

## Overview

A complete test suite with **comprehensive file-backed rules tests** covering:
- Single conditions (flags, GuiFocus, field data)
- Multiple conditions with AND/OR logic
- Multiple state changes (set/clear shifts)
- EDMC-like journal, status/dashboard, and CAPI payloads loaded from fixture files
- Complex real-world scenarios (combat, exploration, emergencies)
- Boundary and transition semantics (`gte`/`lte`, `changed_to_true`, `changed_to`)

**File**: `tests/test_rules_comprehensive.py`  
**Total Tests**: see `test_rules_comprehensive.py`  
**Execution Time**: ~0.5 seconds  
**Status**: ✅ All passing

---

## Test Categories

### 1. Single Condition Tests (3 tests)

These verify that rules can match on individual conditions.

#### `test_rules_single_flag_condition`
- Tests: Flag-based rule with single condition
- Scenario: Hardpoints deployed (flag bit 6)
- Validates: `all_of` flag matching

#### `test_rules_single_gui_focus_condition`
- Tests: GuiFocus-based rule
- Scenario: Galaxy Map opened (GuiFocus = 6)
- Validates: Named GuiFocus matching

#### `test_rules_field_condition`
- Tests: Event field-based rule
- Scenario: Location event with "Empire" in system name
- Validates: Field string containment matching

---

### 2. Multiple Conditions Tests (3 tests)

These test AND/OR logic for combining conditions.

#### `test_rules_multiple_conditions_all`
- Tests: AND logic with multiple blocks (`all`)
- Conditions:
  - Hardpoints deployed AND Shields up
  - NOT on foot
- Validates: All conditions must match for rule

#### `test_rules_multiple_conditions_any`
- Tests: OR logic with `any` blocks
- Conditions:
  - In danger OR Being interdicted OR Low health
- Validates: Any ONE condition triggers rule

#### `test_rules_mixed_conditions`
- Tests: Combining flags, flags2, and GuiFocus
- Conditions:
  - Docked
  - Internal panel OR Station services open
  - Not on foot
- Validates: Mixed condition types work together

---

### 3. Multiple State Setting Tests (2 tests)

These test setting and clearing multiple shift states in one rule.

#### `test_rules_set_multiple_shifts`
- Tests: Setting multiple shifts simultaneously
- Action: `vkb_set_shift: ["Shift1", "Shift2", "Shift3"]`
- Scenario: Entering supercruise
- Validates: Multiple shifts can be set in single `then` block

#### `test_rules_set_and_clear_shifts`
- Tests: Both set and clear in same rule
- Actions:
  - **Then** (hardpoints deployed): Set Shift1, Clear Shift2+3
  - **Else** (hardpoints stowed): Set Shift2, Clear Shift1
- Validates: `then` and `else` blocks with multiple actions

---

### 4. Journal Event Tests (6 tests)

These test rules triggered by game journal events.

#### `test_rules_fsd_jump_event`
- Event: `FSDJump`
- Condition: Jump distance > 5 ly
- Action: Set Shift1
- Validates: Field comparison operators (gt)

#### `test_rules_docked_event`
- Event: `Docked`
- Condition: Docking at station/outpost/mega ship
- Action: Set Shift2
- Validates: Field `in` list operator

#### `test_rules_undocked_event`
- Event: `Undocked`
- Action: Clear Shift2
- Validates: Simple event-triggered rules

#### `test_rules_launch_fighter_event`
- Event: `LaunchFighter`
- Condition: Loadout contains "pulse_laser"
- Action: Set Shift3
- Validates: Array field containment

#### `test_rules_dock_fighter_event`
- Event: `DockFighter`
- Action: Clear Shift3
- Validates: Event-only rules (no conditions)

#### `test_rules_location_event`
- Event: `Location`
- Condition: Star system equals "Colonia"
- Action: Set Shift4
- Validates: Field exact match operator

---

### 5. Dashboard Event Tests (4 tests)

These test rules based on dashboard/status flags.

#### `test_rules_dashboard_weapon_deployment`
- Conditions:
  - Hardpoints deployed AND Cargo scoop deployed
- Action: Set Shift1+2
- Validates: Multiple flag `all_of` conditions

#### `test_rules_dashboard_flight_states`
- Conditions (any):
  - In supercruise OR In wing OR Flight assist off
- Tests multiple OR conditions with different outcomes
- Validates: Flight mode detection

#### `test_rules_dashboard_vehicle_states`
- Conditions (any):
  - In SRV OR In fighter
- Tests both specific vehicle states
- Validates: Vehicle mode detection

#### `test_rules_dashboard_on_foot_states`
- Conditions:
  - On foot AND (in station OR on planet)
- Tests Odyssey-specific states
- Validates: Flags2 (on-foot) conditions

---

### 6. Complex Multi-Condition Rules (3 tests)

These test realistic, complex scenarios with many conditions.

#### `test_rules_combat_context`
- Scenario: Combat readiness
- Conditions:
  - Hardpoints deployed AND Shields up
  - In main ship OR In fighter
  - NOT on foot
- Actions:
  - **Then**: Set Shift1+2+3, log "Combat ready"
  - **Else**: Clear Shift1+2+3, log "Combat disengaged"
- Validates: Real-world combat mode detection

#### `test_rules_exploration_mode`
- Scenario: Active scanning
- Conditions (any):
  - FSS scanning OR SAA scanning
- Action: Set Shift4, log "Scanning active"
- Validates: GuiFocus-based UI state detection
- Tests: Both FSS and SAA options separately

#### `test_rules_emergency_survival`
- Scenario: Emergency protocol
- Conditions (any):
  - (In danger AND being interdicted) OR (Low health OR Low oxygen)
- Action: Set Shift5+6, log "Emergency mode"
- Validates: Complex OR with nested AND
- Tests: Multiple triggers for emergency state

---

### 7. Event/Source Filtering Tests (2 tests)

These test rule filtering by event type and source.

#### `test_rules_event_type_filtering`
- Tests: Event list filtering
- Conditions:
  - `event: ["FSDJump", "SupercruiseEntry", "StartJump"]`
- Tests: FSDJump matches, SupercruiseEntry matches, Docked doesn't match
- Validates: Event list filtering logic

#### `test_rules_source_filtering`
- Tests: Source filtering
- Condition: `source: "journal"`
- Tests: Journal matches, dashboard doesn't match
- Validates: Source filtering logic

---

## Coverage of EDMC Event Types

### Journal Events Tested
| Event | Condition Type | Test |
|-------|---|---|
| FSDJump | Field operator (gt) | `test_rules_fsd_jump_event` |
| Docked | Field operator (in) | `test_rules_docked_event` |
| Undocked | Simple trigger | `test_rules_undocked_event` |
| Location | Field operator (equals) | `test_rules_location_event` |
| LaunchFighter | Array containment | `test_rules_launch_fighter_event` |
| DockFighter | Simple trigger | `test_rules_dock_fighter_event` |

### Dashboard Conditions Tested
| Flags | Test | Scenario |
|-------|------|----------|
| FlagsHardpointsDeployed | Multiple tests | Combat readiness |
| FlagsShieldsUp | combat_context | Combat readiness |
| FlagsSupercruise | flight_states | Flight mode |
| FlagsInWing | flight_states | Flight mode |
| FlagsFlightAssistOff | flight_states | Flight mode |
| FlagsInSRV | vehicle_states | Vehicle mode |
| FlagsInFighter | vehicle/combat tests | Vehicle/combat mode |
| FlagsCargoScoopDeployed | weapon_deployment | Cargo operations |
| FlagsIsInDanger | emergency | Emergency |
| FlagsBeingInterdicted | emergency | Emergency |
| FlagsInMainShip | combat_context | Combat mode |

| Flags2 | Test | Scenario |
|--------|------|----------|
| Flags2OnFoot | on_foot_states | Odyssey mode |
| Flags2OnFootInStation | on_foot_states | Station exploration |
| Flags2OnFootOnPlanet | on_foot_states | Planetary exploration |
| Flags2LowHealth | emergency | Emergency |
| Flags2LowOxygen | emergency | Emergency |

| GuiFocus | Test | Scenario |
|----------|------|----------|
| GuiFocusGalaxyMap | single_gui_condition | Navigation |
| GuiFocusFSS | exploration_mode | Scanning |
| GuiFocusSAA | exploration_mode | Scanning |
| GuiFocusInternalPanel | mixed_conditions | Station interaction |
| GuiFocusStationServices | mixed_conditions | Station services |

---

## Condition Types Tested

### Flag Conditions
- `all_of` - All flags must be set
- `any_of` - At least one flag must be set
- `none_of` - None of the flags must be set
- `equals` - Specific flag values

### GuiFocus Conditions
- `equals` - Specific GUI focus value (by name)
- `in` - Multiple possible GUI focus values

### Field Conditions
- `equals` - Exact match
- `contains` - String/array containment
- `in` - Value in list
- `gt`/`gte`/`lt`/`lte` - Numeric comparisons
- `exists` - Field presence

### Logical Operators
- `all` blocks - AND logic (all must match)
- `any` blocks - OR logic (any one matches)
- `then` / `else` - Conditional actions

---

## State Changes Tested

### Single Shift Changes
- Set individual shift (e.g., Shift1)
- Clear individual shift

### Multiple Shifts
- Set multiple shifts: `["Shift1", "Shift2", "Shift3"]`
- Clear multiple shifts: `["Shift2", "Shift3"]`
- Combined set and clear in single rule

### Shift Ranges
- Shifts 0-7 (8 possible shifts)
- Subshifts (if supported by protocol)

---

## Test Executio n & Integration

### Run Just Rules Tests
```powershell
test.bat rules
```

### Run with Full Dev Suite
```powershell
test.bat dev
```
Rules tests run as part of:
1. Unit tests (5)
2. Integration tests (6)
3. VKB socket tests (8)
4. **Rules tests (23)** ← NEW
5. Total: 42+ tests in ~20 seconds

### Direct Execution
```powershell
cd tests
python test_rules_comprehensive.py
```

---

## Test Data Structure

### Input: Rule Definition
```json
{
  "id": "example_rule",
  "enabled": true,
  "when": {
    "source": "dashboard",
    "all": [
      {"flags": {"all_of": ["FlagsHardpointsDeployed"]}},
      {"flags2": {"none_of": ["Flags2OnFoot"]}}
    ]
  },
  "then": {"vkb_set_shift": ["Shift1"]},
  "else": {"vkb_clear_shift": ["Shift1"]}
}
```

### Inputs: Dashboard Data
```python
{
  "Flags": 0b....,          # 32-bit flags
  "Flags2": 0b....,         # 16-bit on-foot flags
  "GuiFocus": 1-10,         # Current UI panel
  "event": "Status"         # Event type
}
```

### Input: Event Data
```python
{
  "event": "FSDJump",
  "StarSystem": "Beagle Point",
  "JumpDist": 45.3,
  "SystemAddress": 12345
}
```

### Output: RuleMatchResult
- `RuleMatchResult.MATCH` - Rule conditions met
- `RuleMatchResult.NO_MATCH` - Rule conditions not met
- `RuleMatchResult.INDETERMINATE` - Missing required data

---

## Edge Cases Covered

✅ Multiple flags of same type  
✅ Mixed flag/flags2/GuiFocus conditions  
✅ Multiple OR conditions  
✅ Nested AND within OR  
✅ Event with no conditions  
✅ GuiFocus by name vs. by value  
✅ Field operators (gt, in, contains)  
✅ Both set and clear in single rule  
✅ Set multiple shifts simultaneously  
✅ Event filtering (list vs. single)  
✅ Source filtering (journal vs. dashboard)  

---

## Real-World Scenarios Modeled

### Combat Mode
- "When hardpoints deployed, shields up, and in main ship"
- Enables combat profiles (Shift1+2+3)

### Exploration Mode
- "When FSS or SAA is open"
- Enables scanning profile (Shift4)

### Vehicle Modes
- SRV detection (Shift6)
- Fighter detection (Shift6)
- On-foot modes (Shift7)

### Emergency Protocol
- "When under attack or low on health"
- Enables emergency profile (Shift5+6)

### Station Interaction
- "When docked, internal panel open, not on foot"
- Enables station profile (Shift6)

---

## Performance

- **Execution Time**: ~0.5 seconds for all 23 tests
- **Memory Usage**: Minimal (no persistent connections)
- **Scalability**: Tests run in parallel-safe manner

---

## Future Expansion

Potential additional tests for:
- Rules with event data change detection
- Time-based delays between actions
- Custom field types
- Multi-rule interactions
- Rules ordering/priority
- Performance benchmarks for large rule sets
- Real-time event streaming
- Event data persistence across rules

---

## Summary

✅ **23 comprehensive rules tests**  
✅ **All 4 test categories covered** (single, multiple, journal, dashboard)  
✅ **All major EDMC event types tested** (6+ journal, 3+ dashboard state types)  
✅ **Real-world scenarios modeled** (combat, exploration, emergency)  
✅ **Both AND/OR logic tested** (all/any blocks)  
✅ **Multiple state changes** (set/clear multiple shifts)  
✅ **Integrated into test suite** (test.bat, dev_test.py)  
✅ **All passing** (~0.5 seconds execution)  

The rules engine now has production-ready test coverage for complex, real-world use cases!
