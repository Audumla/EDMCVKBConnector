"""
Tests for VKB-Link manager process/download/update/INI flows.

Expected production flow (from CHG-002/004/005/007/008 and current code):
1. If VKB-Link is running, sync INI without forcing a restart.
2. If not running, start from known executable path.
3. If no known executable exists, discover latest release, install it, bootstrap INI when missing, then start it.
4. Update flow stops running process, installs latest release, restarts, and re-syncs INI.
"""

from __future__ import annotations

import configparser
import sys
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

import edmcruleengine.vkb_link_manager as vkbm
from edmcruleengine.config import DEFAULTS
from edmcruleengine.vkb_link_manager import (
    VKBLinkManager,
    VKBLinkProcessInfo,
    VKBLinkRelease,
)


class DictConfig:
    """In-memory config stub that matches the get/set API used by manager code."""

    def __init__(self, **overrides):
        self.values = dict(DEFAULTS)
        self.values.update(overrides)
        self.set_calls = []

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value
        self.set_calls.append((key, value))


def _make_manager(tmp_path: Path, **config_overrides):
    cfg = DictConfig(**config_overrides)
    manager = VKBLinkManager(cfg, tmp_path)
    return manager, cfg


def _touch(path: Path, text: str = "stub") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _make_release_zip(
    zip_path: Path,
    *,
    top_dir: str,
    exe_name: str = "VKB-Link.exe",
    include_ini: bool = True,
):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"{top_dir}/{exe_name}", "binary")
        zf.writestr(f"{top_dir}/README.txt", "example")
        if include_ini:
            zf.writestr(f"{top_dir}/VKBLink.ini", "[TCP]\nAdress=zip-host\nPort=7777\n")


def test_version_helpers():
    assert vkbm._extract_version("VKB-Link v1.2.3.zip") == "1.2.3"
    assert vkbm._parse_version("1.2.10") > vkbm._parse_version("1.2.2")
    assert vkbm._is_version_newer("1.3.0", "1.2.9")
    assert not vkbm._is_version_newer("1.2.0", "1.2.0")


def test_resolve_known_exe_path_uses_install_dir_when_stored_exe_is_stale(tmp_path):
    install_dir = tmp_path / "VKB-Link v2.3.4"
    exe_path = _touch(install_dir / "VKB-Link.exe")
    stale_exe = tmp_path / "missing.exe"

    manager, cfg = _make_manager(
        tmp_path,
        vkb_link_exe_path=str(stale_exe),
        vkb_link_install_dir=str(install_dir),
    )
    resolved = manager._resolve_known_exe_path()

    assert resolved == str(exe_path)
    assert cfg.get("vkb_link_exe_path") == str(exe_path)
    assert cfg.get("vkb_link_version") == "2.3.4"


def test_resolve_ini_path_prefers_saved_value(tmp_path):
    saved_ini = _touch(tmp_path / "saved" / "VKBLink.ini", "[TCP]\nAdress=127.0.0.1\nPort=50995\n")
    manager, _ = _make_manager(tmp_path, vkb_ini_path=str(saved_ini))
    assert manager._resolve_ini_path(None) == saved_ini


