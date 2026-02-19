"""
Tests for load.py VKB-Link ownership shutdown behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import load as plugin_load


class DictConfig:
    def __init__(self, **values):
        self._values = dict(values)

    def get(self, key, default=None):
        return self._values.get(key, default)


def _status(*, running: bool) -> SimpleNamespace:
    return SimpleNamespace(
        running=running,
        exe_path=r"G:\Games\vkb\VKB-Link.exe",
        version="0.8.2",
        managed=False,
    )


def test_plugin_stop_does_not_stop_preexisting_vkb_link(monkeypatch):
    manager = Mock()
    manager.get_status.return_value = _status(running=True)
    manager.stop_running.return_value = SimpleNamespace(message="stopped", status=None)

    handler = Mock()
    handler.vkb_link_manager = manager

    monkeypatch.setattr(plugin_load, "_config", DictConfig(vkb_link_auto_manage=True))
    monkeypatch.setattr(plugin_load, "_event_handler", handler)
    monkeypatch.setattr(plugin_load, "_event_recorder", None)
    monkeypatch.setattr(plugin_load, "_vkb_link_started_by_plugin", False)

    plugin_load.plugin_stop()

    handler.disconnect.assert_called_once()
    manager.stop_running.assert_not_called()


def test_plugin_stop_stops_only_when_started_by_plugin(monkeypatch):
    manager = Mock()
    manager.get_status.return_value = _status(running=True)
    manager.stop_running.return_value = SimpleNamespace(message="stopped", status=None)

    handler = Mock()
    handler.vkb_link_manager = manager

    monkeypatch.setattr(plugin_load, "_config", DictConfig(vkb_link_auto_manage=False))
    monkeypatch.setattr(plugin_load, "_event_handler", handler)
    monkeypatch.setattr(plugin_load, "_event_recorder", None)
    monkeypatch.setattr(plugin_load, "_vkb_link_started_by_plugin", True)

    plugin_load.plugin_stop()

    handler.disconnect.assert_called_once()
    manager.stop_running.assert_called_once_with(reason="plugin_shutdown")
