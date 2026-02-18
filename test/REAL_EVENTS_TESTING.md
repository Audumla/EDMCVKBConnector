# Real Events Testing Guide

## Overview

This document describes the comprehensive test suite for rules triggering behavior using real Elite Dangerous game events from `test_event_1.jsonl`.

The new test suite (`test_rules_with_real_events.py`) simulates real game behavior to catch production issues where rules trigger incorrectly or spam actions.

## Problem Statement

Previously, rules were occasionally triggering when they shouldn't, and the action spam issue where the same rule would fire repeatedly even when game state hadn't changed was difficult to debug. This test suite addresses both issues by:

1. **Using real game event data** - Events extracted from actual gameplay in Elite Dangerous
2. **Simulating production conditions** - Processing Status events (~1Hz) like the real system does
3. **Validating edge triggering** - Ensuring rules only trigger on state changes, not repeated states
4. **Testing consistency** - Verifying rules behave the same way across multiple runs

## Test Structure

### Rule Files (Fixtures)

Rule files are stored in `test/fixtures/` and represent different rule categories:

#### 1. `combat_mode_rule.json`
Basic rule demonstrating the core issue: when hardpoints are deployed, send Shift1. Otherwise, clear Shift1.

```json
{
  "title": "Combat Mode Shift Control",
  "when": {
    "all": [{"signal": "hardpoints", "op": "eq", "value": "deployed"}]
  },
  "then": [{"vkb_set_shift": ["Shift1"]}],
  "else": [{"vkb_clear_shift": ["Shift1"]}]
}
```

**Key test**: Verify that when hardpoints stay in the same state across multiple Status events, only ONE action fires (not multiple).

#### 2. `docking_state_rules.json`
Tests state transitions with two complementary rules:
- Shift2 when docked
- Shift3 when in space

**Key test**: Verify state consistency and no rapid oscillations.

#### 3. `multi_condition_rules.json`
Tests rule evaluation with:
- AND conditions (all must be true)
- ANY conditions (at least one must be true)

**Key test**: Verify complex condition logic stays consistent.

## Test Classes

### TestRulesWithRealEvents

Main test class for comprehensive rule testing with real events.

#### test_combat_mode_rule_triggering
- **Purpose**: Verify the core issue is fixed (no action spam)
- **Process**:
  1. Load combat mode rule
  2. Feed all 277 Status events from test_event_1.jsonl
  3. Track every action triggered
  4. Verify actions only trigger on state changes
- **Expected**: Action count ≤ number of state transitions + 1
- **Regression Test**: This catches the production bug

#### test_docking_state_consistency
- **Purpose**: Verify docking state rules don't oscillate
- **Process**:
  1. Load docking state rules
  2. Feed Status events
  3. Track state transitions
  4. Count oscillation patterns (True->False->True)
- **Expected**: ≤ 2 oscillations (realistic game behavior)

#### test_multi_condition_rule_evaluation
- **Purpose**: Verify AND/ANY conditions work correctly
- **Process**:
  1. Load complex rules with multiple conditions
  2. Feed Status events
  3. Track rule matches
  4. Verify rules match when expected
- **Expected**: Both rule types evaluate correctly

#### test_event_processing_volume
- **Purpose**: Verify engine handles all events without errors
- **Process**:
  1. Load rules
  2. Process all 277 Status events
  3. Count actions generated
- **Expected**: All events processed, >0 actions generated

#### test_rule_file_loading_and_validation
- **Purpose**: Verify all rule fixture files are valid
- **Process**:
  1. Load all three fixture files
  2. Validate structure
  3. Check required fields
- **Expected**: All files load successfully

#### test_commander_state_isolation
- **Purpose**: Verify different commanders have independent state
- **Process**:
  1. Load rules
  2. Send alternating events to CommanderA and CommanderB
  3. Track actions per commander
- **Expected**: Both commanders log actions independently

### TestEdgeTriggeringBehavior

Focused tests for edge triggering (preventing action spam).

#### test_no_action_spam_on_repeated_state
- **Purpose**: Directly test the production bug fix
- **Process**:
  1. Find a sequence of 3+ events with same hardpoints state
  2. Feed all to engine
  3. Count actions
- **Expected**: ≤ 1 action (initial trigger only)
- **Critical**: This is the regression test for the reported issue

#### test_state_change_detection
- **Purpose**: Verify state changes are detected correctly
- **Process**:
  1. Feed first 20 Status events
  2. Track state transitions
  3. Verify reasonable state sequences
- **Expected**: No invalid state patterns

## Running the Tests

### Run only real event tests:
```bash
pytest test/test_rules_with_real_events.py -v
```

