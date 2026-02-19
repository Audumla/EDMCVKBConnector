"""
VKB-Link lifecycle management (process control, INI sync, download/update).
"""

from __future__ import annotations

import configparser
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from . import plugin_logger

logger = plugin_logger(__name__)

VKB_LINK_HOME_URL = "https://www.njoy32.vkb-sim.pro/home"
VKB_LINK_EXE_NAMES = ("VKB-Link.exe", "VKBLink.exe", "VKB-Link64.exe", "VKBLink64.exe")
VKB_LINK_INI_NAMES = ("VKBLink.ini", "VKB-Link.ini", "VKBLink64.ini", "VKB-Link64.ini")
VKB_LINK_ZIP_RE = re.compile(
    r"https?://[^\"'\\s>]+?VKB[- ]?Link[^\"'\\s>]+?\\.zip",
    re.IGNORECASE,
)
VKB_LINK_VERSION_RE = re.compile(r"VKB[- ]?Link\\s*v?(\\d+(?:\\.\\d+)+)", re.IGNORECASE)
ONEDRIVE_RE = re.compile(r"https?://(?:1drv\\.ms|onedrive\\.live\\.com)[^\"'\\s>]+", re.IGNORECASE)


@dataclass(frozen=True)
class VKBLinkProcessInfo:
    pid: Optional[int]
    exe_path: Optional[str]


@dataclass(frozen=True)
class VKBLinkStatus:
    exe_path: Optional[str]
    install_dir: Optional[str]
    version: Optional[str]
    running: Optional[bool]
    managed: bool


@dataclass(frozen=True)
class VKBLinkRelease:
    version: str
    url: str
    filename: str


@dataclass(frozen=True)
class VKBLinkActionResult:
    success: bool
    message: str
    status: Optional[VKBLinkStatus] = None


