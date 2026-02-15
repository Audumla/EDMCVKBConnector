"""
Rule validation utilities for EDMC VKB Connector.

Provides validation functions for rule structures without requiring UI dependencies.
"""

from typing import Any, Dict, Tuple


def validate_rule(rule: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a rule structure.
    
    Args:
        rule: Rule dictionary to validate
        
    Returns:
        (is_valid, error_message) tuple
    """
    # Check rule ID
    rule_id = rule.get("id", "").strip()
    if not rule_id:
        return False, "Rule ID cannot be empty"
    
    # Check when clause
    when = rule.get("when")
    if when and not isinstance(when, dict):
        return False, "When clause must be a dictionary"
    
    if when:
        # Validate source if present
        source = when.get("source")
        if source and not isinstance(source, (str, list)):
            return False, "Source must be a string or list"
        
        # Validate event if present  
        event = when.get("event")
        if event and not isinstance(event, (str, list)):
            return False, "Event must be a string or list"
        
        # Validate condition blocks
        all_blocks = when.get("all", [])
        any_blocks = when.get("any", [])
        
        if not isinstance(all_blocks, list):
            return False, "ALL blocks must be a list"
        if not isinstance(any_blocks, list):
            return False, "ANY blocks must be a list"
    
    # Check then/else clauses
    for action_type in ["then", "else"]:
        actions = rule.get(action_type)
        if actions and not isinstance(actions, dict):
            return False, f"{action_type.capitalize()} clause must be a dictionary"
        
        if actions:
            # Validate shift flag actions
            for key in ["vkb_set_shift", "vkb_clear_shift"]:
                flags = actions.get(key)
                if flags and not isinstance(flags, list):
                    return False, f"{key} must be a list"
            
            # Validate log statement
            log = actions.get("log")
            if log is not None and not isinstance(log, str):
                return False, "Log statement must be a string"
    
    return True, ""
