"""Tests for EventHandler rule + catalog file loading behavior."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

from edmcruleengine.config import DEFAULTS
from edmcruleengine.event_handler import EventHandler


ROOT = Path(__file__).resolve().parent.parent
CATALOG_SOURCE = ROOT / "signals_catalog.json"


class StubConfig:
    """Minimal config stub for deterministic file-loading tests."""

    def __init__(self, **overrides):
        self._values = dict(DEFAULTS)
        self._values.update(overrides)

    def get(self, key, default=None):
        return self._values.get(key, default)


def _write_json(path: Path, payload) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f)


def _write_catalog(plugin_dir: Path) -> None:
    plugin_dir.joinpath("signals_catalog.json").write_text(
        CATALOG_SOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def test_loads_default_rules_json_from_plugin_dir():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        _write_catalog(plugin_dir)
        _write_json(
            plugin_dir / "rules.json",
            [
                {
                    "id": "rule_default",
                    "title": "Rule Default",
                    "enabled": True,
                    "when": {"all": [{"signal": "gear_down", "op": "eq", "value": True}]},
                    "then": [{"type": "log", "message": "default"}],
                }
            ],
        )
        cfg = StubConfig()
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)

        assert handler.rule_engine is not None
        assert len(handler.rule_engine.rules) == 1
        assert handler.rule_engine.rules[0]["id"] == "rule_default"


def test_loads_override_rules_json_path():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        default_path = plugin_dir / "rules.json"
        override_path = plugin_dir / "rules_override.json"
        _write_catalog(plugin_dir)

        _write_json(
            default_path,
            [
                {
                    "id": "rule_default",
                    "title": "Rule Default",
                    "when": {"all": [{"signal": "gear_down", "op": "eq", "value": True}]},
                    "then": [{"type": "log", "message": "default"}],
                }
            ],
        )
        _write_json(
            override_path,
            [
                {
                    "id": "rule_override",
                    "title": "Rule Override",
                    "when": {"all": [{"signal": "hardpoints", "op": "eq", "value": "deployed"}]},
                    "then": [{"type": "log", "message": "override"}],
                }
            ],
        )
        cfg = StubConfig(rules_path=str(override_path))
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)

        assert handler.rule_engine is not None
        assert len(handler.rule_engine.rules) == 1
        assert handler.rule_engine.rules[0]["id"] == "rule_override"


def test_invalid_rules_file_disables_rule_engine():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        bad_path = plugin_dir / "rules.json"
        _write_catalog(plugin_dir)
        with bad_path.open("w", encoding="utf-8") as f:
            f.write("{not-json")

        cfg = StubConfig()
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)
        assert handler.rule_engine is None
