"""
Rule file loading for EDMC VKB Connector.

Handles:
- Loading from file
- Parsing both array and wrapped formats
- Providing clear error messages
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from . import plugin_logger

logger = plugin_logger(__name__)


class RuleLoadError(Exception):
    """Raised when rules cannot be loaded."""
    pass


def load_rules_file(path: Path) -> List[Dict[str, Any]]:
    """
    Load rules from a JSON file.
    
    Supports:
    - Array format: [ rule, rule, ... ]
    - Wrapped format: { "rules": [ rule, rule, ... ] }
    
    Args:
        path: Path to rules file
        
    Returns:
        List of rule dicts
        
    Raises:
        RuleLoadError: If file cannot be loaded or parsed
    """
    if not path.exists():
        raise RuleLoadError(f"Rules file not found: {path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuleLoadError(f"Invalid JSON in rules file: {e}")
    except Exception as e:
        raise RuleLoadError(f"Failed to read rules file: {e}")
    
    # Parse rules data
    rules = _parse_rules_data(data)
    
    logger.info(f"Loaded {len(rules)} rules from {path}")
    
    return rules


def _parse_rules_data(data: Any) -> List[Dict[str, Any]]:
    """
    Parse rules data from JSON.
    
    Args:
        data: Parsed JSON data
        
    Returns:
        List of rule dicts
        
    Raises:
        RuleLoadError: If data format is invalid
    """
    # Handle wrapped format: { "rules": [...] }
    if isinstance(data, dict) and "rules" in data:
        rules = data["rules"]
        if not isinstance(rules, list):
            raise RuleLoadError("Wrapped format: 'rules' must be a list")
        return rules
    
    # Handle array format: [ rule, rule, ... ]
    if isinstance(data, list):
        return data
    
    raise RuleLoadError(
        "Invalid rules file format. Expected array of rules or "
        "wrapped format: { \"rules\": [...] }"
    )
