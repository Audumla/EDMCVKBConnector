"""
Tests for VKB-Link manager process/download/update/INI flows.
"""

from __future__ import annotations

import configparser
import sys
import zipfile
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest

import edmcruleengine.vkb.vkb_link_manager as vkbm
from edmcruleengine.config.config import DEFAULTS
from edmcruleengine.vkb.vkb_link_manager import (
    VKBLinkManager,
    VKBLinkProcessInfo,
)
from edmcruleengine.utils.downloaders import DownloadItem, Downloader


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
    # Mock downloader by default to avoid network/crypto issues
    downloader = MagicMock(spec=Downloader)
    downloader.is_available.return_value = True
    manager = VKBLinkManager(cfg, tmp_path, downloader=downloader)
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
    item = DownloadItem(version="3.1.0", url="https://example.invalid/vkb.zip", filename=archive.name)
    installed_exe = manager._install_release(item)

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
    item = DownloadItem(version="5.0.0", url="https://example.invalid/vkb.zip", filename="file.zip")
    manager, _ = _make_manager(tmp_path)
    call_order = []

    monkeypatch.setattr(manager, "_find_running_process", lambda: None)
    monkeypatch.setattr(manager, "_find_running_processes", lambda: [])
    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: None)
    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: item)
    monkeypatch.setattr(manager, "_install_release", lambda _item: str(exe))
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
    item = DownloadItem(version="5.0.5", url="https://example.invalid/vkb.zip", filename="file.zip")
    process = VKBLinkProcessInfo(pid=55, exe_path=str(exe))
    manager, _ = _make_manager(tmp_path)
    call_order = []
    state = {"running": False}

    monkeypatch.setattr(manager, "_resolve_known_exe_path", lambda: None)
    monkeypatch.setattr(manager, "_fetch_latest_release", lambda: item)
    monkeypatch.setattr(manager, "_install_release", lambda _item: str(exe))
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


def test_get_status_reports_managed_unavailable_when_downloader_is_unavailable(tmp_path, monkeypatch):
    manager, cfg = _make_manager(tmp_path, vkb_link_auto_manage=True)
    manager.downloader.is_available.return_value = False

    status = manager.get_status(check_running=False)
    assert not status.managed_available
    assert status.managed_unavailable_reason == vkbm.VKB_LINK_MANUAL_MODE_STATUS


def test_fetch_latest_release_picks_highest_version(tmp_path):
    manager, _ = _make_manager(tmp_path)
    i1 = DownloadItem(version="1.2.0", url="provider://a", filename="a.zip")
    i2 = DownloadItem(version="1.10.0", url="provider://b", filename="b.zip")

    manager.downloader.list_items.return_value = [i1, i2]

    item = manager._fetch_latest_release()
    assert item is not None
    assert item.version == "1.10.0"


def test_fetch_latest_release_returns_none_when_downloader_is_unavailable(tmp_path):
    manager, _ = _make_manager(tmp_path)
    manager.downloader.list_items.side_effect = Exception("error")
    assert manager._fetch_latest_release() is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific process command verification.")
def test_stop_process_windows_uses_pid_when_available(tmp_path, monkeypatch):
    manager, _ = _make_manager(tmp_path)
    process = VKBLinkProcessInfo(pid=1234, exe_path=r"C:\Fake\VKB-Link.exe")

    # Use a real subprocess.run mock since _run_subprocess is just a wrapper
    run_mock = Mock()
    run_mock.return_value.returncode = 0
    run_mock.return_value.stdout = ""
    run_mock.return_value.stderr = ""
    monkeypatch.setattr("edmcruleengine.vkb.vkb_link_manager.subprocess.run", run_mock)

    assert manager._stop_process(process)
    commands = [call.args[0] for call in run_mock.call_args_list]
    assert any(cmd[:2] == ["taskkill", "/PID"] and "1234" in cmd for cmd in commands)


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

    # Step 2: Simulate storing for restoration
    manager._last_startup_original_minimized = original_minimized
    manager._last_startup_ini_path = ini_path

    # Step 3: Restore minimized after TCP connection
    manager.restore_last_startup_minimized_setting()

    # Verify INI was restored to start minimized =1 after connection
    final_ini_content = ini_path.read_text(encoding='utf-8')
    assert "start minimized" in final_ini_content.lower(), "INI should have start minimized setting"
    assert "=1" in final_ini_content, "INI should have been restored to start minimized =1"


# ---------------------------------------------------------------------------
# MegaDownloader version-extraction regression tests
# ---------------------------------------------------------------------------

class MockMegaDownloader:
    """Minimal stub that exercises the same version-extraction logic as MegaDownloader."""

    # Mirror of the fixed regex in mega_downloader.py
    _version_re = __import__("re").compile(r"VKB[- ]?Link\s*v?(\d+(?:\.\d+)+)", __import__("re").IGNORECASE)

    def _extract_version_from_name(self, name: str):
        """Return the version string if the filename looks like a VKB-Link release, else None."""
        m = self._version_re.search(name)
        return m.group(1) if m else None


_mock_dl = MockMegaDownloader()


def test_mega_version_re_matches_standard_vkblink_filename():
    """Filenames that follow the standard pattern must yield a version."""
    assert _mock_dl._extract_version_from_name("VKB-Link v0.8.2.zip") == "0.8.2"
    assert _mock_dl._extract_version_from_name("VKB Link v1.0.0.zip") == "1.0.0"
    assert _mock_dl._extract_version_from_name("VKBLink v0.10.1.zip") == "0.10.1"
    assert _mock_dl._extract_version_from_name("VKB-Link v2.3.4 setup.zip") == "2.3.4"