def test_resolve_ini_path_finds_near_exe_and_persists_config(tmp_path):
    exe = _touch(tmp_path / "app" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=localhost\nPort=12345\n")
    manager, cfg = _make_manager(tmp_path, vkb_ini_path=str(tmp_path / "not-there.ini"))

    resolved = manager._resolve_ini_path(str(exe))
    assert resolved == ini
    assert cfg.get("vkb_ini_path") == str(ini)


def test_patch_ini_text_creates_tcp_section_and_updates_endpoint(tmp_path):
    manager, _ = _make_manager(tmp_path, vkb_link_restart_on_failure=False)

    updated = manager._patch_ini_text("", "127.0.0.1", 50995)

    cp = configparser.ConfigParser()
    cp.read_string(updated)
    assert cp.has_section("TCP")
    assert cp.get("TCP", "Adress") == "127.0.0.1"
    assert cp.get("TCP", "Port") == "50995"


def test_patch_ini_text_does_not_overwrite_unrelated_content(tmp_path):
    manager, _ = _make_manager(tmp_path)
    source = (
        "; top comment\n"
        "[General]\n"
        "Mode=advanced\n"
        "\n"
        "[TCP]\n"
        "; tcp comment\n"
        "Adress = old-host ; keep\n"
        "Port=1111\n"
        "Custom=still-here\n"
        "\n"
        "[Other]\n"
        "Keep=1\n"
    )

    updated = manager._patch_ini_text(source, "127.0.0.1", 50995)

    assert "; top comment" in updated
    assert "Mode=advanced" in updated
    assert "; tcp comment" in updated
    assert "Adress = 127.0.0.1 ; keep" in updated
    assert "Port=50995" in updated
    assert "Custom=still-here" in updated
    assert "Keep=1" in updated


def test_install_release_uses_cached_archive_and_preserves_existing_ini(tmp_path):
    install_dir = tmp_path / "managed-install"
    downloads = install_dir / "_downloads"
    archive = downloads / "VKB-Link-v3.1.0.zip"

    _make_release_zip(archive, top_dir="VKB-Link v3.1.0")
    original_ini = _touch(install_dir / "VKBLink.ini", "[TCP]\nAdress=keep-me\nPort=60000\n")
    _touch(install_dir / "old.txt", "old")

    manager, cfg = _make_manager(tmp_path, vkb_link_install_dir=str(install_dir))
    release = VKBLinkRelease(version="3.1.0", url="https://example.invalid/vkb.zip", filename=archive.name)
    installed_exe = manager._install_release(release)

    assert installed_exe is not None
    assert Path(installed_exe).exists()
    assert cfg.get("vkb_link_version") == "3.1.0"

    cp = configparser.ConfigParser()
    cp.read(original_ini, encoding="utf-8")
    assert cp.get("TCP", "Adress") == "keep-me"
    assert cp.get("TCP", "Port") == "60000"
    assert (install_dir / "README.txt").exists()
    assert not (install_dir / "old.txt").exists()


def test_ensure_running_updates_ini_when_process_exists(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "VKB-Link v4.0.1" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1111\n")
    process = VKBLinkProcessInfo(pid=42, exe_path=str(exe))

    manager, _ = _make_manager(tmp_path, vkb_link_restart_on_failure=True)
    write_ini_mock = Mock()

    monkeypatch.setattr(manager, "_find_running_process", lambda: process)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [process])
    monkeypatch.setattr(manager, "_write_ini", write_ini_mock)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    assert result.action_taken == "none"
    assert "running" in result.message.lower()
    write_ini_mock.assert_called_once_with(ini, "127.0.0.1", 50995)


def test_ensure_running_updates_ini_without_restart_when_restart_disabled(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "VKB-Link v4.0.2" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1111\n")
    process = VKBLinkProcessInfo(pid=99, exe_path=str(exe))

    manager, _ = _make_manager(tmp_path, vkb_link_restart_on_failure=False)
    write_ini_mock = Mock()

    monkeypatch.setattr(manager, "_find_running_process", lambda: process)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [process])
    monkeypatch.setattr(manager, "_write_ini", write_ini_mock)

    result = manager.ensure_running(host="10.0.0.5", port=5555, reason="test")
    assert result.success
    assert result.action_taken == "none"
    assert "ini updated" in result.message.lower()
    write_ini_mock.assert_called_once_with(ini, "10.0.0.5", 5555)


def test_ensure_running_starts_known_exe_path_when_not_running(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "known" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1111\n")
    manager, _ = _make_manager(tmp_path)
    write_ini_mock = Mock()

    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: str(exe))
    monkeypatch.setattr(manager, "_start_process", lambda _exe: True)
    monkeypatch.setattr(manager, "_wait_for_running_process", lambda: VKBLinkProcessInfo(pid=123, exe_path=str(exe)))
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)
    monkeypatch.setattr(manager, "_resolve_or_default_ini_path", lambda _exe: ini)
    monkeypatch.setattr(manager, "_write_ini", write_ini_mock)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    assert result.action_taken == "started"
    assert "started" in result.message.lower()
    write_ini_mock.assert_called_once_with(ini, "127.0.0.1", 50995)


