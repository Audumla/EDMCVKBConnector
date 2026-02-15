# Multi-Source Signal Mapping Architecture

## Overview

Signals in the Enhanced EDMC VKB Connector can derive their values from multiple EDMC data sources. This allows a single high-level signal (like "docked") to be evaluated using dashboard flags, journal events, or accumulated state depending on the context.

## Data Sources

### 1. **Dashboard** (`dashboard`)
- **Source**: `Status.json` file (~1 Hz update rate)
- **Contains**: Real-time ship/foot status flags and values
- **Use for**: Continuous state monitoring (shields, hardpoints, fuel, etc.)
- **Example fields**: `Flags`, `Flags2`, `GuiFocus`, `Latitude`, `Fuel`, `Cargo`

### 2. **Journal** (`journal`)
- **Source**: Game journal files (event-driven)
- **Contains**: 234+ discrete game events
- **Use for**: Event-based triggers and recent event checks
- **Example events**: `FSDJump`, `Docked`, `Undocked`, `Touchdown`, `Liftoff`

### 3. **State** (`state`)
- **Source**: EDMC's accumulated game state
- **Contains**: Persistent data from journal events
- **Use for**: Historical/persistent info that survives EDMC restarts
- **Example fields**: `Commander`, `StarSystem`, `StationName`, `Rank`, `Cargo`, `Missions`

### 4. **CAPI** (`capi`, `capi_legacy`, `capi_fleetcarrier`)
- **Source**: Frontier Companion API
- **Contains**: Detailed market, outfitting, fleet carrier data
- **Use for**: Station-specific detailed information
- **Update trigger**: On docking, manual refresh

## Signal Derivation Patterns

### Pattern 1: Single-Source Signals

Simple signals derive from one source:

```json
{
  "weapons_out": {
    "type": "bool",
    "derive": {
      "op": "flag",
      "field_ref": "ship_flags",
      "bit": 6
    },
    "sources": {
      "dashboard": {
        "method": "flag",
        "bitfield": "ship_flags",
        "bit": 6
      }
    }
  }
}
```

### Pattern 2: Multi-Source Signals

Signals that can be evaluated from multiple sources:

```json
{
  "docked": {
    "type": "bool",
    "derive": {
      "op": "flag",
      "field_ref": "ship_flags",
      "bit": 0
    },
    "sources": {
      "dashboard": {
        "method": "flag",
        "bitfield": "ship_flags",
        "bit": 0,
        "description": "Real-time docked state"
      },
      "journal": {
        "method": "recent_event",
        "event_name": "Docked",
        "within_seconds": 5,
        "description": "Just docked (event-based)"
      },
      "state": {
        "method": "path",
        "path": "state.Docked",
        "description": "Persistent docked state"
      }
    }
  }
}
```

### Pattern 3: Hybrid Signals (Dashboard + Journal)

Signals that combine real-time state with recent events:

```json
{
  "docking_state": {
    "type": "enum",
    "values": ["in_space", "landed", "docked", "just_docked", "just_undocked"],
    "derive": {
      "op": "first_match",
      "cases": [
        {
          "when": {
            "op": "and",
            "conditions": [
              {"op": "recent", "event_name": "Docked", "within_seconds": 3},
              {"op": "flag", "field_ref": "ship_flags", "bit": 0}
            ]
          },
          "value": "just_docked"
        },
        {
          "when": {"op": "flag", "field_ref": "ship_flags", "bit": 0},
          "value": "docked"
        }
      ],
      "default": "in_space"
    },
    "sources": {
      "primary": ["dashboard", "journal"],
      "fallback": "dashboard"
    }
  }
}
```

## Derivation Operators

### Core Operators

| Operator | Description | Sources | Example |
|----------|-------------|---------|---------|
| `flag` | Bitfield flag check | dashboard | Check if bit 6 is set |
| `path` | Extract nested value | dashboard, state, capi | Get `state.StarSystem` |
| `map` | Map input to output | any | Convert numeric GuiFocus to enum |
| `first_match` | First matching case | any | Complex conditional logic |

### Event-Based Operators

| Operator | Description | Sources | Example |
|----------|-------------|---------|---------|
| `recent` | Event within N seconds | journal | FSDJump within 5 seconds |
| `and` | Combine conditions | any | Recent event AND flag set |
| `or` | Any condition matches | any | Event A OR Event B |
| `not` | Negate condition | any | NOT docked |

## Source Mapping Structure

### Source Mapping Object

Each signal can define how to evaluate it from different sources:

```json
{
  "signal_name": {
    "type": "bool|enum|number|string",
    "derive": {
      "...": "Primary derivation logic (usually dashboard)"
    },
    "sources": {
      "dashboard": {
        "method": "flag|path",
        "...": "Dashboard-specific fields",
        "description": "When to use dashboard source"
      },
      "journal": {
        "method": "event|recent_event",
        "event_name": "EventName",
        "within_seconds": 5,
        "description": "When to use journal source"
      },
      "state": {
        "method": "path",
        "path": "state.FieldName",
        "description": "When to use state source"
      }
    }
  }
}
```

### Source Method Types

#### `flag` - Bitfield flag check
```json
{
  "method": "flag",
  "bitfield": "ship_flags|foot_flags",
  "bit": 0,
  "inverted": false
}
```

#### `path` - Field extraction
```json
{
  "method": "path",
  "path": "dashboard.GuiFocus",
  "default": 0
}
```

