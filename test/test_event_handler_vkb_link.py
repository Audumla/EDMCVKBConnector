"""
Tests for EventHandler VKB-Link control paths used by the preferences UI.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from edmcruleengine.config import DEFAULTS
from edmcruleengine.event_handler import EventHandler
from edmcruleengine.vkb_link_manager import VKBLinkProcessInfo


class DictConfig:
    def __init__(self, **overrides):
        self.values = dict(DEFAULTS)
        self.values.update(overrides)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


def _make_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **overrides):
    cfg = DictConfig(**overrides)
    # Keep unit tests focused on endpoint-change flow.
    monkeypatch.setattr(EventHandler, "_load_catalog", lambda self: None)
    monkeypatch.setattr(EventHandler, "_load_rules", lambda self: None)
    handler = EventHandler(cfg, plugin_dir=str(tmp_path))
    return handler, cfg


def test_apply_endpoint_change_restarts_and_reconnects(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)

    exe_path = str(tmp_path / "managed" / "VKB-Link.exe")
    ini_path = tmp_path / "managed" / "VKB-Link.ini"
    process = VKBLinkProcessInfo(pid=1234, exe_path=exe_path)

    manager = Mock()
    manager._find_running_process.return_value = process
    manager._stop_process.return_value = True
    manager._resolve_known_exe_path.return_value = exe_path
    manager._resolve_or_default_ini_path.return_value = ini_path
    manager._start_process.return_value = True
    manager._write_ini = Mock()
    handler.vkb_link_manager = manager

    delay_mock = Mock()
    monkeypatch.setattr(handler, "_apply_post_start_delay", delay_mock)
    ready_mock = Mock(return_value=True)
    monkeypatch.setattr(handler, "_wait_for_vkb_listener_ready", ready_mock)
    handler.vkb_client.set_on_connected = Mock()
    handler.vkb_client.connect = Mock(return_value=True)

    handler._apply_endpoint_change("127.0.0.1", 60001)

    manager._stop_process.assert_called_once_with(process)
    manager._resolve_or_default_ini_path.assert_called_once_with(exe_path)
    manager._write_ini.assert_called_once_with(ini_path, "127.0.0.1", 60001)
    manager._start_process.assert_called_once_with(exe_path)
    delay_mock.assert_called_once_with(
        "restarted",
        delay_seconds=cfg.get("vkb_link_warmup_delay_seconds"),
        countdown=False,
    )
    ready_mock.assert_called_once_with("127.0.0.1", 60001)
    handler.vkb_client.set_on_connected.assert_called_once()
    handler.vkb_client.connect.assert_called_once()

    assert cfg.get("vkb_ini_path") == str(ini_path)
    assert cfg.get("vkb_host") == "127.0.0.1"
    assert cfg.get("vkb_port") == 60001
    assert handler.vkb_client.host == "127.0.0.1"
    assert handler.vkb_client.port == 60001
    assert handler.get_connection_status_override() is None
    assert handler._endpoint_change_active is False


def test_apply_endpoint_change_starts_when_not_running(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)

    exe_path = str(tmp_path / "managed" / "VKB-Link.exe")
    ini_path = tmp_path / "managed" / "VKBLink.ini"

    manager = Mock()
    manager._find_running_process.return_value = None
    manager._resolve_known_exe_path.return_value = exe_path
    manager._resolve_or_default_ini_path.return_value = ini_path
    manager._start_process.return_value = True
    manager._write_ini = Mock()
    handler.vkb_link_manager = manager

    monkeypatch.setattr(handler, "_apply_post_start_delay", Mock())
    monkeypatch.setattr(handler, "_wait_for_vkb_listener_ready", Mock(return_value=True))
    handler.vkb_client.connect = Mock(return_value=False)
    handler.vkb_client.set_on_connected = Mock()

    handler._apply_endpoint_change("127.0.0.1", 60002)

    manager._stop_process.assert_not_called()
    manager._write_ini.assert_called_once_with(ini_path, "127.0.0.1", 60002)
    manager._start_process.assert_called_once_with(exe_path)
    assert cfg.get("vkb_port") == 60002
    assert handler.vkb_client.port == 60002
    assert handler._endpoint_change_active is False


def test_apply_endpoint_change_does_not_connect_when_start_fails(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)

    exe_path = str(tmp_path / "managed" / "VKB-Link.exe")
    ini_path = tmp_path / "managed" / "VKBLink.ini"
    process = VKBLinkProcessInfo(pid=99, exe_path=exe_path)

    manager = Mock()
    manager._find_running_process.return_value = process
    manager._stop_process.return_value = True
    manager._resolve_known_exe_path.return_value = exe_path
    manager._resolve_or_default_ini_path.return_value = ini_path
    manager._start_process.return_value = False
    manager._write_ini = Mock()
    handler.vkb_link_manager = manager

    handler.vkb_client.connect = Mock(return_value=True)
    handler.vkb_client.set_on_connected = Mock()
    monkeypatch.setattr(handler, "_apply_post_start_delay", Mock())
    monkeypatch.setattr(handler, "_wait_for_vkb_listener_ready", Mock(return_value=True))

    handler._apply_endpoint_change("10.0.0.5", 60003)

    handler.vkb_client.connect.assert_not_called()
    assert cfg.get("vkb_host") == "10.0.0.5"
    assert cfg.get("vkb_port") == 60003
    assert handler.vkb_client.host == "10.0.0.5"
    assert handler.vkb_client.port == 60003
    assert handler.get_connection_status_override() is None
    assert handler._endpoint_change_active is False


def test_apply_endpoint_change_handles_missing_manager(tmp_path, monkeypatch):
    handler, _ = _make_handler(tmp_path, monkeypatch)
    handler.vkb_link_manager = None

    handler.set_connection_status_override("Restarting VKB-Link...")
    handler._apply_endpoint_change("127.0.0.1", 60010)

    assert handler.get_connection_status_override() is None
    assert handler._endpoint_change_active is False


def test_recovery_suppressed_for_send_failed_before_first_connection(tmp_path, monkeypatch):
    handler, _ = _make_handler(tmp_path, monkeypatch)
    manager = Mock()
    manager.ensure_running = Mock()
    handler.vkb_link_manager = manager

    handler._has_successful_vkb_connection = False
    handler._attempt_vkb_link_recovery(reason="send_failed")

    manager.ensure_running.assert_not_called()