def test_ensure_running_skips_start_if_process_appears_during_race(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "known" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1111\n")
    process = VKBLinkProcessInfo(pid=888, exe_path=str(exe))
    manager, _ = _make_manager(tmp_path)

    start_mock = Mock(return_value=True)
    monkeypatch.setattr(manager, "_find_running_process", lambda: process)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: str(exe))
    monkeypatch.setattr(manager, "_resolve_or_default_ini_path", lambda _exe: ini)
    monkeypatch.setattr(manager, "_start_process", start_mock)
    monkeypatch.setattr(manager, "_write_ini", Mock())

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    assert result.action_taken == "none"
    assert "running" in result.message.lower()
    start_mock.assert_not_called()


def test_ensure_running_downloads_installs_and_starts_when_no_known_exe(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "installed" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1111\n")
    release = VKBLinkRelease(version="5.0.0", url="https://example.invalid/vkb.zip", filename="file.zip")
    manager, _ = _make_manager(tmp_path)
    call_order = []

    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: None)
    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: release)
    monkeypatch.setattr(manager, "_install_release", lambda _release: str(exe))
    monkeypatch.setattr(manager, "_resolve_or_default_ini_path", lambda _exe: ini)
    monkeypatch.setattr(manager, "_wait_for_running_process", lambda: VKBLinkProcessInfo(pid=101, exe_path=str(exe)))
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)

    def write_ini_side_effect(_ini, _host, _port):
        call_order.append("write")

    def start_process_side_effect(_exe):
        call_order.append("start")
        return True

    monkeypatch.setattr(manager, "_write_ini", write_ini_side_effect)
    monkeypatch.setattr(manager, "_start_process", start_process_side_effect)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    assert result.action_taken == "started"
    assert "started" in result.message.lower()
    assert call_order == ["write", "start"]


def test_ensure_running_download_bootstraps_first_run_when_ini_is_missing(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "installed-bootstrap" / "VKB-Link.exe")
    generated_ini = exe.parent / "VKB-Link.ini"
    release = VKBLinkRelease(version="5.0.5", url="https://example.invalid/vkb.zip", filename="file.zip")
    process = VKBLinkProcessInfo(pid=55, exe_path=str(exe))
    manager, _ = _make_manager(tmp_path)
    call_order = []
    state = {"running": False}

    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: None)
    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: release)
    monkeypatch.setattr(manager, "_install_release", lambda _release: str(exe))
    monkeypatch.setattr(vkbm.time, "sleep", lambda _seconds: None)

    def find_running_side_effect():
        return process if state["running"] else None

    def find_running_all_side_effect():
        return [process] if state["running"] else []

    def start_process_side_effect(_exe):
        if not generated_ini.exists():
            call_order.append("bootstrap_start")
            generated_ini.write_text("[TCP]\nAdress=bootstrap\nPort=1\n", encoding="utf-8")
        else:
            call_order.append("start")
        state["running"] = True
        return True

    def stop_process_side_effect(_process):
        call_order.append("stop")
        state["running"] = False
        return True

    def write_ini_side_effect(_ini, _host, _port):
        call_order.append("write")

    monkeypatch.setattr(manager, "_find_running_process", find_running_side_effect)
    monkeypatch.setattr(manager, "_find_running_processes", find_running_all_side_effect)
    monkeypatch.setattr(manager, "_start_process", start_process_side_effect)
    monkeypatch.setattr(manager, "_stop_process", stop_process_side_effect)
    monkeypatch.setattr(manager, "_write_ini", write_ini_side_effect)
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    assert result.action_taken == "started"
    assert call_order == ["bootstrap_start", "stop", "write", "start"]


