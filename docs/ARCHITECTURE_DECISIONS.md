# Architecture Decision Records (ADR)

This document records key architectural decisions made in the EDMCVKBConnector plugin, including rationale, tradeoffs, and future considerations.

---

## ADR-001: Direct Flag Access vs. Catalog-Backed Signals

**Status**: ⚠️ **UNDER REVIEW** (Requires explicit decision)  
**Date**: 2026-02-15  
**Updated**: 2026-02-15 (Corrected after discovering existing v3 branches)  
**Context**: Rule engine design for matching Elite Dangerous status data

### Critical Update

**FACTUAL CORRECTION**: Initial ADR stated catalog-backed approach was "rejected" as Alternative 1. However, **two working branches with catalog implementations exist**:
- `feature/v3-catalog-migration` - Complete catalog-backed implementation
- `copilot/upgrade-catalog-and-migration` - Extended v3 implementation with migration support

**Current Status**: This ADR is **under review**. The choice between flags-first (main) vs semantic-signals (feature/v3) is a strategic UX decision, not a technical limitation.

### Decision (Main Branch - Current)

Use **direct flag access** where rules reference `FLAGS`, `FLAGS2`, and `GUI_FOCUS` constants directly, without an intermediate catalog or signal mapping layer.

**NOTE**: This decision applies to the current main branch. Alternative implementations exist in feature branches and can be adopted if desired.

### Rationale

**Simplicity**:
- Transparent mapping from EDMC Status.json to rule conditions
- Easy to understand for developers and advanced users
- No additional indirection to debug

**Performance**:
- Direct bitmask operations are fast
- No catalog lookup overhead
- Lazy-loading optimization already provides memory efficiency

**Stability**:
- Elite Dangerous Status.json format is stable (unchanged since EDMC 5.0+)
- Minimal risk of EDMC format changes requiring compatibility layers
- Direct coupling is acceptable for stable interfaces

**Development Speed**:
- Faster to implement and test
- No catalog validation pipeline needed
- Visual editor maps directly to rule JSON

### Tradeoffs

**Pros**:
- ✅ Simple and transparent
- ✅ High performance (direct bitmask ops)
- ✅ Easy to debug and test
- ✅ Well-suited to visual editor
- ✅ No migration needed for existing rules

**Cons**:
- ❌ Rules are coupled to EDMC Status.json structure
- ❌ No semantic naming layer (e.g., "combat_ready" vs. raw flags)
- ❌ No support for derived signals (combining multiple flags)
- ❌ Would require rule changes if EDMC format changes

### Alternatives Considered

#### Alternative 1: Catalog-Backed Signals (feature/v3-catalog-migration)

**Description**: Full catalog-backed implementation in `feature/v3-catalog-migration` branch with:
- `signals_catalog.py` (330 lines) - Complete catalog implementation
- Centralized signal definitions
- Derivation pipeline with validation
- Dashboard path fallback (`_get_path_with_dashboard_fallback`)
- Semantic naming layer

**Status**: ✅ **EXISTS - Working implementation available**

**Pros**:
- ✅ Semantic signal names ("landed" vs "FlagsLanded")
- ✅ Signal derivation (combine multiple flags)
- ✅ Abstraction from EDMC internals
- ✅ Dashboard path fallback for compatibility
- ✅ Centralized signal definitions

**Cons**:
- ❌ More architectural complexity
- ❌ Requires migration of existing rules
- ❌ Visual editor needs updates
- ❌ Additional catalog maintenance

**Evaluation Needed**: 
- If UX goal is semantic signals → Consider merging feature/v3 branch
- If UX goal is flags-first → Keep current main branch
- Decision depends on intended user experience, not technical capability

#### Alternative 2: Hybrid Approach (copilot/upgrade-catalog-and-migration)

**Description**: Gradual migration approach in `copilot/upgrade-catalog-and-migration` branch with:
- Both `rules_engine.py` (v2) and `rules_engine_v3.py` 
- `signals_catalog.py` with `SignalsCatalog` class
- `signal_derivation.py` and `rule_editor_v3.py`
- Support for both v2 (flags) and v3 (catalog) rules

