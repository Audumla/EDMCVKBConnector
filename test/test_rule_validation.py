"""Tests for v3 rule validation."""

from pathlib import Path

from edmcruleengine.rule_validation import validate_rule
from edmcruleengine.signals_catalog import load_signals_catalog


CATALOG = load_signals_catalog(Path(__file__).resolve().parent.parent / "signals_catalog.json")


def test_valid_rule():
    rule = {
        "id": "test_rule",
        "title": "Landing Gear Down",
        "enabled": True,
        "when": {"all": [{"signal": "gear_down", "op": "eq", "value": True}]},
        "then": [{"type": "vkb_set_shift", "tokens": ["Subshift3"]}],
        "else": [{"type": "vkb_clear_shift", "tokens": ["Subshift3"]}],
    }
    is_valid, error = validate_rule(rule, CATALOG)
    assert is_valid, f"Valid rule failed validation: {error}"


def test_missing_title():
    rule = {"when": {"all": []}}
    is_valid, error = validate_rule(rule)
    assert not is_valid
    assert "title" in error


def test_invalid_when_type():
    rule = {"title": "Bad", "when": "invalid"}
    is_valid, error = validate_rule(rule)
    assert not is_valid
    assert "when" in error


def test_invalid_shift_flags():
    rule = {
        "title": "Bad Shift",
        "when": {"all": []},
        "then": [{"type": "vkb_set_shift", "tokens": [1]}],
    }
    is_valid, error = validate_rule(rule, CATALOG)
    assert not is_valid
    assert "tokens" in error


def test_minimal_rule():
    rule = {"title": "Minimal"}
    is_valid, error = validate_rule(rule)
    assert is_valid, f"Minimal rule should be valid: {error}"


def test_invalid_value_type():
    rule = {
        "title": "Bad Bool",
        "when": {"all": [{"signal": "gear_down", "op": "eq", "value": "true"}]},
    }
    is_valid, error = validate_rule(rule, CATALOG)
    assert not is_valid
    assert "boolean" in error
