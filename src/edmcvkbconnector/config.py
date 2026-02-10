"""
Configuration management for EDMC VKB Connector.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Config:
    """
    Manages configuration for VKB connector.
    
    Configuration can be loaded from a JSON file or set programmatically.
    """

    DEFAULT_CONFIG = {
        "vkb_host": "127.0.0.1",
        "vkb_port": 12345,
        "enabled": True,
        "debug": False,
        "event_types": [
            "Location",
            "FSDJump",
            "DockingGranted",
            "Undocked",
            "LaunchSRV",
            "DockSRV",
        ],
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to configuration JSON file. If not provided,
                        uses default configuration.
        """
        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)

    def load_from_file(self, config_file: str) -> None:
        """
        Load configuration from JSON file.
        
        Args:
            config_file: Path to configuration JSON file.
        """
        try:
            with open(config_file, "r") as f:
                custom_config = json.load(f)
                self.config.update(custom_config)
                logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style assignment."""
        self.config[key] = value