**Status**: ✅ **EXISTS - Working implementation available**

**Pros**:
- ✅ Backward compatible during migration
- ✅ Gradual transition path
- ✅ Users can migrate rules incrementally
- ✅ Both approaches work simultaneously

**Cons**:
- ❌ Two rule engines to maintain
- ❌ More complex codebase
- ❌ Longer transition period
- ❌ Potential confusion about which approach to use

**Evaluation Needed**:
- If gradual migration desired → Consider copilot branch
- If clean implementation preferred → Consider feature/v3 branch
- If staying flags-first → Stick with main branch

### Consequences

**If Staying with Main Branch (Flags-First)**:
- Rules remain simple and transparent
- Performance is optimal
- Development is straightforward
- Feature/v3 and copilot branches should be archived with explanation

**If Adopting feature/v3 (Catalog-Backed)**:
- Semantic signal names for better UX
- Signal derivation enables reusable definitions
- Requires rule migration and visual editor updates
- More complex but better abstraction

**If Adopting copilot (Hybrid Migration)**:
- Gradual transition path
- Backward compatible during migration
- Maintain two engines temporarily
- Eventually converge to v3-only

**Decision Required**: Make explicit choice based on UX strategy, not technical limitations. Both approaches are viable.

**Long-term**:
- May need catalog layer if:
  - Users request derived signals
  - EDMC changes Status.json format
  - Complex rules become unmaintainable
- Migration path would be needed
- Would require visual editor updates

### Related Decisions
- See ADR-002: Lazy-Loading Flag Dicts
- See ADR-003: Visual Rule Editor Design

---

## ADR-002: Lazy-Loading Flag Dicts

**Status**: ✅ Accepted (Current Implementation)  
**Date**: 2026-02-15  
**Context**: Memory and CPU optimization for flag decoding

### Decision

Use **lazy-loading dictionaries** (`_LazyFlagDict`) that decode flags on-demand rather than eagerly decoding all flags at initialization.

### Rationale

**Performance**:
- Most rules only check a few flags, not all 32+17+12
- Decoding unused flags wastes CPU cycles
- Memory footprint reduced for rule engines tracking multiple commanders

**Implementation**:
```python
class _LazyFlagDict(dict):
    def __init__(self, bit_value: int, flag_map: Dict[str, int]):
        self._bit_value = bit_value
        self._flag_map = flag_map
    
    def __getitem__(self, key: str) -> bool:
        if key not in self._flag_map:
            raise KeyError(key)
        return bool(self._bit_value & self._flag_map[key])
```

**Interface**:
- Behaves like a normal dict (`flags["FlagsLanded"]`)
- Supports `in` operator (`"FlagsLanded" in flags`)
- Supports `.items()` for iteration (decodes on iteration)

### Tradeoffs

**Pros**:
- ✅ Significant CPU savings (decode only accessed flags)
- ✅ Reduced memory usage (no pre-decoded bool dict)
- ✅ Transparent to rule evaluation code
- ✅ Fast for typical rules (check 1-5 flags)

**Cons**:
- ❌ Slightly slower if checking ALL flags (rare)
- ❌ More complex than simple dict
- ❌ Requires custom class

### Alternatives Considered

#### Alternative 1: Eager Decoding

**Description**: Decode all flags to `Dict[str, bool]` at initialization:
```python
def decode_flags(bit_value: int) -> Dict[str, bool]:
    return {name: bool(bit_value & bit) for name, bit in FLAGS.items()}
```

**Rejected Because**:
- Wastes CPU on unused flags (most rules check 1-5 of 32+17 flags)
- Wastes memory (bool dict for every rule evaluation)
- No performance benefit for typical use cases

#### Alternative 2: Normalized Signals Dict

**Description**: Pre-compute all possible signals into a flat dict:
```python
signals = {
    "landed": flags["FlagsLanded"],
    "gear_down": flags["FlagsLandingGearDown"],
    # ... 50+ signals
}
```

