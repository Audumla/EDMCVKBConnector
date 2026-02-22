"""
Boolean coercion helpers for config values.
"""

from __future__ import annotations

from typing import Any

_TRUE_LITERALS = {"1", "true", "yes", "on", "y", "t"}
_FALSE_LITERALS = {"0", "false", "no", "off", "n", "f", ""}


def as_bool(value: Any, default: bool = False) -> bool:
    """Convert config-like values to bool with safe string handling."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_LITERALS:
            return True
        if normalized in _FALSE_LITERALS:
            return False
        return default
    if value is None:
        return default
    return bool(value)

