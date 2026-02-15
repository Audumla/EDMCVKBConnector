"""Focused tests for v3 catalog-backed rules."""

import json
import tempfile
from pathlib import Path

from edmcruleengine.config import DEFAULTS
from edmcruleengine.event_handler import EventHandler
from edmcruleengine.rules_engine import DashboardRuleEngine, parse_rules_payload
from edmcruleengine.signals_catalog import load_signals_catalog


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "signals_catalog.json"


class StubConfig:
    def __init__(self, **overrides):
        self._values = dict(DEFAULTS)
        self._values.update(overrides)

    def get(self, key, default=None):
        return self._values.get(key, default)


def _catalog():
    return load_signals_catalog(CATALOG_PATH)


def test_supports_both_rules_file_shapes():
    as_array = [{"title": "A", "when": {"all": []}}]
    as_wrapped = {"rules": [{"title": "A", "when": {"all": []}}]}
    left = parse_rules_payload(as_array)
    right = parse_rules_payload(as_wrapped)
    assert left == right


def test_defaults_and_deterministic_ids_with_collisions():
    rules = [{"title": "Same Title"}, {"title": "Same Title"}]
    engine = DashboardRuleEngine(rules, catalog=_catalog(), action_handler=lambda _: None)
    assert engine.rules[0]["id"] == "same-title"
    assert engine.rules[1]["id"] == "same-title-2"
    assert engine.rules[0]["enabled"] is True
    assert engine.rules[0]["when"] == {"all": [], "any": []}
    assert engine.rules[0]["then"] == []
    assert engine.rules[0]["else"] == []


def test_condition_validation_uses_catalog_signal_types():
    bad = [
        {
            "title": "Bad Bool",
            "when": {"all": [{"signal": "gear_down", "op": "eq", "value": "true"}]},
        }
    ]
    try:
        DashboardRuleEngine(bad, catalog=_catalog(), action_handler=lambda _: None)
        assert False, "expected validation error"
    except ValueError as exc:
        assert "requires boolean value" in str(exc)

    bad_enum = [
        {
            "title": "Bad Enum",
            "when": {"all": [{"signal": "gui_focus", "op": "eq", "value": "NotAValue"}]},
        }
    ]
    try:
        DashboardRuleEngine(bad_enum, catalog=_catalog(), action_handler=lambda _: None)
        assert False, "expected validation error"
    except ValueError as exc:
        assert "must be one of" in str(exc)


def test_edge_triggered_no_spam_and_action_order():
    seen = []
    rules = [
        {
            "title": "Gear Rule",
            "when": {"all": [{"signal": "gear_down", "op": "eq", "value": True}]},
            "then": [
                {"type": "log", "message": "one"},
                {"type": "vkb_set_shift", "tokens": ["Subshift3"]},
            ],
            "else": [{"type": "vkb_clear_shift", "tokens": ["Subshift3"]}],
        }
    ]
    engine = DashboardRuleEngine(rules, catalog=_catalog(), action_handler=lambda result: seen.append(result))

    up = {"dashboard": {"Flags": 0, "Flags2": 0, "GuiFocus": 0}}
    down = {"dashboard": {"Flags": (1 << 2), "Flags2": 0, "GuiFocus": 0}}

    engine.on_notification("cmdr", False, "dashboard", "Status", up)
    engine.on_notification("cmdr", False, "dashboard", "Status", down)
    engine.on_notification("cmdr", False, "dashboard", "Status", down)
    engine.on_notification("cmdr", False, "dashboard", "Status", up)

    assert len(seen) == 2
    assert [a["type"] for a in seen[0].actions] == ["log", "vkb_set_shift"]
    assert seen[0].outcome == "match"
    assert seen[1].outcome == "no_match"


def test_event_handler_fails_clearly_without_catalog():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        (plugin_dir / "rules.json").write_text(json.dumps([{"title": "A"}]), encoding="utf-8")
        cfg = StubConfig()
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        assert handler.rule_engine is None
