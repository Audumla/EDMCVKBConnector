"""
Signal derivation engine for EDMC VKB Connector.

Derives high-level signal values from raw Elite Dangerous status data
according to the catalog's derivation specifications.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from . import plugin_logger

logger = plugin_logger(__name__)


class SignalDerivation:
    """
    Derives signal values from raw dashboard/status data.
    
    Supports derivation operations:
    - map: map input values to output values with defaults
    - flag: extract bitfield flag value
    - path: extract value from nested dict path
    - first_match: return first matching case value
    """
    
    def __init__(self, catalog_data: Dict[str, Any]) -> None:
        """
        Initialize derivation engine with catalog data.
        
        Args:
            catalog_data: Catalog dict containing signals and bitfields
        """
        self.signals = catalog_data.get("signals", {})
        self.bitfields = catalog_data.get("bitfields", {})
        self.catalog_data = catalog_data
    
    def derive_all_signals(
        self,
        entry: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Derive all signal values from entry data.
        
        Args:
            entry: Raw dashboard/status entry
            context: Additional context (recent_events, trigger_source, etc.)
            
        Returns:
            Dict mapping signal names to derived values
        """
        if context is None:
            context = {}
        result = {}
        for signal_name, signal_def in self.signals.items():
            # Skip comment fields (starting with underscore) and non-dict values
            if signal_name.startswith("_") or not isinstance(signal_def, dict):
                continue
            
            try:
                value = self.derive_signal(signal_name, signal_def, entry, context)
                result[signal_name] = value
            except Exception as e:
                logger.warning(f"Failed to derive signal '{signal_name}': {type(e).__name__}: {e}")
                # Use explicit unknown for failed derivation to avoid acting on missing data
                result[signal_name] = "unknown"
        
        return result
    
    def derive_signal(
        self,
        signal_name: str,
        signal_def: Dict[str, Any],
        entry: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Derive a single signal value.

        Args:
            signal_name: Signal name
            signal_def: Signal definition from catalog
            entry: Raw dashboard/status entry
            context: Additional context (recent_events, trigger_source, etc.)

        Returns:
            Derived signal value
        """
        if context is None:
            context = {}
        derive_spec = signal_def.get("derive", {})
        signal_type = signal_def.get("type")

        # Skip container signals (no derive key or derive op is None)
        if not derive_spec or derive_spec.get("op") is None:
            return None
        
        value = self._execute_derive_op(derive_spec, entry, context)
        
        if value is None or value == "unknown":
            return "unknown"
        if signal_type == "bool":
            return bool(value)
        elif signal_type == "enum":
            # Validate enum value; unknown if not a recognised value
            allowed_values = [v.get("value") for v in signal_def.get("values", [])]
            if value not in allowed_values:
                return "unknown"
            return value
        
        return value
    
    def _execute_derive_op(
        self,
        derive_spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Execute a derivation operation.
        
        Args:
            derive_spec: Derivation specification
            entry: Raw data entry
            context: Additional context (recent_events, trigger_source, etc.)
            
        Returns:
            Derived value
        """
        op = derive_spec.get("op")
        
        if op == "flag":
            return self._derive_flag(derive_spec, entry)
        elif op == "path":
            return self._derive_path(derive_spec, entry)
        elif op == "map":
            return self._derive_map(derive_spec, entry, context)
        elif op == "first_match":
            return self._derive_first_match(derive_spec, entry, context)
        elif op == "event":
            return self._derive_event(derive_spec, entry)
        elif op == "recent":
            return self._derive_recent(derive_spec, context)
        elif op == "and":
            return self._derive_and(derive_spec, entry, context)
        elif op == "or":
            return self._derive_or(derive_spec, entry, context)
        elif op == "count":
            return self._derive_count(derive_spec, entry)
        elif op == "exists":
            return self._derive_exists(derive_spec, entry)
        elif op == "sum":
            return self._derive_sum(derive_spec, entry, context)
        elif op == "any":
            return self._derive_any(derive_spec, entry)
        elif op == "not":
            return self._derive_not(derive_spec, entry, context)
        elif op in {"eq", "ne", "lt", "lte", "gt", "gte"}:
            return self._derive_compare(derive_spec, entry, context)
        elif op == "match":
            return self._check_match(derive_spec, entry, context)
        else:
            raise ValueError(f"Unknown derivation op: {op}")
    
    def _derive_flag(self, spec: Dict[str, Any], entry: Dict[str, Any]) -> bool:
        """
        Derive boolean value from a bitfield flag.
        
        Args:
            spec: { "op": "flag", "field_ref": "ship_flags", "bit": 6 }
            entry: Raw data entry
            
        Returns:
            Boolean flag value
        """
        field_ref = spec.get("field_ref")
        bit_num = spec.get("bit")
        
        if field_ref not in self.bitfields:
            raise ValueError(f"Unknown bitfield reference: {field_ref}")
        
        # Resolve bitfield path (e.g., "dashboard.Flags")
        bitfield_path = self.bitfields[field_ref]
        
        # For now, handle dashboard.Flags and dashboard.Flags2 directly
        # Entry structure depends on source (dashboard vs journal)
        if bitfield_path == "dashboard.Flags":
            if "Flags" not in entry:
                return None
            flags_value = entry.get("Flags")
        elif bitfield_path == "dashboard.Flags2":
            if "Flags2" not in entry:
                return None
            flags_value = entry.get("Flags2")
        else:
            # Generic path extraction
            flags_value = self._extract_path(entry, bitfield_path)
            if flags_value is None:
                return None
        
        # Check bit
        if isinstance(flags_value, int):
            return bool(flags_value & (1 << bit_num))

        return None
    
    def _derive_path(self, spec: Dict[str, Any], entry: Dict[str, Any]) -> Any:
        """
        Derive value from a nested path.
        
        Args:
            spec: { "op": "path", "path": "dashboard.GuiFocus", "default": 0 }
            entry: Raw data entry
            
        Returns:
            Extracted value or default
        """
        path = spec.get("path", "")
        default = spec.get("default")
        
        value = self._extract_path(entry, path)
        if value is None:
            return None
        return value
    
    def _derive_map(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Derive value by mapping input to output.
        
        Args:
            spec: { "op": "map", "from": {...}, "map": {...}, "default": ... }
            entry: Raw data entry
            context: Additional context
            
        Returns:
            Mapped value
        """

        # First derive the input value
        from_spec = spec.get("from", {})
        input_value = self._execute_derive_op(from_spec, entry, context)
        
        if input_value is None:
            return None

        # Convert to string for map lookup
        map_dict = spec.get("map", {})
        default = spec.get("default")
        
        # Try string conversion (handle boolean special case)
        if isinstance(input_value, bool):
            key = str(input_value).lower()  # "true" or "false"
        else:
            key = str(input_value)
        
        if key in map_dict:
            return map_dict[key]
        
        # Return default
        return default
    
    def _derive_first_match(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Derive value from first matching case.
        
        Args:
            spec: { "op": "first_match", "cases": [...], "default": ... }
            entry: Raw data entry
            context: Additional context
            
        Returns:
            First matching case value or default
        """

        cases = spec.get("cases", [])
        default = spec.get("default")
        
        for case in cases:
            when_spec = case.get("when", {})
            # Check if condition matches
            if self._check_condition(when_spec, entry, context):
                return case.get("value")
        
        return default
    
    def _check_condition(
        self,
        condition_spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        Check if a condition matches.
        
        Args:
            condition_spec: Condition specification
            entry: Raw data entry
            context: Additional context
            
        Returns:
            True if condition matches
        """

        op = condition_spec.get("op")
        
        if op == "flag":
            return self._derive_flag(condition_spec, entry)
        elif op == "recent":
            return self._derive_recent(condition_spec, context)
        elif op == "and":
            return self._derive_and(condition_spec, entry, context)
        elif op == "or":
            return self._derive_or(condition_spec, entry, context)
        elif op == "not":
            return self._derive_not(condition_spec, entry, context)
        elif op == "match":
            return self._check_match(condition_spec, entry, context)
        elif op in {"eq", "ne", "lt", "lte", "gt", "gte"}:
            return self._derive_compare(condition_spec, entry, context)
        
        # Could add more condition types here
        return False

    def _resolve_operand(
        self,
        operand: Any,
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Resolve an operand that may be a literal or nested derive spec.

        Args:
            operand: Literal value or derive spec dict
            entry: Raw data entry
            context: Additional context

        Returns:
            Resolved operand value
        """

        if isinstance(operand, dict) and "op" in operand:
            op = operand.get("op")
            if op in {"eq", "ne", "lt", "lte", "gt", "gte", "not", "match"}:
                return self._check_condition(operand, entry, context)
            return self._execute_derive_op(operand, entry, context)

        return operand

    def _derive_compare(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        Compare two values using a comparison operator.

        Supports both forms:
        - {"op":"eq","left":{...},"right":...}
        - {"op":"eq","path":"state.Rank.Empire","value":3}
        """
        op = spec.get("op")
        left_spec = spec.get("left")
        right_spec = spec.get("right")

        # Backward-compatible shorthand used in catalog conditions
        if left_spec is None and "path" in spec:
            left_spec = {"op": "path", "path": spec.get("path")}
        if right_spec is None and "value" in spec:
            right_spec = spec.get("value")

        left = self._resolve_operand(left_spec, entry, context)
        right = self._resolve_operand(right_spec, entry, context)

        try:
            if op == "eq":
                return left == right
            if op == "ne":
                return left != right
            if op == "lt":
                return left < right
            if op == "lte":
                return left <= right
            if op == "gt":
                return left > right
            if op == "gte":
                return left >= right
        except TypeError:
            return False

        return False

    def _derive_not(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        Negate a condition.

        Args:
            spec: {"op":"not","condition":{...}}
            entry: Raw data entry
            context: Additional context

        Returns:
            Logical negation of the child condition
        """

        condition = spec.get("condition", {})
        return not self._check_condition(condition, entry, context)
    
    def _derive_event(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any]
    ) -> bool:
        """
        Check if the current entry matches a specific event.
        
        Args:
            spec: { "op": "event", "event_name": "Docked" }
            entry: Raw data entry
            
        Returns:
            True if entry event matches event_name
        """
        event_name = spec.get("event_name")
        current_event = entry.get("event")
        
        return current_event == event_name
    
    def _derive_recent(
        self,
        spec: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if an event occurred recently.
        
        Args:
            spec: { "op": "recent", "event_name": "Docked", "within_seconds": 3 }
            context: Context dict containing recent_events
            
        Returns:
            True if event occurred within time window
        """
        event_name = spec.get("event_name")
        within_seconds = spec.get("within_seconds", 5)
        
        recent_events = context.get("recent_events", {})
        
        if event_name in recent_events:
            event_time = recent_events[event_name]
            current_time = time.time()
            if current_time - event_time <= within_seconds:
                return True
        
        return False
    
    def _derive_and(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if all conditions are true (logical AND).
        
        Args:
            spec: { "op": "and", "conditions": [...] }
            entry: Raw data entry
            context: Additional context
            
        Returns:
            True if all conditions match
        """
        conditions = spec.get("conditions", [])
        
        for condition in conditions:
            if not self._check_condition(condition, entry, context):
                return False
        
        return True
    
    def _derive_or(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if any condition is true (logical OR).
        
        Args:
            spec: { "op": "or", "conditions": [...] }
            entry: Raw data entry
            context: Additional context
            
        Returns:
            True if any condition matches
        """
        conditions = spec.get("conditions", [])
        
        for condition in conditions:
            if self._check_condition(condition, entry, context):
                return True
        
        return False
    
    def _check_match(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        Check if an event property matches a specific value.
        
        Args:
            spec: { "op": "match", "event_property": "IsPlayer", "value": true }
                  or { "op": "match", "event_name": "Interdicted", "event_property": "IsPlayer", "value": true }
            entry: Raw data entry (contains event properties and '__edmc_event_type')
            context: Additional context (optional, unused for match)
            
        Returns:
            True if event property matches value (or if event_name matches if specified)
        """
        # Optional: check if this is the right event type
        expected_event = spec.get("event_name")
        if expected_event:
            current_event = entry.get("event") or entry.get("__edmc_event_type")
            if current_event != expected_event:
                return False
        
        # Extract the property and compare
        property_name = spec.get("event_property", spec.get("field"))
        expected_value = spec.get("value")
        
        if not property_name:
            return False
        
        actual_value = entry.get(property_name)
        return actual_value == expected_value
    
    def _extract_path(self, data: Any, path: str) -> Any:
        """
        Extract value from nested dict using dot notation.
        
        Args:
            data: Data dict
            path: Dot-separated path (e.g., "dashboard.GuiFocus")
            
        Returns:
            Extracted value or None if path doesn't exist
        """
        # Handle special "dashboard" prefix - in raw entries, dashboard fields
        # are at the root level, not nested under "dashboard"
        if path.startswith("dashboard."):
            field_name = path.split(".", 1)[1]
            return data.get(field_name)
        
        current = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _derive_count(self, spec: Dict[str, Any], entry: Dict[str, Any]) -> int:
        """
        Count elements in a list or dict at path.

        Args:
            spec: { "op": "count", "path": "state.Raw", "default": 0 }
            entry: Raw data entry

        Returns:
            Count of elements or default if path doesn't exist
        """
        path = spec.get("path", "")
        default = spec.get("default", 0)

        value = self._extract_path(entry, path)
        if value is None:
            return default

        if isinstance(value, (list, dict)):
            return len(value)

        return default

    def _derive_exists(self, spec: Dict[str, Any], entry: Dict[str, Any]) -> bool:
        """
        Check if a value exists at path.

        Args:
            spec: { "op": "exists", "path": "state.Powerplay.Power" }
            entry: Raw data entry

        Returns:
            True if path exists and is not empty, False otherwise
        """
        path = spec.get("path", "")
        value = self._extract_path(entry, path)

        if value is None or value == "":
            return False

        return True

    def _derive_sum(
        self,
        spec: Dict[str, Any],
        entry: Dict[str, Any],
        context: Dict[str, Any]
    ) -> int:
        """
        Sum multiple derived values.

        Args:
            spec: { "op": "sum", "values": [{"op": "count", ...}, ...], "default": 0 }
            entry: Raw data entry
            context: Additional context

        Returns:
            Sum of all derived values
        """
        values_specs = spec.get("values", [])
        default = spec.get("default", 0)

        total = 0
        for value_spec in values_specs:
            try:
                value = self._execute_derive_op(value_spec, entry, context)
                total += int(value) if value is not None else 0
            except (ValueError, TypeError):
                continue

        return total if total > 0 else default

    def _derive_any(self, spec: Dict[str, Any], entry: Dict[str, Any]) -> bool:
        """
        Check if any element in array has property matching value.

        Args:
            spec: { "op": "any", "path": "state.Passengers", "property": "VIP", "value": true, "default": false }
            entry: Raw data entry

        Returns:
            True if any element matches, False otherwise
        """
        path = spec.get("path", "")
        property_name = spec.get("property")
        match_value = spec.get("value", True)  # Default: check if property is truthy
        default = spec.get("default", False)

        array = self._extract_path(entry, path)
        if not isinstance(array, list):
            return default

        for item in array:
            if isinstance(item, dict):
                if property_name:
                    if item.get(property_name) == match_value:
                        return True
            elif item == match_value:
                return True

        return default
