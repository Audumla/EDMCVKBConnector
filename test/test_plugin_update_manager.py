from pathlib import Path
import zipfile

from edmcruleengine.plugin_update_manager import (
    PluginRelease,
    PluginUpdateManager,
)


def test_update_to_latest_reports_up_to_date(tmp_path):
    manager = PluginUpdateManager(tmp_path)
    release = PluginRelease(
        version="0.8.5",
        asset_name="EDMCVKBConnector-0.8.5.zip",
        download_url="https://example.invalid/release.zip",
    )
    manager._fetch_latest_release = lambda: release  # type: ignore[attr-defined]

    result = manager.update_to_latest(current_version="0.8.5")

    assert result.success is True
    assert result.updated is False
    assert "up to date" in result.message


def test_update_to_latest_installs_release_and_preserves_rules(tmp_path):
    plugin_dir = tmp_path / "EDMCVKBConnector"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "load.py").write_text("old-load", encoding="utf-8")
    (plugin_dir / "rules.json").write_text('{"user":"rules"}', encoding="utf-8")

    manager = PluginUpdateManager(plugin_dir)
    release = PluginRelease(
        version="0.9.0",
        asset_name="EDMCVKBConnector-0.9.0.zip",
        download_url="https://example.invalid/release.zip",
    )
    manager._fetch_latest_release = lambda: release  # type: ignore[attr-defined]

    def _fake_download(_release: PluginRelease, archive_path: Path) -> bool:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("EDMCVKBConnector/load.py", "new-load")
            archive.writestr("EDMCVKBConnector/rules.json", '{"from":"package"}')
            archive.writestr("EDMCVKBConnector/edmcruleengine/version.py", '__version__ = "0.9.0"\n')
        return True

    manager._download_release_archive = _fake_download  # type: ignore[attr-defined]

    result = manager.update_to_latest(current_version="0.8.5")

    assert result.success is True
    assert result.updated is True
    assert (plugin_dir / "load.py").read_text(encoding="utf-8") == "new-load"
    assert (plugin_dir / "rules.json").read_text(encoding="utf-8") == '{"user":"rules"}'
    assert (plugin_dir / "edmcruleengine" / "version.py").exists()


def test_update_to_latest_fails_when_release_unavailable(tmp_path):
    manager = PluginUpdateManager(tmp_path)
    manager._fetch_latest_release = lambda: None  # type: ignore[attr-defined]

    result = manager.update_to_latest(current_version="0.8.5")

    assert result.success is False
    assert "Unable to check" in result.message