def test_ensure_running_download_uses_default_ini_path_when_none_found(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "installed-default" / "VKB-Link.exe")
    release = VKBLinkRelease(version="5.0.1", url="https://example.invalid/vkb.zip", filename="file.zip")
    manager, cfg = _make_manager(tmp_path)

    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: None)
    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: release)
    monkeypatch.setattr(manager, "_install_release", lambda _release: str(exe))
    monkeypatch.setattr(manager, "_bootstrap_ini_after_install", lambda _exe: None)
    monkeypatch.setattr(manager, "_resolve_ini_path", lambda _exe: None)
    monkeypatch.setattr(manager, "_start_process", lambda _exe: True)
    monkeypatch.setattr(manager, "_wait_for_running_process", lambda: VKBLinkProcessInfo(pid=102, exe_path=str(exe)))
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)

    write_ini_mock = Mock()
    monkeypatch.setattr(manager, "_write_ini", write_ini_mock)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    expected_ini = exe.parent / "VKBLink.ini"
    write_ini_mock.assert_called_once_with(expected_ini, "127.0.0.1", 50995)
    assert cfg.get("vkb_ini_path") == str(expected_ini)


def test_ensure_running_download_ignores_stale_saved_ini_and_targets_exe_dir(tmp_path, monkeypatch):
    stale_ini = _touch(tmp_path / "old-install" / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1\n")
    exe = _touch(tmp_path / "new-install" / "VKB-Link.exe")
    release = VKBLinkRelease(version="5.0.2", url="https://example.invalid/vkb.zip", filename="file.zip")
    manager, cfg = _make_manager(tmp_path, vkb_ini_path=str(stale_ini))

    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: None)
    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: release)
    monkeypatch.setattr(manager, "_install_release", lambda _release: str(exe))
    monkeypatch.setattr(manager, "_bootstrap_ini_after_install", lambda _exe: None)
    monkeypatch.setattr(manager, "_find_ini_near_exe", lambda _exe: None)
    monkeypatch.setattr(manager, "_start_process", lambda _exe: True)
    monkeypatch.setattr(manager, "_wait_for_running_process", lambda: VKBLinkProcessInfo(pid=103, exe_path=str(exe)))
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)

    write_ini_mock = Mock()
    monkeypatch.setattr(manager, "_write_ini", write_ini_mock)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    expected_ini = exe.parent / "VKBLink.ini"
    write_ini_mock.assert_called_once_with(expected_ini, "127.0.0.1", 50995)
    assert cfg.get("vkb_ini_path") == str(expected_ini)


def test_ensure_running_fails_when_latest_release_cannot_be_found(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: None)
    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: None)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert not result.success
    assert "unable to locate vkb-link" in result.message.lower()


def test_update_to_latest_reports_up_to_date_when_no_newer_version(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path, vkb_link_version="2.0.0")
    monkeypatch.setattr(
        manager,
        "_fetch_latest_release",
        lambda: VKBLinkRelease(version="2.0.0", url="https://example.invalid", filename="x.zip"),
    )

    result = manager.update_to_latest(host="127.0.0.1", port=50995)
    assert result.success
    assert result.action_taken == "none"
    assert "up to date" in result.message.lower()


def test_update_to_latest_stops_installs_restarts_and_syncs_ini(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "new" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1111\n")
    process = VKBLinkProcessInfo(pid=7, exe_path=str(exe))
    release = VKBLinkRelease(version="2.1.0", url="https://example.invalid", filename="x.zip")
    manager, _ = _make_manager(tmp_path, vkb_link_version="2.0.0")

    stop_mock = Mock(return_value=True)
    call_order = []

    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: release)
    monkeypatch.setattr(manager, "_find_running_process", lambda: process)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [process])
    monkeypatch.setattr(manager, "_stop_process", stop_mock)
    monkeypatch.setattr(manager, "_wait_for_no_running_process", lambda: True)
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)
    monkeypatch.setattr(manager, "_install_release", lambda _release: str(exe))
    monkeypatch.setattr(manager, "_resolve_or_default_ini_path", lambda _exe: ini)

    def write_ini_side_effect(_ini, _host, _port):
        call_order.append("write")

    def start_process_side_effect(_exe):
        call_order.append("start")
        return True

    monkeypatch.setattr(manager, "_write_ini", write_ini_side_effect)
    monkeypatch.setattr(manager, "_start_process", start_process_side_effect)
    monkeypatch.setattr(manager, "_wait_for_running_process", lambda: VKBLinkProcessInfo(pid=500, exe_path=str(exe)))

    result = manager.update_to_latest(host="127.0.0.1", port=50995)
    assert result.success
    assert result.action_taken == "restarted"
    assert "updated vkb-link to v2.1.0" in result.message.lower()
    stop_mock.assert_called_once()
    assert call_order == ["write", "start"]


