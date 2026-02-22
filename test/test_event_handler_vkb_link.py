"""
Tests for EventHandler VKB-Link control paths used by the preferences UI.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from edmcruleengine.config import DEFAULTS
from edmcruleengine.event_handler import EventHandler
from edmcruleengine.vkb_link_manager import VKBLinkManager


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
    monkeypatch.setattr(VKBLinkManager, "start_process_health_monitor", lambda self, on_process_crash: None)
    monkeypatch.setattr(VKBLinkManager, "stop_process_health_monitor", lambda self: None)
    handler = EventHandler(cfg, plugin_dir=str(tmp_path))
    return handler, cfg


def test_apply_endpoint_change_restarts_and_reconnects(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)

    manager = Mock()
    manager.apply_managed_endpoint_change.return_value = Mock(
        success=True,
        message="VKB-Link restarted with updated endpoint",
        action_taken="restarted",
    )
    manager.should_probe_listener_before_connect.return_value = False
    handler.vkb_link_manager = manager

    ready_mock = Mock(return_value=True)
    manager.wait_for_listener_ready = ready_mock
    handler.vkb_client.set_on_connected = Mock()
    handler.vkb_client.connect = Mock(return_value=True)

    handler._apply_endpoint_change("127.0.0.1", 60001)

    manager.apply_managed_endpoint_change.assert_called_once_with(
        host="127.0.0.1",
        port=60001,
        reason="endpoint_change",
    )
    ready_mock.assert_not_called()
    handler.vkb_client.set_on_connected.assert_called_once()
    handler.vkb_client.connect.assert_called_once()

    assert cfg.get("vkb_host") == "127.0.0.1"
    assert cfg.get("vkb_port") == 60001
    assert handler.vkb_client.host == "127.0.0.1"
    assert handler.vkb_client.port == 60001
    assert handler.get_connection_status_override() is None
    assert handler._endpoint_change_active is False


def test_apply_endpoint_change_starts_when_not_running(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)

    manager = Mock()
    manager.apply_managed_endpoint_change.return_value = Mock(
        success=True,
        message="VKB-Link started with updated endpoint",
        action_taken="started",
    )
    manager.should_probe_listener_before_connect.return_value = False
    handler.vkb_link_manager = manager

    manager.wait_for_listener_ready = Mock(return_value=True)
    handler.vkb_client.connect = Mock(return_value=False)
    handler.vkb_client.set_on_connected = Mock()

    handler._apply_endpoint_change("127.0.0.1", 60002)

    manager.apply_managed_endpoint_change.assert_called_once_with(
        host="127.0.0.1",
        port=60002,
        reason="endpoint_change",
    )
    assert cfg.get("vkb_port") == 60002
    assert handler.vkb_client.port == 60002
    assert handler._endpoint_change_active is False


def test_apply_endpoint_change_does_not_connect_when_start_fails(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)

    manager = Mock()
    manager.apply_managed_endpoint_change.return_value = Mock(
        success=False,
        message="Failed to restart VKB-Link after endpoint update",
        action_taken="none",
    )
    manager.should_probe_listener_before_connect.return_value = False
    handler.vkb_link_manager = manager

    handler.vkb_client.connect = Mock(return_value=True)
    handler.vkb_client.set_on_connected = Mock()
    manager.wait_for_listener_ready = Mock(return_value=True)

    handler._apply_endpoint_change("10.0.0.5", 60003)

    manager.apply_managed_endpoint_change.assert_called_once_with(
        host="10.0.0.5",
        port=60003,
        reason="endpoint_change",
    )
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


def test_recovery_ignores_non_process_reasons(tmp_path, monkeypatch):
    handler, _ = _make_handler(tmp_path, monkeypatch)
    manager = Mock()
    manager.ensure_running = Mock()
    handler.vkb_link_manager = manager

    handler._attempt_vkb_link_recovery(reason="connect_failed")

    manager.ensure_running.assert_not_called()


def test_connect_ensures_vkb_process_before_socket_connect(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    cfg.set("vkb_host", "127.0.0.1")
    cfg.set("vkb_port", 60020)

    manager = Mock()
    manager.get_status.return_value = Mock(running=False, exe_path=r"G:\Games\vkb\VKB-Link.exe")
    manager.ensure_running.return_value = Mock(success=True, message="VKB-Link started")
    manager.wait_for_post_start_settle = Mock()
    manager.should_probe_listener_before_connect.return_value = False
    handler.vkb_link_manager = manager

    manager.wait_for_listener_ready = Mock(return_value=True)
    handler.vkb_client.connect = Mock(return_value=True)
    handler.vkb_client.set_on_connected = Mock()

    assert handler.connect() is True
    manager.ensure_running.assert_called_once_with(host="127.0.0.1", port=60020, reason="connect")
    manager.wait_for_post_start_settle.assert_called_once()
    handler.vkb_client.connect.assert_called_once()


def test_connect_aborts_when_not_running_and_auto_manage_disabled(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch, vkb_link_auto_manage=False)
    cfg.set("vkb_host", "127.0.0.1")
    cfg.set("vkb_port", 60021)

    manager = Mock()
    manager.get_status.return_value = Mock(running=False, exe_path=None)
    handler.vkb_link_manager = manager

    handler.vkb_client.connect = Mock(return_value=True)
    handler.vkb_client.set_on_connected = Mock()

    assert handler.connect() is False
    handler.vkb_client.connect.assert_not_called()


def test_connect_aborts_when_not_running_and_auto_manage_disabled_even_with_known_exe(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch, vkb_link_auto_manage=False)
    cfg.set("vkb_host", "127.0.0.1")
    cfg.set("vkb_port", 60024)

    manager = Mock()
    manager.get_status.return_value = Mock(running=False, exe_path=r"G:\Games\vkb\VKB-Link.exe")
    manager.ensure_running = Mock(return_value=Mock(success=True, message="started"))
    handler.vkb_link_manager = manager

    handler.vkb_client.connect = Mock(return_value=True)
    handler.vkb_client.set_on_connected = Mock()

    assert handler.connect() is False
    manager.ensure_running.assert_not_called()
    handler.vkb_client.connect.assert_not_called()


def test_recovery_waits_for_post_start_settle_before_listener_probe(tmp_path, monkeypatch):
    handler, cfg = _make_handler(
        tmp_path,
        monkeypatch,
        vkb_link_probe_listener_before_connect=True,
    )
    cfg.set("vkb_host", "127.0.0.1")
    cfg.set("vkb_port", 60022)

    class ImmediateThread:
        def __init__(self, *, target, daemon=False):  # noqa: ARG002
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr("edmcruleengine.event_handler.threading.Thread", ImmediateThread)

    manager = Mock()
    manager.ensure_running.return_value = Mock(success=True, message="VKB-Link started")
    manager.wait_for_post_start_settle = Mock()
    manager.should_probe_listener_before_connect.return_value = True
    handler.vkb_link_manager = manager
    handler._has_successful_vkb_connection = True

    ready_mock = Mock(return_value=True)
    manager.wait_for_listener_ready = ready_mock
    handler.vkb_client.set_on_connected = Mock()
    handler.vkb_client.connect = Mock(return_value=True)

    handler._attempt_vkb_link_recovery(reason="process_crash_detected")

    manager.ensure_running.assert_called_once_with(
        host="127.0.0.1",
        port=60022,
        reason="process_crash_detected",
    )
    manager.wait_for_post_start_settle.assert_called_once()
    ready_mock.assert_called_once_with("127.0.0.1", 60022)
    handler.vkb_client.connect.assert_called_once()


def test_connect_does_not_probe_listener_by_default(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    cfg.set("vkb_host", "127.0.0.1")
    cfg.set("vkb_port", 60023)

    manager = Mock()
    manager.get_status.return_value = Mock(running=True, exe_path=r"G:\Games\vkb\VKB-Link.exe")
    manager.wait_for_post_start_settle = Mock()
    manager.should_probe_listener_before_connect.return_value = False
    handler.vkb_link_manager = manager

    ready_mock = Mock(return_value=True)
    manager.wait_for_listener_ready = ready_mock
    handler.vkb_client.connect = Mock(return_value=True)
    handler.vkb_client.set_on_connected = Mock()

    assert handler.connect() is True
    ready_mock.assert_not_called()
    handler.vkb_client.connect.assert_called_once()


def test_clear_shift_state_for_shutdown_sends_zero_without_recovery(tmp_path, monkeypatch):
    handler, _ = _make_handler(tmp_path, monkeypatch)
    handler._shift_bitmap = 0x03
    handler._subshift_bitmap = 0x04
    handler.vkb_client.send_event = Mock(return_value=True)
    recovery_mock = Mock()
    monkeypatch.setattr(handler, "_attempt_vkb_link_recovery", recovery_mock)

    assert handler.clear_shift_state_for_shutdown() is True
    handler.vkb_client.send_event.assert_called_once_with(
        "VKBShiftBitmap",
        {"shift": 0, "subshift": 0},
    )
    recovery_mock.assert_not_called()


def test_clear_shift_state_for_shutdown_send_failure_skips_recovery(tmp_path, monkeypatch):
    handler, _ = _make_handler(tmp_path, monkeypatch)
    handler._shift_bitmap = 0x02
    handler._subshift_bitmap = 0x01
    handler.vkb_client.send_event = Mock(return_value=False)
    recovery_mock = Mock()
    monkeypatch.setattr(handler, "_attempt_vkb_link_recovery", recovery_mock)

    assert handler.clear_shift_state_for_shutdown() is False
    handler.vkb_client.send_event.assert_called_once_with(
        "VKBShiftBitmap",
        {"shift": 0, "subshift": 0},
    )
    recovery_mock.assert_not_called()
