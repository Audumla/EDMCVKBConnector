"""
VKB-Link lifecycle management (process control, INI sync, download/update).
"""

from __future__ import annotations

import base64
import configparser
import json
import re
import shutil
import struct
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

MEGA_API_URL = "https://g.api.mega.co.nz/cs"
MEGA_FOLDER_NODE = "980CgDDL"
MEGA_FOLDER_KEY_B64 = "AuSb0tItSbEQCmIIcA8U7w"
MEGA_VKB_LINK_RE = re.compile(r"VKB[- ]?Link\s*v?(\d+(?:\.\d+)+)", re.IGNORECASE)
MEGA_API_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Origin": "https://mega.nz",
    "Referer": "https://mega.nz/",
}


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
    mega_node_handle: Optional[str] = None
    mega_raw_key: Optional[bytes] = None


@dataclass(frozen=True)
class VKBLinkActionResult:
    success: bool
    message: str
    status: Optional[VKBLinkStatus] = None
    action_taken: str = "none"  # "none" | "started" | "restarted" | "stopped"


def _fetch_text(url: str, *, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "EDMCVKBConnector/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _extract_zip_links(text: str) -> list[str]:
    return list({m.group(0) for m in VKB_LINK_ZIP_RE.finditer(text or "")})


def _extract_onedrive_links(text: str) -> list[str]:
    return list({m.group(0) for m in ONEDRIVE_RE.finditer(text or "")})


def _extract_onedrive_links_for_software(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    software_idx = lowered.find("software")
    if software_idx == -1:
        return []
    firmware_idx = lowered.find("firmware", software_idx + 1)
    if firmware_idx == -1:
        firmware_idx = len(text)
    segment = text[software_idx:firmware_idx]
    links = _extract_onedrive_links(segment)
    if links:
        return links
    # Fallback: expand the window a bit to catch links near the label.
    start = max(0, software_idx - 600)
    end = min(len(text), firmware_idx + 600)
    segment = text[start:end]
    return _extract_onedrive_links(segment)


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


def _format_status(status: "VKBLinkStatus") -> str:
    return (
        "running="
        f"{status.running} "
        "exe_path="
        f"{status.exe_path or 'none'} "
        "install_dir="
        f"{status.install_dir or 'none'} "
        "version="
        f"{status.version or 'unknown'} "
        "managed="
        f"{status.managed}"
    )


# ---------------------------------------------------------------------------
# MEGA public-folder helpers
# ---------------------------------------------------------------------------

def _ensure_cryptography() -> bool:
    """Return True if the cryptography library is available.

    If not installed, silently attempts ``pip install cryptography`` using the
    running Python interpreter so no user action is required.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # noqa: F401
        return True
    except ImportError:
        pass
    logger.info("'cryptography' library not found; attempting silent pip install...")
    try:
        import importlib
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "cryptography"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            importlib.invalidate_caches()
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # noqa: F401
            logger.info("'cryptography' installed successfully")
            return True
        logger.warning(
            f"pip install cryptography failed (rc={result.returncode}): "
            f"{result.stderr[:300]}"
        )
    except Exception as e:
        logger.warning(f"Could not install 'cryptography': {e}")
    return False


def _mega_b64(s: str) -> bytes:
    """Decode MEGA's base64url (no padding, - and _ instead of + and /)."""
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * ((-len(s)) % 4)
    return base64.b64decode(s)


def _mega_decode_folder_key(b64_key: str) -> bytes:
    """Return the 16-byte AES-128 folder key from the URL fragment."""
    raw = _mega_b64(b64_key)
    if len(raw) == 32:
        return bytes(raw[i] ^ raw[i + 16] for i in range(16))
    return raw[:16]


def _mega_aes_ecb_dec(key16: bytes, block16: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    c = Cipher(algorithms.AES(key16), modes.ECB())
    d = c.decryptor()
    return d.update(block16) + d.finalize()


def _mega_aes_cbc_dec(key16: bytes, data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    iv = b"\x00" * 16
    pad = (-len(data)) % 16
    data = data + b"\x00" * pad
    c = Cipher(algorithms.AES(key16), modes.CBC(iv))
    d = c.decryptor()
    return d.update(data) + d.finalize()


def _mega_decrypt_node_key(enc_key_b64: str, folder_key: bytes) -> Optional[bytes]:
    """ECB-decrypt each 16-byte block of the node key; return raw bytes."""
    try:
        enc = _mega_b64(enc_key_b64)
    except Exception:
        return None
    dec = b""
    for i in range(0, len(enc), 16):
        blk = enc[i:i + 16]
        if len(blk) < 16:
            break
        dec += _mega_aes_ecb_dec(folder_key, blk)
    return dec if dec else None


def _mega_attr_key(raw_key: bytes, *, is_file: bool) -> bytes:
    """Return the 16-byte key used for attribute (and CTR) decryption."""
    if is_file and len(raw_key) >= 32:
        return bytes(raw_key[i] ^ raw_key[i + 16] for i in range(16))
    return raw_key[:16]


def _mega_ctr_nonce(raw_key: bytes) -> bytes:
    """Return the 16-byte AES-CTR nonce: bytes 16-23 of raw key + 8 zero bytes."""
    return raw_key[16:24] + b"\x00" * 8


def _mega_decrypt_attr(enc_attr_b64: str, attr_key16: bytes) -> str:
    """Decrypt MEGA attribute JSON and return the filename ('n' field)."""
    try:
        enc = _mega_b64(enc_attr_b64)
        dec = _mega_aes_cbc_dec(attr_key16, enc)
        text = dec.decode("utf-8", errors="replace").lstrip("\x00")
        m = re.search(r'MEGA\{(.+?)\}', text)
        if m:
            try:
                return json.loads("{" + m.group(1) + "}").get("n", "")
            except Exception:
                pass
        m2 = re.search(r'\{"n"\s*:\s*"([^"]+)"', text)
        if m2:
            return m2.group(1)
    except Exception:
        pass
    return ""


def _mega_api_post(payload: list, *, n: str = "") -> object:
    """POST to MEGA API and return parsed JSON response."""
    url = MEGA_API_URL + "?id=1" + (f"&n={n}" if n else "")
    body = json.dumps(payload).encode()
    req = Request(url, data=body, headers=MEGA_API_HEADERS)
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _mega_list_folder(folder_node: str, folder_key: bytes) -> list[VKBLinkRelease]:
    """List a MEGA public folder; return VKBLinkRelease entries for VKB-Link zips."""
    resp = _mega_api_post([{"a": "f", "c": 1, "r": 1}], n=folder_node)
    if isinstance(resp, list):
        resp = resp[0]
    if not isinstance(resp, dict):
        return []
    nodes = resp.get("f", [])
    releases: list[VKBLinkRelease] = []
    for node in nodes:
        if node.get("t") != 0:  # files only
            continue
        enc_k = node.get("k", "")
        if ":" in enc_k:
            enc_k = enc_k.split(":", 1)[1]
        enc_a = node.get("a", "")
        handle = node.get("h", "")
        if not (enc_k and enc_a and handle):
            continue
        raw_key = _mega_decrypt_node_key(enc_k, folder_key)
        if not raw_key:
            continue
        attr_key = _mega_attr_key(raw_key, is_file=True)
        name = _mega_decrypt_attr(enc_a, attr_key)
        if not name:
            continue
        m = MEGA_VKB_LINK_RE.search(name)
        if not m:
            continue
        version = m.group(1)
        filename = name if name.lower().endswith(".zip") else name + ".zip"
        releases.append(VKBLinkRelease(
            version=version,
            url=f"mega://{folder_node}/{handle}",
            filename=filename,
            mega_node_handle=handle,
            mega_raw_key=raw_key,
        ))
    return releases


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
        reason_label = reason or "unspecified"
        logger.info(
            f"VKB-Link ensure_running: reason={reason_label} host={host} port={port}"
        )
        status_before = self.get_status(check_running=True)
        logger.info(f"VKB-Link status before ensure: {_format_status(status_before)}")
        process = self._find_running_process()
        if process:
            logger.info(
                "VKB-Link process detected: "
                f"pid={process.pid or 'unknown'} exe_path={process.exe_path or 'unknown'}"
            )
            exe_path = process.exe_path or self._resolve_known_exe_path()
            if exe_path:
                logger.info(f"VKB-Link resolved exe path: {exe_path}")
                self._remember_exe_path(Path(exe_path))
            ini_path = self._resolve_ini_path(exe_path)
            if ini_path:
                logger.info(
                    f"Syncing VKB-Link INI at {ini_path} with host={host} port={port}"
                )
                self._write_ini(ini_path, host, port)
            else:
                logger.warning("No VKB-Link INI path resolved; skipping INI sync")
            restarted = False
            if (
                exe_path
                and self.config
                and bool(self.config.get("vkb_link_restart_on_failure", True))
            ):
                logger.info("Restart-on-failure enabled; restarting VKB-Link")
                restarted = self._restart_process(process, exe_path)
            else:
                logger.info("Restart-on-failure disabled or exe missing; not restarting")
            message = "VKB-Link running; INI updated"
            action = "restarted" if restarted else "none"
            if restarted:
                message = "VKB-Link restarted; INI updated"
            return VKBLinkActionResult(True, message, status=self.get_status(check_running=True), action_taken=action)

        exe_path = self._resolve_known_exe_path()
        if exe_path:
            logger.info(f"VKB-Link: starting from known path: {exe_path}")
            if self._start_process(exe_path):
                ini_path = self._resolve_ini_path(exe_path)
                if ini_path:
                    logger.info(
                        f"Syncing VKB-Link INI at {ini_path} with host={host} port={port}"
                    )
                    self._write_ini(ini_path, host, port)
                return VKBLinkActionResult(
                    True,
                    f"VKB-Link started from {Path(exe_path).name}",
                    status=self.get_status(check_running=True),
                    action_taken="started",
                )
            logger.warning(f"Failed to start VKB-Link from known path: {exe_path}")

        logger.info("No known VKB-Link executable; attempting download of latest release")
        release = self._fetch_latest_release()
        if not release:
            return VKBLinkActionResult(
                False,
                "Unable to locate VKB-Link or download the latest version",
                status=self.get_status(check_running=True),
                action_taken="none",
            )

        logger.info(f"Latest VKB-Link release detected: v{release.version}")
        exe_path = self._install_release(release)
        if not exe_path:
            return VKBLinkActionResult(False, "Failed to install VKB-Link", status=self.get_status(), action_taken="none")

        if self._start_process(exe_path):
            ini_path = self._resolve_ini_path(exe_path)
            if ini_path:
                logger.info(
                    f"Syncing VKB-Link INI at {ini_path} with host={host} port={port}"
                )
                self._write_ini(ini_path, host, port)
            return VKBLinkActionResult(
                True,
                f"Downloaded VKB-Link v{release.version} and started",
                status=self.get_status(check_running=True),
                action_taken="started",
            )

        return VKBLinkActionResult(
            False,
            f"Downloaded VKB-Link v{release.version} but failed to start",
            status=self.get_status(check_running=True),
            action_taken="none",
        )

    def update_to_latest(self, *, host: str, port: int) -> VKBLinkActionResult:
        logger.info(f"VKB-Link: checking for updates (host={host} port={port})")
        release = self._fetch_latest_release()
        if not release:
            return VKBLinkActionResult(False, "Unable to check for VKB-Link updates", action_taken="none")

        current = (self.config.get("vkb_link_version", "") or "").strip() if self.config else ""
        logger.info(
            "VKB-Link update: "
            f"current_version={current or 'unknown'} latest_version={release.version}"
        )
        if current and not _is_version_newer(release.version, current):
            return VKBLinkActionResult(
                True,
                f"VKB-Link is up to date (v{current})",
                status=self.get_status(check_running=True),
                action_taken="none",
            )

        process = self._find_running_process()
        if process:
            logger.info(
                "VKB-Link: stopping for update "
                f"(pid={process.pid or 'unknown'} exe_path={process.exe_path or 'unknown'})"
            )
            self._stop_process(process)
        else:
            logger.info("VKB-Link: no running process; proceeding with update")

        exe_path = self._install_release(release)
        if not exe_path:
            return VKBLinkActionResult(False, "Failed to install VKB-Link update", action_taken="none")

        if self._start_process(exe_path):
            ini_path = self._resolve_ini_path(exe_path)
            if ini_path:
                logger.info(
                    f"Syncing VKB-Link INI at {ini_path} with host={host} port={port}"
                )
                self._write_ini(ini_path, host, port)
            return VKBLinkActionResult(
                True,
                f"Updated VKB-Link to v{release.version} and restarted",
                status=self.get_status(check_running=True),
                action_taken="restarted",
            )

        return VKBLinkActionResult(
            False,
            f"Updated VKB-Link to v{release.version} but failed to start",
            status=self.get_status(check_running=True),
            action_taken="none",
        )

    def stop_running(self, *, reason: str = "") -> VKBLinkActionResult:
        reason_label = reason or "unspecified"
        logger.info(f"VKB-Link: stop requested (reason={reason_label})")
        process = self._find_running_process()
        if not process:
            logger.info("VKB-Link: not running; stop skipped")
            return VKBLinkActionResult(
                True,
                "VKB-Link is not running",
                status=self.get_status(check_running=True),
                action_taken="none",
            )
        logger.info(
            "VKB-Link: stopping process "
            f"(pid={process.pid or 'unknown'} exe_path={process.exe_path or 'unknown'})"
        )
        success = self._stop_process(process)
        if success:
            return VKBLinkActionResult(
                True,
                "VKB-Link stopped",
                status=self.get_status(check_running=True),
                action_taken="stopped",
            )
        return VKBLinkActionResult(
            False,
            "Failed to stop VKB-Link",
            status=self.get_status(check_running=True),
            action_taken="none",
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
            logger.info(f"Detected VKB-Link version from path: v{version}")
        else:
            logger.info(
                "VKB-Link version not detected from path; leaving stored version unchanged"
            )

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
                logger.info(f"Stopping VKB-Link process with command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info("VKB-Link stop command completed successfully")
                    return True
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                detail = stderr or stdout or "no output"
                logger.warning(
                    f"VKB-Link stop command returned {result.returncode}: {detail}"
                )
                return False
            except Exception as e:
                logger.warning(f"Failed to stop VKB-Link: {e}")
                return False
        else:
            try:
                cmd = ["pkill", "-f", "VKB-Link"]
                logger.info(f"Stopping VKB-Link process with command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info("VKB-Link stop command completed successfully")
                    return True
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                detail = stderr or stdout or "no output"
                logger.warning(
                    f"VKB-Link stop command returned {result.returncode}: {detail}"
                )
                return False
            except Exception as e:
                logger.warning(f"Failed to stop VKB-Link: {e}")
                return False

    def _restart_process(self, process: VKBLinkProcessInfo, exe_path: Optional[str]) -> bool:
        logger.info(
            "Restarting VKB-Link process: "
            f"pid={process.pid or 'unknown'} exe_path={exe_path or process.exe_path or 'unknown'}"
        )
        stopped = self._stop_process(process)
        if not stopped:
            logger.warning("VKB-Link restart aborted: stop step failed")
            return False
        if not exe_path:
            logger.info("VKB-Link restart completed with stop only (no exe path available)")
            return stopped
        time.sleep(1.0)
        started = self._start_process(exe_path)
        if started:
            logger.info("VKB-Link restart completed successfully")
        else:
            logger.warning("VKB-Link restart failed during start step")
        return started

    def _start_process(self, exe_path: str) -> bool:
        try:
            exe = Path(exe_path)
            logger.info(f"Starting VKB-Link process from: {exe}")
            process = subprocess.Popen([str(exe)], cwd=str(exe.parent))
            logger.info(f"Started VKB-Link process pid={process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start VKB-Link: {e}")
            return False

    def _fetch_latest_release(self) -> Optional[VKBLinkRelease]:
        # Primary: MEGA public folder (no auth required, reliable)
        if _ensure_cryptography():
            try:
                logger.info(
                    f"Fetching VKB-Link releases from MEGA folder {MEGA_FOLDER_NODE}"
                )
                folder_key = _mega_decode_folder_key(MEGA_FOLDER_KEY_B64)
                releases = _mega_list_folder(MEGA_FOLDER_NODE, folder_key)
                if releases:
                    releases.sort(key=lambda r: _parse_version(r.version), reverse=True)
                    latest = releases[0]
                    logger.info(
                        f"Selected VKB-Link v{latest.version} from MEGA "
                        f"(handle={latest.mega_node_handle})"
                    )
                    return latest
                logger.warning("No VKB-Link zip files found in MEGA folder")
            except Exception as e:
                logger.warning(f"MEGA folder listing failed: {e}")
        else:
            logger.warning("'cryptography' unavailable; skipping MEGA source")

        # Fallback: scrape VKB homepage for direct zip or OneDrive links
        logger.info(f"Falling back to scraping {VKB_LINK_HOME_URL}")
        try:
            homepage = _fetch_text(VKB_LINK_HOME_URL)
        except Exception as e:
            logger.warning(f"Failed to fetch VKB-Link home page: {e}")
            return None

        zip_links = _extract_zip_links(homepage)
        if not zip_links:
            onedrive_links = _extract_onedrive_links_for_software(homepage)
            if not onedrive_links:
                logger.warning(
                    "No Software OneDrive links found on VKB-Link homepage; "
                    "falling back to any OneDrive links"
                )
                onedrive_links = _extract_onedrive_links(homepage)
            logger.info(f"Discovered {len(onedrive_links)} OneDrive link(s) to scan")
            for link in onedrive_links:
                try:
                    onedrive_page = _fetch_text(link)
                except Exception:
                    continue
                zip_links.extend(_extract_zip_links(onedrive_page))
        logger.info(f"Discovered {len(zip_links)} VKB-Link archive link(s)")

        fallback_releases: list[VKBLinkRelease] = []
        for url in zip_links:
            decoded = unquote(url)
            parsed = urlparse(decoded)
            filename = Path(parsed.path).name or Path(decoded).name
            version = _extract_version(filename) or _extract_version(decoded)
            if not version:
                continue
            fallback_releases.append(VKBLinkRelease(version=version, url=url, filename=filename))

        if not fallback_releases:
            return None

        fallback_releases.sort(key=lambda r: _parse_version(r.version), reverse=True)
        latest = fallback_releases[0]
        logger.info(f"Selected VKB-Link release v{latest.version} from {latest.url}")
        return latest

    def _install_release(self, release: VKBLinkRelease) -> Optional[str]:
        install_dir = self._resolve_install_dir()
        logger.info(f"Installing VKB-Link v{release.version} into {install_dir}")
        install_dir.mkdir(parents=True, exist_ok=True)
        download_dir = install_dir / "_downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        archive_path = download_dir / release.filename

        if not archive_path.exists():
            if release.mega_node_handle:
                logger.info(
                    f"Downloading VKB-Link from MEGA node {release.mega_node_handle}"
                )
                if not self._mega_download(release, archive_path):
                    return None
            else:
                try:
                    logger.info(f"Downloading VKB-Link archive from {release.url}")
                    req = Request(release.url, headers={"User-Agent": "EDMCVKBConnector/1.0"})
                    with urlopen(req, timeout=60) as resp, open(archive_path, "wb") as f:
                        shutil.copyfileobj(resp, f)
                except Exception as e:
                    logger.error(f"Failed to download VKB-Link: {e}")
                    return None
        else:
            logger.info(f"Using cached VKB-Link archive: {archive_path}")

        temp_dir = Path(tempfile.mkdtemp(prefix="vkb-link-", dir=str(install_dir)))
        logger.info(f"Extracting VKB-Link archive to {temp_dir}")
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
                logger.info(f"Preserving existing VKB-Link INI: {preserved_ini}")
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
        logger.info(f"Clearing install directory {install_dir} (preserving downloads)")
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
        logger.info(f"Moving extracted files from {extracted_root} to {install_dir}")
        for child in extracted_root.iterdir():
            shutil.move(str(child), str(install_dir / child.name))

        # Restore INI if we preserved one
        if preserved_ini_copy and preserved_ini_copy.exists():
            target_ini_name = preserved_ini_name or preserved_ini_copy.name
            target_ini = install_dir / target_ini_name
            try:
                logger.info(f"Restoring preserved INI to {target_ini}")
                shutil.copyfile(str(preserved_ini_copy), str(target_ini))
            except Exception:
                pass
            try:
                preserved_ini_copy.unlink()
            except OSError:
                pass

        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Cleaned temporary extraction directory {temp_dir}")

        exe_path = self._find_exe_in_dir(install_dir, max_depth=3)
        if not exe_path:
            return None

        self._remember_exe_path(exe_path)
        if self.config:
            self.config.set("vkb_link_version", release.version)
        return str(exe_path)

    def _mega_download(self, release: VKBLinkRelease, archive_path: Path) -> bool:
        """Download and AES-CTR-decrypt a file from the MEGA public folder."""
        if not release.mega_node_handle or not release.mega_raw_key:
            logger.error("_mega_download: missing node handle or raw key")
            return False
        if not _ensure_cryptography():
            logger.error("'cryptography' library unavailable; cannot decrypt MEGA download")
            return False
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        try:
            logger.info(
                f"Requesting MEGA download URL for handle={release.mega_node_handle}"
            )
            resp = _mega_api_post(
                [{"a": "g", "g": 1, "n": release.mega_node_handle}],
                n=MEGA_FOLDER_NODE,
            )
            if isinstance(resp, list):
                resp = resp[0]
            if not isinstance(resp, dict) or "g" not in resp:
                logger.error(f"MEGA API did not return a download URL: {resp!r}")
                return False
            dl_url = resp["g"]
            logger.info(f"MEGA download URL obtained ({len(dl_url)} chars)")

            req = Request(dl_url, headers={"User-Agent": "EDMCVKBConnector/1.0"})
            with urlopen(req, timeout=120) as r:
                encrypted = r.read()
            logger.info(f"Downloaded {len(encrypted):,} encrypted bytes from MEGA")

            file_key = _mega_attr_key(release.mega_raw_key, is_file=True)
            nonce = _mega_ctr_nonce(release.mega_raw_key)
            cipher = Cipher(algorithms.AES(file_key), modes.CTR(nonce))
            dec = cipher.decryptor()
            decrypted = dec.update(encrypted) + dec.finalize()

            archive_path.write_bytes(decrypted)
            logger.info(
                f"Decrypted and saved VKB-Link archive to {archive_path} "
                f"({len(decrypted):,} bytes)"
            )
            return True
        except Exception as e:
            logger.error(f"MEGA download failed: {e}")
            return False

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
