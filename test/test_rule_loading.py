"""Tests for EventHandler rule file loading behavior."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

from edmcruleengine.config import DEFAULTS
from edmcruleengine.event_handler import EventHandler


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


def _copy_catalog_to_plugin_dir(plugin_dir: Path) -> None:
    """Copy signals catalog to plugin directory for tests."""
    # Find catalog in repository root
    repo_root = Path(__file__).parent.parent
    catalog_src = repo_root / "signals_catalog.json"
    catalog_dst = plugin_dir / "signals_catalog.json"
    shutil.copy(catalog_src, catalog_dst)


def test_loads_default_rules_json_from_plugin_dir():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        
        # Copy catalog
        _copy_catalog_to_plugin_dir(plugin_dir)
        
        # Write rules
        _write_json(
            plugin_dir / "rules.json",
            [
                {
                    "title": "Test Rule",
                    "enabled": True,
                    "when": {
                        "all": [
                            {"signal": "docked", "op": "eq", "value": True}
                        ]
                    },
                    "then": [{"log": "Docked"}],
                }
            ],
        )
        cfg = StubConfig()
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)

        assert handler.rule_engine is not None
        assert len(handler.rule_engine.rules) == 1
        # Rules auto-generate ID from title
        print("[OK] Default rules.json loading passed")


def test_loads_override_rules_json_path():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        default_path = plugin_dir / "rules.json"
        override_path = plugin_dir / "rules_override.json"

        # Copy catalog
        _copy_catalog_to_plugin_dir(plugin_dir)

        # Write rules to both paths
        _write_json(
            default_path,
            [
                {
                    "title": "Default Rule",
                    "enabled": True,
                    "when": {
                        "all": [
                            {"signal": "docked", "op": "eq", "value": True}
                        ]
                    },
                    "then": [{"log": "default"}],
                }
            ],
        )
        _write_json(
            override_path,
            [
                {
                    "title": "Override Rule",
                    "enabled": True,
                    "when": {
                        "all": [
                            {"signal": "in_supercruise", "op": "eq", "value": True}
                        ]
                    },
                    "then": [{"log": "override"}],
                }
            ],
        )
        cfg = StubConfig(rules_path=str(override_path))
        handler = EventHandler(cfg, plugin_dir=str(plugin_dir))
        handler.vkb_client.send_event = Mock(return_value=True)

        assert handler.rule_engine is not None
        assert len(handler.rule_engine.rules) == 1
        # Rules auto-generate ID from title (human-readable slug)
        assert handler.rule_engine.rules[0]["id"] == "override-rule"
        print("[OK] Override rules_path loading passed")


def test_invalid_rules_file_disables_rule_engine():
    with tempfile.TemporaryDirectory() as td:
        plugin_dir = Path(td)
        bad_path = plugin_dir / "rules.json"
        
        # Copy catalog
        _copy_catalog_to_plugin_dir(plugin_dir)
        
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