#### `event` - Exact event match
```json
{
  "method": "event",
  "event_name": "FSDJump",
  "field_checks": {
    "JumpType": "Hyperspace"
  }
}
```

#### `recent_event` - Time-windowed event
```json
{
  "method": "recent_event",
  "event_name": "Docked",
  "within_seconds": 5,
  "field_checks": {}
}
```

#### `compound` - Multiple conditions
```json
{
  "method": "compound",
  "op": "and",
  "conditions": [
    {"method": "flag", "bitfield": "ship_flags", "bit": 0},
    {"method": "recent_event", "event_name": "Docked", "within_seconds": 3}
  ]
}
```

## Rule Generation

When a rule uses a multi-source signal, the rule engine must:

1. **Determine Available Sources**: Check which EDMC hooks are active
2. **Select Source**: Choose the most appropriate source:
   - For continuous monitoring: Use dashboard
   - For event triggers: Use journal
   - For persistent state: Use state
3. **Build Condition**: Translate the signal condition to the underlying EDMC check

### Example: Building a Rule

**User-Facing Rule**:
```json
{
  "title": "Alert on docking",
  "when": {
    "all": [
      {"signal": "docked", "op": "eq", "value": true}
    ]
  },
  "then": [
    {"vkb_set_shift": ["Shift1"]}
  ]
}
```

**Generated Low-Level Conditions** (depends on source context):

#### Option A: Dashboard source
```json
{
  "check": "flag",
  "field": "Flags",
  "bit": 0,
  "expected": true
}
```

#### Option B: Journal source (recent event)
```json
{
  "check": "recent_event",
  "event": "Docked",
  "within_seconds": 5
}
```

#### Option C: Combined (edge detection)
```json
{
  "check": "and",
  "conditions": [
    {"check": "recent_event", "event": "Docked", "within_seconds": 1},
    {"check": "flag", "field": "Flags", "bit": 0, "expected": true}
  ]
}
```

## Implementation in Rules Engine

### Evaluating Multi-Source Signals

```python
class MultiSourceSignalEvaluator:
    def evaluate_signal(self, signal_name: str, signal_def: Dict, context: Dict) -> Any:
        """
        Evaluate a signal using the appropriate source.
        
        Args:
            signal_name: Signal identifier
            signal_def: Signal definition with sources
            context: Evaluation context (contains dashboard, journal, state)
        """
        sources = signal_def.get("sources", {})
        
        # Determine which source to use based on context
        if context.get("trigger_source") == "journal":
            # Journal event triggered this evaluation
            if "journal" in sources:
                return self._eval_journal_source(sources["journal"], context)
        
        # Default to primary derivation (usually dashboard)
        return self._eval_primary_derivation(signal_def["derive"], context)
    
    def _eval_journal_source(self, source_spec: Dict, context: Dict) -> Any:
        """Evaluate using journal source mapping."""
        method = source_spec["method"]
        
        if method == "recent_event":
            event_name = source_spec["event_name"]
            within_seconds = source_spec.get("within_seconds", 5)
            return self._check_recent_event(event_name, within_seconds, context)
        elif method == "event":
            # Check if current event matches
            return context.get("event_name") == source_spec["event_name"]
```

### Building Rules with Source Context

```python
class RuleBuilder:
    def build_condition(self, signal: str, operator: str, value: Any, source_hint: str = "auto") -> Dict:
        """
        Build a low-level condition from a high-level signal condition.
        
        Args:
            signal: Signal name
            operator: Comparison operator
            value: Expected value
            source_hint: Preferred source ("auto", "dashboard", "journal", "state")
        """
        signal_def = self.catalog.get_signal(signal)
        sources = signal_def.get("sources", {})
        
        # Select source
        if source_hint == "auto":
            source = self._select_best_source(sources, context="rule_evaluation")
        else:
            source = sources.get(source_hint)
        
        # Build condition based on source method
        return self._build_source_condition(source, operator, value)
```

## Migration Guide

### Updating Existing Signals

To add multi-source support to an existing signal:

1. **Add `sources` object**:
```json
{
  "docked": {
    "type": "bool",
    "derive": { "...existing..." },
    "sources": {
      "dashboard": {
        "method": "flag",
        "bitfield": "ship_flags",
        "bit": 0
      }
    }
  }
}
```

2. **Add journal source if applicable**:
```json
{
  "sources": {
    "dashboard": { "..." },
    "journal": {
      "method": "recent_event",
      "event_name": "Docked",
      "within_seconds": 5
    }
  }
}
```

3. **Add state source if applicable**:
```json
{
  "sources": {
    "dashboard": { "..." },
    "journal": { "..." },
    "state": {
      "method": "path",
      "path": "state.LastDockedStation",
      "description": "Station name where last docked"
    }
  }
}
```

### Backward Compatibility

- Signals without `sources` object use `derive` only
- Existing rules continue to work unchanged
- New rules can specify source preference via UI option

## Best Practices

1. **Always define dashboard source**: It's the most reliable real-time source
2. **Use journal for edge detection**: Detecting state changes (just docked, just jumped)
3. **Use state for persistence**: Historical data that survives EDMC restart
4. **Provide descriptions**: Explain when each source should be used
5. **Test all sources**: Verify behavior with all supported sources
6. **Document time windows**: Clearly specify `within_seconds` for recent events

## Examples

See `signals_catalog_v2.json` for complete examples of:
- `docking_state` - Hybrid dashboard + journal signal
- `docking_request_state` - Pure journal event signal
- `system_name` - State-based persistent signal
- `weapons_out` - Dashboard flag signal