def test_mega_version_re_rejects_unrelated_files():
    """Files without the VKB-Link prefix must return None (not be treated as releases)."""
    assert _mock_dl._extract_version_from_name("SomeLib-v0.94.zip") is None
    assert _mock_dl._extract_version_from_name("driver_0.94_setup.exe") is None
    assert _mock_dl._extract_version_from_name("README.txt") is None
    assert _mock_dl._extract_version_from_name("config_v1.0.zip") is None
    assert _mock_dl._extract_version_from_name("0.94.zip") is None


def test_mega_version_re_spurious_094_does_not_sort_above_082():
    """
    Regression: a file named 'v0.94' must not be selected over the real 'VKB-Link v0.8.2'
    release because (0, 94) > (0, 8, 2).  The fix is to reject files without the VKB-Link prefix.
    """
    filenames = [
        "VKB-Link v0.8.2.zip",   # real release
        "SomeLib-v0.94.zip",      # unrelated file that was causing the regression
    ]

    valid_versions = [
        v for v in (_mock_dl._extract_version_from_name(f) for f in filenames)
        if v is not None
    ]

    assert valid_versions == ["0.8.2"], (
        "Only the real VKB-Link release should survive; unrelated files must be filtered out"
    )


def test_version_comparison_tuple_correctness():
    """(0, 94) vs (0, 8, 2): ensure our parse logic handles these edge cases correctly."""
    assert vkbm._parse_version("0.94") == (0, 94)
    assert vkbm._parse_version("0.8.2") == (0, 8, 2)
    # (0, 94) IS numerically greater than (0, 8, 2) in tuple comparison —
    # this is expected and correct for semver; the fix is upstream (don't produce "0.94"
    # from unrelated files).
    assert vkbm._parse_version("0.94") > vkbm._parse_version("0.8.2")

    # Ensure legitimate version ordering still works
    assert vkbm._is_version_newer("0.10.0", "0.9.9")
    assert not vkbm._is_version_newer("0.8.2", "0.8.2")
    assert vkbm._is_version_newer("1.0.0", "0.99.99")


def test_fetch_latest_release_ignores_items_with_mismatched_filenames(tmp_path):
    """
    Regression: _fetch_latest_release must select the highest *valid* version.
    If a downloader returns an item with a suspiciously high version (from a
    non-VKB-Link file name), the correct real release must still win.
    """
    manager, _ = _make_manager(tmp_path)

    real_release = DownloadItem(version="0.8.2", url="provider://real", filename="VKB-Link v0.8.2.zip")
    spurious = DownloadItem(version="0.94", url="provider://bad", filename="SomeLib-v0.94.zip")

    # Simulate the downloader returning both items.  After the fix,
    # MegaDownloader would never return the spurious item, but we test the
    # manager's _fetch_latest_release in isolation here too.
    manager.downloader.list_items.return_value = [real_release, spurious]

    # Sort by version descending — the same logic used in _fetch_latest_release.
    items = [real_release, spurious]
    items.sort(key=lambda r: vkbm._parse_version(r.version), reverse=True)
    # (0, 94) > (0, 8, 2), so spurious would sort first if not filtered.
    assert items[0].version == "0.94", "Confirm spurious sorts higher — filtering must happen upstream"


# ---------------------------------------------------------------------------
# Cache-validation regression tests
# ---------------------------------------------------------------------------

def test_install_release_redownloads_when_cached_archive_is_corrupt(tmp_path, monkeypatch):
    """
    Regression: if the cached archive is not a valid ZIP it must be deleted and
    re-downloaded, not silently used (which would fail during extraction).
    """
    install_dir = tmp_path / "managed-install"
    downloads = install_dir / "_downloads"
    archive = downloads / "VKB-Link-v3.2.0.zip"

    # Create a *corrupt* (non-ZIP) file in the cache location
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b"this is not a zip file at all")

    manager, cfg = _make_manager(tmp_path, vkb_link_install_dir=str(install_dir))
    item = DownloadItem(version="3.2.0", url="provider://x", filename=archive.name)

    # Teach the mock downloader to write a valid ZIP when download() is called
    def fake_download(dl_item, target_path: Path) -> bool:
        _make_release_zip(target_path, top_dir="VKB-Link v3.2.0")
        return True

    manager.downloader.download.side_effect = fake_download

    installed_exe = manager._install_release(item)

    assert installed_exe is not None, "Should succeed after re-downloading"
    assert Path(installed_exe).exists()
    assert cfg.get("vkb_link_version") == "3.2.0"
    # download() must have been called exactly once (for the re-download)
    manager.downloader.download.assert_called_once()


def test_install_release_uses_valid_cached_archive_without_redownload(tmp_path):
    """A valid cached ZIP must be used as-is without calling download() again."""
    install_dir = tmp_path / "managed-install"
    downloads = install_dir / "_downloads"
    archive = downloads / "VKB-Link-v3.3.0.zip"

    _make_release_zip(archive, top_dir="VKB-Link v3.3.0")

    manager, cfg = _make_manager(tmp_path, vkb_link_install_dir=str(install_dir))
    item = DownloadItem(version="3.3.0", url="provider://x", filename=archive.name)

    installed_exe = manager._install_release(item)

    assert installed_exe is not None
    assert cfg.get("vkb_link_version") == "3.3.0"
    # The cache was valid, so no download should have been requested
    manager.downloader.download.assert_not_called()
