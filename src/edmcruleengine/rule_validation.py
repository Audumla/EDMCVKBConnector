"""Rule validation utilities for v3 catalog-based rules."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .rules_engine import normalize_and_validate_rules


def validate_rule(rule: Dict[str, Any], catalog: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Validate a single v3 rule.

    If a catalog is provided, condition values are fully validated against
    signal/operator definitions. Without a catalog, only structural validation
    is performed.
    """
    if not isinstance(rule, dict):
        return False, "Rule must be an object"

    if catalog is None:
        title = rule.get("title")
        if not isinstance(title, str) or not title.strip():
            return False, "title is required"

        when = rule.get("when", {"all": []})
        if not isinstance(when, dict):
            return False, "when must be an object"
        if "all" in when and not isinstance(when.get("all"), list):
            return False, "when.all must be a list"
        if "any" in when and not isinstance(when.get("any"), list):
            return False, "when.any must be a list"

        for branch in ("then", "else"):
            block = rule.get(branch, [])
            if block is None:
                continue
            if not isinstance(block, (list, dict)):
                return False, f"{branch} must be a list of action objects"
        return True, ""

    try:
        normalize_and_validate_rules([rule], catalog)
    except Exception as exc:
        return False, str(exc)
    return True, ""
