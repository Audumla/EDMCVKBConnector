"""
Test the events configuration loading (no tkinter required).
"""

import json
import sys
from pathlib import Path

import pytest

# Add source paths
plugin_root = Path(__file__).parent.parent
src_path = plugin_root / "src"
sys.path.insert(0, str(src_path))


def test_events_config_file():
    """Test that events_config.json is valid and well-formed."""
    config_path = plugin_root / "events_config.json"

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    required_keys = ["sources", "events", "condition_types", "shift_flags"]
    missing = [key for key in required_keys if key not in config]
    assert not missing, f"Missing required keys: {missing}"

    assert isinstance(config["sources"], list)
    assert isinstance(config["events"], list)
    assert isinstance(config["condition_types"], list)
    assert isinstance(config["shift_flags"], list)


def test_rules_engine_imports():
    """Test that we can import FLAGS and other dicts from rules_engine."""
    from edmcruleengine.rules_engine import FLAGS, FLAGS2, GUI_FOCUS_NAME_TO_VALUE

    assert isinstance(FLAGS, dict)
    assert isinstance(FLAGS2, dict)
    assert isinstance(GUI_FOCUS_NAME_TO_VALUE, dict)


def test_sample_rule_structure():
    """Test that sample rules have the expected structure."""
    rules_path = plugin_root / "rules.json.example"

    if not rules_path.exists():
        pytest.skip(f"{rules_path} does not exist")

    with open(rules_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rules = data if isinstance(data, list) else data.get("rules", [])
    assert isinstance(rules, list)

    for rule in rules:
        assert isinstance(rule, dict)
        assert "when" in rule
        assert "then" in rule
