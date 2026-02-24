"""
MEGA public folder downloader for software packages.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .downloaders import Downloader, DownloadItem

if TYPE_CHECKING:
    from logging import Logger


class MegaDownloader(Downloader):
    """Downloader implementation for MEGA public folders."""

    API_URL = "https://g.api.mega.co.nz/cs"
    API_HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Origin": "https://mega.nz",
        "Referer": "https://mega.nz/",
    }

    def __init__(self, folder_node: str, folder_key_b64: str, config: Any = None, logger: Optional[Logger] = None):
        self.folder_node = folder_node
        self.folder_key_b64 = folder_key_b64
        self.config = config
        self.logger = logger
        
        self._crypto_missing_warned = False
        self._crypto_install_attempted = False
        self._crypto_auto_install_failed = False
        self._crypto_install_lock = threading.Lock()
        
        # Version regex for files — requires the VKB-Link prefix to avoid
        # picking up version numbers from unrelated files in the same folder.
        self._version_re = re.compile(r"VKB[- ]?Link\s*v?(\d+(?:\.\d+)+)", re.IGNORECASE)

        # Lazy load pure python AES if needed
        try:
            from . import pure_python_aes as _pure_python_aes
            self._pure_python_aes = _pure_python_aes
        except Exception:
            self._pure_python_aes = None

    def is_available(self) -> bool:
        return self._ensure_cryptography()

    def list_items(self) -> List[DownloadItem]:
        if not self._ensure_cryptography():
            return []
        
        try:
            folder_key = self._mega_decode_folder_key(self.folder_key_b64)
            resp = self._mega_api_post([{"a": "f", "c": 1, "r": 1}], n=self.folder_node)
            if isinstance(resp, list):
                resp = resp[0]
            if not isinstance(resp, dict):
                return []
            
            nodes = resp.get("f", [])
            items: List[DownloadItem] = []
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
                
                raw_key = self._mega_decrypt_node_key(enc_k, folder_key)
                if not raw_key:
                    continue
                
                attr_key = self._mega_attr_key(raw_key, is_file=True)
                name = self._mega_decrypt_attr(enc_a, attr_key)
                if not name:
                    continue
                
                m = self._version_re.search(name)
                if not m:
                    # Skip files that don't look like VKB-Link releases.
                    # A loose regex here would pick up version numbers from
                    # unrelated files (e.g. "SomeLib-v0.94.zip" → "0.94")
                    # which can sort *higher* than a real release like "0.8.2"
                    # and trigger a spurious downgrade/corrupt install.
                    if self.logger:
                        self.logger.debug(f"MEGA: skipping non-VKB-Link file: {name!r}")
                    continue
                version = m.group(1)
                filename = name if name.lower().endswith(".zip") else name + ".zip"

                items.append(DownloadItem(
                    version=version,
                    filename=filename,
                    url=f"mega://{self.folder_node}/{handle}",
                    provider_data={
                        "handle": handle,
                        "raw_key": raw_key
                    }
                ))
            return items
        except Exception as e:
            if self.logger:
                self.logger.warning(f"MEGA folder listing failed: {e}")
            return []

    def download(self, item: DownloadItem, target_path: Path) -> bool:
        if not self._ensure_cryptography():
            return False
            
        handle = item.provider_data.get("handle")
        raw_key = item.provider_data.get("raw_key")
        
        if not handle or not raw_key:
            return False
        
        try:
            # Request download URL
            resp = self._mega_api_post(
                [{"a": "g", "g": 1, "n": handle}],
                n=self.folder_node,
            )
            if isinstance(resp, list):
                resp = resp[0]
            if not isinstance(resp, dict) or "g" not in resp:
                return False
            
            dl_url = resp["g"]
            req = urllib.request.Request(dl_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as response:
                encrypted = response.read()

            # Decrypt
            file_key = self._mega_attr_key(raw_key, is_file=True)
            nonce = self._mega_ctr_nonce(raw_key)
            decrypted = self._mega_aes_ctr_xor(file_key, nonce, encrypted)

            target_path.write_bytes(decrypted)
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"MEGA download failed: {e}")
            return False

    # --- Internal MEGA Logic ---

    def _mega_api_post(self, payload: list, *, n: str = "") -> object:
        url = self.API_URL + "?id=1" + (f"&n={n}" if n else "")
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, headers=self.API_HEADERS)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())

    def _mega_b64(self, s: str) -> bytes:
        s = s.replace("-", "+").replace("_", "/")
        s += "=" * ((-len(s)) % 4)
        return base64.b64decode(s)

    def _mega_decode_folder_key(self, b64_key: str) -> bytes:
        raw = self._mega_b64(b64_key)
        if len(raw) == 32:
            return bytes(raw[i] ^ raw[i + 16] for i in range(16))
        return raw[:16]

    def _mega_decrypt_node_key(self, enc_key_b64: str, folder_key: bytes) -> Optional[bytes]:
        try:
            enc = self._mega_b64(enc_key_b64)
        except Exception:
            return None
        dec = b""
        for i in range(0, len(enc), 16):
            blk = enc[i:i + 16]
            if len(blk) < 16:
                break
            dec += self._mega_aes_ecb_dec(folder_key, blk)
        return dec if dec else None

    def _mega_attr_key(self, raw_key: bytes, *, is_file: bool) -> bytes:
        if is_file and len(raw_key) >= 32:
            return bytes(raw_key[i] ^ raw_key[i + 16] for i in range(16))
        return raw_key[:16]

    def _mega_ctr_nonce(self, raw_key: bytes) -> bytes:
        return raw_key[16:24] + b"\x00" * 8

    def _mega_decrypt_attr(self, enc_attr_b64: str, attr_key16: bytes) -> str:
        try:
            enc = self._mega_b64(enc_attr_b64)
            dec = self._mega_aes_cbc_dec(attr_key16, enc)
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

    # --- Cryptography Helpers ---

    def _load_cryptography_primitives(self):
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            return Cipher, algorithms, modes
        except ImportError:
            return None

    def _has_pure_python_aes_backend(self) -> bool:
        if self._pure_python_aes is None:
            return False
        required = ("aes_ecb_decrypt", "aes_cbc_decrypt", "aes_ctr_xor")
        return all(callable(getattr(self._pure_python_aes, name, None)) for name in required)

    def _mega_aes_ecb_dec(self, key16: bytes, block16: bytes) -> bytes:
        crypto = self._load_cryptography_primitives()
        if crypto is not None:
            Cipher, algorithms, modes = crypto
            c = Cipher(algorithms.AES(key16), modes.ECB())
            d = c.decryptor()
            return d.update(block16) + d.finalize()
        if self._has_pure_python_aes_backend():
            return self._pure_python_aes.aes_ecb_decrypt(key16, block16)
        raise RuntimeError("No AES backend available for ECB decrypt")

    def _mega_aes_cbc_dec(self, key16: bytes, data: bytes) -> bytes:
        iv = b"\x00" * 16
        pad = (-len(data)) % 16
        data = data + b"\x00" * pad
        crypto = self._load_cryptography_primitives()
        if crypto is not None:
            Cipher, algorithms, modes = crypto
            c = Cipher(algorithms.AES(key16), modes.CBC(iv))
            d = c.decryptor()
            return d.update(data) + d.finalize()
        if self._has_pure_python_aes_backend():
            return self._pure_python_aes.aes_cbc_decrypt(key16, data, iv)
        raise RuntimeError("No AES backend available for CBC decrypt")

    def _mega_aes_ctr_xor(self, key16: bytes, nonce16: bytes, data: bytes) -> bytes:
        crypto = self._load_cryptography_primitives()
        if crypto is not None:
            Cipher, algorithms, modes = crypto
            cipher = Cipher(algorithms.AES(key16), modes.CTR(nonce16))
            dec = cipher.decryptor()
            return dec.update(data) + dec.finalize()
        if self._has_pure_python_aes_backend():
            return self._pure_python_aes.aes_ctr_xor(key16, data, nonce16)
        raise RuntimeError("No AES backend available for CTR decrypt")

    def _ensure_cryptography(self) -> bool:
        auto_install = False
        if self.config:
            auto_install = self.config.get("vkb_link_auto_install_cryptography", False)

        if self._load_cryptography_primitives() is not None:
            self._crypto_auto_install_failed = False
            return True
        if self._has_pure_python_aes_backend():
            self._crypto_auto_install_failed = False
            return True

        if not auto_install:
            self._warn_cryptography_unavailable_once()
            return False

        with self._crypto_install_lock:
            if self._load_cryptography_primitives() is not None:
                self._crypto_auto_install_failed = False
                return True
            if self._has_pure_python_aes_backend():
                self._crypto_auto_install_failed = False
                return True

            if not self._crypto_install_attempted:
                self._crypto_install_attempted = True
                install_cmd = self._resolve_cryptography_install_command()
                if install_cmd:
                    if self.logger:
                        self.logger.info("Attempting background install of 'cryptography' for MEGA support")
                    try:
                        subprocess.run(
                            install_cmd, 
                            capture_output=True, 
                            text=True, 
                            timeout=120,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
                        )
                        if self._load_cryptography_primitives() is not None:
                            self._crypto_auto_install_failed = False
                            return True
                    except Exception:
                        pass
                self._crypto_auto_install_failed = True

        self._warn_cryptography_unavailable_once()
        return False

    def _warn_cryptography_unavailable_once(self) -> None:
        if self._crypto_missing_warned:
            return
        if self.logger:
            self.logger.warning("No AES backend available for MEGA download/update.")
        self._crypto_missing_warned = True

    def _resolve_cryptography_install_command(self) -> Optional[list[str]]:
        seen: set[str] = set()
        candidates: list[str] = []
        for attr in ("executable", "_base_executable"):
            value = getattr(sys, attr, None)
            if not value:
                continue
            value = str(value)
            if value in seen:
                continue
            seen.add(value)
            candidates.append(value)

        for executable in candidates:
            name = Path(executable).name.lower()
            stem = Path(executable).stem.lower()
            if stem.startswith("python") or name.startswith("python"):
                return [executable, "-m", "pip", "install", "--disable-pip-version-check", "--quiet", "cryptography"]
        return None