def test_update_to_latest_fails_when_install_step_fails(tmp_path, monkeypatch):
    release = VKBLinkRelease(version="2.1.0", url="https://example.invalid", filename="x.zip")
    manager, _ = _make_manager(tmp_path, vkb_link_version="2.0.0")

    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: release)
    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_install_release", lambda _release: None)

    result = manager.update_to_latest(host="127.0.0.1", port=50995)
    assert not result.success
    assert "failed to install" in result.message.lower()


def test_stop_running_returns_not_running_when_no_process(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    result = manager.stop_running(reason="test")
    assert result.success
    assert result.action_taken == "none"
    assert "not running" in result.message.lower()


def test_stop_running_reports_failure_when_stop_command_fails(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    monkeypatch.setattr(manager, "_find_running_process", lambda: VKBLinkProcessInfo(pid=1, exe_path=None))
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [VKBLinkProcessInfo(pid=1, exe_path=None)])
    monkeypatch.setattr(manager, "_stop_process", lambda _proc: False)
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)
    result = manager.stop_running(reason="test")
    assert not result.success
    assert result.action_taken == "none"
    assert "failed to stop" in result.message.lower()


def test_ensure_running_stops_duplicate_processes_before_restart(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "VKB-Link v4.0.1" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKBLink.ini", "[TCP]\nAdress=old\nPort=1111\n")
    processes = [
        VKBLinkProcessInfo(pid=42, exe_path=str(exe)),
        VKBLinkProcessInfo(pid=43, exe_path=str(exe)),
    ]
    manager, _ = _make_manager(tmp_path, vkb_link_restart_on_failure=False)

    call_order = []
    state = {"calls": 0}

    def find_processes_side_effect():
        state["calls"] += 1
        if state["calls"] == 1:
            return processes
        return []

    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", find_processes_side_effect)
    monkeypatch.setattr(manager, "_write_ini", lambda _ini, _host, _port: call_order.append("write"))
    monkeypatch.setattr(manager, "_stop_all_processes", lambda _procs: call_order.append("stop_all") or True)
    monkeypatch.setattr(manager, "_wait_for_no_running_process", lambda: True)
    monkeypatch.setattr(manager, "_start_process", lambda _exe: call_order.append("start") or True)
    monkeypatch.setattr(manager, "_wait_for_running_process", lambda: VKBLinkProcessInfo(pid=44, exe_path=str(exe)))
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: str(exe))
    monkeypatch.setattr(manager, "_resolve_or_default_ini_path", lambda _exe: ini)

    result = manager.ensure_running(host="127.0.0.1", port=50995, reason="test")
    assert result.success
    assert result.action_taken == "started"
    assert "started" in result.message.lower()
    assert call_order == ["stop_all", "write", "start"]
    assert ini.exists()