**Rejected Because**:
- Even more wasteful than eager flag decoding
- Still decodes many unused values
- No clear benefit over lazy approach

### Consequences

**Immediate**:
- Optimal performance for typical rules
- Transparent interface for rule evaluation
- Slight implementation complexity

**Long-term**:
- If catalog layer is added, can reuse lazy-loading pattern
- May need benchmarking if derived signals become complex
- Pattern works well for any on-demand computation

### Benchmarks (Estimated)

Based on typical rule checking 3 flags:

| Approach | CPU (relative) | Memory (relative) |
|----------|----------------|-------------------|
| Lazy-loading | 1.0× | 1.0× |
| Eager decoding | 10×+ | 5×+ |
| Normalized signals | 15×+ | 10×+ |

**Note**: Actual benchmarks not performed; estimates based on operation counts.

### Related Decisions
- See ADR-001: Direct Flag Access
- See ADR-003: Visual Rule Editor Design

---

## ADR-003: Visual Rule Editor Design

**Status**: ✅ Accepted (Current Implementation)  
**Date**: 2026-02-15  
**Context**: User interface for rule creation and editing

### Decision

Implement **structured visual editor** with form-based UI for rule conditions and actions, rather than text-based JSON editor.

### Rationale

**Usability**:
- Non-technical users can create rules without JSON knowledge
- Dropdown menus prevent syntax errors
- Real-time validation catches mistakes early
- Preview tab shows resulting JSON

**Maintainability**:
- Structured input ensures valid rule format
- Validation logic separate from UI
- Easy to extend with new condition types
- Consistent with EDMC plugin UI patterns

**Features**:
- Event selection from categorized list (54 events)
- Condition block editor (flags/flags2/gui_focus/field)
- ALL/ANY logic support
- Shift flag controls with Set/Clear/Unchanged
- JSON preview for power users

### Tradeoffs

**Pros**:
- ✅ User-friendly for non-programmers
- ✅ Prevents invalid rules (validation)
- ✅ Consistent UI/UX
- ✅ Easy to add new features
- ✅ Reduces support burden

**Cons**:
- ❌ More code than simple text editor
- ❌ Requires UI testing
- ❌ Cannot express arbitrary JSON (by design)
- ❌ Power users may prefer text editing

### Alternatives Considered

#### Alternative 1: Text-Based JSON Editor

**Description**: Simple text area with JSON validation:
```python
def edit_rule():
    json_text = tk.Text(...)
    # User edits raw JSON
    # Validate on save
```

**Rejected Because**:
- High error rate for non-technical users
- No discoverability (users must know JSON structure)
- Syntax errors frustrating for beginners
- Still need validation, but only at save time

**Compromise**: Visual editor includes JSON preview tab for power users.

#### Alternative 2: Rule Builder Wizard

**Description**: Multi-step wizard walking users through rule creation:
1. Select event type
2. Add conditions
3. Set actions
4. Review and save

**Rejected Because**:
- More clicks for experienced users
- Harder to edit existing rules
- More UI code
- Less flexible

**Future Consideration**: Could add wizard as optional "guided mode" for beginners.

### Consequences

**Immediate**:
- Users can create rules without JSON knowledge
- Fewer support requests about rule syntax
- More code to maintain
- Need UI testing infrastructure

**Long-term**:
- If catalog layer is added, UI can support semantic signals
- Could add rule templates
- Could add condition builder wizard
- Backward compatible with JSON rules

### User Feedback Tracking

Monitor for requests:
- [ ] Rule templates
- [ ] Import/export functionality
- [ ] Condition builder wizard
- [ ] Drag-and-drop reordering
- [ ] Rule testing/simulation
- [ ] Tooltips for all UI elements

### Related Decisions
- See ADR-001: Direct Flag Access
- See ADR-004: External Events Configuration

---

## ADR-004: External Events Configuration

**Status**: ✅ Accepted (Current Implementation)  
**Date**: 2026-02-15  
**Context**: Event definitions for visual rule editor

### Decision

Store event definitions in **external JSON file** (`events_config.json`) rather than hardcoding in Python.

