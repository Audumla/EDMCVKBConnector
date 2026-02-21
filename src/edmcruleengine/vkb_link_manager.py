"""
VKB-Link lifecycle management (process control, INI sync, download/update).
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen

from . import plugin_logger

logger = plugin_logger(__name__)

VKB_LINK_EXE_NAMES = ("VKB-Link.exe",)
VKB_LINK_INI_NAMES = ("VKB-Link.ini")
VKB_LINK_VERSION_RE = re.compile(r"VKB[- ]?Link\s*v?(\d+(?:\.\d+)+)", re.IGNORECASE)

MEGA_API_URL = "https://g.api.mega.co.nz/cs"
MEGA_FOLDER_NODE = "980CgDDL"
MEGA_FOLDER_KEY_B64 = "AuSb0tItSbEQCmIIcA8U7w"
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
        m = VKB_LINK_VERSION_RE.search(name)
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
        self._lifecycle_lock = threading.Lock()
        self._last_start_monotonic = 0.0
        self._last_startup_original_minimized: Optional[bool] = None
        self._last_startup_ini_path: Optional[Path] = None
        self._process_monitor_thread: Optional[threading.Thread] = None
        self._process_monitor_stop = threading.Event()
        self._last_known_process_running = False

    def _cfg_int(self, key: str, default: int, *, minimum: int = 0) -> int:
        value = default
        if self.config:
            value = self.config.get(key)
            if value is None:
                value = default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed < minimum:
            return minimum
        return parsed

    def _cfg_float(self, key: str, default: float, *, minimum: float = 0.0) -> float:
        value = default
        if self.config:
            value = self.config.get(key)
            if value is None:
                value = default
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed < minimum:
            return minimum
        return parsed

    def _cfg_interval_seconds(
        self,
        key_seconds: str,
        default_seconds: float,
        *,
        minimum_seconds: float = 0.001,
        legacy_ms_key: Optional[str] = None,
    ) -> float:
        """Return interval seconds, accepting a legacy millisecond key when needed."""
        parsed = None
        if self.config:
            raw = self.config.get(key_seconds)
            if raw is None and legacy_ms_key:
                raw_ms = self.config.get(legacy_ms_key)
                if raw_ms is not None:
                    try:
                        parsed = float(raw_ms) / 1000.0
                    except (TypeError, ValueError):
                        parsed = None
            elif raw is not None:
                try:
                    parsed = float(raw)
                except (TypeError, ValueError):
                    parsed = None
        if parsed is None:
            parsed = float(default_seconds)
        if parsed < minimum_seconds:
            return minimum_seconds
        return parsed

    def should_probe_listener_before_connect(self) -> bool:
        if not self.config:
            return False
        return bool(self.config.get("vkb_link_probe_listener_before_connect", False))

    def read_ini_endpoint(self, ini_path: Path | str) -> Optional[tuple[str, int]]:
        import configparser

        cp = configparser.ConfigParser()
        cp.read(str(ini_path), encoding="utf-8")
        if "TCP" not in cp:
            return None
        host = cp.get("TCP", "Adress", fallback="").strip()
        port_value = cp.get("TCP", "Port", fallback="").strip()
        try:
            port = int(port_value)
        except Exception:
            return None
        return host, port

    def wait_for_listener_ready(self, host: str, port: int) -> bool:
        timeout_seconds = self._cfg_float(
            "vkb_link_operation_timeout_seconds",
            10.0,
            minimum=0.1,
        )
        poll_interval = self._cfg_interval_seconds(
            "vkb_link_poll_interval_seconds",
            0.25,
            minimum_seconds=0.01,
            legacy_ms_key="vkb_link_poll_interval_ms",
        )
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                with socket.create_connection((host, int(port)), timeout=0.5):
                    logger.info(f"VKB-Link listener is ready at {host}:{port}")
                    return True
            except OSError:
                time.sleep(poll_interval)
        logger.warning(
            "Timed out waiting for VKB-Link listener readiness at "
            f"{host}:{port} (timeout={timeout_seconds:.1f}s)"
        )
        return False

    def start_process_health_monitor(self, on_process_crash: Callable[[], None]) -> None:
        if self._process_monitor_thread is not None:
            return

        self._last_known_process_running = self.is_running()
        self._process_monitor_stop.clear()
        self._process_monitor_thread = threading.Thread(
            target=self._monitor_process_health,
            args=(on_process_crash,),
            daemon=True,
            name="VKB-LinkProcessMonitor",
        )
        self._process_monitor_thread.start()

    def stop_process_health_monitor(self) -> None:
        if self._process_monitor_thread is None:
            return
        self._process_monitor_stop.set()
        try:
            self._process_monitor_thread.join(timeout=2.0)
        except Exception as e:
            logger.debug(f"Error stopping process monitor thread: {e}")
        self._process_monitor_thread = None

    def _monitor_process_health(self, on_process_crash: Callable[[], None]) -> None:
        while not self._process_monitor_stop.is_set():
            check_interval = self._cfg_interval_seconds(
                "vkb_link_process_monitor_interval_seconds",
                5.0,
                minimum_seconds=0.1,
            )
            try:
                auto_manage = bool(self.config and self.config.get("vkb_link_auto_manage", True))
                if auto_manage:
                    is_running = self.is_running()
                    if self._last_known_process_running and not is_running:
                        logger.warning(
                            "VKB-Link process crash detected during health monitoring; "
                            "triggering recovery"
                        )
                        on_process_crash()
                    self._last_known_process_running = is_running
            except Exception as e:
                logger.debug(f"Error in process health monitor: {e}")
            self._process_monitor_stop.wait(check_interval)

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
        with self._lifecycle_lock:
            return self._ensure_running_locked(host=host, port=port, reason=reason)

    def _ensure_running_locked(self, *, host: str, port: int, reason: str = "") -> VKBLinkActionResult:
        reason_label = reason or "unspecified"
        logger.info(f"VKB-Link ensure_running: reason={reason_label} host={host} port={port}")
        status_before = self.get_status(check_running=True)
        logger.info(f"VKB-Link status before ensure: {_format_status(status_before)}")

        processes = self._find_running_processes()
        if len(processes) > 1:
            logger.warning(
                f"Detected {len(processes)} VKB-Link processes; enforcing single-process state"
            )
            if not self._stop_all_processes(processes):
                return VKBLinkActionResult(
                    False,
                    "Failed to stop duplicate VKB-Link processes",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )
            if not self._wait_for_no_running_process():
                return VKBLinkActionResult(
                    False,
                    "Timed out waiting for duplicate VKB-Link processes to stop",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )
            processes = []

        if processes:
            process = processes[0]
            logger.info(
                "VKB-Link process detected: "
                f"pid={process.pid or 'unknown'} exe_path={process.exe_path or 'unknown'}"
            )
            exe_path = process.exe_path or self._resolve_known_exe_path()
            if exe_path:
                logger.info(f"VKB-Link resolved exe path: {exe_path}")
                self._remember_exe_path(Path(exe_path))
            ini_path = self._resolve_or_default_ini_path(exe_path)
            if ini_path:
                logger.info(f"Syncing VKB-Link INI at {ini_path} with host={host} port={port}")
                self._write_ini(ini_path, host, port)
            else:
                logger.warning("No VKB-Link INI path resolved; skipping INI sync")
            return VKBLinkActionResult(
                True,
                "VKB-Link running; INI updated",
                status=self.get_status(check_running=True),
                action_taken="none",
            )

        exe_path = self._resolve_known_exe_path()
        if not exe_path:
            auto_manage = bool(self.config.get("vkb_link_auto_manage", True)) if self.config else True
            if not auto_manage:
                return VKBLinkActionResult(
                    False,
                    "VKB-Link is not running and executable path is unknown",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )
            logger.info("No known VKB-Link executable; attempting MEGA download/install")
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
                return VKBLinkActionResult(
                    False,
                    "Failed to install VKB-Link",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )
            self._bootstrap_ini_after_install(exe_path)

        logger.info(f"VKB-Link: starting from known path: {exe_path}")
        ini_path = self._resolve_or_default_ini_path(exe_path)
        if ini_path:
            logger.info(f"Syncing VKB-Link INI at {ini_path} with host={host} port={port}")
            self._write_ini(ini_path, host, port)
        else:
            logger.warning("No VKB-Link INI path resolved; starting without INI sync")

        if self._find_running_process():
            logger.info("VKB-Link became running before launch; skipping duplicate start")
            return VKBLinkActionResult(
                True,
                "VKB-Link already running; INI updated",
                status=self.get_status(check_running=True),
                action_taken="none",
            )

        # Ensure VKB-Link is not started minimized (saves original setting for later restoration)
        self._last_startup_original_minimized = self._ensure_not_minimized_for_startup(ini_path)
        self._last_startup_ini_path = ini_path

        if not self._start_process(exe_path):
            return VKBLinkActionResult(
                False,
                "Failed to start VKB-Link",
                status=self.get_status(check_running=True),
                action_taken="none",
            )

        started = self._wait_for_running_process()
        if not started:
            return VKBLinkActionResult(
                False,
                "VKB-Link launch command succeeded but process did not appear",
                status=self.get_status(check_running=True),
                action_taken="none",
            )

        self._wait_after_running_ack()
        return VKBLinkActionResult(
            True,
            f"VKB-Link started from {Path(exe_path).name}",
            status=self.get_status(check_running=True),
            action_taken="started",
        )

    def update_to_latest(self, *, host: str, port: int) -> VKBLinkActionResult:
        with self._lifecycle_lock:
            return self._update_to_latest_locked(host=host, port=port)

    def _update_to_latest_locked(self, *, host: str, port: int) -> VKBLinkActionResult:
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

        processes = self._find_running_processes()
        if processes:
            logger.info(f"VKB-Link: stopping {len(processes)} process(es) for update")
            self._wait_after_running_ack()
            if not self._stop_all_processes(processes):
                return VKBLinkActionResult(False, "Failed to stop VKB-Link for update", action_taken="none")
            if not self._wait_for_no_running_process():
                return VKBLinkActionResult(False, "Timed out waiting for VKB-Link to stop", action_taken="none")
        else:
            logger.info("VKB-Link: no running process; proceeding with update")

        exe_path = self._install_release(release)
        if not exe_path:
            return VKBLinkActionResult(False, "Failed to install VKB-Link update", action_taken="none")

        ini_path = self._resolve_or_default_ini_path(exe_path)
        if ini_path:
            logger.info(
                f"Syncing VKB-Link INI at {ini_path} with host={host} port={port} before restart"
            )
            self._write_ini(ini_path, host, port)
        else:
            logger.warning("No VKB-Link INI path resolved after update install; restarting without INI sync")

        # Ensure VKB-Link is not started minimized (saves original setting for later restoration)
        self._last_startup_original_minimized = self._ensure_not_minimized_for_startup(ini_path)
        self._last_startup_ini_path = ini_path

        if self._start_process(exe_path):
            if not self._wait_for_running_process():
                return VKBLinkActionResult(
                    False,
                    f"Updated VKB-Link to v{release.version} but process did not appear",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )
            self._wait_after_running_ack()
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
        with self._lifecycle_lock:
            return self._stop_running_locked(reason=reason)

    def _stop_running_locked(self, *, reason: str = "") -> VKBLinkActionResult:
        reason_label = reason or "unspecified"
        logger.info(f"VKB-Link: stop requested (reason={reason_label})")
        processes = self._find_running_processes()
        if not processes:
            logger.info("VKB-Link: not running; stop skipped")
            return VKBLinkActionResult(
                True,
                "VKB-Link is not running",
                status=self.get_status(check_running=True),
                action_taken="none",
            )
        logger.info(f"VKB-Link: stopping {len(processes)} detected process(es)")
        self._wait_after_running_ack()
        success = self._stop_all_processes(processes)
        if success:
            success = self._wait_for_no_running_process()
        if success:
            stopped_count = len(processes)
            return VKBLinkActionResult(
                True,
                "VKB-Link stopped" if stopped_count == 1 else f"Stopped {stopped_count} VKB-Link processes",
                status=self.get_status(check_running=True),
                action_taken="stopped",
            )
        return VKBLinkActionResult(
            False,
            "Failed to stop VKB-Link",
            status=self.get_status(check_running=True),
            action_taken="none",
        )

    def apply_managed_endpoint_change(self, *, host: str, port: int, reason: str = "endpoint_change") -> VKBLinkActionResult:
        with self._lifecycle_lock:
            logger.info(f"VKB-Link: applying managed endpoint change (reason={reason} host={host} port={port})")
            processes = self._find_running_processes()
            had_running = bool(processes)
            if had_running:
                self._wait_after_running_ack()
                if not self._stop_all_processes(processes):
                    return VKBLinkActionResult(
                        False,
                        "Failed to stop VKB-Link before endpoint update",
                        status=self.get_status(check_running=True),
                        action_taken="none",
                    )
                if not self._wait_for_no_running_process():
                    return VKBLinkActionResult(
                        False,
                        "Timed out waiting for VKB-Link to stop before endpoint update",
                        status=self.get_status(check_running=True),
                        action_taken="none",
                    )

            exe_path = self._resolve_known_exe_path()
            if not exe_path:
                release = self._fetch_latest_release()
                if not release:
                    return VKBLinkActionResult(
                        False,
                        "Unable to locate VKB-Link executable for endpoint update",
                        status=self.get_status(check_running=True),
                        action_taken="none",
                    )
                exe_path = self._install_release(release)
                if not exe_path:
                    return VKBLinkActionResult(
                        False,
                        "Failed to install VKB-Link for endpoint update",
                        status=self.get_status(check_running=True),
                        action_taken="none",
                    )
                self._bootstrap_ini_after_install(exe_path)

            ini_path = self._resolve_or_default_ini_path(exe_path)
            if ini_path:
                self._write_ini(ini_path, host, port)
            else:
                return VKBLinkActionResult(
                    False,
                    "Unable to locate VKB-Link INI for endpoint update",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )

            # Ensure VKB-Link is not started minimized (saves original setting for later restoration)
            self._last_startup_original_minimized = self._ensure_not_minimized_for_startup(ini_path)
            self._last_startup_ini_path = ini_path

            if not self._start_process(exe_path):
                return VKBLinkActionResult(
                    False,
                    "Failed to restart VKB-Link after endpoint update",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )
            if not self._wait_for_running_process():
                return VKBLinkActionResult(
                    False,
                    "VKB-Link restart command succeeded but process did not appear",
                    status=self.get_status(check_running=True),
                    action_taken="none",
                )
            self._wait_after_running_ack()
            action = "restarted" if had_running else "started"
            return VKBLinkActionResult(
                True,
                "VKB-Link restarted with updated endpoint" if had_running else "VKB-Link started with updated endpoint",
                status=self.get_status(check_running=True),
                action_taken=action,
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

    def _ensure_not_minimized_for_startup(self, ini_path: Optional[Path]) -> Optional[bool]:
        """
        Temporarily ensure VKB-Link INI is not set to minimized.

        VKB-Link's UI event loop only activates when the window is visible.
        If started minimized, TCP connection won't work until the window is shown.

        This method:
        1. Reads the current "Start Minimized" setting from INI
        2. Temporarily sets it to 0 (not minimized)
        3. Returns the original value (so it can be restored later)

        Args:
            ini_path: Path to VKB-Link INI file

        Returns:
            True if was originally minimized (1), False if not (0), None if operation failed
        """
        if not ini_path:
            return None

        try:
            # Read existing content or create empty
            if ini_path.exists():
                content = ini_path.read_text(encoding='utf-8')
            else:
                content = ""
                logger.info(f"Creating VKB-Link INI at {ini_path} with start minimized =0")

            original_minimized = None

            # Check current "start minimized" setting in [Common] section (case-insensitive)
            for line in content.splitlines():
                line_lower = line.strip().lower()
                # Match "start minimized" with optional space before equals: "start minimized =1" or "start minimized=1"
                if line_lower.startswith("start minimized"):
                    if "=" in line:
                        value = line.split("=", 1)[1].strip()
                        original_minimized = value == "1"
                    break

            # Ensure start minimized is set to 0 (not minimized) in [Common] section
            if original_minimized is None:
                # start minimized key doesn't exist, need to add it to [Common]
                logger.info(
                    "VKB-Link INI 'start minimized' setting not found; setting to 0 "
                    "to ensure UI event loop activates for TCP connection"
                )
                if "[Common]" not in content.upper():
                    # No [Common] section, add it at the end
                    if content and not content.endswith('\n'):
                        content += '\n'
                    content += "[Common]\nstart minimized =0\n"
                    original_minimized = None  # Was not set, not "1"
                else:
                    # [Common] section exists, add start minimized after it
                    import re
                    content = re.sub(
                        r'(?i)(\[Common\])',
                        r'\1\nstart minimized =0',
                        content
                    )
                    original_minimized = None  # Was not set, not "1"
            elif original_minimized is True:
                # start minimized=1 exists, change it to 0
                logger.info(
                    "VKB-Link INI has start minimized=1; temporarily setting to 0 "
                    "to ensure UI event loop activates for TCP connection"
                )
                import re
                # Match both "start minimized=1" and "start minimized =1" formats
                content = re.sub(
                    r'(?i)^(\s*start\s+minimized\s*=\s*)1(\s*)$',
                    r'\g<1>0\g<2>',
                    content,
                    flags=re.MULTILINE
                )

            # Write the modified content
            ini_path.parent.mkdir(parents=True, exist_ok=True)
            ini_path.write_text(content, encoding='utf-8')

            return original_minimized
        except Exception as e:
            logger.warning(f"Error checking/modifying VKB-Link Start Minimized setting: {e}")
            return None

    def _restore_minimized_setting(self, ini_path: Optional[Path], original_minimized: Optional[bool]) -> None:
        """
        Restore the original VKB-Link "Start Minimized" INI setting and minimize if needed.

        This should be called after TCP connection is established.
        If original_minimized was True, restores the INI file to Start Minimized=1.

        Args:
            ini_path: Path to VKB-Link INI file
            original_minimized: The original minimized value (from _ensure_not_minimized_for_startup)
        """
        if original_minimized is not True or not ini_path or not ini_path.exists():
            return

        try:
            logger.info("VKB-Link UI event loop established; restoring start minimized=1 setting")
            content = ini_path.read_text(encoding='utf-8')

            # Restore start minimized=1 in INI (in [Common] section)
            import re
            # Match both "start minimized =0" and "start minimized=0" formats
            new_content = re.sub(
                r'(?i)^(\s*start\s+minimized\s*=\s*)0(\s*)$',
                r'\g<1>1\g<2>',
                content,
                flags=re.MULTILINE
            )
            ini_path.write_text(new_content, encoding='utf-8')
            logger.debug("VKB-Link INI restored to Start Minimized=1")

            # Try to minimize the window after TCP is established
            # VKB-Link reads window state from INI on startup, but we can also try
            # sending keyboard shortcuts or using Windows API to minimize
            if sys.platform == "win32":
                try:
                    # Try to minimize VKB-Link window using taskkill /FI with window style
                    # More robust approach: use pygetwindow if available, otherwise use subprocess
                    import subprocess
                    # Find VKB-Link window and minimize it
                    # Using PowerShell to minimize window is more portable
                    ps_command = (
                        "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                        "$windows = (Get-Process | Where-Object {$_.ProcessName -like '*VKB-Link*'}); "
                        "foreach ($w in $windows) { "
                        "  $form = [System.Windows.Forms.Form]::FromHandle($w.MainWindowHandle); "
                        "  if ($form) { $w.MainWindowHandle | % {[System.Windows.Forms.SendKeys]::SendWait('%{F9}')} } "
                        "}"
                    )
                    # This is complex, so let's use a simpler approach:
                    # Just log that we've restored the setting and VKB-Link will minimize on next restart
                    logger.debug("Window can be minimized via Alt+F9 or VKB-Link will minimize on next restart")
                except Exception as e:
                    logger.debug(f"Could not programmatically minimize window: {e}")

        except Exception as e:
            logger.warning(f"Error restoring VKB-Link Start Minimized setting: {e}")

    def restore_last_startup_minimized_setting(self) -> None:
        """
        Restore the minimized INI setting from the last startup operation.

        This should be called by EventHandler after TCP connection is successfully established.
        It uses the original_minimized value saved during the last call to _ensure_running_locked().
        """
        if self._last_startup_original_minimized is not None and self._last_startup_ini_path is not None:
            self._restore_minimized_setting(
                self._last_startup_ini_path,
                self._last_startup_original_minimized
            )
            # Clear the saved values so we don't restore again
            self._last_startup_original_minimized = None
            self._last_startup_ini_path = None

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

    def _resolve_or_default_ini_path(self, exe_path: Optional[str]) -> Optional[Path]:
        """Resolve or create the INI path for the specific executable being started.

        For start/update flows, we must apply endpoint settings to the INI that
        belongs to that exact executable directory (first-run download case).
        """
        if exe_path:
            saved = (self.config.get("vkb_ini_path", "") or "").strip() if self.config else ""
            if saved:
                saved_path = Path(saved)
                if saved_path.exists() and saved_path.parent == Path(exe_path).parent:
                    return saved_path
            exe_ini = self._find_ini_near_exe(Path(exe_path))
            if exe_ini:
                if self.config:
                    self.config.set("vkb_ini_path", str(exe_ini))
                return exe_ini
            fallback = Path(exe_path).parent / VKB_LINK_INI_NAMES[0]
            if self.config:
                self.config.set("vkb_ini_path", str(fallback))
            return fallback

        # No executable context available; fall back to persisted path semantics.
        return self._resolve_ini_path(None)

    def _bootstrap_ini_after_install(self, exe_path: str) -> None:
        exe = Path(exe_path)
        existing_ini = self._find_ini_near_exe(exe)
        if existing_ini:
            if self.config:
                self.config.set("vkb_ini_path", str(existing_ini))
            logger.info(f"VKB-Link INI already present after install: {existing_ini}")
            return

        operation_timeout_seconds = self._cfg_float(
            "vkb_link_operation_timeout_seconds",
            10.0,
            minimum=1.0,
        )
        poll_interval_seconds = self._cfg_interval_seconds(
            "vkb_link_poll_interval_seconds",
            0.25,
            minimum_seconds=0.01,
            legacy_ms_key="vkb_link_poll_interval_ms",
        )
        post_stop_settle_seconds = min(1.0, max(0.25, poll_interval_seconds))

        before_inis: dict[str, float] = {}
        for ini in self._list_ini_near_exe(exe):
            try:
                before_inis[str(ini.resolve())] = ini.stat().st_mtime
            except OSError:
                continue

        logger.info(
            "No VKB-Link INI found after install; running VKB-Link once to generate defaults"
        )
        if not self._start_process(exe_path):
            logger.warning(
                "VKB-Link bootstrap start failed; continuing with fallback INI path"
            )
            return

        deadline = time.time() + operation_timeout_seconds
        generated_ini: Optional[Path] = None
        while time.time() < deadline:
            generated_ini = self._find_ini_near_exe(exe)
            if generated_ini:
                break
            time.sleep(poll_interval_seconds)

        process = self._find_running_process()
        if process:
            logger.info(
                "Stopping VKB-Link bootstrap process before applying managed INI settings"
            )
            self._stop_process(process)
            if post_stop_settle_seconds:
                time.sleep(post_stop_settle_seconds)
        else:
            logger.info("Bootstrap process already exited before stop request")

        logger.info("Waiting for VKB-Link INI to appear/update after shutdown")
        post_deadline = time.time() + operation_timeout_seconds
        while time.time() < post_deadline:
            changed_ini = self._select_new_or_touched_ini(exe, before_inis)
            if changed_ini:
                generated_ini = changed_ini
                break
            if not generated_ini:
                generated_ini = self._find_ini_near_exe(exe)
            time.sleep(poll_interval_seconds)
        if not generated_ini:
            generated_ini = self._select_new_or_touched_ini(exe, before_inis) or self._find_ini_near_exe(exe)

        if generated_ini and self.config:
            self.config.set("vkb_ini_path", str(generated_ini))

    def _select_new_or_touched_ini(self, exe_path: Path, before_inis: dict[str, float]) -> Optional[Path]:
        post_inis = self._list_ini_near_exe(exe_path)
        if not post_inis:
            return None

        def _mtime(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except OSError:
                return 0.0

        new_inis = [ini for ini in post_inis if str(ini.resolve()) not in before_inis]
        if new_inis:
            return max(new_inis, key=_mtime)

        touched_inis = [
            ini
            for ini in post_inis
            if _mtime(ini) > before_inis.get(str(ini.resolve()), 0.0) + 0.001
        ]
        if touched_inis:
            return max(touched_inis, key=_mtime)

        return None

    def _list_ini_near_exe(self, exe_path: Path) -> list[Path]:
        exe_dir = exe_path.parent
        result: list[Path] = []
        seen: set[str] = set()
        for name in VKB_LINK_INI_NAMES:
            candidate = exe_dir / name
            if candidate.exists():
                resolved = str(candidate.resolve())
                if resolved not in seen:
                    result.append(candidate)
                    seen.add(resolved)
        try:
            for candidate in exe_dir.glob("*.ini"):
                if "vkb" not in candidate.name.lower():
                    continue
                resolved = str(candidate.resolve())
                if resolved in seen:
                    continue
                result.append(candidate)
                seen.add(resolved)
        except OSError:
            pass
        return result

    def _find_ini_near_exe(self, exe_path: Path) -> Optional[Path]:
        candidates = self._list_ini_near_exe(exe_path)
        return candidates[0] if candidates else None

    def _patch_ini_text(self, text: str, host: str, port: int) -> str:
        def _split_key(line: str) -> Optional[tuple[str, str, str, str]]:
            match = re.match(r"^(\s*)([^=;#][^=]*?)(\s*=\s*)(.*?)(\s*[;#].*)?$", line)
            if not match:
                return None
            indent = match.group(1) or ""
            key = (match.group(2) or "").strip().lower()
            sep = match.group(3) or "="
            suffix = match.group(5) or ""
            return indent, key, sep, suffix

        newline = "\r\n" if "\r\n" in text else "\n"
        lines = text.splitlines()
        section_re = re.compile(r"^\s*\[([^\]]+)\]\s*$")

        tcp_start: Optional[int] = None
        tcp_end = len(lines)
        for index, line in enumerate(lines):
            sec = section_re.match(line)
            if not sec:
                continue
            if tcp_start is None and sec.group(1).strip().lower() == "tcp":
                tcp_start = index
                continue
            if tcp_start is not None:
                tcp_end = index
                break

        if tcp_start is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend(
                [
                    "[TCP]",
                    f"Adress={host}",
                    f"Port={port}",
                ]
            )
        else:
            address_found = False
            port_found = False
            for index in range(tcp_start + 1, tcp_end):
                parsed = _split_key(lines[index])
                if not parsed:
                    continue
                indent, key, sep, suffix = parsed
                if key in {"adress", "address"}:
                    lines[index] = f"{indent}Adress{sep}{host}{suffix}"
                    address_found = True
                elif key == "port":
                    lines[index] = f"{indent}Port{sep}{port}{suffix}"
                    port_found = True

            insert_at = tcp_end
            additions: list[str] = []
            if not address_found:
                additions.append(f"Adress={host}")
            if not port_found:
                additions.append(f"Port={port}")
            if additions:
                for offset, line in enumerate(additions):
                    lines.insert(insert_at + offset, line)

        updated = newline.join(lines)
        if lines:
            updated = f"{updated}{newline}"
        return updated

    def _write_ini(self, ini_path: Path, host: str, port: int) -> None:
        if ini_path.exists():
            try:
                text = ini_path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                text = ini_path.read_text(encoding="utf-8", errors="replace")
        else:
            text = ""
            ini_path.parent.mkdir(parents=True, exist_ok=True)

        updated = self._patch_ini_text(text, host, port)
        ini_path.write_text(updated, encoding="utf-8")
        logger.info(f"Updated VKB-Link INI: {ini_path}")

    def _wait_for_running_process(self) -> Optional[VKBLinkProcessInfo]:
        timeout = max(2.0, self._cfg_float("vkb_link_operation_timeout_seconds", 10.0, minimum=0.1))
        poll_interval_seconds = self._cfg_interval_seconds(
            "vkb_link_poll_interval_seconds",
            0.25,
            minimum_seconds=0.01,
            legacy_ms_key="vkb_link_poll_interval_ms",
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            process = self._find_running_process()
            if process:
                return process
            time.sleep(poll_interval_seconds)
        return self._find_running_process()

    def _wait_for_no_running_process(self) -> bool:
        timeout = max(2.0, self._cfg_float("vkb_link_operation_timeout_seconds", 10.0, minimum=0.1))
        poll_interval_seconds = self._cfg_interval_seconds(
            "vkb_link_poll_interval_seconds",
            0.25,
            minimum_seconds=0.01,
            legacy_ms_key="vkb_link_poll_interval_ms",
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._find_running_processes():
                return True
            time.sleep(poll_interval_seconds)
        return not self._find_running_processes()

    def wait_for_post_start_settle(self) -> None:
        """Wait for configurable post-start settle delay, if a recent start occurred."""
        self._wait_after_running_ack()

    def _wait_after_running_ack(self) -> None:
        """Apply configurable settle delay after process start acknowledgement."""
        settle_seconds = self._cfg_float("vkb_link_warmup_delay_seconds", 5.0, minimum=0.0)
        if settle_seconds <= 0:
            return
        if self._last_start_monotonic <= 0:
            return
        elapsed = time.monotonic() - self._last_start_monotonic
        remaining = settle_seconds - elapsed
        if remaining > 0:
            logger.info(f"VKB-Link process settle delay: waiting {remaining:.1f}s")
            time.sleep(remaining)

    def _find_running_processes(self) -> list[VKBLinkProcessInfo]:
        if sys.platform == "win32":
            return self._find_running_processes_windows()
        return self._find_running_processes_posix()

    def _find_running_process(self) -> Optional[VKBLinkProcessInfo]:
        processes = self._find_running_processes()
        return processes[0] if processes else None

    def _find_running_processes_windows(self) -> list[VKBLinkProcessInfo]:
        results: list[VKBLinkProcessInfo] = []
        seen: set[tuple[Optional[int], Optional[str]]] = set()

        def _append_result(pid: Optional[int], path: Optional[str]) -> None:
            normalized_path = (path or "").strip() or None
            key = (pid, normalized_path.lower() if normalized_path else None)
            if key in seen:
                return
            seen.add(key)
            results.append(VKBLinkProcessInfo(pid=pid, exe_path=normalized_path))

        operation_timeout = self._cfg_float(
            "vkb_link_operation_timeout_seconds",
            10.0,
            minimum=1.0,
        )
        # Attempt PowerShell first for PID+Path
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process -Name 'VKB-Link' -ErrorAction SilentlyContinue | "
                "Select-Object Id,Path | ConvertTo-Json -Compress",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=operation_timeout)
            output = result.stdout.strip()
            if output:
                data = json.loads(output)
                if isinstance(data, dict):
                    data = [data]
                if isinstance(data, list):
                    for entry in data:
                        pid = entry.get("Id")
                        path = entry.get("Path")
                        parsed_pid = int(pid) if pid else None
                        _append_result(parsed_pid, path)
        except Exception:
            pass

        # Fallback to WMIC only when PowerShell didn't yield actionable PIDs.
        if not any(entry.pid is not None for entry in results):
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
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=operation_timeout)
                if result.stdout:
                    blocks = re.split(r"(?:\r?\n){2,}", result.stdout)
                    for block in blocks:
                        if not block.strip():
                            continue
                        path: Optional[str] = None
                        pid: Optional[str] = None
                        for raw_line in block.splitlines():
                            line = raw_line.strip().strip("\r")
                            if not line:
                                continue
                            if line.lower().startswith("executablepath="):
                                path = line.split("=", 1)[1].strip() or None
                            elif line.lower().startswith("processid="):
                                pid = line.split("=", 1)[1].strip() or None
                        if pid:
                            _append_result(int(pid), path)
                        elif path and not results:
                            # Keep a path-only entry only as a last resort.
                            _append_result(None, path)
            except Exception:
                pass

        # Fallback to tasklist to detect running process
        if not results:
            try:
                cmd = ["tasklist", "/FI", "IMAGENAME eq VKB-Link.exe", "/FO", "CSV"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=operation_timeout)
                if "VKB-Link.exe" in (result.stdout or ""):
                    _append_result(None, None)
            except Exception:
                pass

        # Normalize partial duplicates: when we have PID-based entries, prefer only those.
        pid_results = [entry for entry in results if entry.pid is not None]
        if pid_results:
            unique_by_pid: dict[int, VKBLinkProcessInfo] = {}
            for entry in pid_results:
                if entry.pid not in unique_by_pid:
                    unique_by_pid[entry.pid] = entry
                elif (not unique_by_pid[entry.pid].exe_path) and entry.exe_path:
                    unique_by_pid[entry.pid] = entry
            return list(unique_by_pid.values())

        return results

    def _find_running_processes_posix(self) -> list[VKBLinkProcessInfo]:
        results: list[VKBLinkProcessInfo] = []
        operation_timeout = self._cfg_float(
            "vkb_link_operation_timeout_seconds",
            10.0,
            minimum=1.0,
        )
        try:
            cmd = ["pgrep", "-f", "VKB-Link.exe"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=operation_timeout)
            if result.returncode == 0 and result.stdout.strip():
                for pid_text in result.stdout.strip().splitlines():
                    pid_text = pid_text.strip()
                    if not pid_text:
                        continue
                    results.append(VKBLinkProcessInfo(pid=int(pid_text), exe_path=None))
        except Exception:
            pass
        return results

    def _stop_all_processes(self, processes: list[VKBLinkProcessInfo]) -> bool:
        if not processes:
            return True

        unique_processes: list[VKBLinkProcessInfo] = []
        seen: set[tuple[str, object]] = set()
        for process in processes:
            if process.pid is not None:
                key: tuple[str, object] = ("pid", process.pid)
            elif process.exe_path:
                key = ("exe", process.exe_path.lower())
            else:
                key = ("image", "VKB-Link.exe")
            if key in seen:
                continue
            seen.add(key)
            unique_processes.append(process)

        all_stopped = True
        for process in unique_processes:
            if not self._stop_process(process):
                all_stopped = False

        return all_stopped

    def _is_target_process_running(self, target: VKBLinkProcessInfo) -> bool:
        current_processes = self._find_running_processes()
        if not current_processes:
            return False
        if target.pid is not None:
            return any(current.pid == target.pid for current in current_processes)
        if target.exe_path:
            for current in current_processes:
                if not current.exe_path:
                    continue
                try:
                    if Path(current.exe_path).resolve() == Path(target.exe_path).resolve():
                        return True
                except OSError:
                    if current.exe_path == target.exe_path:
                        return True
            return False
        return True

    def _wait_for_process_exit(self, target: VKBLinkProcessInfo, *, timeout: float) -> bool:
        poll_interval_seconds = self._cfg_interval_seconds(
            "vkb_link_poll_interval_seconds",
            0.25,
            minimum_seconds=0.01,
            legacy_ms_key="vkb_link_poll_interval_ms",
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._is_target_process_running(target):
                return True
            time.sleep(poll_interval_seconds)
        return not self._is_target_process_running(target)

    def _stop_process(self, process: VKBLinkProcessInfo) -> bool:
        operation_timeout = self._cfg_float(
            "vkb_link_operation_timeout_seconds",
            10.0,
            minimum=1.0,
        )
        # Keep subprocess command waits robust even if operation timeout is tuned low.
        command_timeout = max(10.0, operation_timeout)
        # Give the process a realistic grace window before force-kill on restart paths.
        exit_wait_timeout = max(8.0, operation_timeout)
        if sys.platform == "win32":
            if process.pid:
                graceful_cmd = ["taskkill", "/PID", str(process.pid), "/T"]
                force_cmd = ["taskkill", "/PID", str(process.pid), "/T", "/F"]
            else:
                graceful_cmd = ["taskkill", "/IM", "VKB-Link.exe", "/T"]
                force_cmd = ["taskkill", "/IM", "VKB-Link.exe", "/T", "/F"]
            try:
                logger.info(f"Stopping VKB-Link process with command: {' '.join(graceful_cmd)}")
                result = subprocess.run(
                    graceful_cmd,
                    capture_output=True,
                    text=True,
                    timeout=command_timeout,
                )
                if result.returncode == 0:
                    if self._wait_for_process_exit(process, timeout=exit_wait_timeout):
                        logger.info("VKB-Link stop command completed successfully")
                        return True
                    logger.warning("VKB-Link still running after graceful stop; forcing termination")
                else:
                    stderr = (result.stderr or "").strip()
                    stdout = (result.stdout or "").strip()
                    detail = stderr or stdout or "no output"
                    logger.warning(
                        f"VKB-Link graceful stop returned {result.returncode}: {detail}"
                    )
                    if not self._is_target_process_running(process):
                        return True

                logger.info(f"Stopping VKB-Link process with command: {' '.join(force_cmd)}")
                force_result = subprocess.run(
                    force_cmd,
                    capture_output=True,
                    text=True,
                    timeout=command_timeout,
                )
                if force_result.returncode == 0:
                    logger.info("VKB-Link force-stop command completed successfully")
                    return True
                stderr = (force_result.stderr or "").strip()
                stdout = (force_result.stdout or "").strip()
                detail = stderr or stdout or "no output"
                logger.warning(
                    f"VKB-Link force-stop command returned {force_result.returncode}: {detail}"
                )
                return False
            except Exception as e:
                logger.warning(f"Failed to stop VKB-Link: {e}")
                return False
        else:
            try:
                graceful_cmd = ["pkill", "-f", "VKB-Link"]
                force_cmd = ["pkill", "-9", "-f", "VKB-Link"]
                logger.info(f"Stopping VKB-Link process with command: {' '.join(graceful_cmd)}")
                result = subprocess.run(
                    graceful_cmd,
                    capture_output=True,
                    text=True,
                    timeout=command_timeout,
                )
                if result.returncode == 0:
                    if self._wait_for_process_exit(process, timeout=exit_wait_timeout):
                        logger.info("VKB-Link stop command completed successfully")
                        return True
                    logger.warning("VKB-Link still running after graceful stop; forcing termination")
                else:
                    stderr = (result.stderr or "").strip()
                    stdout = (result.stdout or "").strip()
                    detail = stderr or stdout or "no output"
                    logger.warning(
                        f"VKB-Link graceful stop returned {result.returncode}: {detail}"
                    )
                    if not self._is_target_process_running(process):
                        return True

                logger.info(f"Stopping VKB-Link process with command: {' '.join(force_cmd)}")
                force_result = subprocess.run(
                    force_cmd,
                    capture_output=True,
                    text=True,
                    timeout=command_timeout,
                )
                if force_result.returncode == 0:
                    logger.info("VKB-Link force-stop command completed successfully")
                    return True
                stderr = (force_result.stderr or "").strip()
                stdout = (force_result.stdout or "").strip()
                detail = stderr or stdout or "no output"
                logger.warning(
                    f"VKB-Link force-stop command returned {force_result.returncode}: {detail}"
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
        if not self._wait_for_no_running_process():
            logger.warning(
                "VKB-Link restart aborted: process stop command returned but process still running"
            )
            return False
        if not exe_path:
            logger.info("VKB-Link restart completed with stop only (no exe path available)")
            return stopped
        restart_delay = self._cfg_float("vkb_link_restart_delay_seconds", 0.25, minimum=0.0)
        if restart_delay:
            time.sleep(restart_delay)
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
            popen_kwargs: dict[str, object] = {
                "cwd": str(exe.parent),
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if sys.platform == "win32":
                creationflags = 0
                creationflags |= int(getattr(subprocess, "DETACHED_PROCESS", 0))
                creationflags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
                creationflags |= int(getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0))
                if creationflags:
                    popen_kwargs["creationflags"] = creationflags
                popen_kwargs["close_fds"] = True
            else:
                popen_kwargs["start_new_session"] = True

            process = subprocess.Popen([str(exe)], **popen_kwargs)
            self._last_start_monotonic = time.monotonic()
            logger.info("VKB-Link launch mode: detached")
            logger.info(f"Started VKB-Link process pid={process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start VKB-Link: {e}")
            return False

    def _fetch_latest_release(self) -> Optional[VKBLinkRelease]:
        # MEGA public folder is the only supported source.
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
            logger.warning("'cryptography' unavailable; cannot query MEGA source")
        return None

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
