"""
Event handler for forwarding Elite Dangerous events to VKB hardware.
"""

import logging
from typing import Any, Callable, Dict, Optional

from .config import Config
from .vkb_client import VKBClient

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Handles EDMC events and forwards them to VKB hardware.
    
    Manages event filtering, serialization, and transmission to VKB device.
    """

    def __init__(self, config: Config, vkb_client: Optional[VKBClient] = None):
        """
        Initialize event handler.
        
        Args:
            config: Configuration object.
            vkb_client: VKB client instance (created if not provided).
        """
        self.config = config
        self.vkb_client = vkb_client or VKBClient(
            host=config.get("vkb_host", "127.0.0.1"),
            port=config.get("vkb_port", 12345),
        )
        self.enabled = config.get("enabled", True)
        self.debug = config.get("debug", False)
        self.event_types = config.get("event_types", [])

    def connect(self) -> bool:
        """Connect to VKB hardware."""
        if self.enabled:
            return self.vkb_client.connect()
        return False

    def disconnect(self) -> None:
        """Disconnect from VKB hardware."""
        self.vkb_client.disconnect()

    def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Handle an EDMC event.
        
        Args:
            event_type: Type of event (e.g., "Location", "FSDJump").
            event_data: Event data dictionary.
        """
        if not self.enabled:
            return

        # Filter by configured event types if list is not empty
        if self.event_types and event_type not in self.event_types:
            return

        # Build forwarding message
        message = {"event": event_type, "data": event_data}

        if self.debug:
            logger.debug(f"Event received: {message}")

        # Send to VKB hardware
        if not self.vkb_client.send_event(message):
            logger.warning(f"Failed to send {event_type} event to VKB")

    def enable(self) -> None:
        """Enable event forwarding."""
        self.enabled = True
        logger.info("Event forwarding enabled")

    def disable(self) -> None:
        """Disable event forwarding."""
        self.enabled = False
        logger.info("Event forwarding disabled")

    def set_debug(self, enabled: bool) -> None:
        """Enable or disable debug logging."""
        self.debug = enabled
        logger.info(f"Debug logging {'enabled' if enabled else 'disabled'}")