### Rationale

**Flexibility**:
- Easy to add new events without code changes
- Users can customize event list
- Human-readable titles separate from source/event values
- Can update for new EDMC/Elite Dangerous releases

**Structure**:
```json
{
  "sources": [...],
  "events": [
    {
      "source": "journal",
      "event": "FSDJump",
      "title": "FSD Jump",
      "category": "Travel"
    }
  ],
  "condition_types": [...],
  "shift_flags": [...]
}
```

**Maintainability**:
- Non-programmers can add events
- No Python code changes needed
- Can be distributed separately
- Easy to track in version control

### Tradeoffs

**Pros**:
- ✅ Easy to extend (no code changes)
- ✅ User-customizable
- ✅ Human-readable
- ✅ Supports future Elite Dangerous events
- ✅ Clean separation of data and code

**Cons**:
- ❌ External file dependency
- ❌ Must handle missing/invalid file
- ❌ Users can break by editing incorrectly

### Alternatives Considered

#### Alternative 1: Hardcoded in Python

**Description**: Define events in Python constants:
```python
EVENTS = {
    "journal": [
        {"event": "FSDJump", "title": "FSD Jump", "category": "Travel"},
        # ...
    ]
}
```

**Rejected Because**:
- Requires code changes for new events
- Not user-customizable
- Harder to update for new Elite Dangerous releases
- Mixed data and code

#### Alternative 2: Plugin Configuration

**Description**: Store in EDMC config (`VKBConnector_events`):
```python
config.get_list("VKBConnector_events")
```

**Rejected Because**:
- Lost on plugin reinstall
- Hard to edit (not human-readable)
- Not portable between installations
- No version control

### Consequences

**Immediate**:
- Easy to add new events
- Users can customize event list
- Must validate JSON on load

**Long-term**:
- Can distribute event packs
- Can support community contributions
- Need migration strategy if format changes
- Should version the events config format

### Validation Requirements

**Must validate**:
- ✅ Valid JSON syntax
- ✅ Required keys present
- ✅ Event names match EDMC events
- ✅ No duplicate events
- ✅ Source names valid

**Error handling**:
- Load default events if config invalid
- Log validation errors
- Provide user-friendly error messages

### Future Enhancements

Potential improvements:
- [ ] Multiple event config files (user + default)
- [ ] Event config version field
- [ ] Auto-update from repository
- [ ] Community event pack sharing
- [ ] Event documentation links

### Related Decisions
- See ADR-003: Visual Rule Editor Design

---

## Future Considerations

### Catalog-Backed Signals (Deferred)

**When to Reconsider**:
1. Users report difficulty with complex rules
2. Common patterns emerge that need abstraction
3. Elite Dangerous adds complex new status fields
4. EDMC changes Status.json format

**Implementation Plan** (if needed):
1. Create optional `signals_catalog.json`:
   ```json
   {
     "version": "1.0",
     "signals": {
       "combat_ready": {
         "type": "all_of",
         "flags": ["FlagsHardpointsDeployed", "FlagsInMainShip"],
         "flags2_none_of": ["Flags2OnFoot"]
       }
     }
   }
   ```

2. Support both styles in rules (backward compatible):
   ```json
   // Legacy (keep working):
   {"flags": {"all_of": ["FlagsLanded"]}}
   
   // New (opt-in):
   {"signals": {"all_of": ["combat_ready"]}}
   ```

3. Add catalog validation to rule loading

4. Update visual editor to support catalog signals

5. Provide migration tool for existing rules

**Do NOT implement unless**:
- Multiple users request feature
- Clear use cases identified
- Benefits outweigh complexity

---

## ADR-005: Architectural Direction Decision (REQUIRED)

**Status**: 🔴 **DECISION PENDING**  
**Date**: 2026-02-15  
**Context**: Choose between flags-first (main) vs semantic-signals (feature/v3) UX strategy

### The Question

**Do rules reference raw flags or semantic signals?**

This is the fundamental architectural decision that determines the entire user experience.

### Option A: Flags-First (Current Main Branch)