### Run specific test:
```bash
pytest test/test_rules_with_real_events.py::TestRulesWithRealEvents::test_combat_mode_rule_triggering -v
```

### Run with detailed output:
```bash
pytest test/test_rules_with_real_events.py -v -s
```

### Run full test suite (includes regression tests):
```bash
pytest test/ -v
```

## Test Data

### test_event_1.jsonl
Real Elite Dangerous game events capturing:
- 277 Status events (dashboard updates, ~1 second intervals)
- Status event details:
  - Flags (32-bit field with ship state)
  - Flags2 (32-bit field with Odyssey on-foot state)
  - Pips (power distribution)
  - GuiFocus (current HUD focus)
  - Fuel, Cargo, LegalState
  - FireGroup, Hardpoints state (Bit 6), etc.

### Event Processing
- Status events come from the "dashboard" source (Status.json in EDMC)
- Processed sequentially as they occur in real gameplay
- Simulate ~1Hz update rate of real HUD
- Test harness extracts relevant flags for signal derivation

## Key Signals Tested

- **hardpoints**: deployed/retracted (Bit 6 of Flags)
- **docking_state**: docked/landed/in_space
- **gui_focus**: Various HUD screens
- **supercruise_status**: In supercruise or normal space
- Many others available in signals_catalog.json

## Detecting the Bug

The production bug manifests as:
1. Rule triggers on initial state (expected)
2. Rule triggers AGAIN on next Status event with same state (BUG)
3. Repeats every Status event (~1Hz) while state unchanged
4. Results in 60+ duplicate actions per minute per rule

### How Tests Catch It:
```
Expected: 1 action (state change event)
Actual:   30 actions (repeated firing)
Test fails with: "Too many actions logged: 30 (expected at most 1)"
```

## Rule File Maintenance

When adding new test cases:

1. **Create fixture file** in `test/fixtures/`:
   ```bash
   # Name should describe what's being tested
   test/fixtures/my_feature_rule.json
   ```

2. **Use valid signals** - Check `signals_catalog.json` for available signals

3. **Add test method** to `TestRulesWithRealEvents`:
   ```python
   def test_my_feature(self, test_events, catalog):
       rules_path = Path(__file__).parent / "fixtures" / "my_feature_rule.json"
       rules = load_rules_file(rules_path)
       # ... test logic
   ```

4. **Verify with full suite**:
   ```bash
   pytest test/test_rules_with_real_events.py -v
   ```

## Expected Test Results

All tests should pass with output similar to:
```
test/test_rules_with_real_events.py::TestRulesWithRealEvents::test_combat_mode_rule_triggering PASSED
  Status events processed: 32
  State transitions: ['retracted', 'deployed', 'retracted', 'deployed']
  Actions triggered: 5
  Rule matched: 2 times
  Rule unmatched: 3 times

test/test_rules_with_real_events.py::TestEdgeTriggeringBehavior::test_no_action_spam_on_repeated_state PASSED
  Repeated same state 3 times
  Actions triggered: 1 (expected: 1)
```

## Debugging Failed Tests

If a test fails:

1. **Check the log output** - Look for ERROR or WARNING in captured logs
2. **Examine action_log** - Print the action log to see what triggered
3. **Verify rule file** - Ensure rule signals exist in catalog
4. **Check test_event_1.jsonl** - Ensure events have expected flags
5. **Run single test** - Isolate the failure with -v -s flags

### Example Debug
```bash
pytest test/test_rules_with_real_events.py::TestRulesWithRealEvents::test_combat_mode_rule_triggering -v -s
# Look for ERROR lines in output
# Check if hardpoints flag is actually changing in test data
```

## Integration with CI/CD

These tests should run as part of the test suite:
```bash
# CI/CD command
python -m pytest test/ -v --tb=short
```

All 285+ tests should pass including:
- 8 new real event tests
- 277 existing unit/integration tests
- Regression tests for bug fixes

## Related Files

- **test_rules_with_real_events.py** - All test implementations
- **test/fixtures/combat_mode_rule.json** - Core rule test case
- **test/fixtures/docking_state_rules.json** - State transition test
- **test/fixtures/multi_condition_rules.json** - Complex logic test
- **test/fixtures/test_event_1.jsonl** - Real game events (277 lines)
- **signals_catalog.json** - Signal definitions (in src root)

## Summary

This test suite provides:
✅ Regression test for action spam bug
✅ Real game event simulation
✅ Edge triggering validation
✅ State consistency verification
✅ Commander isolation testing
✅ Complex rule logic validation
✅ Volume/stress testing

The tests ensure that rules work correctly in production when fed real game events over extended periods.
