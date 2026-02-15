# Multi-Source Signal Mapping Implementation Summary

## What Was Done

### 1. Created Architecture Documentation
**File**: [docs/MULTI_SOURCE_SIGNALS.md](docs/MULTI_SOURCE_SIGNALS.md)

Comprehensive documentation explaining:
- The four EDMC data sources (dashboard, journal, state, CAPI)
- Three signal derivation patterns (single-source, multi-source, hybrid)
- Source mapping structure specification
- Derivation operators (core + event-based)
- Rule generation using source mappings
- Migration guide for updating existing signals
- Best practices and examples

### 2. Updated Signal Catalog
**File**: `signals_catalog_v2.json` (copied from provided catalog)

Added `sources` mappings to key signals:

#### `docking_state` - Hybrid Dashboard + Journal Signal
```json
{
  "sources": {
    "primary": ["dashboard", "journal"],
    "dashboard": {
      "method": "flag",
      "flags": {
        "docked": {"bitfield": "ship_flags", "bit": 0},
        "landed": {"bitfield": "ship_flags", "bit": 1}
      },
      "description": "Real-time docked/landed state"
    },
    "journal": {
      "method": "compound",
      "events": [
        {"event": "Docked", "maps_to": "just_docked", "within_seconds": 3},
        {"event": "Undocked", "maps_to": "just_undocked", "within_seconds": 3}
      ],
      "description": "Recent docking/landing events for edge detection"
    }
  }
}
```

Shows how a signal combines:
- Real-time dashboard flags for persistent state
- Recent journal events for edge detection (just docked, just landed)

#### `system_name` - State-Based with Journal Fallback
```json
{
  "sources": {
    "primary": "state",
    "state": {
      "method": "path",
      "path":  "state.StarSystem",
      "description": "Persistent system name from LoadGame/FSDJump/Location events"
    },
    "journal": {
      "method": "event_field",
      "events": ["FSDJump", "Location", "CarrierJump"],
      "field": "StarSystem",
      "description": "System name from jump/location events"
    }
  }
}
```

Shows:
- Primary source is accumulated state (persists across sessions)
- Journal source for extracting system name from jump events

#### `flag_docked` - Dashboard Flag with Journal Alternative
```json
{
  "sources": {
    "primary": "dashboard",
    "dashboard": {
      "method": "flag",
      "bitfield": "ship_flags",
      "bit": 0,
      "description": "Real-time docked state from Status.json"
    },
    "journal": {
      "method": "recent_event",
      "event_name": "Docked",
      "within_seconds": 5,
      "description": "Alternative: just docked event trigger"
    }
  }
}
```

Shows:
- Simple boolean flag with dashboard as primary
- Journal event as alternative trigger mechanism

#### `gui_focus` - Dashboard Value Mapping
```json
{
  "sources": {
    "primary": "dashboard",
    "dashboard": {
      "method": "path",
      "path": "dashboard.GuiFocus",
      "value_map": {
        "0": "NoFocus",
        "1": "InternalPanel",
        "2": "ExternalPanel",
        // ... etc
      },
      "description": "Real-time UI focus from Status.json"
    }
  }
}
```

Shows:
- Numeric dashboard value mapped to enum labels
- Value mapping at source level

### 3. Catalog Features Included

The updated catalog (signals_catalog_v2.json) includes:

**Comprehensive Coverage**:
- 200+ signals covering all game aspects
- Commander status, ranks, credits
- Location & navigation (system, station, body, coordinates)
- Ship status (docked, landed, supercruise, FSD state)
- Foot/Odyssey status (on foot, taxi, multicrew) 
- Combat (hardpoints, shields, danger, targeting)
- Fuel, cargo, vehicle states
- HUD modes, GUI focus, night vision
- SRV operations, fighter operations
- Complete bitfield flag coverage (50+ flags)

**Signal Types**:
- `bool` - Binary flags and states
- `enum` - Multi-value categorical data
- `number` - Numeric values (fuel, cargo, credits, coordinates)
- `string` - Text data (system name, station name, body name)

**Derivation Operators**:
- `flag` - Bitfield flag extraction
- `path` - Nested field access
- `map` - Value mapping with defaults
- `first_match` - Conditional logic chains
- `recent` - **NEW** - Time-windowed vent checks
- `and` - **NEW** - Combine multiple conditions

**UI Organization**:
- Three tiers: `core`, `detail`, `advanced`
- 20+ categories for logical grouping
- Icon support for all signals and values
- Human-readable labels

