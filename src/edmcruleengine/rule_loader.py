"""
Rule file loading with support for v2 (old) and v3 (new) schemas.

Handles:
- Loading from file
- Detecting schema version
- Parsing both array and wrapped formats
- Providing clear error messages
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import plugin_logger

logger = plugin_logger(__name__)


class RuleLoadError(Exception):
    """Raised when rules cannot be loaded."""
    pass


def load_rules_file(path: Path) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Load rules from a JSON file.
    
    Supports:
    - v2 (old): Array of rules with when.source/event/flags structure
    - v3 (new): Array of rules with when.all/any of signal conditions
                or wrapped: { "rules": [...] }
    
    Args:
        path: Path to rules file
        
    Returns:
        Tuple of (schema_version, rules_list)
        
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
    
    # Detect format and extract rules
    rules, schema_version = _parse_rules_data(data)
    
    return schema_version, rules


def _parse_rules_data(data: Any) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse rules data and detect schema version.
    
    Args:
        data: Parsed JSON data
        
    Returns:
        Tuple of (rules_list, schema_version)
        
    Raises:
        RuleLoadError: If data format is invalid
    """
    # Handle wrapped format: { "rules": [...] }
    if isinstance(data, dict) and "rules" in data:
        rules = data["rules"]
        if not isinstance(rules, list):
            raise RuleLoadError("Wrapped format: 'rules' must be a list")
        
        # Wrapped format is always v3
        version = 3
        logger.info(f"Loaded {len(rules)} rules (wrapped format, v3 schema)")
        return rules, version
    
    # Handle array format: [ rule, rule, ... ]
    if isinstance(data, list):
        rules = data
        
        # Detect schema version by inspecting first rule
        if rules:
            version = _detect_rule_schema_version(rules[0])
            logger.info(f"Loaded {len(rules)} rules (array format, v{version} schema)")
        else:
            # Empty rules list, default to v3
            version = 3
            logger.info("Loaded 0 rules (empty list, defaulting to v3 schema)")
        
        return rules, version
    
    raise RuleLoadError(
        "Invalid rules file format. Expected array of rules or "
        "wrapped format: { \"rules\": [...] }"
    )


def _detect_rule_schema_version(rule: Dict[str, Any]) -> int:
    """
    Detect schema version from a single rule.
    
    v2 rules have:
    - when.source, when.event, when.flags, when.flags2, when.gui_focus, when.field
    
    v3 rules have:
    - when.all / when.any with signal-based conditions
    - title field (required in v3)
    
    Args:
        rule: Rule dict
        
    Returns:
        Schema version (2 or 3)
    """
    if not isinstance(rule, dict):
        # Assume v3 for non-dict (will fail validation later)
        return 3
    
    # Check for v3 indicators
    if "title" in rule:
        # v3 has required 'title' field
        return 3
    
    when = rule.get("when", {})
    if not isinstance(when, dict):
        return 3
    
    # Check for v3 structure (all/any)
    if "all" in when or "any" in when:
        # Check if conditions use signals
        all_conds = when.get("all", [])
        any_conds = when.get("any", [])
        
        for cond in all_conds + any_conds:
            if isinstance(cond, dict) and "signal" in cond:
                return 3
    
    # Check for v2 structure (source, event, flags, etc.)
    v2_keys = ["source", "event", "flags", "flags2", "gui_focus", "field"]
    if any(key in when for key in v2_keys):
        return 2
    
    # Default to v3
    return 3


def validate_rules_schema(rules: List[Dict[str, Any]], version: int) -> List[str]:
    """
    Basic validation of rules structure.
    
    Args:
        rules: List of rule dicts
        version: Schema version (2 or 3)
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"Rule at index {i}: must be a dictionary")
            continue
        
        if version == 3:
            # V3 requires 'title'
            if "title" not in rule:
                errors.append(f"Rule at index {i}: missing required 'title' field")
        else:
            # V2 requires 'id'
            if "id" not in rule:
                errors.append(f"Rule at index {i}: missing required 'id' field")
    
    return errors