def test_stop_running_stops_all_detected_processes(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    processes = [
        VKBLinkProcessInfo(pid=1001, exe_path=r"C:\VKB\VKB-Link.exe"),
        VKBLinkProcessInfo(pid=1002, exe_path=r"C:\VKB\VKB-Link.exe"),
    ]
    monkeypatch.setattr(manager, "_find_running_process", lambda: processes[0])
    monkeypatch.setattr(manager, "_find_running_processes", lambda: processes)
    stop_all_mock = Mock(return_value=True)
    monkeypatch.setattr(manager, "_stop_all_processes", stop_all_mock)
    monkeypatch.setattr(manager, "_wait_for_no_running_process", lambda: True)
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)

    result = manager.stop_running(reason="test")
    assert result.success
    assert result.action_taken == "stopped"
    assert "stopped 2 vkb-link processes" in result.message.lower()
    stop_all_mock.assert_called_once_with(processes)


def test_apply_managed_endpoint_change_stops_updates_and_restarts(tmp_path, monkeypatch):
    exe = _touch(tmp_path / "managed" / "VKB-Link.exe")
    ini = _touch(exe.parent / "VKB-Link.ini", "[TCP]\nAdress=old\nPort=1111\n")
    manager, _ = _make_manager(tmp_path)

    running = [VKBLinkProcessInfo(pid=2200, exe_path=str(exe))]
    monkeypatch.setattr(manager, "_find_running_processes", lambda: running)
    stop_all_mock = Mock(return_value=True)
    monkeypatch.setattr(manager, "_stop_all_processes", stop_all_mock)
    monkeypatch.setattr(manager, "_wait_for_no_running_process", lambda: True)
    monkeypatch.setattr(manager, "_wait_after_running_ack", lambda: None)
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: str(exe))
    monkeypatch.setattr(manager, "_resolve_or_default_ini_path", lambda _exe: ini)
    write_ini_mock = Mock()
    monkeypatch.setattr(manager, "_write_ini", write_ini_mock)
    monkeypatch.setattr(manager, "_start_process", lambda _exe: True)
    monkeypatch.setattr(manager, "_wait_for_running_process", lambda: VKBLinkProcessInfo(pid=2300, exe_path=str(exe)))

    result = manager.apply_managed_endpoint_change(host="127.0.0.1", port=62000)
    assert result.success
    assert result.action_taken == "restarted"
    stop_all_mock.assert_called_once_with(running)
    write_ini_mock.assert_called_once_with(ini, "127.0.0.1", 62000)


