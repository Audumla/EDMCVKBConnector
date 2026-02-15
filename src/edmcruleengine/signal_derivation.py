"""
Signal derivation engine for EDMC VKB Connector.

Derives high-level signal values from raw Elite Dangerous status data
according to the catalog's derivation specifications.
"""

from __future__ import annotations

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
    
    def derive_all_signals(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Derive all signal values from entry data.
        
        Args:
            entry: Raw dashboard/status entry
            
        Returns:
            Dict mapping signal names to derived values
        """
        result = {}
        for signal_name, signal_def in self.signals.items():
            try:
                value = self.derive_signal(signal_name, signal_def, entry)
                result[signal_name] = value
            except Exception as e:
                logger.warning(f"Failed to derive signal '{signal_name}': {type(e).__name__}: {e}")
                # Use default for failed derivation
                signal_type = signal_def.get("type")
                if signal_type == "bool":
                    result[signal_name] = False
                elif signal_type == "enum":
                    # Use first enum value as fallback
                    values = signal_def.get("values", [])
                    if values:
                        result[signal_name] = values[0].get("value", "unknown")
                    else:
                        result[signal_name] = "unknown"
                else:
                    result[signal_name] = None
        
        return result
    
    def derive_signal(
        self,
        signal_name: str,
        signal_def: Dict[str, Any],
        entry: Dict[str, Any]
    ) -> Any:
        """
        Derive a single signal value.
        
        Args:
            signal_name: Signal name
            signal_def: Signal definition from catalog
            entry: Raw dashboard/status entry
            
        Returns:
            Derived signal value
        """
        derive_spec = signal_def.get("derive", {})
        signal_type = signal_def.get("type")
        
        value = self._execute_derive_op(derive_spec, entry)
        
        # Ensure value matches signal type
        if signal_type == "bool":
            return bool(value)
        elif signal_type == "enum":
            # Validate enum value
            allowed_values = [v.get("value") for v in signal_def.get("values", [])]
            if value not in allowed_values:
                # Use default if specified
                default = derive_spec.get("default")
                if default and default in allowed_values:
                    return default
                # Otherwise use first value
                return allowed_values[0] if allowed_values else "unknown"
            return value
        
        return value
    
    def _execute_derive_op(self, derive_spec: Dict[str, Any], entry: Dict[str, Any]) -> Any:
        """
        Execute a derivation operation.
        
        Args:
            derive_spec: Derivation specification
            entry: Raw data entry
            
        Returns:
            Derived value
        """
        op = derive_spec.get("op")
        
        if op == "flag":
            return self._derive_flag(derive_spec, entry)
        elif op == "path":
            return self._derive_path(derive_spec, entry)
        elif op == "map":
            return self._derive_map(derive_spec, entry)
        elif op == "first_match":
            return self._derive_first_match(derive_spec, entry)
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
            flags_value = entry.get("Flags", 0)
        elif bitfield_path == "dashboard.Flags2":
            flags_value = entry.get("Flags2", 0)
        else:
            # Generic path extraction
            flags_value = self._extract_path(entry, bitfield_path)
        
        # Check bit
        if isinstance(flags_value, int):
            return bool(flags_value & (1 << bit_num))
        
        return False
    
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
            return default
        return value
    
    def _derive_map(self, spec: Dict[str, Any], entry: Dict[str, Any]) -> Any:
        """
        Derive value by mapping input to output.
        
        Args:
            spec: { "op": "map", "from": {...}, "map": {...}, "default": ... }
            entry: Raw data entry
            
        Returns:
            Mapped value
        """
        # First derive the input value
        from_spec = spec.get("from", {})
        input_value = self._execute_derive_op(from_spec, entry)
        
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
    
    def _derive_first_match(self, spec: Dict[str, Any], entry: Dict[str, Any]) -> Any:
        """
        Derive value from first matching case.
        
        Args:
            spec: { "op": "first_match", "cases": [...], "default": ... }
            entry: Raw data entry
            
        Returns:
            First matching case value or default
        """
        cases = spec.get("cases", [])
        default = spec.get("default")
        
        for case in cases:
            when_spec = case.get("when", {})
            # Check if condition matches
            if self._check_condition(when_spec, entry):
                return case.get("value")
        
        return default
    
    def _check_condition(self, condition_spec: Dict[str, Any], entry: Dict[str, Any]) -> bool:
        """
        Check if a condition matches.
        
        Args:
            condition_spec: Condition specification
            entry: Raw data entry
            
        Returns:
            True if condition matches
        """
        # For now, support simple flag conditions
        op = condition_spec.get("op")
        
        if op == "flag":
            return self._derive_flag(condition_spec, entry)
        
        # Could add more condition types here
        return False
    
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
