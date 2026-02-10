"""
TCP/IP socket client for VKB hardware communication.
"""

import json
import logging
import socket
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class VKBClient:
    """
    TCP/IP socket client for communicating with VKB hardware.
    
    Handles socket connection, message serialization, and event forwarding.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 12345):
        """
        Initialize VKB client.
        
        Args:
            host: VKB device IP address (default: localhost)
            port: VKB device port (default: 12345)
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False

    def connect(self) -> bool:
        """
        Establish connection to VKB hardware.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to VKB device at {self.host}:{self.port}")
            return True
        except (socket.error, ConnectionRefusedError, OSError) as e:
            logger.error(f"Failed to connect to VKB device: {e}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Close connection to VKB hardware."""
        if self.socket:
            try:
                self.socket.close()
                self.connected = False
                logger.info("Disconnected from VKB device")
            except socket.error as e:
                logger.error(f"Error closing socket: {e}")

    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Send event data to VKB hardware.
        
        Args:
            event_data: Dictionary containing event information.
            
        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.connected:
            logger.warning("Cannot send event: not connected to VKB device")
            return False

        try:
            message = json.dumps(event_data) + "\n"
            self.socket.sendall(message.encode("utf-8"))
            logger.debug(f"Sent event to VKB: {event_data}")
            return True
        except (socket.error, OSError) as e:
            logger.error(f"Failed to send event: {e}")
            self.connected = False
            return False

    def is_connected(self) -> bool:
        """Check if currently connected to VKB hardware."""
        return self.connected

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
