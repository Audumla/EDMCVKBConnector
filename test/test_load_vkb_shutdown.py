"""
Tests for load.py VKB-Link ownership shutdown behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import edmcruleengine
import edmcruleengine.event_recorder as event_recorder_module
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
    handler.clear_shift_state_for_shutdown = Mock(return_value=True)

    monkeypatch.setattr(plugin_load, "_config", DictConfig(vkb_link_auto_manage=True))
    monkeypatch.setattr(plugin_load, "_event_handler", handler)
    monkeypatch.setattr(plugin_load, "_event_recorder", None)
    monkeypatch.setattr(plugin_load, "_vkb_link_started_by_plugin", False)

    plugin_load.plugin_stop()

    handler.clear_shift_state_for_shutdown.assert_called_once()
    handler.disconnect.assert_called_once()
    manager.stop_running.assert_not_called()


def test_plugin_stop_stops_only_when_started_by_plugin(monkeypatch):
    manager = Mock()
    manager.get_status.return_value = _status(running=True)
    manager.stop_running.return_value = SimpleNamespace(message="stopped", status=None)

    handler = Mock()
    handler.vkb_link_manager = manager
    handler.clear_shift_state_for_shutdown = Mock(return_value=True)

    monkeypatch.setattr(plugin_load, "_config", DictConfig(vkb_link_auto_manage=False))
    monkeypatch.setattr(plugin_load, "_event_handler", handler)
    monkeypatch.setattr(plugin_load, "_event_recorder", None)
    monkeypatch.setattr(plugin_load, "_vkb_link_started_by_plugin", True)

    plugin_load.plugin_stop()

    handler.clear_shift_state_for_shutdown.assert_called_once()
    handler.disconnect.assert_called_once()
    manager.stop_running.assert_called_once_with(reason="plugin_shutdown")


def test_plugin_start_skips_ensure_running_when_auto_manage_disabled_string(monkeypatch, tmp_path):
    manager = Mock()
    manager.get_status.return_value = SimpleNamespace(
        running=False,
        exe_path=None,
        install_dir=None,
        version=None,
        managed=False,
    )
    manager.ensure_running = Mock(
        return_value=SimpleNamespace(
            success=True,
            message="VKB-Link started",
            action_taken="started",
            status=manager.get_status.return_value,
        )
    )

    class FakeConfig:
        def get(self, key, default=None):
            values = {
                "vkb_link_auto_manage": "false",
                "vkb_host": "127.0.0.1",
                "vkb_port": 50995,
            }
            return values.get(key, default)

    class FakeHandler:
        def __init__(self, *_args, **_kwargs):
            self.vkb_link_manager = manager

        def refresh_unregistered_events_against_catalog(self):
            return 0

        def set_connection_status_override(self, _status):
            return None

        def connect(self):
            return False

    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, **_thread_kwargs):
            self._target = target
            self._args = args
            self._kwargs = kwargs or {}

        def start(self):
            if self._target:
                self._target(*self._args, **self._kwargs)

        def join(self, timeout=None):
            return None

    monkeypatch.setattr(edmcruleengine, "Config", FakeConfig)
    monkeypatch.setattr(edmcruleengine, "EventHandler", FakeHandler)
    monkeypatch.setattr(event_recorder_module, "EventRecorder", lambda: object())
    monkeypatch.setattr(plugin_load, "_ensure_rules_file_exists", lambda _plugin_dir: None)
    monkeypatch.setattr(plugin_load, "_restore_test_shift_state_from_config", lambda: None)
    monkeypatch.setattr("threading.Thread", ImmediateThread)

    result = plugin_load.plugin_start3(str(tmp_path))

    assert result == "VKB Connector"
    manager.ensure_running.assert_not_called()