## Architecture Benefits

### 1. **Flexibility**
Signals can derive from the most appropriate source:
- Real-time monitoring → Dashboard
- Event detection → Journal
- Persistent state → State
- Station data → CAPI

### 2. **Edge Detection**
Combine dashboard state + journal events:
```
"just_docked" = (recent Docked event) AND (docked flag = true)
```

### 3. **Rule Simplicity**
Users write rules with high-level signals:
```json
{
  "when": {"all": [{"signal": "docked", "op": "eq", "value": true}]},
  "then": [{"vkb_set_shift": ["Shift1"]}]
}
```

### 4. **Source Context Awareness**
Rule engine selects appropriate low-level check based on:
- Which EDMC hook triggered evaluation
- Available data sources
- User preference (if specified)

### 5. **Backward Compatibility**
- Signals without `sources` use `derive` only
- Existing rules work unchanged
- Progressive enhancement path

## Implementation Roadmap

### Phase 1: Foundation (Current)
- ✅ Architecture documentation
- ✅ Catalog structure with `sources` examples
- ✅ Documentation of patterns and best practices

### Phase 2: Signal Derivation Engine Updates
**File to modify**: `src/edmcruleengine/signal_derivation.py`

**Add support for**:
1. **Recent event operator**:
```python
def _derive_recent(self, spec: Dict, context: Dict) -> bool:
    """Check if event occurred within time window."""
    event_name = spec["event_name"]
    within_seconds = spec.get("within_seconds", 5)
    recent_events = context.get("recent_events", {})
    
    if event_name in recent_events:
        event_time = recent_events[event_name]
        age = time.time() - event_time
        return age <= within_seconds
    return False
```

2. **AND/OR operators**:
```python
def _derive_and(self, spec: Dict, context: Dict) -> bool:
    """All conditions must be true."""
    conditions = spec.get("conditions", [])
    return all(self._execute_derive_op(cond, context) for cond in conditions)

def _derive_or(self, spec: Dict, context: Dict) -> bool:
    """At least one condition must be true."""
    conditions = spec.get("conditions", [])
    return any(self._execute_derive_op(cond, context) for cond in conditions)
```

3. **Source-aware derivation**:
```python
def derive_signal_with_source(
    self,
    signal_def: Dict,
    context: Dict,
    preferred_source: str = "auto"
) -> Any:
    """Derive signal using source-specific logic."""
    sources = signal_def.get("sources", {})
    
    if not sources:
        # Fallback to primary derivation
        return self.derive_signal(signal_def, context)
    
    # Select source based on context
    source = self._select_source(sources, context, preferred_source)
    return self._evaluate_source(source, context)
```

### Phase 3: Event Handler Updates
**File to modify**: `src/edmcruleengine/event_handler.py`

**Add event tracking**:
```python
class EventHandler:
    def __init__(self, ...):
        # ... existing init ...
        self._recent_events: Dict[str, float] = {}
        self._event_window = 5.0  # seconds
    
    def handle_event(self, event_type: str, event_data: Dict, ...):
        # Track event timestamp
        self._recent_events[event_type] = time.time()
        
        # Prune old events
        current_time = time.time()
        self._recent_events = {
            event: timestamp
            for event, timestamp in self._recent_events.items()
            if current_time - timestamp <= self._event_window
        }
        
        # Evaluate rules with event context
        context = {
            "dashboard": event_data if source == "dashboard" else {},
            "journal": event_data if source == "journal" else {},
            "state": self.state,
            "recent_events": self._recent_events,
            "trigger_source": source,
            "event_name": event_type
        }
        self.rule_engine.evaluate_rules(context)
```

### Phase 4: Rule Engine Updates
**File to modify**: `src/edmcruleengine/rules_engine.py`

**Add source context**:
```python
class RuleEngine:
    def evaluate_rules(self, context: Dict):
        """Evaluate all rules with full context."""
        for rule in self.rules:
            # Pass context to signal derivation
            matched = self._evaluate_when_clause(rule["when"], context)
            # ... execute actions if matched ...
    
    def _evaluate_when_clause(self, when_clause: Dict, context: Dict) -> bool:
        """Evaluate when clause with context."""
        # Pass context through to signal derivation
        for condition in when_clause.get("all", []):
            signal_value = self._derive_signal(condition["signal"], context)
            # ... compare with condition["value"] ...
```

