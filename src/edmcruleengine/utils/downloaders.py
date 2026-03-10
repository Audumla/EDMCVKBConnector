"""
Generic downloader interface for software packages.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DownloadItem:
    """Represents a generic downloadable item."""
    version: str
    filename: str
    url: str
    # Provider-specific metadata can be stored in provider_data
    provider_data: Dict[str, Any] = field(default_factory=dict)


class Downloader(abc.ABC):
    """Abstract base class for software downloaders."""

    @abc.abstractmethod
    def list_items(self) -> List[DownloadItem]:
        """List all available items from this provider."""
        pass

    @abc.abstractmethod
    def download(self, item: DownloadItem, target_path: Path) -> bool:
        """Download a specific item to the given path."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if this downloader is available for use (e.g. backend present)."""
        pass