def _fetch_text(url: str, *, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "EDMCVKBConnector/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _extract_zip_links(text: str) -> list[str]:
    return list({m.group(0) for m in VKB_LINK_ZIP_RE.finditer(text or "")})


def _extract_onedrive_links(text: str) -> list[str]:
    return list({m.group(0) for m in ONEDRIVE_RE.finditer(text or "")})


def _extract_version(text: str) -> Optional[str]:
    match = VKB_LINK_VERSION_RE.search(text or "")
    if match:
        return match.group(1)
    return None


def _parse_version(value: str) -> tuple[int, ...]:
    tokens = re.split(r"[\\.-]", value or "")
    numbers = [int(tok) for tok in tokens if tok.isdigit()]
    return tuple(numbers) if numbers else (0,)


def _is_version_newer(candidate: str, current: str) -> bool:
    return _parse_version(candidate) > _parse_version(current)


def _is_path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


class VKBLinkManager:
    """Manage VKB-Link process, configuration INI, and update/download flow."""

    def __init__(self, config, plugin_dir: Path) -> None:
        self.config = config
        self.plugin_dir = Path(plugin_dir)
        self.managed_dir = self.plugin_dir / "vkb-link"

    def get_status(self, *, check_running: bool = False) -> VKBLinkStatus:
        exe_path = (self.config.get("vkb_link_exe_path", "") or "").strip() if self.config else ""
        install_dir = (self.config.get("vkb_link_install_dir", "") or "").strip() if self.config else ""
        version = (self.config.get("vkb_link_version", "") or "").strip() if self.config else ""
        managed = bool(self.config.get("vkb_link_managed", False)) if self.config else False
        running = None
        if check_running:
            running = self.is_running()
        return VKBLinkStatus(
            exe_path=exe_path or None,
            install_dir=install_dir or None,
            version=version or None,
            running=running,
            managed=managed,
        )

    def ensure_running(self, *, host: str, port: int, reason: str = "") -> VKBLinkActionResult:
        logger.info(f"VKB-Link recovery triggered ({reason})")
        process = self._find_running_process()
        if process:
            exe_path = process.exe_path or self._resolve_known_exe_path()
            if exe_path:
                self._remember_exe_path(Path(exe_path))
            ini_path = self._resolve_ini_path(exe_path)
            if ini_path:
                self._write_ini(ini_path, host, port)
            restarted = False
            if (
                exe_path
                and self.config
                and bool(self.config.get("vkb_link_restart_on_failure", True))
            ):
                restarted = self._restart_process(process, exe_path)
            message = "VKB-Link running; INI updated"
            if restarted:
                message = "VKB-Link restarted; INI updated"
            return VKBLinkActionResult(True, message, status=self.get_status(check_running=True))

        exe_path = self._resolve_known_exe_path()
        if exe_path:
            if self._start_process(exe_path):
                ini_path = self._resolve_ini_path(exe_path)
                if ini_path:
                    self._write_ini(ini_path, host, port)
                return VKBLinkActionResult(
                    True,
                    f"VKB-Link started from {Path(exe_path).name}",
                    status=self.get_status(check_running=True),
                )

        release = self._fetch_latest_release()
        if not release:
            return VKBLinkActionResult(
                False,
                "Unable to locate VKB-Link or download the latest version",
                status=self.get_status(check_running=True),
            )

        exe_path = self._install_release(release)
        if not exe_path:
            return VKBLinkActionResult(False, "Failed to install VKB-Link", status=self.get_status())

        if self._start_process(exe_path):
            ini_path = self._resolve_ini_path(exe_path)
            if ini_path:
                self._write_ini(ini_path, host, port)
            return VKBLinkActionResult(
                True,
                f"Downloaded VKB-Link v{release.version} and started",
                status=self.get_status(check_running=True),
            )

        return VKBLinkActionResult(
            False,
            f"Downloaded VKB-Link v{release.version} but failed to start",
            status=self.get_status(check_running=True),
        )

    def update_to_latest(self, *, host: str, port: int) -> VKBLinkActionResult:
        release = self._fetch_latest_release()
        if not release:
            return VKBLinkActionResult(False, "Unable to check for VKB-Link updates")

        current = (self.config.get("vkb_link_version", "") or "").strip() if self.config else ""
        if current and not _is_version_newer(release.version, current):
            return VKBLinkActionResult(
                True,
                f"VKB-Link is up to date (v{current})",
                status=self.get_status(check_running=True),
            )

        process = self._find_running_process()
        if process:
            self._stop_process(process)

        exe_path = self._install_release(release)
        if not exe_path:
            return VKBLinkActionResult(False, "Failed to install VKB-Link update")

        if self._start_process(exe_path):
            ini_path = self._resolve_ini_path(exe_path)
            if ini_path:
                self._write_ini(ini_path, host, port)
            return VKBLinkActionResult(
                True,
                f"Updated VKB-Link to v{release.version} and restarted",
                status=self.get_status(check_running=True),
            )

        return VKBLinkActionResult(
            False,
            f"Updated VKB-Link to v{release.version} but failed to start",
            status=self.get_status(check_running=True),
        )

    def relocate_install(self, destination: Path) -> VKBLinkActionResult:
        destination = Path(destination)
        if not destination.exists():
            destination.mkdir(parents=True, exist_ok=True)
        if any(destination.iterdir()):
            return VKBLinkActionResult(False, "Destination folder is not empty")

        current_dir = (self.config.get("vkb_link_install_dir", "") or "").strip() if self.config else ""
        if not current_dir:
            return VKBLinkActionResult(False, "No VKB-Link installation to relocate")

        current_path = Path(current_dir)
        if not current_path.exists():
            return VKBLinkActionResult(False, "Current VKB-Link folder does not exist")
        if current_path.resolve() == destination.resolve():
            return VKBLinkActionResult(True, "VKB-Link is already at that location")

        try:
            for child in current_path.iterdir():
                shutil.move(str(child), str(destination / child.name))
            try:
                current_path.rmdir()
            except OSError:
                pass
            self._remember_install_dir(destination)
            exe_path = self._find_exe_in_dir(destination)
            if exe_path:
                self._remember_exe_path(exe_path)
                ini_path = self._find_ini_near_exe(exe_path)
                if ini_path and self.config:
                    self.config.set("vkb_ini_path", str(ini_path))
            return VKBLinkActionResult(
                True,
                f"Relocated VKB-Link to {destination}",
                status=self.get_status(check_running=True),
            )
        except Exception as e:
            logger.error(f"Failed to relocate VKB-Link: {e}")
            return VKBLinkActionResult(False, f"Failed to relocate VKB-Link: {e}")

    def set_known_exe_path(self, exe_path: str) -> VKBLinkActionResult:
        exe_path = Path(exe_path)
        if not exe_path.exists():
            return VKBLinkActionResult(False, "Selected VKB-Link executable not found")
        self._remember_exe_path(exe_path)
        ini_path = self._find_ini_near_exe(exe_path)
        if ini_path and self.config:
            self.config.set("vkb_ini_path", str(ini_path))
        return VKBLinkActionResult(True, f"VKB-Link set to {exe_path.name}", status=self.get_status())

    def is_running(self) -> bool:
        return self._find_running_process() is not None

    def _remember_install_dir(self, install_dir: Path) -> None:
        if not self.config:
            return
        self.config.set("vkb_link_install_dir", str(install_dir))
        self.config.set("vkb_link_managed", _is_path_within(install_dir, self.plugin_dir))

    def _remember_exe_path(self, exe_path: Path) -> None:
        if not self.config:
            return
        self.config.set("vkb_link_exe_path", str(exe_path))
        self.config.set("vkb_link_install_dir", str(exe_path.parent))
        self.config.set("vkb_link_managed", _is_path_within(exe_path.parent, self.plugin_dir))
        version = _extract_version(exe_path.parent.name) or _extract_version(exe_path.name)
        if version:
            self.config.set("vkb_link_version", version)

    def _resolve_known_exe_path(self) -> Optional[str]:
        if not self.config:
            return None
        exe_path = (self.config.get("vkb_link_exe_path", "") or "").strip()
        if exe_path and Path(exe_path).exists():
            return exe_path

        install_dir = (self.config.get("vkb_link_install_dir", "") or "").strip()
        if install_dir:
            exe = self._find_exe_in_dir(Path(install_dir))
            if exe:
                self._remember_exe_path(exe)
                return str(exe)

        if self.managed_dir.exists():
            exe = self._find_exe_in_dir(self.managed_dir)
            if exe:
                self._remember_exe_path(exe)
                return str(exe)

        return None

    def _find_exe_in_dir(self, directory: Path, *, max_depth: int = 2) -> Optional[Path]:
        if not directory.exists():
            return None
        for name in VKB_LINK_EXE_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate

        queue: list[tuple[Path, int]] = [(directory, 0)]
        seen: set[Path] = set()
        while queue:
            current, depth = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            for name in VKB_LINK_EXE_NAMES:
                candidate = current / name
                if candidate.exists():
                    return candidate
            if depth >= max_depth:
                continue
            try:
                for child in current.iterdir():
                    if child.is_dir():
                        queue.append((child, depth + 1))
            except OSError:
                continue
        return None

    def _resolve_ini_path(self, exe_path: Optional[str]) -> Optional[Path]:
        if not self.config:
            return None
        saved = (self.config.get("vkb_ini_path", "") or "").strip()
        if saved and Path(saved).exists():
            return Path(saved)

        if exe_path:
            candidate = self._find_ini_near_exe(Path(exe_path))
            if candidate and self.config:
                self.config.set("vkb_ini_path", str(candidate))
            return candidate
        return None

    def _find_ini_near_exe(self, exe_path: Path) -> Optional[Path]:
        exe_dir = exe_path.parent
        for name in VKB_LINK_INI_NAMES:
            candidate = exe_dir / name
            if candidate.exists():
                return candidate
        try:
            for candidate in exe_dir.glob("*.ini"):
                if "vkb" in candidate.name.lower():
                    return candidate
        except OSError:
            pass
        return None

    def _write_ini(self, ini_path: Path, host: str, port: int) -> None:
        cp = configparser.ConfigParser()
        cp.read(ini_path, encoding="utf-8")
        if "TCP" not in cp:
            cp.add_section("TCP")
        cp.set("TCP", "Adress", host)
        cp.set("TCP", "Port", str(port))
        with open(ini_path, "w", encoding="utf-8") as f:
            cp.write(f)
        logger.info(f"Updated VKB-Link INI: {ini_path}")

    def _find_running_process(self) -> Optional[VKBLinkProcessInfo]:
        if sys.platform == "win32":
            return self._find_running_process_windows()
        return self._find_running_process_posix()

    def _find_running_process_windows(self) -> Optional[VKBLinkProcessInfo]:
        # Attempt PowerShell first for PID+Path
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process -Name 'VKB-Link' -ErrorAction SilentlyContinue | "
                "Select-Object Id,Path | ConvertTo-Json -Compress",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = result.stdout.strip()
            if output:
                data = json.loads(output)
                if isinstance(data, dict):
                    data = [data]
                if isinstance(data, list):
                    for entry in data:
                        pid = entry.get("Id")
                        path = entry.get("Path")
                        return VKBLinkProcessInfo(pid=int(pid) if pid else None, exe_path=path)
        except Exception:
            pass

        # Fallback to WMIC for PID+Path
        try:
            cmd = [
                "wmic",
                "process",
                "where",
                "name='VKB-Link.exe'",
                "get",
                "ExecutablePath,ProcessId",
                "/FORMAT:LIST",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.stdout:
                path = None
                pid = None
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.lower().startswith("executablepath="):
                        path = line.split("=", 1)[1].strip()
                    elif line.lower().startswith("processid="):
                        pid = line.split("=", 1)[1].strip()
                if path or pid:
                    return VKBLinkProcessInfo(pid=int(pid) if pid else None, exe_path=path)
        except Exception:
            pass

        # Fallback to tasklist to detect running process
        try:
            cmd = ["tasklist", "/FI", "IMAGENAME eq VKB-Link.exe", "/FO", "CSV"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if "VKB-Link.exe" in (result.stdout or ""):
                return VKBLinkProcessInfo(pid=None, exe_path=None)
        except Exception:
            pass

        return None

    def _find_running_process_posix(self) -> Optional[VKBLinkProcessInfo]:
        try:
            cmd = ["pgrep", "-f", "VKB-Link"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pid = result.stdout.strip().splitlines()[0]
                return VKBLinkProcessInfo(pid=int(pid), exe_path=None)
        except Exception:
            pass
        return None

    def _stop_process(self, process: VKBLinkProcessInfo) -> bool:
        if sys.platform == "win32":
            cmd = None
            if process.pid:
                cmd = ["taskkill", "/PID", str(process.pid), "/T", "/F"]
            else:
                cmd = ["taskkill", "/IM", "VKB-Link.exe", "/T", "/F"]
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return True
            except Exception as e:
                logger.warning(f"Failed to stop VKB-Link: {e}")
                return False
        else:
            try:
                cmd = ["pkill", "-f", "VKB-Link"]
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return True
            except Exception as e:
                logger.warning(f"Failed to stop VKB-Link: {e}")
                return False

    def _restart_process(self, process: VKBLinkProcessInfo, exe_path: Optional[str]) -> bool:
        stopped = self._stop_process(process)
        if not exe_path:
            return stopped
        time.sleep(1.0)
        return self._start_process(exe_path)

    def _start_process(self, exe_path: str) -> bool:
        try:
            exe = Path(exe_path)
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
            return True
        except Exception as e:
            logger.error(f"Failed to start VKB-Link: {e}")
            return False

    def _fetch_latest_release(self) -> Optional[VKBLinkRelease]:
        try:
            homepage = _fetch_text(VKB_LINK_HOME_URL)
        except Exception as e:
            logger.warning(f"Failed to fetch VKB-Link home page: {e}")
            return None

        zip_links = _extract_zip_links(homepage)
        if not zip_links:
            for link in _extract_onedrive_links(homepage):
                try:
                    onedrive_page = _fetch_text(link)
                except Exception:
                    continue
                zip_links.extend(_extract_zip_links(onedrive_page))

        releases: list[VKBLinkRelease] = []
        for url in zip_links:
            decoded = unquote(url)
            parsed = urlparse(decoded)
            filename = Path(parsed.path).name or Path(decoded).name
            version = _extract_version(filename) or _extract_version(decoded)
            if not version:
                continue
            releases.append(VKBLinkRelease(version=version, url=url, filename=filename))

        if not releases:
            return None

        releases.sort(key=lambda r: _parse_version(r.version), reverse=True)
        return releases[0]

    def _install_release(self, release: VKBLinkRelease) -> Optional[str]:
        install_dir = self._resolve_install_dir()
        install_dir.mkdir(parents=True, exist_ok=True)
        download_dir = install_dir / "_downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        archive_path = download_dir / release.filename

        if not archive_path.exists():
            try:
                req = Request(release.url, headers={"User-Agent": "EDMCVKBConnector/1.0"})
                with urlopen(req, timeout=60) as resp, open(archive_path, "wb") as f:
                    shutil.copyfileobj(resp, f)
            except Exception as e:
                logger.error(f"Failed to download VKB-Link: {e}")
                return None

        temp_dir = Path(tempfile.mkdtemp(prefix="vkb-link-", dir=str(install_dir)))
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(temp_dir)
        except Exception as e:
            logger.error(f"Failed to unpack VKB-Link archive: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        # Preserve existing INI if present
        preserved_ini_copy: Optional[Path] = None
        preserved_ini_name: Optional[str] = None
        if install_dir.exists():
            preserved_ini = self._find_ini_in_dir(install_dir)
            if preserved_ini:
                preserved_ini_name = preserved_ini.name
                try:
                    tmp = tempfile.NamedTemporaryFile(
                        prefix="vkb-link-ini-",
                        suffix=preserved_ini.suffix,
                        delete=False,
                    )
                    tmp.close()
                    preserved_ini_copy = Path(tmp.name)
                    shutil.copyfile(str(preserved_ini), str(preserved_ini_copy))
                except Exception:
                    preserved_ini_copy = None

        # Clear install dir (keep downloads)
        for child in install_dir.iterdir():
            if child.name == "_downloads" or child == temp_dir:
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass

        extracted_root = self._select_extracted_root(temp_dir)
        for child in extracted_root.iterdir():
            shutil.move(str(child), str(install_dir / child.name))

        # Restore INI if we preserved one
        if preserved_ini_copy and preserved_ini_copy.exists():
            target_ini_name = preserved_ini_name or preserved_ini_copy.name
            target_ini = install_dir / target_ini_name
            try:
                shutil.copyfile(str(preserved_ini_copy), str(target_ini))
            except Exception:
                pass
            try:
                preserved_ini_copy.unlink()
            except OSError:
                pass

        shutil.rmtree(temp_dir, ignore_errors=True)

        exe_path = self._find_exe_in_dir(install_dir, max_depth=3)
        if not exe_path:
            return None

        self._remember_exe_path(exe_path)
        if self.config:
            self.config.set("vkb_link_version", release.version)
        return str(exe_path)

    def _find_ini_in_dir(self, directory: Path) -> Optional[Path]:
        for name in VKB_LINK_INI_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate
        try:
            for candidate in directory.glob("*.ini"):
                if "vkb" in candidate.name.lower():
                    return candidate
        except OSError:
            return None
        return None

    def _select_extracted_root(self, temp_dir: Path) -> Path:
        entries = [p for p in temp_dir.iterdir()]
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if not p.is_dir()]
        if len(dirs) == 1 and not files:
            return dirs[0]
        return temp_dir

    def _resolve_install_dir(self) -> Path:
        if not self.config:
            return self.managed_dir
        configured = (self.config.get("vkb_link_install_dir", "") or "").strip()
        if configured:
            path = Path(configured)
            self._remember_install_dir(path)
            return path
        self._remember_install_dir(self.managed_dir)
        return self.managed_dir