### Phase 5: UI Updates
**File to modify**: `src/edmcruleengine/rule_editor_v3.py`

**Add source selection**:
```python
def _add_condition(self, group: str, condition: Optional[Dict] = None):
    # ... existing code ...
    
    # Add source hint dropdown (optional)
    ttk.Label(row_frame, text="Source:").pack(side=tk.LEFT, padx=2)
    source_var = tk.StringVar(value=condition.get("source_hint", "auto") if condition else "auto")
    source_combo = ttk.Combobox(
        row_frame,
        textvariable=source_var,
        state="readonly",
        width=12,
        values=["auto", "dashboard", "journal", "state", "capi"]
    )
    source_combo.pack(side=tk.LEFT, padx=2)
```

### Phase 6: Validation & Testing
**Files to modify**: `test/test_v3_rules.py`, `test/test_signal_derivation.py`

**Add tests for**:
1. Recent event operator
2. AND/OR combination
3. Multi-source signal derivation
4. Source selection logic
5. Event tracking and pruning
6. Edge detection scenarios

### Phase 7: Migration
1. Backup existing `signals_catalog.json`
2. Rename `signals_catalog_v2.json` → `signals_catalog.json`
3. Update all remaining signals with `sources` mappings
4. Test with real EDMC instance
5. Document migration for users

## Next Steps

### Immediate (This Session)
1. ✅ Document architecture
2. ✅ Add example source mappings to catalog
3. ⏳ Review with user for feedback

### Short Term (Next Development Cycle)
1. Implement recent event tracking in event_handler.py
2. Add recent/and/or operators to signal_derivation.py
3. Update rule engine to pass event context
4. Add basic tests

### Medium Term
1. Update UI to show/select sources
2. Add source-specific validation
3. Write comprehensive tests
4. Update all signals with source mappings

### Long Term
1. Performance optimization for event tracking
2. Source analytics (which sources used most)
3. Advanced UI features (source debugging)
4. Community feedback integration

## Usage Examples

### Example 1: Trigger on Docking
```json
{
  "title": "Set lights on docking",
  "when": {
    "all": [
      {"signal": "docking_state", "op": "eq", "value": "just_docked"}
    ]
  },
  "then": [
    {"vkb_set_shift": ["Shift1"]}
  ]
}
```

**Generated check** (journal source):
```python
recent_event("Docked", within_seconds=3) AND flag(ship_flags, bit=0)
```

### Example 2: Monitor Fuel Level
```json
{
  "title": "Warn on low fuel",
  "when": {
    "all": [
      {"signal": "fuel_percent", "op": "lt", "value": 25}
    ]
  },
  "then": [
    {"vkb_set_shift": ["Subshift1"]}
  ]
}
```

**Generated check** (dashboard source):
```python
path("dashboard.Fuel.FuelMain") / path("dashboard.Fuel.FuelReservoir") < 0.25
```

### Example 3: System Entry Detection
```json
{
  "title": "Alert on new system",
  "when": {
    "all": [
      {"signal": "edmc_event", "op": "eq", "value": "FSDJump"}
    ]
  },
  "then": [
    {"vkb_set_shift": ["Shift2"]}
  ]
}
```

**Generated check** (journal source):
```python
event_name == "FSDJump"
```

## Files Created/Modified

### Created
- `docs/MULTI_SOURCE_SIGNALS.md` - Architecture documentation
- This summary document

### Modified
- `signals_catalog_v2.json` - Added source mappings to 4 signals

### To Be Modified (Implementation Phase)
- `src/edmcruleengine/signal_derivation.py` - Add new operators
- `src/edmcruleengine/event_handler.py` - Add event tracking  
- `src/edmcruleengine/rules_engine.py` - Pass event context
- `src/edmcruleengine/rule_editor_v3.py` - UI for source selection
- `test/*.py` - Add comprehensive tests

## Questions for Review

1. **Source Selection**: Should users explicitly choose source, or always auto-select?
2. **Event Window**: Is 5 seconds a good default for `within_seconds`?
3. **Performance**: How many historical events should we track?
4. **Priority**: Which implementation phase should we tackle first?
5. **Migration**: Should we support both catalogs during transition?

## References

- [MULTI_SOURCE_SIGNALS.md](docs/MULTI_SOURCE_SIGNALS.md) - Complete architecture guide
- `signals_catalog_v2.json` - Updated catalog with examples
- Current implementation files in `src/edmcruleengine/`