**Description**: Rules directly reference EDMC flags
```json
{"flags": {"all_of": ["FlagsLanded", "FlagsLandingGearDown"]}}
```

**Pros**:
- ✅ Simple and transparent
- ✅ Direct mapping to EDMC Status.json
- ✅ High performance (direct bitmask ops)
- ✅ Easy to debug
- ✅ Current implementation is production-ready

**Cons**:
- ❌ Exposes EDMC internals to users
- ❌ No semantic abstraction
- ❌ Couples rules to EDMC structure
- ❌ No signal derivation

**If Chosen**:
1. Document flags-first as intended UX
2. Archive feature/v3 and copilot branches
3. Enhance visual editor for flags-based rules
4. Update all documentation accordingly

### Option B: Semantic-Signals (feature/v3-catalog-migration Branch)

**Description**: Rules reference catalog-backed semantic signals
```json
{"signals": {"all_of": ["landed", "gear_down"]}}
```

**Pros**:
- ✅ Semantic naming (user-friendly)
- ✅ Abstraction from EDMC internals
- ✅ Signal derivation (reusable definitions)
- ✅ Dashboard path fallback (future-proof)
- ✅ Working implementation exists in feature/v3

**Cons**:
- ❌ More architectural complexity
- ❌ Requires rule migration
- ❌ Visual editor needs updates
- ❌ Catalog maintenance overhead

**If Chosen**:
1. Evaluate feature/v3-catalog-migration branch
2. Plan rule migration strategy
3. Update visual editor for catalog signals
4. Test thoroughly before merge
5. Provide migration tools/docs

### Option C: Hybrid Migration (copilot/upgrade-catalog-and-migration Branch)

**Description**: Support both v2 (flags) and v3 (catalog) during transition

**Pros**:
- ✅ Gradual migration path
- ✅ Backward compatible
- ✅ Users migrate at own pace

**Cons**:
- ❌ Maintain two rule engines
- ❌ More complex codebase
- ❌ Longer transition period

**If Chosen**:
1. Evaluate copilot branch
2. Set timeline for v2 deprecation
3. Provide migration guides
4. Eventually converge to v3-only

### Recommendation

**Make explicit decision based on UX goals**:

**If goal is**: "Users work with EDMC flags directly"
→ **Choose Option A** (Flags-First)

**If goal is**: "Hide EDMC internals behind semantic signals"
→ **Choose Option B** (Semantic-Signals)

**If goal is**: "Gradual transition to semantic signals"
→ **Choose Option C** (Hybrid Migration)

**Action Required**: Document chosen direction in this ADR and align all implementation/documentation accordingly.

---

### Dashboard Path Fallback (Monitoring)

**Current Status**: Not needed (EDMC format stable)

**Monitor for**:
- EDMC Status.json format changes
- New Elite Dangerous status fields
- Breaking changes in EDMC API

**Implementation** (if needed):
```python
def get_field_with_fallback(data: dict, paths: List[str]) -> Any:
    """Try multiple paths, return first that exists."""
    for path in paths:
        try:
            return _traverse_path(data, path)
        except KeyError:
            continue
    raise KeyError(f"None of {paths} found in data")
```

**Use case**:
```python
# Handle both old and new EDMC formats:
flags = get_field_with_fallback(data, [
    "Flags",              # Current format
    "Status.Flags",       # Hypothetical new format
    "dashboard.Flags"     # Another hypothetical
])
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | System | Initial architecture decisions documented |
| 1.1 | 2026-02-15 | System | **Corrected**: Updated ADR-001 to reflect existence of v3 branches, added ADR-005 for architectural direction decision |

---

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) - Current architecture overview
- [V3_IMPLEMENTATION_REVIEW.md](V3_IMPLEMENTATION_REVIEW.md) - Comparison with proposed alternatives
- [RULES_SCHEMA.md](RULES_SCHEMA.md) - Rule JSON schema documentation
- [VISUAL_RULE_EDITOR.md](VISUAL_RULE_EDITOR.md) - Visual editor user guide