def test_fetch_latest_release_prefers_mega_and_picks_highest_version(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    r1 = VKBLinkRelease(version="1.2.0", url="mega://a", filename="a.zip")
    r2 = VKBLinkRelease(version="1.10.0", url="mega://b", filename="b.zip")

    monkeypatch.setattr(vkbm, "_ensure_cryptography", lambda: True)
    monkeypatch.setattr(vkbm, "_mega_decode_folder_key", lambda _k: b"\x00" * 16)
    monkeypatch.setattr(vkbm, "_mega_list_folder", lambda _node, _key: [r1, r2])

    release = manager._fetch_latest_release()
    assert release is not None
    assert release.version == "1.10.0"
    assert release.url == "mega://b"


def test_fetch_latest_release_returns_none_when_mega_is_unavailable(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    monkeypatch.setattr(vkbm, "_ensure_cryptography", lambda: False)
    assert manager._fetch_latest_release() is None


def test_fetch_latest_release_returns_none_when_mega_listing_fails(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    monkeypatch.setattr(vkbm, "_ensure_cryptography", lambda: True)
    monkeypatch.setattr(vkbm, "_mega_decode_folder_key", lambda _k: b"\x00" * 16)
    monkeypatch.setattr(vkbm, "_mega_list_folder", lambda _node, _key: [])
    assert manager._fetch_latest_release() is None


def test_mega_download_fails_when_required_release_key_material_is_missing(tmp_path):
    manager, _ = _make_manager(tmp_path)
    archive_path = tmp_path / "x.zip"
    release = VKBLinkRelease(version="1.0.0", url="mega://node", filename="x.zip")
    assert not manager._mega_download(release, archive_path)
    assert not archive_path.exists()


def test_mega_download_fails_when_cryptography_is_unavailable(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    archive_path = tmp_path / "x.zip"
    release = VKBLinkRelease(
        version="1.0.0",
        url="mega://node",
        filename="x.zip",
        mega_node_handle="abc123",
        mega_raw_key=b"\x00" * 32,
    )
    monkeypatch.setattr(vkbm, "_ensure_cryptography", lambda: False)
    assert not manager._mega_download(release, archive_path)
    assert not archive_path.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific process command verification.")
def test_stop_process_windows_uses_pid_when_available(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    process = VKBLinkProcessInfo(pid=1234, exe_path=r"C:\Fake\VKB-Link.exe")

    run_mock = Mock()
    run_mock.return_value.returncode = 0
    run_mock.return_value.stdout = ""
    run_mock.return_value.stderr = ""
    monkeypatch.setattr(vkbm.subprocess, "run", run_mock)

    assert manager._stop_process(process)
    commands = [call.args[0] for call in run_mock.call_args_list]
    assert any(cmd[:2] == ["taskkill", "/PID"] and "1234" in cmd for cmd in commands)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific process parsing.")
def test_find_running_processes_windows_prefers_unique_pid_entries(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)

    def _result(stdout: str = "", returncode: int = 0):
        r = Mock()
        r.stdout = stdout
        r.stderr = ""
        r.returncode = returncode
        return r

    def run_side_effect(cmd, *args, **kwargs):
        joined = " ".join(cmd).lower()
        if "get-process -name 'vkb-link'" in joined:
            return _result('[{"Id":66972,"Path":"G:\\\\Games\\\\vkb\\\\VKB-Link.exe"}]')
        if cmd[:2] == ["wmic", "process"]:
            # Deliberately malformed WMIC-style output that can split into path-only and pid-only blocks.
            return _result("ExecutablePath=G:\\Games\\vkb\\VKB-Link.exe\n\nProcessId=66972\n")
        if cmd and cmd[0].lower() == "tasklist":
            return _result("")
        return _result("")

    monkeypatch.setattr(vkbm.subprocess, "run", Mock(side_effect=run_side_effect))

    processes = manager._find_running_processes_windows()
    assert len(processes) == 1
    assert processes[0].pid == 66972
    assert processes[0].exe_path == "G:\\Games\\vkb\\VKB-Link.exe"


def test_ensure_not_minimized_temporarily_disables_minimized_setting(tmp_path: Path):
    """Test that _ensure_not_minimized_for_startup temporarily disables minimized in INI."""
    manager, cfg = _make_manager(tmp_path)

    # Create a mock INI file with Start Minimized=1
    ini_path = tmp_path / "test.ini"
    ini_content = """\
[TCP]
host=127.0.0.1
port=50995

[Common]
start minimized =1
other_setting=value
"""
    ini_path.write_text(ini_content, encoding='utf-8')

    # Call _ensure_not_minimized_for_startup which should return True (was minimized)
    # and modify the INI file to set Start Minimized=0
    original_value = manager._ensure_not_minimized_for_startup(ini_path)

    assert original_value is True, "Should have detected Start Minimized=1"

    # Verify INI was modified to Start Minimized=0
    modified_content = ini_path.read_text(encoding='utf-8')
    assert "start minimized" in modified_content.lower() and "=0" in modified_content.lower(), "INI should have start minimized =0"
    # Make sure "start minimized" is set to 0, not 1
    for line in modified_content.lower().splitlines():
        if "start minimized" in line:
            assert "=0" in line, "start minimized should be set to 0"
            assert "=1" not in line, "start minimized should not be set to 1"


def test_ensure_not_minimized_creates_ini_when_missing(tmp_path: Path):
    """Test that _ensure_not_minimized_for_startup creates INI with Start Minimized=0 if missing."""
    manager, cfg = _make_manager(tmp_path)

    # Path to non-existent INI file
    ini_path = tmp_path / "test.ini"
    assert not ini_path.exists(), "INI should not exist initially"

    # Call _ensure_not_minimized_for_startup with non-existent INI
    # Should create it with Start Minimized=0
    original_value = manager._ensure_not_minimized_for_startup(ini_path)

    assert ini_path.exists(), "INI file should have been created"
    assert original_value is None, "Should return None for non-existent setting (not True)"

    # Verify INI contains [Settings] section with Start Minimized=0
    content = ini_path.read_text(encoding='utf-8')
    assert "[common]" in content.lower(), "INI should have [Settings] section"
    assert "start minimized" in content.lower() and "=0" in content.lower(), "INI should have start minimized =0"


def test_ensure_not_minimized_adds_section_if_missing(tmp_path: Path):
    """Test that _ensure_not_minimized_for_startup adds [Settings] section if it doesn't exist."""
    manager, cfg = _make_manager(tmp_path)

    # Create INI with TCP section but no Settings section
    ini_path = tmp_path / "test.ini"
    ini_content = """\
[TCP]
host=127.0.0.1
port=50995
"""
    ini_path.write_text(ini_content, encoding='utf-8')

    # Call _ensure_not_minimized_for_startup
    original_value = manager._ensure_not_minimized_for_startup(ini_path)

    assert original_value is None, "Should return None since Start Minimized was not set"

    # Verify INI now has [Common] section with start minimized =0
    modified_content = ini_path.read_text(encoding='utf-8')
    assert "[common]" in modified_content.lower(), "INI should have [Common] section"
    assert "start minimized" in modified_content.lower() and "=0" in modified_content.lower(), "INI should have start minimized =0"
    assert "[TCP]" in modified_content, "TCP section should be preserved"


def test_restore_minimized_setting_restores_original_value(tmp_path: Path):
    """Test that _restore_minimized_setting restores the original Start Minimized value."""
    manager, cfg = _make_manager(tmp_path)

    # Create a mock INI file with Start Minimized=0 (as it would be after ensure_not_minimized)
    ini_path = tmp_path / "test.ini"
    ini_content = """\
[TCP]
host=127.0.0.1
port=50995

[Settings]
Start Minimized=0
other_setting=value
"""
    ini_path.write_text(ini_content, encoding='utf-8')

    # Call _restore_minimized_setting with original_minimized=True to restore it back
    manager._restore_minimized_setting(ini_path, original_minimized=True)

    # Verify INI was restored to Start Minimized=1
    restored_content = ini_path.read_text(encoding='utf-8')
    # INI uses "start minimized =1" format (with space before equals)
    assert "start minimized" in restored_content.lower(), "INI should have start minimized setting"
    assert "=1" in restored_content, "INI should be restored to start minimized =1"


def test_minimized_handling_full_startup_flow(tmp_path: Path):
    """Test complete flow: disable Start Minimized before start, restore after connection."""
    manager, cfg = _make_manager(tmp_path)

    # Create test INI with Start Minimized=1
    ini_path = tmp_path / "VKBLink.ini"
    original_ini = """\
[TCP]
host=127.0.0.1
port=50995

[Common]
start minimized =1
"""
    ini_path.write_text(original_ini, encoding='utf-8')

    # Directly test the minimized handling functions
    # Step 1: Disable minimized before startup
    original_minimized = manager._ensure_not_minimized_for_startup(ini_path)

    assert original_minimized is True, "Should have saved that it was originally minimized (1)"

    # Verify INI was temporarily modified to start minimized =0
    startup_ini_content = ini_path.read_text(encoding='utf-8')
    assert "start minimized" in startup_ini_content.lower() and "=0" in startup_ini_content.lower(), "INI should have been changed to start minimized =0"

    # Step 2: Simulate storing for restoration
    manager._last_startup_original_minimized = original_minimized
    manager._last_startup_ini_path = ini_path

    # Step 3: Restore minimized after TCP connection
    manager.restore_last_startup_minimized_setting()

    # Verify INI was restored to start minimized =1 after connection
    final_ini_content = ini_path.read_text(encoding='utf-8')
    assert "start minimized" in final_ini_content.lower(), "INI should have start minimized setting"
    assert "=1" in final_ini_content, "INI should have been restored to start minimized =1"
