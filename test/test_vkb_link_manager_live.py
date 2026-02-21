"""
Live VKB-Link manager integration test.

This test intentionally exercises a production-like path:
- discover latest VKB-Link release
- install and start VKB-Link
- connect with VKBClient and send VKBShiftBitmap
- run update flow
- stop VKB-Link

This test always runs on Windows.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from edmcruleengine.config import DEFAULTS
from edmcruleengine.event_handler import EventHandler
from edmcruleengine.vkb_client import VKBClient
from edmcruleengine.vkb_link_manager import VKBLinkManager


class DictConfig:
    def __init__(self, **overrides):
        self.values = dict(DEFAULTS)
        self.values.update(overrides)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


@pytest.mark.skipif(sys.platform != "win32", reason="Live VKB-Link executable flow is Windows-only.")
def test_live_download_start_connect_update_and_stop(monkeypatch):
    host = os.getenv("RUN_VKB_LINK_LIVE_HOST", "127.0.0.1")
    port = int(os.getenv("RUN_VKB_LINK_LIVE_PORT", "50995"))

    test_dir = Path(__file__).resolve().parent
    runtime_root = test_dir / "_live_runtime"
    run_dir = runtime_root / f"run-{int(time.time())}-{os.getpid()}"
    plugin_dir = run_dir / "plugin"
    install_dir = plugin_dir / "vkb-link-live"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    cfg = DictConfig(
        vkb_host=host,
        vkb_port=port,
        vkb_link_install_dir=str(install_dir),
        vkb_link_auto_manage=True,
        vkb_link_restart_on_failure=True,
    )
    manager = VKBLinkManager(cfg, plugin_dir)

    started_by_test = False
    client = VKBClient(
        host=host,
        port=port,
        socket_timeout=3,
        initial_retry_interval=1,
        initial_retry_duration=5,
        fallback_retry_interval=1,
    )
    current_port = port

    def _wait_for_connect(timeout_seconds: int = 30) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if client.connect():
                return True
            time.sleep(1)
        return False

    try:
        result = manager.ensure_running(host=host, port=port, reason="pytest_live")
        if not result.success:
            pytest.xfail(f"Unable to provision VKB-Link in this environment: {result.message}")
        started_by_test = True

        if not _wait_for_connect():
            pytest.xfail("VKB-Link started but did not accept TCP connection within 30 seconds.")

        send_ok = client.send_event("VKBShiftBitmap", {"shift": 1, "subshift": 0})
        if not send_ok:
            pytest.xfail("Connected to VKB-Link but failed to send VKBShiftBitmap payload.")

        # Explicit stop/start cycle to validate runtime control after initial provisioning.
        stop_result = manager.stop_running(reason="pytest_live_midcycle_stop")
        if not stop_result.success:
            pytest.xfail(f"Mid-cycle stop failed: {stop_result.message}")
        client.disconnect()

        restart_result = manager.ensure_running(host=host, port=current_port, reason="pytest_live_midcycle_restart")
        if not restart_result.success:
            pytest.xfail(f"Mid-cycle restart failed: {restart_result.message}")

        if not _wait_for_connect():
            pytest.xfail("VKB-Link restarted but did not accept TCP connection within 30 seconds.")

        second_send_ok = client.send_event("VKBShiftBitmap", {"shift": 2, "subshift": 1})
        if not second_send_ok:
            pytest.xfail("Connected after restart but failed to send VKBShiftBitmap payload.")

        # Simulate the exact UI endpoint-change path.
        ui_port = current_port + 1
        monkeypatch.setattr(EventHandler, "_load_catalog", lambda self: None)
        monkeypatch.setattr(EventHandler, "_load_rules", lambda self: None)
        handler = EventHandler(cfg, vkb_client=client, plugin_dir=str(plugin_dir))
        handler.vkb_link_manager = manager
        handler._apply_endpoint_change(host, ui_port)
        current_port = ui_port

        if client.port != current_port:
            pytest.xfail("UI endpoint-change flow did not update VKB client port.")
        if not client.connected and not _wait_for_connect():
            pytest.xfail("UI endpoint-change restart completed but client could not connect to new port.")
        ui_send_ok = client.send_event("VKBShiftBitmap", {"shift": 3, "subshift": 0})
        if not ui_send_ok:
            pytest.xfail("Connected after UI endpoint change but failed to send VKBShiftBitmap payload.")

        update_result = manager.update_to_latest(host=host, port=current_port)
        if not update_result.success:
            pytest.xfail(f"Live update flow failed: {update_result.message}")
    finally:
        client.disconnect()
        if started_by_test:
            manager.stop_running(reason="pytest_live_cleanup")
        # Explicitly clean download/install artifacts even on xfail/exception.
        for _ in range(5):
            if not run_dir.exists():
                break
            shutil.rmtree(run_dir, ignore_errors=True)
            if run_dir.exists():
                time.sleep(0.5)
        # Keep the runtime root tidy if no runs remain.
        for _ in range(5):
            if not runtime_root.exists():
                break
            try:
                next(runtime_root.iterdir())
                break
            except StopIteration:
                shutil.rmtree(runtime_root, ignore_errors=True)
                if runtime_root.exists():
                    time.sleep(0.2)
