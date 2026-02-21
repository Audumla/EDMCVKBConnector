"""
TCP/IP socket client for VKB-Link communication.

Uses the current VKB-Link `VKBShiftBitmap` message format by default.
Socket lifecycle management is intentionally driven by process workflow in
EventHandler/VKBLinkManager, not by aggressive socket retry loops.
"""

import socket
import threading
from typing import Any, Dict, Optional, TYPE_CHECKING

from . import plugin_logger

if TYPE_CHECKING:
    from .message_formatter import MessageFormatter

logger = plugin_logger(__name__)


class VKBClient:
    """
    TCP/IP socket client for communicating with VKB-Link.

    Handles socket connection, message serialization, and event forwarding.
    """

    DEFAULT_SOCKET_TIMEOUT = 5  # seconds

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50995,
        message_formatter: Optional["MessageFormatter"] = None,
        *,
        header_byte: int = 0xA5,
        command_byte: int = 13,
        socket_timeout: int = DEFAULT_SOCKET_TIMEOUT,
        on_connected: Optional[callable] = None,
    ):
        """
        Initialize VKB client.

        Args:
            host: VKB-Link host (default: localhost)
            port: VKB-Link port (default: 50995)
            message_formatter: Optional message formatter for VKB protocol.
                             If not provided, uses VKBLinkMessageFormatter.
            header_byte: VKB protocol header byte (default: 0xA5)
            command_byte: VKB protocol command byte (default: 13)
            socket_timeout: Socket timeout in seconds (default: 5)
            on_connected: Optional callback function to invoke after successful connection
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False

        # Connection callback for resending state after reconnection
        self._on_connected_callback = on_connected
        # Terminal error: if set, stop all reconnection attempts
        self._terminal_error = False
        self._terminal_error_message = ""

        self.SOCKET_TIMEOUT = socket_timeout

        # Message formatting
        if message_formatter is None:
            from .message_formatter import VKBLinkMessageFormatter
            message_formatter = VKBLinkMessageFormatter(
                header_byte=header_byte,
                command_byte=command_byte,
            )
        self.message_formatter = message_formatter

        self._send_lock = threading.Lock()

    def connect(self) -> bool:
        """
        Establish connection to VKB hardware.

        Calls the on_connected callback (if set) after successful connection
        to allow resending state to the hardware.

        Returns:
            True if connection successful, False otherwise.
        """
        with self._send_lock:
            try:
                # Close existing socket if any
                self._close_socket()

                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.SOCKET_TIMEOUT)
                self.socket.connect((self.host, self.port))
                self.connected = True
                logger.info(f"Connected to VKB device at {self.host}:{self.port}")

                # Store that we should invoke callback (after releasing lock)
                should_invoke_callback = True

            except (socket.error, socket.timeout, ConnectionRefusedError, OSError, TimeoutError) as e:
                logger.warning(f"Failed to connect to VKB device: {e}")
                self.connected = False
                should_invoke_callback = False

        # Invoke callback outside the lock to avoid deadlock
        if should_invoke_callback and self._on_connected_callback:
            try:
                self._on_connected_callback()
            except Exception as e:
                logger.error(f"Error in on_connected callback: {e}", exc_info=True)

        return self.connected

    def set_on_connected(self, callback: Optional[callable]) -> None:
        """
        Set or update the callback to invoke after successful connection.

        The callback is invoked outside the connection lock to avoid deadlocks.
        Useful for resending state after reconnection.

        Args:
            callback: Callable with no arguments, or None to remove callback.
        """
        self._on_connected_callback = callback

    def _close_socket(self) -> None:
        """Close socket without locking. Must be called with _send_lock held."""
        if self.socket:
            try:
                self.socket.close()
            except socket.error:
                pass
            self.socket = None

    def disconnect(self) -> None:
        """Close connection to VKB hardware."""
        with self._send_lock:
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
        with self._send_lock:
            # Atomic check of both connected flag and socket object
            if not self.connected or not self.socket:
                logger.debug("Cannot send event: not connected to VKB-Link")
                return False

            try:
                # Format the event using the message formatter
                message_bytes = self.message_formatter.format_event(event_type, event_data)

                self.socket.sendall(message_bytes)
                return True
            except (socket.error, socket.timeout, OSError, BrokenPipeError, TimeoutError) as e:
                logger.warning(f"Failed to send event (connection lost): {e}")
                self.connected = False
                self._close_socket()

                return False
            except Exception as e:
                logger.error(f"Error formatting or sending event: {e}")
                return False

    def is_connected(self) -> bool:
        """Check if currently connected to VKB-Link."""
        return self.connected

    def is_reconnecting(self) -> bool:
        """Socket reconnection worker is disabled; always False."""
        return False

    def mark_terminal_error(self, message: str = "Cannot connect to VKB-Link") -> None:
        """
        Mark a terminal error condition that stops all reconnection attempts.

        Use this when process is running and configuration matches, but TCP connection fails.
        Once set, reconnection attempts will not be made.

        Args:
            message: Human-readable error message for status display
        """
        with self._send_lock:
            self._terminal_error = True
            self._terminal_error_message = message
        logger.warning(f"VKB-Link terminal error marked: {message}")

    def is_terminal_error(self) -> bool:
        """Check if a terminal error condition has been set."""
        with self._send_lock:
            return self._terminal_error

    def clear_terminal_error(self) -> None:
        """Clear the terminal error condition (used on new connection attempt or recovery)."""
        with self._send_lock:
            self._terminal_error = False
            self._terminal_error_message = ""

    def get_terminal_error_message(self) -> str:
        """Get the terminal error message if set."""
        with self._send_lock:
            return self._terminal_error_message if self._terminal_error else ""

    def start_reconnection(self) -> None:
        """
        No-op by design.

        Reconnection attempts are process-driven by EventHandler when process
        lifecycle events require a reconnect.
        """
        return

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
