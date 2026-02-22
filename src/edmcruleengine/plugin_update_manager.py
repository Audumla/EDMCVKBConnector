"""
Plugin self-update helper for EDMC VKB Connector.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.request import Request, urlopen


GITHUB_RELEASE_API_URL = "https://api.github.com/repos/Audumla/EDMCVKBConnector/releases/latest"
VERSION_RE = re.compile(r"(\d+(?:\.\d+)+)")


def _parse_version(value: str) -> tuple[int, ...]:
    parts = []
    for token in (value or "").strip().split("."):
        if token.isdigit():
            parts.append(int(token))
        else:
            break
    return tuple(parts)


def _is_version_newer(candidate: str, current: str) -> bool:
    return _parse_version(candidate) > _parse_version(current)


def _extract_version(value: str) -> Optional[str]:
    match = VERSION_RE.search(value or "")
    if not match:
        return None
    return match.group(1)


@dataclass(frozen=True)
class PluginRelease:
    version: str
    asset_name: str
    download_url: str


@dataclass(frozen=True)
class PluginUpdateResult:
    success: bool
    message: str
    updated: bool = False
    latest_version: Optional[str] = None


class PluginUpdateManager:
    """Check GitHub releases and install a packaged plugin update."""

    def __init__(
        self,
        plugin_dir: Path,
        *,
        logger: Any = None,
        release_api_url: str = GITHUB_RELEASE_API_URL,
    ) -> None:
        self.plugin_dir = Path(plugin_dir)
        self.logger = logger
        self.release_api_url = release_api_url

    def _log(self, level: str, message: str) -> None:
        method = getattr(self.logger, level, None)
        if callable(method):
            method(message)

    def _fetch_latest_release(self) -> Optional[PluginRelease]:
        request = Request(
            self.release_api_url,
            headers={
                "User-Agent": "EDMCVKBConnector/1.0",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self._log("error", f"Plugin update: failed to query GitHub releases: {exc}")
            return None

        tag_name = str(payload.get("tag_name", "")).strip()
        version = _extract_version(tag_name)

        zip_asset = None
        assets = payload.get("assets") or []
        for asset in assets:
            name = str(asset.get("name", "")).strip()
            if not name.lower().endswith(".zip"):
                continue
            if "edmcvkbconnector" in name.lower():
                zip_asset = asset
                break
            if zip_asset is None:
                zip_asset = asset

        if not zip_asset:
            self._log("warning", "Plugin update: no ZIP asset found in latest release")
            return None

        asset_name = str(zip_asset.get("name", "")).strip()
        download_url = str(zip_asset.get("browser_download_url", "")).strip()
        if not version:
            version = _extract_version(asset_name)
        if not version or not download_url:
            self._log("warning", "Plugin update: unable to resolve release version/download URL")
            return None

        return PluginRelease(version=version, asset_name=asset_name, download_url=download_url)

    def _download_release_archive(self, release: PluginRelease, archive_path: Path) -> bool:
        request = Request(
            release.download_url,
            headers={"User-Agent": "EDMCVKBConnector/1.0"},
        )
        try:
            with urlopen(request, timeout=30) as response, archive_path.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            return True
        except Exception as exc:
            self._log("error", f"Plugin update: download failed: {exc}")
            return False

    def _locate_payload_root(self, extract_dir: Path) -> Optional[Path]:
        candidates = [extract_dir]
        candidates.extend(
            sorted((item for item in extract_dir.iterdir() if item.is_dir()), key=lambda p: p.name.lower())
        )
        for candidate in candidates:
            if (candidate / "load.py").is_file() and (candidate / "edmcruleengine").is_dir():
                return candidate
        return None

    def _install_payload(self, payload_root: Path) -> None:
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        for source in payload_root.iterdir():
            if source.name == "rules.json":
                # Preserve user-authored rules during plugin update.
                continue
            destination = self.plugin_dir / source.name
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)

    def update_to_latest(self, *, current_version: str) -> PluginUpdateResult:
        if not self.plugin_dir.exists():
            return PluginUpdateResult(False, f"Plugin directory not found: {self.plugin_dir}")

        release = self._fetch_latest_release()
        if not release:
            return PluginUpdateResult(False, "Unable to check for plugin updates")

        if current_version and not _is_version_newer(release.version, current_version):
            return PluginUpdateResult(
                True,
                f"Plugin is already up to date (v{current_version})",
                updated=False,
                latest_version=release.version,
            )

        try:
            with tempfile.TemporaryDirectory(prefix="edmcvkb-plugin-update-") as temp_dir:
                temp_path = Path(temp_dir)
                archive_path = temp_path / release.asset_name
                if not self._download_release_archive(release, archive_path):
                    return PluginUpdateResult(False, "Failed to download plugin update archive")

                extract_dir = temp_path / "extract"
                extract_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(archive_path, "r") as archive:
                    archive.extractall(extract_dir)

                payload_root = self._locate_payload_root(extract_dir)
                if not payload_root:
                    return PluginUpdateResult(False, "Downloaded archive does not contain a valid plugin package")

                self._install_payload(payload_root)
        except Exception as exc:
            self._log("error", f"Plugin update: install failed: {exc}")
            return PluginUpdateResult(False, f"Failed to install plugin update: {exc}")

        self._log("info", f"Plugin update: installed v{release.version}")
        return PluginUpdateResult(
            True,
            f"Plugin updated to v{release.version}. Restart EDMC to load the new version.",
            updated=True,
            latest_version=release.version,
        )

