"""
Tests for EventHandler VKB-Link control delegation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest

from edmcruleengine.config.config import DEFAULTS
from edmcruleengine.events.event_handler import EventHandler
from edmcruleengine.vkb.vkb_link_manager import VKBLinkManager


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
    # Keep unit tests focused on delegation.
    monkeypatch.setattr(EventHandler, "_load_catalog", lambda self: None)
    monkeypatch.setattr(EventHandler, "_load_rules", lambda self: None)
    handler = EventHandler(cfg, endpoints=[], plugin_dir=str(tmp_path))
    return handler, cfg


def test_apply_endpoint_change_delegates_to_manager(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    manager = MagicMock(spec=VKBLinkManager)
    manager.name = "VKB-Link"
    handler.add_endpoint(manager)

    handler._apply_endpoint_change("127.0.0.1", 60001)

    manager.apply_managed_endpoint_change.assert_called_once_with(
        host="127.0.0.1",
        port=60001,
    )


def test_connect_delegates_to_manager(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    manager = MagicMock(spec=VKBLinkManager)
    manager.name = "VKB-Link"
    manager.connect.return_value = True
    handler.add_endpoint(manager)

    assert handler.connect() is True
    manager.connect.assert_called_once()


def test_disconnect_delegates_to_manager(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    manager = MagicMock(spec=VKBLinkManager)
    manager.name = "VKB-Link"
    handler.add_endpoint(manager)

    handler.disconnect()
    manager.disconnect.assert_called_once()


def test_on_vkb_link_process_crash_delegates_to_manager(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    manager = MagicMock(spec=VKBLinkManager)
    manager.name = "VKB-Link"
    handler.add_endpoint(manager)

    handler._on_vkb_link_process_crash()
    manager._attempt_recovery.assert_called_once_with(
        reason="process_crash_detected",
        on_connected_callback=handler._on_socket_connected
    )


def test_set_connection_status_override_delegates_to_manager(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    manager = MagicMock(spec=VKBLinkManager)
    manager.name = "VKB-Link"
    handler.add_endpoint(manager)

    handler.set_connection_status_override("Testing...")
    manager.set_connection_status_override.assert_called_once_with("Testing...")


def test_get_connection_status_override_delegates_to_manager(tmp_path, monkeypatch):
    handler, cfg = _make_handler(tmp_path, monkeypatch)
    manager = MagicMock(spec=VKBLinkManager)
    manager.name = "VKB-Link"
    manager.get_connection_status_override.return_value = "Status"
    handler.add_endpoint(manager)

    assert handler.get_connection_status_override() == "Status"
    manager.get_connection_status_override.assert_called_once()
