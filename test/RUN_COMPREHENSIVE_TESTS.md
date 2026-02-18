# Running Comprehensive Real Events Tests

## Quick Start

```bash
# Run all comprehensive tests with DEBUG logging (default)
pytest test/test_rules_with_real_events.py -v

# Expected: 8/8 PASSED in ~0.2 seconds
```

## What Gets Tested

Each test processes **ALL 113 Status events** from test_event_1.jsonl:

| Test | What It Validates | Events | Result |
|------|-------------------|--------|--------|
| combat_mode_rule_triggering | No action spam on state changes | 113 | 2 actions (no spam!) |
| docking_state_consistency | Stable state transitions | 113 | 0 oscillations |
| multi_condition_rule_evaluation | AND/ANY logic | 113 | All correct |
| event_processing_volume | Production load | 113 | 0.02x ratio (excellent) |
| commander_state_isolation | No crosstalk | 113 | Each isolated |
| no_action_spam_on_repeated_state | Repeated states | 113 | No duplicate actions |
| state_change_detection | Valid state sequences | 113 | 0 invalid patterns |
| rule_file_loading_and_validation | Rule files valid | N/A | 3/3 valid |

## Running Tests

### All Tests with Full Debug Logs
```bash
pytest test/test_rules_with_real_events.py -v
```

Shows:
- Rule engine logs (INFO level)
- Test output with event counts
- Action spam metrics
- State transition analysis
- False trigger detection

### Specific Test
```bash
# Test combat mode rule
pytest test/test_rules_with_real_events.py::TestRulesWithRealEvents::test_combat_mode_rule_triggering -v

# Test action spam prevention (regression test)
pytest test/test_rules_with_real_events.py::TestEdgeTriggeringBehavior::test_no_action_spam_on_repeated_state -v
```

### With Maximum Detail
```bash
pytest test/test_rules_with_real_events.py -v -s --log-cli-level=DEBUG --tb=long
```

Shows:
- Every print statement
- All debug logs
- Full stack traces on failure
- Detailed output for debugging

### Run from VSCode
1. Click Test Explorer (flask icon)
2. Click play button next to test
3. See output in Test Output panel
4. DEBUG logging enabled automatically

## Understanding the Output

### Expected Output Example
```
test_combat_mode_rule_triggering PASSED
  Status events processed: 113 (total available: 113)
  State transitions detected: ['retracted', 'deployed']
  Total actions triggered: 2
  Rule matched (True): 1 times
  Rule unmatched (False): 1 times
  Action spam check: 2 <= 3 [OK]
```

**Meaning:**
- Processed all 113 available Status events ✓
- Only 2 actions fired (one per state change) ✓
- No action spam detected ✓

### If Test Fails

Look for:
```
AssertionError: Too many actions logged: 45 (expected at most 3)
```

This means:
- Action spam is happening
- Rule is triggering repeatedly
- Edge triggering not working

## Test Data

**File:** `test/fixtures/test_event_1.jsonl`
- 277 total events
- **113 Status events** (what tests use)
- Real Elite Dangerous gameplay
- Contains state transitions (hardpoints deployed/retracted)

### How to Add More Test Data

1. Collect new .log file from EDMC
2. Parse to JSON format
3. Replace test_event_1.jsonl
4. Re-run tests automatically processes new data

## Performance

```
8 tests × 113 events each = 904 total event evaluations
Execution time: 0.19 seconds
Performance: EXCELLENT (5000+ events/second)
```

## Integration

### CI/CD Pipeline
Add to your test workflow:
```yaml
- name: Run Comprehensive Real Events Tests
  run: pytest test/test_rules_with_real_events.py -v
```

### Pre-Commit Hook
```bash
#!/bin/bash
pytest test/test_rules_with_real_events.py -q || exit 1
```

### Manual Testing
```bash
# After code changes, run comprehensive validation
pytest test/test_rules_with_real_events.py -v --tb=short
```

## Debugging Failed Tests

### Step 1: Run with verbose output
```bash
pytest test/test_rules_with_real_events.py::TestRulesWithRealEvents::test_combat_mode_rule_triggering -v -s
```

### Step 2: Check logs
```
12:24:15 [    INFO] edmcruleengine: Loaded 1 rules...
12:24:15 [    INFO] edmcruleengine: Rule 'Combat Mode...' initial (matched=False)
12:24:15 [    INFO] edmcruleengine: Rule 'Combat Mode...' activated (matched=True)
```

### Step 3: Look at action counts
```
Actions triggered: 150 (expected at most 3)
```
→ Shows action spam is happening

### Step 4: Use breakpoints
1. Click line number in VSCode
2. Right-click test → Debug Test
3. Inspect variables in Debug Console
4. Step through execution

## Key Metrics to Monitor

| Metric | Expected | Good | Warning | Problem |
|--------|----------|------|---------|---------|
| Action ratio | 0.02x | <0.1x | 0.1-1x | >1x |
| Oscillations | 0 | 0 | 0-2 | >2 |
| Invalid patterns | 0 | 0 | 0 | >0 |
| Exec time | 0.2s | <1s | 1-5s | >5s |

## Common Issues & Solutions

### Issue: Tests timeout (>5 seconds)
**Solution:** Something wrong with rule evaluation. Check rule logic.

### Issue: Action spam detected
**Solution:** Edge triggering not working. Check RuleEngine.on_notification().

### Issue: State oscillations
**Solution:** Signal derivation unstable. Check signal definitions.

### Issue: False triggers
**Solution:** Rule conditions too broad. Review when/then/else logic.

## Test Rules Used

### combat_mode_rule.json
```
When: hardpoints == deployed
Then: Send Shift1
Else: Clear Shift1
```

Tests if action only fires on state change.

### docking_state_rules.json
```
When: docking_state == docked → Send Shift2
When: docking_state == in_space → Send Shift3
```

Tests state consistency and transitions.

### multi_condition_rules.json
```
When: hardpoints == deployed (AND conditions)
When: hardpoints == deployed (ANY conditions)
```

Tests complex condition logic.

## Real Event Simulation

Tests use actual game events with:
- Real HUD flag patterns
- Realistic state transitions
- Production load (113 events)
- Multi-second gameplay

This catches bugs that unit tests miss!

## Success Criteria

All tests PASSING means:
✅ No action spam in production
✅ Rules trigger only on state changes
✅ State transitions are stable
✅ Complex conditions work correctly
✅ Commander isolation prevents crosstalk
✅ Production load is sustainable
✅ No false triggers across entire dataset

Run tests regularly to maintain quality!
