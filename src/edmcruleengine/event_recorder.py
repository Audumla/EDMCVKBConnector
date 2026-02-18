"""
Event Recorder for EDMC VKB Connector.

Records all incoming EDMC events to a JSONL file for debugging and analysis.
Each line is a self-contained JSON object with timestamp, source, event type,
and the anonymized event payload. Personal information is automatically redacted.
"""

import copy
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import plugin_logger

logger = plugin_logger(__name__)

# Keys whose values are always commander-identifying
_COMMANDER_KEYS = {"Commander", "FID"}

# Keys whose string values may contain filesystem paths or environment info
_PATH_KEYS = {
    "filename", "Filename", "FileName",
    "path", "Path",
    "directory", "Directory",
    "gameversion", "build",
}

# Regex patterns for environment-identifying strings
_WIN_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\\\/:*?\"<>|\r\n]+\\)*[^\\\/:*?\"<>|\r\n]*")
_UNIX_HOME_RE = re.compile(r"/home/[^/\s]+")
_IP_RE = re.compile(
    r"\b(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)"
    r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b"
)


class EventRecorder:
    """Records EDMC events to a JSONL file."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._file = None
        self._output_path: Optional[Path] = None
        self._event_count: int = 0
        self._last_event_type: str = ""
        self._recording: bool = False

        # Anonymization is mandatory
        self.mock_commander: str = "CMDR_Redacted"
        self.mock_fid: str = "F0000000"

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def event_count(self) -> int:
        return self._event_count

    @property
    def last_event_type(self) -> str:
        return self._last_event_type

    @property
    def output_path(self) -> Optional[Path]:
        return self._output_path

    def start(self, output_path: Path) -> None:
        """Start recording events to the given file path."""
        with self._lock:
            if self._recording:
                return
            try:
                self._output_path = output_path
                self._file = open(output_path, "a", encoding="utf-8")
                self._event_count = 0
                self._last_event_type = ""
                self._recording = True
                logger.info(f"Event recording started: {output_path}")
            except Exception as e:
                logger.error(f"Failed to start event recording: {e}")
                self._recording = False
                if self._file:
                    self._file.close()
                    self._file = None
                raise

    def stop(self) -> None:
        """Stop recording and close the file."""
        with self._lock:
            if not self._recording:
                return
            self._recording = False
            if self._file:
                try:
                    self._file.close()
                except Exception as e:
                    logger.error(f"Error closing recording file: {e}")
                finally:
                    self._file = None
            logger.info(
                f"Event recording stopped. {self._event_count} events recorded to {self._output_path}"
            )

    def record(self, source: str, event_type: str, event_data: Dict[str, Any]) -> None:
        """Record a single event with mandatory anonymization. No-op if not recording."""
        if not self._recording:
            return
        with self._lock:
            if not self._recording or not self._file:
                return
            try:
                record = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "source": source,
                    "event": event_type,
                    "data": self._anonymize_data(event_data),  # Always anonymize
                }
                self._file.write(json.dumps(record, default=str) + "\n")
                self._file.flush()
                self._event_count += 1
                self._last_event_type = event_type
            except Exception as e:
                logger.error(f"Error recording event: {e}")

    # ------------------------------------------------------------------
    # Anonymization
    # ------------------------------------------------------------------

    def _anonymize_data(self, data: Any) -> Any:
        """Create an anonymized deep copy of event data.

        Replaces:
        - Commander name and FID fields with configured mock values
        - Windows/Unix filesystem paths with redacted placeholders
        - Non-localhost IP addresses with 0.0.0.0
        """
        return self._walk(copy.deepcopy(data))

    def _walk(self, obj: Any) -> Any:
        """Recursively walk and scrub a data structure."""
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                if key in _COMMANDER_KEYS:
                    if key == "FID":
                        obj[key] = self.mock_fid
                    else:
                        obj[key] = self.mock_commander
                elif key in _PATH_KEYS and isinstance(obj[key], str):
                    obj[key] = self._scrub_string(obj[key])
                else:
                    obj[key] = self._walk(obj[key])
            return obj
        elif isinstance(obj, list):
            return [self._walk(item) for item in obj]
        elif isinstance(obj, str):
            return self._scrub_string(obj)
        return obj

    def _scrub_string(self, value: str) -> str:
        """Scrub identifying information from a string value."""
        # Replace Windows paths  (e.g. C:\Users\john\... → X:\Redacted\path)
        value = _WIN_PATH_RE.sub(self._redact_win_path, value)
        # Replace Unix home paths (e.g. /home/john/... → /home/redacted/...)
        value = _UNIX_HOME_RE.sub("/home/redacted", value)
        # Replace non-localhost IP addresses
        value = _IP_RE.sub("0.0.0.0", value)
        return value

    @staticmethod
    def _redact_win_path(match: re.Match) -> str:
        """Replace a Windows path, keeping the structure but removing user info."""
        path = match.group(0)
        # Keep only the last component (filename) if present
        parts = path.split("\\")
        if len(parts) > 2:
            return f"X:\\Redacted\\{parts[-1]}"
        return "X:\\Redacted"
