"""Comprehensive v3 rules tests using file-backed fixtures."""

import json
from pathlib import Path
from unittest.mock import Mock

from edmcruleengine.config import DEFAULTS
from edmcruleengine.event_handler import EventHandler
from edmcruleengine.rules_engine import DashboardRuleEngine, RuleMatchResult
from edmcruleengine.signals_catalog import derive_signal_values, load_signals_catalog


FIXTURES_DIR = Path(__file__).parent / "fixtures"
RULES_FILE = FIXTURES_DIR / "rules_comprehensive.json"
PAYLOADS_FILE = FIXTURES_DIR / "edmc_notifications.json"
CATALOG_FILE = FIXTURES_DIR / "signals_catalog.json"


class StubConfig:
    def __init__(self, **overrides):
        self._values = dict(DEFAULTS)
        self._values.update(overrides)

    def get(self, key, default=None):
        return self._values.get(key, default)


def load_rules(path: Path = RULES_FILE):
    return json.loads(path.read_text(encoding="utf-8"))


def load_payloads(path: Path = PAYLOADS_FILE):
    return json.loads(path.read_text(encoding="utf-8"))


def payload(group: str, name: str) -> dict:
    return dict(load_payloads()[group][name])


def create_handler_with_fixture_rules():
    cfg = StubConfig(
        rules_path=str(RULES_FILE),
        signals_catalog_path=str(CATALOG_FILE),
        event_types=[],
    )
    handler = EventHandler(cfg, plugin_dir=str(FIXTURES_DIR))
    handler.vkb_client.send_event = Mock(return_value=True)
    handler.vkb_client.connect = Mock(return_value=False)
    return handler


def _evaluate_once(rule_id: str, entry: dict) -> RuleMatchResult:
    catalog = load_signals_catalog(CATALOG_FILE)
    rules = load_rules()
    target = next(r for r in rules if r["id"] == rule_id)
    engine = DashboardRuleEngine([target], catalog=catalog, action_handler=lambda _: None)
    signal_values = derive_signal_values(catalog, entry)
    return RuleMatchResult.MATCH if engine._rule_matches(engine.rules[0], signal_values) else RuleMatchResult.NO_MATCH


def test_positive_rules():
    assert _evaluate_once("hardpoints_shift", payload("status_dashboard", "hardpoints_only")) == RuleMatchResult.MATCH
    assert _evaluate_once("map_focus_shift", payload("status_dashboard", "galaxy_map")) == RuleMatchResult.MATCH
    assert _evaluate_once("gear_down_shift", {"event": "Status", "Flags": 4, "Flags2": 0, "GuiFocus": 0}) == RuleMatchResult.MATCH


def test_negative_rule_outcomes():
    assert _evaluate_once("hardpoints_shift", payload("status_dashboard", "neutral")) == RuleMatchResult.NO_MATCH
    assert _evaluate_once("map_focus_shift", payload("status_dashboard", "neutral")) == RuleMatchResult.NO_MATCH
    assert _evaluate_once("gear_down_shift", {"event": "Status", "Flags": 0, "Flags2": 0, "GuiFocus": 0}) == RuleMatchResult.NO_MATCH


def test_state_transition_rules_for_status_stream():
    handler = create_handler_with_fixture_rules()

    handler.handle_event("Status", payload("status_dashboard", "neutral"), source="dashboard", cmdr="TestCmdr", is_beta=False)
    assert handler._shift_bitmap == 0
    assert handler._subshift_bitmap == 0

    handler.handle_event("Status", payload("status_dashboard", "hardpoints_only"), source="dashboard", cmdr="TestCmdr", is_beta=False)
    assert handler._shift_bitmap & 0b00000001 == 0b00000001

    handler.handle_event("Status", payload("status_dashboard", "galaxy_map"), source="dashboard", cmdr="TestCmdr", is_beta=False)
    assert handler._shift_bitmap & 0b00000010 == 0b00000010

    handler.handle_event("Status", {"event": "Status", "Flags": 4, "Flags2": 0, "GuiFocus": 0}, source="dashboard", cmdr="TestCmdr", is_beta=False)
    assert handler._subshift_bitmap & 0b00000100 == 0b00000100


def test_edge_trigger_no_spam_invariant():
    calls = []
    catalog = load_signals_catalog(CATALOG_FILE)
    rules = [
        {
            "id": "spam-check",
            "title": "Spam Check",
            "when": {"all": [{"signal": "hardpoints", "op": "eq", "value": "deployed"}]},
            "then": [{"type": "log", "message": "on"}],
            "else": [{"type": "log", "message": "off"}],
        }
    ]
    engine = DashboardRuleEngine(rules, catalog=catalog, action_handler=lambda result: calls.append(result))

    neutral = payload("status_dashboard", "neutral")
    hardpoints = payload("status_dashboard", "hardpoints_only")

    engine.on_notification("Cmdr", False, "dashboard", "Status", neutral)
    engine.on_notification("Cmdr", False, "dashboard", "Status", hardpoints)
    engine.on_notification("Cmdr", False, "dashboard", "Status", hardpoints)
    engine.on_notification("Cmdr", False, "dashboard", "Status", neutral)
    engine.on_notification("Cmdr", False, "dashboard", "Status", neutral)

    assert len(calls) == 2
    assert calls[0].outcome == RuleMatchResult.MATCH
    assert calls[1].outcome == RuleMatchResult.NO_MATCH


def test_rules_file_loading_logic():
    handler = create_handler_with_fixture_rules()
    assert handler.rule_engine is not None
    assert len(handler.rule_engine.rules) == 3
    handler.reload_rules()
    assert handler.rule_engine is not None
