"""
Signal catalog loading and management for EDMC VKB Connector.

Loads and validates the signals catalog which defines:
- Signal types and their UI metadata
- Signal derivation specifications
- Operators for rule conditions
- UI tiers for signal organization
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from . import plugin_logger

logger = plugin_logger(__name__)


class CatalogError(Exception):
    """Raised when catalog is missing, invalid, or incompatible."""
    pass


class SignalsCatalog:
    """
    Loads and provides access to the signals catalog.
    
    The catalog defines all available signals, their types, derivation logic,
    and UI metadata. This ensures signals are never hardcoded in rules.
    """
    
    REQUIRED_KEYS = ["ui_tiers", "operators", "bitfields", "signals"]
    
    def __init__(self, catalog_data: Dict[str, Any]) -> None:
        """
        Initialize catalog from parsed JSON data.
        
        Args:
            catalog_data: Parsed catalog JSON
            
        Raises:
            CatalogError: If catalog is invalid or incompatible
        """
        self._validate_catalog(catalog_data)
        self._data = catalog_data
        # Flatten nested signals into dot-notation keys
        self._flattened_signals: Dict[str, Any] = self._flatten_signals(catalog_data["signals"])
        # Build hierarchical structure for UI navigation
        self._signal_hierarchy: Dict[str, Any] = self._build_signal_hierarchy(catalog_data["signals"])
        
    @classmethod
    def from_file(cls, path: Path) -> SignalsCatalog:
        """
        Load catalog from a JSON file.
        
        Args:
            path: Path to signals_catalog.json
            
        Returns:
            SignalsCatalog instance
            
        Raises:
            CatalogError: If file is missing, invalid JSON, or incompatible
        """
        if not path.exists():
            raise CatalogError(f"Catalog file not found: {path}")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CatalogError(f"Invalid JSON in catalog: {e}")
        except Exception as e:
            raise CatalogError(f"Failed to read catalog: {e}")
        
        return cls(data)
    
    @classmethod
    def from_plugin_dir(cls, plugin_dir: Optional[str] = None) -> SignalsCatalog:
        """
        Load catalog from the plugin directory.
        
        Args:
            plugin_dir: Plugin directory path, or None to auto-detect
            
        Returns:
            SignalsCatalog instance
            
        Raises:
            CatalogError: If catalog cannot be loaded
        """
        if plugin_dir is None:
            # Auto-detect: assume we're in src/edmcruleengine, go up to root
            this_file = Path(__file__).resolve()
            plugin_dir = this_file.parent.parent.parent
        else:
            plugin_dir = Path(plugin_dir)
        
        catalog_path = plugin_dir / "signals_catalog.json"
        return cls.from_file(catalog_path)
    
    def _validate_catalog(self, data: Dict[str, Any]) -> None:
        """
        Validate catalog structure and version.
        
        Args:
            data: Parsed catalog JSON
            
        Raises:
            CatalogError: If catalog is invalid or incompatible
        """
        # Check required keys
        missing = [k for k in self.REQUIRED_KEYS if k not in data]
        if missing:
            raise CatalogError(f"Catalog missing required keys: {missing}")
        
        # Validate ui_tiers
        tiers = data.get("ui_tiers", {})
        if "core" not in tiers or "detail" not in tiers:
            raise CatalogError("Catalog must define 'core' and 'detail' UI tiers")
        
        # Validate operators
        operators = data.get("operators", {})
        required_ops = ["eq", "ne", "in", "nin", "lt", "lte", "gt", "gte", "contains", "exists"]
        missing_ops = [op for op in required_ops if op not in operators]
        if missing_ops:
            raise CatalogError(f"Catalog missing required operators: {missing_ops}")
        
        # Validate signals structure
        signals = data.get("signals", {})
        if not signals:
            raise CatalogError("Catalog must define at least one signal")
        
        for signal_name, signal_def in signals.items():
            # Skip comment fields (starting with underscore)
            if signal_name.startswith("_"):
                continue
            self._validate_signal(signal_name, signal_def)
    
    def _validate_signal(self, name: str, signal_def: Dict[str, Any]) -> None:
        """
        Validate a single signal definition.
        
        Args:
            name: Signal name
            signal_def: Signal definition dict
            
        Raises:
            CatalogError: If signal definition is invalid
        """
        # Skip comment fields and nested containers
        if name.startswith("_") or isinstance(signal_def, dict) and "type" not in signal_def:
            # This is either a comment or a container (nested signals)
            if name.startswith("_") or "_comment" in signal_def:
                return
            # For containers, recursively validate nested signals
            for nested_name, nested_def in signal_def.items():
                if not nested_name.startswith("_") and isinstance(nested_def, dict):
                    self._validate_signal(f"{name}.{nested_name}", nested_def)
            return
        
        required = ["type", "title", "ui", "derive"]
        missing = [k for k in required if k not in signal_def]
        if missing:
            raise CatalogError(f"Signal '{name}' missing required keys: {missing}")
        
        signal_type = signal_def.get("type")
        valid_types = ["bool", "enum", "string", "number", "array", "object", "event"]
        if signal_type not in valid_types:
            raise CatalogError(f"Signal '{name}' has invalid type: {signal_type}")
        
        # Validate enum signals have values
        if signal_type == "enum":
            values = signal_def.get("values")
            if not values or not isinstance(values, list) or len(values) == 0:
                raise CatalogError(f"Enum signal '{name}' must have non-empty 'values' list")
        
        # Validate UI metadata
        ui = signal_def.get("ui", {})
        if "tier" not in ui or ui["tier"] not in ["core", "detail", "advanced"]:
            raise CatalogError(f"Signal '{name}' must have UI tier 'core', 'detail', or 'advanced'")
    
    def _flatten_signals(self, signals: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Flatten nested signal definitions using dot notation.
        
        Example:
            {"commander_ranks": {"combat": {...}, "trade": {...}}}
            becomes:
            {"commander_ranks.combat": {...}, "commander_ranks.trade": {...}}
        
        Args:
            signals: Signal definitions (may be nested)
            prefix: Current path prefix for nested signals
            
        Returns:
            Flattened signals dict with dot-notation keys
        """
        flattened = {}
        
        for key, value in signals.items():
            # Skip comments and documentation
            if key.startswith("_"):
                continue
            
            # Skip non-dict entries
            if not isinstance(value, dict):
                continue
            
            # Check if this is a signal definition (has "type" key) or a container
            if "type" in value:
                # This is a signal definition
                full_key = f"{prefix}.{key}" if prefix else key
                flattened[full_key] = value
            else:
                # This is a container of signals - recursively flatten
                # Skip if it only has a "_comment" key
                content = {k: v for k, v in value.items() if not k.startswith("_")}
                if content:
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    nested = self._flatten_signals(value, new_prefix)
                    flattened.update(nested)
        
        return flattened
    
    def _build_signal_hierarchy(self, signals: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Build a hierarchical tree structure for UI navigation.
        
        Returns a dict where each entry can be either:
        - A signal definition (has "type" key) - leaf node
        - A group with "children" key - branch node
        
        Example structure:
        {
            "commander_name": {...signal def...},  # Leaf - goes directly to operator
            "commander_ranks": {                    # Branch - needs another dropdown
                "_is_group": True,
                "_group_label": "Rank",
                "children": {
                    "combat": {...signal def...},
                    "trade": {...signal def...},
                }
            }
        }
        
        Args:
            signals: Signal definitions (may be nested)
            prefix: Current path prefix for building full signal IDs
            
        Returns:
            Hierarchical dict with groups and signals
        """
        hierarchy = {}
        
        for key, value in signals.items():
            # Skip comments and documentation
            if key.startswith("_"):
                continue
            
            # Skip non-dict entries
            if not isinstance(value, dict):
                continue
            
            full_key = f"{prefix}.{key}" if prefix else key
            
            # Check if this is a signal definition (has "type" key) or a container/group
            if "type" in value:
                # This is a signal definition (leaf node)
                # Add the full flattened key so we can look it up later
                signal_copy = value.copy()
                signal_copy["_signal_id"] = full_key
                hierarchy[key] = signal_copy
            else:
                # This is a container/group of signals - treat as branch node
                # Skip if it only has a "_comment" key
                content = {k: v for k, v in value.items() if not k.startswith("_")}
                if content:
                    # Create a group node
                    group_label = value.get("_comment", key.replace("_", " ").title())
                    hierarchy[key] = {
                        "_is_group": True,
                        "_group_label": group_label,
                        "_group_id": full_key,
                        "children": self._build_signal_hierarchy(value, full_key)
                    }
        
        return hierarchy
    
    @property
    def signals(self) -> Dict[str, Any]:
        """Get all signal definitions (flattened from nested structure)."""
        return self._flattened_signals
    
    @property
    def operators(self) -> Dict[str, Any]:
        """Get all operator definitions."""
        return self._data["operators"]
    
    @property
    def ui_tiers(self) -> Dict[str, Any]:
        """Get UI tier definitions."""
        return self._data["ui_tiers"]
    
    @property
    def bitfields(self) -> Dict[str, str]:
        """Get bitfield references."""
        return self._data["bitfields"]
    
    @property
    def signal_hierarchy(self) -> Dict[str, Any]:
        """Get signal hierarchy for UI navigation (groups and signals)."""
        return self._signal_hierarchy
    
    def get_signal(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get signal definition by name.
        
        Args:
            name: Signal name
            
        Returns:
            Signal definition dict, or None if not found
        """
        return self._flattened_signals.get(name)
    
    def signal_exists(self, name: str) -> bool:
        """Check if a signal exists in the catalog."""
        return name in self._flattened_signals

    def resolve_signal_name(self, name: str) -> str:
        """Return the signal name as-is (dot-notation canonical form)."""
        return name
    
    def operator_exists(self, op: str) -> bool:
        """Check if an operator exists in the catalog."""
        return op in self.operators
    
    def get_signal_type(self, name: str) -> Optional[str]:
        """Get signal type (bool, enum, etc.)."""
        signal = self.get_signal(name)
        return signal.get("type") if signal else None
    
    def get_signal_values(self, name: str) -> Optional[List[str]]:
        """
        Get allowed values for an enum signal.
        
        Args:
            name: Signal name
            
        Returns:
            List of allowed value strings, or None if not an enum signal
        """
        signal = self.get_signal(name)
        if not signal or signal.get("type") != "enum":
            return None
        
        values = signal.get("values", [])
        return [v["value"] for v in values if isinstance(v, dict) and "value" in v]
    
    def get_signals_by_tier(self, tier: str) -> List[str]:
        """Get list of signal names for the given UI tier (e.g. 'core', 'detail')."""
        return [
            name for name, sig in self.signals.items()
            if not name.startswith("_") and isinstance(sig, dict) and sig.get("ui", {}).get("tier") == tier
        ]

    def get_core_signals(self) -> List[str]:
        """Get list of core-tier signal names."""
        return self.get_signals_by_tier("core")

    def get_detail_signals(self) -> List[str]:
        """Get list of detail-tier signal names."""
        return self.get_signals_by_tier("detail")

    def get_signals_by_category(self, category: str) -> List[str]:
        """Get signal names filtered by UI category."""
        return [
            name for name, sig in self.signals.items()
            if sig.get("ui", {}).get("category") == category
        ]
    
    def get_all_known_events(self) -> Set[str]:
        """
        Extract all known event names from the catalog.
        
        Scans through all signals to find event names referenced in:
        - Signal derive.op == "event" (event_name field)
        - Signal sources Journal events list
        - Any recent_event references in enum values
        
        Returns:
            Set of all known event type names from the catalog
        """
        known_events = set()
        
        for signal_name, signal_def in self.signals.items():
            if not isinstance(signal_def, dict):
                continue
            
            # Check derive section for event_name
            derive = signal_def.get("derive", {})
            if isinstance(derive, dict):
                if derive.get("op") == "event":
                    event_name = derive.get("event_name")
                    if isinstance(event_name, str):
                        known_events.add(event_name)
            
            # Check sources.journal for events list
            sources = signal_def.get("sources", {})
            if isinstance(sources, dict):
                journal_source = sources.get("journal", {})
                if isinstance(journal_source, dict):
                    events = journal_source.get("events")
                    if isinstance(events, list):
                        for event in events:
                            if isinstance(event, str):
                                known_events.add(event)
            
            # Check enum values for recent_event references  
            signal_type = signal_def.get("type")
            if signal_type == "enum":
                values = signal_def.get("values", [])
                if isinstance(values, list):
                    for value_def in values:
                        if isinstance(value_def, dict):
                            recent_event = value_def.get("recent_event")
                            if isinstance(recent_event, str):
                                known_events.add(recent_event)
                
                # Also check derive cases for recent_event references
                derive = signal_def.get("derive", {})
                if isinstance(derive, dict):
                    cases = derive.get("cases", [])
                    if isinstance(cases, list):
                        for case in cases:
                            if isinstance(case, dict):
                                when = case.get("when", {})
                                if isinstance(when, dict) and when.get("op") == "recent":
                                    event_name = when.get("event_name")
                                    if isinstance(event_name, str):
                                        known_events.add(event_name)
        
        return known_events


# Maximum length for readable part of generated ID
MAX_READABLE_ID_LENGTH = 40


def generate_id_from_title(title: str, used_ids: Optional[set] = None) -> str:
    """
    Generate a deterministic, human-readable ID from a rule title.
    
    Uses slugification with numeric suffixes for collision handling.
    Based on reference implementation from catalog migration work.
    
    Args:
        title: Rule title string
        used_ids: Set of already-used IDs for collision detection
        
    Returns:
        Generated ID string (e.g., "my-rule" or "my-rule-2" if collision)
    """
    if used_ids is None:
        used_ids = set()
    
    # Slugify: lowercase, replace non-alphanumeric with hyphens
    base_id = re.sub(r'[^a-z0-9]+', '-', title.strip().lower())
    base_id = base_id.strip('-') or 'rule'
    base_id = base_id[:MAX_READABLE_ID_LENGTH].strip('-')
    
    # Handle collisions with numeric suffix
    candidate = base_id
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base_id}-{suffix}"
        suffix += 1
    
    used_ids.add(candidate)
    return candidate
