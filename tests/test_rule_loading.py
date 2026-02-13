"""Tests for EventHandler rule file loading behavior."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

from edmcvkbconnector.config import DEFAULTS
from edmcvkbconnector.event_handler import EventHandler


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


def test_loads_default_rules_json_from_plugin_dir():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        _write_json(
            plugin_dir / "rules.json",
            [
                {
                    "id": "rule_default",
                    "enabled": True,
                    "when": {"source": "journal", "event": "Location"},
                    "then": {"log": "default"},
                }
            ],
        )
        cfg = StubConfig()
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)

        assert handler.rule_engine is not None
        assert len(handler.rule_engine.rules) == 1
        assert handler.rule_engine.rules[0]["id"] == "rule_default"
        print("[OK] Default rules.json loading passed")


def test_loads_override_rules_json_path():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        default_path = plugin_dir / "rules.json"
        override_path = plugin_dir / "rules_override.json"

        _write_json(
            default_path,
            [
                {
                    "id": "rule_default",
                    "enabled": True,
                    "when": {"source": "journal", "event": "Location"},
                    "then": {"log": "default"},
                }
            ],
        )
        _write_json(
            override_path,
            [
                {
                    "id": "rule_override",
                    "enabled": True,
                    "when": {"source": "journal", "event": "FSDJump"},
                    "then": {"log": "override"},
                }
            ],
        )
        cfg = StubConfig(rules_path=str(override_path))
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)

        assert handler.rule_engine is not None
        assert len(handler.rule_engine.rules) == 1
        assert handler.rule_engine.rules[0]["id"] == "rule_override"
        print("[OK] Override rules_path loading passed")


def test_invalid_rules_file_disables_rule_engine():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        bad_path = plugin_dir / "rules.json"
        with bad_path.open("w", encoding="utf-8") as f:
            f.write("{not-json")

        cfg = StubConfig()
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)
        assert handler.rule_engine is None
        print("[OK] Invalid rules file handling passed")


if __name__ == "__main__":
    test_loads_default_rules_json_from_plugin_dir()
    test_loads_override_rules_json_path()
    test_invalid_rules_file_disables_rule_engine()

    print("\n" + "=" * 70)
    print("[SUCCESS] Rule loading tests passed")
    print("=" * 70)
