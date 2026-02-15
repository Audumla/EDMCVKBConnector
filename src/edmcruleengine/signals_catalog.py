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
    
    @property
    def signals(self) -> Dict[str, Any]:
        """Get all signal definitions."""
        return self._data["signals"]
    
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
    
    def get_signal(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get signal definition by name.
        
        Args:
            name: Signal name
            
        Returns:
            Signal definition dict, or None if not found
        """
        return self.signals.get(name)
    
    def signal_exists(self, name: str) -> bool:
        """Check if a signal exists in the catalog."""
        return name in self.signals
    
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
    
    def get_core_signals(self) -> List[str]:
        """Get list of core-tier signal names."""
        return [
            name for name, sig in self.signals.items()
            if not name.startswith("_") and isinstance(sig, dict) and sig.get("ui", {}).get("tier") == "core"
        ]
    
    def get_detail_signals(self) -> List[str]:
        """Get list of detail-tier signal names."""
        return [
            name for name, sig in self.signals.items()
            if not name.startswith("_") and isinstance(sig, dict) and sig.get("ui", {}).get("tier") == "detail"
        ]
    
    def get_signals_by_category(self, category: str) -> List[str]:
        """Get signal names filtered by UI category."""
        return [
            name for name, sig in self.signals.items()
            if sig.get("ui", {}).get("category") == category
        ]


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
