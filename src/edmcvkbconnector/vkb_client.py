"""
TCP/IP socket client for VKB hardware communication.

Implements fault-tolerant connection management with automatic reconnection.
The message format is abstracted and can be customized via MessageFormatter.
"""

import json
import logging
import socket
import threading
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .message_formatter import MessageFormatter

logger = logging.getLogger(__name__)


class VKBClient:
    """
    TCP/IP socket client for communicating with VKB hardware.
    
    Handles socket connection, message serialization, and event forwarding
    with fault-tolerant automatic reconnection capabilities.
    
    Reconnection Strategy:
    - Retry every 2 seconds for 1 minute (initial aggressive reconnection)
    - Then retry every 10 seconds indefinitely (fallback periodic reconnection)
    """

    # Reconnection constants
    INITIAL_RETRY_INTERVAL = 2  # seconds
    INITIAL_RETRY_DURATION = 60  # seconds
    FALLBACK_RETRY_INTERVAL = 10  # seconds
    SOCKET_TIMEOUT = 5  # seconds

    def __init__(self, host: str = "127.0.0.1", port: int = 12345, message_formatter: Optional["MessageFormatter"] = None):
        """
        Initialize VKB client.
        
        Args:
            host: VKB device IP address (default: localhost)
            port: VKB device port (default: 12345)
            message_formatter: Optional message formatter for VKB protocol.
                             If not provided, uses PlaceholderMessageFormatter.
                             Implement a custom MessageFormatter subclass to use
                             different serialization formats.
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
        # Message formatting
        if message_formatter is None:
            from .message_formatter import PlaceholderMessageFormatter
            message_formatter = PlaceholderMessageFormatter()
        self.message_formatter = message_formatter
        
        # Reconnection management
        self._reconnect_thread: Optional[threading.Thread] = None
        self._reconnect_event = threading.Event()
        self._stop_event = threading.Event()
        self._reconnect_lock = threading.Lock()
        self._last_connection_attempt = 0.0
        self._initial_retry_start_time = 0.0

    def connect(self) -> bool:
        """
        Establish connection to VKB hardware.
        
        Returns:
            True if connection successful, False otherwise.
        """
        with self._reconnect_lock:
            try:
                # Close existing socket if any
                self._close_socket()
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.SOCKET_TIMEOUT)
                self.socket.connect((self.host, self.port))
                self.connected = True
                self._last_connection_attempt = time.time()
                self._initial_retry_start_time = time.time()
                logger.info(f"Connected to VKB device at {self.host}:{self.port}")
                
                # Clear the reconnect event when connected
                self._reconnect_event.clear()
                
                return True
            except (socket.error, ConnectionRefusedError, OSError) as e:
                logger.warning(f"Failed to connect to VKB device: {e}")
                self.connected = False
                self._reconnect_event.set()
                return False

    def _close_socket(self) -> None:
        """Close socket without locking. Must be called with _reconnect_lock held."""
        if self.socket:
            try:
                self.socket.close()
            except socket.error:
                pass
            self.socket = None

    def disconnect(self) -> None:
        """Close connection to VKB hardware and stop reconnection attempts."""
        self._stop_event.set()
        self._wait_for_reconnect_thread()
        
        with self._reconnect_lock:
            self._close_socket()
            self.connected = False
            logger.info("Disconnected from VKB device")

    def send_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Send event data to VKB hardware.
        
        The event is formatted using the configured message formatter before
        transmission. This allows the protocol format to be independent of the
        event handling logic.
        
        Args:
            event_type: Type of Elite Dangerous event (e.g., "FSDJump").
            event_data: Event data dictionary.
            
        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.connected:
            logger.debug("Cannot send event: not connected to VKB device")
            return False

        with self._reconnect_lock:
            try:
                if not self.socket:
                    return False
                
                # Format the event using the message formatter
                message_bytes = self.message_formatter.format_event(event_type, event_data)
                
                self.socket.sendall(message_bytes)
                logger.debug(f"Sent {event_type} event to VKB")
                return True
            except (socket.error, OSError, BrokenPipeError) as e:
                logger.warning(f"Failed to send event (connection lost): {e}")
                self.connected = False
                self._reconnect_event.set()
                
                # Attempt to restart reconnection thread if not running
                if not self._reconnect_thread or not self._reconnect_thread.is_alive():
                    self._start_reconnect_thread()
                
                return False

    def is_connected(self) -> bool:
        """Check if currently connected to VKB hardware."""
        return self.connected

    def start_reconnection(self) -> None:
        """
        Start automatic reconnection attempts.
        
        Spawns a background thread that handles reconnection with exponential backoff:
        - Aggressive retry: every 2 seconds for 1 minute
        - Fallback retry: every 10 seconds indefinitely
        """
        self._stop_event.clear()
        self._start_reconnect_thread()

    def _start_reconnect_thread(self) -> None:
        """Start or restart the reconnection thread."""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._reconnect_thread = threading.Thread(
            target=self._reconnect_worker, daemon=True, name="VKBReconnect"
        )
        self._reconnect_thread.start()
        logger.debug("Started VKB reconnection thread")

    def _wait_for_reconnect_thread(self) -> None:
        """Wait for reconnection thread to finish."""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=5)

    def _reconnect_worker(self) -> None:
        """
        Background worker thread for handling automatic reconnection.
        
        Implements reconnection strategy:
        1. Try every 2 seconds for 1 minute
        2. Fall back to every 10 seconds indefinitely
        """
        logger.info("VKB reconnection worker started")
        self._initial_retry_start_time = time.time()

        while not self._stop_event.is_set():
            try:
                # Check if reconnection is needed
                if self._reconnect_event.is_set():
                    current_time = time.time()
                    time_since_initial = current_time - self._initial_retry_start_time

                    # Determine retry interval based on duration
                    if time_since_initial < self.INITIAL_RETRY_DURATION:
                        # First minute: retry every 2 seconds
                        if (
                            current_time - self._last_connection_attempt
                            >= self.INITIAL_RETRY_INTERVAL
                        ):
                            logger.debug(
                                f"Attempting to reconnect to {self.host}:{self.port} "
                                f"(initial phase)"
                            )
                            if self.connect():
                                logger.info(
                                    "Reconnection successful after connection loss"
                                )
                            else:
                                self._last_connection_attempt = time.time()
                    else:
                        # After minute: retry every 10 seconds
                        if (
                            current_time - self._last_connection_attempt
                            >= self.FALLBACK_RETRY_INTERVAL
                        ):
                            logger.debug(
                                f"Attempting to reconnect to {self.host}:{self.port} "
                                f"(fallback phase)"
                            )
                            if self.connect():
                                logger.info(
                                    "Reconnection successful (fallback phase)"
                                )
                            else:
                                self._last_connection_attempt = time.time()

                # Sleep briefly to avoid busy-waiting
                self._stop_event.wait(0.5)

            except Exception as e:
                logger.error(f"Unexpected error in reconnection worker: {e}")
                self._stop_event.wait(1)

        logger.info("VKB reconnection worker stopped")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
